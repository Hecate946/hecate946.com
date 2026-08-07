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

SCRIPT_VERSION = "ballroom-approved-build-sheet-v7-framing-fix-2026-08-07"
SCRIPT_DIR = Path(__file__).resolve().parent
REFERENCE_PATH = SCRIPT_DIR / "reference" / "approved-ballroom-build-sheet.png"
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
    "PREVIEW": {"width": 960, "height": 640, "samples": 24},
    "WEB": {"width": 1800, "height": 1200, "samples": 96},
    "FINAL": {"width": 2700, "height": 1800, "samples": 192},
}
if QUALITY not in QUALITY_PRESETS:
    raise ValueError(
        "HECATE_BALLROOM_QUALITY must be PREVIEW, WEB, or FINAL "
        f"(received {QUALITY!r})."
    )

# These proportions are deliberately stage-like and chosen to reproduce the
# approved wide establishing composition rather than to simulate a floor plan.
ROOM_WIDTH = 11.60
ROOM_DEPTH = 8.20
ROOM_HEIGHT = 5.40
WALL_THICKNESS = 0.22
BACK_Y = ROOM_DEPTH / 2
LEFT_X = -ROOM_WIDTH / 2
RIGHT_X = ROOM_WIDTH / 2

# House palette copied from blender/house/house.py.
HOUSE_CREAM = (0.73, 0.67, 0.53, 1.0)
HOUSE_TRIM = (0.91, 0.86, 0.72, 1.0)
DOOR_WOOD_DARK = (0.018, 0.0025, 0.0015, 1.0)
DOOR_WOOD_LIGHT = (0.072, 0.010, 0.005, 1.0)


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
    """Very low-frequency plaster variation; never visible as noisy microtexture."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    tex = nodes.new("ShaderNodeTexNoise")
    ramp = nodes.new("ShaderNodeValToRGB")
    texcoord = nodes.new("ShaderNodeTexCoord")

    tex.inputs["Scale"].default_value = 1.35
    tex.inputs["Detail"].default_value = 1.1
    tex.inputs["Roughness"].default_value = 0.38
    dark = tuple(max(0.0, channel * 0.96) for channel in base[:3]) + (1.0,)
    light = tuple(min(1.0, channel * 1.035) for channel in base[:3]) + (1.0,)
    ramp.color_ramp.elements[0].color = dark
    ramp.color_ramp.elements[1].color = light
    ramp.color_ramp.elements[0].position = 0.25
    ramp.color_ramp.elements[1].position = 0.78

    set_input(bsdf, ("Roughness",), 0.77)
    set_input(bsdf, ("Specular IOR Level", "Specular"), 0.20)

    links.new(texcoord.outputs["Generated"], tex.inputs["Vector"])
    links.new(tex.outputs["Fac"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


def make_carpet(name: str) -> bpy.types.Material:
    """Dark teal broadcloth: rich field color without visible fibers."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    texcoord = nodes.new("ShaderNodeTexCoord")
    noise = nodes.new("ShaderNodeTexNoise")
    ramp = nodes.new("ShaderNodeValToRGB")
    bump = nodes.new("ShaderNodeBump")

    noise.inputs["Scale"].default_value = 3.4
    noise.inputs["Detail"].default_value = 1.3
    noise.inputs["Roughness"].default_value = 0.42
    ramp.color_ramp.elements[0].color = (0.006, 0.035, 0.033, 1.0)
    ramp.color_ramp.elements[1].color = (0.015, 0.078, 0.070, 1.0)
    ramp.color_ramp.elements[0].position = 0.25
    ramp.color_ramp.elements[1].position = 0.78

    set_input(bsdf, ("Roughness",), 0.88)
    set_input(bsdf, ("Specular IOR Level", "Specular"), 0.16)
    bump.inputs["Strength"].default_value = 0.035
    bump.inputs["Distance"].default_value = 0.010

    links.new(texcoord.outputs["Generated"], noise.inputs["Vector"])
    links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(noise.outputs["Fac"], bump.inputs["Height"])
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

    mapping.inputs["Scale"].default_value = (4.0, 2.0, 0.42)
    wave.wave_type = "BANDS"
    wave.bands_direction = "X"
    wave.inputs["Scale"].default_value = 11.0
    wave.inputs["Distortion"].default_value = 3.6
    noise.inputs["Scale"].default_value = 5.0
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
    bump.inputs["Strength"].default_value = 0.12
    bump.inputs["Distance"].default_value = 0.014

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
    return simple_material(name, (0.32, 0.18, 0.045, 1.0), roughness=0.30, metallic=0.82)


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
    emission.inputs["Strength"].default_value = 4.0
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
    # Stacked rectangles are intentionally used instead of ornate profiles so the
    # module looks like the exterior house and remains trivial to regenerate.
    add_box(f"{name} plinth", (x, y, 0.23), (0.44, 0.13, 0.42), trim, target, bevel=0.018)
    add_box(f"{name} base", (x, y - 0.006, 0.51), (0.35, 0.14, 0.18), trim, target, bevel=0.014)
    add_box(f"{name} shaft", (x, y, 2.58), (0.24, 0.11, 3.96), trim, target, bevel=0.014)
    add_box(f"{name} neck", (x, y - 0.006, 4.61), (0.32, 0.13, 0.15), trim, target, bevel=0.014)
    add_box(f"{name} capital", (x, y - 0.012, 4.76), (0.43, 0.15, 0.16), trim, target, bevel=0.018)


