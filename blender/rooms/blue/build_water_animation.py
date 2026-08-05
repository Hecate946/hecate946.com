"""Build and render the blue room as a Cycles water panorama animation.

This script is intentionally blue-room-only. It rebuilds the current blue room
through the shared room builder, adds a Mantaflow liquid simulation in a
separate collection, renders an equirectangular PNG sequence, and encodes a
looping VP9 WebM for the website.

Run from the project root:

    blender --background --python blender/rooms/blue/build_water_animation.py

The website files are published afterward with:

    npm run assets:sync
"""

from __future__ import annotations

import importlib.util
import math
from pathlib import Path
import shutil
import subprocess
import sys

import bpy


# =============================================================================
# EASY SETTINGS
# =============================================================================
# "FAST", "LIT", or "CRISP". LIT is the recommended first full render.
QUALITY = "FAST"

# Rebuild the base room from the exact current shared room code before adding
# water. Keep this True unless you are intentionally iterating inside the saved
# blue-room-water.blend file.
REBUILD_BASE_ROOM = True

# Bake Mantaflow and render the final video. Turning either off is useful when
# inspecting the generated .blend interactively.
BAKE_SIMULATION = True
RENDER_ANIMATION = True

# Remove the large temporary PNG sequence after WebM encoding succeeds.
KEEP_RENDERED_FRAMES = False

# Use the user's configured Cycles GPU devices when available.
USE_GPU = True

FPS = 24
SIMULATION_START_FRAME = 1
RENDER_START_FRAME = 25  # one-second simulation warm-up

QUALITY_PRESETS = {
    "FAST": {
        "width": 2048,
        "height": 1024,
        "samples": 16,
        "liquid_resolution": 64,
        "render_frames": 96,
        "vp9_crf": 29,
    },
    "LIT": {
        "width": 3072,
        "height": 1536,
        "samples": 32,
        "liquid_resolution": 96,
        "render_frames": 144,
        "vp9_crf": 25,
    },
    "CRISP": {
        "width": 4096,
        "height": 2048,
        "samples": 64,
        "liquid_resolution": 128,
        "render_frames": 192,
        "vp9_crf": 22,
    },
}


BLUE_DIRECTORY = Path(__file__).resolve().parent
ROOMS_ROOT = BLUE_DIRECTORY.parent
PROJECT_ROOT = ROOMS_ROOT.parent.parent
SHARED_BUILDER_FILE = ROOMS_ROOT / "shared" / "room_builder.py"
CACHE_DIRECTORY = BLUE_DIRECTORY / "cache" / "water"
FRAMES_DIRECTORY = BLUE_DIRECTORY / "water-frames"
WATER_BLEND_FILE = BLUE_DIRECTORY / "blue-room-water.blend"
WATER_VIDEO_FILE = BLUE_DIRECTORY / "blue-room-water.webm"
WATER_POSTER_FILE = BLUE_DIRECTORY / "blue-room-water-poster.png"


def load_room_builder():
    module_name = "hecate_blue_water_room_builder"
    spec = importlib.util.spec_from_file_location(module_name, SHARED_BUILDER_FILE)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load room builder: {SHARED_BUILDER_FILE}")

    sys.modules.pop(module_name, None)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def move_to_collection(obj: bpy.types.Object, collection: bpy.types.Collection):
    for old_collection in list(obj.users_collection):
        old_collection.objects.unlink(obj)
    collection.objects.link(obj)


def activate(obj: bpy.types.Object):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def apply_transform(obj: bpy.types.Object):
    activate(obj)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)


def set_if_present(owner, attribute: str, value):
    if not hasattr(owner, attribute):
        return False
    try:
        setattr(owner, attribute, value)
        return True
    except (AttributeError, TypeError, ValueError):
        return False


def set_socket(node, names, value):
    if isinstance(names, str):
        names = (names,)
    for name in names:
        socket = node.inputs.get(name)
        if socket is not None:
            socket.default_value = value
            return True
    return False


def create_water_material() -> bpy.types.Material:
    material = bpy.data.materials.new("Blue Room Physical Water")
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()

    output = nodes.new("ShaderNodeOutputMaterial")
    principled = nodes.new("ShaderNodeBsdfPrincipled")
    absorption = nodes.new("ShaderNodeVolumeAbsorption")

    set_socket(principled, "Base Color", (0.006, 0.025, 0.045, 1.0))
    set_socket(principled, "Roughness", 0.035)
    set_socket(principled, ("Transmission Weight", "Transmission"), 1.0)
    set_socket(principled, "IOR", 1.333)
    set_socket(principled, ("Coat Weight", "Clearcoat"), 0.08)
    set_socket(principled, ("Coat Roughness", "Clearcoat Roughness"), 0.025)

    absorption.inputs["Color"].default_value = (0.035, 0.22, 0.34, 1.0)
    absorption.inputs["Density"].default_value = 0.12

    links.new(principled.outputs["BSDF"], output.inputs["Surface"])
    links.new(absorption.outputs["Volume"], output.inputs["Volume"])
    return material


