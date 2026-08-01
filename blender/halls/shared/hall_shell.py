"""
Shared Neoclassical Hall Shell Generator for Blender 4.x
========================================================

This script builds the canonical shared architectural shell used by both the
museum and ballroom. The website mirrors this shell for the ballroom while
loading each hall's unique objects from a separate GLB.

The recovered large-floor version includes:

- a 28 m × 20 m room with the original 6.4 m ceiling height
- small, flush 0.36 m diagonal black-and-white checkerboard tiles
- ivory plaster walls and plain white recessed ceiling
- flat black dado / base trim
- layered cornices and wall panel moldings
- fluted pilasters with simplified classical capitals
- three equidistant frame-and-cartouche groups across each uninterrupted wall
- a centered arched niche with equidistant side groups on the right short wall
- plaster cartouches and garland-like relief details
- invisible soft lighting (no visible ceiling fixtures)
- centered equirectangular 360° preview camera

The reference is a single perspective image, so the unseen sides are inferred
and designed to remain stylistically consistent rather than being a literal
survey reconstruction.

Recommended use:
1. Open Blender.
2. Go to the Scripting workspace.
3. Open this .py file in the Text Editor.
4. Press Run Script.
5. Inspect the generated scene.
6. Press F12 or choose Render > Render Image.

By default, the generated deliverables are written directly to:
    ~/Desktop/projects/hecate946.com/blender/halls/shared/hall-shell.glb
    ~/Desktop/projects/hecate946.com/blender/halls/shared/hall-shell.png

The destination directory is created automatically if it does not exist.
This source file is intended to be saved as:
    ~/Desktop/projects/hecate946.com/blender/halls/shared/hall_shell.py

For a quick test, change RENDER_RESOLUTION from (4096, 2048) to (2048, 1024)
and CYCLES_SAMPLES from 160 to 32.
"""

from __future__ import annotations

import importlib
import importlib.util
import math
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Sequence

import bpy
from mathutils import Vector


SCRIPT_VERSION = "shared-hall-flat-materials-equidistant-v3-2026-07-30"
HALL_BUILDER_VERSION = "2026-07-31-v2-shared-blend-assets"


# -----------------------------------------------------------------------------
# USER SETTINGS
# -----------------------------------------------------------------------------

ROOM_WIDTH = 28.0       # doubled X dimension for a larger, more distant room
ROOM_DEPTH = 20.0       # doubled Y dimension for a larger, more distant room
ROOM_HEIGHT = 6.40      # retain the original ceiling height and proportions
WALL_THICKNESS = 0.24

CAMERA_HEIGHT = 1.68
RENDER_RESOLUTION = (4096, 2048)  # 2:1 equirectangular panorama
CYCLES_SAMPLES = 160

# All generated files are written here. Path.home() expands ``~`` safely.
OUTPUT_DIRECTORY = (
    Path.home()
    / "Desktop"
    / "projects"
    / "hecate946.com"
    / "blender"
    / "halls"
    / "shared"
)

PYTHON_OUTPUT_PATH = OUTPUT_DIRECTORY / "hall_shell.py"
GLB_OUTPUT_PATH = OUTPUT_DIRECTORY / "hall-shell.glb"
PNG_OUTPUT_PATH = OUTPUT_DIRECTORY / "hall-shell.png"
BLEND_OUTPUT_PATH = OUTPUT_DIRECTORY / "hall-shell.blend"

# The GLB is exported every time the script successfully builds the scene.
AUTO_EXPORT_GLB = True
AUTO_RENDER = False
AUTO_SAVE_BLEND = False

# When True, uses Cycles. When False, uses Eevee Next for faster previews.
USE_CYCLES = True

# Smaller checker tiles. Pitch equals size, so adjacent tiles meet exactly.
FLOOR_TILE_PITCH = 0.36
FLOOR_TILE_SIZE = 0.36
FLOOR_TILE_THICKNESS = 0.035
FLOOR_ROTATION_DEGREES = 45.0


# -----------------------------------------------------------------------------
# DATA CONTAINERS
# -----------------------------------------------------------------------------

@dataclass(frozen=True)
class MaterialSet:
    plaster: bpy.types.Material
    plaster_detail: bpy.types.Material
    plaster_shadow: bpy.types.Material
    black_stone: bpy.types.Material
    white_stone: bpy.types.Material
    grout: bpy.types.Material
    doorway_dark: bpy.types.Material


@dataclass(frozen=True)
class HallDefinition:
    slug: str
    title: str
    mirror_shell_x: bool


@dataclass(frozen=True)
class RenderSettings:
    width: int
    height: int
    samples: int
    use_gpu: bool
    auto_render: bool


@dataclass
class HallObjectContext:
    definition: HallDefinition
    output_directory: Path
    scene: bpy.types.Scene
    objects_collection: bpy.types.Collection
    objects_root: bpy.types.Object
    assets_root: Path
    add_box: Callable
    material: Callable
    linear_hex: Callable
    import_glb: Callable
    asset_path: Callable
    place_asset: Callable


# -----------------------------------------------------------------------------
# OUTPUT HELPERS
# -----------------------------------------------------------------------------


def ensure_output_directory() -> Path:
    """Create and return the requested project output directory."""
    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)
    return OUTPUT_DIRECTORY


def _filter_supported_operator_kwargs(operator, kwargs: dict) -> dict:
    """
    Keep this script tolerant of small glTF exporter option changes between
    Blender 4.x releases by passing only properties exposed by the operator.
    """
    try:
        supported = {
            prop.identifier
            for prop in operator.get_rna_type().properties
            if prop.identifier != "rna_type"
        }
        return {key: value for key, value in kwargs.items() if key in supported}
    except Exception:
        return kwargs


def export_glb() -> Path:
    """Export the shared architectural shell as one binary glTF file."""
    ensure_output_directory()

    options = {
        "filepath": str(GLB_OUTPUT_PATH),
        "export_format": "GLB",
        "use_selection": False,
        "export_apply": True,
        "export_cameras": False,
        "export_lights": True,
        "export_materials": "EXPORT",
        "export_yup": True,
        "export_extras": True,
    }
    options = _filter_supported_operator_kwargs(bpy.ops.export_scene.gltf, options)

    result = bpy.ops.export_scene.gltf(**options)
    if "FINISHED" not in result:
        raise RuntimeError(f"GLB export did not finish successfully: {result}")

    print(f"Shared hall shell GLB exported to: {GLB_OUTPUT_PATH}")
    return GLB_OUTPUT_PATH


# -----------------------------------------------------------------------------
# GENERAL HELPERS
# -----------------------------------------------------------------------------


def clear_scene() -> None:
    """Delete the current scene contents."""
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")

    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)

    # Remove now-unused datablocks so rerunning the script stays clean.
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


def get_or_create_collection(name: str) -> bpy.types.Collection:
    collection = bpy.data.collections.get(name)
    if collection is None:
        collection = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(collection)
    return collection


def move_to_collection(obj: bpy.types.Object, collection: bpy.types.Collection) -> None:
    for current in list(obj.users_collection):
        current.objects.unlink(obj)
    collection.objects.link(obj)


def set_node_input(node: bpy.types.Node, names: Sequence[str], value) -> None:
    """Set a node input while tolerating small Blender-version name changes."""
    for name in names:
        socket = node.inputs.get(name)
        if socket is not None:
            socket.default_value = value
            return


def add_bevel_modifier(
    obj: bpy.types.Object,
    width: float,
    segments: int = 3,
    angle_limit: float = math.radians(30.0),
) -> None:
    if width <= 0.0:
        return
    modifier = obj.modifiers.new(name="Soft architectural bevel", type="BEVEL")
    modifier.width = width
    modifier.segments = segments
    modifier.limit_method = "ANGLE"
    modifier.angle_limit = angle_limit


