"""
HECATE946.COM — PROFESSIONAL SEASONAL HOUSE EXTERIOR (v7 realism pass) (v4 scene cleanup pass) (v2 composition pass)
====================================================

Target Blender: 5.2.0 LTS
Renderer: Cycles
Website model: pre-rendered 2.5D

This is the "Option B" exterior:
- the exact existing house is imported from blender/house/house.blend
- professional CC0 botanical assets and HDRI are used as source material
- Python owns the complete scene assembly
- the same geometry / camera / landscaping positions persist between seasons
- season changes are material / visibility / snow / lighting changes only
- the final website still receives four flat PNGs

GPU texture warnings
--------------------
Some imported asset libraries may log GPU texture creation warnings in the
interactive viewport. If the final PNG renders correctly, those warnings are
usually non-fatal. This composition pass reduces dependence on bright window
cards and improves the scene framing, which were the main visible issues.

The composition is intentionally wide because it lives between the site's header
and footer on desktop. Narrow/mobile screens use a centered cover crop; the door,
central pediment, circular window and path stay on the center axis.

Outputs
-------
blender/house/exterior/exterior-pro.blend
public/scenes/house/exterior/spring.png
public/scenes/house/exterior/summer.png
public/scenes/house/exterior/autumn.png
public/scenes/house/exterior/winter.png
"""

from __future__ import annotations

import json
import math
import os
import random
import warnings
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import bpy
from mathutils import Vector

warnings.filterwarnings(
    "ignore", category=DeprecationWarning,
    message=r".*Material\\.use_nodes.*",
)

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from blender.shared.render_compat import set_cycles_or_best


# =============================================================================
# PATHS / BUILD CONTROLS
# =============================================================================

HOUSE_BLEND = PROJECT_ROOT / "blender" / "house" / "house.blend"
ASSET_ROOT = PROJECT_ROOT / "blender" / "assets" / "exterior" / "polyhaven"
ASSET_MANIFEST = ASSET_ROOT / "manifest.local.json"
BLEND_OUTPUT = SCRIPT_DIR / "exterior-pro.blend"
PUBLIC_OUTPUT = PROJECT_ROOT / "public" / "scenes" / "house" / "exterior"

SEASONS = ("spring", "summer", "autumn", "winter")
QUALITY = os.environ.get("HECATE_EXTERIOR_QUALITY", "PREVIEW").strip().upper()
DEFAULT_SEASON = os.environ.get("HECATE_EXTERIOR_DEFAULT_SEASON", "winter").strip().lower()
RENDER_SEASONS = tuple(
    item.strip().lower()
    for item in os.environ.get("HECATE_EXTERIOR_SEASONS", ",".join(SEASONS)).split(",")
    if item.strip()
)
AUTO_RENDER = os.environ.get("HECATE_EXTERIOR_RENDER", "1").strip().lower() not in {
    "0", "false", "off", "no",
}

QUALITY_PRESETS = {
    # Same wide desktop aspect as the visible area between header/footer.
    "PREVIEW": {"x": 1600, "y": 750, "samples": 48, "noise": 0.040},
    "WEB": {"x": 2560, "y": 1200, "samples": 160, "noise": 0.016},
    "FINAL": {"x": 3840, "y": 1800, "samples": 320, "noise": 0.008},
}

if QUALITY not in QUALITY_PRESETS:
    raise ValueError("HECATE_EXTERIOR_QUALITY must be PREVIEW, WEB, or FINAL.")
if DEFAULT_SEASON not in SEASONS:
    raise ValueError("Invalid default season.")
if any(season not in SEASONS for season in RENDER_SEASONS):
    raise ValueError("HECATE_EXTERIOR_SEASONS contains an invalid season.")

HOUSE_WIDTH = 14.0
HOUSE_DEPTH = 3.10
HOUSE_FRONT_Y = -HOUSE_DEPTH / 2.0

# Long-lens calm architectural composition.
CAMERA_LOCATION = (0.0, -46.0, 4.45)
CAMERA_TARGET = (0.0, -1.05, 3.12)
CAMERA_LENS = 70.0

TREE_X = 11.8
TREE_Y = 1.90

SHRUB_POSITIONS = ()

FLOWER_POSITIONS = ()


@dataclass
class Season:
    world_strength: float
    sun_energy: float
    sun_angle: float
    sun_color: tuple[float, float, float]
    ground_color: tuple[float, float, float, float]
    hill_far: tuple[float, float, float, float]
    hill_mid: tuple[float, float, float, float]
    hill_near: tuple[float, float, float, float]
    tree_tint: tuple[float, float, float, float]
    tree_tint_mix: float
    grass_tint: tuple[float, float, float, float]
    grass_tint_mix: float
    shrub_tint: tuple[float, float, float, float]
    shrub_tint_mix: float
    leaf_visibility: float
    grass_visibility: bool
    shrub_visibility: bool
    flower_visibility: bool
    snow_visibility: bool
    window_strength: float
    exposure: float


