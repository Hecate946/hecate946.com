"""Build the approved Hecate946 2.5D ballroom entirely from Python.

Approved visual target
----------------------
The scene intentionally follows ``reference/approved-ballroom-build-sheet.png``:

- windowless Georgian / restrained Neoclassical ballroom
- one centered dark arched double door on the back wall
- NO side door
- NO wall sconces / lights inside framed wall panels
- warm ivory plaster and slightly lighter architectural trim
- dark teal wall-to-wall carpet
- tiny, low-contrast muted-gold diamond field + simple double border
- one centered brass ring chandelier
- warm recessed ceiling glow plus invisible "magical" architectural lighting
- empty floor: no piano or filler props in this first canonical ballroom view

The room is a 2.5D stage set. Blender owns the finished appearance; the browser
only displays the authored still and projected hotspot metadata.

Build through the website pipeline:

    HECATE_BALLROOM_QUALITY=PREVIEW npm run ballroom:render
    HECATE_BALLROOM_QUALITY=WEB     npm run ballroom:render
    HECATE_BALLROOM_QUALITY=FINAL   npm run ballroom:render

Outputs beside this file:

    ballroom-25d.blend
    ballroom-25d.png
"""

from __future__ import annotations

import math
import os
from pathlib import Path
from typing import Iterable, Sequence

import bpy
from mathutils import Vector


# =============================================================================
# EASY SETTINGS
# =============================================================================

SCRIPT_VERSION = "ballroom-cycles-realism-v9.1-blender-5.2-2026-08-07"
SCRIPT_DIR = Path(__file__).resolve().parent
REFERENCE_PATH = SCRIPT_DIR / "reference" / "ballroom-target-reference.png"
BLEND_PATH = SCRIPT_DIR / "ballroom-25d.blend"
ESTABLISHING_RENDER = SCRIPT_DIR / "ballroom-25d.png"


def env_flag(name: str, default: bool) -> bool:
    fallback = "1" if default else "0"
    return os.environ.get(name, fallback).strip().lower() not in {"0", "false", "no"}


QUALITY = str(
    globals().get("QUALITY", os.environ.get("HECATE_BALLROOM_QUALITY", "WEB"))
).strip().upper()
AUTO_RENDER = bool(globals().get("AUTO_RENDER", env_flag("HECATE_BALLROOM_RENDER", True)))
USE_GPU = bool(globals().get("USE_GPU", env_flag("HECATE_BALLROOM_GPU", True)))

QUALITY_PRESETS = {
    "PREVIEW": {"width": 1024, "height": 768, "samples": 32},
    "WEB": {"width": 2048, "height": 1536, "samples": 256},
    "FINAL": {"width": 3200, "height": 2400, "samples": 512},
}
if QUALITY not in QUALITY_PRESETS:
    raise ValueError(
        "HECATE_BALLROOM_QUALITY must be PREVIEW, WEB, or FINAL "
        f"(received {QUALITY!r})."
    )

# These proportions are deliberately stage-like and chosen to reproduce the
# approved wide establishing composition rather than to simulate a floor plan.
ROOM_WIDTH = 12.40
ROOM_DEPTH = 9.10
ROOM_HEIGHT = 5.55
WALL_THICKNESS = 0.22
BACK_Y = ROOM_DEPTH / 2
LEFT_X = -ROOM_WIDTH / 2
RIGHT_X = ROOM_WIDTH / 2

# House palette copied from blender/house/house.py.
HOUSE_CREAM = (0.70, 0.61, 0.50, 1.0)
HOUSE_TRIM = (0.88, 0.80, 0.67, 1.0)
DOOR_WOOD_DARK = (0.020, 0.006, 0.0025, 1.0)
DOOR_WOOD_LIGHT = (0.105, 0.032, 0.012, 1.0)


# =============================================================================
# SCENE / COLLECTION HELPERS
# =============================================================================


def clear_scene() -> None:
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)

    for datablocks in (
        bpy.data.meshes,
        bpy.data.curves,
        bpy.data.cameras,
        bpy.data.lights,
        bpy.data.materials,
    ):
        for block in list(datablocks):
            if block.users == 0:
                datablocks.remove(block)


def collection(name: str, parent: bpy.types.Collection | None = None) -> bpy.types.Collection:
    existing = bpy.data.collections.get(name)
    if existing is not None:
        return existing
    result = bpy.data.collections.new(name)
    (parent or bpy.context.scene.collection).children.link(result)
    return result


def move_to_collection(obj: bpy.types.Object, target: bpy.types.Collection) -> None:
    for current in list(obj.users_collection):
        current.objects.unlink(obj)
    target.objects.link(obj)


def set_input(node: bpy.types.Node, names: Sequence[str], value) -> None:
    for name in names:
        socket = node.inputs.get(name)
        if socket is not None:
            socket.default_value = value
            return


def target_object(obj: bpy.types.Object, point: Iterable[float]) -> None:
    direction = Vector(point) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def add_bevel(obj: bpy.types.Object, width: float, segments: int = 3) -> None:
    if width <= 0:
        return
    modifier = obj.modifiers.new("Soft architectural edges", "BEVEL")
    modifier.width = width
    modifier.segments = segments
    modifier.limit_method = "ANGLE"


