"""
HECATE946.COM — MODULAR HOUSE EXTERIOR 2.5D
===========================================

Builds the complete seasonal exterior around the EXISTING house model.

Source of truth
---------------
The house itself is NOT rebuilt here. This script appends these collections from:

    blender/house/house.blend

    Architecture
    Windows
    Door
    Roof

That preserves the exact house the site already uses while allowing the exterior
environment to evolve independently.

Visual thesis
-------------
A quiet Neoclassical architectural miniature in a soft seasonal landscape:
- the house remains the focal point
- one centered stone path leads to the door
- two restrained trees frame the facade
- the same shrubs / flower positions persist in every season
- distant low hills give depth without creating a "game world"
- lighting is broad and soft
- the camera is calm, nearly frontal, and long-lens

Responsive composition
----------------------
The master render is 16:9 and deliberately center-safe.

Desktop:
    the entire house + most framing trees are visible.

Mobile:
    the website uses object-fit: cover and crops the SIDES only.
    The central door, pediment, circular window, path, and central facade remain
    inside the safe crop, so no second mobile render is required.

Season policy
-------------
Fixed between seasons:
    house geometry
    path
    plinth
    terrain geometry
    hill geometry
    tree trunks / branches
    shrub positions
    flower positions
    camera

Seasonal only:
    sky / landscape palette
    foliage color
    blossom / leaf visibility
    snow
    sparse atmospheric accents
    lighting temperature
    window glow strength

Outputs
-------
Editable Blender scene:
    blender/house/exterior/exterior-25d.blend

Website renders:
    public/scenes/house/exterior/spring.png
    public/scenes/house/exterior/summer.png
    public/scenes/house/exterior/autumn.png
    public/scenes/house/exterior/winter.png

Usage
-----
Fast preview:
    HECATE_EXTERIOR_QUALITY=PREVIEW blender --background --python blender/house/exterior/build_exterior_25d.py

Normal website render:
    blender --background --python blender/house/exterior/build_exterior_25d.py

Final render:
    HECATE_EXTERIOR_QUALITY=FINAL blender --background --python blender/house/exterior/build_exterior_25d.py

Build .blend only:
    HECATE_EXTERIOR_RENDER=0 blender --background --python blender/house/exterior/build_exterior_25d.py
"""

from __future__ import annotations

import math
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import bpy
from mathutils import Vector


# =============================================================================
# EASY SETTINGS
# =============================================================================

SCRIPT_VERSION = "house-exterior-25d-v3-realism-2026-08-07"

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[2]
HOUSE_BLEND = PROJECT_ROOT / "blender" / "house" / "house.blend"
BLEND_PATH = SCRIPT_DIR / "exterior-25d.blend"
PUBLIC_RENDER_DIR = PROJECT_ROOT / "public" / "scenes" / "house" / "exterior"

HOUSE_SOURCE_COLLECTIONS = ("Architecture", "Windows", "Door", "Roof")
SEASONS = ("spring", "summer", "autumn", "winter")


def env_flag(name: str, default: bool) -> bool:
    fallback = "1" if default else "0"
    return os.environ.get(name, fallback).strip().lower() not in {
        "0",
        "false",
        "no",
        "off",
    }


QUALITY = str(os.environ.get("HECATE_EXTERIOR_QUALITY", "WEB")).strip().upper()
AUTO_RENDER = env_flag("HECATE_EXTERIOR_RENDER", True)
USE_GPU = env_flag("HECATE_EXTERIOR_GPU", True)
DEFAULT_SEASON = str(os.environ.get("HECATE_EXTERIOR_DEFAULT_SEASON", "winter")).strip().lower()

RENDER_SEASONS = tuple(
    season.strip().lower()
    for season in os.environ.get(
        "HECATE_EXTERIOR_SEASONS",
        ",".join(SEASONS),
    ).split(",")
    if season.strip()
)

QUALITY_PRESETS = {
    # Eevee composition check: intentionally quick.
    "PREVIEW": {"width": 1280, "height": 720, "samples": 24},
    # Normal website source. Browser can generate WebP/AVIF later if desired.
    "WEB": {"width": 2400, "height": 1350, "samples": 72},
    # High-resolution master.
    "FINAL": {"width": 3200, "height": 1800, "samples": 144},
}

if QUALITY not in QUALITY_PRESETS:
    raise ValueError(
        "HECATE_EXTERIOR_QUALITY must be PREVIEW, WEB, or FINAL "
        f"(received {QUALITY!r})."
    )

if DEFAULT_SEASON not in SEASONS:
    raise ValueError(
        "HECATE_EXTERIOR_DEFAULT_SEASON must be spring, summer, autumn, or winter "
        f"(received {DEFAULT_SEASON!r})."
    )

invalid_render_seasons = [season for season in RENDER_SEASONS if season not in SEASONS]
if invalid_render_seasons:
    raise ValueError(
        "HECATE_EXTERIOR_SEASONS may contain only spring, summer, autumn, winter "
        f"(received {invalid_render_seasons!r})."
    )

# Existing house dimensions, kept here only to make the landscaping readable.
# The house itself always comes from house.blend.
HOUSE_WIDTH = 14.0
HOUSE_DEPTH = 3.10
HOUSE_HEIGHT_APPROX = 7.98
FACADE_Y = -HOUSE_DEPTH / 2.0

# The camera is deliberately long-lens and nearly level.
# This makes the house fill the desktop view while preserving calm geometry.
CAMERA_LOCATION = (0.0, -34.7, 3.72)
CAMERA_TARGET = (0.0, -0.20, 3.58)
CAMERA_LENS_MM = 70.0

# Website crop metadata. A narrow phone showing the 16:9 render with object-fit:
# cover sees roughly the center third of the source. All critical architecture
# stays inside this region.
MOBILE_SAFE_SOURCE_FRACTION = 0.32

# Stable landscaping coordinates. Do not change these per season.
TREE_X = 8.25
TREE_Y = 0.75

SHRUB_LAYOUT = (
    (-7.95, -0.85, 0.48, 0.74),
    (-7.20, -0.35, 0.55, 0.88),
    (-4.25, -3.55, 0.50, 0.78),
    (-3.58, -3.82, 0.34, 0.50),
    (3.58, -3.82, 0.34, 0.50),
    (4.25, -3.55, 0.50, 0.78),
    (7.20, -0.35, 0.55, 0.88),
    (7.95, -0.85, 0.48, 0.74),
)

FLOWER_LAYOUT = (
    (-8.10, -1.35, 0.18),
    (-7.62, -1.48, 0.16),
    (-4.54, -4.08, 0.16),
    (-4.00, -4.22, 0.15),
    (-3.45, -4.15, 0.14),
    (3.45, -4.15, 0.14),
    (4.00, -4.22, 0.15),
    (4.54, -4.08, 0.16),
    (7.62, -1.48, 0.16),
    (8.10, -1.35, 0.18),
)


# =============================================================================
# SEASON PALETTE
# =============================================================================

Color = tuple[float, float, float, float]


