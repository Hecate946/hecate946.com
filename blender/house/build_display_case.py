"""
Modular museum-vitrine generator for the hecate946.com homepage.

This script deliberately keeps the display case separate from the house. It
creates one Blender file and three transparent PNG passes that share the exact
camera and 1800 x 1200 framing used by blender/house/house.py:

    blender/house/display-case.blend
    blender/house/display-case-glass.png
    blender/house/display-case-base.png
    blender/house/display-case-preview.png

The website uses the base pass behind the interactive house and the glass pass
above it. The preview pass contains both case layers and is only for inspection.

Run from the project root:

    blender --background --python blender/house/build_display_case.py

Blender 3.6 and Blender 4.x are supported.
"""

from __future__ import annotations

import math
import os
from collections.abc import Iterable, Sequence

import bpy
from mathutils import Vector


# -----------------------------------------------------------------------------
# OUTPUT AND CAMERA — intentionally matched to blender/house/house.py
# -----------------------------------------------------------------------------

OUTPUT_DIR = os.path.expanduser("~/Desktop/projects/hecate946.com/blender/house")
BLEND_NAME = "display-case.blend"
GLASS_RENDER_NAME = "display-case-glass.png"
BASE_RENDER_NAME = "display-case-base.png"
PREVIEW_RENDER_NAME = "display-case-preview.png"

RENDER_WIDTH = 1800
RENDER_HEIGHT = 1200
RENDER_PERCENTAGE = 100

CAMERA_LOCATION = (0.0, -23.2, 5.22)
CAMERA_TARGET = (0.0, 0.0, 3.55)
CAMERA_ORTHO_SCALE = 16.65


# -----------------------------------------------------------------------------
# CASE PROPORTIONS
# -----------------------------------------------------------------------------

# The current house is about 14 units wide and 8 units tall. These dimensions
# leave a quiet margin without making the vitrine look like a literal jar.
CASE_WIDTH = 15.95
CASE_DEPTH = 4.85
CASE_HEIGHT = 9.95
CASE_BOTTOM_Z = -0.26
CASE_TOP_Z = CASE_BOTTOM_Z + CASE_HEIGHT
CASE_FRONT_Y = -3.15
CASE_BACK_Y = CASE_FRONT_Y + CASE_DEPTH
CASE_CENTER_Y = (CASE_FRONT_Y + CASE_BACK_Y) / 2.0
CASE_CENTER_Z = CASE_BOTTOM_Z + CASE_HEIGHT / 2.0

TOP_CORNER_RADIUS = 1.04
BOTTOM_CORNER_RADIUS = 0.34

# The base is intentionally shallow and quiet. The house then sits inside a
# small landscaped world rather than on a glossy turntable.
BASE_RADIUS_X = 7.10
BASE_RADIUS_Y = 2.16
BASE_TOP_Z = -0.25
BASE_THICKNESS = 0.075

GROUND_RADIUS_X = 5.95
GROUND_RADIUS_Y = 1.56
GROUND_TOP_Z = -0.105
GROUND_THICKNESS = 0.12
GROUND_CENTER_Y = 0.20

PATH_TOP_Z = GROUND_TOP_Z + 0.022
PATH_SEGMENT_DEPTH = 0.33
PATH_SEGMENT_HEIGHT = 0.038


# -----------------------------------------------------------------------------
# GENERAL HELPERS
# -----------------------------------------------------------------------------


def clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)

    for datablocks in (
        bpy.data.meshes,
        bpy.data.curves,
        bpy.data.materials,
        bpy.data.cameras,
        bpy.data.lights,
    ):
        for block in list(datablocks):
            if block.users == 0:
                datablocks.remove(block)


def create_collection(name: str) -> bpy.types.Collection:
    collection = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(collection)
    return collection


def move_to_collection(obj: bpy.types.Object, collection: bpy.types.Collection) -> None:
    for old_collection in list(obj.users_collection):
        old_collection.objects.unlink(obj)
    collection.objects.link(obj)


def look_at(obj: bpy.types.Object, target: Sequence[float]) -> None:
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def set_input(node: bpy.types.Node, names: Iterable[str], value) -> bool:
    for name in names:
        socket = node.inputs.get(name)
        if socket is not None:
            socket.default_value = value
            return True
    return False


