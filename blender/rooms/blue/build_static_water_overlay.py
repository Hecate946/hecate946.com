"""Render a clear water overlay (poster + preview animation) for the blue room.

This script keeps the base blue-room panorama exactly as rendered by the shared
room builder and produces:

- blue-room-water-overlay.png   (static poster / fallback)
- blue-room-water-overlay.webm  (transparent looping preview animation)

The browser composites the overlay on top of the existing blue-room panorama.
Only the water is visible in the overlay; the rest of the frame remains
transparent.
"""

from __future__ import annotations

from pathlib import Path
import importlib
import importlib.util
import shutil
import subprocess
import sys

import bpy


# =============================================================================
# EASY SETTINGS
# =============================================================================
# False keeps the existing room panorama untouched and renders only the overlay.
AUTO_RENDER_BASE_PANORAMA = False

# Small and quick by default so you can preview the motion ASAP.
# "PREVIEW", "FAST", or "LIT"
RENDER_QUALITY = "PREVIEW"

USE_GPU = True
FRAME_START = 1
FRAME_END = 36
FRAME_RATE = 12
KEEP_RENDERED_FRAMES = False

# Water tuning: lower fill, clearer water, calmer motion, and wall-to-wall coverage.
WATER_FILL_RATIO = 0.30
WATER_SURFACE_PRIMARY_SLOSH = 0.045
WATER_SURFACE_SECONDARY_SLOSH = 0.028
WATER_RIPPLE_A_STRENGTH = 0.008
WATER_RIPPLE_B_STRENGTH = 0.0045
WATER_EDGE_OVERSCAN = 0.22
SEAM_FIX_COLUMNS = 6
WATER_WALL_OVERLAP = 0.18
WATER_RIPPLE_C_STRENGTH = 0.003

QUALITY_PRESETS = {
    "PREVIEW": {"width": 1600, "height": 800, "samples": 18},
    "FAST": {"width": 2048, "height": 1024, "samples": 32},
    "LIT": {"width": 4096, "height": 2048, "samples": 64},
}


def is_preview_quality(quality_name: str) -> bool:
    return quality_name.strip().upper() == "PREVIEW"


def script_directory() -> Path:
    try:
        text = bpy.context.space_data.text
        if text and text.filepath:
            path = Path(bpy.path.abspath(text.filepath)).resolve()
            if path.suffix.lower() == ".py":
                return path.parent
    except (AttributeError, RuntimeError):
        pass

    try:
        path = Path(__file__).resolve()
        if path.suffix.lower() == ".py":
            return path.parent
    except NameError:
        pass

    if bpy.data.filepath:
        return Path(bpy.data.filepath).resolve().parent

    return Path.cwd().resolve()


def load_live_room_builder(builder_file: Path):
    module_name = "hecate_room_builder_live_water_overlay"
    importlib.invalidate_caches()
    sys.modules.pop(module_name, None)

    try:
        pyc_path = Path(importlib.util.cache_from_source(str(builder_file)))
        if pyc_path.exists():
            pyc_path.unlink()
    except Exception:
        pass

    spec = importlib.util.spec_from_file_location(module_name, builder_file)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load shared room builder: {builder_file}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def set_socket(node, names, value) -> None:
    if isinstance(names, str):
        names = (names,)
    for name in names:
        if name in node.inputs:
            node.inputs[name].default_value = value
            return