@dataclass(frozen=True)
class SeasonStyle:
    sky_bottom: Color
    sky_top: Color
    hill_far: Color
    hill_mid: Color
    hill_near: Color
    ground: Color
    shrub: Color
    canopy: Color
    flower: Color
    trunk: Color
    path: Color
    snow: Color
    key_color: tuple[float, float, float]
    key_energy: float
    fill_color: tuple[float, float, float]
    fill_energy: float
    world_color: tuple[float, float, float]
    world_strength: float
    window_color: Color
    window_strength: float
    show_canopy: bool
    show_flowers: bool
    show_snow_caps: bool
    accent_collection: str


STYLES: dict[str, SeasonStyle] = {
    "spring": SeasonStyle(
        sky_bottom=(0.84, 0.90, 0.95, 1.0),
        sky_top=(0.70, 0.82, 0.91, 1.0),
        hill_far=(0.42, 0.57, 0.52, 1.0),
        hill_mid=(0.28, 0.47, 0.39, 1.0),
        hill_near=(0.19, 0.37, 0.29, 1.0),
        ground=(0.23, 0.42, 0.29, 1.0),
        shrub=(0.12, 0.30, 0.18, 1.0),
        canopy=(0.82, 0.44, 0.55, 1.0),
        flower=(0.88, 0.58, 0.67, 1.0),
        trunk=(0.24, 0.15, 0.10, 1.0),
        path=(0.62, 0.61, 0.55, 1.0),
        snow=(0.86, 0.90, 0.92, 1.0),
        key_color=(1.0, 0.82, 0.68),
        key_energy=1180.0,
        fill_color=(0.78, 0.88, 1.0),
        fill_energy=430.0,
        world_color=(0.58, 0.69, 0.78),
        world_strength=0.34,
        window_color=(1.0, 0.58, 0.24, 1.0),
        window_strength=1.35,
        show_canopy=True,
        show_flowers=True,
        show_snow_caps=False,
        accent_collection="SEASON__spring",
    ),
    "summer": SeasonStyle(
        sky_bottom=(0.83, 0.91, 0.97, 1.0),
        sky_top=(0.55, 0.75, 0.91, 1.0),
        hill_far=(0.33, 0.53, 0.45, 1.0),
        hill_mid=(0.18, 0.43, 0.30, 1.0),
        hill_near=(0.10, 0.34, 0.20, 1.0),
        ground=(0.16, 0.39, 0.22, 1.0),
        shrub=(0.07, 0.27, 0.13, 1.0),
        canopy=(0.09, 0.34, 0.16, 1.0),
        flower=(0.83, 0.71, 0.26, 1.0),
        trunk=(0.21, 0.13, 0.085, 1.0),
        path=(0.65, 0.63, 0.56, 1.0),
        snow=(0.86, 0.90, 0.92, 1.0),
        key_color=(1.0, 0.88, 0.72),
        key_energy=1320.0,
        fill_color=(0.76, 0.88, 1.0),
        fill_energy=470.0,
        world_color=(0.56, 0.72, 0.86),
        world_strength=0.38,
        window_color=(1.0, 0.60, 0.27, 1.0),
        window_strength=0.95,
        show_canopy=True,
        show_flowers=True,
        show_snow_caps=False,
        accent_collection="SEASON__summer",
    ),
    "autumn": SeasonStyle(
        sky_bottom=(0.87, 0.79, 0.69, 1.0),
        sky_top=(0.59, 0.65, 0.68, 1.0),
        hill_far=(0.48, 0.39, 0.29, 1.0),
        hill_mid=(0.35, 0.30, 0.22, 1.0),
        hill_near=(0.24, 0.24, 0.17, 1.0),
        ground=(0.28, 0.32, 0.20, 1.0),
        shrub=(0.20, 0.28, 0.14, 1.0),
        canopy=(0.67, 0.28, 0.09, 1.0),
        flower=(0.56, 0.25, 0.11, 1.0),
        trunk=(0.20, 0.12, 0.075, 1.0),
        path=(0.58, 0.53, 0.45, 1.0),
        snow=(0.86, 0.90, 0.92, 1.0),
        key_color=(1.0, 0.65, 0.42),
        key_energy=980.0,
        fill_color=(0.70, 0.78, 0.86),
        fill_energy=340.0,
        world_color=(0.45, 0.42, 0.37),
        world_strength=0.28,
        window_color=(1.0, 0.48, 0.15, 1.0),
        window_strength=1.75,
        show_canopy=True,
        show_flowers=False,
        show_snow_caps=False,
        accent_collection="SEASON__autumn",
    ),
    "winter": SeasonStyle(
        sky_bottom=(0.76, 0.84, 0.90, 1.0),
        sky_top=(0.44, 0.58, 0.68, 1.0),
        hill_far=(0.55, 0.63, 0.68, 1.0),
        hill_mid=(0.45, 0.55, 0.59, 1.0),
        hill_near=(0.36, 0.47, 0.48, 1.0),
        ground=(0.80, 0.84, 0.84, 1.0),
        shrub=(0.11, 0.22, 0.15, 1.0),
        canopy=(0.12, 0.22, 0.15, 1.0),
        flower=(0.36, 0.36, 0.33, 1.0),
        trunk=(0.21, 0.19, 0.17, 1.0),
        path=(0.67, 0.69, 0.68, 1.0),
        snow=(0.90, 0.94, 0.95, 1.0),
        key_color=(0.73, 0.84, 1.0),
        key_energy=760.0,
        fill_color=(0.72, 0.82, 0.95),
        fill_energy=300.0,
        world_color=(0.44, 0.55, 0.65),
        world_strength=0.26,
        window_color=(1.0, 0.43, 0.12, 1.0),
        window_strength=2.30,
        show_canopy=False,
        show_flowers=False,
        show_snow_caps=True,
        accent_collection="SEASON__winter",
    ),
}


# =============================================================================
# DATA CONTAINERS
# =============================================================================


@dataclass
class SceneParts:
    root: bpy.types.Collection
    background: bpy.types.Collection
    landscape: bpy.types.Collection
    vegetation: bpy.types.Collection
    foreground: bpy.types.Collection
    seasonal: dict[str, bpy.types.Collection]
    lights: bpy.types.Collection
    cameras: bpy.types.Collection
    house_parent: bpy.types.Collection
    canopy: bpy.types.Collection
    flowers: bpy.types.Collection
    snow_caps: bpy.types.Collection
    materials: dict[str, bpy.types.Material]
    key_light: bpy.types.Object
    fill_light: bpy.types.Object
    camera: bpy.types.Object


# =============================================================================
# SCENE / COLLECTION HELPERS
# =============================================================================


def clear_scene() -> None:
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")

    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)

    # The script is intended to be rerunnable from Blender's Text Editor.
    for scene in bpy.data.scenes:
        for child in list(scene.collection.children):
            scene.collection.children.unlink(child)

    for collection in list(bpy.data.collections):
        try:
            bpy.data.collections.remove(collection)
        except Exception:
            pass

    for datablocks in (
        bpy.data.meshes,
        bpy.data.curves,
        bpy.data.cameras,
        bpy.data.lights,
    ):
        for block in list(datablocks):
            if block.users == 0:
                datablocks.remove(block)