def create_box(
    name: str,
    dimensions: Sequence[float],
    location: Sequence[float],
    material: bpy.types.Material | None,
    collection: bpy.types.Collection,
    bevel: float = 0.0,
    rotation: Sequence[float] = (0.0, 0.0, 0.0),
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cube_add(location=location, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    if material is not None:
        obj.data.materials.append(material)
    if bevel > 0.0:
        add_bevel_modifier(obj, bevel)

    move_to_collection(obj, collection)
    return obj


def create_uv_sphere(
    name: str,
    location: Sequence[float],
    scale: Sequence[float],
    material: bpy.types.Material,
    collection: bpy.types.Collection,
    rotation: Sequence[float] = (0.0, 0.0, 0.0),
    segments: int = 32,
    rings: int = 16,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=segments,
        ring_count=rings,
        location=location,
        rotation=rotation,
    )
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(material)
    bpy.ops.object.shade_smooth()
    move_to_collection(obj, collection)
    return obj


def create_cylinder(
    name: str,
    radius: float,
    depth: float,
    location: Sequence[float],
    material: bpy.types.Material,
    collection: bpy.types.Collection,
    vertices: int = 64,
    bevel: float = 0.0,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=vertices,
        radius=radius,
        depth=depth,
        location=location,
    )
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(material)
    if bevel:
        add_bevel_modifier(obj, bevel, segments=3)
    bpy.ops.object.shade_smooth()
    move_to_collection(obj, collection)
    return obj


def create_curve_object(
    name: str,
    points: Iterable[Vector],
    bevel_depth: float,
    material: bpy.types.Material,
    collection: bpy.types.Collection,
    cyclic: bool = False,
    bevel_resolution: int = 4,
) -> bpy.types.Object:
    curve_data = bpy.data.curves.new(name=f"{name}_Curve", type="CURVE")
    curve_data.dimensions = "3D"
    curve_data.resolution_u = 2
    curve_data.bevel_depth = bevel_depth
    curve_data.bevel_resolution = bevel_resolution
    curve_data.resolution_u = 2
    curve_data.materials.append(material)

    point_list = list(points)
    spline = curve_data.splines.new(type="POLY")
    spline.points.add(len(point_list) - 1)
    for index, point in enumerate(point_list):
        spline.points[index].co = (point.x, point.y, point.z, 1.0)
    spline.use_cyclic_u = cyclic

    obj = bpy.data.objects.new(name, curve_data)
    collection.objects.link(obj)
    return obj


def point_camera_at(camera: bpy.types.Object, target: Sequence[float]) -> None:
    direction = Vector(target) - camera.location
    camera.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


# -----------------------------------------------------------------------------
# MATERIALS
# -----------------------------------------------------------------------------


def create_plaster_material(
    name: str,
    base_color: tuple[float, float, float, float],
    roughness: float,
    bump_strength: float,
) -> bpy.types.Material:
    material = bpy.data.materials.new(name=name)
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()

    output = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    noise = nodes.new("ShaderNodeTexNoise")
    bump = nodes.new("ShaderNodeBump")
    texcoord = nodes.new("ShaderNodeTexCoord")

    output.location = (550, 0)
    bsdf.location = (280, 0)
    bump.location = (50, -120)
    noise.location = (-190, -120)
    texcoord.location = (-420, -120)

    set_node_input(bsdf, ["Base Color"], base_color)
    set_node_input(bsdf, ["Roughness"], roughness)
    set_node_input(bsdf, ["Specular IOR Level", "Specular"], 0.28)

    set_node_input(noise, ["Scale"], 4.5)
    set_node_input(noise, ["Detail"], 4.0)
    set_node_input(noise, ["Roughness"], 0.70)

    set_node_input(bump, ["Strength"], bump_strength)
    set_node_input(bump, ["Distance"], 0.065)

    links.new(texcoord.outputs["Generated"], noise.inputs["Vector"])
    links.new(noise.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])

    material.diffuse_color = base_color
    return material


def create_simple_material(
    name: str,
    base_color: tuple[float, float, float, float],
    roughness: float,
) -> bpy.types.Material:
    material = bpy.data.materials.new(name=name)
    material.use_nodes = True
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        set_node_input(bsdf, ["Base Color"], base_color)
        set_node_input(bsdf, ["Roughness"], roughness)
        set_node_input(bsdf, ["Specular IOR Level", "Specular"], 0.30)
    material.diffuse_color = base_color
    return material


def create_materials() -> MaterialSet:
    plaster = create_plaster_material(
        "Ivory Plaster",
        (0.82, 0.79, 0.74, 1.0),
        roughness=0.76,
        bump_strength=0.055,
    )
    plaster_detail = create_plaster_material(
        "Raised Plaster Detail",
        (0.90, 0.88, 0.84, 1.0),
        roughness=0.69,
        bump_strength=0.035,
    )
    plaster_shadow = create_plaster_material(
        "Recessed Plaster",
        (0.69, 0.67, 0.64, 1.0),
        roughness=0.82,
        bump_strength=0.040,
    )
    # Flat polished stone colors: no procedural texture, mapping, veins, or bump.
    black_stone = create_simple_material(
        "Flat Polished Black Stone",
        (0.012, 0.014, 0.018, 1.0),
        roughness=0.18,
    )
    white_stone = create_simple_material(
        "Flat Polished Ivory Stone",
        (0.80, 0.81, 0.79, 1.0),
        roughness=0.18,
    )
    grout = create_simple_material(
        "Dark Grout",
        (0.035, 0.038, 0.040, 1.0),
        roughness=0.48,
    )
    doorway_dark = create_simple_material(
        "Doorway Shadow",
        (0.018, 0.020, 0.024, 1.0),
        roughness=0.42,
    )
    return MaterialSet(
        plaster=plaster,
        plaster_detail=plaster_detail,
        plaster_shadow=plaster_shadow,
        black_stone=black_stone,
        white_stone=white_stone,
        grout=grout,
        doorway_dark=doorway_dark,
    )


# -----------------------------------------------------------------------------
# WALL COORDINATE HELPERS
# -----------------------------------------------------------------------------


WALLS = ("FRONT", "BACK", "LEFT", "RIGHT")


def wall_length(wall: str) -> float:
    return ROOM_WIDTH if wall in {"FRONT", "BACK"} else ROOM_DEPTH


def wall_inward_normal(wall: str) -> Vector:
    return {
        "FRONT": Vector((0.0, -1.0, 0.0)),
        "BACK": Vector((0.0, 1.0, 0.0)),
        "LEFT": Vector((1.0, 0.0, 0.0)),
        "RIGHT": Vector((-1.0, 0.0, 0.0)),
    }[wall]


def wall_local_to_world(wall: str, u: float, z: float, depth: float = 0.0) -> Vector:
    """
    Convert local wall coordinates to world coordinates.

    u: distance along the wall from its center
    z: world height
    depth: positive distance extending into the room from the wall surface
    """
    if wall == "FRONT":
        surface = Vector((u, ROOM_DEPTH / 2.0 - WALL_THICKNESS / 2.0, z))
    elif wall == "BACK":
        surface = Vector((u, -ROOM_DEPTH / 2.0 + WALL_THICKNESS / 2.0, z))
    elif wall == "LEFT":
        surface = Vector((-ROOM_WIDTH / 2.0 + WALL_THICKNESS / 2.0, u, z))
    elif wall == "RIGHT":
        surface = Vector((ROOM_WIDTH / 2.0 - WALL_THICKNESS / 2.0, u, z))
    else:
        raise ValueError(f"Unknown wall: {wall}")

    return surface + wall_inward_normal(wall) * depth


def add_wall_box(
    name: str,
    wall: str,
    center_u: float,
    center_z: float,
    width_u: float,
    height_z: float,
    depth: float,
    material: bpy.types.Material,
    collection: bpy.types.Collection,
    offset: float = 0.0,
    bevel: float = 0.0,
) -> bpy.types.Object:
    center = wall_local_to_world(wall, center_u, center_z, offset + depth / 2.0)
    if wall in {"FRONT", "BACK"}:
        dimensions = (width_u, depth, height_z)
    else:
        dimensions = (depth, width_u, height_z)
    return create_box(name, dimensions, center, material, collection, bevel=bevel)


def add_wall_ellipsoid(
    name: str,
    wall: str,
    center_u: float,
    center_z: float,
    width_u: float,
    height_z: float,
    depth: float,
    material: bpy.types.Material,
    collection: bpy.types.Collection,
    angle_in_plane: float = 0.0,
    offset: float = 0.0,
) -> bpy.types.Object:
    center = wall_local_to_world(wall, center_u, center_z, offset + depth / 2.0)

    if wall in {"FRONT", "BACK"}:
        scale = (width_u / 2.0, depth / 2.0, height_z / 2.0)
        rotation = (0.0, angle_in_plane, 0.0)
    else:
        scale = (depth / 2.0, width_u / 2.0, height_z / 2.0)
        rotation = (angle_in_plane, 0.0, 0.0)

    return create_uv_sphere(
        name,
        center,
        scale,
        material,
        collection,
        rotation=rotation,
        segments=24,
        rings=12,
    )


def add_wall_prism(
    name: str,
    wall: str,
    coordinates_u_z: Sequence[tuple[float, float]],
    depth: float,
    offset: float,
    material: bpy.types.Material,
    collection: bpy.types.Collection,
) -> bpy.types.Object:
    """Create a shallow polygonal relief or dark opening on a wall."""
    count = len(coordinates_u_z)
    vertices: list[tuple[float, float, float]] = []

    for d in (offset, offset + depth):
        for u, z in coordinates_u_z:
            point = wall_local_to_world(wall, u, z, d)
            vertices.append(tuple(point))

    faces: list[tuple[int, ...]] = []
    faces.append(tuple(reversed(range(count))))
    faces.append(tuple(range(count, count * 2)))
    for index in range(count):
        next_index = (index + 1) % count
        faces.append((index, next_index, count + next_index, count + index))

    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    mesh.materials.append(material)

    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    add_bevel_modifier(obj, 0.018, segments=2)
    return obj


# -----------------------------------------------------------------------------
# FLOOR
# -----------------------------------------------------------------------------


def add_floor_tile_geometry(
    vertices: list[tuple[float, float, float]],
    faces: list[tuple[int, ...]],
    material_indices: list[int],
    center_x: float,
    center_y: float,
    size: float,
    z_top: float,
    rotation_radians: float,
    material_index: int,
) -> None:
    """Add one perfectly flat tile top with no beveled or recessed edges."""
    half = size / 2.0
    local_corners = [
        (-half, -half),
        (half, -half),
        (half, half),
        (-half, half),
    ]
    cosine = math.cos(rotation_radians)
    sine = math.sin(rotation_radians)

    base_index = len(vertices)
    for x_local, y_local in local_corners:
        x_rotated = x_local * cosine - y_local * sine
        y_rotated = x_local * sine + y_local * cosine
        vertices.append((center_x + x_rotated, center_y + y_rotated, z_top))

    faces.append((base_index, base_index + 1, base_index + 2, base_index + 3))
    material_indices.append(material_index)


def build_checkerboard_floor(
    materials: MaterialSet,
    architecture_collection: bpy.types.Collection,
    floor_collection: bpy.types.Collection,
) -> None:
    # Dark under-slab appears as grout between the individual checkerboard tiles.
    create_box(
        "Floor grout slab",
        (ROOM_WIDTH - 0.08, ROOM_DEPTH - 0.08, 0.08),
        (0.0, 0.0, -0.04),
        materials.grout,
        floor_collection,
        bevel=0.01,
    )

    vertices: list[tuple[float, float, float]] = []
    faces: list[tuple[int, ...]] = []
    material_indices: list[int] = []

    angle = math.radians(FLOOR_ROTATION_DEGREES)
    cosine = math.cos(angle)
    sine = math.sin(angle)
    maximum_span = math.sqrt(ROOM_WIDTH ** 2 + ROOM_DEPTH ** 2)
    count = int(math.ceil(maximum_span / FLOOR_TILE_PITCH)) + 3

    for i in range(-count, count + 1):
        for j in range(-count, count + 1):
            grid_x = i * FLOOR_TILE_PITCH
            grid_y = j * FLOOR_TILE_PITCH
            center_x = grid_x * cosine - grid_y * sine
            center_y = grid_x * sine + grid_y * cosine

            if abs(center_x) > ROOM_WIDTH / 2.0 + FLOOR_TILE_SIZE:
                continue
            if abs(center_y) > ROOM_DEPTH / 2.0 + FLOOR_TILE_SIZE:
                continue

            add_floor_tile_geometry(
                vertices,
                faces,
                material_indices,
                center_x,
                center_y,
                FLOOR_TILE_SIZE,
                FLOOR_TILE_THICKNESS,
                angle,
                (i + j) & 1,
            )

    mesh = bpy.data.meshes.new("Checkerboard Floor Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    mesh.materials.append(materials.white_stone)
    mesh.materials.append(materials.black_stone)

    for polygon, material_index in zip(mesh.polygons, material_indices):
        polygon.material_index = material_index

    floor = bpy.data.objects.new("Flat checkerboard floor tiles", mesh)
    floor_collection.objects.link(floor)
    # Deliberately no bevel: neighboring tiles meet flush with no grooves.

    # A thin stone threshold / perimeter band hides uncut diagonal tile edges.
    perimeter_height = 0.045
    perimeter_width = 0.16
    z = FLOOR_TILE_THICKNESS / 2.0
    create_box(
        "Floor perimeter north",
        (ROOM_WIDTH, perimeter_width, perimeter_height),
        (0.0, ROOM_DEPTH / 2.0 - perimeter_width / 2.0, z),
        materials.black_stone,
        floor_collection,
        bevel=0.008,
    )
    create_box(
        "Floor perimeter south",
        (ROOM_WIDTH, perimeter_width, perimeter_height),
        (0.0, -ROOM_DEPTH / 2.0 + perimeter_width / 2.0, z),
        materials.black_stone,
        floor_collection,
        bevel=0.008,
    )
    create_box(
        "Floor perimeter west",
        (perimeter_width, ROOM_DEPTH - 2.0 * perimeter_width, perimeter_height),
        (-ROOM_WIDTH / 2.0 + perimeter_width / 2.0, 0.0, z),
        materials.black_stone,
        floor_collection,
        bevel=0.008,
    )
    create_box(
        "Floor perimeter east",
        (perimeter_width, ROOM_DEPTH - 2.0 * perimeter_width, perimeter_height),
        (ROOM_WIDTH / 2.0 - perimeter_width / 2.0, 0.0, z),
        materials.black_stone,
        floor_collection,
        bevel=0.008,
    )


# -----------------------------------------------------------------------------
# WALLS, BASEBOARDS, PANELS, PILASTERS
# -----------------------------------------------------------------------------


def build_shell(materials: MaterialSet, architecture: bpy.types.Collection) -> None:
    # Structural walls.
    create_box(
        "Front structural wall",
        (ROOM_WIDTH + WALL_THICKNESS * 2.0, WALL_THICKNESS, ROOM_HEIGHT),
        (0.0, ROOM_DEPTH / 2.0, ROOM_HEIGHT / 2.0),
        materials.plaster,
        architecture,
    )
    create_box(
        "Back structural wall",
        (ROOM_WIDTH + WALL_THICKNESS * 2.0, WALL_THICKNESS, ROOM_HEIGHT),
        (0.0, -ROOM_DEPTH / 2.0, ROOM_HEIGHT / 2.0),
        materials.plaster,
        architecture,
    )
    create_box(
        "Left structural wall",
        (WALL_THICKNESS, ROOM_DEPTH, ROOM_HEIGHT),
        (-ROOM_WIDTH / 2.0, 0.0, ROOM_HEIGHT / 2.0),
        materials.plaster,
        architecture,
    )
    create_box(
        "Right structural wall",
        (WALL_THICKNESS, ROOM_DEPTH, ROOM_HEIGHT),
        (ROOM_WIDTH / 2.0, 0.0, ROOM_HEIGHT / 2.0),
        materials.plaster,
        architecture,
    )

    # Plain ceiling slab.
    create_box(
        "Plain white ceiling",
        (ROOM_WIDTH + 0.5, ROOM_DEPTH + 0.5, 0.24),
        (0.0, 0.0, ROOM_HEIGHT + 0.12),
        materials.plaster_detail,
        architecture,
    )


def add_baseboard_system(
    wall: str,
    materials: MaterialSet,
    architecture: bpy.types.Collection,
    decoration: bpy.types.Collection,
) -> None:
    length = wall_length(wall)

    add_wall_box(
        f"{wall} flat black dado",
        wall,
        0.0,
        0.46,
        length - 0.04,
        0.79,
        0.090,
        materials.black_stone,
        architecture,
        offset=0.005,
        bevel=0.012,
    )
    add_wall_box(
        f"{wall} lower black plinth",
        wall,
        0.0,
        0.12,
        length - 0.01,
        0.18,
        0.125,
        materials.black_stone,
        architecture,
        bevel=0.012,
    )
    add_wall_box(
        f"{wall} dado top cap",
        wall,
        0.0,
        0.90,
        length,
        0.105,
        0.135,
        materials.plaster_detail,
        decoration,
        bevel=0.018,
    )

    # Pale inlay rails over the dark dado band.
    add_wall_box(
        f"{wall} dado upper inlay",
        wall,
        0.0,
        0.68,
        length - 0.22,
        0.034,
        0.105,
        materials.plaster_detail,
        decoration,
    )
    add_wall_box(
        f"{wall} dado lower inlay",
        wall,
        0.0,
        0.27,
        length - 0.22,
        0.034,
        0.105,
        materials.plaster_detail,
        decoration,
    )

    target_panel_width = 1.65 if length > 11.0 else 1.45
    divisions = max(4, int(length / target_panel_width))
    spacing = (length - 0.55) / divisions
    for index in range(divisions + 1):
        u = -length / 2.0 + 0.275 + index * spacing
        add_wall_box(
            f"{wall} dado divider {index:02d}",
            wall,
            u,
            0.475,
            0.032,
            0.395,
            0.108,
            materials.plaster_detail,
            decoration,
        )


def add_panel_frame(
    wall: str,
    center_u: float,
    center_z: float,
    width: float,
    height: float,
    materials: MaterialSet,
    decoration: bpy.types.Collection,
    double_frame: bool = True,
) -> None:
    # Slightly darker inner panel gives subtle depth without booleans.
    add_wall_box(
        f"{wall} recessed panel backing",
        wall,
        center_u,
        center_z,
        width - 0.12,
        height - 0.12,
        0.020,
        materials.plaster_shadow,
        decoration,
        offset=0.004,
        bevel=0.008,
    )

    def frame(frame_width: float, frame_height: float, rail: float, depth: float, suffix: str) -> None:
        add_wall_box(
            f"{wall} panel {suffix} top",
            wall,
            center_u,
            center_z + frame_height / 2.0,
            frame_width + rail,
            rail,
            depth,
            materials.plaster_detail,
            decoration,
            bevel=rail * 0.10,
        )
        add_wall_box(
            f"{wall} panel {suffix} bottom",
            wall,
            center_u,
            center_z - frame_height / 2.0,
            frame_width + rail,
            rail,
            depth,
            materials.plaster_detail,
            decoration,
            bevel=rail * 0.10,
        )
        add_wall_box(
            f"{wall} panel {suffix} left",
            wall,
            center_u - frame_width / 2.0,
            center_z,
            rail,
            frame_height,
            depth,
            materials.plaster_detail,
            decoration,
            bevel=rail * 0.10,
        )
        add_wall_box(
            f"{wall} panel {suffix} right",
            wall,
            center_u + frame_width / 2.0,
            center_z,
            rail,
            frame_height,
            depth,
            materials.plaster_detail,
            decoration,
            bevel=rail * 0.10,
        )

    frame(width, height, 0.060, 0.072, "outer")
    if double_frame and width > 1.0 and height > 1.2:
        frame(width - 0.16, height - 0.16, 0.027, 0.082, "inner")


def add_pilaster(
    wall: str,
    center_u: float,
    materials: MaterialSet,
    architecture: bpy.types.Collection,
    decoration: bpy.types.Collection,
    z_bottom: float = 0.92,
    z_top: float = 4.53,
    width: float = 0.48,
) -> None:
    # Base blocks.
    add_wall_box(
        f"{wall} pilaster base lower",
        wall,
        center_u,
        z_bottom + 0.16,
        width * 1.22,
        0.32,
        0.18,
        materials.plaster_detail,
        architecture,
        bevel=0.014,
    )
    add_wall_box(
        f"{wall} pilaster base upper",
        wall,
        center_u,
        z_bottom + 0.39,
        width * 1.06,
        0.15,
        0.15,
        materials.plaster_detail,
        architecture,
        bevel=0.012,
    )

    shaft_bottom = z_bottom + 0.47
    shaft_top = z_top - 0.52
    shaft_height = shaft_top - shaft_bottom
    shaft_center = (shaft_bottom + shaft_top) / 2.0

    add_wall_box(
        f"{wall} pilaster shaft",
        wall,
        center_u,
        shaft_center,
        width * 0.72,
        shaft_height,
        0.122,
        materials.plaster_detail,
        architecture,
        bevel=0.014,
    )

    # Raised reeds approximate the reference's fluting.
    flute_count = 5
    usable_width = width * 0.54
    for index in range(flute_count):
        if flute_count == 1:
            u = center_u
        else:
            u = center_u - usable_width / 2.0 + index * usable_width / (flute_count - 1)
        add_wall_box(
            f"{wall} pilaster flute {index}",
            wall,
            u,
            shaft_center,
            0.026,
            shaft_height - 0.14,
            0.151,
            materials.plaster_shadow,
            decoration,
            bevel=0.006,
        )

    # Simplified Ionic/Corinthian capital built as layered relief.
    capital_z = z_top - 0.26
    add_wall_box(
        f"{wall} pilaster neck",
        wall,
        center_u,
        capital_z - 0.18,
        width * 0.84,
        0.15,
        0.145,
        materials.plaster_detail,
        decoration,
        bevel=0.010,
    )
    add_wall_box(
        f"{wall} pilaster capital block",
        wall,
        center_u,
        capital_z,
        width * 1.20,
        0.28,
        0.185,
        materials.plaster_detail,
        decoration,
        bevel=0.024,
    )
    add_wall_box(
        f"{wall} pilaster capital top",
        wall,
        center_u,
        capital_z + 0.19,
        width * 1.42,
        0.105,
        0.215,
        materials.plaster_detail,
        decoration,
        bevel=0.012,
    )

    for side in (-1.0, 1.0):
        add_wall_ellipsoid(
            f"{wall} pilaster volute {side:+.0f}",
            wall,
            center_u + side * width * 0.34,
            capital_z + 0.015,
            0.18,
            0.18,
            0.075,
            materials.plaster_shadow,
            decoration,
        )
        add_wall_ellipsoid(
            f"{wall} pilaster leaf {side:+.0f}",
            wall,
            center_u + side * width * 0.19,
            capital_z - 0.07,
            0.11,
            0.22,
            0.06,
            materials.plaster_shadow,
            decoration,
            angle_in_plane=side * math.radians(24.0),
        )


def equidistant_group_centers(wall: str, count: int = 3) -> tuple[float, ...]:
    """Return centers of equal wall-width zones, including equal edge margins."""
    length = wall_length(wall)
    zone_width = length / count
    return tuple(
        -length / 2.0 + zone_width * (index + 0.5)
        for index in range(count)
    )


def add_framed_panel_with_columns(
    wall: str,
    center_u: float,
    materials: MaterialSet,
    architecture: bpy.types.Collection,
    decoration: bpy.types.Collection,
    panel_width: float = 1.55,
    panel_height: float = 2.56,
    panel_center_z: float = 2.72,
    pilaster_offset: float = 1.02,
    pilaster_width: float = 0.38,
) -> None:
    """Add one unchanged-size framed panel with a pilaster on each side."""
    add_panel_frame(
        wall,
        center_u,
        panel_center_z,
        panel_width,
        panel_height,
        materials,
        decoration,
    )
    for side in (-1.0, 1.0):
        add_pilaster(
            wall,
            center_u + side * pilaster_offset,
            materials,
            architecture,
            decoration,
            z_bottom=0.90,
            z_top=4.52,
            width=pilaster_width,
        )


def build_primary_wall_layout(
    wall: str,
    materials: MaterialSet,
    architecture: bpy.types.Collection,
    decoration: bpy.types.Collection,
) -> None:
    """Three equidistant framed groups across each 28 m long wall."""
    centers = equidistant_group_centers(wall)

    # Preserve the exact previous frame sizes: narrow, wide, narrow.
    frame_specs = (
        (1.75, 0.40, 1.46, 0.48),
        (6.55, 0.48, 3.95, 0.92),
        (1.75, 0.40, 1.46, 0.48),
    )
    for center_u, (panel_width, pilaster_width, pilaster_offset, cartouche_scale) in zip(
        centers,
        frame_specs,
    ):
        add_framed_panel_with_columns(
            wall,
            center_u,
            materials,
            architecture,
            decoration,
            panel_width=panel_width,
            panel_height=2.56,
            panel_center_z=2.72,
            pilaster_offset=pilaster_offset,
            pilaster_width=pilaster_width,
        )
        add_cartouche(
            wall,
            center_u=center_u,
            center_z=5.53,
            scale=cartouche_scale,
            materials=materials,
            decoration=decoration,
        )


def build_left_short_wall(
    materials: MaterialSet,
    architecture: bpy.types.Collection,
    decoration: bpy.types.Collection,
) -> None:
    """Three unchanged-size framed groups centered in equal wall-width zones."""
    for center_u in equidistant_group_centers("LEFT"):
        add_framed_panel_with_columns(
            "LEFT",
            center_u,
            materials,
            architecture,
            decoration,
        )
        add_cartouche(
            "LEFT",
            center_u=center_u,
            center_z=5.58,
            scale=0.48,
            materials=materials,
            decoration=decoration,
        )


def build_right_short_wall(
    materials: MaterialSet,
    architecture: bpy.types.Collection,
    decoration: bpy.types.Collection,
) -> None:
    """Use three equal zones: framed group, arched opening, framed group."""
    left_center, center_center, right_center = equidistant_group_centers("RIGHT")

    add_arch_niche(
        "RIGHT",
        center_u=center_center,
        materials=materials,
        architecture=architecture,
        decoration=decoration,
    )

    for center_u in (left_center, right_center):
        add_framed_panel_with_columns(
            "RIGHT",
            center_u,
            materials,
            architecture,
            decoration,
        )

    for center_u in (left_center, center_center, right_center):
        add_cartouche(
            "RIGHT",
            center_u=center_u,
            center_z=5.58,
            scale=0.48,
            materials=materials,
            decoration=decoration,
        )


# -----------------------------------------------------------------------------
# CORNICE, CEILING MOLDINGS, AND RELIEF DETAILS
# -----------------------------------------------------------------------------


def add_cornice_system(
    wall: str,
    materials: MaterialSet,
    architecture: bpy.types.Collection,
    decoration: bpy.types.Collection,
) -> None:
    length = wall_length(wall)
    layers = [
        (4.64, 0.10, 0.10),
        (4.76, 0.065, 0.13),
        (4.87, 0.13, 0.17),
        (5.02, 0.075, 0.20),
        (5.13, 0.11, 0.15),
    ]
    for index, (z, height, depth) in enumerate(layers):
        add_wall_box(
            f"{wall} lower cornice layer {index}",
            wall,
            0.0,
            z,
            length,
            height,
            depth,
            materials.plaster_detail,
            architecture,
            bevel=min(height, depth) * 0.22,
        )

    # Smooth upper cove band: kept plain to match the requested ceiling edit.
    add_wall_box(
        f"{wall} upper cove field",
        wall,
        0.0,
        5.58,
        length,
        0.77,
        0.045,
        materials.plaster,
        architecture,
    )

    top_layers = [
        (6.00, 0.095, 0.12),
        (6.11, 0.070, 0.18),
        (6.20, 0.090, 0.23),
    ]
    for index, (z, height, depth) in enumerate(top_layers):
        add_wall_box(
            f"{wall} upper cornice layer {index}",
            wall,
            0.0,
            z,
            length,
            height,
            depth,
            materials.plaster_detail,
            architecture,
            bevel=min(height, depth) * 0.24,
        )

    # Repeating floral bead / rosette approximation along the lower frieze.
    spacing = 0.72
    count = int((length - 0.8) / spacing)
    for index in range(count + 1):
        u = -length / 2.0 + 0.40 + index * (length - 0.80) / max(count, 1)
        add_wall_ellipsoid(
            f"{wall} frieze bead {index:02d}",
            wall,
            u,
            4.985,
            0.12,
            0.10,
            0.055,
            materials.plaster_shadow,
            decoration,
            angle_in_plane=math.radians(45.0 if index % 2 else -45.0),
            offset=0.18,
        )


def build_ceiling_moldings(
    materials: MaterialSet,
    decoration: bpy.types.Collection,
) -> None:
    # A plain recessed center framed by three clean neoclassical bands.
    z_values = (ROOM_HEIGHT - 0.080, ROOM_HEIGHT - 0.105, ROOM_HEIGHT - 0.130)
    margins = (0.58, 0.78, 0.98)
    widths = (0.115, 0.070, 0.050)

    for layer, (z, margin, width) in enumerate(zip(z_values, margins, widths)):
        inner_w = ROOM_WIDTH - 2.0 * margin
        inner_d = ROOM_DEPTH - 2.0 * margin
        create_box(
            f"Ceiling frame {layer} north",
            (inner_w, width, 0.060),
            (0.0, inner_d / 2.0, z),
            materials.plaster_detail,
            decoration,
            bevel=0.015,
        )
        create_box(
            f"Ceiling frame {layer} south",
            (inner_w, width, 0.060),
            (0.0, -inner_d / 2.0, z),
            materials.plaster_detail,
            decoration,
            bevel=0.015,
        )
        create_box(
            f"Ceiling frame {layer} west",
            (width, inner_d, 0.060),
            (-inner_w / 2.0, 0.0, z),
            materials.plaster_detail,
            decoration,
            bevel=0.015,
        )
        create_box(
            f"Ceiling frame {layer} east",
            (width, inner_d, 0.060),
            (inner_w / 2.0, 0.0, z),
            materials.plaster_detail,
            decoration,
            bevel=0.015,
        )


def add_cartouche(
    wall: str,
    center_u: float,
    center_z: float,
    scale: float,
    materials: MaterialSet,
    decoration: bpy.types.Collection,
) -> None:
    # Shield.
    shield = [
        (center_u - 0.34 * scale, center_z + 0.30 * scale),
        (center_u + 0.34 * scale, center_z + 0.30 * scale),
        (center_u + 0.29 * scale, center_z - 0.03 * scale),
        (center_u, center_z - 0.44 * scale),
        (center_u - 0.29 * scale, center_z - 0.03 * scale),
    ]
    add_wall_prism(
        f"{wall} cartouche shield",
        wall,
        shield,
        depth=0.080,
        offset=0.045,
        material=materials.plaster_detail,
        collection=decoration,
    )

    # Inner shield inset.
    inner = [
        (center_u - 0.22 * scale, center_z + 0.18 * scale),
        (center_u + 0.22 * scale, center_z + 0.18 * scale),
        (center_u + 0.18 * scale, center_z - 0.01 * scale),
        (center_u, center_z - 0.27 * scale),
        (center_u - 0.18 * scale, center_z - 0.01 * scale),
    ]
    add_wall_prism(
        f"{wall} cartouche shield inset",
        wall,
        inner,
        depth=0.045,
        offset=0.130,
        material=materials.plaster_shadow,
        collection=decoration,
    )

    # Garland branches formed from overlapping leaves.
    for side in (-1.0, 1.0):
        leaf_count = 10
        for index in range(leaf_count):
            t = index / max(leaf_count - 1, 1)
            u = center_u + side * (0.38 + 1.28 * t) * scale
            z = center_z - (0.05 + 0.30 * t + 0.08 * math.sin(t * math.pi)) * scale
            angle = side * math.radians(20.0 + 34.0 * t)
            add_wall_ellipsoid(
                f"{wall} cartouche leaf {side:+.0f} {index:02d}",
                wall,
                u,
                z,
                0.23 * scale,
                0.105 * scale,
                0.075,
                materials.plaster_detail,
                decoration,
                angle_in_plane=angle,
                offset=0.08,
            )

        # Ribbon tails.
        ribbon_points = []
        for step in range(18):
            t = step / 17.0
            u = center_u + side * (0.34 + 1.40 * t) * scale
            z = center_z - (0.28 + 0.22 * t + 0.07 * math.sin(t * math.pi * 2.0)) * scale
            ribbon_points.append(wall_local_to_world(wall, u, z, 0.16))
        create_curve_object(
            f"{wall} cartouche ribbon {side:+.0f}",
            ribbon_points,
            bevel_depth=0.026 * scale,
            material=materials.plaster_shadow,
            collection=decoration,
            bevel_resolution=3,
        )

    add_wall_ellipsoid(
        f"{wall} cartouche center bead",
        wall,
        center_u,
        center_z - 0.48 * scale,
        0.20 * scale,
        0.14 * scale,
        0.085,
        materials.plaster_detail,
        decoration,
        offset=0.10,
    )


# -----------------------------------------------------------------------------
# DOORWAY AND ARCHITECTURAL FEATURES
# -----------------------------------------------------------------------------


# The older barley-twist doorway generator was intentionally removed.
# The active shared shell uses the revised aligned short-wall composition below.


def add_arch_niche(
    wall: str,
    center_u: float,
    materials: MaterialSet,
    architecture: bpy.types.Collection,
    decoration: bpy.types.Collection,
) -> None:
    width = 1.85
    radius = width / 2.0
    base_z = 0.12
    spring_z = 2.68

    polygon: list[tuple[float, float]] = [
        (center_u - radius, base_z),
        (center_u - radius, spring_z),
    ]
    arc_steps = 28
    for step in range(arc_steps + 1):
        angle = math.pi - step * math.pi / arc_steps
        polygon.append(
            (
                center_u + radius * math.cos(angle),
                spring_z + radius * math.sin(angle),
            )
        )
    polygon.append((center_u + radius, base_z))

    add_wall_prism(
        f"{wall} arched niche dark field",
        wall,
        polygon,
        depth=0.030,
        offset=0.012,
        material=materials.doorway_dark,
        collection=architecture,
    )

    # Architrave curve follows the opening boundary.
    arch_points: list[Vector] = [
        wall_local_to_world(wall, center_u - radius - 0.09, base_z, 0.10),
        wall_local_to_world(wall, center_u - radius - 0.09, spring_z, 0.10),
    ]
    outer_radius = radius + 0.09
    for step in range(arc_steps + 1):
        angle = math.pi - step * math.pi / arc_steps
        u = center_u + outer_radius * math.cos(angle)
        z = spring_z + outer_radius * math.sin(angle)
        arch_points.append(wall_local_to_world(wall, u, z, 0.10))
    arch_points.append(wall_local_to_world(wall, center_u + radius + 0.09, base_z, 0.10))

    create_curve_object(
        f"{wall} arched niche architrave",
        arch_points,
        bevel_depth=0.085,
        material=materials.plaster_detail,
        collection=decoration,
        bevel_resolution=5,
    )

    # Outer pilaster-like sides.
    for side in (-1.0, 1.0):
        add_pilaster(
            wall,
            center_u + side * 1.30,
            materials,
            architecture,
            decoration,
            z_bottom=0.90,
            z_top=4.52,
            width=0.38,
        )


# -----------------------------------------------------------------------------
# LIGHTING AND CAMERA
# -----------------------------------------------------------------------------


def create_area_light(
    name: str,
    location: Sequence[float],
    target: Sequence[float],
    energy: float,
    size: float,
    collection: bpy.types.Collection,
    color: tuple[float, float, float] = (1.0, 0.93, 0.84),
) -> bpy.types.Object:
    light_data = bpy.data.lights.new(name=f"{name}_Data", type="AREA")
    light_data.energy = energy
    light_data.shape = "DISK"
    light_data.size = size
    light_data.color = color

    obj = bpy.data.objects.new(name, light_data)
    obj.location = location
    collection.objects.link(obj)
    point_camera_at(obj, target)
    return obj


def build_lighting(lighting: bpy.types.Collection) -> None:
    # These are light objects only; no visible fixture geometry is created.
    # Four broad sources give the closed room a natural gallery-like ambient fill.
    positions = [
        (-3.7, -2.4, 5.75),
        (3.7, -2.4, 5.75),
        (-3.7, 2.4, 5.75),
        (3.7, 2.4, 5.75),
    ]
    for index, position in enumerate(positions):
        create_area_light(
            f"Invisible ceiling bounce {index + 1}",
            position,
            (0.0, 0.0, 1.30),
            energy=780.0,
            size=4.0,
            collection=lighting,
            color=(1.0, 0.91, 0.82),
        )

    # Subtle wall-grazing fill keeps the plaster relief readable in panorama.
    create_area_light(
        "Front wall soft fill",
        (0.0, -3.9, 3.4),
        (0.0, 4.4, 3.0),
        energy=420.0,
        size=3.0,
        collection=lighting,
        color=(0.90, 0.94, 1.0),
    )
    create_area_light(
        "Back wall soft fill",
        (0.0, 3.9, 3.4),
        (0.0, -4.4, 3.0),
        energy=420.0,
        size=3.0,
        collection=lighting,
        color=(0.90, 0.94, 1.0),
    )


def configure_equirectangular_projection(camera_data: bpy.types.Camera) -> None:
    """Force a full 360x180 equirectangular projection across Blender versions."""
    configured_paths: list[str] = []

    # Current Blender versions expose the panorama projection directly on Camera.
    if hasattr(camera_data, "panorama_type"):
        try:
            camera_data.panorama_type = "EQUIRECTANGULAR"
            configured_paths.append("Camera.panorama_type")
        except (AttributeError, TypeError, ValueError):
            pass

    # Some Blender/Cycles versions expose the same option through Camera.cycles.
    cycles_settings = getattr(camera_data, "cycles", None)
    if cycles_settings is not None and hasattr(cycles_settings, "panorama_type"):
        try:
            cycles_settings.panorama_type = "EQUIRECTANGULAR"
            configured_paths.append("Camera.cycles.panorama_type")
        except (AttributeError, TypeError, ValueError):
            pass

        for attribute, value in (
            ("latitude_min", -math.pi / 2.0),
            ("latitude_max", math.pi / 2.0),
            ("longitude_min", -math.pi),
            ("longitude_max", math.pi),
        ):
            if hasattr(cycles_settings, attribute):
                setattr(cycles_settings, attribute, value)

    detected_values: list[str] = []
    if hasattr(camera_data, "panorama_type"):
        detected_values.append(str(camera_data.panorama_type))
    if cycles_settings is not None and hasattr(cycles_settings, "panorama_type"):
        detected_values.append(str(cycles_settings.panorama_type))

    if "EQUIRECTANGULAR" not in detected_values:
        raise RuntimeError(
            "The 360 camera did not accept the EQUIRECTANGULAR projection. "
            f"Detected panorama settings: {detected_values or ['unavailable']}"
        )

    print(
        "[Hall] Full 360x180 equirectangular projection confirmed via: "
        + ", ".join(configured_paths)
    )


def verify_equirectangular_render_camera(camera: bpy.types.Object) -> None:
    """Stop before rendering rather than silently producing a circular fisheye."""
    if camera.type != "CAMERA" or camera.data.type != "PANO":
        raise RuntimeError("The active hall render camera is not a panoramic camera.")

    values: list[str] = []
    if hasattr(camera.data, "panorama_type"):
        values.append(str(camera.data.panorama_type))
    cycles_settings = getattr(camera.data, "cycles", None)
    if cycles_settings is not None and hasattr(cycles_settings, "panorama_type"):
        values.append(str(cycles_settings.panorama_type))

    if "EQUIRECTANGULAR" not in values:
        raise RuntimeError(
            "Refusing to render because the camera is not equirectangular. "
            f"Detected panorama settings: {values or ['unavailable']}"
        )


def build_360_camera(cameras: bpy.types.Collection) -> bpy.types.Object:
    camera_data = bpy.data.cameras.new("Camera_360_Data")
    camera_data.type = "PANO"
    camera_data.clip_start = 0.05
    camera_data.clip_end = 100.0
    configure_equirectangular_projection(camera_data)

    camera = bpy.data.objects.new("Camera_360_Centered", camera_data)
    camera.location = (0.0, 0.0, CAMERA_HEIGHT)
    cameras.objects.link(camera)

    # Keep the panorama perfectly level; only its longitude seam changes.
    camera.rotation_euler = (math.pi / 2.0, 0.0, 0.0)
    bpy.context.scene.camera = camera
    return camera


# -----------------------------------------------------------------------------
# SCENE SETTINGS
# -----------------------------------------------------------------------------


def configure_scene(
    settings: RenderSettings | None = None,
    output_path: Path | None = None,
) -> None:
    """Configure Cycles using either builder settings or direct-script globals."""
    ensure_output_directory()
    scene = bpy.context.scene

    width = settings.width if settings is not None else RENDER_RESOLUTION[0]
    height = settings.height if settings is not None else RENDER_RESOLUTION[1]
    samples = settings.samples if settings is not None else CYCLES_SAMPLES
    use_gpu = settings.use_gpu if settings is not None else True
    render_path = Path(output_path) if output_path is not None else PNG_OUTPUT_PATH

    render_path.parent.mkdir(parents=True, exist_ok=True)
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.length_unit = "METERS"
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.image_settings.color_depth = "16"
    scene.render.film_transparent = False
    scene.render.filepath = str(render_path)

    # Cycles only; no alternate render-engine assignments are used.
    scene.render.engine = "CYCLES"
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    scene.cycles.preview_samples = min(48, samples)
    scene.cycles.max_bounces = 9
    scene.cycles.diffuse_bounces = 4
    scene.cycles.glossy_bounces = 5
    scene.cycles.transparent_max_bounces = 4
    if hasattr(scene.cycles, "use_adaptive_sampling"):
        scene.cycles.use_adaptive_sampling = True

    # Prefer GPU when requested and available, but fall back safely to CPU.
    scene.cycles.device = "CPU"
    if use_gpu:
        try:
            prefs = bpy.context.preferences.addons["cycles"].preferences
            prefs.get_devices()
            gpu_types = {"CUDA", "OPTIX", "HIP", "METAL", "ONEAPI"}
            has_gpu = False
            for device in getattr(prefs, "devices", []):
                if getattr(device, "type", None) in gpu_types:
                    device.use = True
                    has_gpu = True
            if has_gpu:
                scene.cycles.device = "GPU"
        except Exception as error:
            print(f"Cycles device setup warning: {error}")
            scene.cycles.device = "CPU"

    # Physically plausible soft contrast.
    try:
        scene.view_settings.look = "AgX - Medium High Contrast"
    except Exception:
        try:
            scene.view_settings.look = "Medium High Contrast"
        except Exception:
            pass

    scene.view_settings.exposure = 0.35

    world = scene.world
    if world is None:
        world = bpy.data.worlds.new("Neoclassical Room World")
        scene.world = world
    world.use_nodes = True
    background = world.node_tree.nodes.get("Background")
    if background:
        background.inputs["Color"].default_value = (0.018, 0.020, 0.024, 1.0)
        background.inputs["Strength"].default_value = 0.16


# -----------------------------------------------------------------------------
# MAIN BUILD
# -----------------------------------------------------------------------------


def build_scene(settings: RenderSettings | None = None) -> None:
    loaded_from = globals().get("__file__", "<Blender Text Editor>")
    print(f"\n[Shared Hall {SCRIPT_VERSION}] Running script: {loaded_from}")
    clear_scene()
    configure_scene(settings=settings)

    architecture = get_or_create_collection("01 Architecture")
    floor = get_or_create_collection("02 Checkerboard Floor")
    decoration = get_or_create_collection("03 Moldings and Relief")
    lighting = get_or_create_collection("04 Invisible Lighting")
    cameras = get_or_create_collection("05 Cameras")

    materials = create_materials()

    build_shell(materials, architecture)
    build_checkerboard_floor(materials, architecture, floor)

    for wall in WALLS:
        add_baseboard_system(wall, materials, architecture, decoration)
        add_cornice_system(wall, materials, architecture, decoration)

    build_primary_wall_layout("FRONT", materials, architecture, decoration)
    build_primary_wall_layout("BACK", materials, architecture, decoration)

    # Short-side custom compositions.
    build_left_short_wall(materials, architecture, decoration)
    build_right_short_wall(materials, architecture, decoration)

    build_ceiling_moldings(materials, decoration)
    build_lighting(lighting)
    build_360_camera(cameras)

    # Keep the viewport organized and place the 3D cursor at the room center.
    bpy.context.scene.cursor.location = (0.0, 0.0, 0.0)

    # Save/export only after the complete scene has been built successfully.
    if AUTO_SAVE_BLEND:
        ensure_output_directory()
        bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_OUTPUT_PATH))
        print(f"Blend file saved to: {BLEND_OUTPUT_PATH}")

    if AUTO_EXPORT_GLB:
        export_glb()

    if AUTO_RENDER:
        ensure_output_directory()
        if bpy.context.scene.camera is None:
            raise RuntimeError("No active camera is assigned for the panorama render.")
        verify_equirectangular_render_camera(bpy.context.scene.camera)
        bpy.context.scene.render.filepath = str(PNG_OUTPUT_PATH)
        bpy.ops.render.render(write_still=True)
        print(f"Panorama rendered to: {PNG_OUTPUT_PATH}")

    print(f"\nShared neoclassical hall shell generated successfully. Version: {SCRIPT_VERSION}")
    print(f"Room dimensions: {ROOM_WIDTH:.2f} m x {ROOM_DEPTH:.2f} m x {ROOM_HEIGHT:.2f} m")
    scene = bpy.context.scene
    print(f"Panorama resolution: {scene.render.resolution_x} x {scene.render.resolution_y}")
    print(f"Python target: {PYTHON_OUTPUT_PATH}")
    print(f"GLB path: {GLB_OUTPUT_PATH}")
    print(f"PNG path: {PNG_OUTPUT_PATH}")
    print("Main camera: Camera_360_Centered")