def add_cube(
    name: str,
    location: tuple[float, float, float],
    dimensions: tuple[float, float, float],
    collection: bpy.types.Collection,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    apply_transform(obj)
    move_to_collection(obj, collection)
    return obj


def add_fluid_modifier(obj: bpy.types.Object, fluid_type: str):
    activate(obj)
    modifier = obj.modifiers.new(name=f"{fluid_type.title()} Fluid", type="FLUID")
    modifier.fluid_type = fluid_type
    bpy.context.view_layer.update()
    return modifier


def require_settings(modifier, attribute: str):
    for _ in range(8):
        bpy.context.view_layer.update()
        settings = getattr(modifier, attribute, None)
        if settings is not None:
            return settings
    raise RuntimeError(
        f"Blender did not initialize {attribute} for modifier {modifier.name}."
    )


def add_liquid_source(
    collection: bpy.types.Collection,
    room_width: float,
    room_depth: float,
    water_level: float,
):
    bottom = 0.045
    source = add_cube(
        "Blue Water Initial Fill (50 Percent)",
        (0.0, 0.0, (bottom + water_level) / 2.0),
        (room_width - 0.10, room_depth - 0.10, water_level - bottom),
        collection,
    )
    source.display_type = "WIRE"
    source["water_simulation_helper"] = True

    modifier = add_fluid_modifier(source, "FLOW")
    settings = require_settings(modifier, "flow_settings")
    settings.flow_type = "LIQUID"
    settings.flow_behavior = "GEOMETRY"
    set_if_present(settings, "surface_distance", 1.5)
    set_if_present(settings, "use_plane_init", False)
    return source


def add_wave_paddle(
    collection: bpy.types.Collection,
    name: str,
    location: tuple[float, float, float],
    dimensions: tuple[float, float, float],
    motion: tuple[float, float, float],
    phase: float,
    simulation_end: int,
):
    paddle = add_cube(name, location, dimensions, collection)
    paddle.display_type = "WIRE"
    paddle["water_simulation_helper"] = True

    modifier = add_fluid_modifier(paddle, "EFFECTOR")
    settings = require_settings(modifier, "effector_settings")
    settings.effector_type = "COLLISION"
    set_if_present(settings, "surface_distance", 0.003)
    set_if_present(settings, "use_plane_init", False)

    base = paddle.location.copy()
    sample_step = 8
    period = 48.0
    for frame in range(SIMULATION_START_FRAME, simulation_end + sample_step, sample_step):
        angle = (2.0 * math.pi * (frame - SIMULATION_START_FRAME) / period) + phase
        paddle.location = (
            base.x + motion[0] * math.sin(angle),
            base.y + motion[1] * math.sin(angle * 0.83 + phase * 0.35),
            base.z + motion[2] * math.sin(angle),
        )
        paddle.rotation_euler[2] = math.radians(10.0) * math.sin(angle * 0.5 + phase)
        paddle.keyframe_insert(data_path="location", frame=frame)
        paddle.keyframe_insert(data_path="rotation_euler", frame=frame)

    # Do not access Action.fcurves here. Blender 5.0 removed the legacy
    # Action.fcurves API in favor of layered/slotted Actions. Newly inserted
    # keyframes already use Blender's configured interpolation (Bezier by
    # default), so no post-processing is required for this sampled motion.
    return paddle


def add_turbulence_field(
    collection: bpy.types.Collection,
    name: str,
    location: tuple[float, float, float],
    phase: float,
    simulation_end: int,
):
    bpy.ops.object.effector_add(type="TURBULENCE", location=location)
    field = bpy.context.object
    field.name = name
    move_to_collection(field, collection)
    field.hide_render = True
    field.display_type = "WIRE"
    field.field.strength = 2.4
    field.field.size = 0.9
    field.field.noise = 1.2

    sample_step = 12
    for frame in range(SIMULATION_START_FRAME, simulation_end + sample_step, sample_step):
        angle = (2.0 * math.pi * (frame - SIMULATION_START_FRAME) / 72.0) + phase
        field.field.strength = 2.2 + 1.4 * (0.5 + 0.5 * math.sin(angle))
        field.rotation_euler[2] = angle * 0.18
        field.keyframe_insert(data_path="field.strength", frame=frame)
        field.keyframe_insert(data_path="rotation_euler", frame=frame)

    # Keep this compatible with both legacy and layered/slotted Actions by
    # avoiding the removed Action.fcurves collection.
    return field


def add_liquid_domain(
    collection: bpy.types.Collection,
    room_width: float,
    room_depth: float,
    room_height: float,
    simulation_end: int,
    liquid_resolution: int,
    water_material: bpy.types.Material,
):
    domain_bottom = 0.035
    domain_top = room_height - 0.18
    domain = add_cube(
        "Blue Water Liquid Domain",
        (0.0, 0.0, (domain_bottom + domain_top) / 2.0),
        (room_width - 0.035, room_depth - 0.035, domain_top - domain_bottom),
        collection,
    )
    domain.display_type = "WIRE"
    domain.data.materials.append(water_material)

    modifier = add_fluid_modifier(domain, "DOMAIN")
    settings = require_settings(modifier, "domain_settings")
    settings.domain_type = "LIQUID"
    settings.cache_type = "ALL"
    settings.cache_directory = str(CACHE_DIRECTORY)
    settings.cache_frame_start = SIMULATION_START_FRAME
    settings.cache_frame_end = simulation_end
    settings.resolution_max = liquid_resolution
    settings.timesteps_min = 2
    settings.timesteps_max = 5
    settings.time_scale = 1.0

    set_if_present(settings, "cache_resumable", True)
    set_if_present(settings, "cache_data_format", "OPENVDB")
    set_if_present(settings, "simulation_method", "FLIP")
    set_if_present(settings, "flip_ratio", 0.97)
    set_if_present(settings, "particle_number", 2)
    set_if_present(settings, "particle_randomness", 0.08)
    set_if_present(settings, "use_fractions", True)
    set_if_present(settings, "fractions_threshold", 0.02)
    set_if_present(settings, "use_speed_vectors", True)
    set_if_present(settings, "use_mesh", True)
    set_if_present(settings, "mesh_scale", 2)
    set_if_present(settings, "particle_radius", 1.35)
    set_if_present(settings, "mesh_smoothen_pos", 2)
    set_if_present(settings, "mesh_smoothen_neg", 1)
    set_if_present(settings, "use_diffusion", True)
    set_if_present(settings, "viscosity_base", 1.0)
    set_if_present(settings, "viscosity_exponent", 6)
    set_if_present(settings, "surface_tension", 0.072)

    # Keep the rectangular room watertight using the domain's own boundaries.
    for side in ("front", "back", "left", "right", "top", "bottom"):
        set_if_present(settings, f"use_collision_border_{side}", True)

    return domain, modifier



def hide_simulation_helpers(collection: bpy.types.Collection):
    """Hide source/collision geometry only after the liquid cache is baked."""
    for obj in collection.all_objects:
        if obj.get("water_simulation_helper", False):
            obj.hide_render = True


def configure_cycles_render(scene: bpy.types.Scene, preset: dict, render_end: int):
    scene.render.engine = "CYCLES"
    scene.cycles.device = "GPU" if USE_GPU else "CPU"
    scene.cycles.samples = preset["samples"]
    scene.cycles.use_denoising = True
    set_if_present(scene.cycles, "use_adaptive_sampling", True)
    set_if_present(scene.cycles, "max_bounces", 10)
    set_if_present(scene.cycles, "transmission_bounces", 8)
    set_if_present(scene.cycles, "transparent_max_bounces", 8)

    scene.render.resolution_x = preset["width"]
    scene.render.resolution_y = preset["height"]
    scene.render.resolution_percentage = 100
    scene.render.fps = FPS
    scene.render.fps_base = 1.0
    scene.frame_start = RENDER_START_FRAME
    scene.frame_end = render_end
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    set_if_present(scene.render.image_settings, "color_depth", "8")
    scene.render.film_transparent = False
    set_if_present(scene.render, "use_motion_blur", True)
    set_if_present(scene.render, "motion_blur_shutter", 0.32)

    camera = bpy.data.objects.get("Panorama_Camera")
    if camera is None or camera.type != "CAMERA":
        raise RuntimeError("The shared room builder did not create Panorama_Camera.")
    camera.data.clip_start = 0.01
    scene.camera = camera

    FRAMES_DIRECTORY.mkdir(parents=True, exist_ok=True)
    scene.render.filepath = str(FRAMES_DIRECTORY / "frame_")


def bake_simulation(domain: bpy.types.Object):
    if CACHE_DIRECTORY.exists():
        shutil.rmtree(CACHE_DIRECTORY)
    CACHE_DIRECTORY.mkdir(parents=True, exist_ok=True)

    bpy.context.scene.frame_set(SIMULATION_START_FRAME)
    activate(domain)
    print("Baking blue-room liquid simulation...")

    with bpy.context.temp_override(
        object=domain,
        active_object=domain,
        selected_objects=[domain],
        selected_editable_objects=[domain],
    ):
        result = bpy.ops.fluid.bake_all()
    if "FINISHED" not in result:
        raise RuntimeError(f"Mantaflow bake did not finish: {result}")


def render_frames(scene: bpy.types.Scene):
    if FRAMES_DIRECTORY.exists():
        shutil.rmtree(FRAMES_DIRECTORY)
    FRAMES_DIRECTORY.mkdir(parents=True, exist_ok=True)
    scene.render.filepath = str(FRAMES_DIRECTORY / "frame_")
    print("Rendering Cycles equirectangular water animation frames...")
    bpy.ops.render.render(animation=True)


def run_ffmpeg(command: list[str]):
    print("Encoding command:")
    print(" ".join(command))
    subprocess.run(command, check=True)


def encode_webm(preset: dict, render_end: int):
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError(
            "ffmpeg is required to encode blue-room-water.webm but was not found."
        )

    source_pattern = str(FRAMES_DIRECTORY / "frame_%04d.png")
    frame_count = render_end - RENDER_START_FRAME + 1
    duration = frame_count / FPS
    overlap = min(0.75, duration / 4.0)
    main_duration = duration - overlap

    # Blend the final fraction of a second into the opening frames so the HTML
    # video loop has no hard cut. If the filter is unavailable in the user's
    # ffmpeg build, fall back to a normal VP9 encode rather than losing the render.
    blend_span = max(overlap - (1.0 / FPS), 0.1)
    loop_filter = (
        f"[0:v]trim=start=0:end={main_duration:.6f},setpts=PTS-STARTPTS[main];"
        f"[0:v]trim=start={main_duration:.6f}:end={duration:.6f},"
        "setpts=PTS-STARTPTS[tail];"
        f"[1:v]trim=start=0:end={overlap:.6f},setpts=PTS-STARTPTS[head];"
        f"[tail][head]blend=all_expr='A*(1-min(1,T/{blend_span:.6f}))"
        f"+B*min(1,T/{blend_span:.6f})'[blend];"
        f"[main][blend]concat=n=2:v=1:a=0,fps={FPS},"
        "format=yuv420p[outv]"
    )

    common_codec = [
        "-c:v",
        "libvpx-vp9",
        "-crf",
        str(preset["vp9_crf"]),
        "-b:v",
        "0",
        "-deadline",
        "good",
        "-cpu-used",
        "2",
        "-row-mt",
        "1",
        "-an",
        "-y",
        str(WATER_VIDEO_FILE),
    ]

    seamless_command = [
        ffmpeg,
        "-framerate",
        str(FPS),
        "-start_number",
        str(RENDER_START_FRAME),
        "-i",
        source_pattern,
        "-framerate",
        str(FPS),
        "-start_number",
        str(RENDER_START_FRAME),
        "-i",
        source_pattern,
        "-filter_complex",
        loop_filter,
        "-map",
        "[outv]",
        *common_codec,
    ]

    try:
        run_ffmpeg(seamless_command)
    except subprocess.CalledProcessError:
        print("Seamless crossfade encode failed; encoding a standard loop instead.")
        fallback_command = [
            ffmpeg,
            "-framerate",
            str(FPS),
            "-start_number",
            str(RENDER_START_FRAME),
            "-i",
            source_pattern,
            "-pix_fmt",
            "yuv420p",
            *common_codec,
        ]
        run_ffmpeg(fallback_command)

    first_frame = FRAMES_DIRECTORY / f"frame_{RENDER_START_FRAME:04d}.png"
    if not first_frame.exists():
        raise RuntimeError(f"Missing first rendered water frame: {first_frame}")
    shutil.copy2(first_frame, WATER_POSTER_FILE)

    if not KEEP_RENDERED_FRAMES:
        shutil.rmtree(FRAMES_DIRECTORY)


def main():
    quality_name = QUALITY.strip().upper()
    if quality_name not in QUALITY_PRESETS:
        raise ValueError('QUALITY must be "FAST", "LIT", or "CRISP".')
    preset = QUALITY_PRESETS[quality_name]
    render_end = RENDER_START_FRAME + preset["render_frames"] - 1

    room_builder = load_room_builder()
    if REBUILD_BASE_ROOM:
        base_settings = room_builder.RenderSettings(
            width=preset["width"],
            height=preset["height"],
            samples=preset["samples"],
            use_gpu=USE_GPU,
            auto_render=False,
        )
        room_builder.build_room(
            room_builder.RoomDefinition(
                "blue",
                "The Blue Room",
                "Room 004",
                "#3088D6",
            ),
            base_settings,
            ROOMS_ROOT,
        )

    scene = bpy.context.scene
    scene.frame_start = SIMULATION_START_FRAME
    scene.frame_end = render_end

    existing_collection = bpy.data.collections.get("BLUE_WATER_ANIMATION")
    if existing_collection is not None:
        for obj in list(existing_collection.objects):
            bpy.data.objects.remove(obj, do_unlink=True)
        bpy.data.collections.remove(existing_collection)

    water_collection = bpy.data.collections.new("BLUE_WATER_ANIMATION")
    scene.collection.children.link(water_collection)

    room_width = room_builder.ROOM_WIDTH
    room_depth = room_builder.ROOM_DEPTH
    room_height = room_builder.ROOM_HEIGHT
    water_level = room_height * 0.5

    print("=" * 72)
    print("Blue-room water animation")
    print(f"Quality:          {quality_name}")
    print(f"Water level:      {water_level:.3f} m (50% of room height)")
    print(f"Camera height:    {room_builder.CAMERA_LOCATION[2]:.3f} m")
    print(f"Liquid resolution:{preset['liquid_resolution']}")
    print(f"Frames:           {RENDER_START_FRAME}-{render_end} at {FPS} fps")
    print("=" * 72)

    water_material = create_water_material()
    add_liquid_source(water_collection, room_width, room_depth, water_level)

    paddle_specs = (
        (
            "Water Wave Paddle A",
            (-1.20, 1.65, water_level - 0.12),
            (0.66, 0.16, 0.42),
            (0.10, 0.13, 0.38),
            0.0,
        ),
        (
            "Water Wave Paddle B",
            (1.18, -1.35, water_level - 0.16),
            (0.62, 0.16, 0.40),
            (-0.11, 0.12, 0.34),
            math.pi * 0.72,
        ),
        (
            "Water Wave Paddle C",
            (-1.46, -0.55, water_level - 0.20),
            (0.14, 0.70, 0.38),
            (0.12, -0.10, 0.30),
            math.pi * 1.31,
        ),
        (
            "Water Wave Paddle D",
            (1.42, 0.72, water_level - 0.18),
            (0.14, 0.66, 0.38),
            (-0.10, 0.11, 0.32),
            math.pi * 1.76,
        ),
    )
    for name, location, dimensions, motion, phase in paddle_specs:
        add_wave_paddle(
            water_collection,
            name,
            location,
            dimensions,
            motion,
            phase,
            render_end,
        )

    add_turbulence_field(
        water_collection,
        "Submerged Turbulence A",
        (-0.72, 0.62, water_level - 0.65),
        0.4,
        render_end,
    )
    add_turbulence_field(
        water_collection,
        "Submerged Turbulence B",
        (0.82, -0.74, water_level - 0.58),
        2.2,
        render_end,
    )

    domain, _ = add_liquid_domain(
        water_collection,
        room_width,
        room_depth,
        room_height,
        render_end,
        preset["liquid_resolution"],
        water_material,
    )

    configure_cycles_render(scene, preset, render_end)
    bpy.ops.wm.save_as_mainfile(filepath=str(WATER_BLEND_FILE))

    if BAKE_SIMULATION:
        bake_simulation(domain)
        bpy.ops.wm.save_as_mainfile(filepath=str(WATER_BLEND_FILE))
    else:
        print("Skipped Mantaflow bake.")

    hide_simulation_helpers(water_collection)

    if RENDER_ANIMATION:
        render_frames(scene)
        encode_webm(preset, render_end)
    else:
        print("Skipped animation render and WebM encode.")

    bpy.ops.wm.save_as_mainfile(filepath=str(WATER_BLEND_FILE))
    print("Blue-room water animation finished.")
    print(f"  Water blend: {WATER_BLEND_FILE}")
    print(f"  Water video: {WATER_VIDEO_FILE}")
    print(f"  Water poster:{WATER_POSTER_FILE}")
    print("Run `npm run assets:sync` to publish the video and poster.")


if __name__ == "__main__":
    main()