def collection(
    name: str,
    parent: bpy.types.Collection | None = None,
) -> bpy.types.Collection:
    result = bpy.data.collections.new(name)
    if parent is None:
        bpy.context.scene.collection.children.link(result)
    else:
        parent.children.link(result)
    return result


def move_to_collection(
    obj: bpy.types.Object,
    target: bpy.types.Collection,
) -> None:
    for old in list(obj.users_collection):
        old.objects.unlink(obj)
    target.objects.link(obj)


def walk_collection_objects(
    target: bpy.types.Collection,
) -> list[bpy.types.Object]:
    objects = list(target.objects)
    for child in target.children:
        objects.extend(walk_collection_objects(child))
    return objects


def target_object(
    obj: bpy.types.Object,
    point: Iterable[float],
) -> None:
    direction = Vector(point) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def smooth_mesh(obj: bpy.types.Object) -> None:
    data = getattr(obj, "data", None)
    polygons = getattr(data, "polygons", None)
    if polygons is None:
        return
    for polygon in polygons:
        polygon.use_smooth = True


# =============================================================================
# MATERIAL HELPERS
# =============================================================================


def _scale_rgb(color: Color, factor: float) -> Color:
    return (
        max(0.0, min(1.0, color[0] * factor)),
        max(0.0, min(1.0, color[1] * factor)),
        max(0.0, min(1.0, color[2] * factor)),
        color[3],
    )


def material(
    name: str,
    color: Color,
    *,
    roughness: float = 0.72,
    metallic: float = 0.0,
    variation: float = 0.0,
    bump: float = 0.0,
    noise_scale: float = 4.0,
    noise_detail: float = 2.0,
) -> bpy.types.Material:
    """Quiet low-frequency procedural material; no external textures required."""
    result = bpy.data.materials.new(name=name)
    result.use_nodes = True
    nodes = result.node_tree.nodes
    links = result.node_tree.links

    bsdf = nodes.get("Principled BSDF")
    if bsdf is None:
        return result

    bsdf.inputs["Base Color"].default_value = color
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic

    if variation <= 0.0 and bump <= 0.0:
        return result

    noise = nodes.new("ShaderNodeTexNoise")
    noise.name = f"{name} broad variation"
    noise.inputs["Scale"].default_value = noise_scale
    if "Detail" in noise.inputs:
        noise.inputs["Detail"].default_value = noise_detail
    if "Roughness" in noise.inputs:
        noise.inputs["Roughness"].default_value = 0.58

    texcoord = nodes.new("ShaderNodeTexCoord")
    texcoord.name = f"{name} coordinates"
    links.new(texcoord.outputs["Generated"], noise.inputs["Vector"])

    if variation > 0.0:
        ramp = nodes.new("ShaderNodeValToRGB")
        ramp.name = f"{name} color variation"
        ramp.color_ramp.elements[0].color = _scale_rgb(color, 1.0 - variation)
        ramp.color_ramp.elements[1].color = _scale_rgb(color, 1.0 + variation)
        ramp.color_ramp.elements[0].position = 0.26
        ramp.color_ramp.elements[1].position = 0.74
        links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
        links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])

    if bump > 0.0:
        bump_node = nodes.new("ShaderNodeBump")
        bump_node.name = f"{name} soft bump"
        bump_node.inputs["Strength"].default_value = bump
        bump_node.inputs["Distance"].default_value = 0.10
        links.new(noise.outputs["Fac"], bump_node.inputs["Height"])
        links.new(bump_node.outputs["Normal"], bsdf.inputs["Normal"])

    return result


def set_material_color(
    target: bpy.types.Material,
    color: Color,
) -> None:
    if not target.use_nodes:
        target.diffuse_color = color
        return
    bsdf = target.node_tree.nodes.get("Principled BSDF")
    if bsdf is not None:
        bsdf.inputs["Base Color"].default_value = color


def glowing_material(
    name: str,
    color: Color,
    strength: float,
) -> bpy.types.Material:
    result = material(name, color, roughness=0.30)
    bsdf = result.node_tree.nodes.get("Principled BSDF")
    if bsdf is not None:
        emission_color = bsdf.inputs.get("Emission Color")
        if emission_color is None:
            emission_color = bsdf.inputs.get("Emission")
        if emission_color is not None:
            emission_color.default_value = color
        emission_strength = bsdf.inputs.get("Emission Strength")
        if emission_strength is not None:
            emission_strength.default_value = strength
    return result


def set_glow(
    target: bpy.types.Material,
    color: Color,
    strength: float,
) -> None:
    set_material_color(target, color)
    if not target.use_nodes:
        return
    bsdf = target.node_tree.nodes.get("Principled BSDF")
    if bsdf is None:
        return
    emission_color = bsdf.inputs.get("Emission Color")
    if emission_color is None:
        emission_color = bsdf.inputs.get("Emission")
    if emission_color is not None:
        emission_color.default_value = color
    emission_strength = bsdf.inputs.get("Emission Strength")
    if emission_strength is not None:
        emission_strength.default_value = strength


def sky_gradient_material(
    name: str,
    bottom: Color,
    top: Color,
) -> bpy.types.Material:
    result = bpy.data.materials.new(name=name)
    result.use_nodes = True

    nodes = result.node_tree.nodes
    links = result.node_tree.links
    nodes.clear()

    output = nodes.new("ShaderNodeOutputMaterial")
    output.name = "Sky Output"

    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.name = "Sky Surface"
    bsdf.inputs["Roughness"].default_value = 1.0

    texcoord = nodes.new("ShaderNodeTexCoord")
    texcoord.name = "Sky Coordinates"

    separate = nodes.new("ShaderNodeSeparateXYZ")
    separate.name = "Sky Separate"

    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.name = "Sky Ramp"
    ramp.color_ramp.elements[0].position = 0.0
    ramp.color_ramp.elements[0].color = bottom
    ramp.color_ramp.elements[1].position = 1.0
    ramp.color_ramp.elements[1].color = top

    links.new(texcoord.outputs["Generated"], separate.inputs["Vector"])
    links.new(separate.outputs["Z"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])

    emission_color = bsdf.inputs.get("Emission Color")
    if emission_color is None:
        emission_color = bsdf.inputs.get("Emission")
    if emission_color is not None:
        links.new(ramp.outputs["Color"], emission_color)

    emission_strength = bsdf.inputs.get("Emission Strength")
    if emission_strength is not None:
        emission_strength.default_value = 0.30

    links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])
    return result


def set_sky_gradient(
    target: bpy.types.Material,
    bottom: Color,
    top: Color,
) -> None:
    ramp = target.node_tree.nodes.get("Sky Ramp")
    if ramp is None:
        return
    ramp.color_ramp.elements[0].color = bottom
    ramp.color_ramp.elements[1].color = top


# =============================================================================
# GEOMETRY HELPERS
# =============================================================================


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
    if bevel > 0:
        modifier = obj.modifiers.new("Soft bevel", type="BEVEL")
        modifier.width = bevel
        modifier.segments = 2
    obj.data.materials.append(mat)
    move_to_collection(obj, target)
    return obj