# -----------------------------------------------------------------------------
# SHARED HALL BUILD WORKFLOW
# -----------------------------------------------------------------------------


def load_live_module(module_name: str, file_path: Path):
    """Force-load a Blender Python module fresh from disk every run."""
    file_path = Path(file_path).expanduser().resolve()
    if not file_path.exists():
        raise FileNotFoundError(f"Blender module does not exist: {file_path}")

    importlib.invalidate_caches()
    sys.modules.pop(module_name, None)

    try:
        pyc_path = Path(importlib.util.cache_from_source(str(file_path)))
        if pyc_path.exists():
            pyc_path.unlink()
    except (NotImplementedError, OSError, ValueError):
        pass

    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load Blender module: {file_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(module_name, None)
        raise

    print(f"Loaded fresh module from: {file_path}")
    return module


def reset_scene_for_hall() -> bpy.types.Scene:
    """Reset all scene objects and generated collections between hall builds."""
    clear_scene()

    for collection in list(bpy.data.collections):
        try:
            bpy.data.collections.remove(collection)
        except RuntimeError:
            pass

    for datablocks in (bpy.data.images, bpy.data.worlds):
        for block in list(datablocks):
            if block.users == 0:
                try:
                    datablocks.remove(block)
                except RuntimeError:
                    pass

    return bpy.context.scene


def linear_hex(value: str):
    """Convert an sRGB hex color to Blender's linear RGBA representation."""
    value = value.lstrip("#")
    rgb = [int(value[index : index + 2], 16) / 255.0 for index in (0, 2, 4)]

    def linear(channel: float) -> float:
        if channel <= 0.04045:
            return channel / 12.92
        return ((channel + 0.055) / 1.055) ** 2.4

    return (*[linear(channel) for channel in rgb], 1.0)


def object_material(
    name,
    color,
    roughness=0.35,
    coat=0.0,
    metallic=0.0,
):
    """Create a simple material for hall-specific objects."""
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    if bsdf is not None:
        set_node_input(bsdf, ["Base Color"], color)
        set_node_input(bsdf, ["Roughness"], roughness)
        set_node_input(bsdf, ["Coat Weight", "Clearcoat"], coat)
        set_node_input(bsdf, ["Metallic"], metallic)
    material.diffuse_color = color
    return material


def add_object_box(
    name,
    center,
    size,
    material,
    collection,
    bevel=0.0,
    parent=None,
):
    """Object-hook box helper with the same argument order as room hooks."""
    obj = create_box(
        name=name,
        dimensions=size,
        location=center,
        material=material,
        collection=collection,
        bevel=bevel,
    )
    if parent is not None:
        obj.parent = parent
    return obj


def import_glb(file_path, collection, parent=None, name_prefix=""):
    """Import a GLB and move all imported objects into one export collection."""
    file_path = Path(file_path).expanduser().resolve()
    if not file_path.exists():
        raise FileNotFoundError(f"Object GLB does not exist: {file_path}")

    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(file_path))
    imported = [obj for obj in bpy.data.objects if obj not in before]
    imported_set = set(imported)

    for obj in imported:
        if name_prefix:
            obj.name = f"{name_prefix}{obj.name}"
        move_to_collection(obj, collection)

    for obj in imported:
        if obj.parent not in imported_set and parent is not None:
            matrix_world = obj.matrix_world.copy()
            obj.parent = parent
            obj.matrix_world = matrix_world

    return imported