STYLES = {
    "spring": Season(
        world_strength=0.52,
        sun_energy=1.15,
        sun_angle=math.radians(7.0),
        sun_color=(1.0, 0.84, 0.72),
        ground_color=(0.15, 0.28, 0.11, 1.0),
        hill_far=(0.50, 0.67, 0.46, 1.0),
        hill_mid=(0.34, 0.58, 0.30, 1.0),
        hill_near=(0.24, 0.49, 0.21, 1.0),
        tree_tint=(0.98, 0.79, 0.86, 1.0),
        tree_tint_mix=0.82,
        grass_tint=(0.22, 0.47, 0.15, 1.0),
        grass_tint_mix=0.18,
        shrub_tint=(0.42, 0.61, 0.30, 1.0),
        shrub_tint_mix=0.08,
        leaf_visibility=1.0,
        grass_visibility=True,
        shrub_visibility=False,
        flower_visibility=False,
        snow_visibility=False,
        window_strength=0.0,
        exposure=0.10,
    ),
    "summer": Season(
        world_strength=0.72,
        sun_energy=1.65,
        sun_angle=math.radians(5.0),
        sun_color=(1.0, 0.94, 0.82),
        ground_color=(0.12, 0.27, 0.09, 1.0),
        hill_far=(0.36, 0.57, 0.39, 1.0),
        hill_mid=(0.23, 0.48, 0.26, 1.0),
        hill_near=(0.16, 0.40, 0.18, 1.0),
        tree_tint=(0.22, 0.45, 0.16, 1.0),
        tree_tint_mix=0.03,
        grass_tint=(0.28, 0.51, 0.19, 1.0),
        grass_tint_mix=0.03,
        shrub_tint=(0.19, 0.40, 0.14, 1.0),
        shrub_tint_mix=0.03,
        leaf_visibility=1.0,
        grass_visibility=True,
        shrub_visibility=False,
        flower_visibility=False,
        snow_visibility=False,
        window_strength=0.0,
        exposure=0.08,
    ),
    "autumn": Season(
        world_strength=0.55,
        sun_energy=1.35,
        sun_angle=math.radians(8.0),
        sun_color=(1.0, 0.58, 0.34),
        ground_color=(0.23, 0.25, 0.11, 1.0),
        hill_far=(0.40, 0.35, 0.27, 1.0),
        hill_mid=(0.29, 0.27, 0.19, 1.0),
        hill_near=(0.20, 0.22, 0.14, 1.0),
        tree_tint=(0.88, 0.24, 0.045, 1.0),
        tree_tint_mix=0.70,
        grass_tint=(0.50, 0.40, 0.15, 1.0),
        grass_tint_mix=0.35,
        shrub_tint=(0.39, 0.35, 0.12, 1.0),
        shrub_tint_mix=0.22,
        leaf_visibility=0.90,
        grass_visibility=True,
        shrub_visibility=False,
        flower_visibility=False,
        snow_visibility=False,
        window_strength=0.0,
        exposure=0.02,
    ),
    "winter": Season(
        world_strength=0.44,
        sun_energy=0.55,
        sun_angle=math.radians(14.0),
        sun_color=(0.72, 0.83, 1.0),
        ground_color=(0.34, 0.38, 0.35, 1.0),
        hill_far=(0.56, 0.63, 0.67, 1.0),
        hill_mid=(0.46, 0.54, 0.58, 1.0),
        hill_near=(0.36, 0.45, 0.48, 1.0),
        tree_tint=(0.24, 0.20, 0.17, 1.0),
        tree_tint_mix=0.0,
        grass_tint=(0.30, 0.31, 0.25, 1.0),
        grass_tint_mix=0.0,
        shrub_tint=(0.18, 0.24, 0.16, 1.0),
        shrub_tint_mix=0.08,
        leaf_visibility=0.0,
        grass_visibility=False,
        shrub_visibility=False,
        flower_visibility=False,
        snow_visibility=True,
        window_strength=0.0,
        exposure=0.20,
    ),
}


# =============================================================================
# CORE HELPERS
# =============================================================================


def clear_scene() -> None:
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")

    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)

    scene = bpy.context.scene
    for child in list(scene.collection.children):
        scene.collection.children.unlink(child)

    for block_collection in (
        bpy.data.collections,
        bpy.data.meshes,
        bpy.data.curves,
        bpy.data.cameras,
        bpy.data.lights,
    ):
        for block in list(block_collection):
            if getattr(block, "users", 0) == 0:
                try:
                    block_collection.remove(block)
                except Exception:
                    pass


def new_collection(name: str, parent: bpy.types.Collection | None = None):
    result = bpy.data.collections.new(name)
    if parent is None:
        bpy.context.scene.collection.children.link(result)
    else:
        parent.children.link(result)
    return result


def move_to_collection(obj: bpy.types.Object, target: bpy.types.Collection) -> None:
    for old in list(obj.users_collection):
        old.objects.unlink(obj)
    target.objects.link(obj)


def look_at(obj: bpy.types.Object, target: Iterable[float]) -> None:
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def all_collection_objects(collection: bpy.types.Collection) -> list[bpy.types.Object]:
    result = list(collection.objects)
    for child in collection.children:
        result.extend(all_collection_objects(child))
    return result


def bounds_of(objects: list[bpy.types.Object]) -> tuple[Vector, Vector] | None:
    bpy.context.view_layer.update()
    points: list[Vector] = []
    for obj in objects:
        if obj.type not in {"MESH", "CURVE", "SURFACE", "FONT"}:
            continue
        for corner in obj.bound_box:
            points.append(obj.matrix_world @ Vector(corner))
    if not points:
        return None
    return (
        Vector((
            min(p.x for p in points),
            min(p.y for p in points),
            min(p.z for p in points),
        )),
        Vector((
            max(p.x for p in points),
            max(p.y for p in points),
            max(p.z for p in points),
        )),
    )


def material_simple(
    name: str,
    color: tuple[float, float, float, float],
    *,
    roughness: float = 0.75,
    metallic: float = 0.0,
):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = color
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    return mat


def set_principled_color(mat: bpy.types.Material, color) -> None:
    if not mat.use_nodes:
        mat.diffuse_color = color
        return
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = color


def load_image(path: Path, *, non_color: bool = False) -> bpy.types.Image:
    image = bpy.data.images.load(str(path), check_existing=True)
    if non_color:
        try:
            image.colorspace_settings.name = "Non-Color"
        except Exception:
            pass
    return image


def pbr_material(
    name: str,
    diffuse: Path,
    *,
    roughness: Path | None = None,
    normal: Path | None = None,
    displacement: Path | None = None,
    scale: float = 5.0,
):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Roughness"].default_value = 0.78

    texcoord = nodes.new("ShaderNodeTexCoord")
    mapping = nodes.new("ShaderNodeMapping")
    mapping.inputs["Scale"].default_value = (scale, scale, scale)
    links.new(texcoord.outputs["Generated"], mapping.inputs["Vector"])

    color_tex = nodes.new("ShaderNodeTexImage")
    color_tex.image = load_image(diffuse)
    color_tex.extension = "REPEAT"
    links.new(mapping.outputs["Vector"], color_tex.inputs["Vector"])
    links.new(color_tex.outputs["Color"], bsdf.inputs["Base Color"])

    if roughness and roughness.exists():
        rough_tex = nodes.new("ShaderNodeTexImage")
        rough_tex.image = load_image(roughness, non_color=True)
        rough_tex.extension = "REPEAT"
        links.new(mapping.outputs["Vector"], rough_tex.inputs["Vector"])
        links.new(rough_tex.outputs["Color"], bsdf.inputs["Roughness"])

    if normal and normal.exists():
        normal_tex = nodes.new("ShaderNodeTexImage")
        normal_tex.image = load_image(normal, non_color=True)
        normal_tex.extension = "REPEAT"
        normal_node = nodes.new("ShaderNodeNormalMap")
        normal_node.space = "TANGENT"
        normal_node.inputs["Strength"].default_value = 0.38
        links.new(mapping.outputs["Vector"], normal_tex.inputs["Vector"])
        links.new(normal_tex.outputs["Color"], normal_node.inputs["Color"])
        links.new(normal_node.outputs["Normal"], bsdf.inputs["Normal"])

    if displacement and displacement.exists():
        disp_tex = nodes.new("ShaderNodeTexImage")
        disp_tex.image = load_image(displacement, non_color=True)
        disp_tex.extension = "REPEAT"
        bump = nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = 0.16
        bump.inputs["Distance"].default_value = 0.07
        links.new(mapping.outputs["Vector"], disp_tex.inputs["Vector"])
        links.new(disp_tex.outputs["Color"], bump.inputs["Height"])
        if not normal or not normal.exists():
            links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