def animate_socket_ping_pong(socket, start_value: float, peak_value: float, end_frame: int):
    mid_frame = max(2, end_frame // 2)
    socket.default_value = start_value
    socket.keyframe_insert(data_path="default_value", frame=1)
    socket.default_value = peak_value
    socket.keyframe_insert(data_path="default_value", frame=mid_frame)
    socket.default_value = start_value
    socket.keyframe_insert(data_path="default_value", frame=end_frame)


def create_water_material(name: str, preview_mode: bool = False, frame_end: int = FRAME_END):
    mat = bpy.data.materials.new(name)
    node_tree = mat.node_tree
    if node_tree is None:
        raise RuntimeError("Material node tree is unavailable.")

    nodes = node_tree.nodes
    links = node_tree.links
    bsdf = nodes.get("Principled BSDF")
    material_output = nodes.get("Material Output")
    if bsdf is None or material_output is None:
        raise RuntimeError("Principled BSDF or Material Output is unavailable.")

    # More realistic swimming-pool water: bluer tint, more reflective highlights,
    # and far less milky opacity so the tiled floor remains visible below.
    set_socket(bsdf, "Roughness", 0.02 if preview_mode else 0.014)
    set_socket(bsdf, "IOR", 1.333)
    set_socket(bsdf, "Specular IOR Level", 0.32 if preview_mode else 0.42)
    set_socket(bsdf, "Transmission Weight", 0.0)
    set_socket(bsdf, "Transmission", 0.0)

    noise_a = nodes.new("ShaderNodeTexNoise")
    noise_a.noise_dimensions = "4D"
    noise_a.inputs["Scale"].default_value = 9.5
    noise_a.inputs["Detail"].default_value = 7.5
    noise_a.inputs["Roughness"].default_value = 0.46

    noise_b = nodes.new("ShaderNodeTexNoise")
    noise_b.noise_dimensions = "4D"
    noise_b.inputs["Scale"].default_value = 3.6
    noise_b.inputs["Detail"].default_value = 5.4
    noise_b.inputs["Roughness"].default_value = 0.34

    noise_caustic = nodes.new("ShaderNodeTexNoise")
    noise_caustic.noise_dimensions = "4D"
    noise_caustic.inputs["Scale"].default_value = 23.0
    noise_caustic.inputs["Detail"].default_value = 2.2
    noise_caustic.inputs["Roughness"].default_value = 0.28

    # Animate the procedural surface itself so every frame has visible motion.
    animate_socket_ping_pong(noise_a.inputs["W"], 0.0, 0.7, frame_end)
    animate_socket_ping_pong(noise_b.inputs["W"], 0.25, 1.0, frame_end)
    animate_socket_ping_pong(noise_caustic.inputs["W"], 0.14, 1.25, frame_end)

    bump_mix = nodes.new("ShaderNodeMixRGB")
    bump_mix.blend_type = "ADD"
    bump_mix.inputs["Fac"].default_value = 0.12

    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.010 if preview_mode else 0.0135
    bump.inputs["Distance"].default_value = 1.0

    deep_blue = nodes.new("ShaderNodeRGB")
    deep_blue.outputs[0].default_value = (0.18, 0.58, 0.9, 1.0)
    shallow_blue = nodes.new("ShaderNodeRGB")
    shallow_blue.outputs[0].default_value = (0.54, 0.88, 1.0, 1.0)
    tint_mix = nodes.new("ShaderNodeMixRGB")
    tint_mix.blend_type = "MIX"
    tint_mix.inputs["Fac"].default_value = 0.35

    caustic_ramp = nodes.new("ShaderNodeValToRGB")
    caustic_ramp.color_ramp.elements[0].position = 0.62
    caustic_ramp.color_ramp.elements[0].color = (0.0, 0.0, 0.0, 1.0)
    caustic_ramp.color_ramp.elements[1].position = 0.95
    caustic_ramp.color_ramp.elements[1].color = (0.75, 0.95, 1.0, 1.0)
    caustic_screen = nodes.new("ShaderNodeMixRGB")
    caustic_screen.blend_type = "SCREEN"
    caustic_screen.inputs["Fac"].default_value = 0.18 if preview_mode else 0.22

    transparent = nodes.new("ShaderNodeBsdfTransparent")
    fresnel = nodes.new("ShaderNodeFresnel")
    fresnel.inputs["IOR"].default_value = 1.333
    visibility_scale = nodes.new("ShaderNodeMath")
    visibility_scale.operation = "MULTIPLY"
    visibility_scale.inputs[1].default_value = 0.38 if preview_mode else 0.46
    visibility_bias = nodes.new("ShaderNodeMath")
    visibility_bias.operation = "ADD"
    visibility_bias.inputs[1].default_value = 0.02 if preview_mode else 0.03
    clamp = nodes.new("ShaderNodeClamp")
    mix_shader = nodes.new("ShaderNodeMixShader")

    links.new(noise_a.outputs["Fac"], bump_mix.inputs[1])
    links.new(noise_b.outputs["Fac"], bump_mix.inputs[2])
    links.new(bump_mix.outputs["Color"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

    links.new(deep_blue.outputs["Color"], tint_mix.inputs[1])
    links.new(shallow_blue.outputs["Color"], tint_mix.inputs[2])
    links.new(noise_caustic.outputs["Fac"], caustic_ramp.inputs["Fac"])
    links.new(tint_mix.outputs["Color"], caustic_screen.inputs[1])
    links.new(caustic_ramp.outputs["Color"], caustic_screen.inputs[2])
    links.new(caustic_screen.outputs["Color"], bsdf.inputs["Base Color"])

    links.new(fresnel.outputs["Fac"], visibility_scale.inputs[0])
    links.new(visibility_scale.outputs["Value"], visibility_bias.inputs[0])
    links.new(visibility_bias.outputs["Value"], clamp.inputs["Value"])
    links.new(clamp.outputs["Result"], mix_shader.inputs[0])
    links.new(transparent.outputs["BSDF"], mix_shader.inputs[1])
    links.new(bsdf.outputs["BSDF"], mix_shader.inputs[2])
    links.new(mix_shader.outputs["Shader"], material_output.inputs["Surface"])

    return mat


def add_motion_driver_empty(name: str, location=(0.0, 0.0, 0.0)):
    empty = bpy.data.objects.new(name, None)
    empty.empty_display_type = "PLAIN_AXES"
    empty.location = location
    bpy.context.scene.collection.objects.link(empty)
    return empty


def animate_empty_loop(empty, waypoints):
    for frame, location in waypoints:
        empty.location = location
        empty.keyframe_insert(data_path="location", frame=frame)


def add_water_clip_box(room_width: float, room_depth: float, water_height: float):
    bpy.ops.mesh.primitive_cube_add(
        location=(0.0, 0.0, water_height / 2.0),
        scale=(
            room_width / 2.0 + WATER_WALL_OVERLAP,
            room_depth / 2.0 + WATER_WALL_OVERLAP,
            water_height / 2.0 + 0.02,
        ),
    )
    clip_box = bpy.context.active_object
    clip_box.name = "BlueRoomWaterClipBox"
    clip_box.display_type = "WIRE"
    clip_box.hide_render = True
    return clip_box


def add_water_object(room_builder_module, frame_end: int, preview_mode: bool = False):
    room_width = room_builder_module.ROOM_WIDTH
    room_depth = room_builder_module.ROOM_DEPTH
    room_height = room_builder_module.ROOM_HEIGHT

    water_height = room_height * WATER_FILL_RATIO
    grid_x = 64 if preview_mode else 120
    grid_y = 96 if preview_mode else 180

    bpy.ops.mesh.primitive_grid_add(
        x_subdivisions=grid_x,
        y_subdivisions=grid_y,
        size=1.0,
        location=(0.0, 0.0, water_height),
    )
    water = bpy.context.active_object
    water.name = "BlueRoomWaterOverlay"

    # primitive_grid_add(size=1.0) creates a 1 m x 1 m grid. Its scale must
    # therefore equal the desired final dimensions, not half the dimensions.
    # The previous /2 scaling was the real reason the water covered only the
    # center portion of the room.
    water.scale = (
        room_width + WATER_EDGE_OVERSCAN * 2.0,
        room_depth + WATER_EDGE_OVERSCAN * 2.0,
        1.0,
    )
    bpy.context.view_layer.objects.active = water
    water.select_set(True)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    water.data.materials.clear()
    water.data.materials.append(
        create_water_material(
            "BlueRoomAnimatedWater",
            preview_mode=preview_mode,
            frame_end=frame_end,
        )
    )

    # Broad, gentle slosh across the pool. These waves stay subtle so the
    # motion feels like calm water in a room rather than stormy water.
    wave_x = water.modifiers.new("WaterSloshX", "WAVE")
    wave_x.use_x = True
    wave_x.use_y = False
    wave_x.height = WATER_SURFACE_PRIMARY_SLOSH
    wave_x.width = 2.3
    wave_x.narrowness = 0.95
    wave_x.speed = 0.34
    wave_x.start_position_x = -room_width * 0.62

    wave_y = water.modifiers.new("WaterSloshY", "WAVE")
    wave_y.use_x = False
    wave_y.use_y = True
    wave_y.height = WATER_SURFACE_SECONDARY_SLOSH
    wave_y.width = 1.9
    wave_y.narrowness = 0.82
    wave_y.speed = 0.27
    wave_y.start_position_y = room_depth * 0.46

    # Layer several very weak moving displacement fields on top of the broad
    # slosh to create realistic, gentle ripple interference.
    ripple_empty_a = add_motion_driver_empty("WaterRippleDriverA")
    ripple_empty_b = add_motion_driver_empty("WaterRippleDriverB")
    ripple_empty_c = add_motion_driver_empty("WaterRippleDriverC")

    quarter = max(frame_end // 4, 2)
    half = max(frame_end // 2, 3)
    three_quarter = max((frame_end * 3) // 4, 4)

    animate_empty_loop(
        ripple_empty_a,
        [
            (1, (-0.65, -0.24, 0.0)),
            (quarter, (-0.1, 0.42, 0.0)),
            (half, (0.56, 0.12, 0.0)),
            (three_quarter, (0.08, -0.48, 0.0)),
            (frame_end, (-0.65, -0.24, 0.0)),
        ],
    )
    animate_empty_loop(
        ripple_empty_b,
        [
            (1, (0.58, -0.44, 0.0)),
            (quarter, (0.16, -0.02, 0.0)),
            (half, (-0.42, 0.54, 0.0)),
            (three_quarter, (-0.18, 0.05, 0.0)),
            (frame_end, (0.58, -0.44, 0.0)),
        ],
    )
    animate_empty_loop(
        ripple_empty_c,
        [
            (1, (0.0, 0.58, 0.0)),
            (quarter, (0.42, 0.08, 0.0)),
            (half, (0.0, -0.55, 0.0)),
            (three_quarter, (-0.46, -0.12, 0.0)),
            (frame_end, (0.0, 0.58, 0.0)),
        ],
    )

    ripple_texture_a = bpy.data.textures.new("BlueWaterRippleA", "CLOUDS")
    ripple_texture_a.noise_scale = 0.16
    ripple_texture_a.noise_depth = 3
    ripple_texture_a.contrast = 1.05
    ripple_texture_a.intensity = 1.0

    ripple_displace_a = water.modifiers.new("WaterRippleA", "DISPLACE")
    ripple_displace_a.texture = ripple_texture_a
    ripple_displace_a.texture_coords = "OBJECT"
    ripple_displace_a.texture_coords_object = ripple_empty_a
    ripple_displace_a.strength = WATER_RIPPLE_A_STRENGTH
    ripple_displace_a.mid_level = 0.5

    ripple_texture_b = bpy.data.textures.new("BlueWaterRippleB", "MUSGRAVE")
    ripple_texture_b.noise_scale = 0.075
    ripple_texture_b.intensity = 0.82

    ripple_displace_b = water.modifiers.new("WaterRippleB", "DISPLACE")
    ripple_displace_b.texture = ripple_texture_b
    ripple_displace_b.texture_coords = "OBJECT"
    ripple_displace_b.texture_coords_object = ripple_empty_b
    ripple_displace_b.strength = WATER_RIPPLE_B_STRENGTH
    ripple_displace_b.mid_level = 0.5

    ripple_texture_c = bpy.data.textures.new("BlueWaterRippleC", "DISTORTED_NOISE")
    ripple_texture_c.noise_scale = 0.055
    ripple_texture_c.distortion = 0.8

    ripple_displace_c = water.modifiers.new("WaterRippleC", "DISPLACE")
    ripple_displace_c.texture = ripple_texture_c
    ripple_displace_c.texture_coords = "OBJECT"
    ripple_displace_c.texture_coords_object = ripple_empty_c
    ripple_displace_c.strength = WATER_RIPPLE_C_STRENGTH
    ripple_displace_c.mid_level = 0.5

    # Make the overall waterline visibly breathe and rock. This is deliberately
    # stronger than the previous pass, but still below rough/stormy motion.
    half = max(2, frame_end // 2)
    water.location.z = water_height
    water.rotation_euler = (0.0, 0.0, 0.0)
    water.keyframe_insert(data_path="location", frame=1)
    water.keyframe_insert(data_path="rotation_euler", frame=1)
    water.location.z = water_height + 0.018
    water.rotation_euler = (0.018, -0.014, 0.0)
    water.keyframe_insert(data_path="location", frame=half)
    water.keyframe_insert(data_path="rotation_euler", frame=half)
    water.location.z = water_height
    water.rotation_euler = (0.0, 0.0, 0.0)
    water.keyframe_insert(data_path="location", frame=frame_end)
    water.keyframe_insert(data_path="rotation_euler", frame=frame_end)

    solidify = water.modifiers.new("WaterBody", "SOLIDIFY")
    solidify.thickness = water_height
    solidify.offset = -1.0
    solidify.use_even_offset = True
    solidify.use_rim = True
    solidify.material_offset_rim = 0

    clip_box = add_water_clip_box(room_width, room_depth, water_height)
    boolean_clip = water.modifiers.new("WaterRoomClip", "BOOLEAN")
    boolean_clip.operation = "INTERSECT"
    boolean_clip.solver = "FLOAT" if preview_mode else "EXACT"
    boolean_clip.object = clip_box

    subdivision = water.modifiers.new("WaterSubdivision", "SUBSURF")
    subdivision.levels = 0 if preview_mode else 1
    subdivision.render_levels = 0 if preview_mode else 1

    bpy.ops.object.shade_smooth()
    return water


def configure_overlay_render(scene: bpy.types.Scene, settings, output_path: Path, preview_mode: bool = False):
    scene.render.engine = "CYCLES"
    scene.cycles.samples = settings.samples
    scene.cycles.device = "GPU" if settings.use_gpu else "CPU"
    scene.cycles.use_denoising = True
    try:
        scene.cycles.use_adaptive_sampling = True
    except Exception:
        pass

    if preview_mode:
        scene.cycles.max_bounces = 3
        scene.cycles.diffuse_bounces = 1
        scene.cycles.glossy_bounces = 1
        scene.cycles.transmission_bounces = 2
        scene.cycles.transparent_max_bounces = 2
        scene.cycles.volume_bounces = 0
        try:
            scene.render.use_persistent_data = True
        except Exception:
            pass

    scene.render.resolution_x = settings.width
    scene.render.resolution_y = settings.height
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    try:
        scene.render.image_settings.color_depth = "8"
    except Exception:
        pass
    scene.render.film_transparent = True
    scene.render.filepath = str(output_path)

    scene.frame_start = FRAME_START
    scene.frame_end = FRAME_END
    scene.render.fps = FRAME_RATE


def set_camera_visibility_excluding(target):
    previous = []
    for obj in bpy.context.scene.objects:
        if obj == target or obj.type == "CAMERA":
            continue

        cycles_visibility = getattr(obj, "cycles_visibility", None)
        if cycles_visibility is None:
            continue

        previous.append((obj, cycles_visibility.camera))
        cycles_visibility.camera = False

    return previous


def restore_camera_visibility(previous):
    for obj, visible_camera in previous:
        if obj.name in bpy.data.objects:
            obj.cycles_visibility.camera = visible_camera


def heal_overlay_seam(image_path: Path, columns: int = SEAM_FIX_COLUMNS):
    if columns <= 0:
        return

    image = bpy.data.images.load(str(image_path), check_existing=False)
    try:
        width = image.size[0]
        height = image.size[1]
        if width <= columns * 2:
            image.save()
            return

        pixels = list(image.pixels[:])

        def index(x: int, y: int) -> int:
            return (y * width + x) * 4

        # Force both wrapped edges to share identical pixels so the panorama
        # seam does not show up as a colored vertical line in the browser.
        for y in range(height):
            for offset in range(columns):
                source_x = columns + offset
                source_i = index(source_x, y)
                rgba = pixels[source_i : source_i + 4]

                left_i = index(offset, y)
                right_i = index(width - columns + offset, y)
                pixels[left_i : left_i + 4] = rgba
                pixels[right_i : right_i + 4] = rgba

        image.pixels[:] = pixels
        image.save()
    finally:
        bpy.data.images.remove(image)


def encode_webm_from_frames(frames_pattern: Path, output_file: Path):
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        print("ffmpeg not found; skipped WebM encoding. PNG frames were kept.")
        return False

    command = [
        ffmpeg,
        "-y",
        "-framerate",
        str(FRAME_RATE),
        "-i",
        str(frames_pattern),
        "-c:v",
        "libvpx-vp9",
        "-pix_fmt",
        "yuva420p",
        "-b:v",
        "0",
        "-crf",
        "32",
        "-row-mt",
        "1",
        "-deadline",
        "good",
        "-cpu-used",
        "4",
        str(output_file),
    ]
    print("Encoding transparent WebM...")
    result = subprocess.run(command, check=False)
    if result.returncode != 0:
        print("ffmpeg failed; PNG frames were kept.")
        return False
    return True


def render_animation_frames(scene: bpy.types.Scene, frames_directory: Path):
    frames_directory.mkdir(parents=True, exist_ok=True)
    scene.render.filepath = str(frames_directory / "water-frame_")
    print("Rendering clear-water overlay animation frames...")
    bpy.ops.render.render(animation=True)

    missing = [
        frame
        for frame in range(FRAME_START, FRAME_END + 1)
        if not (frames_directory / f"water-frame_{frame:04d}.png").exists()
    ]
    if missing:
        raise RuntimeError(f"Missing rendered frames: {missing[:5]}")

    for frame in range(FRAME_START, FRAME_END + 1):
        heal_overlay_seam(frames_directory / f"water-frame_{frame:04d}.png")


def cleanup_rendered_frames(frames_directory: Path):
    if KEEP_RENDERED_FRAMES:
        return
    shutil.rmtree(frames_directory, ignore_errors=True)


def main():
    rooms_root = script_directory().resolve().parent
    if str(rooms_root) not in sys.path:
        sys.path.insert(0, str(rooms_root))

    builder_file = rooms_root / "shared" / "room_builder.py"
    room_builder = load_live_room_builder(builder_file)

    quality_name = RENDER_QUALITY.strip().upper()
    if quality_name not in QUALITY_PRESETS:
        raise ValueError('RENDER_QUALITY must be "PREVIEW", "FAST", or "LIT".')

    preview_mode = is_preview_quality(quality_name)

    quality = QUALITY_PRESETS[quality_name]
    settings = room_builder.RenderSettings(
        width=quality["width"],
        height=quality["height"],
        samples=quality["samples"],
        use_gpu=USE_GPU,
        auto_render=AUTO_RENDER_BASE_PANORAMA,
    )

    definition = room_builder.RoomDefinition(
        "blue",
        "The Blue Room",
        "Room 004",
        "#3088D6",
    )

    print("=" * 72)
    print("Blue room clear-water overlay builder")
    print(f"Quality:              {quality_name}")
    print(f"Resolution:           {settings.width} x {settings.height}")
    print(f"Cycles samples:       {settings.samples}")
    print(f"Frame range:          {FRAME_START}..{FRAME_END}")
    print(f"Frame rate:           {FRAME_RATE} fps")
    print(f"Water fill ratio:     {WATER_FILL_RATIO:.2f}")
    print(f"Water overscan:       {WATER_EDGE_OVERSCAN:.3f} m")
    print(f"Wall overlap:         {WATER_WALL_OVERLAP:.3f} m")
    print(f"Base panorama render: {settings.auto_render}")
    print(f"Cycles device:        {'GPU' if settings.use_gpu else 'CPU'}")
    if preview_mode:
        print("Preview optimizations: overlay-only water shading, no room refraction, reduced bounces, simplified mesh")
    print("=" * 72)

    room_builder.build_room(definition, settings, rooms_root)

    output_directory = rooms_root / "blue"
    poster_file = output_directory / "blue-room-water-overlay.png"
    webm_file = output_directory / "blue-room-water-overlay.webm"
    frames_directory = output_directory / "water-overlay-frames"

    if poster_file.exists():
        poster_file.unlink()
    if webm_file.exists():
        webm_file.unlink()
    shutil.rmtree(frames_directory, ignore_errors=True)

    scene = bpy.context.scene
    water = add_water_object(room_builder, FRAME_END, preview_mode=preview_mode)
    configure_overlay_render(scene, settings, poster_file, preview_mode=preview_mode)

    previous_visibility = set_camera_visibility_excluding(water)
    try:
        render_animation_frames(scene, frames_directory)
    finally:
        restore_camera_visibility(previous_visibility)

    first_frame = frames_directory / f"water-frame_{FRAME_START:04d}.png"
    if not first_frame.exists():
        raise RuntimeError(f"Missing first frame: {first_frame}")
    shutil.copy2(first_frame, poster_file)
    heal_overlay_seam(poster_file)

    encoded = encode_webm_from_frames(
        frames_directory / "water-frame_%04d.png",
        webm_file,
    )
    if encoded:
        print(f"Encoded animated overlay: {webm_file}")
    else:
        print("Animated overlay video was not encoded.")

    cleanup_rendered_frames(frames_directory)
    print(f"Rendered static overlay poster: {poster_file}")


if __name__ == "__main__":
    main()
