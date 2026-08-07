"""
Procedural Neoclassical House Generator — v11
Blender 4.x / Blender 3.6 compatible

This revision preserves v10 and makes two precise roof-line corrections:
- removes the highlighted upper roof cornice completely
- lowers the remaining roof cornice by 0.02 units so its top aligns exactly with the house wall
- realistic, very small overlapping slate tiles across all four roof slopes
- a much darker natural blue-green slate palette and stone micro-relief
- realistic hip corners, full side-roof slate coverage, and a continuous blue-green fascia
- a true projecting gable roof over the central pediment that extends backward in 3D
- the selected inner triangular pediment field is removed completely
- a circular window whose white cross reaches the glazing edge cleanly
- a lower, perfectly fitted arched door surround that never reaches the upper floor
- plain, uninterrupted mahogany leaves with procedural vertical wood grain
- polished-gold f-hole pulls traced from the user's latest exact paired silhouette
- the existing 5-degree mirrored f-hole tilt is preserved exactly
- both f-hole pulls are moved a tiny amount farther apart without changing their shape, scale, height, or tilt
- completely smooth curls with the small outward center notches kept sharp
- mirrored lower windows centered inside their architectural bays
- identical upper windows whose outer edges align with the lower windows
- orthographic transparent render for a clean 2D website asset

Run inside Blender:
    Scripting workspace -> Open -> choose this file -> Run Script

Outputs are written to:
    ~/Desktop/projects/hecate946.com/blender/house/house.blend
    ~/Desktop/projects/hecate946.com/blender/house/house.png
"""

from __future__ import annotations

import math
import os
from mathutils import Vector

import bpy

# Shared project compatibility rule: never assume an Eevee enum name.
import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from blender.shared.render_compat import set_best_eevee


# -----------------------------------------------------------------------------
# USER CONTROLS
# -----------------------------------------------------------------------------

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
BLEND_NAME = "house.blend"
RENDER_NAME = "house.png"

RENDER_WIDTH = 1800
RENDER_HEIGHT = 1200
RENDER_PERCENTAGE = 100

# Existing outward tilt for the mirrored f-hole pulls; preserved from the supplied v9 script.
F_HOLE_TILT_DEGREES = 5.0

# Horizontal distance of each f-hole center from the door centerline.
# v9 used 0.305; v10 increases it subtly by 0.020 on each side.
F_HOLE_CENTER_X = 0.35

HOUSE_WIDTH = 14.0
HOUSE_DEPTH = 3.10
GROUND_FLOOR_HEIGHT = 3.20
UPPER_FLOOR_HEIGHT = 3.00
ROOF_HEIGHT = 1.78

# Exact mirrored facade dimensions.  The side pairs are derived from the
# corresponding lower window so their margins and spacing match perfectly.
LOWER_WINDOW_X = (-4.525, 4.525)
LOWER_WINDOW_WIDTH = 3.04
LOWER_WINDOW_HEIGHT = 1.78
LOWER_WINDOW_Z = 1.72

UPPER_WINDOW_WIDTH = 0.88
UPPER_WINDOW_HEIGHT = 1.58
UPPER_WINDOW_Z = 4.72
# On each wing, the outside edge of the outer upper window aligns with the
# outside edge of the lower window, and the inside edge of the inner upper
# window aligns with the lower window's inside edge.  The center window stays
# untouched.
_LEFT_LOWER_OUTER_EDGE = LOWER_WINDOW_X[0] - LOWER_WINDOW_WIDTH / 2.0
_LEFT_LOWER_INNER_EDGE = LOWER_WINDOW_X[0] + LOWER_WINDOW_WIDTH / 2.0
_LEFT_UPPER_OUTER_X = _LEFT_LOWER_OUTER_EDGE + UPPER_WINDOW_WIDTH / 2.0
_LEFT_UPPER_INNER_X = _LEFT_LOWER_INNER_EDGE - UPPER_WINDOW_WIDTH / 2.0
UPPER_WINDOW_X = (
    _LEFT_UPPER_OUTER_X,
    _LEFT_UPPER_INNER_X,
    0.0,
    -_LEFT_UPPER_INNER_X,
    -_LEFT_UPPER_OUTER_X,
)

# Dark, restrained materials intended for the softly rendered storybook look.
CREAM = (0.73, 0.67, 0.53, 1.0)
TRIM_CREAM = (0.91, 0.86, 0.72, 1.0)
PEDIMENT_INSET = (0.78, 0.72, 0.59, 1.0)
ARCHITECTURAL_LINE = (0.085, 0.070, 0.046, 1.0)
WINDOW_GLASS = (0.006, 0.015, 0.018, 1.0)
DOOR_WOOD_DARK = (0.010, 0.0018, 0.0012, 1.0)
DOOR_WOOD_LIGHT = (0.072, 0.010, 0.005, 1.0)
GOLD = (0.95, 0.57, 0.075, 1.0)

# These values are deliberately very dark because Blender material inputs are
# linear, not display-referred. They render as deep weathered blue-green slate.
ROOF_BASE = (0.0018, 0.0080, 0.0100, 1.0)
ROOF_SLATE_1 = (0.0045, 0.0200, 0.0230, 1.0)
ROOF_SLATE_2 = (0.0060, 0.0260, 0.0290, 1.0)
ROOF_SLATE_3 = (0.0035, 0.0150, 0.0180, 1.0)
ROOF_EDGE = (0.0010, 0.0038, 0.0048, 1.0)

# More rows and narrower tiles make the building read at a larger scale.
SLATE_ROWS = 36
SLATE_TARGET_WIDTH = 0.190
SLATE_GAP_RATIO = 0.045
LINE_THICKNESS = 0.72

# Normalized anchors traced from the LEFT silhouette in the user's latest clean
# paired f-hole reference. The right pull is produced by mirroring this exact
# outline, preserving the current inward-facing orientation on the doors.
#
# Coordinates are normalized by the silhouette height. The deliberately sharp
# center-notch clusters are identified separately; every other section is
# interpolated into a dense, smooth outline at runtime.
F_HOLE_REFERENCE_ANCHORS = [
    (0.304035, 0.476945),
    (0.234870, 0.500000),
    (0.168588, 0.494236),
    (0.108069, 0.465418),
    (0.056196, 0.407781),
    (0.007205, 0.295389),
    (-0.012968, 0.079251),
    (-0.044669, 0.036023),
    (-0.021614, 0.010086),
    (-0.027378, -0.151297),
    (-0.059078, -0.324207),
    (-0.125360, -0.427954),
    (-0.223343, -0.471182),
    (-0.257925, -0.407781),
    (-0.203170, -0.364553),
    (-0.208934, -0.306916),
    (-0.263689, -0.278098),
    (-0.315562, -0.292507),
    (-0.350000, -0.335735),
    (-0.350000, -0.393372),
    (-0.324207, -0.442363),
    (-0.283862, -0.476945),
    (-0.234870, -0.500000),
    (-0.116715, -0.476945),
    (-0.036023, -0.427954),
    (0.018732, -0.358790),
    (0.059078, -0.231988),
    (0.076369, -0.061960),
    (0.102305, -0.033141),
    (0.076369, -0.001441),
    (0.116715, 0.381844),
    (0.148415, 0.439481),
    (0.208934, 0.474063),
    (0.255043, 0.436599),
    (0.211816, 0.402017),
    (0.217579, 0.355908),
    (0.272334, 0.327089),
    (0.324207, 0.341499),
    (0.344380, 0.370317),
    (0.344380, 0.413545),
]

# These clusters form the two small outward-pointing center notches. Segments
# touching these anchors remain straight, so the notches stay crisp while all
# curls and long edges are smoothed densely.
F_HOLE_SHARP_INDICES = frozenset({6, 7, 8, 27, 28, 29})


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


def add_world_hotspot(
    hotspot_id: str,
    *,
    location: tuple[float, float, float],
    dimensions: tuple[float, float, float],
    collection: bpy.types.Collection,
) -> bpy.types.Object:
    """Add a non-rendering authoring volume consumed by the website world exporter."""
    bpy.ops.mesh.primitive_cube_add(location=location)
    obj = bpy.context.object
    obj.name = f"WORLD_HOTSPOT__{hotspot_id}"
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj["world_hotspot_id"] = hotspot_id
    obj.hide_render = True
    obj.display_type = "WIRE"
    obj.show_in_front = True
    move_to_collection(obj, collection)
    return obj