def add_side_pilaster(
    name: str,
    side: int,
    y: float,
    x: float,
    trim: bpy.types.Material,
    target: bpy.types.Collection,
) -> None:
    add_box(f"{name} plinth", (x, y, 0.23), (0.13, 0.44, 0.42), trim, target, bevel=0.018)
    add_box(f"{name} base", (x - side * 0.006, y, 0.51), (0.14, 0.35, 0.18), trim, target, bevel=0.014)
    add_box(f"{name} shaft", (x, y, 2.58), (0.11, 0.24, 3.96), trim, target, bevel=0.014)
    add_box(f"{name} neck", (x - side * 0.006, y, 4.61), (0.13, 0.32, 0.15), trim, target, bevel=0.014)
    add_box(f"{name} capital", (x - side * 0.012, y, 4.76), (0.15, 0.43, 0.16), trim, target, bevel=0.018)


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
    size = 0.038
    x_step = 0.72
    y_step = 0.68
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
    extruded_arch_xz("Door outer cream arch", 0, wall_front - 0.035, 0.10, 2.30, 2.68, 0.12, trim, target)
    extruded_arch_xz("Door inner cream arch", 0, wall_front - 0.090, 0.13, 2.10, 2.61, 0.10, plaster_inset, target)
    extruded_arch_xz("Dark mahogany arched double door", 0, wall_front - 0.145, 0.14, 1.88, 2.54, 0.09, wood, target)

    face_y = wall_front - 0.202
    add_box("Door center seam", (0, face_y, 1.58), (0.028, 0.022, 2.88), wood_dark, target, bevel=0.004)

    # Simple raised panels: enough depth to feel real, still exactly within the scene bible.
    for side in (-1, 1):
        cx = side * 0.47
        add_box(f"Door lower panel {side:+d}", (cx, face_y - 0.012, 0.69), (0.66, 0.032, 0.74), wood_dark, target, bevel=0.025)
        add_box(f"Door upper panel {side:+d}", (cx, face_y - 0.012, 1.77), (0.66, 0.032, 1.15), wood_dark, target, bevel=0.025)
        # Thin wood rails around the two rectangular panels.
        for label, zc, width, height in (
            ("lower", 0.69, 0.73, 0.82),
            ("upper", 1.77, 0.73, 1.23),
        ):
            t = 0.035
            add_box(f"Door {label} panel L {side:+d}", (cx - width / 2, face_y - 0.035, zc), (t, 0.030, height), wood, target, bevel=0.006)
            add_box(f"Door {label} panel R {side:+d}", (cx + width / 2, face_y - 0.035, zc), (t, 0.030, height), wood, target, bevel=0.006)
            add_box(f"Door {label} panel B {side:+d}", (cx, face_y - 0.035, zc - height / 2), (width, 0.030, t), wood, target, bevel=0.006)
            add_box(f"Door {label} panel T {side:+d}", (cx, face_y - 0.035, zc + height / 2), (width, 0.030, t), wood, target, bevel=0.006)

    for side in (-1, 1):
        x = side * 0.18
        add_cylinder(f"Door brass pull {side:+d}", (x, face_y - 0.060, 1.47), 0.022, 0.46, brass, target, vertices=24)
        add_uv_sphere(f"Door pull top cap {side:+d}", (x, face_y - 0.060, 1.70), 0.030, brass, target)
        add_uv_sphere(f"Door pull bottom cap {side:+d}", (x, face_y - 0.060, 1.24), 0.030, brass, target)


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
    add_perimeter_rail("Cornice lower", 4.73, 0.14, 0.16, trim, background)
    add_perimeter_rail("Cornice middle", 4.91, 0.18, 0.20, trim, background)
    add_perimeter_rail("Cornice upper", 5.09, 0.16, 0.25, trim, background)

    # Back wall pilasters and modular framed panels.
    back_detail_y = BACK_Y - WALL_THICKNESS / 2 - 0.078
    for index, x in enumerate((-5.05, -2.25, 2.25, 5.05), 1):
        add_back_pilaster(f"Back pilaster {index}", x, back_detail_y, trim, background)

    # Upper frames exactly avoid wall lights; they remain empty architectural panels.
    back_panels = (
        (-3.65, 2.05),
        (-1.55, 0.72),
        (1.55, 0.72),
        (3.65, 2.05),
    )
    for index, (x, width) in enumerate(back_panels, 1):
        add_back_molding_rect(f"Back upper panel {index}", x, width, 1.48, 4.38, back_detail_y - 0.028, trim, background)
        add_back_molding_rect(f"Back lower panel {index}", x, width, 0.35, 0.90, back_detail_y - 0.026, trim, background, strip=0.045)

    # Side walls use the same module rhythm and no side doors or sconces.
    for side in (-1, 1):
        side_detail_x = side * (ROOM_WIDTH / 2 - WALL_THICKNESS / 2 - 0.078)
        for index, y in enumerate((-2.85, 0.0, 2.85), 1):
            add_side_pilaster(f"{'Left' if side < 0 else 'Right'} pilaster {index}", side, y, side_detail_x, trim, background)
        for index, y in enumerate((-1.45, 1.45), 1):
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
    add_box("Back dropped ceiling soffit", (0, BACK_Y - 0.43, 5.18), (ROOM_WIDTH - 0.18, 0.70, 0.25), trim, background, bevel=0.028)
    add_box("Left dropped ceiling soffit", (LEFT_X + 0.43, 0, 5.18), (0.70, ROOM_DEPTH - 0.18, 0.25), trim, background, bevel=0.028)
    add_box("Right dropped ceiling soffit", (RIGHT_X - 0.43, 0, 5.18), (0.70, ROOM_DEPTH - 0.18, 0.25), trim, background, bevel=0.028)
    add_box("Back cove inner lip", (0, BACK_Y - 0.81, 5.02), (ROOM_WIDTH - 1.50, 0.12, 0.16), trim, background, bevel=0.018)
    add_box("Left cove inner lip", (LEFT_X + 0.81, 0, 5.02), (0.12, ROOM_DEPTH - 1.50, 0.16), trim, background, bevel=0.018)
    add_box("Right cove inner lip", (RIGHT_X - 0.81, 0, 5.02), (0.12, ROOM_DEPTH - 1.50, 0.16), trim, background, bevel=0.018)

    build_door(background, plaster_inset, trim, wood, wood_dark, brass)


