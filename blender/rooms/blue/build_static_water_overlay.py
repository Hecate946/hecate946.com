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
RENDER_QUALITY = "FAST"

USE_GPU = True
FRAME_START = 1
FRAME_END = 24
FRAME_RATE = 12
KEEP_RENDERED_FRAMES = False

# Water tuning: lower fill, clearer water, calmer motion, and wall-to-wall coverage.
WATER_FILL_RATIO = 0.30
WATER_SURFACE_PRIMARY_SLOSH = 0.018
WATER_SURFACE_SECONDARY_SLOSH = 0.010
WATER_RIPPLE_A_STRENGTH = 0.0022
WATER_RIPPLE_B_STRENGTH = 0.0011
WATER_EDGE_OVERSCAN = 0.22
SEAM_FIX_COLUMNS = 6

QUALITY_PRESETS = {
    "PREVIEW": {"width": 1280, "height": 640, "samples": 16},
    "FAST": {"width": 2048, "height": 1024, "samples": 32},
    "LIT": {"width": 4096, "height": 2048, "samples": 64},
}


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


def create_water_material(name: str):
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

    # Clear, pool-like water: very transparent, only lightly tinted, and with
    # low absorption so the underlying floor remains visible.
    set_socket(bsdf, "Base Color", (0.975, 0.99, 1.0, 1.0))
    set_socket(bsdf, "Roughness", 0.0025)
    set_socket(bsdf, "IOR", 1.333)
    set_socket(bsdf, "Specular IOR Level", 0.5)
    set_socket(bsdf, "Transmission Weight", 1.0)
    set_socket(bsdf, "Transmission", 1.0)

    noise_a = nodes.new("ShaderNodeTexNoise")
    noise_a.inputs["Scale"].default_value = 11.0
    noise_a.inputs["Detail"].default_value = 6.5
    noise_a.inputs["Roughness"].default_value = 0.42

    noise_b = nodes.new("ShaderNodeTexNoise")
    noise_b.inputs["Scale"].default_value = 4.0
    noise_b.inputs["Detail"].default_value = 5.0
    noise_b.inputs["Roughness"].default_value = 0.36

    mix = nodes.new("ShaderNodeMixRGB")
    mix.blend_type = "ADD"
    mix.inputs["Fac"].default_value = 0.08

    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.002
    bump.inputs["Distance"].default_value = 1.0

    absorption = nodes.new("ShaderNodeVolumeAbsorption")
    absorption.inputs["Color"].default_value = (0.93, 0.98, 1.0, 1.0)
    absorption.inputs["Density"].default_value = 0.0014

    links.new(noise_a.outputs["Fac"], mix.inputs[1])
    links.new(noise_b.outputs["Fac"], mix.inputs[2])
    links.new(mix.outputs["Color"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    links.new(absorption.outputs["Volume"], material_output.inputs["Volume"])

    return mat


def add_motion_driver_empty(name: str, location=(0.0, 0.0, 0.0)):
    empty = bpy.data.objects.new(name, None)
    empty.empty_display_type = "PLAIN_AXES"
    empty.location = location
    bpy.context.scene.collection.objects.link(empty)
    return empty


def add_water_clip_box(room_width: float, room_depth: float, water_height: float):
    bpy.ops.mesh.primitive_cube_add(
        location=(0.0, 0.0, water_height / 2.0),
        scale=(room_width / 2.0, room_depth / 2.0, water_height / 2.0 + 0.02),
    )
    clip_box = bpy.context.active_object
    clip_box.name = "BlueRoomWaterClipBox"
    clip_box.display_type = "WIRE"
    clip_box.hide_render = True
    return clip_box


def add_water_object(room_builder_module, frame_end: int):
    room_width = room_builder_module.ROOM_WIDTH
    room_depth = room_builder_module.ROOM_DEPTH
    room_height = room_builder_module.ROOM_HEIGHT

    water_height = room_height * WATER_FILL_RATIO
    inset = -WATER_EDGE_OVERSCAN

    bpy.ops.mesh.primitive_grid_add(
        x_subdivisions=120,
        y_subdivisions=180,
        size=1.0,
        location=(0.0, 0.0, water_height),
    )
    water = bpy.context.active_object
    water.name = "BlueRoomWaterOverlay"
    water.scale = ((room_width - inset) / 2.0, (room_depth - inset) / 2.0, 1.0)

    water.data.materials.clear()
    water.data.materials.append(create_water_material("BlueRoomAnimatedWater"))

    # Large slow slosh travelling across the pool.
    wave_x = water.modifiers.new("WaterSloshX", "WAVE")
    wave_x.use_x = True
    wave_x.use_y = False
    wave_x.height = WATER_SURFACE_PRIMARY_SLOSH
    wave_x.width = 2.8
    wave_x.narrowness = 0.8
    wave_x.speed = 0.14
    wave_x.start_position_x = -room_width * 0.55

    wave_y = water.modifiers.new("WaterSloshY", "WAVE")
    wave_y.use_x = False
    wave_y.use_y = True
    wave_y.height = WATER_SURFACE_SECONDARY_SLOSH
    wave_y.width = 2.5
    wave_y.narrowness = 0.72
    wave_y.speed = 0.11
    wave_y.start_position_y = room_depth * 0.38

    # Finer surface motion on top of the large slosh.
    ripple_empty_a = add_motion_driver_empty("WaterRippleDriverA")
    ripple_empty_b = add_motion_driver_empty("WaterRippleDriverB")

    ripple_empty_a.location = (-0.2, -0.5, 0.0)
    ripple_empty_a.keyframe_insert(data_path="location", frame=1)
    ripple_empty_a.location = (0.5, 0.75, 0.0)
    ripple_empty_a.keyframe_insert(data_path="location", frame=frame_end)

    ripple_empty_b.location = (0.4, 0.25, 0.0)
    ripple_empty_b.keyframe_insert(data_path="location", frame=1)
    ripple_empty_b.location = (-0.55, -0.65, 0.0)
    ripple_empty_b.keyframe_insert(data_path="location", frame=frame_end)

    ripple_texture_a = bpy.data.textures.new("BlueWaterRippleA", "CLOUDS")
    ripple_texture_a.noise_scale = 0.18
    ripple_texture_a.noise_depth = 3
    ripple_texture_a.contrast = 1.25
    ripple_texture_a.intensity = 1.0

    ripple_displace_a = water.modifiers.new("WaterRippleA", "DISPLACE")
    ripple_displace_a.texture = ripple_texture_a
    ripple_displace_a.texture_coords = "OBJECT"
    ripple_displace_a.texture_coords_object = ripple_empty_a
    ripple_displace_a.strength = WATER_RIPPLE_A_STRENGTH
    ripple_displace_a.mid_level = 0.5

    ripple_texture_b = bpy.data.textures.new("BlueWaterRippleB", "MUSGRAVE")
    ripple_texture_b.noise_scale = 0.08
    ripple_texture_b.intensity = 0.9

    ripple_displace_b = water.modifiers.new("WaterRippleB", "DISPLACE")
    ripple_displace_b.texture = ripple_texture_b
    ripple_displace_b.texture_coords = "OBJECT"
    ripple_displace_b.texture_coords_object = ripple_empty_b
    ripple_displace_b.strength = WATER_RIPPLE_B_STRENGTH
    ripple_displace_b.mid_level = 0.5

    solidify = water.modifiers.new("WaterBody", "SOLIDIFY")
    solidify.thickness = water_height
    solidify.offset = -1.0
    solidify.use_even_offset = True
    solidify.use_rim = True
    solidify.material_offset_rim = 0

    clip_box = add_water_clip_box(room_width, room_depth, water_height)
    boolean_clip = water.modifiers.new("WaterRoomClip", "BOOLEAN")
    boolean_clip.operation = "INTERSECT"
    boolean_clip.solver = "EXACT"
    boolean_clip.object = clip_box

    subdivision = water.modifiers.new("WaterSubdivision", "SUBSURF")
    subdivision.levels = 1
    subdivision.render_levels = 1

    bpy.ops.object.shade_smooth()
    return water


def configure_overlay_render(scene: bpy.types.Scene, settings, output_path: Path):
    scene.render.engine = "CYCLES"
    scene.cycles.samples = settings.samples
    scene.cycles.device = "GPU" if settings.use_gpu else "CPU"
    scene.cycles.use_denoising = True
    try:
        scene.cycles.use_adaptive_sampling = True
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

        # Transparent areas should contain neutral RGB to avoid chroma bleed
        # during VP9 + alpha encoding.
        for y in range(height):
            for x in range(width):
                pixel_i = index(x, y)
                if pixels[pixel_i + 3] <= 0.0001:
                    pixels[pixel_i : pixel_i + 4] = [0.0, 0.0, 0.0, 0.0]

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
    print(f"Base panorama render: {settings.auto_render}")
    print(f"Cycles device:        {'GPU' if settings.use_gpu else 'CPU'}")
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
    water = add_water_object(room_builder, FRAME_END)
    configure_overlay_render(scene, settings, poster_file)

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