def export_collection(
    main_scene: bpy.types.Scene,
    collection: bpy.types.Collection,
    output_file: Path,
) -> None:
    """Export only one collection as a binary glTF file."""
    output_file.parent.mkdir(parents=True, exist_ok=True)

    selected_before = [obj for obj in main_scene.objects if obj.select_get()]
    active_before = bpy.context.view_layer.objects.active

    try:
        bpy.ops.object.select_all(action="DESELECT")
        export_objects = list(collection.all_objects)
        for obj in export_objects:
            obj.hide_set(False)
            obj.hide_render = False
            obj.select_set(True)

        if export_objects:
            bpy.context.view_layer.objects.active = export_objects[0]

        options = {
            "filepath": str(output_file),
            "export_format": "GLB",
            "use_selection": True,
            "export_selected_objects": True,
            "export_lights": True,
            "export_cameras": False,
            "export_apply": True,
            "export_extras": True,
        }
        options = _filter_supported_operator_kwargs(bpy.ops.export_scene.gltf, options)
        result = bpy.ops.export_scene.gltf(**options)
        if "FINISHED" not in result:
            raise RuntimeError(f"Hall object GLB export failed: {result}")
    finally:
        bpy.ops.object.select_all(action="DESELECT")
        for obj in selected_before:
            if obj.name in main_scene.objects:
                obj.select_set(True)
        if active_before is not None and active_before.name in main_scene.objects:
            bpy.context.view_layer.objects.active = active_before