def add_ico(
    name: str,
    location: tuple[float, float, float],
    scale: tuple[float, float, float],
    mat: bpy.types.Material,
    target: bpy.types.Collection,
    *,
    subdivisions: int = 2,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_ico_sphere_add(
        subdivisions=subdivisions,
        radius=1.0,
        location=location,
    )
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(mat)
    move_to_collection(obj, target)
    smooth_mesh(obj)
    return obj


def add_branch(
    name: str,
    start: tuple[float, float, float],
    end: tuple[float, float, float],
    radius_start: float,
    radius_end: float,
    mat: bpy.types.Material,
    target: bpy.types.Collection,
) -> bpy.types.Object:
    a = Vector(start)
    b = Vector(end)
    direction = b - a
    length = direction.length
    midpoint = (a + b) * 0.5

    bpy.ops.mesh.primitive_cone_add(
        vertices=12,
        radius1=radius_start,
        radius2=radius_end,
        depth=length,
        location=midpoint,
    )
    obj = bpy.context.object
    obj.name = name
    obj.rotation_euler = direction.to_track_quat("Z", "Y").to_euler()
    obj.data.materials.append(mat)
    move_to_collection(obj, target)
    smooth_mesh(obj)
    return obj


def add_flat_trapezoid_path(
    mat: bpy.types.Material,
    target: bpy.types.Collection,
) -> bpy.types.Object:
    # Back edge lands at the front door. Front edge widens toward the viewer.
    y_front = -15.2
    y_back = -1.72
    front_half = 2.55
    back_half = 0.98
    z0 = 0.055
    z1 = 0.105

    verts = [
        (-front_half, y_front, z0),
        (front_half, y_front, z0),
        (back_half, y_back, z0),
        (-back_half, y_back, z0),
        (-front_half, y_front, z1),
        (front_half, y_front, z1),
        (back_half, y_back, z1),
        (-back_half, y_back, z1),
    ]
    faces = [
        (0, 3, 2, 1),
        (4, 5, 6, 7),
        (0, 1, 5, 4),
        (1, 2, 6, 5),
        (2, 3, 7, 6),
        (3, 0, 4, 7),
    ]

    mesh = bpy.data.meshes.new("Centered path mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new("Centered stone path", mesh)
    target.objects.link(obj)
    obj.data.materials.append(mat)

    bevel = obj.modifiers.new("Soft path edge", type="BEVEL")
    bevel.width = 0.035
    bevel.segments = 2
    return obj


def add_vertical_hill(
    name: str,
    *,
    y: float,
    base_z: float,
    height: float,
    width: float,
    center_x: float,
    mat: bpy.types.Material,
    target: bpy.types.Collection,
    phase: float,
) -> bpy.types.Object:
    segments = 48
    top_points: list[tuple[float, float, float]] = []
    for index in range(segments + 1):
        t = index / segments
        x = center_x - width / 2 + width * t
        envelope = math.sin(math.pi * t) ** 0.72
        wave = 0.12 * math.sin(t * math.pi * 3.0 + phase)
        z = base_z + height * max(0.0, envelope + wave)
        top_points.append((x, y, z))

    verts = [(center_x - width / 2, y, -0.60)]
    verts.extend(top_points)
    verts.append((center_x + width / 2, y, -0.60))
    face = tuple(range(len(verts)))

    mesh = bpy.data.meshes.new(f"{name} mesh")
    mesh.from_pydata(verts, [], [face])
    mesh.update()

    obj = bpy.data.objects.new(name, mesh)
    target.objects.link(obj)
    obj.data.materials.append(mat)
    return obj


def add_leaf_disc(
    name: str,
    location: tuple[float, float, float],
    size: float,
    rotation_z: float,
    mat: bpy.types.Material,
    target: bpy.types.Collection,
) -> bpy.types.Object:
    # Tiny flattened ico-sphere: readable as a leaf/petal without requiring textures.
    obj = add_ico(
        name,
        location,
        (size * 1.45, size * 0.36, size * 0.74),
        mat,
        target,
        subdivisions=1,
    )
    obj.rotation_euler.z = rotation_z
    return obj


# =============================================================================
# HOUSE IMPORT
# =============================================================================


def _house_objects_from_import(
    imported: dict[str, bpy.types.Collection],
) -> list[bpy.types.Object]:
    seen: set[str] = set()
    result: list[bpy.types.Object] = []

    for source_collection in imported.values():
        for obj in walk_collection_objects(source_collection):
            if obj.name not in seen:
                seen.add(obj.name)
                result.append(obj)

            parent = obj.parent
            while parent is not None and parent.name not in seen:
                seen.add(parent.name)
                result.append(parent)
                parent = parent.parent

    return result


def _world_bounds(
    objects: list[bpy.types.Object],
) -> tuple[Vector, Vector] | None:
    points: list[Vector] = []
    bpy.context.view_layer.update()

    for obj in objects:
        if obj.type != "MESH":
            continue
        for corner in obj.bound_box:
            points.append(obj.matrix_world @ Vector(corner))

    if not points:
        return None

    minimum = Vector((
        min(point.x for point in points),
        min(point.y for point in points),
        min(point.z for point in points),
    ))
    maximum = Vector((
        max(point.x for point in points),
        max(point.y for point in points),
        max(point.z for point in points),
    ))
    return minimum, maximum


def _normalize_house(
    objects: list[bpy.types.Object],
    target: bpy.types.Collection,
) -> bpy.types.Object:
    """Center, ground, and size the imported house without remodeling it."""
    imported_set = set(objects)

    root = bpy.data.objects.new("HOUSE__ROOT", None)
    root.empty_display_type = "PLAIN_AXES"
    target.objects.link(root)

    top_level = [
        obj for obj in objects
        if obj.parent is None or obj.parent not in imported_set
    ]

    for obj in top_level:
        matrix_world = obj.matrix_world.copy()
        obj.parent = root
        obj.matrix_world = matrix_world

    bounds = _world_bounds(objects)
    if bounds is None:
        raise RuntimeError("Imported house contains no mesh geometry.")

    minimum, maximum = bounds
    width = maximum.x - minimum.x
    if width <= 0.001:
        raise RuntimeError("Imported house has invalid width.")

    scale = HOUSE_WIDTH / width
    root.scale = (scale, scale, scale)
    bpy.context.view_layer.update()

    bounds = _world_bounds(objects)
    if bounds is None:
        raise RuntimeError("Could not evaluate house bounds after scaling.")

    minimum, maximum = bounds
    center = (minimum + maximum) * 0.5
    root.location.x += -center.x
    root.location.y += -center.y
    root.location.z += -minimum.z
    bpy.context.view_layer.update()

    bounds = _world_bounds(objects)
    if bounds is None:
        raise RuntimeError("Could not evaluate final house bounds.")

    minimum, maximum = bounds
    print(
        "HOUSE IMPORT OK — "
        f"objects={len(objects)}, "
        f"bounds=({minimum.x:.2f},{minimum.y:.2f},{minimum.z:.2f}) -> "
        f"({maximum.x:.2f},{maximum.y:.2f},{maximum.z:.2f})"
    )
    return root


def append_house(
    target: bpy.types.Collection,
) -> dict[str, bpy.types.Collection]:
    if not HOUSE_BLEND.exists():
        raise FileNotFoundError(
            "The exterior builder could not find the existing house source: "
            f"{HOUSE_BLEND}"
        )

    with bpy.data.libraries.load(str(HOUSE_BLEND), link=False) as (data_from, data_to):
        available = set(data_from.collections)
        missing = [name for name in HOUSE_SOURCE_COLLECTIONS if name not in available]
        if missing:
            raise RuntimeError(
                f"{HOUSE_BLEND} is missing required collection(s): {', '.join(missing)}"
            )
        data_to.collections = [
            name for name in HOUSE_SOURCE_COLLECTIONS if name in available
        ]

    imported: dict[str, bpy.types.Collection] = {}
    for source_name, source_collection in zip(
        HOUSE_SOURCE_COLLECTIONS,
        data_to.collections,
    ):
        if source_collection is None:
            continue
        source_collection.name = f"HOUSE_SOURCE__{source_name}"
        source_collection.hide_render = False
        source_collection.hide_viewport = False
        imported[source_name] = source_collection

    objects = _house_objects_from_import(imported)
    if not objects:
        raise RuntimeError("House collections loaded but no house objects were found.")

    # Direct-link objects into this scene. This bypasses hidden/excluded
    # collection state saved inside house.blend.
    for obj in objects:
        if target.objects.get(obj.name) is None:
            target.objects.link(obj)
        obj.hide_render = False
        obj.hide_viewport = False
        try:
            obj.hide_set(False)
        except Exception:
            pass

    _normalize_house(objects, target)
    return imported


def apply_window_glow(
    imported: dict[str, bpy.types.Collection],
    glow: bpy.types.Material,
) -> int:
    windows = imported.get("Windows")
    if windows is None:
        return 0

    changed = 0
    for obj in walk_collection_objects(windows):
        data = getattr(obj, "data", None)
        materials = getattr(data, "materials", None)
        if materials is None:
            continue

        object_name = obj.name.lower()
        material_names = " ".join(
            mat.name.lower() for mat in materials if mat is not None
        )
        if "glass" not in object_name and "glass" not in material_names:
            continue

        materials.clear()
        materials.append(glow)
        changed += 1

    print(f"Applied seasonal window glow to {changed} house glass object(s).")
    return changed


# =============================================================================
# ENVIRONMENT BUILDERS
# =============================================================================


def build_background(
    target: bpy.types.Collection,
    materials: dict[str, bpy.types.Material],
) -> None:
    # Large vertical card. Generated Z drives the material's sky gradient.
    add_box(
        "Sky backdrop",
        (0.0, 8.8, 5.6),
        (54.0, 0.10, 18.0),
        materials["sky"],
        target,
    )

    # Three soft, low-frequency landscape layers.
    add_vertical_hill(
        "Far hill",
        y=7.7,
        base_z=0.40,
        height=2.15,
        width=39.0,
        center_x=-2.0,
        mat=materials["hill_far"],
        target=target,
        phase=0.3,
    )
    add_vertical_hill(
        "Mid hill",
        y=6.5,
        base_z=0.28,
        height=1.85,
        width=35.0,
        center_x=3.5,
        mat=materials["hill_mid"],
        target=target,
        phase=1.2,
    )
    add_vertical_hill(
        "Near hill",
        y=5.3,
        base_z=0.16,
        height=1.55,
        width=31.0,
        center_x=-2.5,
        mat=materials["hill_near"],
        target=target,
        phase=2.0,
    )


def build_stone_walkway(
    target: bpy.types.Collection,
    mat: bpy.types.Material,
) -> None:
    """Constant-width stone walkway; camera perspective creates the taper."""
    y_front = -15.1
    y_back = -1.76
    width = 2.05
    slab_count = 10
    gap = 0.055
    total = y_back - y_front
    slab_length = (total - gap * (slab_count - 1)) / slab_count

    for index in range(slab_count):
        y0 = y_front + index * (slab_length + gap)
        center_y = y0 + slab_length * 0.5
        add_box(
            f"Walkway slab {index + 1:02d}",
            (0.0, center_y, 0.055),
            (width, slab_length, 0.11),
            mat,
            target,
            bevel=0.035,
        )

    path_length = y_back - y_front
    center_y = (y_front + y_back) * 0.5
    for side in (-1, 1):
        add_box(
            f"Walkway edge {'L' if side < 0 else 'R'}",
            (side * (width * 0.5 + 0.075), center_y, 0.075),
            (0.10, path_length, 0.15),
            mat,
            target,
            bevel=0.025,
        )


def build_ground_and_path(
    landscape: bpy.types.Collection,
    foreground: bpy.types.Collection,
    materials: dict[str, bpy.types.Material],
) -> None:
    add_box(
        "Landscape ground",
        (0.0, -4.2, -0.12),
        (38.0, 24.0, 0.22),
        materials["ground"],
        landscape,
        bevel=0.05,
    )

    add_box(
        "House landscape plinth",
        (0.0, 0.05, 0.035),
        (15.45, 4.75, 0.18),
        materials["ground"],
        landscape,
        bevel=0.055,
    )

    build_stone_walkway(foreground, materials["path"])


def build_one_tree(
    side: int,
    vegetation: bpy.types.Collection,
    canopy: bpy.types.Collection,
    materials: dict[str, bpy.types.Material],
) -> None:
    x = side * TREE_X
    y = TREE_Y
    trunk = materials["trunk"]

    local_segments = [
        ((0.00, 0.00, 0.04), (0.00, 0.00, 3.46), 0.145, 0.082),
        ((0.00, 0.00, 1.72), (-0.74, 0.05, 2.68), 0.090, 0.040),
        ((0.00, 0.00, 2.02), (0.81, -0.02, 2.98), 0.085, 0.039),
        ((0.00, 0.00, 2.43), (-0.52, 0.02, 3.61), 0.070, 0.031),
        ((0.00, 0.00, 2.66), (0.61, 0.03, 3.79), 0.067, 0.030),
        ((-0.38, 0.04, 2.44), (-1.10, 0.03, 3.24), 0.046, 0.021),
        ((0.42, 0.00, 2.61), (1.12, 0.04, 3.34), 0.045, 0.020),
        ((-0.30, 0.02, 3.14), (-0.82, 0.05, 4.08), 0.039, 0.016),
        ((0.35, 0.03, 3.23), (0.88, 0.04, 4.15), 0.038, 0.016),
        ((0.00, 0.00, 3.36), (0.02, 0.04, 4.40), 0.036, 0.014),
    ]

    for index, (a, b, r1, r2) in enumerate(local_segments, start=1):
        start = (x + side * a[0], y + a[1], a[2])
        end = (x + side * b[0], y + b[1], b[2])
        add_branch(
            f"{'Left' if side < 0 else 'Right'} tree branch {index:02d}",
            start,
            end,
            r1,
            r2,
            trunk,
            vegetation,
        )

    # 21 smaller overlapping clusters instead of five giant low-poly balls.
    cluster_specs: list[tuple[float, float, float, float]] = []
    layers = (
        (3.48, 0.88, 7, 0.44),
        (3.90, 1.08, 8, 0.50),
        (4.28, 0.78, 6, 0.43),
    )
    for layer_index, (z, radius, count, size) in enumerate(layers):
        for index in range(count):
            angle = (index / count) * math.tau + layer_index * 0.43
            dx = math.cos(angle) * radius * (0.70 + 0.12 * math.sin(index * 1.7))
            dy = math.sin(angle) * 0.16
            dz = 0.11 * math.sin(angle * 2.0 + layer_index)
            scale = size * (0.90 + 0.13 * math.sin(index * 2.3 + layer_index))
            cluster_specs.append((dx, dy, z + dz, scale))

    for index, (dx, dy, z, scale) in enumerate(cluster_specs, start=1):
        add_ico(
            f"{'Left' if side < 0 else 'Right'} tree canopy {index:02d}",
            (x + side * dx, y + dy, z),
            (scale * 1.05, scale * 0.84, scale),
            materials["canopy"],
            canopy,
            subdivisions=3,
        )


def build_vegetation(
    vegetation: bpy.types.Collection,
    canopy: bpy.types.Collection,
    flowers: bpy.types.Collection,
    snow_caps: bpy.types.Collection,
    materials: dict[str, bpy.types.Material],
) -> None:
    build_one_tree(-1, vegetation, canopy, materials)
    build_one_tree(1, vegetation, canopy, materials)

    for index, (x, y, z, scale) in enumerate(SHRUB_LAYOUT, start=1):
        lobes = (
            (-0.28, 0.00, -0.02, 0.78),
            (0.24, 0.02, 0.00, 0.74),
            (0.00, -0.03, 0.18, 0.90),
        )
        for lobe_index, (dx, dy, dz, mul) in enumerate(lobes, start=1):
            add_ico(
                f"Shrub {index:02d}-{lobe_index}",
                (x + dx * scale, y + dy * scale, z + dz * scale),
                (
                    scale * mul,
                    scale * mul * 0.82,
                    scale * mul * 0.72,
                ),
                materials["shrub"],
                vegetation,
                subdivisions=3,
            )

        add_ico(
            f"Shrub snow cap {index:02d}",
            (x, y - 0.015, z + scale * 0.43),
            (scale * 0.95, scale * 0.75, scale * 0.34),
            materials["snow"],
            snow_caps,
            subdivisions=3,
        )

    flower_offsets = (
        (-0.15, 0.00, 0.00),
        (-0.07, -0.03, 0.08),
        (0.03, 0.03, 0.02),
        (0.11, -0.02, 0.07),
        (0.17, 0.03, 0.01),
    )
    for index, (x, y, z) in enumerate(FLOWER_LAYOUT, start=1):
        for offset_index, (dx, dy, dz) in enumerate(flower_offsets, start=1):
            add_ico(
                f"Flower {index:02d}-{offset_index}",
                (x + dx, y + dy, z + dz),
                (0.075, 0.065, 0.065),
                materials["flower"],
                flowers,
                subdivisions=2,
            )


def build_seasonal_accents(
    season_collections: dict[str, bpy.types.Collection],
    materials: dict[str, bpy.types.Material],
) -> None:
    # SPRING — a few petals, mostly at the tree edges.
    spring = season_collections["spring"]
    spring_petals = (
        (-8.55, -0.35, 4.28),
        (-7.72, -0.28, 3.72),
        (-8.15, -1.10, 3.28),
        (8.55, -0.35, 4.28),
        (7.72, -0.28, 3.72),
        (8.15, -1.10, 3.28),
        (-3.35, -2.85, 1.25),
        (3.35, -2.85, 1.25),
    )
    for i, xyz in enumerate(spring_petals):
        add_leaf_disc(
            f"Spring petal {i:02d}",
            xyz,
            0.085,
            i * 0.57,
            materials["spring_accent"],
            spring,
        )

    # SUMMER — intentionally empty. The saturated canopy/grass is enough.
    # A named collection still exists so season switching stays structurally
    # identical and future summer motion can be added without changing the API.

    # AUTUMN — restrained fallen / drifting leaves.
    autumn = season_collections["autumn"]
    autumn_leaves = (
        (-8.30, -1.10, 2.65),
        (-7.62, -1.50, 1.22),
        (-5.80, -2.55, 0.32),
        (-3.80, -4.05, 0.26),
        (-2.55, -5.80, 0.23),
        (2.55, -5.80, 0.23),
        (3.80, -4.05, 0.26),
        (5.80, -2.55, 0.32),
        (7.62, -1.50, 1.22),
        (8.30, -1.10, 2.65),
    )
    for i, xyz in enumerate(autumn_leaves):
        add_leaf_disc(
            f"Autumn leaf {i:02d}",
            xyz,
            0.105,
            0.33 + i * 0.48,
            materials["autumn_accent"],
            autumn,
        )

    # WINTER — sparse fixed flakes. They provide the concept-art read while
    # leaving room for a future browser atmospheric overlay.
    winter = season_collections["winter"]
    winter_flakes = (
        (-9.2, -0.5, 6.2, 0.075),
        (-6.6, -1.2, 5.5, 0.060),
        (-4.4, -2.0, 6.7, 0.065),
        (-2.1, -1.5, 5.8, 0.055),
        (0.0, -2.5, 6.4, 0.070),
        (2.3, -0.9, 5.5, 0.050),
        (4.9, -1.6, 6.5, 0.065),
        (7.1, -0.8, 5.6, 0.060),
        (9.0, -1.5, 6.8, 0.075),
        (-7.8, -3.6, 3.2, 0.045),
        (-3.0, -4.1, 3.9, 0.048),
        (3.4, -4.2, 3.5, 0.046),
        (7.6, -3.4, 4.0, 0.050),
    )
    for i, (x, y, z, scale) in enumerate(winter_flakes):
        add_ico(
            f"Winter snowflake {i:02d}",
            (x, y, z),
            (scale, scale, scale),
            materials["snow"],
            winter,
            subdivisions=1,
        )


# =============================================================================
# CAMERA / LIGHTING / HOTSPOT
# =============================================================================


def add_area_light(
    name: str,
    location: tuple[float, float, float],
    target: tuple[float, float, float],
    energy: float,
    size: float,
    color: tuple[float, float, float],
    target_collection: bpy.types.Collection,
) -> bpy.types.Object:
    data = bpy.data.lights.new(name=name, type="AREA")
    data.energy = energy
    data.shape = "DISK"
    data.size = size
    data.color = color
    obj = bpy.data.objects.new(name, data)
    target_collection.objects.link(obj)
    obj.location = location
    target_object(obj, target)
    return obj


def build_lighting(
    lights: bpy.types.Collection,
) -> tuple[bpy.types.Object, bpy.types.Object]:
    # One broad architectural key + one broad fill: deliberately not a forest
    # of small "realism" lights.
    key = add_area_light(
        "Exterior soft key",
        (-9.5, -10.5, 12.5),
        (0.0, -0.5, 3.1),
        850.0,
        8.5,
        (0.78, 0.84, 1.0),
        lights,
    )
    fill = add_area_light(
        "Exterior broad fill",
        (7.5, -8.0, 7.0),
        (0.0, 0.0, 3.0),
        310.0,
        11.0,
        (0.74, 0.84, 1.0),
        lights,
    )
    return key, fill


def build_camera(
    cameras: bpy.types.Collection,
) -> bpy.types.Object:
    data = bpy.data.cameras.new("WORLD_CAMERA__house-exterior")
    data.lens = CAMERA_LENS_MM
    data.sensor_width = 36.0
    data.dof.use_dof = False

    obj = bpy.data.objects.new("WORLD_CAMERA__house-exterior", data)
    cameras.objects.link(obj)
    obj.location = CAMERA_LOCATION
    target_object(obj, CAMERA_TARGET)

    obj["world_view_id"] = "house-exterior"
    obj["website_fit"] = "cover"
    obj["website_object_position"] = "50% 50%"
    obj["mobile_safe_source_fraction"] = MOBILE_SAFE_SOURCE_FRACTION
    obj["composition_note"] = (
        "Keep door, pediment, circular window, and path on center axis. "
        "Mobile intentionally crops side trees and outer facade."
    )
    return obj


def add_house_hotspot(
    target_collection: bpy.types.Collection,
) -> bpy.types.Object:
    # Render-hidden, future-proof interaction source. The whole facade can be
    # projected by the existing rendered-world exporter if desired.
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0.0, -1.77, 3.45))
    obj = bpy.context.object
    obj.name = "WORLD_HOTSPOT__house"
    obj.dimensions = (14.6, 0.20, 7.25)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    move_to_collection(obj, target_collection)
    obj.display_type = "WIRE"
    obj.hide_render = True
    obj["world_hotspot_id"] = "house"
    return obj