def configure_transparent_material(material: bpy.types.Material) -> None:
    """Use the closest available transparent-surface settings in each version."""
    material.diffuse_color = (*material.diffuse_color[:3], material.diffuse_color[3])

    try:
        material.surface_render_method = "DITHERED"
    except Exception:
        try:
            material.blend_method = "HASHED"
        except Exception:
            pass

    try:
        material.use_transparency_overlap = False
    except Exception:
        pass

    try:
        material.use_screen_refraction = True
    except Exception:
        pass

    try:
        material.show_transparent_back = False
    except Exception:
        pass


def make_principled_material(
    name: str,
    color: tuple[float, float, float, float],
    *,
    roughness: float,
    metallic: float = 0.0,
    transmission: float = 0.0,
    ior: float = 1.45,
    coat: float = 0.0,
    coat_roughness: float = 0.1,
    emission_strength: float = 0.0,
) -> bpy.types.Material:
    material = bpy.data.materials.new(name=name)
    material.use_nodes = True
    material.diffuse_color = color

    bsdf = material.node_tree.nodes.get("Principled BSDF")
    if bsdf is None:
        raise RuntimeError(f"Principled BSDF was not created for {name}")

    set_input(bsdf, ("Base Color",), color)
    set_input(bsdf, ("Roughness",), roughness)
    set_input(bsdf, ("Metallic",), metallic)
    set_input(bsdf, ("IOR",), ior)
    set_input(bsdf, ("Alpha",), color[3])
    set_input(bsdf, ("Transmission Weight", "Transmission"), transmission)
    set_input(bsdf, ("Coat Weight", "Clearcoat"), coat)
    set_input(bsdf, ("Coat Roughness", "Clearcoat Roughness"), coat_roughness)

    if emission_strength > 0.0:
        set_input(bsdf, ("Emission Color", "Emission"), color)
        set_input(bsdf, ("Emission Strength",), emission_strength)

    if color[3] < 1.0 or transmission > 0.0:
        configure_transparent_material(material)

    return material