def add_box(name, location, dimensions, mat, collection, bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel:
        modifier = obj.modifiers.new("Soft edge", "BEVEL")
        modifier.width = bevel
        modifier.segments = 3
    obj.data.materials.append(mat)
    move_to_collection(obj, collection)
    return obj


# =============================================================================
# HOUSE
# =============================================================================


def ensure_house_blend() -> None:
    if HOUSE_BLEND.exists():
        return

    raise FileNotFoundError(
        "This exterior builder imports the existing house directly from "
        f"{HOUSE_BLEND}. It will not recreate the house procedurally. "
        "Please generate or restore house.blend first, then rerun this builder."
    )


def append_house(target: bpy.types.Collection) -> list[bpy.types.Object]:
    required = {"Architecture", "Windows", "Door", "Roof"}

    with bpy.data.libraries.load(str(HOUSE_BLEND), link=False) as (data_from, data_to):
        available = set(data_from.collections)
        missing = sorted(required - available)
        if missing:
            raise RuntimeError(f"house.blend missing collections: {missing}")
        data_to.collections = [name for name in required]

    imported_collections = [
        collection for collection in data_to.collections if collection is not None
    ]

    seen = set()
    objects = []
    for source_collection in imported_collections:
        for obj in all_collection_objects(source_collection):
            if obj.name in seen:
                continue
            seen.add(obj.name)
            objects.append(obj)
            if target.objects.get(obj.name) is None:
                target.objects.link(obj)
            obj.hide_render = False
            obj.hide_viewport = False
            try:
                obj.hide_set(False)
            except Exception:
                pass

    bounds = bounds_of(objects)
    if bounds is None:
        raise RuntimeError("House import contains no visible geometry.")

    minimum, maximum = bounds
    width = maximum.x - minimum.x
    root = bpy.data.objects.new("HOUSE__ROOT", None)
    target.objects.link(root)

    object_set = set(objects)
    for obj in objects:
        if obj.parent is None or obj.parent not in object_set:
            matrix = obj.matrix_world.copy()
            obj.parent = root
            obj.matrix_world = matrix

    root.scale = (HOUSE_WIDTH / width,) * 3
    bpy.context.view_layer.update()
    minimum, maximum = bounds_of(objects)
    center = (minimum + maximum) * 0.5
    root.location += Vector((-center.x, -center.y, -minimum.z))
    bpy.context.view_layer.update()

    minimum, maximum = bounds_of(objects)
    print(
        "HOUSE IMPORT OK — "
        f"{len(objects)} objects, "
        f"bounds ({minimum.x:.2f},{minimum.y:.2f},{minimum.z:.2f}) "
        f"to ({maximum.x:.2f},{maximum.y:.2f},{maximum.z:.2f})"
    )
    return objects


def add_window_glow(collection: bpy.types.Collection):
    """
    Compatibility stub: the visible orange facade overlays have been removed.
    The house should render exactly as imported from house.blend.
    """
    glow = material_simple(
        "Inactive window glow",
        (0.0, 0.0, 0.0, 1.0),
        roughness=1.0,
    )
    bsdf = glow.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        emission_color = bsdf.inputs.get("Emission Color") or bsdf.inputs.get("Emission")
        if emission_color:
            emission_color.default_value = (0.0, 0.0, 0.0, 1.0)
        strength = bsdf.inputs.get("Emission Strength")
        if strength:
            strength.default_value = 0.0
    cards: list[bpy.types.Object] = []
    return glow, cards




def grass_material(name: str):
    """
    Darker, richer lawn material for the website exterior.

    Blender 5.2-safe: uses supported Noise nodes only.
    """
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Roughness"].default_value = 0.72
    bsdf.inputs["Subsurface Weight"].default_value = 0.03
    bsdf.inputs["Subsurface Scale"].default_value = 0.015
    bsdf.inputs["Specular IOR Level"].default_value = 0.34

    texcoord = nodes.new("ShaderNodeTexCoord")
    mapping = nodes.new("ShaderNodeMapping")
    mapping.inputs["Scale"].default_value = (2.35, 2.35, 2.35)

    broad_noise = nodes.new("ShaderNodeTexNoise")
    broad_noise.inputs["Scale"].default_value = 3.6
    broad_noise.inputs["Detail"].default_value = 4.5
    broad_noise.inputs["Roughness"].default_value = 0.48

    fine_noise = nodes.new("ShaderNodeTexNoise")
    fine_noise.name = "Fine lawn variation"
    fine_noise.inputs["Scale"].default_value = 26.0
    if "Detail" in fine_noise.inputs:
        fine_noise.inputs["Detail"].default_value = 8.0
    if "Roughness" in fine_noise.inputs:
        fine_noise.inputs["Roughness"].default_value = 0.42

    color_ramp = nodes.new("ShaderNodeValToRGB")
    color_ramp.color_ramp.elements[0].position = 0.22
    color_ramp.color_ramp.elements[0].color = (0.11, 0.27, 0.08, 1.0)
    color_ramp.color_ramp.elements[1].position = 0.82
    color_ramp.color_ramp.elements[1].color = (0.26, 0.49, 0.17, 1.0)

    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.05
    bump.inputs["Distance"].default_value = 0.05

    links.new(texcoord.outputs["Object"], mapping.inputs["Vector"])
    links.new(mapping.outputs["Vector"], broad_noise.inputs["Vector"])
    links.new(mapping.outputs["Vector"], fine_noise.inputs["Vector"])
    links.new(broad_noise.outputs["Fac"], color_ramp.inputs["Fac"])
    links.new(color_ramp.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(fine_noise.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


def plant_material(name: str, base=(0.16, 0.28, 0.14, 1.0), roughness=0.82):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = base
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Subsurface Weight"].default_value = 0.02
    bsdf.inputs["Subsurface Scale"].default_value = 0.01
    return mat


def flower_material(name: str):
    return plant_material(name, base=(0.90, 0.72, 0.78, 1.0), roughness=0.76)


def create_procedural_lawn_mesh(
    collection: bpy.types.Collection,
    material: bpy.types.Material,
    *,
    count: int,
) -> bpy.types.Object:
    """
    Denser fixed-camera lawn with finer grass needles.
    """
    rng = random.Random(946)
    vertices = []
    faces = []

    x_min, x_max = -10.75, 10.75
    y_min, y_max = -8.15, 2.55
    z0 = 0.035

    made = 0
    attempts = 0
    while made < count and attempts < count * 7:
        attempts += 1
        x = rng.uniform(x_min, x_max)
        y = rng.uniform(y_min, y_max)

        if y < -1.55 and abs(x) < 1.42:
            continue
        if -1.65 <= y <= 0.18 and abs(x) < 1.76:
            continue
        if y > 1.78 and rng.random() < 0.40:
            continue

        depth = max(0.0, min(1.0, (2.55 - y) / 10.70))
        height = rng.uniform(0.11, 0.22) * (0.80 + depth * 0.42)
        half_w = rng.uniform(0.0035, 0.0075)
        base_angle = rng.uniform(0.0, math.tau)
        lean = rng.uniform(0.006, 0.020)
        lean_angle = rng.uniform(0.0, math.tau)
        lx = math.cos(lean_angle) * lean
        ly = math.sin(lean_angle) * lean

        # Three crossed blades per tuft for fuller, more realistic coverage.
        for cross in (0.0, math.pi / 3.0, 2.0 * math.pi / 3.0):
            angle = base_angle + cross
            dx = math.cos(angle) * half_w
            dy = math.sin(angle) * half_w
            tx = dx * 0.14
            ty = dy * 0.14

            i = len(vertices)
            vertices.extend([
                (x - dx, y - dy, z0),
                (x + dx, y + dy, z0),
                (x + lx + tx, y + ly + ty, z0 + height),
                (x + lx - tx, y + ly - ty, z0 + height),
            ])
            faces.append((i, i + 1, i + 2, i + 3))

        made += 1

    mesh = bpy.data.meshes.new("Procedural lawn blade mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()

    lawn = bpy.data.objects.new("Procedural Grass Blades", mesh)
    collection.objects.link(lawn)
    lawn.data.materials.append(material)
    return lawn



def yellow_brick_material(name: str):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Roughness"].default_value = 0.68
    bsdf.inputs["Specular IOR Level"].default_value = 0.28

    texcoord = nodes.new("ShaderNodeTexCoord")
    mapping = nodes.new("ShaderNodeMapping")
    mapping.inputs["Scale"].default_value = (2.2, 6.8, 1.0)

    brick = nodes.new("ShaderNodeTexBrick")
    brick.inputs["Scale"].default_value = 7.5
    brick.inputs["Mortar Size"].default_value = 0.03
    brick.inputs["Mortar Smooth"].default_value = 0.03
    brick.inputs["Bias"].default_value = 0.22
    brick.inputs["Brick Width"].default_value = 0.56
    brick.inputs["Row Height"].default_value = 0.22
    brick.inputs["Color1"].default_value = (0.92, 0.73, 0.21, 1.0)
    brick.inputs["Color2"].default_value = (0.84, 0.61, 0.12, 1.0)
    brick.inputs["Mortar"].default_value = (0.58, 0.42, 0.12, 1.0)

    noise = nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 18.0
    noise.inputs["Detail"].default_value = 6.0
    noise.inputs["Roughness"].default_value = 0.46

    mix = nodes.new("ShaderNodeMixRGB")
    mix.blend_type = "MULTIPLY"
    mix.inputs[0].default_value = 0.18
    mix.inputs[2].default_value = (0.96, 0.92, 0.84, 1.0)

    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.08
    bump.inputs["Distance"].default_value = 0.03

    links.new(texcoord.outputs["Generated"], mapping.inputs["Vector"])
    links.new(mapping.outputs["Vector"], brick.inputs["Vector"])
    links.new(mapping.outputs["Vector"], noise.inputs["Vector"])
    links.new(brick.outputs["Color"], mix.inputs[1])
    links.new(mix.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(noise.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


def blossom_material(name: str):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (0.98, 0.82, 0.88, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.76
    bsdf.inputs["Subsurface Weight"].default_value = 0.03
    bsdf.inputs["Subsurface Scale"].default_value = 0.02
    return mat


def add_cherry_blossom_canopy(collection: bpy.types.Collection, material: bpy.types.Material, center_x: float, center_y: float, tree_height: float):
    rng = random.Random(int((center_x + 20.0) * 100))
    canopy_center_z = tree_height * 0.70
    offsets = [
        (-0.65, -0.10, -0.10, 0.90),
        (-0.25, 0.15, 0.10, 0.88),
        (0.20, -0.05, 0.18, 0.98),
        (0.55, 0.12, -0.05, 0.82),
        (0.00, 0.30, 0.05, 1.05),
        (-0.42, 0.36, 0.22, 0.76),
        (0.42, 0.34, 0.22, 0.74),
    ]
    for idx, (ox, oy, oz, scale) in enumerate(offsets, start=1):
        bpy.ops.mesh.primitive_ico_sphere_add(
            subdivisions=3,
            radius=0.62 * scale,
            location=(center_x + ox, center_y + oy, canopy_center_z + oz),
        )
        obj = bpy.context.object
        obj.name = f"Cherry blossom canopy {center_x:+.2f} {idx:02d}"
        obj.scale = (
            scale * rng.uniform(0.95, 1.16),
            scale * rng.uniform(0.88, 1.08),
            scale * rng.uniform(0.72, 0.98),
        )
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        obj.data.materials.append(material)
        move_to_collection(obj, collection)

def add_formal_shrub(collection: bpy.types.Collection, material: bpy.types.Material, name: str, location, scale: float):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=4, radius=0.5, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = (scale * 1.10, scale, scale * 0.82)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    subdiv = obj.modifiers.new("Subsurf", "SUBSURF")
    subdiv.levels = 2
    subdiv.render_levels = 2
    obj.data.materials.append(material)
    move_to_collection(obj, collection)
    return obj


def add_flower_clump(collection: bpy.types.Collection, leaf_mat: bpy.types.Material, bloom_mat: bpy.types.Material, name: str, location, scale: float):
    add_formal_shrub(collection, leaf_mat, f"{name} mound", location, scale * 0.58)
    offsets = [(-0.11, 0.00, 0.08), (0.04, 0.06, 0.10), (0.12, -0.05, 0.07), (-0.03, -0.08, 0.09)]
    for i, (dx, dy, dz) in enumerate(offsets, start=1):
        bpy.ops.mesh.primitive_uv_sphere_add(
            radius=0.028 * scale,
            location=(location[0] + dx * scale, location[1] + dy * scale, location[2] + dz * scale),
        )
        bloom = bpy.context.object
        bloom.name = f"{name} bloom {i:02d}"
        bloom.data.materials.append(bloom_mat)
        move_to_collection(bloom, collection)

# =============================================================================
# POLY HAVEN ASSET LOADING
# =============================================================================


def read_asset_manifest() -> dict:
    if not ASSET_MANIFEST.exists():
        raise FileNotFoundError(
            "Professional exterior assets are not installed.\n"
            "Run:\n"
            "  python3 blender/house/exterior/download_exterior_assets.py"
        )
    return json.loads(ASSET_MANIFEST.read_text())


def manifest_path(manifest: dict, asset_id: str, key: str) -> Path:
    value = manifest["assets"][asset_id][key]
    return PROJECT_ROOT / value


def relink_images(asset_dir: Path) -> None:
    index = {}
    for path in asset_dir.rglob("*"):
        if path.is_file():
            index.setdefault(path.name.lower(), path)

    for image in bpy.data.images:
        current = Path(bpy.path.abspath(image.filepath or ""))
        if current.exists():
            continue
        basename = Path(image.filepath or image.name).name.lower()
        match = index.get(basename)
        if match:
            image.filepath = str(match)


@dataclass
class ModelSource:
    collection: bpy.types.Collection
    objects: list[bpy.types.Object]
    materials: list[bpy.types.Material]
    bounds_min: Vector
    bounds_max: Vector


def import_blend_model(
    asset_id: str,
    blend_path: Path,
    asset_library: bpy.types.Collection,
) -> ModelSource:
    source_collection = new_collection(f"ASSET_SOURCE__{asset_id}", asset_library)

    with bpy.data.libraries.load(str(blend_path), link=False) as (data_from, data_to):
        data_to.objects = list(data_from.objects)

    objects = []
    materials = []
    seen_materials = set()

    for obj in data_to.objects:
        if obj is None or obj.type in {"CAMERA", "LIGHT"}:
            continue
        source_collection.objects.link(obj)
        objects.append(obj)

        data = getattr(obj, "data", None)
        for mat in getattr(data, "materials", []) if data else []:
            if mat and mat.name not in seen_materials:
                seen_materials.add(mat.name)
                materials.append(mat)

    relink_images(blend_path.parent)
    bounds = bounds_of(objects)
    if bounds is None:
        raise RuntimeError(f"{asset_id} imported without renderable geometry.")

    source_collection.hide_render = True
    return ModelSource(source_collection, objects, materials, bounds[0], bounds[1])


def duplicate_model(
    source: ModelSource,
    target: bpy.types.Collection,
    name: str,
    *,
    location=(0.0, 0.0, 0.0),
    scale=1.0,
    rotation_z=0.0,
):
    mapping = {}
    duplicates = []

    for obj in source.objects:
        duplicate = obj.copy()
        if obj.data is not None:
            duplicate.data = obj.data
        target.objects.link(duplicate)
        mapping[obj] = duplicate
        duplicates.append(duplicate)

    for original, duplicate in mapping.items():
        if original.parent in mapping:
            duplicate.parent = mapping[original.parent]

    root = bpy.data.objects.new(name, None)
    target.objects.link(root)

    duplicate_set = set(duplicates)
    for duplicate in duplicates:
        if duplicate.parent is None or duplicate.parent not in duplicate_set:
            matrix = duplicate.matrix_world.copy()
            duplicate.parent = root
            duplicate.matrix_world = matrix

    root.location = location
    root.scale = (scale, scale, scale)
    root.rotation_euler.z = rotation_z
    return root, duplicates


def source_height(source: ModelSource) -> float:
    return max(0.001, source.bounds_max.z - source.bounds_min.z)


def source_width(source: ModelSource) -> float:
    return max(0.001, source.bounds_max.x - source.bounds_min.x)


# =============================================================================
# SEASON SHADER CONTROLS
# =============================================================================


def material_signature(mat: bpy.types.Material) -> str:
    parts = [mat.name.lower()]
    if mat.use_nodes:
        for node in mat.node_tree.nodes:
            if node.type == "TEX_IMAGE" and node.image:
                parts.append(node.image.name.lower())
                parts.append(Path(node.image.filepath or "").name.lower())
    return " ".join(parts)


def add_material_controls(mat: bpy.types.Material, prefix: str) -> bool:
    if not mat.use_nodes:
        return False

    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    out = next((node for node in nodes if node.type == "OUTPUT_MATERIAL"), None)
    if out is None or not out.inputs["Surface"].is_linked:
        return False

    if nodes.get(f"{prefix}__VISIBILITY") is not None:
        return True

    # Visibility control wraps the entire surface in a Transparent/Mix shader.
    original_surface = out.inputs["Surface"].links[0]
    from_socket = original_surface.from_socket
    links.remove(original_surface)

    transparent = nodes.new("ShaderNodeBsdfTransparent")
    transparent.name = f"{prefix}__TRANSPARENT"

    mix_shader = nodes.new("ShaderNodeMixShader")
    mix_shader.name = f"{prefix}__MIX_SHADER"

    visibility = nodes.new("ShaderNodeValue")
    visibility.name = f"{prefix}__VISIBILITY"
    visibility.outputs[0].default_value = 1.0

    links.new(visibility.outputs[0], mix_shader.inputs[0])
    links.new(transparent.outputs[0], mix_shader.inputs[1])
    links.new(from_socket, mix_shader.inputs[2])
    links.new(mix_shader.outputs[0], out.inputs["Surface"])

    # Find the first Principled base color and insert a tint mix.
    principled = next((node for node in nodes if node.type == "BSDF_PRINCIPLED"), None)
    if principled is None:
        return True

    base = principled.inputs.get("Base Color")
    if base is None:
        return True

    tint = nodes.new("ShaderNodeMixRGB")
    tint.name = f"{prefix}__TINT"
    tint.blend_type = "MIX"
    tint.inputs[0].default_value = 0.0
    tint.inputs[2].default_value = (0.5, 0.5, 0.5, 1.0)

    if base.is_linked:
        old_link = base.links[0]
        source_socket = old_link.from_socket
        links.remove(old_link)
        links.new(source_socket, tint.inputs[1])
    else:
        tint.inputs[1].default_value = base.default_value

    links.new(tint.outputs["Color"], base)
    return True


def controlled_materials(materials, prefix: str, keywords: tuple[str, ...]):
    result = []
    for mat in materials:
        signature = material_signature(mat)
        if keywords and not any(keyword in signature for keyword in keywords):
            continue
        if add_material_controls(mat, prefix):
            result.append(mat)
    return result


def set_material_control(
    mats: list[bpy.types.Material],
    prefix: str,
    *,
    visibility: float,
    tint,
    tint_mix: float,
):
    for mat in mats:
        nodes = mat.node_tree.nodes
        visibility_node = nodes.get(f"{prefix}__VISIBILITY")
        tint_node = nodes.get(f"{prefix}__TINT")
        if visibility_node:
            visibility_node.outputs[0].default_value = visibility
        if tint_node:
            tint_node.inputs[0].default_value = tint_mix
            tint_node.inputs[2].default_value = tint


# =============================================================================
# LANDSCAPE / PATH / BACKGROUND
# =============================================================================


def add_hill_mesh(
    name: str,
    collection: bpy.types.Collection,
    material: bpy.types.Material,
    *,
    center_y: float,
    width: float,
    depth: float,
    peak: float,
    base_z: float,
    phase: float,
):
    nx = 44
    ny = 8
    verts = []
    faces = []

    for j in range(ny):
        ty = j / (ny - 1)
        y = center_y + (ty - 0.5) * depth
        for i in range(nx):
            tx = i / (nx - 1)
            x = (tx - 0.5) * width
            envelope = math.sin(math.pi * tx) ** 0.78
            rolling = (
                0.16 * math.sin(tx * math.tau * 1.7 + phase)
                + 0.08 * math.sin(tx * math.tau * 3.2 + phase * 0.6)
            )
            z = base_z + peak * max(0.0, envelope + rolling) * (0.78 + 0.22 * ty)
            verts.append((x, y, z))

    for j in range(ny - 1):
        for i in range(nx - 1):
            a = j * nx + i
            b = a + 1
            c = a + nx + 1
            d = a + nx
            faces.append((a, b, c, d))

    mesh = bpy.data.meshes.new(f"{name} mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    obj.data.materials.append(material)

    subdiv = obj.modifiers.new("Hill subdivision", "SUBSURF")
    subdiv.subdivision_type = "CATMULL_CLARK"
    subdiv.levels = 2
    subdiv.render_levels = 2
    return obj


def build_path(collection, path_material):
    y_front = -17.0
    y_back = -1.70
    width = 2.55
    slab_count = 17
    gap = 0.045
    total = y_back - y_front
    slab_length = (total - (slab_count - 1) * gap) / slab_count

    for index in range(slab_count):
        y0 = y_front + index * (slab_length + gap)
        add_box(
            f"Stone path slab {index:02d}",
            (0.0, y0 + slab_length / 2, 0.085),
            (width, slab_length, 0.16),
            path_material,
            collection,
            bevel=0.035,
        )


def build_world(hdri_path: Path):
    world = bpy.context.scene.world or bpy.data.worlds.new("Exterior World")
    bpy.context.scene.world = world
    world.use_nodes = True
    nodes = world.node_tree.nodes
    links = world.node_tree.links
    nodes.clear()

    out = nodes.new("ShaderNodeOutputWorld")
    background = nodes.new("ShaderNodeBackground")
    background.name = "HECATE_HDRI_BACKGROUND"
    background.inputs["Strength"].default_value = 0.6

    env = nodes.new("ShaderNodeTexEnvironment")
    env.image = load_image(hdri_path)

    texcoord = nodes.new("ShaderNodeTexCoord")
    mapping = nodes.new("ShaderNodeMapping")
    mapping.inputs["Rotation"].default_value[2] = math.radians(18.0)

    links.new(texcoord.outputs["Generated"], mapping.inputs["Vector"])
    links.new(mapping.outputs["Vector"], env.inputs["Vector"])
    links.new(env.outputs["Color"], background.inputs["Color"])
    links.new(background.outputs["Background"], out.inputs["Surface"])
    return background


# =============================================================================
# LIGHTING / CAMERA
# =============================================================================


def build_camera(collection):
    data = bpy.data.cameras.new("Exterior Camera")
    data.lens = CAMERA_LENS
    data.sensor_width = 36.0
    data.dof.use_dof = False

    camera = bpy.data.objects.new("Exterior Camera", data)
    collection.objects.link(camera)
    camera.location = CAMERA_LOCATION
    look_at(camera, CAMERA_TARGET)
    bpy.context.scene.camera = camera
    return camera


def build_lights(collection):
    sun_data = bpy.data.lights.new("Exterior Sun", "SUN")
    sun_data.energy = 1.0
    sun_data.angle = math.radians(7.0)
    sun = bpy.data.objects.new("Exterior Sun", sun_data)
    collection.objects.link(sun)
    sun.rotation_euler = (
        math.radians(38.0),
        math.radians(-18.0),
        math.radians(-32.0),
    )

    area_data = bpy.data.lights.new("Facade soft fill", "AREA")
    area_data.energy = 420.0
    area_data.shape = "DISK"
    area_data.size = 8.0
    area = bpy.data.objects.new("Facade soft fill", area_data)
    collection.objects.link(area)
    area.location = (-7.5, -10.5, 10.0)
    look_at(area, (0.0, 0.0, 3.4))
    return sun, area


# =============================================================================
# SCENE BUILD
# =============================================================================


@dataclass
class SceneParts:
    tree_materials: list[bpy.types.Material]
    grass_materials: list[bpy.types.Material]
    shrub_materials: list[bpy.types.Material]
    flower_materials: list[bpy.types.Material]
    grass_collection: bpy.types.Collection
    shrub_collection: bpy.types.Collection
    flower_collection: bpy.types.Collection
    blossom_collection: bpy.types.Collection
    snow_collection: bpy.types.Collection
    ground_material: bpy.types.Material
    hill_materials: tuple[bpy.types.Material, bpy.types.Material, bpy.types.Material]
    world_background: bpy.types.Node
    sun: bpy.types.Object
    window_glow: bpy.types.Material


def texture_paths(manifest: dict, asset_id: str):
    data = manifest["assets"][asset_id]
    return {
        key: PROJECT_ROOT / value
        for key, value in data.items()
        if key in {"diffuse", "roughness", "normal", "displacement"}
    }


def configure_render():
    scene = bpy.context.scene
    preset = QUALITY_PRESETS[QUALITY]
    selected = set_cycles_or_best(scene)
    print(f"Exterior render engine: {selected}")

    scene.render.resolution_x = preset["x"]
    scene.render.resolution_y = preset["y"]
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.film_transparent = False
    scene.render.image_settings.color_depth = "8"

    if selected == "CYCLES":
        scene.cycles.samples = preset["samples"]
        scene.cycles.use_adaptive_sampling = True
        scene.cycles.adaptive_threshold = preset["noise"]
        scene.cycles.use_denoising = True

        # Conservative bounce budget: enough for convincing outdoor GI without
        # wasting time on invisible caustic complexity.
        scene.cycles.max_bounces = 8
        scene.cycles.diffuse_bounces = 4
        scene.cycles.glossy_bounces = 4
        scene.cycles.transmission_bounces = 4
        scene.cycles.transparent_max_bounces = 8

        try:
            scene.cycles.use_light_tree = True
        except Exception:
            pass

    try:
        scene.view_settings.look = "AgX - Medium High Contrast"
    except Exception:
        pass


def build_scene() -> SceneParts:
    ensure_house_blend()
    manifest = read_asset_manifest()

    clear_scene()

    root = new_collection("WORLD__house-exterior-pro")
    house_col = new_collection("WORLD_HOUSE", root)
    ground_col = new_collection("WORLD_GROUND", root)
    path_col = new_collection("WORLD_PATH", root)
    hills_col = new_collection("WORLD_HILLS", root)
    trees_col = new_collection("WORLD_TREES", root)
    blossom_col = new_collection("WORLD_BLOSSOMS", root)
    grass_col = new_collection("WORLD_GRASS", root)
    shrubs_col = new_collection("WORLD_SHRUBS", root)
    flowers_col = new_collection("WORLD_FLOWERS", root)
    snow_col = new_collection("WORLD_SNOW", root)
    lights_col = new_collection("WORLD_LIGHTS", root)
    cameras_col = new_collection("WORLD_CAMERAS", root)
    asset_library = new_collection("ASSET_LIBRARY__hidden", root)

    append_house(house_col)
    window_glow, _ = add_window_glow(house_col)

    path_material = yellow_brick_material("Yellow brick road")

    ground_material = material_simple(
        "Seasonal ground underlay",
        STYLES["spring"].ground_color,
        roughness=0.94,
    )
    add_box(
        "Ground plane",
        (0.0, -4.8, -0.12),
        (46.0, 30.0, 0.24),
        ground_material,
        ground_col,
        bevel=0.05,
    )
    add_box(
        "House landscape base",
        (0.0, 0.0, 0.025),
        (16.0, 5.0, 0.18),
        ground_material,
        ground_col,
        bevel=0.06,
    )
    build_path(path_col, path_material)

    # Realistic broadleaf trees.
    tree_blend = manifest_path(manifest, "tree_small_02", "blend")
    tree_source = import_blend_model(
        "tree_small_02",
        tree_blend,
        asset_library,
    )
    desired_tree_height = 6.35
    tree_scale = desired_tree_height / source_height(tree_source)

    duplicate_model(
        tree_source,
        trees_col,
        "Tree Left",
        location=(-TREE_X, TREE_Y, 0.0),
        scale=tree_scale,
        rotation_z=math.radians(8.0),
    )
    duplicate_model(
        tree_source,
        trees_col,
        "Tree Right",
        location=(TREE_X, TREE_Y, 0.0),
        scale=tree_scale * 1.02,
        rotation_z=math.radians(196.0),
    )
    tree_materials = controlled_materials(
        tree_source.materials,
        "HECATE_TREE",
        ("leaf", "leaves"),
    )
    blossom_mat = blossom_material("Cherry blossom petals")
    add_cherry_blossom_canopy(blossom_col, blossom_mat, -TREE_X, TREE_Y, desired_tree_height)
    add_cherry_blossom_canopy(blossom_col, blossom_mat, TREE_X, TREE_Y, desired_tree_height)

    # Image-free foreground: geometry-rich lawn only.
    lawn_material = grass_material("Procedural lawn")
    add_box(
        "Lawn underlay",
        (0.0, -2.6, 0.012),
        (22.0, 10.8, 0.04),
        lawn_material,
        grass_col,
        bevel=0.02,
    )

    lawn_mesh = bpy.data.meshes.new("Lawn surface mesh")
    lawn_mesh.from_pydata(
        [(-10.5, -7.9, 0.03), (10.5, -7.9, 0.03), (10.0, 2.6, 0.03), (-10.0, 2.6, 0.03)],
        [],
        [(0, 1, 2, 3)],
    )
    lawn_mesh.update()
    lawn = bpy.data.objects.new("Formal Lawn", lawn_mesh)
    grass_col.objects.link(lawn)

    grass_count = {
        "PREVIEW": 14000,
        "WEB": 26000,
        "FINAL": 42000,
    }[QUALITY]
    create_procedural_lawn_mesh(
        grass_col,
        lawn_material,
        count=grass_count,
    )
    grass_materials = [lawn_material]

    shrub_leaf = plant_material("Formal shrub foliage", base=(0.12, 0.20, 0.11, 1.0), roughness=0.86)
    flower_leaf = plant_material("Groundcover foliage", base=(0.20, 0.29, 0.14, 1.0), roughness=0.84)
    bloom_mat = flower_material("Groundcover blossoms")

    for index, (x, y, z, scale) in enumerate(SHRUB_POSITIONS):
        add_formal_shrub(
            shrubs_col,
            shrub_leaf,
            f"Shrub {index:02d}",
            (x, y, z + scale * 0.20),
            scale * 0.70,
        )

    for index, (x, y, z, scale) in enumerate(FLOWER_POSITIONS):
        add_flower_clump(
            flowers_col,
            flower_leaf,
            bloom_mat,
            f"Flower groundcover {index:02d}",
            (x, y, z + 0.02),
            scale,
        )

    shrub_materials = [shrub_leaf]
    flower_materials = [flower_leaf, bloom_mat]

    # Background terrain is deliberately softer and simpler than the foreground.
    hill_far = material_simple("Hill far", STYLES["spring"].hill_far, roughness=0.96)
    hill_mid = material_simple("Hill mid", STYLES["spring"].hill_mid, roughness=0.95)
    hill_near = material_simple("Hill near", STYLES["spring"].hill_near, roughness=0.94)

    add_hill_mesh(
        "Far rolling hills", hills_col, hill_far,
        center_y=18.5, width=58.0, depth=8.2, peak=3.8, base_z=-0.26, phase=0.4,
    )
    add_hill_mesh(
        "Mid rolling hills", hills_col, hill_mid,
        center_y=13.8, width=48.0, depth=6.6, peak=2.8, base_z=-0.24, phase=1.5,
    )
    add_hill_mesh(
        "Near rolling hills", hills_col, hill_near,
        center_y=10.2, width=42.0, depth=5.6, peak=1.9, base_z=-0.20, phase=2.4,
    )

    # Winter snow sits above the underlay but below path slabs.
    snow_material = material_simple(
        "Soft winter snow",
        (0.86, 0.91, 0.95, 1.0),
        roughness=0.99,
    )
    add_box(
        "Winter snow field",
        (0.0, -3.8, 0.015),
        (40.0, 25.0, 0.06),
        snow_material,
        snow_col,
        bevel=0.035,
    )

    hdri = manifest_path(manifest, "kloppenheim_01_puresky", "environment")
    world_background = build_world(hdri)
    sun, _ = build_lights(lights_col)
    build_camera(cameras_col)
    configure_render()

    # The asset source library must never appear directly in the render.
    asset_library.hide_render = True

    return SceneParts(
        tree_materials=tree_materials,
        grass_materials=grass_materials,
        shrub_materials=shrub_materials,
        flower_materials=flower_materials,
        grass_collection=grass_col,
        shrub_collection=shrubs_col,
        flower_collection=flowers_col,
        blossom_collection=blossom_col,
        snow_collection=snow_col,
        ground_material=ground_material,
        hill_materials=(hill_far, hill_mid, hill_near),
        world_background=world_background,
        sun=sun,
        window_glow=window_glow,
    )


# =============================================================================
# SEASON STATE / RENDER
# =============================================================================


def set_emission_strength(material: bpy.types.Material, value: float):
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    if not bsdf:
        return
    strength = bsdf.inputs.get("Emission Strength")
    if strength:
        strength.default_value = value


def apply_season(parts: SceneParts, season_name: str):
    style = STYLES[season_name]
    scene = bpy.context.scene
    scene["hecate_season"] = season_name

    set_principled_color(parts.ground_material, style.ground_color)
    for material, color in zip(
        parts.hill_materials,
        (style.hill_far, style.hill_mid, style.hill_near),
    ):
        set_principled_color(material, color)

    set_material_control(
        parts.tree_materials,
        "HECATE_TREE",
        visibility=style.leaf_visibility,
        tint=style.tree_tint,
        tint_mix=style.tree_tint_mix,
    )
    for mat in parts.grass_materials:
        set_principled_color(mat, style.grass_tint)
    for mat in parts.shrub_materials:
        set_principled_color(mat, style.shrub_tint)
    if parts.flower_materials:
        set_principled_color(parts.flower_materials[0], (
            max(style.grass_tint[0] * 0.80, 0.02),
            max(style.grass_tint[1] * 0.80, 0.02),
            max(style.grass_tint[2] * 0.80, 0.02),
            1.0,
        ))

    parts.grass_collection.hide_render = not style.grass_visibility
    parts.grass_collection.hide_viewport = not style.grass_visibility
    parts.shrub_collection.hide_render = not style.shrub_visibility
    parts.shrub_collection.hide_viewport = not style.shrub_visibility
    parts.flower_collection.hide_render = not style.flower_visibility
    parts.flower_collection.hide_viewport = not style.flower_visibility
    spring_blossoms = season_name == "spring"
    parts.blossom_collection.hide_render = not spring_blossoms
    parts.blossom_collection.hide_viewport = not spring_blossoms
    parts.snow_collection.hide_render = not style.snow_visibility
    parts.snow_collection.hide_viewport = not style.snow_visibility

    parts.world_background.inputs["Strength"].default_value = style.world_strength
    parts.sun.data.energy = style.sun_energy
    parts.sun.data.angle = style.sun_angle
    parts.sun.data.color = style.sun_color
    set_emission_strength(parts.window_glow, style.window_strength)
    scene.view_settings.exposure = style.exposure

    print(f"Season applied: {season_name}")


def render_season(parts: SceneParts, season_name: str):
    apply_season(parts, season_name)
    PUBLIC_OUTPUT.mkdir(parents=True, exist_ok=True)
    output = PUBLIC_OUTPUT / f"{season_name}.png"
    bpy.context.scene.render.filepath = str(output)
    bpy.ops.render.render(write_still=True)
    print(f"Rendered {season_name}: {output}")


def main():
    print("=" * 76)
    print("HECATE946 PROFESSIONAL HOUSE EXTERIOR")
    print(f"Blender: {bpy.app.version_string}")
    print(f"Quality: {QUALITY}")
    print("=" * 76)

    parts = build_scene()

    apply_season(parts, DEFAULT_SEASON)
    BLEND_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_OUTPUT))
    print(f"Saved editable scene: {BLEND_OUTPUT}")

    if AUTO_RENDER:
        for season_name in RENDER_SEASONS:
            render_season(parts, season_name)

        apply_season(parts, DEFAULT_SEASON)
        bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_OUTPUT))

    print("=" * 76)
    print("EXTERIOR COMPLETE")
    print("=" * 76)


if __name__ == "__main__":
    main()