# =============================================================================
# RENDER SETTINGS
# =============================================================================


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
        supported = {"CUDA", "OPTIX", "HIP", "METAL", "ONEAPI"}
        gpu_devices = [
            device
            for device in devices
            if getattr(device, "type", "CPU") in supported
        ]

        if not gpu_devices:
            print("No Cycles GPU device detected; using CPU.")
            return

        for device in devices:
            device.use = device in gpu_devices

        scene.cycles.device = "GPU"
        print(
            "Cycles GPU devices: "
            + ", ".join(getattr(device, "name", "GPU") for device in gpu_devices)
        )
    except Exception as exc:
        scene.cycles.device = "CPU"
        print(f"Cycles GPU setup warning; using CPU: {exc}")


def available_render_engines(scene: bpy.types.Scene) -> set[str]:
    """
    Return the render-engine identifiers supported by THIS Blender build.

    Eevee's identifier changed across Blender versions:
      older Blender: BLENDER_EEVEE
      newer Blender: BLENDER_EEVEE_NEXT

    Never assign either identifier blindly. Unsupported enum assignment raises
    TypeError immediately, before any normal fallback can run.
    """
    try:
        engine_property = scene.render.bl_rna.properties["engine"]
        return {item.identifier for item in engine_property.enum_items}
    except Exception:
        # Conservative fallback for unusual builds.
        return {"BLENDER_EEVEE", "BLENDER_WORKBENCH", "CYCLES"}