# =============================================================================
# CHANDELIER + LIGHTING
# =============================================================================


def build_chandelier(
    target: bpy.types.Collection,
    brass: bpy.types.Material,
    candle: bpy.types.Material,
    flame: bpy.types.Material,
) -> None:
    center = (0.0, -0.05, 4.18)
    ring_radius = 1.05
    add_torus("Simple centered brass chandelier ring", center, ring_radius, 0.035, brass, target)

    add_cylinder("Chandelier ceiling rose", (0, -0.05, 5.23), 0.18, 0.08, brass, target, vertices=32)
    add_cylinder("Chandelier lower hub", (0, -0.05, 4.18), 0.09, 0.16, brass, target, vertices=28)

    support_z = 5.18
    for index, angle in enumerate((45, 135, 225, 315), 1):
        rad = math.radians(angle)
        end = (math.cos(rad) * ring_radius * 0.93, -0.05 + math.sin(rad) * ring_radius * 0.93, 4.20)
        add_cylinder_between(
            f"Chandelier support {index}",
            (0.0, -0.05, support_z),
            end,
            0.014,
            brass,
            target,
            vertices=12,
        )

    for index in range(8):
        angle = 2 * math.pi * index / 8
        x = math.cos(angle) * ring_radius
        y = -0.05 + math.sin(angle) * ring_radius
        add_cylinder(f"Chandelier candle cup {index+1}", (x, y, 4.28), 0.060, 0.090, brass, target, vertices=20)
        add_cylinder(f"Chandelier candle {index+1}", (x, y, 4.43), 0.032, 0.25, candle, target, vertices=20)
        flame_obj = add_uv_sphere(f"Chandelier flame {index+1}", (x, y, 4.59), 0.040, flame, target)
        flame_obj.scale.z = 1.45


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