def import_shell_preview(
    scene: bpy.types.Scene,
    shared_glb: Path,
    mirror_x: bool,
) -> bpy.types.Object:
    """Import the canonical shell and mirror only its preview when requested."""
    if not shared_glb.exists():
        raise FileNotFoundError(f"Shared hall shell is missing: {shared_glb}")

    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(shared_glb))
    imported = [obj for obj in bpy.data.objects if obj not in before]
    imported_set = set(imported)

    shell_root = bpy.data.objects.new("Shared_Hall_Shell_Preview", None)
    scene.collection.objects.link(shell_root)

    for obj in imported:
        if obj.parent not in imported_set:
            matrix_world = obj.matrix_world.copy()
            obj.parent = shell_root
            obj.matrix_world = matrix_world

    shell_root.scale.x = -1.0 if mirror_x else 1.0
    shell_root["website_shell_scale_x"] = -1.0 if mirror_x else 1.0
    shell_root["preview_only"] = True
    shell_root["exported_separately"] = True
    bpy.context.view_layer.update()
    return shell_root


def load_unique_module(unique_file: Path):
    if not unique_file.exists():
        return None
    return load_live_module(f"hall_unique_{unique_file.parent.name}", unique_file)


def call_unique_hook(module, context: HallObjectContext) -> None:
    if module is None:
        return
    hook = getattr(module, "add_objects", None)
    if callable(hook):
        hook(context)