def look_at(obj: bpy.types.Object, target: tuple[float, float, float]) -> None:
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def make_material(
    name: str,
    color: tuple[float, float, float, float],
    roughness: float = 0.55,
    metallic: float = 0.0,
) -> bpy.types.Material:
    material = bpy.data.materials.new(name=name)
    material.use_nodes = True
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    if bsdf is not None:
        bsdf.inputs["Base Color"].default_value = color
        bsdf.inputs["Roughness"].default_value = roughness
        bsdf.inputs["Metallic"].default_value = metallic
    return material


def make_gold_material(name: str) -> bpy.types.Material:
    """Polished gold with a controlled center highlight and darker edge shading."""
    material = bpy.data.materials.new(name=name)
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()

    output = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    texcoord = nodes.new("ShaderNodeTexCoord")
    separate = nodes.new("ShaderNodeSeparateXYZ")
    ramp = nodes.new("ShaderNodeValToRGB")

    # The generated-coordinate ramp produces a soft polished highlight through
    # the middle of each filled silhouette while keeping its outline unchanged.
    ramp.color_ramp.elements.remove(ramp.color_ramp.elements[1])
    left = ramp.color_ramp.elements[0]
    left.position = 0.0
    left.color = (0.16, 0.055, 0.004, 1.0)
    mid_left = ramp.color_ramp.elements.new(0.30)
    mid_left.color = (0.66, 0.27, 0.018, 1.0)
    center = ramp.color_ramp.elements.new(0.52)
    center.color = (1.0, 0.72, 0.16, 1.0)
    mid_right = ramp.color_ramp.elements.new(0.74)
    mid_right.color = (0.72, 0.31, 0.022, 1.0)
    right = ramp.color_ramp.elements.new(1.0)
    right.color = (0.20, 0.065, 0.005, 1.0)

    bsdf.inputs["Metallic"].default_value = 0.94
    bsdf.inputs["Roughness"].default_value = 0.16
    coat = bsdf.inputs.get("Coat Weight")
    if coat is None:
        coat = bsdf.inputs.get("Clearcoat")
    if coat is not None:
        coat.default_value = 0.28
    coat_roughness = bsdf.inputs.get("Coat Roughness")
    if coat_roughness is None:
        coat_roughness = bsdf.inputs.get("Clearcoat Roughness")
    if coat_roughness is not None:
        coat_roughness.default_value = 0.08

    links.new(texcoord.outputs["Generated"], separate.inputs["Vector"])
    links.new(separate.outputs["X"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])
    return material


def make_wood_material(name: str) -> bpy.types.Material:
    """Deep mahogany with vertical grain, pores, roughness variation, and relief."""
    material = bpy.data.materials.new(name=name)
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()

    output = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    texcoord = nodes.new("ShaderNodeTexCoord")
    mapping = nodes.new("ShaderNodeMapping")
    wave = nodes.new("ShaderNodeTexWave")
    macro_noise = nodes.new("ShaderNodeTexNoise")
    pore_noise = nodes.new("ShaderNodeTexNoise")
    grain_mix = nodes.new("ShaderNodeMixRGB")
    color_ramp = nodes.new("ShaderNodeValToRGB")
    rough_ramp = nodes.new("ShaderNodeValToRGB")
    bump = nodes.new("ShaderNodeBump")

    # Generated coordinates make the grain follow every door leaf consistently.
    mapping.inputs["Scale"].default_value = (4.0, 2.0, 0.42)
    wave.wave_type = "BANDS"
    wave.bands_direction = "X"
    wave.inputs["Scale"].default_value = 11.0
    wave.inputs["Distortion"].default_value = 4.2
    wave_detail = wave.inputs.get("Detail")
    if wave_detail is not None:
        wave_detail.default_value = 5.0

    macro_noise.inputs["Scale"].default_value = 5.5
    macro_noise.inputs["Detail"].default_value = 6.0
    macro_noise.inputs["Roughness"].default_value = 0.76
    pore_noise.inputs["Scale"].default_value = 42.0
    pore_noise.inputs["Detail"].default_value = 3.0
    pore_noise.inputs["Roughness"].default_value = 0.62

    grain_mix.blend_type = "MULTIPLY"
    grain_mix.inputs[0].default_value = 0.72

    color_ramp.color_ramp.elements[0].position = 0.18
    color_ramp.color_ramp.elements[0].color = DOOR_WOOD_DARK
    color_ramp.color_ramp.elements[1].position = 0.82
    color_ramp.color_ramp.elements[1].color = DOOR_WOOD_LIGHT

    rough_ramp.color_ramp.elements[0].color = (0.28, 0.28, 0.28, 1.0)
    rough_ramp.color_ramp.elements[1].color = (0.56, 0.56, 0.56, 1.0)

    bsdf.inputs["Roughness"].default_value = 0.40
    specular_socket = bsdf.inputs.get("Specular IOR Level") or bsdf.inputs.get("Specular")
    if specular_socket is not None:
        specular_socket.default_value = 0.32
    coat_socket = bsdf.inputs.get("Coat Weight") or bsdf.inputs.get("Clearcoat")
    if coat_socket is not None:
        coat_socket.default_value = 0.08

    bump.inputs["Strength"].default_value = 0.24
    bump.inputs["Distance"].default_value = 0.026

    links.new(texcoord.outputs["Generated"], mapping.inputs["Vector"])
    links.new(mapping.outputs["Vector"], wave.inputs["Vector"])
    links.new(mapping.outputs["Vector"], macro_noise.inputs["Vector"])
    links.new(mapping.outputs["Vector"], pore_noise.inputs["Vector"])
    links.new(wave.outputs["Color"], grain_mix.inputs[1])
    links.new(macro_noise.outputs["Fac"], grain_mix.inputs[2])
    links.new(grain_mix.outputs["Color"], color_ramp.inputs["Fac"])
    links.new(color_ramp.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(macro_noise.outputs["Fac"], rough_ramp.inputs["Fac"])
    links.new(rough_ramp.outputs["Color"], bsdf.inputs["Roughness"])
    links.new(pore_noise.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])
    return material


def make_slate_material(
    name: str,
    color: tuple[float, float, float, float],
) -> bpy.types.Material:
    """Layered weathered slate with macro color drift and fine chipped relief."""
    material = bpy.data.materials.new(name=name)
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()

    output = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    texcoord = nodes.new("ShaderNodeTexCoord")
    mapping = nodes.new("ShaderNodeMapping")
    macro_noise = nodes.new("ShaderNodeTexNoise")
    micro_noise = nodes.new("ShaderNodeTexNoise")
    color_ramp = nodes.new("ShaderNodeValToRGB")
    bump = nodes.new("ShaderNodeBump")

    mapping.inputs["Scale"].default_value = (1.0, 1.0, 1.0)
    macro_noise.inputs["Scale"].default_value = 5.0
    macro_noise.inputs["Detail"].default_value = 5.0
    macro_noise.inputs["Roughness"].default_value = 0.74
    micro_noise.inputs["Scale"].default_value = 58.0
    micro_noise.inputs["Detail"].default_value = 4.0
    micro_noise.inputs["Roughness"].default_value = 0.70

    darker = tuple(max(0.0, channel * 0.62) for channel in color[:3]) + (1.0,)
    lighter = tuple(min(1.0, channel * 1.42 + 0.002) for channel in color[:3]) + (1.0,)
    color_ramp.color_ramp.elements[0].position = 0.18
    color_ramp.color_ramp.elements[0].color = darker
    color_ramp.color_ramp.elements[1].position = 0.82
    color_ramp.color_ramp.elements[1].color = lighter

    bsdf.inputs["Roughness"].default_value = 0.84
    specular_socket = bsdf.inputs.get("Specular IOR Level") or bsdf.inputs.get("Specular")
    if specular_socket is not None:
        specular_socket.default_value = 0.16
    bump.inputs["Strength"].default_value = 0.30
    bump.inputs["Distance"].default_value = 0.020

    links.new(texcoord.outputs["Generated"], mapping.inputs["Vector"])
    links.new(mapping.outputs["Vector"], macro_noise.inputs["Vector"])
    links.new(mapping.outputs["Vector"], micro_noise.inputs["Vector"])
    links.new(macro_noise.outputs["Fac"], color_ramp.inputs["Fac"])
    links.new(color_ramp.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(micro_noise.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])
    return material