def add_box(
    name: str,
    location: tuple[float, float, float],
    dimensions: tuple[float, float, float],
    mat: bpy.types.Material,
    target: bpy.types.Collection,
    *,
    bevel: float = 0.0,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(mat)
    add_bevel(obj, bevel)
    move_to_collection(obj, target)
    return obj


def add_cylinder(
    name: str,
    location: tuple[float, float, float],
    radius: float,
    depth: float,
    mat: bpy.types.Material,
    target: bpy.types.Collection,
    *,
    vertices: int = 32,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=vertices,
        radius=radius,
        depth=depth,
        location=location,
    )
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(mat)
    for polygon in obj.data.polygons:
        polygon.use_smooth = True
    move_to_collection(obj, target)
    return obj


def add_cylinder_between(
    name: str,
    start: tuple[float, float, float],
    end: tuple[float, float, float],
    radius: float,
    mat: bpy.types.Material,
    target: bpy.types.Collection,
    *,
    vertices: int = 20,
) -> bpy.types.Object:
    a = Vector(start)
    b = Vector(end)
    direction = b - a
    length = direction.length
    midpoint = (a + b) * 0.5
    obj = add_cylinder(name, tuple(midpoint), radius, length, mat, target, vertices=vertices)
    obj.rotation_euler = direction.to_track_quat("Z", "Y").to_euler()
    return obj


def add_uv_sphere(
    name: str,
    location: tuple[float, float, float],
    radius: float,
    mat: bpy.types.Material,
    target: bpy.types.Collection,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=24,
        ring_count=12,
        radius=radius,
        location=location,
    )
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(mat)
    for polygon in obj.data.polygons:
        polygon.use_smooth = True
    move_to_collection(obj, target)
    return obj


def add_torus(
    name: str,
    location: tuple[float, float, float],
    major_radius: float,
    minor_radius: float,
    mat: bpy.types.Material,
    target: bpy.types.Collection,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_torus_add(
        major_segments=64,
        minor_segments=12,
        location=location,
        major_radius=major_radius,
        minor_radius=minor_radius,
    )
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(mat)
    for polygon in obj.data.polygons:
        polygon.use_smooth = True
    move_to_collection(obj, target)
    return obj


# =============================================================================
# MATERIALS
# =============================================================================


def simple_material(
    name: str,
    color: tuple[float, float, float, float],
    *,
    roughness: float = 0.55,
    metallic: float = 0.0,
) -> bpy.types.Material:
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf is not None:
        set_input(bsdf, ("Base Color",), color)
        set_input(bsdf, ("Roughness",), roughness)
        set_input(bsdf, ("Metallic",), metallic)
        set_input(bsdf, ("Specular IOR Level", "Specular"), 0.30)
    return mat


def make_plaster(name: str, base: tuple[float, float, float, float]) -> bpy.types.Material:
    """Fine architectural plaster: broad tonal variation plus imperceptible micro-bump."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    texcoord = nodes.new("ShaderNodeTexCoord")
    broad = nodes.new("ShaderNodeTexNoise")
    micro = nodes.new("ShaderNodeTexNoise")
    ramp = nodes.new("ShaderNodeValToRGB")
    bump = nodes.new("ShaderNodeBump")

    broad.inputs["Scale"].default_value = 0.95
    broad.inputs["Detail"].default_value = 0.65
    broad.inputs["Roughness"].default_value = 0.28
    micro.inputs["Scale"].default_value = 48.0
    micro.inputs["Detail"].default_value = 1.5
    micro.inputs["Roughness"].default_value = 0.48

    dark = tuple(max(0.0, channel * 0.965) for channel in base[:3]) + (1.0,)
    light = tuple(min(1.0, channel * 1.025) for channel in base[:3]) + (1.0,)
    ramp.color_ramp.elements[0].color = dark
    ramp.color_ramp.elements[1].color = light
    ramp.color_ramp.elements[0].position = 0.28
    ramp.color_ramp.elements[1].position = 0.74

    set_input(bsdf, ("Roughness",), 0.72)
    set_input(bsdf, ("Specular IOR Level", "Specular"), 0.22)
    bump.inputs["Strength"].default_value = 0.055
    bump.inputs["Distance"].default_value = 0.0025

    links.new(texcoord.outputs["Generated"], broad.inputs["Vector"])
    links.new(texcoord.outputs["Generated"], micro.inputs["Vector"])
    links.new(broad.outputs["Fac"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(micro.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


def make_trim(name: str, base: tuple[float, float, float, float]) -> bpy.types.Material:
    """Painted/limestone trim with just enough texture to catch grazing light."""
    mat = make_plaster(name, base)
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf is not None:
        set_input(bsdf, ("Roughness",), 0.58)
        set_input(bsdf, ("Specular IOR Level", "Specular"), 0.28)
    return mat


def make_emission(name: str, color: tuple[float, float, float, float], strength: float) -> bpy.types.Material:
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    emission = nodes.new("ShaderNodeEmission")
    emission.inputs["Color"].default_value = color
    emission.inputs["Strength"].default_value = strength
    links.new(emission.outputs["Emission"], out.inputs["Surface"])
    return mat

def make_carpet(name: str) -> bpy.types.Material:
    """Dark teal wool carpet with soft fiber-scale bump and restrained sheen."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    texcoord = nodes.new("ShaderNodeTexCoord")
    broad = nodes.new("ShaderNodeTexNoise")
    fiber = nodes.new("ShaderNodeTexNoise")
    ramp = nodes.new("ShaderNodeValToRGB")
    bump = nodes.new("ShaderNodeBump")

    broad.inputs["Scale"].default_value = 2.6
    broad.inputs["Detail"].default_value = 1.2
    broad.inputs["Roughness"].default_value = 0.38
    fiber.inputs["Scale"].default_value = 125.0
    fiber.inputs["Detail"].default_value = 2.0
    fiber.inputs["Roughness"].default_value = 0.62
    ramp.color_ramp.elements[0].color = (0.009, 0.055, 0.050, 1.0)
    ramp.color_ramp.elements[1].color = (0.026, 0.125, 0.112, 1.0)
    ramp.color_ramp.elements[0].position = 0.26
    ramp.color_ramp.elements[1].position = 0.76

    set_input(bsdf, ("Roughness",), 0.91)
    set_input(bsdf, ("Specular IOR Level", "Specular"), 0.14)
    set_input(bsdf, ("Sheen Weight", "Sheen"), 0.16)
    set_input(bsdf, ("Sheen Roughness",), 0.72)
    bump.inputs["Strength"].default_value = 0.12
    bump.inputs["Distance"].default_value = 0.0018

    links.new(texcoord.outputs["Generated"], broad.inputs["Vector"])
    links.new(texcoord.outputs["Generated"], fiber.inputs["Vector"])
    links.new(broad.outputs["Fac"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(fiber.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat

def make_wood(name: str) -> bpy.types.Material:
    """Use the same restrained mahogany language as the exterior house door."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    texcoord = nodes.new("ShaderNodeTexCoord")
    mapping = nodes.new("ShaderNodeMapping")
    wave = nodes.new("ShaderNodeTexWave")
    noise = nodes.new("ShaderNodeTexNoise")
    mix = nodes.new("ShaderNodeMixRGB")
    ramp = nodes.new("ShaderNodeValToRGB")
    rough = nodes.new("ShaderNodeValToRGB")
    bump = nodes.new("ShaderNodeBump")

    mapping.inputs["Scale"].default_value = (5.5, 1.4, 0.50)
    wave.wave_type = "BANDS"
    wave.bands_direction = "X"
    wave.inputs["Scale"].default_value = 16.0
    wave.inputs["Distortion"].default_value = 2.1
    noise.inputs["Scale"].default_value = 7.0
    noise.inputs["Detail"].default_value = 4.0
    noise.inputs["Roughness"].default_value = 0.68
    mix.blend_type = "MULTIPLY"
    mix.inputs[0].default_value = 0.70

    ramp.color_ramp.elements[0].position = 0.18
    ramp.color_ramp.elements[0].color = DOOR_WOOD_DARK
    ramp.color_ramp.elements[1].position = 0.82
    ramp.color_ramp.elements[1].color = DOOR_WOOD_LIGHT
    rough.color_ramp.elements[0].color = (0.34, 0.34, 0.34, 1.0)
    rough.color_ramp.elements[1].color = (0.56, 0.56, 0.56, 1.0)

    set_input(bsdf, ("Specular IOR Level", "Specular"), 0.30)
    bump.inputs["Strength"].default_value = 0.07
    bump.inputs["Distance"].default_value = 0.006

    links.new(texcoord.outputs["Generated"], mapping.inputs["Vector"])
    links.new(mapping.outputs["Vector"], wave.inputs["Vector"])
    links.new(mapping.outputs["Vector"], noise.inputs["Vector"])
    links.new(wave.outputs["Color"], mix.inputs[1])
    links.new(noise.outputs["Fac"], mix.inputs[2])
    links.new(mix.outputs["Color"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(noise.outputs["Fac"], rough.inputs["Fac"])
    links.new(rough.outputs["Color"], bsdf.inputs["Roughness"])
    links.new(noise.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


def make_brass(name: str) -> bpy.types.Material:
    return simple_material(name, (0.30, 0.135, 0.025, 1.0), roughness=0.22, metallic=0.88)


def make_candle(name: str) -> bpy.types.Material:
    mat = simple_material(name, (0.91, 0.82, 0.65, 1.0), roughness=0.48)
    return mat


def make_flame(name: str) -> bpy.types.Material:
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    emission = nodes.new("ShaderNodeEmission")
    emission.inputs["Color"].default_value = (1.0, 0.52, 0.12, 1.0)
    emission.inputs["Strength"].default_value = 12.0
    links.new(emission.outputs["Emission"], out.inputs["Surface"])
    return mat


# =============================================================================
# ARCHITECTURAL GEOMETRY
# =============================================================================


def extruded_arch_xz(
    name: str,
    center_x: float,
    center_y: float,
    bottom_z: float,
    width: float,
    straight_height: float,
    depth: float,
    mat: bpy.types.Material,
    target: bpy.types.Collection,
    *,
    segments: int = 32,
) -> bpy.types.Object:
    """Filled arch silhouette facing the camera and extruded along Y."""
    half = width / 2
    points: list[tuple[float, float]] = [(-half, 0.0), (half, 0.0), (half, straight_height)]
    for index in range(1, segments + 1):
        angle = math.pi * index / segments
        points.append((math.cos(angle) * half, straight_height + math.sin(angle) * half))

    y0 = center_y - depth / 2
    y1 = center_y + depth / 2
    count = len(points)
    vertices = [(center_x + x, y0, bottom_z + z) for x, z in points]
    vertices += [(center_x + x, y1, bottom_z + z) for x, z in points]
    faces: list[tuple[int, ...]] = [
        tuple(range(count - 1, -1, -1)),
        tuple(range(count, count * 2)),
    ]
    for index in range(count):
        nxt = (index + 1) % count
        faces.append((index, nxt, count + nxt, count + index))

    mesh = bpy.data.meshes.new(f"{name}Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    target.objects.link(obj)
    obj.data.materials.append(mat)
    add_bevel(obj, 0.012, 2)
    return obj


def add_back_molding_rect(
    name: str,
    center_x: float,
    width: float,
    lower: float,
    upper: float,
    y: float,
    mat: bpy.types.Material,
    target: bpy.types.Collection,
    *,
    strip: float = 0.055,
    depth: float = 0.050,
) -> None:
    zmid = (lower + upper) / 2
    add_box(f"{name} left", (center_x - width / 2, y, zmid), (strip, depth, upper - lower), mat, target, bevel=0.012)
    add_box(f"{name} right", (center_x + width / 2, y, zmid), (strip, depth, upper - lower), mat, target, bevel=0.012)
    add_box(f"{name} bottom", (center_x, y, lower), (width, depth, strip), mat, target, bevel=0.012)
    add_box(f"{name} top", (center_x, y, upper), (width, depth, strip), mat, target, bevel=0.012)


def add_side_molding_rect(
    name: str,
    side: int,
    center_y: float,
    span: float,
    lower: float,
    upper: float,
    x: float,
    mat: bpy.types.Material,
    target: bpy.types.Collection,
    *,
    strip: float = 0.055,
    depth: float = 0.050,
) -> None:
    zmid = (lower + upper) / 2
    add_box(f"{name} near", (x, center_y - span / 2, zmid), (depth, strip, upper - lower), mat, target, bevel=0.012)
    add_box(f"{name} far", (x, center_y + span / 2, zmid), (depth, strip, upper - lower), mat, target, bevel=0.012)
    add_box(f"{name} bottom", (x, center_y, lower), (depth, span, strip), mat, target, bevel=0.012)
    add_box(f"{name} top", (x, center_y, upper), (depth, span, strip), mat, target, bevel=0.012)


def add_back_pilaster(
    name: str,
    x: float,
    y: float,
    trim: bpy.types.Material,
    target: bpy.types.Collection,
) -> None:
    """Restrained fluted pilaster matching the reference wall rhythm."""
    add_box(f"{name} plinth", (x, y, 0.23), (0.46, 0.15, 0.42), trim, target, bevel=0.018)
    add_box(f"{name} base lower", (x, y - 0.006, 0.48), (0.38, 0.15, 0.14), trim, target, bevel=0.014)
    add_box(f"{name} base upper", (x, y - 0.010, 0.61), (0.31, 0.14, 0.10), trim, target, bevel=0.012)
    add_box(f"{name} shaft", (x, y, 2.62), (0.27, 0.12, 3.86), trim, target, bevel=0.012)
    # Four shallow raised fillets create the fluted reading at normal website scale.
    for index, dx in enumerate((-0.082, -0.027, 0.027, 0.082), 1):
        add_box(
            f"{name} flute {index}",
            (x + dx, y - 0.067, 2.62),
            (0.018, 0.018, 3.42),
            trim,
            target,
            bevel=0.006,
        )
    add_box(f"{name} neck lower", (x, y - 0.006, 4.55), (0.32, 0.14, 0.11), trim, target, bevel=0.012)
    add_box(f"{name} neck upper", (x, y - 0.010, 4.66), (0.37, 0.15, 0.10), trim, target, bevel=0.012)
    add_box(f"{name} capital", (x, y - 0.014, 4.76), (0.47, 0.17, 0.13), trim, target, bevel=0.018)
    add_box(f"{name} abacus", (x, y - 0.017, 4.86), (0.53, 0.19, 0.08), trim, target, bevel=0.014)


def add_side_pilaster(
    name: str,
    side: int,
    y: float,
    x: float,
    trim: bpy.types.Material,
    target: bpy.types.Collection,
) -> None:
    add_box(f"{name} plinth", (x, y, 0.23), (0.15, 0.46, 0.42), trim, target, bevel=0.018)
    add_box(f"{name} base lower", (x - side * 0.006, y, 0.48), (0.15, 0.38, 0.14), trim, target, bevel=0.014)
    add_box(f"{name} base upper", (x - side * 0.010, y, 0.61), (0.14, 0.31, 0.10), trim, target, bevel=0.012)
    add_box(f"{name} shaft", (x, y, 2.62), (0.12, 0.27, 3.86), trim, target, bevel=0.012)
    for index, dy in enumerate((-0.082, -0.027, 0.027, 0.082), 1):
        add_box(
            f"{name} flute {index}",
            (x - side * 0.067, y + dy, 2.62),
            (0.018, 0.018, 3.42),
            trim,
            target,
            bevel=0.006,
        )
    add_box(f"{name} neck lower", (x - side * 0.006, y, 4.55), (0.14, 0.32, 0.11), trim, target, bevel=0.012)
    add_box(f"{name} neck upper", (x - side * 0.010, y, 4.66), (0.15, 0.37, 0.10), trim, target, bevel=0.012)
    add_box(f"{name} capital", (x - side * 0.014, y, 4.76), (0.17, 0.47, 0.13), trim, target, bevel=0.018)
    add_box(f"{name} abacus", (x - side * 0.017, y, 4.86), (0.19, 0.53, 0.08), trim, target, bevel=0.014)

def add_perimeter_rail(
    name: str,
    z: float,
    height: float,
    depth: float,
    mat: bpy.types.Material,
    target: bpy.types.Collection,
) -> None:
    back_surface = BACK_Y - WALL_THICKNESS / 2 - depth / 2
    side_surface = ROOM_WIDTH / 2 - WALL_THICKNESS / 2 - depth / 2
    add_box(f"{name} back", (0, back_surface, z), (ROOM_WIDTH - 0.08, depth, height), mat, target, bevel=min(0.018, height * 0.2))
    add_box(f"{name} left", (-side_surface, 0, z), (depth, ROOM_DEPTH, height), mat, target, bevel=min(0.018, height * 0.2))
    add_box(f"{name} right", (side_surface, 0, z), (depth, ROOM_DEPTH, height), mat, target, bevel=min(0.018, height * 0.2))


def build_carpet(
    target: bpy.types.Collection,
    carpet: bpy.types.Material,
    gold: bpy.types.Material,
) -> None:
    add_box(
        "Dark teal wall-to-wall carpet",
        (0.0, 0.0, 0.025),
        (ROOM_WIDTH - 0.04, ROOM_DEPTH - 0.04, 0.050),
        carpet,
        target,
        bevel=0.012,
    )

    z = 0.056
    outer_x = ROOM_WIDTH / 2 - 0.23
    outer_y = ROOM_DEPTH / 2 - 0.23
    inner_x = outer_x - 0.14
    inner_y = outer_y - 0.14
    for label, x, y, thickness in (
        ("outer", outer_x, outer_y, 0.020),
        ("inner", inner_x, inner_y, 0.012),
    ):
        add_box(f"Carpet {label} border L", (-x, 0, z), (thickness, y * 2, 0.008), gold, target)
        add_box(f"Carpet {label} border R", (x, 0, z), (thickness, y * 2, 0.008), gold, target)
        add_box(f"Carpet {label} border F", (0, -y, z), (x * 2, thickness, 0.008), gold, target)
        add_box(f"Carpet {label} border B", (0, y, z), (x * 2, thickness, 0.008), gold, target)

    # All tiny motifs live in one mesh, so the approved patterned field stays cheap.
    verts: list[tuple[float, float, float]] = []
    faces: list[tuple[int, int, int, int]] = []
    size = 0.030
    x_step = 0.60
    y_step = 0.58
    x_limit = inner_x - 0.28
    y_limit = inner_y - 0.28
    row = 0
    y = -y_limit
    while y <= y_limit + 1e-6:
        offset = 0.0 if row % 2 == 0 else x_step * 0.5
        x = -x_limit + offset
        while x <= x_limit + 1e-6:
            base = len(verts)
            verts.extend([
                (x, y - size, z + 0.003),
                (x + size, y, z + 0.003),
                (x, y + size, z + 0.003),
                (x - size, y, z + 0.003),
            ])
            faces.append((base, base + 1, base + 2, base + 3))
            x += x_step
        y += y_step
        row += 1

    mesh = bpy.data.meshes.new("Carpet sparse diamond field mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new("Carpet sparse muted-gold diamond field", mesh)
    target.objects.link(obj)
    obj.data.materials.append(gold)


def build_door(
    target: bpy.types.Collection,
    plaster_inset: bpy.types.Material,
    trim: bpy.types.Material,
    wood: bpy.types.Material,
    wood_dark: bpy.types.Material,
    brass: bpy.types.Material,
) -> None:
    wall_front = BACK_Y - WALL_THICKNESS / 2
    # Nested filled arch silhouettes create a clean, layered surround with no booleans.
    extruded_arch_xz("Door outer cream arch", 0, wall_front - 0.030, 0.08, 2.42, 2.78, 0.12, trim, target)
    extruded_arch_xz("Door middle cream arch", 0, wall_front - 0.066, 0.105, 2.24, 2.70, 0.10, plaster_inset, target)
    extruded_arch_xz("Door inner cream arch", 0, wall_front - 0.100, 0.13, 2.08, 2.62, 0.09, trim, target)
    extruded_arch_xz("Dark mahogany arched double door", 0, wall_front - 0.140, 0.14, 1.90, 2.55, 0.08, wood, target)

    face_y = wall_front - 0.194
    # Raised arched upper panel follows the geometry of the opening instead of
    # terminating as a rectangular slab, which is what makes the reference door read.
    extruded_arch_xz("Door upper arched raised frame", 0, face_y - 0.018, 1.62, 1.62, 0.28, 0.030, wood, target, segments=40)
    extruded_arch_xz("Door upper arched recessed panel", 0, face_y - 0.040, 1.68, 1.46, 0.24, 0.024, wood_dark, target, segments=40)
    add_box("Door center seam", (0, face_y, 1.58), (0.028, 0.022, 2.88), wood_dark, target, bevel=0.004)

    # Simple raised panels: enough depth to feel real, still exactly within the scene bible.
    for side in (-1, 1):
        cx = side * 0.47
        add_box(f"Door lower panel {side:+d}", (cx, face_y - 0.012, 0.70), (0.64, 0.030, 0.76), wood_dark, target, bevel=0.022)
        add_box(f"Door middle panel {side:+d}", (cx, face_y - 0.012, 1.48), (0.64, 0.030, 0.52), wood_dark, target, bevel=0.022)
        # Thin wood rails around the lower rectangular panels.
        for label, zc, width, height in (
            ("lower", 0.70, 0.72, 0.84),
            ("middle", 1.48, 0.72, 0.60),
        ):
            t = 0.035
            add_box(f"Door {label} panel L {side:+d}", (cx - width / 2, face_y - 0.035, zc), (t, 0.030, height), wood, target, bevel=0.006)
            add_box(f"Door {label} panel R {side:+d}", (cx + width / 2, face_y - 0.035, zc), (t, 0.030, height), wood, target, bevel=0.006)
            add_box(f"Door {label} panel B {side:+d}", (cx, face_y - 0.035, zc - height / 2), (width, 0.030, t), wood, target, bevel=0.006)
            add_box(f"Door {label} panel T {side:+d}", (cx, face_y - 0.035, zc + height / 2), (width, 0.030, t), wood, target, bevel=0.006)

    for side in (-1, 1):
        x = side * 0.18
        add_cylinder(f"Door brass pull {side:+d}", (x, face_y - 0.060, 1.43), 0.018, 0.42, brass, target, vertices=24)
        add_uv_sphere(f"Door pull top cap {side:+d}", (x, face_y - 0.060, 1.64), 0.025, brass, target)
        add_uv_sphere(f"Door pull bottom cap {side:+d}", (x, face_y - 0.060, 1.22), 0.025, brass, target)


def build_architecture(
    background: bpy.types.Collection,
    foreground: bpy.types.Collection,
    plaster: bpy.types.Material,
    plaster_inset: bpy.types.Material,
    trim: bpy.types.Material,
    carpet: bpy.types.Material,
    carpet_gold: bpy.types.Material,
    wood: bpy.types.Material,
    wood_dark: bpy.types.Material,
    brass: bpy.types.Material,
    cove_emission: bpy.types.Material,
) -> None:
    # Clean stage shell: back + side walls + ceiling, deliberately no front wall.
    add_box("Back plaster wall", (0, BACK_Y, ROOM_HEIGHT / 2), (ROOM_WIDTH, WALL_THICKNESS, ROOM_HEIGHT), plaster, background, bevel=0.015)
    add_box("Left plaster wall", (LEFT_X, 0, ROOM_HEIGHT / 2), (WALL_THICKNESS, ROOM_DEPTH, ROOM_HEIGHT), plaster, background, bevel=0.015)
    add_box("Right plaster wall", (RIGHT_X, 0, ROOM_HEIGHT / 2), (WALL_THICKNESS, ROOM_DEPTH, ROOM_HEIGHT), plaster, background, bevel=0.015)
    add_box("Ballroom ceiling", (0, 0, ROOM_HEIGHT - 0.075), (ROOM_WIDTH, ROOM_DEPTH, 0.15), plaster_inset, background, bevel=0.012)

    build_carpet(foreground, carpet, carpet_gold)

    # Base / wainscot / cornice: repeated unchanged on all three visible walls.
    add_perimeter_rail("Base plinth lower", 0.18, 0.32, 0.16, trim, background)
    add_perimeter_rail("Base plinth upper", 0.43, 0.12, 0.14, trim, background)
    add_perimeter_rail("Wainscot rail lower", 1.03, 0.10, 0.11, trim, background)
    add_perimeter_rail("Wainscot rail upper", 1.18, 0.13, 0.14, trim, background)
    add_perimeter_rail("Cornice lower", 4.70, 0.12, 0.14, trim, background)
    add_perimeter_rail("Cornice bead", 4.82, 0.05, 0.10, trim, background)
    add_perimeter_rail("Cornice middle", 4.93, 0.16, 0.18, trim, background)
    add_perimeter_rail("Cornice upper", 5.10, 0.16, 0.24, trim, background)

    # Back wall pilasters and modular framed panels.
    back_detail_y = BACK_Y - WALL_THICKNESS / 2 - 0.078
    for index, x in enumerate((-5.35, -2.35, 2.35, 5.35), 1):
        add_back_pilaster(f"Back pilaster {index}", x, back_detail_y, trim, background)

    # Upper frames exactly avoid wall lights; they remain empty architectural panels.
    back_panels = (
        (-3.90, 2.22),
        (-1.62, 0.78),
        (1.62, 0.78),
        (3.90, 2.22),
    )
    for index, (x, width) in enumerate(back_panels, 1):
        add_back_molding_rect(f"Back upper panel {index}", x, width, 1.48, 4.38, back_detail_y - 0.028, trim, background)
        add_back_molding_rect(f"Back lower panel {index}", x, width, 0.35, 0.90, back_detail_y - 0.026, trim, background, strip=0.045)

    # Side walls use the same module rhythm and no side doors or sconces.
    for side in (-1, 1):
        side_detail_x = side * (ROOM_WIDTH / 2 - WALL_THICKNESS / 2 - 0.078)
        for index, y in enumerate((-3.15, 0.0, 3.15), 1):
            add_side_pilaster(f"{'Left' if side < 0 else 'Right'} pilaster {index}", side, y, side_detail_x, trim, background)
        for index, y in enumerate((-1.62, 1.62), 1):
            add_side_molding_rect(
                f"{'Left' if side < 0 else 'Right'} upper panel {index}",
                side,
                y,
                2.25,
                1.48,
                4.38,
                side_detail_x - side * 0.028,
                trim,
                background,
            )
            add_side_molding_rect(
                f"{'Left' if side < 0 else 'Right'} lower panel {index}",
                side,
                y,
                2.25,
                0.35,
                0.90,
                side_detail_x - side * 0.026,
                trim,
                background,
                strip=0.045,
            )

    # A slightly deeper ceiling tray / cove lip. The light itself stays invisible.
    add_box("Back dropped ceiling soffit", (0, BACK_Y - 0.46, 5.23), (ROOM_WIDTH - 0.18, 0.76, 0.26), trim, background, bevel=0.028)
    add_box("Left dropped ceiling soffit", (LEFT_X + 0.46, 0, 5.23), (0.76, ROOM_DEPTH - 0.18, 0.26), trim, background, bevel=0.028)
    add_box("Right dropped ceiling soffit", (RIGHT_X - 0.46, 0, 5.23), (0.76, ROOM_DEPTH - 0.18, 0.26), trim, background, bevel=0.028)
    add_box("Back cove inner lip", (0, BACK_Y - 0.86, 5.05), (ROOM_WIDTH - 1.62, 0.12, 0.18), trim, background, bevel=0.018)
    add_box("Left cove inner lip", (LEFT_X + 0.86, 0, 5.05), (0.12, ROOM_DEPTH - 1.62, 0.18), trim, background, bevel=0.018)
    add_box("Right cove inner lip", (RIGHT_X - 0.86, 0, 5.05), (0.12, ROOM_DEPTH - 1.62, 0.18), trim, background, bevel=0.018)

    # Thin continuous luminous lines are visible in the reference. These meshes are
    # physically emissive in Cycles; hidden area lights below provide clean fill.
    add_box("Back cove luminous line", (0, BACK_Y - 0.78, 5.18), (ROOM_WIDTH - 1.48, 0.045, 0.035), cove_emission, background, bevel=0.008)
    add_box("Left cove luminous line", (LEFT_X + 0.78, 0, 5.18), (0.045, ROOM_DEPTH - 1.48, 0.035), cove_emission, background, bevel=0.008)
    add_box("Right cove luminous line", (RIGHT_X - 0.78, 0, 5.18), (0.045, ROOM_DEPTH - 1.48, 0.035), cove_emission, background, bevel=0.008)

    build_door(background, plaster_inset, trim, wood, wood_dark, brass)


# =============================================================================
# CHANDELIER + LIGHTING
# =============================================================================


def build_chandelier(
    target: bpy.types.Collection,
    brass: bpy.types.Material,
    candle: bpy.types.Material,
    flame: bpy.types.Material,
) -> list[tuple[float, float, float]]:
    """Simple but properly proportioned brass ring chandelier from the reference."""
    center = (0.0, -0.08, 4.34)
    ring_radius = 0.90
    add_torus("Centered brass chandelier ring", center, ring_radius, 0.032, brass, target)
    add_torus("Chandelier inner ring detail", center, ring_radius - 0.075, 0.010, brass, target)

    add_cylinder("Chandelier ceiling rose", (0, -0.08, 5.32), 0.16, 0.07, brass, target, vertices=40)
    add_cylinder("Chandelier lower hub", (0, -0.08, 4.34), 0.075, 0.13, brass, target, vertices=32)

    support_z = 5.27
    for index, angle in enumerate((45, 135, 225, 315), 1):
        rad = math.radians(angle)
        end = (math.cos(rad) * ring_radius * 0.94, -0.08 + math.sin(rad) * ring_radius * 0.94, 4.36)
        add_cylinder_between(
            f"Chandelier chain {index}",
            (0.0, -0.08, support_z),
            end,
            0.009,
            brass,
            target,
            vertices=12,
        )

    flame_positions: list[tuple[float, float, float]] = []
    candle_count = 10
    for index in range(candle_count):
        angle = 2 * math.pi * index / candle_count
        x = math.cos(angle) * ring_radius
        y = -0.08 + math.sin(angle) * ring_radius
        add_cylinder(f"Chandelier candle cup {index+1}", (x, y, 4.43), 0.050, 0.075, brass, target, vertices=24)
        add_cylinder(f"Chandelier candle {index+1}", (x, y, 4.57), 0.027, 0.22, candle, target, vertices=24)
        flame_pos = (x, y, 4.715)
        flame_obj = add_uv_sphere(f"Chandelier flame {index+1}", flame_pos, 0.034, flame, target)
        flame_obj.scale.z = 1.5
        flame_positions.append(flame_pos)
    return flame_positions

def add_area_light(
    name: str,
    location: tuple[float, float, float],
    target_point: tuple[float, float, float],
    energy: float,
    size: float,
    target: bpy.types.Collection,
    *,
    color: tuple[float, float, float] = (1.0, 0.90, 0.78),
    size_y: float | None = None,
) -> bpy.types.Object:
    data = bpy.data.lights.new(name=name, type="AREA")
    data.energy = energy
    data.color = color
    if hasattr(data, "use_shadow"):
        data.use_shadow = True
    if hasattr(data, "use_contact_shadow"):
        data.use_contact_shadow = True
    if size_y is not None:
        try:
            data.shape = "RECTANGLE"
            data.size = size
            data.size_y = size_y
        except Exception:
            data.shape = "DISK"
            data.size = max(size, size_y)
    else:
        data.shape = "DISK"
        data.size = size
    obj = bpy.data.objects.new(name, data)
    target.objects.link(obj)
    obj.location = location
    target_object(obj, target_point)
    return obj


def add_point_light(
    name: str,
    location: tuple[float, float, float],
    energy: float,
    radius: float,
    target: bpy.types.Collection,
    *,
    color: tuple[float, float, float] = (1.0, 0.56, 0.28),
) -> bpy.types.Object:
    data = bpy.data.lights.new(name=name, type="POINT")
    data.energy = energy
    data.color = color
    data.shadow_soft_size = radius
    obj = bpy.data.objects.new(name, data)
    target.objects.link(obj)
    obj.location = location
    return obj


def build_lighting(
    target: bpy.types.Collection,
    chandelier_flames: Sequence[tuple[float, float, float]],
) -> None:
    # Broad off-camera sources reproduce the source image's impossible, elegant
    # illumination without introducing windows or visible studio fixtures.
    add_area_light("Left magical key", (-5.4, -6.2, 6.8), (0.0, 1.0, 2.50), 780.0, 6.0, target)
    add_area_light("Right magical key", (5.4, -6.2, 6.8), (0.0, 1.0, 2.50), 780.0, 6.0, target)
    add_area_light("Centered magical fill", (0.0, -7.0, 5.15), (0.0, 1.2, 2.35), 540.0, 6.4, target)
    add_area_light("Soft overhead bounce", (0.0, 0.0, 7.8), (0.0, 0.9, 2.20), 430.0, 5.8, target, color=(1.0, 0.84, 0.67))

    # Cove bounce follows the three visible sides of the ceiling tray.
    add_area_light("Back hidden cove", (0.0, BACK_Y - 0.98, 5.15), (0.0, 2.45, 5.42), 390.0, 8.8, target, size_y=0.50, color=(1.0, 0.66, 0.38))
    add_area_light("Left hidden cove", (LEFT_X + 0.98, 0.0, 5.15), (-4.8, 0.0, 5.42), 300.0, 6.5, target, size_y=0.50, color=(1.0, 0.66, 0.38))
    add_area_light("Right hidden cove", (RIGHT_X - 0.98, 0.0, 5.15), (4.8, 0.0, 5.42), 300.0, 6.5, target, size_y=0.50, color=(1.0, 0.66, 0.38))

    # The visible chandelier contributes only a gentle local pool of warm light.
    # A subset of points is enough at this viewing distance and keeps Cycles clean.
    for index, position in enumerate(chandelier_flames[::2], 1):
        add_point_light(f"Chandelier candle light {index}", position, 18.0, 0.16, target)


# =============================================================================
# CAMERA + WEBSITE METADATA
# =============================================================================


def make_camera(
    name: str,
    location: tuple[float, float, float],
    look_at: tuple[float, float, float],
    lens: float,
    view_id: str,
    target: bpy.types.Collection,
) -> bpy.types.Object:
    data = bpy.data.cameras.new(name)
    data.lens = lens
    data.sensor_width = 36.0
    data.dof.use_dof = False
    data.clip_start = 0.08
    data.clip_end = 100.0
    obj = bpy.data.objects.new(name, data)
    target.objects.link(obj)
    obj.location = location
    target_object(obj, look_at)
    obj["world_view_id"] = view_id
    return obj


def add_hotspot(
    hotspot_id: str,
    location: tuple[float, float, float],
    dimensions: tuple[float, float, float],
    target: bpy.types.Collection,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=location)
    obj = bpy.context.object
    obj.name = f"WORLD_HOTSPOT__{hotspot_id}"
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    move_to_collection(obj, target)
    obj.display_type = "WIRE"
    obj.hide_render = True
    obj["world_hotspot_id"] = hotspot_id
    return obj


def build_camera_and_hotspot(
    cameras: bpy.types.Collection,
    interactions: bpy.types.Collection,
) -> bpy.types.Object:
    # A deliberately wide authored view reproduces the approved build sheet: full
    # chandelier visibility, broad carpet foreground, centered door, visible side
    # walls, and enough edge margin that the image survives mobile/desktop crops.
    camera = make_camera(
        "WORLD_CAMERA__ballroom",
        (0.0, -5.45, 2.48),
        (0.0, 1.52, 2.46),
        18.6,
        "ballroom",
        cameras,
    )
    add_hotspot(
        "ballroom-exit",
        (0.0, BACK_Y - 0.36, 1.65),
        (2.12, 0.30, 3.30),
        interactions,
    )
    return camera


# =============================================================================
# RENDER SETTINGS
# =============================================================================


def configure_eevee_engine(scene: bpy.types.Scene) -> str:
    errors: list[str] = []
    for engine in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            scene.render.engine = engine
            print(f"Preview render engine: {engine}")
            return engine
        except (TypeError, ValueError) as exc:
            errors.append(f"{engine}: {exc}")
    raise RuntimeError("No supported Eevee engine. " + " | ".join(errors))


def configure_cycles_device(scene: bpy.types.Scene) -> None:
    scene.cycles.device = "CPU"
    if not USE_GPU:
        return
    try:
        addon = bpy.context.preferences.addons.get("cycles")
        if addon is None:
            return
        preferences = addon.preferences
        try:
            preferences.get_devices()
        except Exception:
            pass
        devices = list(getattr(preferences, "devices", ()))
        gpu_devices = [device for device in devices if getattr(device, "type", "CPU") != "CPU"]
        if not gpu_devices:
            print("No Cycles GPU device detected; using CPU.")
            return
        for device in devices:
            device.use = device in gpu_devices
        scene.cycles.device = "GPU"
        print("Cycles GPU devices: " + ", ".join(device.name for device in gpu_devices))
    except Exception as exc:
        print(f"Cycles GPU setup warning; using CPU: {exc}")
        scene.cycles.device = "CPU"


def configure_compositor(scene: bpy.types.Scene) -> None:
    """Very restrained highlight bloom, similar to a real lens rather than game bloom."""
    try:
        scene.use_nodes = True
        tree = scene.node_tree
        nodes = tree.nodes
        links = tree.links
        nodes.clear()
        render_layers = nodes.new("CompositorNodeRLayers")
        glare = nodes.new("CompositorNodeGlare")
        composite = nodes.new("CompositorNodeComposite")
        glare.glare_type = "FOG_GLOW"
        glare.quality = "HIGH"
        glare.threshold = 1.15
        glare.size = 6
        glare.mix = -0.94
        links.new(render_layers.outputs["Image"], glare.inputs["Image"])
        links.new(glare.outputs["Image"], composite.inputs["Image"])
    except Exception as exc:
        print(f"Compositor setup warning: {exc}")


def configure_render(scene: bpy.types.Scene) -> None:
    preset = QUALITY_PRESETS[QUALITY]

    # Every published ballroom image is a real Cycles render. PREVIEW simply uses
    # fewer samples; it never swaps to Eevee, so composition/material feedback is reliable.
    scene.render.engine = "CYCLES"
    scene.cycles.samples = preset["samples"]
    scene.cycles.preview_samples = min(64, preset["samples"])
    scene.cycles.use_denoising = True
    if hasattr(scene.cycles, "use_preview_denoising"):
        scene.cycles.use_preview_denoising = True
    if hasattr(scene.cycles, "use_adaptive_sampling"):
        scene.cycles.use_adaptive_sampling = True
    if hasattr(scene.cycles, "adaptive_threshold"):
        scene.cycles.adaptive_threshold = {
            "PREVIEW": 0.040,
            "WEB": 0.010,
            "FINAL": 0.006,
        }[QUALITY]
    if hasattr(scene.cycles, "max_bounces"):
        scene.cycles.max_bounces = 12
    if hasattr(scene.cycles, "diffuse_bounces"):
        scene.cycles.diffuse_bounces = 5
    if hasattr(scene.cycles, "glossy_bounces"):
        scene.cycles.glossy_bounces = 5
    if hasattr(scene.cycles, "transmission_bounces"):
        scene.cycles.transmission_bounces = 8
    if hasattr(scene.cycles, "transparent_max_bounces"):
        scene.cycles.transparent_max_bounces = 8
    if hasattr(scene.cycles, "volume_bounces"):
        scene.cycles.volume_bounces = 2
    if hasattr(scene.cycles, "use_light_tree"):
        scene.cycles.use_light_tree = True
    if hasattr(scene.cycles, "sample_clamp_indirect"):
        scene.cycles.sample_clamp_indirect = 4.0
    if hasattr(scene.cycles, "blur_glossy"):
        scene.cycles.blur_glossy = 0.5
    configure_cycles_device(scene)

    scene.render.resolution_x = preset["width"]
    scene.render.resolution_y = preset["height"]
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = "8"
    scene.render.film_transparent = False
    scene.render.use_file_extension = True

    # Blender 5.2 uses AgX; keep the grade warm and controlled like the reference.
    for transform in ("AgX", "Filmic", "Standard"):
        try:
            scene.view_settings.view_transform = transform
            break
        except Exception:
            continue
    for look in ("AgX - Medium High Contrast", "Medium High Contrast", "AgX - Medium Low Contrast", "None"):
        try:
            scene.view_settings.look = look
            break
        except Exception:
            continue
    scene.view_settings.exposure = -0.10

    world = scene.world or bpy.data.worlds.new("Ballroom world")
    scene.world = world
    world.use_nodes = True
    background = world.node_tree.nodes.get("Background")
    if background is not None:
        background.inputs["Color"].default_value = (0.018, 0.015, 0.012, 1.0)
        background.inputs["Strength"].default_value = 0.075

    configure_compositor(scene)


def render_view(scene: bpy.types.Scene, camera: bpy.types.Object, output: Path) -> None:
    scene.camera = camera
    scene.render.filepath = str(output)
    bpy.ops.render.render(write_still=True)
    print(f"Rendered {camera.name} -> {output}")


# =============================================================================
# BUILD
# =============================================================================


def main() -> None:
    clear_scene()
    scene = bpy.context.scene
    scene.name = "Hecate946 Approved Ballroom 2.5D"
    scene["hecate_scene_style"] = "house-matched-restrained-neoclassical"
    scene["hecate_scene_version"] = SCRIPT_VERSION
    scene["hecate_scene_thesis"] = "empty teal ballroom / symmetry / magical light"
    scene["hecate_scene_reference"] = str(REFERENCE_PATH.relative_to(SCRIPT_DIR)) if REFERENCE_PATH.exists() else "approved build sheet missing"

    root = collection("WORLD__ballroom")
    background = collection("WORLD_BACKGROUND", root)
    midground = collection("WORLD_MIDGROUND", root)
    foreground = collection("WORLD_FOREGROUND", root)
    interactions = collection("WORLD_INTERACTION", root)
    cameras = collection("WORLD_CAMERAS", root)
    lights = collection("WORLD_LIGHTS", root)

    plaster = make_plaster("House-matched warm cream plaster", HOUSE_CREAM)
    plaster_inset = make_plaster("Slightly lighter inset plaster", (0.77, 0.71, 0.58, 1.0))
    trim = make_trim("House-matched cream limestone trim", HOUSE_TRIM)
    carpet = make_carpet("Approved dark teal carpet")
    carpet_gold = simple_material("Muted gold carpet pattern", (0.22, 0.105, 0.020, 1.0), roughness=0.48, metallic=0.42)
    wood = make_wood("House-matched procedural mahogany")
    wood_dark = simple_material("Door recessed mahogany", (0.010, 0.0015, 0.0010, 1.0), roughness=0.58)
    brass = make_brass("Muted warm brass")
    candle = make_candle("Warm ivory chandelier candles")
    flame = make_flame("Quiet candle flame")
    cove_emission = make_emission("Warm recessed cove glow", (1.0, 0.54, 0.24, 1.0), 7.5)

    build_architecture(
        background,
        foreground,
        plaster,
        plaster_inset,
        trim,
        carpet,
        carpet_gold,
        wood,
        wood_dark,
        brass,
        cove_emission,
    )
    chandelier_flames = build_chandelier(midground, brass, candle, flame)
    build_lighting(lights, chandelier_flames)
    camera = build_camera_and_hotspot(cameras, interactions)
    configure_render(scene)

    SCRIPT_DIR.mkdir(parents=True, exist_ok=True)
    scene.camera = camera
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH))
    print(f"Saved ballroom scene -> {BLEND_PATH}")

    if AUTO_RENDER:
        render_view(scene, camera, ESTABLISHING_RENDER)
        scene.camera = camera
        bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH))

    print("=" * 76)
    print("Hecate946 approved ballroom build complete")
    print(f"Version:   {SCRIPT_VERSION}")
    print(f"Quality:   {QUALITY}")
    print(f"Reference: {REFERENCE_PATH}")
    print(f"Blend:     {BLEND_PATH}")
    if AUTO_RENDER:
        print(f"Render:    {ESTABLISHING_RENDER}")
    print("=" * 76)


if __name__ == "__main__":
    main()