def build_shared_shell(settings: RenderSettings, halls_root: Path) -> Path:
    """Build the canonical architecture once for all requested halls."""
    global OUTPUT_DIRECTORY
    global PYTHON_OUTPUT_PATH
    global GLB_OUTPUT_PATH
    global PNG_OUTPUT_PATH
    global BLEND_OUTPUT_PATH
    global AUTO_EXPORT_GLB
    global AUTO_RENDER
    global AUTO_SAVE_BLEND

    shared_root = halls_root / "shared"
    shared_root.mkdir(parents=True, exist_ok=True)

    OUTPUT_DIRECTORY = shared_root
    PYTHON_OUTPUT_PATH = shared_root / "hall_shell.py"
    GLB_OUTPUT_PATH = shared_root / "hall-shell.glb"
    PNG_OUTPUT_PATH = shared_root / "hall-shell.png"
    BLEND_OUTPUT_PATH = shared_root / "hall-shell.blend"
    AUTO_EXPORT_GLB = True
    AUTO_RENDER = False
    AUTO_SAVE_BLEND = True

    shell_settings = RenderSettings(
        width=settings.width,
        height=settings.height,
        samples=settings.samples,
        use_gpu=settings.use_gpu,
        auto_render=False,
    )
    build_scene(settings=shell_settings)

    project_root = halls_root.parent.parent
    public_shell = project_root / "public" / "scenes" / "halls" / "shared" / "shell.glb"
    public_shell.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(GLB_OUTPUT_PATH, public_shell)
    print(f"Published shared hall shell to: {public_shell}")
    return GLB_OUTPUT_PATH