def build_lighting(target: bpy.types.Collection) -> None:
    # House-like symmetrical "impossible" light. These sources sit outside the
    # authored frame; visible chandelier candles are decorative only.
    add_area_light("Left magical key", (-4.6, -5.0, 6.4), (0.0, 0.7, 2.45), 720.0, 5.0, target)
    add_area_light("Right magical key", (4.6, -5.0, 6.4), (0.0, 0.7, 2.45), 720.0, 5.0, target)
    add_area_light("Centered magical fill", (0.0, -5.8, 4.9), (0.0, 0.8, 2.25), 480.0, 5.6, target)
    add_area_light("Soft overhead fill", (0.0, 0.2, 7.4), (0.0, 0.6, 2.2), 520.0, 4.8, target, color=(1.0, 0.86, 0.68))

    # Cove glow: three hidden rectangular area lights bounce into the ceiling tray.
    add_area_light("Back hidden cove", (0.0, BACK_Y - 0.90, 5.03), (0.0, 2.2, 5.34), 330.0, 7.8, target, size_y=0.45, color=(1.0, 0.68, 0.42))
    add_area_light("Left hidden cove", (LEFT_X + 0.90, 0.0, 5.03), (-4.25, 0.0, 5.34), 250.0, 5.6, target, size_y=0.45, color=(1.0, 0.68, 0.42))
    add_area_light("Right hidden cove", (RIGHT_X - 0.90, 0.0, 5.03), (4.25, 0.0, 5.34), 250.0, 5.6, target, size_y=0.45, color=(1.0, 0.68, 0.42))


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


def configure_render(scene: bpy.types.Scene) -> None:
    preset = QUALITY_PRESETS[QUALITY]
    if QUALITY == "PREVIEW":
        configure_eevee_engine(scene)
        # Enable conservative Eevee quality features when this Blender exposes them.
        eevee = getattr(scene, "eevee", None)
        if eevee is not None:
            for attr, value in (
                ("use_gtao", True),
                ("gtao_distance", 3.0),
                ("gtao_factor", 1.15),
                ("use_soft_shadows", True),
            ):
                if hasattr(eevee, attr):
                    setattr(eevee, attr, value)
    else:
        try:
            scene.render.engine = "CYCLES"
            scene.cycles.samples = preset["samples"]
            scene.cycles.use_denoising = True
            scene.cycles.preview_samples = min(32, preset["samples"])
            if hasattr(scene.cycles, "use_adaptive_sampling"):
                scene.cycles.use_adaptive_sampling = True
            if hasattr(scene.cycles, "adaptive_threshold"):
                scene.cycles.adaptive_threshold = 0.020 if QUALITY == "WEB" else 0.012
            configure_cycles_device(scene)
        except Exception as exc:
            print(f"Cycles setup warning; falling back to Eevee: {exc}")
            configure_eevee_engine(scene)

    scene.render.resolution_x = preset["width"]
    scene.render.resolution_y = preset["height"]
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = False
    scene.render.use_file_extension = True

    # Match the quiet exterior render rather than pushing cinematic contrast.
    for transform in ("AgX", "Filmic", "Standard"):
        try:
            scene.view_settings.view_transform = transform
            break
        except Exception:
            continue
    for look in ("AgX - Medium High Contrast", "Medium High Contrast", "Medium High Contrast"):
        try:
            scene.view_settings.look = look
            break
        except Exception:
            continue
    scene.view_settings.exposure = -0.15

    world = scene.world or bpy.data.worlds.new("Ballroom world")
    scene.world = world
    world.use_nodes = True
    background = world.node_tree.nodes.get("Background")
    if background is not None:
        background.inputs["Color"].default_value = (0.020, 0.018, 0.015, 1.0)
        background.inputs["Strength"].default_value = 0.10


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
    trim = simple_material("House-matched cream limestone trim", HOUSE_TRIM, roughness=0.64)
    carpet = make_carpet("Approved dark teal carpet")
    carpet_gold = simple_material("Muted gold carpet pattern", (0.26, 0.145, 0.032, 1.0), roughness=0.48, metallic=0.58)
    wood = make_wood("House-matched procedural mahogany")
    wood_dark = simple_material("Door recessed mahogany", (0.010, 0.0015, 0.0010, 1.0), roughness=0.58)
    brass = make_brass("Muted warm brass")
    candle = make_candle("Warm ivory chandelier candles")
    flame = make_flame("Quiet candle flame")

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
    )
    build_chandelier(midground, brass, candle, flame)
    build_lighting(lights)
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