def add_box(
    name: str,
    location: tuple[float, float, float],
    dimensions: tuple[float, float, float],
    material: bpy.types.Material,
    bevel: float = 0.04,
    collection: bpy.types.Collection | None = None,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cube_add(location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    if bevel > 0:
        bevel_modifier = obj.modifiers.new(name="Soft bevel", type="BEVEL")
        bevel_modifier.width = bevel
        bevel_modifier.segments = 2

    obj.data.materials.append(material)
    if collection is not None:
        move_to_collection(obj, collection)
    return obj


def add_rotated_box_y(
    name: str,
    location: tuple[float, float, float],
    dimensions: tuple[float, float, float],
    rotation_y: float,
    material: bpy.types.Material,
    bevel: float,
    collection: bpy.types.Collection,
) -> bpy.types.Object:
    """Create a cuboid rotated around Y, useful for solid gable-roof plates."""
    bpy.ops.mesh.primitive_cube_add(location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.rotation_euler = (0.0, rotation_y, 0.0)
    if bevel > 0:
        modifier = obj.modifiers.new(name="Soft bevel", type="BEVEL")
        modifier.width = bevel
        modifier.segments = 2
    obj.data.materials.append(material)
    move_to_collection(obj, collection)
    return obj


def add_mesh_object(
    name: str,
    vertices: list[tuple[float, float, float]],
    faces: list[tuple[int, ...]],
    material: bpy.types.Material,
    collection: bpy.types.Collection,
    bevel: float = 0.0,
) -> bpy.types.Object:
    mesh = bpy.data.meshes.new(f"{name}_mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()

    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    obj.data.materials.append(material)

    if bevel > 0:
        bevel_modifier = obj.modifiers.new(name="Soft bevel", type="BEVEL")
        bevel_modifier.width = bevel
        bevel_modifier.segments = 2
    return obj


def add_bezier_curve(
    name: str,
    points: list[tuple[float, float, float]],
    bevel_depth: float,
    material: bpy.types.Material,
    collection: bpy.types.Collection,
    cyclic: bool = False,
) -> bpy.types.Object:
    curve_data = bpy.data.curves.new(name=f"{name}_curve", type="CURVE")
    curve_data.dimensions = "3D"
    curve_data.resolution_u = 16
    curve_data.bevel_resolution = 4
    curve_data.bevel_depth = bevel_depth

    spline = curve_data.splines.new("BEZIER")
    spline.bezier_points.add(len(points) - 1)
    for bezier_point, coordinate in zip(spline.bezier_points, points):
        bezier_point.co = coordinate
        bezier_point.handle_left_type = "AUTO"
        bezier_point.handle_right_type = "AUTO"
    spline.use_cyclic_u = cyclic

    obj = bpy.data.objects.new(name, curve_data)
    collection.objects.link(obj)
    obj.data.materials.append(material)
    return obj


def add_poly_curve(
    name: str,
    points: list[tuple[float, float, float]],
    bevel_depth: float,
    material: bpy.types.Material,
    collection: bpy.types.Collection,
    cyclic: bool = False,
) -> bpy.types.Object:
    """Straight segmented trim. Unlike auto Bezier handles, this cannot overshoot."""
    curve_data = bpy.data.curves.new(name=f"{name}_curve", type="CURVE")
    curve_data.dimensions = "3D"
    curve_data.resolution_u = 1
    curve_data.bevel_resolution = 3
    curve_data.bevel_depth = bevel_depth

    spline = curve_data.splines.new("POLY")
    spline.points.add(len(points) - 1)
    for point, coordinate in zip(spline.points, points):
        point.co = (*coordinate, 1.0)
    spline.use_cyclic_u = cyclic

    obj = bpy.data.objects.new(name, curve_data)
    collection.objects.link(obj)
    obj.data.materials.append(material)
    return obj


def extrude_polygon_xz(
    name: str,
    outline: list[tuple[float, float]],
    y_front: float,
    y_back: float,
    material: bpy.types.Material,
    collection: bpy.types.Collection,
    bevel: float = 0.018,
) -> bpy.types.Object:
    """Extrude an arbitrary X/Z polygon between two Y planes."""
    vertices: list[tuple[float, float, float]] = []
    vertices.extend((x, y_front, z) for x, z in outline)
    vertices.extend((x, y_back, z) for x, z in outline)

    count = len(outline)
    faces: list[tuple[int, ...]] = [
        tuple(reversed(range(count))),
        tuple(range(count, count * 2)),
    ]
    for index in range(count):
        next_index = (index + 1) % count
        faces.append((index, count + index, count + next_index, next_index))

    return add_mesh_object(name, vertices, faces, material, collection, bevel=bevel)


# -----------------------------------------------------------------------------
# WINDOWS
# -----------------------------------------------------------------------------


def create_window(
    name: str,
    x: float,
    z: float,
    width: float,
    height: float,
    columns: int,
    rows: int,
    wall_front_y: float,
    trim: bpy.types.Material,
    glass: bpy.types.Material,
    collection: bpy.types.Collection,
) -> None:
    y_glass = wall_front_y - 0.038
    y_frame = wall_front_y - 0.090

    add_box(
        f"{name}_glass",
        (x, y_glass, z),
        (width, 0.055, height),
        glass,
        bevel=0.018,
        collection=collection,
    )

    frame = 0.085
    add_box(f"{name}_top", (x, y_frame, z + height / 2 + frame / 2), (width + 0.20, 0.09, frame), trim, 0.018, collection)
    add_box(f"{name}_bottom", (x, y_frame, z - height / 2 - frame / 2), (width + 0.24, 0.10, frame), trim, 0.018, collection)
    add_box(f"{name}_left", (x - width / 2 - frame / 2, y_frame, z), (frame, 0.09, height + 0.15), trim, 0.018, collection)
    add_box(f"{name}_right", (x + width / 2 + frame / 2, y_frame, z), (frame, 0.09, height + 0.15), trim, 0.018, collection)

    mullion = 0.042
    for index in range(1, columns):
        xx = x - width / 2 + width * index / columns
        add_box(f"{name}_v{index}", (xx, y_frame - 0.012, z), (mullion, 0.052, height), trim, 0.006, collection)
    for index in range(1, rows):
        zz = z - height / 2 + height * index / rows
        add_box(f"{name}_h{index}", (x, y_frame - 0.012, zz), (width, 0.052, mullion), trim, 0.006, collection)

    add_box(f"{name}_lintel", (x, y_frame - 0.006, z + height / 2 + 0.165), (width + 0.40, 0.13, 0.125), trim, 0.022, collection)
    add_box(f"{name}_sill", (x, y_frame - 0.006, z - height / 2 - 0.155), (width + 0.34, 0.15, 0.115), trim, 0.022, collection)


# -----------------------------------------------------------------------------
# DOOR
# -----------------------------------------------------------------------------


def arch_leaf_outline(
    side: str,
    width: float,
    straight_height: float,
    base_z: float,
    arc_segments: int = 30,
) -> list[tuple[float, float]]:
    """Create one half of a true semicircular double-door profile."""
    radius = width / 2.0
    spring_z = base_z + straight_height
    top_z = spring_z + radius

    if side == "LEFT":
        outline: list[tuple[float, float]] = [
            (0.0, base_z),
            (-radius, base_z),
            (-radius, spring_z),
        ]
        # The left spring point is already present, so start at segment 1.
        for index in range(1, arc_segments + 1):
            angle = math.pi - (math.pi / 2.0) * index / arc_segments
            outline.append((radius * math.cos(angle), spring_z + radius * math.sin(angle)))
        return outline

    outline = [(0.0, base_z), (0.0, top_z)]
    # The top-center point is already present, so start at segment 1.
    for index in range(1, arc_segments + 1):
        angle = (math.pi / 2.0) * (1.0 - index / arc_segments)
        outline.append((radius * math.cos(angle), spring_z + radius * math.sin(angle)))
    outline.append((radius, base_z))
    return outline


def create_panel_frame(
    name: str,
    x: float,
    z: float,
    width: float,
    height: float,
    y: float,
    wood_trim: bpy.types.Material,
    wood_inset: bpy.types.Material,
    collection: bpy.types.Collection,
) -> None:
    """A shallow inset panel with beveled wooden rails."""
    add_box(f"{name}_inset", (x, y + 0.010, z), (width, 0.025, height), wood_inset, 0.025, collection)
    rail = 0.050
    projection_y = y - 0.012
    add_box(f"{name}_left", (x - width / 2, projection_y, z), (rail, 0.035, height + rail), wood_trim, 0.012, collection)
    add_box(f"{name}_right", (x + width / 2, projection_y, z), (rail, 0.035, height + rail), wood_trim, 0.012, collection)
    add_box(f"{name}_top", (x, projection_y, z + height / 2), (width + rail, 0.035, rail), wood_trim, 0.012, collection)
    add_box(f"{name}_bottom", (x, projection_y, z - height / 2), (width + rail, 0.035, rail), wood_trim, 0.012, collection)


def create_arch_trim(
    name: str,
    width: float,
    straight_height: float,
    base_z: float,
    y: float,
    material: bpy.types.Material,
    collection: bpy.types.Collection,
    thickness: float,
) -> bpy.types.Object:
    radius = width / 2.0
    spring_z = base_z + straight_height
    points: list[tuple[float, float, float]] = [(-radius, y, base_z), (-radius, y, spring_z)]
    segments = 64
    for index in range(segments + 1):
        angle = math.pi - math.pi * index / segments
        points.append((radius * math.cos(angle), y, spring_z + radius * math.sin(angle)))
    points.extend([(radius, y, spring_z), (radius, y, base_z)])
    return add_poly_curve(name, points, thickness, material, collection)


def _centripetal_catmull_rom(
    p0: Vector,
    p1: Vector,
    p2: Vector,
    p3: Vector,
    t: float,
    alpha: float = 0.5,
) -> Vector:
    """Interpolate one stable, non-overshooting centripetal Catmull-Rom point."""

    def next_parameter(previous: float, a: Vector, b: Vector) -> float:
        return previous + max((b - a).length, 1e-9) ** alpha

    t0 = 0.0
    t1 = next_parameter(t0, p0, p1)
    t2 = next_parameter(t1, p1, p2)
    t3 = next_parameter(t2, p2, p3)
    sample_t = t1 + (t2 - t1) * t

    def interpolate(a: Vector, b: Vector, ta: float, tb: float) -> Vector:
        denominator = tb - ta
        if abs(denominator) < 1e-9:
            return a.copy()
        return ((tb - sample_t) / denominator) * a + ((sample_t - ta) / denominator) * b

    a1 = interpolate(p0, p1, t0, t1)
    a2 = interpolate(p1, p2, t1, t2)
    a3 = interpolate(p2, p3, t2, t3)

    denominator_02 = t2 - t0
    denominator_13 = t3 - t1
    b1 = a1 if abs(denominator_02) < 1e-9 else ((t2 - sample_t) / denominator_02) * a1 + ((sample_t - t0) / denominator_02) * a2
    b2 = a2 if abs(denominator_13) < 1e-9 else ((t3 - sample_t) / denominator_13) * a2 + ((sample_t - t1) / denominator_13) * a3

    denominator_12 = t2 - t1
    if abs(denominator_12) < 1e-9:
        return p1.copy()
    return ((t2 - sample_t) / denominator_12) * b1 + ((sample_t - t1) / denominator_12) * b2


def _build_exact_f_hole_outline(subdivisions: int = 8) -> list[tuple[float, float]]:
    """Return a dense smooth outline while retaining both triangular notches."""
    anchors = [Vector((x, z)) for x, z in F_HOLE_REFERENCE_ANCHORS]
    point_count = len(anchors)
    outline: list[tuple[float, float]] = []

    for index in range(point_count):
        next_index = (index + 1) % point_count
        p1 = anchors[index]
        p2 = anchors[next_index]

        # The exact notch sides are intentionally straight. This keeps the tiny
        # center indents sharp and prevents any smoothing from rounding them off.
        use_linear = index in F_HOLE_SHARP_INDICES or next_index in F_HOLE_SHARP_INDICES

        if use_linear:
            for step in range(subdivisions):
                fraction = step / subdivisions
                point = p1.lerp(p2, fraction)
                outline.append((point.x, point.y))
            continue

        p0 = anchors[(index - 1) % point_count]
        p3 = anchors[(index + 2) % point_count]

        # Do not let a sharp notch anchor influence the tangent of a neighboring
        # smooth segment. Duplicating the endpoint produces a clean transition.
        if (index - 1) % point_count in F_HOLE_SHARP_INDICES:
            p0 = p1
        if (index + 2) % point_count in F_HOLE_SHARP_INDICES:
            p3 = p2

        for step in range(subdivisions):
            fraction = step / subdivisions
            point = _centripetal_catmull_rom(p0, p1, p2, p3, fraction)
            outline.append((point.x, point.y))

    return outline


def create_f_hole(
    name: str,
    center_x: float,
    center_z: float,
    mirror_x: bool,
    rotation_degrees: float,
    y: float,
    gold: bpy.types.Material,
    collection: bpy.types.Collection,
) -> bpy.types.Object:
    """Create the exact mirrored silhouette, rotated around its own center."""
    curve_data = bpy.data.curves.new(name=f"{name}_curve", type="CURVE")
    curve_data.dimensions = "2D"
    curve_data.resolution_u = 12
    curve_data.render_resolution_u = 16
    curve_data.fill_mode = "BOTH"
    curve_data.extrude = 0.008
    curve_data.bevel_depth = 0.0011
    curve_data.bevel_resolution = 5
    curve_data.resolution_v = 5

    exact_outline = _build_exact_f_hole_outline(subdivisions=8)
    spline = curve_data.splines.new("POLY")
    spline.points.add(len(exact_outline) - 1)

    # The new reference is naturally broader than the old silhouette. A scale of
    # 0.82 preserves its exact proportions while fitting cleanly on each door leaf.
    scale = 0.82
    rotation_radians = math.radians(rotation_degrees)
    cosine = math.cos(rotation_radians)
    sine = math.sin(rotation_radians)

    for point, (x, z) in zip(spline.points, exact_outline):
        # Mirror first so both pulls retain the requested inward-facing orientation,
        # then rotate the finished silhouette around its own local origin/center.
        local_x = -x if mirror_x else x
        scaled_x = local_x * scale
        scaled_z = z * scale
        rotated_x = scaled_x * cosine - scaled_z * sine
        rotated_z = scaled_x * sine + scaled_z * cosine
        point.co = (rotated_x, rotated_z, 0.0, 1.0)

    spline.use_cyclic_u = True

    obj = bpy.data.objects.new(name, curve_data)
    collection.objects.link(obj)
    obj.location = (center_x, y, center_z)
    # Curve fills live in local XY; rotate them into the facade's XZ plane.
    obj.rotation_euler = (math.radians(90.0), 0.0, 0.0)
    obj.data.materials.append(gold)
    return obj


def create_door(
    collection: bpy.types.Collection,
    wall_front_y: float,
    trim: bpy.types.Material,
    wood: bpy.types.Material,
    wood_inset: bpy.types.Material,
    gold: bpy.types.Material,
) -> None:
    # The outer surround tops out below z=2.90; the floor cornice begins above 3.04.
    # This guarantees that the doorway never spills into the upper floor.
    door_width = 1.72
    door_straight_height = 1.39
    door_base_z = 0.40
    door_front_y = wall_front_y - 0.155
    door_back_y = wall_front_y - 0.045

    left_outline = arch_leaf_outline("LEFT", door_width, door_straight_height, door_base_z)
    right_outline = arch_leaf_outline("RIGHT", door_width, door_straight_height, door_base_z)

    extrude_polygon_xz("Left arched mahogany leaf", left_outline, door_front_y, door_back_y, wood, collection, bevel=0.030)
    extrude_polygon_xz("Right arched mahogany leaf", right_outline, door_front_y, door_back_y, wood, collection, bevel=0.030)

    top_z = door_base_z + door_straight_height + door_width / 2.0
    add_box(
        "Door center recessed seam",
        (0.0, door_front_y - 0.022, (door_base_z + top_z) / 2.0),
        (0.026, 0.030, top_z - door_base_z - 0.03),
        wood_inset,
        bevel=0.003,
        collection=collection,
    )

    # Keep both leaves as uninterrupted wood.  The procedural material provides
    # realistic vertical grain without decorative square panels.

    # Three concentric, exactly calculated surrounds; all remain on the first floor.
    create_arch_trim("Door innermost reveal", 1.82, 1.415, door_base_z - 0.005, wall_front_y - 0.205, trim, collection, 0.035)
    create_arch_trim("Door inner stone trim", 1.92, 1.445, door_base_z - 0.020, wall_front_y - 0.215, trim, collection, 0.047)
    create_arch_trim("Door outer stone trim", 2.06, 1.470, door_base_z - 0.035, wall_front_y - 0.205, trim, collection, 0.064)

    # Filled silhouettes are traced from the user's exact reference and mirrored.
    create_f_hole(
        "Left exact gold f hole",
        -F_HOLE_CENTER_X,
        1.50,
        mirror_x=False,
        rotation_degrees=F_HOLE_TILT_DEGREES,
        y=door_front_y - 0.074,
        gold=gold,
        collection=collection,
    )
    create_f_hole(
        "Right exact gold f hole",
        F_HOLE_CENTER_X,
        1.50,
        mirror_x=True,
        rotation_degrees=-F_HOLE_TILT_DEGREES,
        y=door_front_y - 0.074,
        gold=gold,
        collection=collection,
    )


# -----------------------------------------------------------------------------
# ROOF AND PEDIMENT
# -----------------------------------------------------------------------------


def append_oriented_cuboid(
    vertices: list[tuple[float, float, float]],
    faces: list[tuple[int, ...]],
    center: tuple[float, float, float],
    dimensions: tuple[float, float, float],
    rotation_x: float,
) -> None:
    """Append one disconnected, X-axis-rotated cuboid to an aggregate mesh."""
    cx, cy, cz = center
    sx, sy, sz = (dimension / 2.0 for dimension in dimensions)
    start = len(vertices)
    cosine = math.cos(rotation_x)
    sine = math.sin(rotation_x)

    local_vertices = [
        (-sx, -sy, -sz),
        (sx, -sy, -sz),
        (sx, sy, -sz),
        (-sx, sy, -sz),
        (-sx, -sy, sz),
        (sx, -sy, sz),
        (sx, sy, sz),
        (-sx, sy, sz),
    ]
    for x, y, z in local_vertices:
        rotated_y = y * cosine - z * sine
        rotated_z = y * sine + z * cosine
        vertices.append((cx + x, cy + rotated_y, cz + rotated_z))

    faces.extend(
        [
            (start + 0, start + 1, start + 2, start + 3),
            (start + 4, start + 7, start + 6, start + 5),
            (start + 0, start + 4, start + 5, start + 1),
            (start + 1, start + 5, start + 6, start + 2),
            (start + 2, start + 6, start + 7, start + 3),
            (start + 4, start + 0, start + 3, start + 7),
        ]
    )


def append_oriented_cuboid_y(
    vertices: list[tuple[float, float, float]],
    faces: list[tuple[int, ...]],
    center: tuple[float, float, float],
    dimensions: tuple[float, float, float],
    rotation_y: float,
) -> None:
    """Append one disconnected, Y-axis-rotated cuboid to an aggregate mesh."""
    cx, cy, cz = center
    sx, sy, sz = (dimension / 2.0 for dimension in dimensions)
    start = len(vertices)
    cosine = math.cos(rotation_y)
    sine = math.sin(rotation_y)

    local_vertices = [
        (-sx, -sy, -sz),
        (sx, -sy, -sz),
        (sx, sy, -sz),
        (-sx, sy, -sz),
        (-sx, -sy, sz),
        (sx, -sy, sz),
        (sx, sy, sz),
        (-sx, sy, sz),
    ]
    for x, y, z in local_vertices:
        rotated_x = x * cosine + z * sine
        rotated_z = -x * sine + z * cosine
        vertices.append((cx + rotated_x, cy + y, cz + rotated_z))

    faces.extend(
        [
            (start + 0, start + 1, start + 2, start + 3),
            (start + 4, start + 7, start + 6, start + 5),
            (start + 0, start + 4, start + 5, start + 1),
            (start + 1, start + 5, start + 6, start + 2),
            (start + 2, start + 6, start + 7, start + 3),
            (start + 4, start + 0, start + 3, start + 7),
        ]
    )


def _finish_slate_mesh(
    name: str,
    vertices: list[tuple[float, float, float]],
    faces: list[tuple[int, ...]],
    material_by_face: list[int],
    collection: bpy.types.Collection,
    materials: tuple[bpy.types.Material, bpy.types.Material, bpy.types.Material],
    edge_material: bpy.types.Material,
) -> bpy.types.Object:
    mesh = bpy.data.meshes.new(f"{name}_mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    slate_object = bpy.data.objects.new(name, mesh)
    collection.objects.link(slate_object)
    for material in materials:
        slate_object.data.materials.append(material)
    slate_object.data.materials.append(edge_material)
    for polygon, material_index in zip(slate_object.data.polygons, material_by_face):
        polygon.material_index = material_index

    bevel_modifier = slate_object.modifiers.new(name="Naturally softened slate edges", type="BEVEL")
    bevel_modifier.width = 0.006
    bevel_modifier.segments = 1
    return slate_object


def create_slate_field(
    collection: bpy.types.Collection,
    materials: tuple[bpy.types.Material, bpy.types.Material, bpy.types.Material],
    edge_material: bpy.types.Material,
    half_width: float,
    half_depth: float,
    ridge_half_width: float,
    roof_base_z: float,
    ridge_z: float,
    eave_sign: int,
) -> None:
    """Create one detailed front or rear trapezoidal field of overlapping slate."""
    if eave_sign not in (-1, 1):
        raise ValueError("eave_sign must be -1 for front or +1 for rear")

    roof_run = half_depth
    roof_rise = ridge_z - roof_base_z
    slope_angle = math.atan2(roof_rise, roof_run)
    slope_length = math.hypot(roof_run, roof_rise)
    row_pitch = slope_length / SLATE_ROWS
    slate_depth = row_pitch * 1.46
    slate_thickness = 0.030
    rotation_x = -eave_sign * slope_angle
    field_name = "Front" if eave_sign < 0 else "Rear"

    vertices: list[tuple[float, float, float]] = []
    faces: list[tuple[int, ...]] = []
    material_by_face: list[int] = []

    for row in range(SLATE_ROWS):
        t = (row + 0.45) / SLATE_ROWS
        center_y = eave_sign * half_depth * (1.0 - t)
        center_z = roof_base_z + roof_rise * t + 0.021
        available_half_width = half_width + (ridge_half_width - half_width) * t

        pitch = SLATE_TARGET_WIDTH
        positions: list[float] = []
        if row % 2 == 0:
            positions.append(0.0)
            index = 1
            while index * pitch <= available_half_width - pitch * 0.42:
                positions.extend((-index * pitch, index * pitch))
                index += 1
        else:
            index = 0
            while (index + 0.5) * pitch <= available_half_width - pitch * 0.42:
                value = (index + 0.5) * pitch
                positions.extend((-value, value))
                index += 1

        for x in sorted(positions):
            # Variation uses abs(x), preserving exact left-right symmetry.
            phase = row * 1.713 + abs(x) * 8.119
            width_factor = 0.965 + 0.025 * math.sin(phase)
            depth_factor = 0.985 + 0.025 * math.cos(phase * 0.73)
            relief = 0.0035 * math.sin(phase * 1.31)
            slate_width = pitch * (1.0 - SLATE_GAP_RATIO) * width_factor

            face_start = len(faces)
            append_oriented_cuboid(
                vertices,
                faces,
                (x, center_y, center_z + relief),
                (slate_width, slate_depth * depth_factor, slate_thickness),
                rotation_x,
            )
            variation = (row + int(round(abs(x) / max(pitch, 0.001)))) % 3
            material_by_face.extend([3, variation, 3, 3, 3, 3])
            assert len(faces) - face_start == 6

    _finish_slate_mesh(
        f"{field_name} fine overlapping natural slate",
        vertices,
        faces,
        material_by_face,
        collection,
        materials,
        edge_material,
    )


def create_side_slate_field(
    collection: bpy.types.Collection,
    materials: tuple[bpy.types.Material, bpy.types.Material, bpy.types.Material],
    edge_material: bpy.types.Material,
    half_width: float,
    half_depth: float,
    ridge_half_width: float,
    roof_base_z: float,
    ridge_z: float,
    side_sign: int,
) -> None:
    """Tile a triangular hip side so the roof texture wraps around naturally."""
    if side_sign not in (-1, 1):
        raise ValueError("side_sign must be -1 for left or +1 for right")

    roof_run = half_width - ridge_half_width
    roof_rise = ridge_z - roof_base_z
    slope_angle = math.atan2(roof_rise, roof_run)
    slope_length = math.hypot(roof_run, roof_rise)
    row_pitch = slope_length / SLATE_ROWS
    slate_depth = row_pitch * 1.46
    slate_thickness = 0.030
    rotation_y = side_sign * slope_angle
    field_name = "Left" if side_sign < 0 else "Right"

    vertices: list[tuple[float, float, float]] = []
    faces: list[tuple[int, ...]] = []
    material_by_face: list[int] = []

    for row in range(SLATE_ROWS):
        t = (row + 0.45) / SLATE_ROWS
        center_x = side_sign * (half_width - roof_run * t)
        center_z = roof_base_z + roof_rise * t + 0.022
        available_half_depth = half_depth * (1.0 - t)

        pitch = SLATE_TARGET_WIDTH
        positions: list[float] = []
        if row % 2 == 0:
            positions.append(0.0)
            index = 1
            while index * pitch <= available_half_depth - pitch * 0.42:
                positions.extend((-index * pitch, index * pitch))
                index += 1
        else:
            index = 0
            while (index + 0.5) * pitch <= available_half_depth - pitch * 0.42:
                value = (index + 0.5) * pitch
                positions.extend((-value, value))
                index += 1

        for y in sorted(positions):
            # Variation uses abs(y), keeping front/back edges balanced.
            phase = row * 1.713 + abs(y) * 8.119
            width_factor = 0.965 + 0.025 * math.sin(phase)
            depth_factor = 0.985 + 0.025 * math.cos(phase * 0.73)
            relief = 0.0035 * math.sin(phase * 1.31)
            slate_width = pitch * (1.0 - SLATE_GAP_RATIO) * width_factor

            face_start = len(faces)
            append_oriented_cuboid_y(
                vertices,
                faces,
                (center_x, y, center_z + relief),
                (slate_depth * depth_factor, slate_width, slate_thickness),
                rotation_y,
            )
            variation = (row + int(round(abs(y) / max(pitch, 0.001)))) % 3
            material_by_face.extend([3, variation, 3, 3, 3, 3])
            assert len(faces) - face_start == 6

    _finish_slate_mesh(
        f"{field_name} fine overlapping natural slate",
        vertices,
        faces,
        material_by_face,
        collection,
        materials,
        edge_material,
    )


def create_roof(
    collection: bpy.types.Collection,
    shell_material: bpy.types.Material,
    slate_materials: tuple[bpy.types.Material, bpy.types.Material, bpy.types.Material],
    edge_material: bpy.types.Material,
    roof_base_z: float,
) -> None:
    half_width = HOUSE_WIDTH / 2.0 + 0.34
    half_depth = HOUSE_DEPTH / 2.0 + 0.30
    ridge_half_width = HOUSE_WIDTH * 0.31
    ridge_z = roof_base_z + ROOF_HEIGHT

    vertices = [
        (-half_width, -half_depth, roof_base_z),
        (half_width, -half_depth, roof_base_z),
        (half_width, half_depth, roof_base_z),
        (-half_width, half_depth, roof_base_z),
        (-ridge_half_width, 0.0, ridge_z),
        (ridge_half_width, 0.0, ridge_z),
    ]
    faces = [
        (0, 1, 5, 4),
        (1, 2, 5),
        (2, 3, 4, 5),
        (3, 0, 4),
    ]
    add_mesh_object("Dark hip roof shell", vertices, faces, shell_material, collection, bevel=0.028)

    # Tile every roof plane.  The side fields are the key change from v3: the
    # realistic small-slate texture now wraps around both hip ends.
    create_slate_field(collection, slate_materials, edge_material, half_width, half_depth, ridge_half_width, roof_base_z, ridge_z, eave_sign=-1)
    create_slate_field(collection, slate_materials, edge_material, half_width, half_depth, ridge_half_width, roof_base_z, ridge_z, eave_sign=1)
    create_side_slate_field(collection, slate_materials, edge_material, half_width, half_depth, ridge_half_width, roof_base_z, ridge_z, side_sign=-1)
    create_side_slate_field(collection, slate_materials, edge_material, half_width, half_depth, ridge_half_width, roof_base_z, ridge_z, side_sign=1)

    # Full perimeter edges and all four hip caps hide field intersections and make
    # the roof corners read as constructed rather than cut off.
    add_poly_curve("Front roof drip edge", [(-half_width, -half_depth - 0.025, roof_base_z), (half_width, -half_depth - 0.025, roof_base_z)], 0.050, edge_material, collection)
    add_poly_curve("Rear roof drip edge", [(-half_width, half_depth + 0.025, roof_base_z), (half_width, half_depth + 0.025, roof_base_z)], 0.050, edge_material, collection)
    add_poly_curve("Left side roof drip edge", [(-half_width - 0.025, -half_depth, roof_base_z), (-half_width - 0.025, half_depth, roof_base_z)], 0.050, edge_material, collection)
    add_poly_curve("Right side roof drip edge", [(half_width + 0.025, -half_depth, roof_base_z), (half_width + 0.025, half_depth, roof_base_z)], 0.050, edge_material, collection)
    add_poly_curve("Front left hip cap", [(-half_width, -half_depth, roof_base_z), (-ridge_half_width, 0.0, ridge_z)], 0.046, edge_material, collection)
    add_poly_curve("Front right hip cap", [(half_width, -half_depth, roof_base_z), (ridge_half_width, 0.0, ridge_z)], 0.046, edge_material, collection)
    add_poly_curve("Rear left hip cap", [(-half_width, half_depth, roof_base_z), (-ridge_half_width, 0.0, ridge_z)], 0.046, edge_material, collection)
    add_poly_curve("Rear right hip cap", [(half_width, half_depth, roof_base_z), (ridge_half_width, 0.0, ridge_z)], 0.046, edge_material, collection)
    add_poly_curve("Roof ridge cap", [(-ridge_half_width, 0.0, ridge_z), (ridge_half_width, 0.0, ridge_z)], 0.050, edge_material, collection)


def create_pediment(
    collection: bpy.types.Collection,
    trim: bpy.types.Material,
    inset_material: bpy.types.Material,
    blue_outline: bpy.types.Material,
    glass: bpy.types.Material,
    roof_material: bpy.types.Material,
    wall_front_y: float,
    roof_base_z: float,
) -> None:
    width = 4.18
    height = 1.52
    depth = 0.24
    y_front = wall_front_y - 0.45
    y_back = y_front + depth

    # The triangular wall begins fully above the fascia.  This prevents the
    # cream pediment from peeking below or around the blue-green strip.
    z_base = roof_base_z + 0.045

    front = [(-width / 2, y_front, z_base), (width / 2, y_front, z_base), (0.0, y_front, z_base + height)]
    back = [(-width / 2, y_back, z_base), (width / 2, y_back, z_base), (0.0, y_back, z_base + height)]
    vertices = front + back
    faces = [
        (0, 1, 2),
        (3, 5, 4),
        (0, 3, 4, 1),
        (1, 4, 5, 2),
        (2, 5, 3, 0),
    ]
    add_mesh_object("Central triangular pediment", vertices, faces, trim, collection, bevel=0.012)

    # The previously selected inner triangular field has been removed. The
    # structural pediment wall remains, so the circular window and gable roof
    # stay correctly supported without a redundant face layered in front.

    # Pronounced blue-green outlines match the fascia directly below.
    # The previously selected inner raking strip has intentionally been removed.
    # The outer cream cornice and thin blue roof accent remain unchanged.
    add_poly_curve(
        "Pediment cream raking cornice",
        [
            (-width / 2 - 0.08, y_front - 0.078, z_base + 0.015),
            (0.0, y_front - 0.078, z_base + height + 0.08),
            (width / 2 + 0.08, y_front - 0.078, z_base + 0.015),
        ],
        0.054,
        trim,
        collection,
    )
    add_poly_curve(
        "Pediment blue outer accent",
        [
            (-width / 2 - 0.02, y_front - 0.090, z_base + 0.045),
            (0.0, y_front - 0.090, z_base + height + 0.055),
            (width / 2 + 0.02, y_front - 0.090, z_base + 0.045),
        ],
        0.018,
        blue_outline,
        collection,
    )

    # Build a true projecting gable roof that continues backward into the main
    # roof rather than ending as a flat triangular signboard.
    roof_front_y = y_front - 0.105
    roof_back_y = 0.42
    eave_x = width / 2 + 0.13
    eave_z = z_base + 0.08
    ridge_z = z_base + height + 0.16
    slope_length = math.hypot(eave_x, ridge_z - eave_z)
    slope_angle = math.atan2(ridge_z - eave_z, eave_x)
    roof_depth = roof_back_y - roof_front_y
    plate_thickness = 0.055

    add_rotated_box_y(
        "Pediment left backward gable roof",
        (-eave_x / 2.0, (roof_front_y + roof_back_y) / 2.0, (eave_z + ridge_z) / 2.0),
        (slope_length, roof_depth, plate_thickness),
        -slope_angle,
        roof_material,
        0.010,
        collection,
    )
    add_rotated_box_y(
        "Pediment right backward gable roof",
        (eave_x / 2.0, (roof_front_y + roof_back_y) / 2.0, (eave_z + ridge_z) / 2.0),
        (slope_length, roof_depth, plate_thickness),
        slope_angle,
        roof_material,
        0.010,
        collection,
    )
    add_poly_curve(
        "Pediment front blue roof edges",
        [
            (-eave_x, roof_front_y - 0.018, eave_z),
            (0.0, roof_front_y - 0.018, ridge_z),
            (eave_x, roof_front_y - 0.018, eave_z),
        ],
        0.030,
        blue_outline,
        collection,
    )
    add_poly_curve(
        "Pediment gable ridge cap",
        [(0.0, roof_front_y, ridge_z), (0.0, roof_back_y, ridge_z)],
        0.030,
        blue_outline,
        collection,
    )

    window_z = z_base + 0.73
    glass_radius = 0.238
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=64,
        radius=glass_radius,
        depth=0.055,
        location=(0.0, y_front - 0.054, window_z),
        rotation=(math.radians(90.0), 0.0, 0.0),
    )
    round_glass = bpy.context.object
    round_glass.name = "Pediment circular window glass"
    round_glass.data.materials.append(glass)
    move_to_collection(round_glass, collection)

    # The cross reaches the full glazing diameter.  The rings overlap its ends,
    # producing the same clean construction used by the rectangular windows.
    cross_span = glass_radius * 2.02
    add_box(
        "Pediment window vertical muntin",
        (0.0, y_front - 0.115, window_z),
        (0.047, 0.030, cross_span),
        trim,
        0.004,
        collection,
    )
    add_box(
        "Pediment window horizontal muntin",
        (0.0, y_front - 0.116, window_z),
        (cross_span, 0.030, 0.047),
        trim,
        0.004,
        collection,
    )

    for index, (major_radius, minor_radius, y_offset, material) in enumerate(
        (
            (0.294, 0.044, -0.080, trim),
            (0.355, 0.042, -0.087, blue_outline),
        ),
        start=1,
    ):
        bpy.ops.mesh.primitive_torus_add(
            major_radius=major_radius,
            minor_radius=minor_radius,
            major_segments=64,
            minor_segments=12,
            location=(0.0, y_front + y_offset, window_z),
            rotation=(math.radians(90.0), 0.0, 0.0),
        )
        ring = bpy.context.object
        ring.name = f"Pediment circular window ring {index}"
        ring.data.materials.append(material)
        move_to_collection(ring, collection)


# -----------------------------------------------------------------------------
# HOUSE ASSEMBLY
# -----------------------------------------------------------------------------


def validate_symmetry() -> None:
    epsilon = 1e-9
    assert abs(UPPER_WINDOW_X[0] + UPPER_WINDOW_X[-1]) < epsilon
    assert abs(UPPER_WINDOW_X[1] + UPPER_WINDOW_X[-2]) < epsilon
    assert UPPER_WINDOW_X[2] == 0.0
    assert abs(LOWER_WINDOW_X[0] + LOWER_WINDOW_X[1]) < epsilon
    assert abs((UPPER_WINDOW_X[0] - UPPER_WINDOW_WIDTH / 2.0) - (LOWER_WINDOW_X[0] - LOWER_WINDOW_WIDTH / 2.0)) < epsilon
    assert abs((UPPER_WINDOW_X[1] + UPPER_WINDOW_WIDTH / 2.0) - (LOWER_WINDOW_X[0] + LOWER_WINDOW_WIDTH / 2.0)) < epsilon
    assert abs((UPPER_WINDOW_X[3] - UPPER_WINDOW_WIDTH / 2.0) - (LOWER_WINDOW_X[1] - LOWER_WINDOW_WIDTH / 2.0)) < epsilon
    assert abs((UPPER_WINDOW_X[4] + UPPER_WINDOW_WIDTH / 2.0) - (LOWER_WINDOW_X[1] + LOWER_WINDOW_WIDTH / 2.0)) < epsilon


def build_house() -> None:
    validate_symmetry()
    clear_scene()
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    architecture = create_collection("Architecture")
    windows_collection = create_collection("Windows")
    door_collection = create_collection("Door")
    roof_collection = create_collection("Roof")
    lighting_collection = create_collection("Lighting")
    world_metadata = create_collection("WORLD_METADATA")

    wall_material = make_material("Warm cream stucco", CREAM, roughness=0.76)
    trim_material = make_material("Cream limestone trim", TRIM_CREAM, roughness=0.64)
    pediment_inset_material = make_material("Pediment inset stone", PEDIMENT_INSET, roughness=0.72)
    architectural_line_material = make_material("Architectural recessed outline", ARCHITECTURAL_LINE, roughness=0.78)
    glass_material = make_material("Near black window glass", WINDOW_GLASS, roughness=0.30)
    door_material = make_wood_material("Procedural dark mahogany")
    door_inset_material = make_material("Deep recessed mahogany", DOOR_WOOD_DARK, roughness=0.55)
    gold_material = make_gold_material("Polished shaded warm gold")

    roof_shell_material = make_slate_material("Dark blue-green roof shell", ROOF_BASE)
    slate_materials = (
        make_slate_material("Blue-green slate A", ROOF_SLATE_1),
        make_slate_material("Blue-green slate B", ROOF_SLATE_2),
        make_slate_material("Blue-green slate C", ROOF_SLATE_3),
    )
    roof_edge_material = make_material("Near-black roof edges", ROOF_EDGE, roughness=0.72)

    wall_front_y = -HOUSE_DEPTH / 2.0
    ground_center_z = GROUND_FLOOR_HEIGHT / 2.0
    upper_center_z = GROUND_FLOOR_HEIGHT + UPPER_FLOOR_HEIGHT / 2.0
    roof_base_z = GROUND_FLOOR_HEIGHT + UPPER_FLOOR_HEIGHT

    add_box(
        "Perfectly symmetrical mansion body",
        (0.0, 0.0, (GROUND_FLOOR_HEIGHT + UPPER_FLOOR_HEIGHT) / 2.0),
        (HOUSE_WIDTH, HOUSE_DEPTH, GROUND_FLOOR_HEIGHT + UPPER_FLOOR_HEIGHT),
        wall_material,
        bevel=0.045,
        collection=architecture,
    )

    # Classical horizontal bands.
    add_box("Base plinth", (0.0, wall_front_y - 0.10, 0.22), (HOUSE_WIDTH + 0.12, 0.23, 0.42), trim_material, 0.032, architecture)
    add_box("Lower floor cornice", (0.0, wall_front_y - 0.12, GROUND_FLOOR_HEIGHT - 0.08), (HOUSE_WIDTH + 0.18, 0.24, 0.16), trim_material, 0.028, architecture)
    add_box("Upper floor cornice", (0.0, wall_front_y - 0.13, GROUND_FLOOR_HEIGHT + 0.08), (HOUSE_WIDTH + 0.20, 0.26, 0.11), trim_material, 0.024, architecture)
    # Its 0.20-unit height now ends exactly at roof_base_z, flush with the top of the house.
    add_box("Roof cornice lower", (0.0, wall_front_y - 0.13, roof_base_z - 0.10), (HOUSE_WIDTH + 0.42, 0.28, 0.20), trim_material, 0.032, architecture)

    # Mirrored pilasters.
    for x in (-2.05, 2.05):
        add_box(f"Upper pilaster {x:+.2f}", (x, wall_front_y - 0.075, upper_center_z), (0.20, 0.17, UPPER_FLOOR_HEIGHT - 0.12), trim_material, 0.016, architecture)
        add_box(f"Lower pilaster {x:+.2f}", (x, wall_front_y - 0.075, ground_center_z), (0.20, 0.17, GROUND_FLOOR_HEIGHT - 0.30), trim_material, 0.016, architecture)

    # Five top windows share exactly the same parameters and computed alignment.
    for index, x in enumerate(UPPER_WINDOW_X, start=1):
        create_window(
            f"Upper window {index}",
            x,
            UPPER_WINDOW_Z,
            UPPER_WINDOW_WIDTH,
            UPPER_WINDOW_HEIGHT,
            3,
            4,
            wall_front_y,
            trim_material,
            glass_material,
            windows_collection,
        )

    # Lower windows are centered inside the mirrored left and right architectural bays.
    for index, x in enumerate(LOWER_WINDOW_X, start=1):
        create_window(
            f"Lower window {index}",
            x,
            LOWER_WINDOW_Z,
            LOWER_WINDOW_WIDTH,
            LOWER_WINDOW_HEIGHT,
            8,
            4,
            wall_front_y,
            trim_material,
            glass_material,
            windows_collection,
        )

    create_door(door_collection, wall_front_y, trim_material, door_material, door_inset_material, gold_material)

    # Centered, restrained stairs.
    stair_specs = (
        (5.48, 0.70, 0.15, 0.075, wall_front_y - 0.82),
        (4.84, 0.58, 0.15, 0.220, wall_front_y - 0.59),
        (4.20, 0.46, 0.15, 0.365, wall_front_y - 0.39),
    )
    for index, (width, depth, height, z, y) in enumerate(stair_specs, start=1):
        add_box(f"Centered step {index}", (0.0, y, z), (width, depth, height), trim_material, 0.030, architecture)

    create_roof(roof_collection, roof_shell_material, slate_materials, roof_edge_material, roof_base_z)
    create_pediment(architecture, trim_material, pediment_inset_material, slate_materials[0], glass_material, roof_shell_material, wall_front_y, roof_base_z)

    # A thin continuous blue-green fascia crosses in front of the pediment base,
    # matching the strip beneath the rest of the roof and hiding the unwanted
    # beige vertical seams at the pediment corners.
    add_box(
        "Continuous blue-green roof fascia",
        (0.0, wall_front_y - 0.575, roof_base_z + 0.035),
        (HOUSE_WIDTH + 0.58, 0.090, 0.090),
        slate_materials[0],
        0.010,
        roof_collection,
    )

    # Orthographic camera gives the desired 2D facade appearance.
    camera_data = bpy.data.cameras.new("Orthographic website camera")
    camera = bpy.data.objects.new("Orthographic website camera", camera_data)
    bpy.context.scene.collection.objects.link(camera)
    camera.location = (0.0, -23.2, 5.22)
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 16.65
    look_at(camera, (0.0, 0.0, 3.55))
    camera["world_view_id"] = "exterior"
    bpy.context.scene.camera = camera

    # Website interaction geometry lives in Blender beside the visual scene.
    # These invisible volumes are projected through the active camera by
    # blender/world/export_rendered_world.py, so browser hotspots never need
    # hand-tuned pixel coordinates after the house or camera changes.
    hotspot_front_y = wall_front_y - 0.72
    for hotspot_id, x in zip(
        ("red-room", "green-room", "orange-room", "blue-room", "purple-room"),
        UPPER_WINDOW_X,
    ):
        add_world_hotspot(
            hotspot_id,
            location=(x, hotspot_front_y, UPPER_WINDOW_Z),
            dimensions=(UPPER_WINDOW_WIDTH, 0.06, UPPER_WINDOW_HEIGHT),
            collection=world_metadata,
        )

    for hotspot_id, x in (("ballroom", LOWER_WINDOW_X[0]), ("museum", LOWER_WINDOW_X[1])):
        add_world_hotspot(
            hotspot_id,
            location=(x, hotspot_front_y, LOWER_WINDOW_Z),
            dimensions=(LOWER_WINDOW_WIDTH, 0.06, LOWER_WINDOW_HEIGHT),
            collection=world_metadata,
        )

    add_world_hotspot(
        "about",
        location=(0.0, hotspot_front_y, 1.58),
        dimensions=(1.82, 0.06, 2.62),
        collection=world_metadata,
    )
    add_world_hotspot(
        "graph",
        location=(0.0, hotspot_front_y, roof_base_z + 0.73),
        dimensions=(0.76, 0.06, 0.76),
        collection=world_metadata,
    )

    # Symmetrical lighting prevents one side/window from appearing different.
    def add_area(
        name: str,
        location: tuple[float, float, float],
        energy: float,
        size: float,
        target: tuple[float, float, float],
    ) -> None:
        light_data = bpy.data.lights.new(name=name, type="AREA")
        light_data.energy = energy
        light_data.shape = "DISK"
        light_data.size = size
        light = bpy.data.objects.new(name, light_data)
        lighting_collection.objects.link(light)
        light.location = location
        look_at(light, target)

    add_area("Left symmetrical key", (-6.5, -9.5, 8.5), 900.0, 6.5, (0.0, 0.0, 3.2))
    add_area("Right symmetrical key", (6.5, -9.5, 8.5), 900.0, 6.5, (0.0, 0.0, 3.2))
    add_area("Centered frontal fill", (0.0, -11.0, 6.0), 620.0, 7.0, (0.0, 0.0, 3.2))
    add_area("Centered roof fill", (0.0, -1.0, 12.0), 850.0, 5.5, (0.0, 0.0, 5.6))

    scene = bpy.context.scene
    selected_engine = set_best_eevee(scene)
    print(f"House preview render engine: {selected_engine}")

    scene.render.resolution_x = RENDER_WIDTH
    scene.render.resolution_y = RENDER_HEIGHT
    scene.render.resolution_percentage = RENDER_PERCENTAGE
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = True
    scene.render.filepath = os.path.join(OUTPUT_DIR, RENDER_NAME)

    scene.render.use_freestyle = True
    scene.render.line_thickness = LINE_THICKNESS
    try:
        line_style = bpy.data.linestyles.get("LineStyle")
        if line_style is not None:
            line_style.color = (0.010, 0.009, 0.008)
            line_style.thickness = LINE_THICKNESS
    except Exception:
        pass

    scene.world.color = (0.025, 0.025, 0.025)
    try:
        scene.view_settings.look = "AgX - Medium High Contrast"
    except Exception:
        pass

    bpy.ops.object.select_all(action="DESELECT")

    blend_path = os.path.join(OUTPUT_DIR, BLEND_NAME)
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)
    bpy.ops.render.render(write_still=True)

    print("\nHouse v11 generation complete.")
    print(f"Blend file: {blend_path}")
    print(f"Transparent render: {scene.render.filepath}\n")


if __name__ == "__main__":
    build_house()