def set_preview_render_engine(scene: bpy.types.Scene) -> str:
    """Select the best Eevee-compatible preview engine actually available."""
    engines = available_render_engines(scene)

    if "BLENDER_EEVEE_NEXT" in engines:
        selected = "BLENDER_EEVEE_NEXT"
    elif "BLENDER_EEVEE" in engines:
        selected = "BLENDER_EEVEE"
    elif "BLENDER_WORKBENCH" in engines:
        selected = "BLENDER_WORKBENCH"
    elif "CYCLES" in engines:
        selected = "CYCLES"
    else:
        raise RuntimeError(
            "No supported render engine found. Blender reports: "
            + ", ".join(sorted(engines))
        )

    scene.render.engine = selected
    print(f"Preview render engine: {selected}")
    return selected


def configure_render(scene: bpy.types.Scene) -> None:
    preset = QUALITY_PRESETS[QUALITY]
    engines = available_render_engines(scene)

    # Cycles is the authored look. PREVIEW uses low-sample Cycles + denoising
    # whenever available so preview does not look like a different art style.
    if "CYCLES" in engines:
        try:
            scene.render.engine = "CYCLES"
            scene.cycles.samples = preset["samples"]
            scene.cycles.use_denoising = True
            scene.cycles.preview_samples = min(24, preset["samples"])
            scene.cycles.use_adaptive_sampling = True
            scene.cycles.adaptive_threshold = (
                0.040 if QUALITY == "PREVIEW"
                else 0.024 if QUALITY == "WEB"
                else 0.014
            )
            configure_cycles_device(scene)
        except Exception as exc:
            print(
                "Cycles setup warning; falling back to best supported preview engine: "
                f"{exc}"
            )
            set_preview_render_engine(scene)
    else:
        set_preview_render_engine(scene)

    scene.render.resolution_x = preset["width"]
    scene.render.resolution_y = preset["height"]
    scene.render.resolution_percentage = 100

    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.film_transparent = False

    try:
        scene.view_settings.view_transform = "AgX"
    except Exception:
        pass

    try:
        scene.view_settings.look = "AgX - Medium High Contrast"
    except Exception:
        try:
            scene.view_settings.look = "Medium High Contrast"
        except Exception:
            pass

    scene.view_settings.exposure = 0.10

    world = scene.world or bpy.data.worlds.new("House exterior world")
    scene.world = world
    world.use_nodes = True


