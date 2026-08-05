"""Render a static transparent water overlay for the blue room only.

This script keeps the base blue-room panorama exactly as rendered by the shared
room builder and produces a second equirectangular PNG containing only the
water, with transparency everywhere else. The browser composites that overlay
on top of the existing panorama.
"""

from __future__ import annotations

from pathlib import Path
import importlib
import importlib.util
import sys

import bpy


# =============================================================================
# EASY SETTINGS
# =============================================================================
# False keeps the existing room panorama untouched and renders only the overlay.
# Turn this on only if you also want to rebuild the regular blue-room panorama
# and interactive GLB from the current sources.
AUTO_RENDER_BASE_PANORAMA = False

# "FAST", "LIT", "SLOW", or "CRISP"
RENDER_QUALITY = "FAST"

USE_GPU = True

QUALITY_PRESETS = {
    "FAST": {"width": 2048, "height": 1024, "samples": 32},
    "LIT": {"width": 6144, "height": 3072, "samples": 64},
    "SLOW": {"width": 4096, "height": 2048, "samples": 128},
    "CRISP": {"width": 6144, "height": 3072, "samples": 48},
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
    # Blender 5 materials already use nodes; assigning use_nodes there emits a
    # deprecation warning. Blender 4.x still needs the explicit opt-in.
    if bpy.app.version < (5, 0, 0):
        mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    bsdf = nodes.get("Principled BSDF")
    if bsdf is None:
        raise RuntimeError("Principled BSDF not available for water material.")

    set_socket(bsdf, "Base Color", (0.72, 0.9, 1.0, 1.0))
    set_socket(bsdf, "Roughness", 0.02)
    set_socket(bsdf, "IOR", 1.333)
    set_socket(bsdf, "Transmission Weight", 1.0)
    set_socket(bsdf, "Transmission", 1.0)
    set_socket(bsdf, "Specular IOR Level", 0.5)

    noise_a = nodes.new("ShaderNodeTexNoise")
    noise_a.inputs["Scale"].default_value = 18.0
    noise_a.inputs["Detail"].default_value = 8.0
    noise_a.inputs["Roughness"].default_value = 0.52

    noise_b = nodes.new("ShaderNodeTexNoise")
    noise_b.inputs["Scale"].default_value = 4.2
    noise_b.inputs["Detail"].default_value = 7.0
    noise_b.inputs["Roughness"].default_value = 0.4

    mix = nodes.new("ShaderNodeMixRGB")
    mix.blend_type = "ADD"
    mix.inputs["Fac"].default_value = 0.36

    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.015
    bump.inputs["Distance"].default_value = 1.0

    absorption = nodes.new("ShaderNodeVolumeAbsorption")
    absorption.inputs["Color"].default_value = (0.25, 0.62, 0.88, 1.0)
    absorption.inputs["Density"].default_value = 0.12

    material_output = nodes.get("Material Output")

    links.new(noise_a.outputs["Fac"], mix.inputs[1])
    links.new(noise_b.outputs["Fac"], mix.inputs[2])
    links.new(mix.outputs["Color"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    links.new(absorption.outputs["Volume"], material_output.inputs["Volume"])

    # Blend/shadow methods are Eevee viewport settings and are not required
    # for this Cycles-only transparent-film overlay. Blender 5 removed the
    # legacy Material.shadow_method API, so leaving both unset keeps this
    # script compatible across Blender 4.x and 5.x.
    return mat


def add_water_object(room_builder_module):
    room_width = room_builder_module.ROOM_WIDTH
    room_depth = room_builder_module.ROOM_DEPTH
    room_height = room_builder_module.ROOM_HEIGHT

    water_height = room_height * 0.5
    inset = 0.018

    bpy.ops.mesh.primitive_grid_add(
        x_subdivisions=200,
        y_subdivisions=280,
        size=1.0,
        location=(0.0, 0.0, water_height),
    )
    water = bpy.context.active_object
    water.name = "BlueRoomWaterOverlay"
    water.scale = ((room_width - inset) / 2.0, (room_depth - inset) / 2.0, 1.0)

    displace_primary = water.modifiers.new("WaterPrimaryWaves", "DISPLACE")
    texture_primary = bpy.data.textures.new("BlueWaterPrimary", "CLOUDS")
    texture_primary.noise_scale = 0.22
    texture_primary.noise_depth = 4
    texture_primary.contrast = 1.6
    displace_primary.texture = texture_primary
    displace_primary.strength = 0.05
    displace_primary.mid_level = 0.5

    displace_secondary = water.modifiers.new("WaterSecondaryRipples", "DISPLACE")
    texture_secondary = bpy.data.textures.new("BlueWaterSecondary", "MUSGRAVE")
    texture_secondary.noise_scale = 0.055
    texture_secondary.intensity = 0.72
    displace_secondary.texture = texture_secondary
    displace_secondary.strength = 0.012
    displace_secondary.mid_level = 0.5

    solidify = water.modifiers.new("WaterBody", "SOLIDIFY")
    solidify.thickness = water_height
    solidify.offset = -1.0
    solidify.use_even_offset = True
    solidify.use_rim = True
    solidify.material_offset_rim = 0

    subdivision = water.modifiers.new("WaterSubdivision", "SUBSURF")
    subdivision.levels = 1
    subdivision.render_levels = 2

    water.data.materials.append(create_water_material("BlueRoomStaticWater"))
    bpy.ops.object.shade_smooth()
    return water


def configure_overlay_render(scene: bpy.types.Scene, settings, output_file: Path):
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
    scene.render.filepath = str(output_file)


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


def main():
    rooms_root = script_directory().resolve().parent
    if str(rooms_root) not in sys.path:
        sys.path.insert(0, str(rooms_root))

    builder_file = rooms_root / "shared" / "room_builder.py"
    room_builder = load_live_room_builder(builder_file)

    quality_name = RENDER_QUALITY.strip().upper()
    if quality_name not in QUALITY_PRESETS:
        raise ValueError('RENDER_QUALITY must be "FAST", "LIT", "SLOW", or "CRISP".')

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
    print("Blue room static water overlay builder")
    print(f"Quality:              {quality_name}")
    print(f"Resolution:           {settings.width} x {settings.height}")
    print(f"Cycles samples:       {settings.samples}")
    print(f"Base panorama render: {settings.auto_render}")
    print(f"Cycles device:        {'GPU' if settings.use_gpu else 'CPU'}")
    print("=" * 72)

    room_builder.build_room(definition, settings, rooms_root)

    output_directory = rooms_root / "blue"
    overlay_file = output_directory / "blue-room-water-overlay.png"
    if overlay_file.exists():
        overlay_file.unlink()

    scene = bpy.context.scene
    water = add_water_object(room_builder)
    configure_overlay_render(scene, settings, overlay_file)

    previous_visibility = set_camera_visibility_excluding(water)
    try:
        bpy.ops.render.render(write_still=True)
    finally:
        restore_camera_visibility(previous_visibility)

    if not overlay_file.exists():
        raise RuntimeError(f"Static water overlay render did not create {overlay_file}")

    print(f"Rendered blue-room water overlay: {overlay_file}")


if __name__ == "__main__":
    main()