def build_hall_objects(
    definition: HallDefinition,
    settings: RenderSettings,
    halls_root: Path,
    shared_glb: Path,
) -> None:
    """Build one hall's authored objects, preview blend, and optional panorama."""
    output_directory = halls_root / definition.slug
    output_directory.mkdir(parents=True, exist_ok=True)

    objects_file = output_directory / f"{definition.slug}-objects.glb"
    preview_file = output_directory / f"{definition.slug}-objects.blend"
    panorama_file = output_directory / f"{definition.slug}-panorama.png"

    if settings.auto_render and panorama_file.exists():
        panorama_file.unlink()

    scene = reset_scene_for_hall()
    configure_scene(settings=settings, output_path=panorama_file)
    shell_root = import_shell_preview(scene, shared_glb, definition.mirror_shell_x)

    objects_collection = bpy.data.collections.new("HALL_OBJECTS_EXPORT")
    scene.collection.children.link(objects_collection)

    objects_root = bpy.data.objects.new(f"{definition.slug.title()}_Objects_Root", None)
    objects_collection.objects.link(objects_root)
    objects_root["hall_slug"] = definition.slug
    objects_root["shell_mirrored_x"] = definition.mirror_shell_x

    blender_root = halls_root.parent
    project_root = blender_root.parent
    assets_root = blender_root / "assets"
    asset_library = load_live_module(
        "hecate_shared_asset_library_halls",
        blender_root / "shared" / "asset_library.py",
    )

    def asset_path(asset_id, *, file_name=None):
        return asset_library.resolve_asset_path(
            assets_root,
            asset_id,
            file_name=file_name,
        )

    def place_asset(asset_id, *, name=None, extras=None, **placement):
        placed = asset_library.place_asset(
            assets_root=assets_root,
            asset_id=asset_id,
            collection=objects_collection,
            name=name,
            extras=extras,
            **placement,
        )
        matrix_world = placed.root.matrix_world.copy()
        placed.root.parent = objects_root
        placed.root.matrix_world = matrix_world
        return placed

    context = HallObjectContext(
        definition=definition,
        output_directory=output_directory,
        scene=scene,
        objects_collection=objects_collection,
        objects_root=objects_root,
        assets_root=assets_root,
        add_box=add_object_box,
        material=object_material,
        linear_hex=linear_hex,
        import_glb=import_glb,
        asset_path=asset_path,
        place_asset=place_asset,
    )

    unique_module = load_unique_module(output_directory / "unique.py")
    call_unique_hook(unique_module, context)

    shell_root["hall_slug"] = definition.slug
    camera_collection = get_or_create_collection("HALL_PREVIEW_CAMERA")
    camera = build_360_camera(camera_collection)
    scene.camera = camera

    bpy.ops.wm.save_as_mainfile(filepath=str(preview_file))

    if settings.auto_render:
        verify_equirectangular_render_camera(camera)
        bpy.ops.render.render(write_still=True)
        if not panorama_file.exists():
            raise RuntimeError(f"Panorama render did not create {panorama_file}")
        print(f"Panorama rendered to: {panorama_file}")
    else:
        print(f"Skipped panorama render for {definition.slug}.")

    export_collection(scene, objects_collection, objects_file)
    bpy.ops.wm.save_as_mainfile(filepath=str(preview_file))

    public_directory = project_root / "public" / "scenes" / "halls" / definition.slug
    public_directory.mkdir(parents=True, exist_ok=True)
    shutil.copy2(objects_file, public_directory / "objects.glb")
    if settings.auto_render:
        shutil.copy2(panorama_file, public_directory / "panorama.png")

    print(f"Built {definition.title}")
    print(f"  Shared shell: {shared_glb}")
    print(f"  Mirrored X:   {definition.mirror_shell_x}")
    print(f"  Objects GLB:  {objects_file}")
    print(f"  Preview:      {preview_file}")
    print(f"  Panorama:     {panorama_file}")
    print(f"  Website:      {public_directory}")


def build_halls(
    definitions: Sequence[HallDefinition],
    settings: RenderSettings,
    halls_root: Path,
) -> None:
    """Build the shared shell once, then each selected hall from that shell."""
    halls_root = Path(halls_root).expanduser().resolve()
    if not definitions:
        raise ValueError("At least one hall definition is required.")

    print(f"Hall builder version: {HALL_BUILDER_VERSION}")
    print(f"Hall builder source:  {Path(__file__).resolve()}")
    print(f"Shared asset directory: {(halls_root.parent / 'assets').resolve()}")

    shared_glb = build_shared_shell(settings, halls_root)
    for definition in definitions:
        build_hall_objects(definition, settings, halls_root, shared_glb)

    print("All requested hall assets finished.")

if __name__ == "__main__":
    build_scene()