# =============================================================================
# SEASON SWITCHING
# =============================================================================


def apply_season(
    scene: bpy.types.Scene,
    parts: SceneParts,
    season: str,
) -> None:
    style = STYLES[season]
    mats = parts.materials

    set_sky_gradient(mats["sky"], style.sky_bottom, style.sky_top)
    set_material_color(mats["hill_far"], style.hill_far)
    set_material_color(mats["hill_mid"], style.hill_mid)
    set_material_color(mats["hill_near"], style.hill_near)
    set_material_color(mats["ground"], style.ground)
    set_material_color(mats["shrub"], style.shrub)
    set_material_color(mats["canopy"], style.canopy)
    set_material_color(mats["flower"], style.flower)
    set_material_color(mats["trunk"], style.trunk)
    set_material_color(mats["path"], style.path)
    set_material_color(mats["snow"], style.snow)

    set_glow(
        mats["window_glow"],
        style.window_color,
        style.window_strength,
    )

    parts.canopy.hide_render = not style.show_canopy
    parts.canopy.hide_viewport = not style.show_canopy

    parts.flowers.hide_render = not style.show_flowers
    parts.flowers.hide_viewport = not style.show_flowers

    parts.snow_caps.hide_render = not style.show_snow_caps
    parts.snow_caps.hide_viewport = not style.show_snow_caps

    for season_name, season_collection in parts.seasonal.items():
        visible = season_collection.name == style.accent_collection
        season_collection.hide_render = not visible
        season_collection.hide_viewport = not visible

    parts.key_light.data.color = style.key_color
    parts.key_light.data.energy = style.key_energy
    parts.fill_light.data.color = style.fill_color
    parts.fill_light.data.energy = style.fill_energy

    world = scene.world
    if world and world.use_nodes:
        background = world.node_tree.nodes.get("Background")
        if background:
            background.inputs["Color"].default_value = (
                *style.world_color,
                1.0,
            )
            background.inputs["Strength"].default_value = style.world_strength

    scene["hecate_season"] = season
    print(f"Applied season: {season}")