def add_beveled_cube(
    name: str,
    location: Sequence[float],
    dimensions: Sequence[float],
    material: bpy.types.Material,
    collection: bpy.types.Collection,
    *,
    bevel: float,
    bevel_segments: int,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cube_add(location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    bevel_modifier = obj.modifiers.new(name="Soft museum-case corners", type="BEVEL")
    bevel_modifier.width = bevel
    bevel_modifier.segments = bevel_segments
    bevel_modifier.limit_method = "ANGLE"
    try:
        bevel_modifier.affect = "EDGES"
    except Exception:
        pass

    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=bevel_modifier.name)
    obj.data.materials.append(material)
    move_to_collection(obj, collection)
    return obj


def add_ellipse_cylinder(
    name: str,
    *,
    location: Sequence[float],
    radius_x: float,
    radius_y: float,
    depth: float,
    material: bpy.types.Material,
    collection: bpy.types.Collection,
    bevel: float = 0.0,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=160,
        radius=1.0,
        depth=depth,
        location=location,
    )
    obj = bpy.context.object
    obj.name = name
    obj.scale = (radius_x, radius_y, 1.0)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    if bevel > 0.0:
        bevel_modifier = obj.modifiers.new(name="Soft elliptical edge", type="BEVEL")
        bevel_modifier.width = bevel
        bevel_modifier.segments = 5
        bevel_modifier.limit_method = "ANGLE"
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.modifier_apply(modifier=bevel_modifier.name)

    obj.data.materials.append(material)
    move_to_collection(obj, collection)
    return obj


def add_ellipse_torus(
    name: str,
    *,
    location: Sequence[float],
    radius_x: float,
    radius_y: float,
    tube_radius: float,
    material: bpy.types.Material,
    collection: bpy.types.Collection,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_torus_add(
        major_radius=1.0,
        minor_radius=tube_radius,
        major_segments=192,
        minor_segments=12,
        location=location,
    )
    obj = bpy.context.object
    obj.name = name
    obj.scale = (radius_x, radius_y, 1.0)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(material)
    move_to_collection(obj, collection)
    return obj


def add_curve(
    name: str,
    points: Sequence[Sequence[float]],
    *,
    material: bpy.types.Material,
    collection: bpy.types.Collection,
    bevel_depth: float,
    cyclic: bool = False,
    bevel_resolution: int = 4,
) -> bpy.types.Object:
    curve_data = bpy.data.curves.new(name=f"{name} curve", type="CURVE")
    curve_data.dimensions = "3D"
    curve_data.resolution_u = 2
    curve_data.bevel_depth = bevel_depth
    curve_data.bevel_resolution = bevel_resolution
    curve_data.resolution_u = 2

    spline = curve_data.splines.new(type="POLY")
    spline.points.add(len(points) - 1)
    for point, coordinate in zip(spline.points, points):
        point.co = (*coordinate, 1.0)
    spline.use_cyclic_u = cyclic

    obj = bpy.data.objects.new(name, curve_data)
    collection.objects.link(obj)
    obj.data.materials.append(material)
    return obj


def rounded_front_outline_points(
    *,
    width: float,
    bottom_z: float,
    top_z: float,
    y: float,
    top_radius: float,
    bottom_radius: float,
    arc_segments: int = 18,
) -> list[tuple[float, float, float]]:
    half_width = width / 2.0
    points: list[tuple[float, float, float]] = []

    # Bottom edge, then clockwise around the enclosure.
    points.append((-half_width + bottom_radius, y, bottom_z))
    points.append((half_width - bottom_radius, y, bottom_z))

    for index in range(arc_segments + 1):
        angle = math.radians(-90.0 + 90.0 * index / arc_segments)
        points.append(
            (
                half_width - bottom_radius + bottom_radius * math.cos(angle),
                y,
                bottom_z + bottom_radius + bottom_radius * math.sin(angle),
            )
        )

    points.append((half_width, y, top_z - top_radius))
    for index in range(arc_segments + 1):
        angle = math.radians(90.0 * index / arc_segments)
        points.append(
            (
                half_width - top_radius + top_radius * math.cos(angle),
                y,
                top_z - top_radius + top_radius * math.sin(angle),
            )
        )

    points.append((-half_width + top_radius, y, top_z))
    for index in range(arc_segments + 1):
        angle = math.radians(90.0 + 90.0 * index / arc_segments)
        points.append(
            (
                -half_width + top_radius + top_radius * math.cos(angle),
                y,
                top_z - top_radius + top_radius * math.sin(angle),
            )
        )

    points.append((-half_width, y, bottom_z + bottom_radius))
    for index in range(arc_segments + 1):
        angle = math.radians(180.0 + 90.0 * index / arc_segments)
        points.append(
            (
                -half_width + bottom_radius + bottom_radius * math.cos(angle),
                y,
                bottom_z + bottom_radius + bottom_radius * math.sin(angle),
            )
        )

    return points


def add_area_light(
    name: str,
    *,
    location: Sequence[float],
    target: Sequence[float],
    energy: float,
    size: float,
    color: tuple[float, float, float],
    collection: bpy.types.Collection,
    shape: str = "RECTANGLE",
    size_y: float | None = None,
) -> bpy.types.Object:
    light_data = bpy.data.lights.new(name=name, type="AREA")
    light_data.energy = energy
    light_data.color = color
    light_data.shape = shape
    light_data.size = size
    if size_y is not None and hasattr(light_data, "size_y"):
        light_data.size_y = size_y

    light = bpy.data.objects.new(name, light_data)
    collection.objects.link(light)
    light.location = location
    look_at(light, target)
    return light


# -----------------------------------------------------------------------------
# CASE ASSEMBLY
# -----------------------------------------------------------------------------


def build_glass(
    glass_collection: bpy.types.Collection,
    shell_material: bpy.types.Material,
    edge_material: bpy.types.Material,
    reflection_material: bpy.types.Material,
) -> None:
    # A nearly invisible rounded solid supplies real 3D refraction/specularity.
    # The stylized edge and reflection objects guarantee that the silhouette
    # still reads after rendering onto a transparent background.
    add_beveled_cube(
        "Museum vitrine glass volume",
        (0.0, CASE_CENTER_Y, CASE_CENTER_Z),
        (CASE_WIDTH, CASE_DEPTH, CASE_HEIGHT),
        shell_material,
        glass_collection,
        bevel=0.58,
        bevel_segments=12,
    )

    front_outline = rounded_front_outline_points(
        width=CASE_WIDTH,
        bottom_z=CASE_BOTTOM_Z,
        top_z=CASE_TOP_Z,
        y=CASE_FRONT_Y - 0.030,
        top_radius=TOP_CORNER_RADIUS,
        bottom_radius=BOTTOM_CORNER_RADIUS,
    )
    add_curve(
        "Front glass perimeter highlight",
        front_outline,
        material=edge_material,
        collection=glass_collection,
        bevel_depth=0.012,
        cyclic=True,
        bevel_resolution=4,
    )

    inset_outline = rounded_front_outline_points(
        width=CASE_WIDTH - 0.14,
        bottom_z=CASE_BOTTOM_Z + 0.045,
        top_z=CASE_TOP_Z - 0.05,
        y=CASE_FRONT_Y - 0.045,
        top_radius=TOP_CORNER_RADIUS - 0.05,
        bottom_radius=BOTTOM_CORNER_RADIUS - 0.03,
    )
    add_curve(
        "Inset glass thickness highlight",
        inset_outline,
        material=reflection_material,
        collection=glass_collection,
        bevel_depth=0.006,
        cyclic=True,
        bevel_resolution=4,
    )

    top_reflection: list[tuple[float, float, float]] = []
    reflection_half_width = CASE_WIDTH * 0.33
    for index in range(49):
        ratio = index / 48.0
        x = -reflection_half_width + ratio * reflection_half_width * 2.0
        normalized_x = x / reflection_half_width
        z = CASE_TOP_Z - 0.43 - 0.10 * (1.0 - normalized_x * normalized_x)
        top_reflection.append((x, CASE_FRONT_Y - 0.064, z))
    add_curve(
        "Upper bowed glass reflection",
        top_reflection,
        material=reflection_material,
        collection=glass_collection,
        bevel_depth=0.007,
        bevel_resolution=4,
    )

    left_streak = [
        (-CASE_WIDTH * 0.442, CASE_FRONT_Y - 0.060, CASE_BOTTOM_Z + 2.2),
        (-CASE_WIDTH * 0.448, CASE_FRONT_Y - 0.064, CASE_TOP_Z - 1.6),
    ]
    right_streak = [
        (CASE_WIDTH * 0.444, CASE_FRONT_Y - 0.060, CASE_BOTTOM_Z + 2.35),
        (CASE_WIDTH * 0.450, CASE_FRONT_Y - 0.065, CASE_TOP_Z - 1.75),
    ]
    add_curve(
        "Left vertical glass reflection",
        left_streak,
        material=reflection_material,
        collection=glass_collection,
        bevel_depth=0.008,
        bevel_resolution=4,
    )
    add_curve(
        "Right vertical glass reflection",
        right_streak,
        material=reflection_material,
        collection=glass_collection,
        bevel_depth=0.007,
        bevel_resolution=4,
    )

    lower_seam: list[tuple[float, float, float]] = []
    seam_half_width = CASE_WIDTH * 0.34
    for index in range(41):
        ratio = index / 40.0
        x = -seam_half_width + ratio * seam_half_width * 2.0
        normalized_x = x / seam_half_width
        z = CASE_BOTTOM_Z + 0.040 + 0.020 * (1.0 - normalized_x * normalized_x)
        lower_seam.append((x, CASE_FRONT_Y - 0.068, z))
    add_curve(
        "Lower glass seating seam",
        lower_seam,
        material=reflection_material,
        collection=glass_collection,
        bevel_depth=0.005,
        bevel_resolution=4,
    )


def build_base(
    base_collection: bpy.types.Collection,
    pedestal_material: bpy.types.Material,
    pedestal_edge_material: bpy.types.Material,
    ground_material: bpy.types.Material,
    grass_edge_material: bpy.types.Material,
    path_material: bpy.types.Material,
    shadow_material: bpy.types.Material,
) -> None:
    add_ellipse_cylinder(
        "Quiet stone pedestal",
        location=(0.0, -0.05, BASE_TOP_Z - BASE_THICKNESS / 2.0),
        radius_x=BASE_RADIUS_X,
        radius_y=BASE_RADIUS_Y,
        depth=BASE_THICKNESS,
        material=pedestal_material,
        collection=base_collection,
        bevel=0.032,
    )

    add_ellipse_torus(
        "Pedestal upper rim",
        location=(0.0, -0.05, BASE_TOP_Z + 0.002),
        radius_x=BASE_RADIUS_X * 0.986,
        radius_y=BASE_RADIUS_Y * 0.986,
        tube_radius=0.008,
        material=pedestal_edge_material,
        collection=base_collection,
    )

    add_ellipse_cylinder(
        "Grass island",
        location=(0.0, GROUND_CENTER_Y, GROUND_TOP_Z - GROUND_THICKNESS / 2.0),
        radius_x=GROUND_RADIUS_X,
        radius_y=GROUND_RADIUS_Y,
        depth=GROUND_THICKNESS,
        material=ground_material,
        collection=base_collection,
        bevel=0.05,
    )

    add_ellipse_torus(
        "Grass edge highlight",
        location=(0.0, GROUND_CENTER_Y, GROUND_TOP_Z + 0.003),
        radius_x=GROUND_RADIUS_X * 0.986,
        radius_y=GROUND_RADIUS_Y * 0.986,
        tube_radius=0.010,
        material=grass_edge_material,
        collection=base_collection,
    )

    path_segments = [
        (0.78, 0.56),
        (0.34, 0.74),
        (-0.12, 0.96),
        (-0.62, 1.22),
    ]
    for index, (center_y, width) in enumerate(path_segments, start=1):
        add_beveled_cube(
            f"Golden pathway stone {index}",
            (0.0, center_y, PATH_TOP_Z + PATH_SEGMENT_HEIGHT / 2.0),
            (width, PATH_SEGMENT_DEPTH, PATH_SEGMENT_HEIGHT),
            path_material,
            base_collection,
            bevel=0.030,
            bevel_segments=6,
        )

    add_ellipse_cylinder(
        "Soft contact shadow",
        location=(0.0, -0.03, BASE_TOP_Z - 0.060),
        radius_x=BASE_RADIUS_X * 0.82,
        radius_y=BASE_RADIUS_Y * 0.76,
        depth=0.014,
        material=shadow_material,
        collection=base_collection,
        bevel=0.032,
    )


def setup_camera() -> bpy.types.Object:
    camera_data = bpy.data.cameras.new("Display case website camera")
    camera = bpy.data.objects.new("Display case website camera", camera_data)
    bpy.context.scene.collection.objects.link(camera)
    camera.location = CAMERA_LOCATION
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = CAMERA_ORTHO_SCALE
    look_at(camera, CAMERA_TARGET)
    bpy.context.scene.camera = camera
    return camera


def setup_lighting(lighting_collection: bpy.types.Collection) -> None:
    # Narrow side lights draw the vertical edge arcs. The large top/front lights
    # provide subtle broad reflections rather than illuminating a room.
    add_area_light(
        "Left glass strip",
        location=(-8.8, -8.0, 5.3),
        target=(-7.4, CASE_FRONT_Y, 5.1),
        energy=300.0,
        size=7.0,
        size_y=0.42,
        color=(0.70, 0.84, 0.94),
        collection=lighting_collection,
    )
    add_area_light(
        "Right glass strip",
        location=(8.9, -7.2, 5.8),
        target=(7.45, CASE_FRONT_Y, 5.0),
        energy=245.0,
        size=6.5,
        size_y=0.32,
        color=(0.78, 0.88, 0.96),
        collection=lighting_collection,
    )
    add_area_light(
        "Top glass ribbon",
        location=(0.0, -4.0, 12.7),
        target=(0.0, CASE_FRONT_Y, CASE_TOP_Z - 0.4),
        energy=350.0,
        size=13.0,
        size_y=1.0,
        color=(0.82, 0.91, 1.0),
        collection=lighting_collection,
    )
    add_area_light(
        "Soft frontal reflection",
        location=(-2.2, -10.5, 7.2),
        target=(-1.0, CASE_FRONT_Y, 4.7),
        energy=120.0,
        size=5.5,
        color=(0.84, 0.91, 0.98),
        collection=lighting_collection,
        shape="DISK",
    )
    add_area_light(
        "Pedestal top light",
        location=(0.0, -5.0, 2.2),
        target=(0.0, 0.0, BASE_TOP_Z),
        energy=180.0,
        size=8.0,
        color=(0.72, 0.82, 0.90),
        collection=lighting_collection,
        shape="DISK",
    )


def configure_render() -> bpy.types.Scene:
    scene = bpy.context.scene
    try:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    except Exception:
        scene.render.engine = "BLENDER_EEVEE"

    scene.render.resolution_x = RENDER_WIDTH
    scene.render.resolution_y = RENDER_HEIGHT
    scene.render.resolution_percentage = RENDER_PERCENTAGE
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = "8"
    scene.render.film_transparent = True
    scene.render.use_file_extension = True

    # Transparent PNGs should remain compositing-friendly in the browser.
    try:
        scene.render.image_settings.color_mode = "RGBA"
        scene.render.alpha_mode = "STRAIGHT"
    except Exception:
        pass

    try:
        scene.view_settings.look = "AgX - Medium High Contrast"
    except Exception:
        pass

    scene.world.color = (0.018, 0.026, 0.032)
    try:
        scene.world.use_nodes = True
        background = scene.world.node_tree.nodes.get("Background")
        if background is not None:
            background.inputs["Color"].default_value = (0.018, 0.027, 0.034, 1.0)
            background.inputs["Strength"].default_value = 0.18
    except Exception:
        pass

    return scene


def render_pass(
    scene: bpy.types.Scene,
    *,
    filepath: str,
    glass_collection: bpy.types.Collection,
    base_collection: bpy.types.Collection,
    show_glass: bool,
    show_base: bool,
) -> None:
    glass_collection.hide_render = not show_glass
    base_collection.hide_render = not show_base
    scene.render.filepath = filepath
    bpy.ops.render.render(write_still=True)


def build_display_case() -> None:
    clear_scene()
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    glass_collection = create_collection("CASE_GLASS")
    base_collection = create_collection("CASE_BASE")
    lighting_collection = create_collection("CASE_LIGHTS")

    shell_material = make_principled_material(
        "Near-invisible museum glass",
        (0.20, 0.34, 0.42, 0.018),
        roughness=0.11,
        transmission=1.0,
        ior=1.445,
        coat=0.20,
        coat_roughness=0.08,
    )
    edge_material = make_principled_material(
        "Cool glass edge highlight",
        (0.60, 0.76, 0.86, 0.22),
        roughness=0.22,
        transmission=0.10,
        coat=0.16,
        coat_roughness=0.10,
        emission_strength=0.018,
    )
    reflection_material = make_principled_material(
        "Restrained glass reflections",
        (0.72, 0.84, 0.92, 0.08),
        roughness=0.28,
        transmission=0.04,
        coat=0.10,
        coat_roughness=0.12,
        emission_strength=0.008,
    )
    pedestal_material = make_principled_material(
        "Quiet stone pedestal",
        (0.084, 0.095, 0.100, 0.88),
        roughness=0.68,
        metallic=0.02,
        transmission=0.0,
        coat=0.04,
        coat_roughness=0.24,
    )
    pedestal_edge_material = make_principled_material(
        "Pedestal rim highlight",
        (0.34, 0.42, 0.46, 0.26),
        roughness=0.50,
        metallic=0.02,
        coat=0.08,
        coat_roughness=0.16,
        emission_strength=0.0,
    )
    ground_material = make_principled_material(
        "Museum lawn",
        (0.225, 0.330, 0.180, 0.98),
        roughness=0.88,
        metallic=0.0,
        coat=0.0,
    )
    grass_edge_material = make_principled_material(
        "Grass edge highlight",
        (0.315, 0.425, 0.235, 0.92),
        roughness=0.82,
        metallic=0.0,
        coat=0.0,
    )
    path_material = make_principled_material(
        "Golden pathway stone",
        (0.635, 0.515, 0.255, 0.98),
        roughness=0.72,
        metallic=0.02,
        coat=0.04,
        coat_roughness=0.22,
    )
    shadow_material = make_principled_material(
        "Transparent contact shadow",
        (0.004, 0.008, 0.011, 0.12),
        roughness=1.0,
    )

    build_glass(glass_collection, shell_material, edge_material, reflection_material)
    build_base(
        base_collection,
        pedestal_material,
        pedestal_edge_material,
        ground_material,
        grass_edge_material,
        path_material,
        shadow_material,
    )
    setup_camera()
    setup_lighting(lighting_collection)
    scene = configure_render()

    # Save a reusable scene with both modular collections visible.
    glass_collection.hide_render = False
    base_collection.hide_render = False
    blend_path = os.path.join(OUTPUT_DIR, BLEND_NAME)
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)

    glass_path = os.path.join(OUTPUT_DIR, GLASS_RENDER_NAME)
    base_path = os.path.join(OUTPUT_DIR, BASE_RENDER_NAME)
    preview_path = os.path.join(OUTPUT_DIR, PREVIEW_RENDER_NAME)

    render_pass(
        scene,
        filepath=glass_path,
        glass_collection=glass_collection,
        base_collection=base_collection,
        show_glass=True,
        show_base=False,
    )
    render_pass(
        scene,
        filepath=base_path,
        glass_collection=glass_collection,
        base_collection=base_collection,
        show_glass=False,
        show_base=True,
    )
    render_pass(
        scene,
        filepath=preview_path,
        glass_collection=glass_collection,
        base_collection=base_collection,
        show_glass=True,
        show_base=True,
    )

    # Leave the saved file in its natural all-visible state.
    glass_collection.hide_render = False
    base_collection.hide_render = False
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)

    print("\nDisplay case generation complete.")
    print(f"Blend file: {blend_path}")
    print(f"Glass pass: {glass_path}")
    print(f"Base pass: {base_path}")
    print(f"Case preview: {preview_path}\n")


if __name__ == "__main__":
    build_display_case()
