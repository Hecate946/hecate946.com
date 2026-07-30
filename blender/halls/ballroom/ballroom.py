"""
Neoclassical 360° Room Generator for Blender 4.x
=================================================

This script builds a complete, enclosed 360-degree neoclassical gallery room
inspired by the supplied reference image:

- centered, symmetrical room proportions
- polished black-and-white diagonal checkerboard marble floor
- ivory plaster walls and plain white recessed ceiling
- black marble dado / base trim
- layered cornices and wall panel moldings
- fluted pilasters with simplified classical capitals
- a barley-twist column doorway on one side
- a tall arched niche on the opposite side
- plaster cartouches and garland-like relief details
- invisible soft lighting (no visible ceiling fixtures)
- centered equirectangular 360° camera

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
    ~/Desktop/projects/hecate946.com/blender/halls/ballroom/ballroom.glb
    ~/Desktop/projects/hecate946.com/blender/halls/ballroom/ballroom.png

The destination directory is created automatically if it does not exist.
This source file is intended to be saved as:
    ~/Desktop/projects/hecate946.com/blender/halls/ballroom/ballroom.py

For a quick test, change RENDER_RESOLUTION from (4096, 2048) to (2048, 1024)
and CYCLES_SAMPLES from 160 to 32.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

import bpy
from mathutils import Vector


SCRIPT_VERSION = "ballroom-smaller-floor-tiles-v1-2026-07-29"


# -----------------------------------------------------------------------------
# USER SETTINGS
# -----------------------------------------------------------------------------

ROOM_WIDTH = 14.0       # X dimension, meters
ROOM_DEPTH = 10.0       # Y dimension, meters
ROOM_HEIGHT = 6.40      # finished floor to ceiling, meters
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
    / "ballroom"
)

PYTHON_OUTPUT_PATH = OUTPUT_DIRECTORY / "ballroom.py"
GLB_OUTPUT_PATH = OUTPUT_DIRECTORY / "ballroom.glb"
PNG_OUTPUT_PATH = OUTPUT_DIRECTORY / "ballroom.png"
BLEND_OUTPUT_PATH = OUTPUT_DIRECTORY / "ballroom.blend"

# The GLB is exported every time the script successfully builds the scene.
AUTO_EXPORT_GLB = True
AUTO_RENDER = True
AUTO_SAVE_BLEND = False

# When True, uses Cycles. When False, uses Eevee Next for faster previews.
USE_CYCLES = True

# Floor proportions adjusted for smaller tiles with no visible spacing.
FLOOR_TILE_PITCH = 0.50
FLOOR_TILE_SIZE = 0.50
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
    black_marble: bpy.types.Material
    white_marble: bpy.types.Material
    grout: bpy.types.Material
    doorway_dark: bpy.types.Material


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
    """Export the complete generated scene as one binary glTF file."""
    ensure_output_directory()

    options = {
        "filepath": str(GLB_OUTPUT_PATH),
        "export_format": "GLB",
        "use_selection": False,
        "export_apply": True,
        "export_cameras": True,
        "export_lights": True,
        "export_materials": "EXPORT",
        "export_yup": True,
        "export_extras": True,
    }
    options = _filter_supported_operator_kwargs(bpy.ops.export_scene.gltf, options)

    result = bpy.ops.export_scene.gltf(**options)
    if "FINISHED" not in result:
        raise RuntimeError(f"GLB export did not finish successfully: {result}")

    print(f"GLB exported to: {GLB_OUTPUT_PATH}")
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


def create_marble_material(
    name: str,
    base_color: tuple[float, float, float, float],
    vein_color: tuple[float, float, float, float],
    roughness: float,
    scale: float,
    distortion: float,
) -> bpy.types.Material:
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
    noise = nodes.new("ShaderNodeTexNoise")
    mix = nodes.new("ShaderNodeMixRGB")
    ramp = nodes.new("ShaderNodeValToRGB")
    bump = nodes.new("ShaderNodeBump")

    output.location = (800, 40)
    bsdf.location = (560, 40)
    bump.location = (330, -120)
    ramp.location = (310, 90)
    mix.location = (90, 90)
    wave.location = (-160, 140)
    noise.location = (-160, -100)
    mapping.location = (-390, 50)
    texcoord.location = (-620, 50)

    set_node_input(bsdf, ["Roughness"], roughness)
    set_node_input(bsdf, ["Metallic"], 0.0)
    set_node_input(bsdf, ["Specular IOR Level", "Specular"], 0.48)
    set_node_input(bsdf, ["Coat Weight", "Clearcoat"], 0.18)
    set_node_input(bsdf, ["Coat Roughness", "Clearcoat Roughness"], 0.10)

    wave.wave_type = "BANDS"
    wave.bands_direction = "X"
    set_node_input(wave, ["Scale"], scale)
    set_node_input(wave, ["Distortion"], distortion)
    set_node_input(wave, ["Detail"], 5.0)
    set_node_input(wave, ["Detail Scale"], 1.8)

    set_node_input(noise, ["Scale"], scale * 1.7)
    set_node_input(noise, ["Detail"], 7.0)
    set_node_input(noise, ["Roughness"], 0.75)

    mix.blend_type = "MULTIPLY"
    mix.inputs[0].default_value = 0.68

    color_ramp = ramp.color_ramp
    color_ramp.elements.remove(color_ramp.elements[1])
    first = color_ramp.elements[0]
    first.position = 0.30
    first.color = base_color
    middle = color_ramp.elements.new(0.53)
    middle.color = base_color
    vein = color_ramp.elements.new(0.61)
    vein.color = vein_color
    final = color_ramp.elements.new(0.68)
    final.color = base_color

    set_node_input(bump, ["Strength"], 0.10)
    set_node_input(bump, ["Distance"], 0.035)

    links.new(texcoord.outputs["Generated"], mapping.inputs["Vector"])
    links.new(mapping.outputs["Vector"], wave.inputs["Vector"])
    links.new(mapping.outputs["Vector"], noise.inputs["Vector"])
    links.new(wave.outputs["Color"], mix.inputs[1])
    links.new(noise.outputs["Fac"], mix.inputs[2])
    links.new(mix.outputs["Color"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(mix.outputs["Color"], bump.inputs["Height"])
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
        (0.73, 0.71, 0.68, 1.0),
        roughness=0.82,
        bump_strength=0.045,
    )
    black_marble = create_marble_material(
        "Black Marble",
        (0.012, 0.014, 0.018, 1.0),
        (0.24, 0.25, 0.27, 1.0),
        roughness=0.16,
        scale=2.9,
        distortion=7.0,
    )
    white_marble = create_marble_material(
        "White Marble",
        (0.78, 0.79, 0.77, 1.0),
        (0.30, 0.32, 0.34, 1.0),
        roughness=0.15,
        scale=2.4,
        distortion=6.0,
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
        black_marble=black_marble,
        white_marble=white_marble,
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


def add_cube_geometry(
    vertices: list[tuple[float, float, float]],
    faces: list[tuple[int, ...]],
    material_indices: list[int],
    center_x: float,
    center_y: float,
    size: float,
    z_bottom: float,
    z_top: float,
    rotation_radians: float,
    material_index: int,
) -> None:
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
    for z in (z_bottom, z_top):
        for x_local, y_local in local_corners:
            x_rotated = x_local * cosine - y_local * sine
            y_rotated = x_local * sine + y_local * cosine
            vertices.append((center_x + x_rotated, center_y + y_rotated, z))

    cube_faces = [
        (0, 3, 2, 1),
        (4, 5, 6, 7),
        (0, 1, 5, 4),
        (1, 2, 6, 5),
        (2, 3, 7, 6),
        (3, 0, 4, 7),
    ]
    for face in cube_faces:
        faces.append(tuple(base_index + vertex for vertex in face))
        material_indices.append(material_index)


def build_checkerboard_floor(
    materials: MaterialSet,
    architecture_collection: bpy.types.Collection,
    floor_collection: bpy.types.Collection,
) -> None:
    # Dark under-slab appears as grout between the individual marble tiles.
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

            add_cube_geometry(
                vertices,
                faces,
                material_indices,
                center_x,
                center_y,
                FLOOR_TILE_SIZE,
                0.0,
                FLOOR_TILE_THICKNESS,
                angle,
                (i + j) & 1,
            )

    mesh = bpy.data.meshes.new("Checkerboard Marble Floor Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    mesh.materials.append(materials.white_marble)
    mesh.materials.append(materials.black_marble)

    for polygon, material_index in zip(mesh.polygons, material_indices):
        polygon.material_index = material_index

    floor = bpy.data.objects.new("Checkerboard marble tiles", mesh)
    floor_collection.objects.link(floor)
    add_bevel_modifier(floor, 0.006, segments=2)

    # A thin marble threshold / perimeter band hides uncut diagonal tile edges.
    perimeter_height = 0.045
    perimeter_width = 0.16
    z = FLOOR_TILE_THICKNESS / 2.0
    create_box(
        "Floor perimeter north",
        (ROOM_WIDTH, perimeter_width, perimeter_height),
        (0.0, ROOM_DEPTH / 2.0 - perimeter_width / 2.0, z),
        materials.black_marble,
        floor_collection,
        bevel=0.008,
    )
    create_box(
        "Floor perimeter south",
        (ROOM_WIDTH, perimeter_width, perimeter_height),
        (0.0, -ROOM_DEPTH / 2.0 + perimeter_width / 2.0, z),
        materials.black_marble,
        floor_collection,
        bevel=0.008,
    )
    create_box(
        "Floor perimeter west",
        (perimeter_width, ROOM_DEPTH - 2.0 * perimeter_width, perimeter_height),
        (-ROOM_WIDTH / 2.0 + perimeter_width / 2.0, 0.0, z),
        materials.black_marble,
        floor_collection,
        bevel=0.008,
    )
    create_box(
        "Floor perimeter east",
        (perimeter_width, ROOM_DEPTH - 2.0 * perimeter_width, perimeter_height),
        (ROOM_WIDTH / 2.0 - perimeter_width / 2.0, 0.0, z),
        materials.black_marble,
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
        f"{wall} black marble dado",
        wall,
        0.0,
        0.46,
        length - 0.04,
        0.79,
        0.090,
        materials.black_marble,
        architecture,
        offset=0.005,
        bevel=0.012,
    )
    add_wall_box(
        f"{wall} lower marble plinth",
        wall,
        0.0,
        0.12,
        length - 0.01,
        0.18,
        0.125,
        materials.black_marble,
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

    # Pale inlay rails over the dark marble band.
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
        0.014,
        materials.plaster_shadow,
        decoration,
        offset=0.004,
        bevel=0.012,
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
            bevel=rail * 0.18,
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
            bevel=rail * 0.18,
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
            bevel=rail * 0.18,
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
            bevel=rail * 0.18,
        )

    frame(width, height, 0.060, 0.055, "outer")
    if double_frame and width > 1.0 and height > 1.2:
        frame(width - 0.16, height - 0.16, 0.027, 0.063, "inner")


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
        bevel=0.022,
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
        bevel=0.018,
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
        0.115,
        materials.plaster_detail,
        architecture,
        bevel=0.022,
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
            0.139,
            materials.plaster_shadow,
            decoration,
            bevel=0.010,
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
        bevel=0.016,
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
        bevel=0.036,
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
        bevel=0.018,
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


def build_primary_wall_layout(
    wall: str,
    materials: MaterialSet,
    architecture: bpy.types.Collection,
    decoration: bpy.types.Collection,
) -> None:
    # Front/back composition inferred from the reference.
    add_panel_frame(wall, 0.0, 2.72, 6.55, 2.56, materials, decoration)
    add_panel_frame(wall, -5.18, 2.72, 1.75, 2.56, materials, decoration)
    add_panel_frame(wall, 5.18, 2.72, 1.75, 2.56, materials, decoration)

    for u in (-3.95, 3.95):
        add_pilaster(wall, u, materials, architecture, decoration)

    # Near-corner narrow pilasters make the panoramic corners feel complete.
    for u in (-6.35, 6.35):
        add_pilaster(
            wall,
            u,
            materials,
            architecture,
            decoration,
            width=0.40,
        )


def build_secondary_wall_layout(
    wall: str,
    materials: MaterialSet,
    architecture: bpy.types.Collection,
    decoration: bpy.types.Collection,
    reserve_center: bool = False,
) -> None:
    # Side walls are inferred from the same proportional language.
    if reserve_center:
        add_panel_frame(wall, -3.15, 2.72, 2.25, 2.56, materials, decoration)
        add_panel_frame(wall, 3.15, 2.72, 2.25, 2.56, materials, decoration)
        for u in (-4.55, -1.72, 1.72, 4.55):
            add_pilaster(wall, u, materials, architecture, decoration, width=0.40)
    else:
        add_panel_frame(wall, -2.52, 2.72, 3.45, 2.56, materials, decoration)
        add_panel_frame(wall, 2.52, 2.72, 3.45, 2.56, materials, decoration)
        for u in (-4.55, 0.0, 4.55):
            add_pilaster(wall, u, materials, architecture, decoration, width=0.40)


SIDE_DECOR_CENTERS = (-3.15, 0.0, 3.15)


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
    """Add a framed wall panel with a pilaster on each side."""
    add_panel_frame(
        wall,
        center_u,
        panel_center_z,
        panel_width,
        panel_height,
        materials,
        decoration,
    )
    add_pilaster(
        wall,
        center_u - pilaster_offset,
        materials,
        architecture,
        decoration,
        z_bottom=0.90,
        z_top=4.52,
        width=pilaster_width,
    )
    add_pilaster(
        wall,
        center_u + pilaster_offset,
        materials,
        architecture,
        decoration,
        z_bottom=0.90,
        z_top=4.52,
        width=pilaster_width,
    )


def build_left_short_wall(
    materials: MaterialSet,
    architecture: bpy.types.Collection,
    decoration: bpy.types.Collection,
) -> None:
    """Three equidistant decorative groups, no dark doorway."""
    for center_u in SIDE_DECOR_CENTERS:
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
    """Keep the rounded arched opening in the center, with framed groups on both sides."""
    add_arch_niche(
        "RIGHT",
        center_u=0.0,
        materials=materials,
        architecture=architecture,
        decoration=decoration,
    )

    # Three equidistant upper decorations, aligned with left, center, and right zones.
    for center_u in SIDE_DECOR_CENTERS:
        add_cartouche(
            "RIGHT",
            center_u=center_u,
            center_z=5.58,
            scale=0.48,
            materials=materials,
            decoration=decoration,
        )

    # Framed groups sit directly below the left and right decoration elements.
    for center_u in (-3.15, 3.15):
        add_framed_panel_with_columns(
            "RIGHT",
            center_u,
            materials,
            architecture,
            decoration,
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


def add_twisted_column(
    name: str,
    wall: str,
    u: float,
    base_z: float,
    height: float,
    radius: float,
    materials: MaterialSet,
    architecture: bpy.types.Collection,
    decoration: bpy.types.Collection,
) -> None:
    depth_from_wall = radius + 0.16
    center = wall_local_to_world(wall, u, base_z + height / 2.0, depth_from_wall)

    create_cylinder(
        f"{name} core",
        radius=radius * 0.77,
        depth=height,
        location=center,
        material=materials.plaster_detail,
        collection=architecture,
        vertices=64,
        bevel=0.015,
    )

    # Two raised helical bands create the barley-twist silhouette.
    for ridge in range(2):
        points: list[Vector] = []
        steps = 180
        phase = ridge * math.pi
        for index in range(steps + 1):
            t = index / steps
            angle = phase + t * math.tau * 4.2
            x = center.x + radius * math.cos(angle)
            y = center.y + radius * math.sin(angle)
            z = base_z + t * height
            points.append(Vector((x, y, z)))
        create_curve_object(
            f"{name} helical ridge {ridge}",
            points,
            bevel_depth=radius * 0.115,
            material=materials.plaster_shadow,
            collection=decoration,
            bevel_resolution=4,
        )

    # Bases and capitals are free-standing blocks in the room.
    create_box(
        f"{name} square plinth",
        (radius * 2.6, radius * 2.6, 0.25),
        (center.x, center.y, base_z + 0.125),
        materials.plaster_detail,
        architecture,
        bevel=0.025,
    )
    create_box(
        f"{name} lower base",
        (radius * 2.25, radius * 2.25, 0.16),
        (center.x, center.y, base_z + 0.31),
        materials.plaster_detail,
        architecture,
        bevel=0.020,
    )
    create_box(
        f"{name} capital block",
        (radius * 2.45, radius * 2.45, 0.20),
        (center.x, center.y, base_z + height - 0.10),
        materials.plaster_detail,
        decoration,
        bevel=0.030,
    )
    create_box(
        f"{name} capital slab",
        (radius * 2.80, radius * 2.80, 0.12),
        (center.x, center.y, base_z + height + 0.06),
        materials.plaster_detail,
        decoration,
        bevel=0.020,
    )


def add_twisted_column_doorway(
    wall: str,
    center_u: float,
    materials: MaterialSet,
    architecture: bpy.types.Collection,
    decoration: bpy.types.Collection,
) -> None:
    door_width = 1.40
    door_height = 2.72
    base_z = 0.12

    add_wall_box(
        f"{wall} doorway dark opening",
        wall,
        center_u,
        base_z + door_height / 2.0,
        door_width,
        door_height,
        0.025,
        materials.doorway_dark,
        architecture,
        offset=0.012,
        bevel=0.025,
    )

    # Door panel relief.
    add_panel_frame(
        wall,
        center_u,
        base_z + door_height / 2.0,
        door_width - 0.25,
        door_height - 0.28,
        MaterialSet(
            plaster=materials.doorway_dark,
            plaster_detail=materials.plaster_shadow,
            plaster_shadow=materials.doorway_dark,
            black_marble=materials.black_marble,
            white_marble=materials.white_marble,
            grout=materials.grout,
            doorway_dark=materials.doorway_dark,
        ),
        decoration,
        double_frame=True,
    )

    # Move the twisted columns outward so they flank the framed wall panels
    # on either side of the doorway rather than hugging the door itself.
    for column_u in (-1.90, 1.90):
        add_twisted_column(
            f"{wall} twisted column {column_u:+.2f}",
            wall,
            center_u + column_u,
            base_z=0.18,
            height=3.28,
            radius=0.245,
            materials=materials,
            architecture=architecture,
            decoration=decoration,
        )

    # Entablature over the doorway.
    add_wall_box(
        f"{wall} doorway lintel lower",
        wall,
        center_u,
        3.55,
        2.72,
        0.20,
        0.32,
        materials.plaster_detail,
        decoration,
        bevel=0.025,
    )
    add_wall_box(
        f"{wall} doorway lintel upper",
        wall,
        center_u,
        3.76,
        3.02,
        0.20,
        0.27,
        materials.plaster_detail,
        decoration,
        bevel=0.030,
    )
    add_wall_box(
        f"{wall} doorway crown",
        wall,
        center_u,
        3.93,
        2.55,
        0.13,
        0.23,
        materials.plaster_detail,
        decoration,
        bevel=0.025,
    )


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


def configure_scene() -> None:
    ensure_output_directory()
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.length_unit = "METERS"
    scene.render.resolution_x = RENDER_RESOLUTION[0]
    scene.render.resolution_y = RENDER_RESOLUTION[1]
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.image_settings.color_depth = "16"
    scene.render.film_transparent = False
    scene.render.filepath = str(PNG_OUTPUT_PATH)

    # Cycles only; no alternate render-engine assignments are used.
    scene.render.engine = "CYCLES"
    scene.cycles.samples = CYCLES_SAMPLES
    scene.cycles.use_denoising = True
    scene.cycles.preview_samples = min(48, CYCLES_SAMPLES)
    scene.cycles.max_bounces = 9
    scene.cycles.diffuse_bounces = 4
    scene.cycles.glossy_bounces = 5
    scene.cycles.transparent_max_bounces = 4
    if hasattr(scene.cycles, "use_adaptive_sampling"):
        scene.cycles.use_adaptive_sampling = True

    # Prefer GPU when available, but fall back safely to CPU.
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.get_devices()
        scene.cycles.device = "CPU"
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


def build_scene() -> None:
    loaded_from = globals().get("__file__", "<Blender Text Editor>")
    print(f"\n[Hall {SCRIPT_VERSION}] Running script: {loaded_from}")
    clear_scene()
    configure_scene()

    architecture = get_or_create_collection("01 Architecture")
    floor = get_or_create_collection("02 Marble Floor")
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

    # Central upper reliefs echo the reference image on both principal walls.
    add_cartouche(
        "FRONT",
        center_u=0.0,
        center_z=5.53,
        scale=0.92,
        materials=materials,
        decoration=decoration,
    )
    add_cartouche(
        "BACK",
        center_u=0.0,
        center_z=5.53,
        scale=0.92,
        materials=materials,
        decoration=decoration,
    )

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

    print(f"\nNeoclassical 360 room generated successfully. Version: {SCRIPT_VERSION}")
    print(f"Room dimensions: {ROOM_WIDTH:.2f} m x {ROOM_DEPTH:.2f} m x {ROOM_HEIGHT:.2f} m")
    print(f"Panorama resolution: {RENDER_RESOLUTION[0]} x {RENDER_RESOLUTION[1]}")
    print(f"Python target: {PYTHON_OUTPUT_PATH}")
    print(f"GLB path: {GLB_OUTPUT_PATH}")
    print(f"PNG path: {PNG_OUTPUT_PATH}")
    print("Main camera: Camera_360_Centered")


if __name__ == "__main__":
    build_scene()