def render_season(
    scene: bpy.types.Scene,
    parts: SceneParts,
    season: str,
) -> Path:
    apply_season(scene, parts, season)
    PUBLIC_RENDER_DIR.mkdir(parents=True, exist_ok=True)
    output = PUBLIC_RENDER_DIR / f"{season}.png"
    scene.render.filepath = str(output)
    bpy.ops.render.render(write_still=True)
    print(f"Rendered {season} -> {output}")
    return output


# =============================================================================
# BUILD
# =============================================================================


def create_materials() -> dict[str, bpy.types.Material]:
    winter = STYLES["winter"]
    return {
        "sky": sky_gradient_material(
            "Exterior sky gradient",
            winter.sky_bottom,
            winter.sky_top,
        ),
        "hill_far": material(
            "Far hill", winter.hill_far,
            roughness=0.93, variation=0.025, noise_scale=1.4,
        ),
        "hill_mid": material(
            "Mid hill", winter.hill_mid,
            roughness=0.92, variation=0.035, noise_scale=1.8,
        ),
        "hill_near": material(
            "Near hill", winter.hill_near,
            roughness=0.91, variation=0.045, noise_scale=2.2,
        ),
        "ground": material(
            "Landscape ground", winter.ground,
            roughness=0.94, variation=0.075, bump=0.12,
            noise_scale=5.0, noise_detail=2.0,
        ),
        "path": material(
            "Quiet stone path", winter.path,
            roughness=0.86, variation=0.055, bump=0.10,
            noise_scale=7.0, noise_detail=2.2,
        ),
        "trunk": material(
            "Tree wood", winter.trunk,
            roughness=0.89, variation=0.11, bump=0.18,
            noise_scale=4.0, noise_detail=2.4,
        ),
        "shrub": material(
            "Shrub foliage", winter.shrub,
            roughness=0.90, variation=0.085, bump=0.07,
            noise_scale=3.6, noise_detail=2.0,
        ),
        "canopy": material(
            "Tree canopy", winter.canopy,
            roughness=0.91, variation=0.10, bump=0.065,
            noise_scale=4.0, noise_detail=2.0,
        ),
        "flower": material(
            "Flowers", winter.flower,
            roughness=0.82, variation=0.08, noise_scale=6.0,
        ),
        "snow": material(
            "Soft snow", winter.snow,
            roughness=0.98, variation=0.025, bump=0.035,
            noise_scale=8.0,
        ),
        "spring_accent": material(
            "Spring petals",
            (0.91, 0.58, 0.69, 1.0),
            roughness=0.84, variation=0.06, noise_scale=5.0,
        ),
        "autumn_accent": material(
            "Autumn leaves",
            (0.70, 0.25, 0.06, 1.0),
            roughness=0.86, variation=0.10, noise_scale=5.0,
        ),
        "window_glow": glowing_material(
            "Seasonal warm window glow",
            winter.window_color,
            winter.window_strength,
        ),
    }


def build_scene() -> SceneParts:
    clear_scene()

    scene = bpy.context.scene
    scene.name = "Hecate946 House Exterior 2.5D"
    scene["hecate_scene_style"] = "restrained-neoclassical-maquette"
    scene["hecate_scene_version"] = SCRIPT_VERSION
    scene["hecate_scene_thesis"] = "house / path / season / stillness"
    scene["responsive_strategy"] = "16:9 master; centered cover crop on narrow viewports"
    scene["mobile_safe_source_fraction"] = MOBILE_SAFE_SOURCE_FRACTION

    root = collection("WORLD__house-exterior")
    background = collection("WORLD_BACKGROUND", root)
    landscape = collection("WORLD_MIDGROUND__landscape", root)
    vegetation = collection("WORLD_MIDGROUND__vegetation", root)
    foreground = collection("WORLD_FOREGROUND", root)
    house_parent = collection("WORLD_HOUSE_SOURCE", root)
    canopy = collection("WORLD_VEGETATION__canopy", vegetation)
    flowers = collection("WORLD_VEGETATION__flowers", vegetation)
    snow_caps = collection("WORLD_VEGETATION__snow-caps", vegetation)
    interactions = collection("WORLD_INTERACTION", root)
    cameras = collection("WORLD_CAMERAS", root)
    lights = collection("WORLD_LIGHTS", root)
    seasonal_root = collection("WORLD_SEASONAL", root)
    season_collections = {
        season: collection(f"SEASON__{season}", seasonal_root)
        for season in SEASONS
    }

    materials = create_materials()

    imported = append_house(house_parent)
    # Preserve the exact house materials from house.blend.

    build_background(background, materials)
    build_ground_and_path(landscape, foreground, materials)
    build_vegetation(
        vegetation,
        canopy,
        flowers,
        snow_caps,
        materials,
    )
    build_seasonal_accents(season_collections, materials)
    key, fill = build_lighting(lights)
    camera = build_camera(cameras)
    add_house_hotspot(interactions)

    scene.camera = camera
    configure_render(scene)

    parts = SceneParts(
        root=root,
        background=background,
        landscape=landscape,
        vegetation=vegetation,
        foreground=foreground,
        seasonal=season_collections,
        lights=lights,
        cameras=cameras,
        house_parent=house_parent,
        canopy=canopy,
        flowers=flowers,
        snow_caps=snow_caps,
        materials=materials,
        key_light=key,
        fill_light=fill,
        camera=camera,
    )
    return parts


def main() -> None:
    print("=" * 78)
    print("HECATE946 HOUSE EXTERIOR 2.5D")
    print(f"Version: {SCRIPT_VERSION}")
    print(f"Quality: {QUALITY}")
    print(f"House source: {HOUSE_BLEND}")
    print("=" * 78)

    SCRIPT_DIR.mkdir(parents=True, exist_ok=True)
    PUBLIC_RENDER_DIR.mkdir(parents=True, exist_ok=True)

    parts = build_scene()
    scene = bpy.context.scene

    # Save the master with the user's preferred winter state active.
    apply_season(scene, parts, DEFAULT_SEASON)
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH))
    print(f"Saved modular exterior -> {BLEND_PATH}")

    if AUTO_RENDER:
        for season in RENDER_SEASONS:
            render_season(scene, parts, season)

        # Restore the configured default after batch rendering, then save again
        # so opening the .blend never leaves it in an arbitrary last-render state.
        apply_season(scene, parts, DEFAULT_SEASON)
        bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH))

    print("=" * 78)
    print("HOUSE EXTERIOR BUILD COMPLETE")
    print(f"Blend: {BLEND_PATH}")
    if AUTO_RENDER:
        for season in RENDER_SEASONS:
            print(f"{season.title():>7}: {PUBLIC_RENDER_DIR / f'{season}.png'}")
    print("=" * 78)


if __name__ == "__main__":
    main()
