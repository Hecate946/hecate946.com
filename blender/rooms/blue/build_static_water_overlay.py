"""Build a multi-pass realistic pool-water overlay system for the blue room.

Outputs inside blender/rooms/blue:

- blue-room-underwater-grade.png        static blue underwater grade
- blue-room-water-caustics.png          poster / fallback for caustics
- blue-room-water-caustics.webm         animated caustics overlay
- blue-room-water-surface.png           poster / fallback for surface glints
- blue-room-water-surface.webm          animated surface overlay

The website layers those overlays on top of the original sharp room panorama:

1) underwater grade (static blue submersion)
2) caustics overlay (animated light patterns)
3) surface overlay (animated ripples, Fresnel glints, waterline)

This keeps the base room crisp while making the water feel much more like a
pool rather than a milky full-frame video.
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
AUTO_RENDER_BASE_PANORAMA = False
RENDER_QUALITY = "PREVIEW"  # PREVIEW, FAST, LIT
USE_GPU = True
FRAME_START = 1
FRAME_END = 24
FRAME_RATE = 8
KEEP_RENDERED_FRAMES = False

WATER_FILL_RATIO = 0.30
WATER_SURFACE_PRIMARY_SLOSH = 0.024
WATER_SURFACE_SECONDARY_SLOSH = 0.016
WATER_RIPPLE_A_STRENGTH = 0.0065
WATER_RIPPLE_B_STRENGTH = 0.0035
WATER_RIPPLE_C_STRENGTH = 0.0022
WATER_EDGE_OVERSCAN = 0.22
WATER_WALL_OVERLAP = 0.18
SEAM_FIX_COLUMNS = 6

QUALITY_PRESETS = {
    # PREVIEW uses Eevee and a smaller render. It is intended for quickly
    # judging motion, color, and waterline behavior before a final Cycles pass.
    "PREVIEW": {"width": 1024, "height": 512, "samples": 8, "crf": 30, "engine": "EEVEE"},
    "FAST": {"width": 2048, "height": 1024, "samples": 24, "crf": 26, "engine": "CYCLES"},
    "LIT": {"width": 4096, "height": 2048, "samples": 96, "crf": 20, "engine": "CYCLES"},
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
    module_name = "hecate_room_builder_live_multi_pass_water"
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


def script_paths(base_dir: Path):
    return {
        "underwater_grade": base_dir / "blue-room-underwater-grade.png",
        "caustics_poster": base_dir / "blue-room-water-caustics.png",
        "caustics_video": base_dir / "blue-room-water-caustics.webm",
        "surface_poster": base_dir / "blue-room-water-surface.png",
        "surface_video": base_dir / "blue-room-water-surface.webm",
        "caustics_frames": base_dir / "water-caustics-frames",
        "surface_frames": base_dir / "water-surface-frames",
    }


# -----------------------------------------------------------------------------
# Materials
# -----------------------------------------------------------------------------

def create_surface_water_material(name: str, preview_mode: bool, frame_end: int):
    mat = bpy.data.materials.new(name)
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    bsdf = nodes.get("Principled BSDF")
    out = nodes.get("Material Output")
    if bsdf is None or out is None:
        raise RuntimeError("Material setup failed for water surface")

    set_socket(bsdf, "Roughness", 0.018 if preview_mode else 0.012)
    set_socket(bsdf, "IOR", 1.333)
    set_socket(bsdf, "Specular IOR Level", 0.42 if preview_mode else 0.52)
    set_socket(bsdf, "Transmission Weight", 0.0)
    set_socket(bsdf, "Transmission", 0.0)

    noise_a = nodes.new("ShaderNodeTexNoise")
    noise_a.noise_dimensions = "4D"
    noise_a.inputs["Scale"].default_value = 11.0
    noise_a.inputs["Detail"].default_value = 9.0
    noise_a.inputs["Roughness"].default_value = 0.42

    noise_b = nodes.new("ShaderNodeTexNoise")
    noise_b.noise_dimensions = "4D"
    noise_b.inputs["Scale"].default_value = 4.5
    noise_b.inputs["Detail"].default_value = 6.0
    noise_b.inputs["Roughness"].default_value = 0.34

    animate_socket_ping_pong(noise_a.inputs["W"], 0.0, 0.85, frame_end)
    animate_socket_ping_pong(noise_b.inputs["W"], 0.2, 1.1, frame_end)

    bump_mix = nodes.new("ShaderNodeMixRGB")
    bump_mix.blend_type = "ADD"
    bump_mix.inputs["Fac"].default_value = 0.18

    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.012 if preview_mode else 0.016

    # Pool-blue highlight tint rather than milky white.
    deep_blue = nodes.new("ShaderNodeRGB")
    deep_blue.outputs[0].default_value = (0.10, 0.46, 0.82, 1.0)
    light_aqua = nodes.new("ShaderNodeRGB")
    light_aqua.outputs[0].default_value = (0.60, 0.93, 1.0, 1.0)
    tint_mix = nodes.new("ShaderNodeMixRGB")
    tint_mix.inputs["Fac"].default_value = 0.34

    transparent = nodes.new("ShaderNodeBsdfTransparent")
    fresnel = nodes.new("ShaderNodeFresnel")
    fresnel.inputs["IOR"].default_value = 1.333
    vis_scale = nodes.new("ShaderNodeMath")
    vis_scale.operation = "MULTIPLY"
    vis_scale.inputs[1].default_value = 0.42 if preview_mode else 0.48
    vis_bias = nodes.new("ShaderNodeMath")
    vis_bias.operation = "ADD"
    vis_bias.inputs[1].default_value = 0.015 if preview_mode else 0.025
    clamp = nodes.new("ShaderNodeClamp")
    mix_shader = nodes.new("ShaderNodeMixShader")

    links.new(noise_a.outputs["Fac"], bump_mix.inputs[1])
    links.new(noise_b.outputs["Fac"], bump_mix.inputs[2])
    links.new(bump_mix.outputs["Color"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    links.new(deep_blue.outputs["Color"], tint_mix.inputs[1])
    links.new(light_aqua.outputs["Color"], tint_mix.inputs[2])
    links.new(tint_mix.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(fresnel.outputs["Fac"], vis_scale.inputs[0])
    links.new(vis_scale.outputs["Value"], vis_bias.inputs[0])
    links.new(vis_bias.outputs["Value"], clamp.inputs["Value"])
    links.new(clamp.outputs["Result"], mix_shader.inputs[0])
    links.new(transparent.outputs["BSDF"], mix_shader.inputs[1])
    links.new(bsdf.outputs["BSDF"], mix_shader.inputs[2])
    links.new(mix_shader.outputs["Shader"], out.inputs["Surface"])

    return mat


def create_underwater_grade_material(name: str, water_height: float, room_height: float):
    mat = bpy.data.materials.new(name)
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    for node in list(nodes):
        if node.name not in {"Material Output"}:
            nodes.remove(node)
    out = nodes.get("Material Output")
    transparent = nodes.new("ShaderNodeBsdfTransparent")
    emission = nodes.new("ShaderNodeEmission")
    emission.inputs["Strength"].default_value = 1.0
    texcoord = nodes.new("ShaderNodeTexCoord")
    separate = nodes.new("ShaderNodeSeparateXYZ")
    map_range = nodes.new("ShaderNodeMapRange")
    map_range.inputs[1].default_value = -room_height * 0.5
    map_range.inputs[2].default_value = water_height - room_height * 0.5
    map_range.inputs[3].default_value = 1.0
    map_range.inputs[4].default_value = 0.0
    vertical_ramp = nodes.new("ShaderNodeValToRGB")
    vertical_ramp.color_ramp.elements[0].position = 0.0
    vertical_ramp.color_ramp.elements[0].color = (0.05, 0.24, 0.55, 1.0)
    vertical_ramp.color_ramp.elements[1].position = 1.0
    vertical_ramp.color_ramp.elements[1].color = (0.20, 0.64, 0.95, 1.0)
    facing = nodes.new("ShaderNodeLayerWeight")
    facing.inputs["Blend"].default_value = 0.25
    alpha_scale = nodes.new("ShaderNodeMath")
    alpha_scale.operation = "MULTIPLY"
    alpha_scale.inputs[1].default_value = 0.30
    alpha_bias = nodes.new("ShaderNodeMath")
    alpha_bias.operation = "ADD"
    alpha_bias.inputs[1].default_value = 0.06
    clamp = nodes.new("ShaderNodeClamp")
    mix_shader = nodes.new("ShaderNodeMixShader")

    links.new(texcoord.outputs["Object"], separate.inputs["Vector"])
    links.new(separate.outputs["Z"], map_range.inputs["Value"])
    links.new(map_range.outputs["Result"], vertical_ramp.inputs["Fac"])
    links.new(vertical_ramp.outputs["Color"], emission.inputs["Color"])
    links.new(facing.outputs["Facing"], alpha_scale.inputs[0])
    links.new(alpha_scale.outputs["Value"], alpha_bias.inputs[0])
    links.new(alpha_bias.outputs["Value"], clamp.inputs["Value"])
    links.new(clamp.outputs["Result"], mix_shader.inputs[0])
    links.new(transparent.outputs["BSDF"], mix_shader.inputs[1])
    links.new(emission.outputs["Emission"], mix_shader.inputs[2])
    links.new(mix_shader.outputs["Shader"], out.inputs["Surface"])
    return mat


def create_caustics_material(name: str, preview_mode: bool, frame_end: int, water_height: float, room_height: float):
    mat = bpy.data.materials.new(name)
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    for node in list(nodes):
        if node.name not in {"Material Output"}:
            nodes.remove(node)
    out = nodes.get("Material Output")

    transparent = nodes.new("ShaderNodeBsdfTransparent")
    emission = nodes.new("ShaderNodeEmission")
    emission.inputs["Strength"].default_value = 1.0

    texcoord = nodes.new("ShaderNodeTexCoord")
    mapping = nodes.new("ShaderNodeMapping")
    noise = nodes.new("ShaderNodeTexNoise")
    noise.noise_dimensions = "4D"
    noise.inputs["Scale"].default_value = 19.0
    noise.inputs["Detail"].default_value = 2.4
    noise.inputs["Roughness"].default_value = 0.26
    animate_socket_ping_pong(noise.inputs["W"], 0.0, 1.1, frame_end)

    noise_b = nodes.new("ShaderNodeTexNoise")
    noise_b.noise_dimensions = "4D"
    noise_b.inputs["Scale"].default_value = 8.0
    noise_b.inputs["Detail"].default_value = 3.2
    noise_b.inputs["Roughness"].default_value = 0.20
    animate_socket_ping_pong(noise_b.inputs["W"], 0.4, 1.6, frame_end)

    mult = nodes.new("ShaderNodeMixRGB")
    mult.blend_type = "MULTIPLY"
    mult.inputs["Fac"].default_value = 1.0

    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.73
    ramp.color_ramp.elements[0].color = (0, 0, 0, 1)
    ramp.color_ramp.elements[1].position = 0.95
    ramp.color_ramp.elements[1].color = (0.85, 0.98, 1.0, 1.0)

    separate = nodes.new("ShaderNodeSeparateXYZ")
    z_map = nodes.new("ShaderNodeMapRange")
    z_map.inputs[1].default_value = -room_height * 0.5
    z_map.inputs[2].default_value = water_height - room_height * 0.5
    z_map.inputs[3].default_value = 1.0
    z_map.inputs[4].default_value = 0.0
    z_ramp = nodes.new("ShaderNodeValToRGB")
    z_ramp.color_ramp.elements[0].position = 0.0
    z_ramp.color_ramp.elements[0].color = (1, 1, 1, 1)
    z_ramp.color_ramp.elements[1].position = 1.0
    z_ramp.color_ramp.elements[1].color = (0.25, 0.25, 0.25, 1)

    alpha_mult = nodes.new("ShaderNodeMath")
    alpha_mult.operation = "MULTIPLY"
    alpha_mult.inputs[1].default_value = 0.26 if preview_mode else 0.32
    mix_shader = nodes.new("ShaderNodeMixShader")

    links.new(texcoord.outputs["Object"], mapping.inputs["Vector"])
    links.new(mapping.outputs["Vector"], noise.inputs["Vector"])
    links.new(mapping.outputs["Vector"], noise_b.inputs["Vector"])
    links.new(noise.outputs["Fac"], mult.inputs[1])
    links.new(noise_b.outputs["Fac"], mult.inputs[2])
    links.new(mult.outputs["Color"], ramp.inputs["Fac"])
    links.new(texcoord.outputs["Object"], separate.inputs["Vector"])
    links.new(separate.outputs["Z"], z_map.inputs["Value"])
    links.new(z_map.outputs["Result"], z_ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], emission.inputs["Color"])
    links.new(z_ramp.outputs["Color"], alpha_mult.inputs[0])
    links.new(alpha_mult.outputs["Value"], mix_shader.inputs[0])
    links.new(transparent.outputs["BSDF"], mix_shader.inputs[1])
    links.new(emission.outputs["Emission"], mix_shader.inputs[2])
    links.new(mix_shader.outputs["Shader"], out.inputs["Surface"])
    return mat


# -----------------------------------------------------------------------------
# Objects
# -----------------------------------------------------------------------------

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

    grid_x = 36 if preview_mode else 140
    grid_y = 54 if preview_mode else 220
    bpy.ops.mesh.primitive_grid_add(
        x_subdivisions=grid_x,
        y_subdivisions=grid_y,
        size=1.0,
        location=(0.0, 0.0, water_height),
    )
    water = bpy.context.active_object
    water.name = "BlueRoomWaterSurface"
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
        create_surface_water_material(
            "BlueRoomWaterSurfaceMat",
            preview_mode=preview_mode,
            frame_end=frame_end,
        )
    )

    wave_x = water.modifiers.new("WaterSloshX", "WAVE")
    wave_x.use_x = True
    wave_x.use_y = False
    wave_x.height = WATER_SURFACE_PRIMARY_SLOSH
    wave_x.width = 2.9
    wave_x.narrowness = 0.72
    wave_x.speed = 0.18
    wave_x.start_position_x = -room_width * 0.6

    wave_y = water.modifiers.new("WaterSloshY", "WAVE")
    wave_y.use_x = False
    wave_y.use_y = True
    wave_y.height = WATER_SURFACE_SECONDARY_SLOSH
    wave_y.width = 2.1
    wave_y.narrowness = 0.68
    wave_y.speed = 0.14
    wave_y.start_position_y = room_depth * 0.45

    ripple_empty_a = add_motion_driver_empty("WaterRippleDriverA")
    ripple_empty_b = add_motion_driver_empty("WaterRippleDriverB")
    ripple_empty_c = add_motion_driver_empty("WaterRippleDriverC")
    quarter = max(frame_end // 4, 2)
    half = max(frame_end // 2, 3)
    three_quarter = max((frame_end * 3) // 4, 4)

    animate_empty_loop(ripple_empty_a, [
        (1, (-0.62, -0.2, 0.0)),
        (quarter, (-0.12, 0.44, 0.0)),
        (half, (0.58, 0.10, 0.0)),
        (three_quarter, (0.12, -0.46, 0.0)),
        (frame_end, (-0.62, -0.2, 0.0)),
    ])
    animate_empty_loop(ripple_empty_b, [
        (1, (0.55, -0.42, 0.0)),
        (quarter, (0.20, -0.02, 0.0)),
        (half, (-0.46, 0.52, 0.0)),
        (three_quarter, (-0.16, 0.02, 0.0)),
        (frame_end, (0.55, -0.42, 0.0)),
    ])
    animate_empty_loop(ripple_empty_c, [
        (1, (0.0, 0.56, 0.0)),
        (quarter, (0.38, 0.12, 0.0)),
        (half, (0.0, -0.52, 0.0)),
        (three_quarter, (-0.42, -0.10, 0.0)),
        (frame_end, (0.0, 0.56, 0.0)),
    ])

    ripple_texture_a = bpy.data.textures.new("BlueWaterRippleA", "CLOUDS")
    ripple_texture_a.noise_scale = 0.14
    ripple_texture_a.noise_depth = 3
    ripple_texture_a.contrast = 1.08
    ripple_displace_a = water.modifiers.new("WaterRippleA", "DISPLACE")
    ripple_displace_a.texture = ripple_texture_a
    ripple_displace_a.texture_coords = "OBJECT"
    ripple_displace_a.texture_coords_object = ripple_empty_a
    ripple_displace_a.strength = WATER_RIPPLE_A_STRENGTH
    ripple_displace_a.mid_level = 0.5

    ripple_texture_b = bpy.data.textures.new("BlueWaterRippleB", "MUSGRAVE")
    ripple_texture_b.noise_scale = 0.070
    ripple_displace_b = water.modifiers.new("WaterRippleB", "DISPLACE")
    ripple_displace_b.texture = ripple_texture_b
    ripple_displace_b.texture_coords = "OBJECT"
    ripple_displace_b.texture_coords_object = ripple_empty_b
    ripple_displace_b.strength = WATER_RIPPLE_B_STRENGTH
    ripple_displace_b.mid_level = 0.5

    ripple_texture_c = bpy.data.textures.new("BlueWaterRippleC", "DISTORTED_NOISE")
    ripple_texture_c.noise_scale = 0.050
    ripple_texture_c.distortion = 0.8
    ripple_displace_c = water.modifiers.new("WaterRippleC", "DISPLACE")
    ripple_displace_c.texture = ripple_texture_c
    ripple_displace_c.texture_coords = "OBJECT"
    ripple_displace_c.texture_coords_object = ripple_empty_c
    ripple_displace_c.strength = WATER_RIPPLE_C_STRENGTH
    ripple_displace_c.mid_level = 0.5

    water.location.z = water_height
    water.rotation_euler = (0.0, 0.0, 0.0)
    water.keyframe_insert(data_path="location", frame=1)
    water.keyframe_insert(data_path="rotation_euler", frame=1)
    water.location.z = water_height + 0.012
    water.rotation_euler = (0.012, -0.009, 0.0)
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

    clip_box = add_water_clip_box(room_width, room_depth, water_height)
    boolean_clip = water.modifiers.new("WaterRoomClip", "BOOLEAN")
    boolean_clip.operation = "INTERSECT"
    boolean_clip.solver = "FLOAT" if preview_mode else "EXACT"
    boolean_clip.object = clip_box

    subdivision = water.modifiers.new("WaterSubdivision", "SUBSURF")
    subdivision.levels = 0 if preview_mode else 2
    subdivision.render_levels = 0 if preview_mode else 2

    bpy.ops.object.shade_smooth()
    return water


def add_underwater_grade_object(room_builder_module):
    room_width = room_builder_module.ROOM_WIDTH
    room_depth = room_builder_module.ROOM_DEPTH
    room_height = room_builder_module.ROOM_HEIGHT
    water_height = room_height * WATER_FILL_RATIO
    bpy.ops.mesh.primitive_cube_add(
        location=(0.0, 0.0, water_height / 2.0),
        scale=(room_width / 2.0 + WATER_WALL_OVERLAP, room_depth / 2.0 + WATER_WALL_OVERLAP, water_height / 2.0),
    )
    grade = bpy.context.active_object
    grade.name = "BlueRoomUnderwaterGrade"
    grade.data.materials.clear()
    grade.data.materials.append(create_underwater_grade_material("BlueRoomUnderwaterGradeMat", water_height, room_height))
    return grade


def add_caustics_shell(room_builder_module, frame_end: int, preview_mode: bool = False):
    room_width = room_builder_module.ROOM_WIDTH
    room_depth = room_builder_module.ROOM_DEPTH
    room_height = room_builder_module.ROOM_HEIGHT
    water_height = room_height * WATER_FILL_RATIO
    bpy.ops.mesh.primitive_cube_add(
        location=(0.0, 0.0, room_height / 2.0),
        scale=(room_width / 2.0 - 0.03, room_depth / 2.0 - 0.03, room_height / 2.0 - 0.03),
    )
    shell = bpy.context.active_object
    shell.name = "BlueRoomCausticsShell"
    shell.data.materials.clear()
    shell.data.materials.append(create_caustics_material("BlueRoomCausticsMat", preview_mode, frame_end, water_height, room_height))
    return shell


# -----------------------------------------------------------------------------
# Render helpers
# -----------------------------------------------------------------------------

def set_fast_preview_engine(scene: bpy.types.Scene) -> str:
    # Blender renamed Eevee across releases. Try both identifiers so this works
    # with Blender 3.x/4.x/5.x installations.
    for engine_name in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            scene.render.engine = engine_name
            return engine_name
        except (TypeError, ValueError):
            continue

    scene.render.engine = "CYCLES"
    return "CYCLES"


def configure_overlay_render(scene: bpy.types.Scene, settings: dict, output_path: Path, preview_mode: bool = False):
    requested_engine = settings.get("engine", "CYCLES")
    actual_engine = set_fast_preview_engine(scene) if requested_engine == "EEVEE" else "CYCLES"

    if actual_engine == "CYCLES":
        scene.render.engine = "CYCLES"
        scene.cycles.samples = settings["samples"]
        scene.cycles.device = "GPU" if USE_GPU else "CPU"
        scene.cycles.use_denoising = True
        try:
            scene.cycles.use_adaptive_sampling = True
        except Exception:
            pass

        if preview_mode:
            scene.cycles.max_bounces = 2
            scene.cycles.diffuse_bounces = 0
            scene.cycles.glossy_bounces = 1
            scene.cycles.transmission_bounces = 0
            scene.cycles.transparent_max_bounces = 2
            scene.cycles.volume_bounces = 0
    else:
        # Eevee is dramatically faster for these transparent/emission overlay
        # passes and is sufficient for evaluating the animation design.
        eevee = getattr(scene, "eevee", None)
        if eevee is not None:
            if hasattr(eevee, "taa_render_samples"):
                eevee.taa_render_samples = settings["samples"]
            if hasattr(eevee, "use_gtao"):
                eevee.use_gtao = False
            if hasattr(eevee, "use_soft_shadows"):
                eevee.use_soft_shadows = False

    try:
        scene.render.use_persistent_data = True
    except Exception:
        pass

    scene.render.resolution_x = settings["width"]
    scene.render.resolution_y = settings["height"]
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


def set_render_isolation(targets):
    target_names = {target.name for target in targets}
    previous = []
    for obj in bpy.context.scene.objects:
        previous.append((obj, obj.hide_render))
        if obj.type in {"CAMERA", "LIGHT"}:
            obj.hide_render = False
        else:
            obj.hide_render = obj.name not in target_names
    return previous


def restore_render_isolation(previous):
    for obj, hidden in previous:
        if obj.name in bpy.data.objects:
            obj.hide_render = hidden


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

        for y in range(height):
            for offset in range(columns):
                source_x = columns + offset
                src_i = index(source_x, y)
                rgba = pixels[src_i:src_i + 4]
                left_i = index(offset, y)
                right_i = index(width - columns + offset, y)
                pixels[left_i:left_i + 4] = rgba
                pixels[right_i:right_i + 4] = rgba

        for y in range(height):
            for x in range(width):
                i = index(x, y)
                if pixels[i + 3] <= 0.0001:
                    pixels[i:i + 4] = [0.0, 0.0, 0.0, 0.0]

        image.pixels[:] = pixels
        image.save()
    finally:
        bpy.data.images.remove(image)


def encode_webm_from_frames(frames_pattern: Path, output_file: Path, crf: int):
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise RuntimeError("ffmpeg is required but was not found on PATH.")

    cmd = [
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
        "-auto-alt-ref",
        "0",
        "-b:v",
        "0",
        "-crf",
        str(crf),
        str(output_file),
    ]
    subprocess.run(cmd, check=True)


def render_animation_pass(targets, frames_directory: Path, poster_file: Path, video_file: Path, settings: dict, preview_mode: bool):
    frames_directory.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    previous = set_render_isolation(targets)
    try:
        configure_overlay_render(scene, settings, frames_directory / "frame_", preview_mode=preview_mode)
        scene.render.filepath = str(frames_directory / "frame_")
        bpy.ops.render.render(animation=True)
    finally:
        restore_render_isolation(previous)

    for frame in range(FRAME_START, FRAME_END + 1):
        heal_overlay_seam(frames_directory / f"frame_{frame:04d}.png")

    first_frame = frames_directory / f"frame_{FRAME_START:04d}.png"
    shutil.copy2(first_frame, poster_file)
    heal_overlay_seam(poster_file)
    encode_webm_from_frames(frames_directory / "frame_%04d.png", video_file, settings["crf"])

    if not KEEP_RENDERED_FRAMES:
        shutil.rmtree(frames_directory, ignore_errors=True)


def render_still_pass(targets, output_file: Path, settings: dict, preview_mode: bool):
    scene = bpy.context.scene
    previous = set_render_isolation(targets)
    try:
        configure_overlay_render(scene, settings, output_file, preview_mode=preview_mode)
        scene.frame_set(FRAME_START)
        bpy.ops.render.render(write_still=True)
    finally:
        restore_render_isolation(previous)
    heal_overlay_seam(output_file)


def cleanup_previous_outputs(paths: dict[str, Path]):
    for path in paths.values():
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
        else:
            path.unlink(missing_ok=True)


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

def main() -> None:
    base_dir = script_directory()
    paths = script_paths(base_dir)
    builder_file = base_dir.parent / "shared" / "room_builder.py"
    room_builder = load_live_room_builder(builder_file)

    quality_name = RENDER_QUALITY.strip().upper()
    if quality_name not in QUALITY_PRESETS:
        raise ValueError(f"RENDER_QUALITY must be one of: {', '.join(QUALITY_PRESETS)}")
    settings = QUALITY_PRESETS[quality_name]
    preview_mode = is_preview_quality(quality_name)

    print("\n=== Blue room realistic multi-pass pool water ===")
    print(f"Quality:              {quality_name}")
    print(f"Resolution:           {settings['width']}x{settings['height']}")
    print(f"Engine:               {settings.get('engine', 'CYCLES')}")
    print(f"Samples:              {settings['samples']}")
    print(f"Frames:               {FRAME_START}-{FRAME_END} @ {FRAME_RATE} fps")
    print(f"Water fill ratio:     {WATER_FILL_RATIO:.2f}")
    print(f"Base panorama render: {AUTO_RENDER_BASE_PANORAMA}")
    print(f"Cycles device:        {'GPU' if USE_GPU else 'CPU'}")

    cleanup_previous_outputs(paths)

    definition = room_builder.RoomDefinition(
        "blue",
        "The Blue Room",
        "Room 004",
        "#3088D6",
    )
    render_settings = room_builder.RenderSettings(
        width=settings["width"],
        height=settings["height"],
        samples=max(settings["samples"], 64) if AUTO_RENDER_BASE_PANORAMA else settings["samples"],
        use_gpu=USE_GPU,
        auto_render=AUTO_RENDER_BASE_PANORAMA,
    )
    room_builder.build_room(definition, render_settings, base_dir.parent)

    water = add_water_object(room_builder, FRAME_END, preview_mode=preview_mode)
    underwater_grade = add_underwater_grade_object(room_builder)
    caustics = add_caustics_shell(room_builder, FRAME_END, preview_mode=preview_mode)

    render_still_pass([underwater_grade], paths["underwater_grade"], settings, preview_mode)
    render_animation_pass([caustics], paths["caustics_frames"], paths["caustics_poster"], paths["caustics_video"], settings, preview_mode)
    render_animation_pass([water], paths["surface_frames"], paths["surface_poster"], paths["surface_video"], settings, preview_mode)

    print("\nGenerated overlays:")
    print(f"- {paths['underwater_grade'].name}")
    print(f"- {paths['caustics_poster'].name}")
    print(f"- {paths['caustics_video'].name}")
    print(f"- {paths['surface_poster'].name}")
    print(f"- {paths['surface_video'].name}")
    print("\nRun your asset sync script next.")


if __name__ == "__main__":
    main()
