"""Shared Cycles panorama room builder for the five second-story rooms.

All rooms use this file for geometry, materials, lighting, camera placement,
render settings, and interactive GLB export. Each room folder can optionally
provide unique.py with add_static(context) and add_interactive(context) hooks.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import importlib.util
import math
import random
import shutil
import sys
from typing import Callable

import bpy
from mathutils import Vector


ROOM_BUILDER_VERSION = "2026-07-30-v7-corner-seam-dimmer-lighting"

ROOM_WIDTH = 6.8
ROOM_DEPTH = 10.0
ROOM_HEIGHT = 3.6
ENTRY_CLEARANCE = 0.45
CAMERA_LOCATION = (0.0, -(ROOM_DEPTH / 2) + ENTRY_CLEARANCE, 1.65)

TILE_WIDTH = 0.205
TILE_HEIGHT = 0.074
WALL_GROUT = 0.0015
TILE_DEPTH = 0.024
TILE_BEVEL = 0.0

FLOOR_TILE_SIZE = 0.285
FLOOR_GAP = 0.0
FLOOR_TILE_DEPTH = 0.036
FLOOR_BEVEL = 0.0

DOOR_WIDTH = 1.15
DOOR_HEIGHT = 2.85
DOOR_DEPTH = 0.05

AREA_LIGHT_POWER = 1400.0
AREA_LIGHT_SIZE = 2.8
AREA_LIGHT_LOCATION = (0.0, 0.0, ROOM_HEIGHT - 0.28)
WORLD_LIGHT_STRENGTH = 0.24


@dataclass(frozen=True)
class RoomDefinition:
    slug: str
    title: str
    number: str
    color_hex: str


@dataclass(frozen=True)
class RenderSettings:
    width: int
    height: int
    samples: int
    use_gpu: bool
    auto_render: bool


@dataclass
class RoomContext:
    definition: RoomDefinition
    output_directory: Path
    scene: bpy.types.Scene
    static_collection: bpy.types.Collection
    interactive_collection: bpy.types.Collection
    wall_material: bpy.types.Material
    grout_material: bpy.types.Material
    ceiling_material: bpy.types.Material
    colored_floor_material: bpy.types.Material
    white_floor_material: bpy.types.Material
    assets_root: Path
    add_box: Callable
    material: Callable
    linear_hex: Callable
    asset_path: Callable
    place_asset: Callable
    place_static_asset: Callable
    place_interactive_asset: Callable


def linear_hex(value: str):
    value = value.lstrip("#")
    rgb = [int(value[i : i + 2], 16) / 255.0 for i in (0, 2, 4)]

    def linear(channel: float) -> float:
        if channel <= 0.04045:
            return channel / 12.92
        return ((channel + 0.055) / 1.055) ** 2.4

    return (*[linear(channel) for channel in rgb], 1.0)


def mix_hex(value: str, target: str = "#FFFFFF", amount: float = 0.25) -> str:
    source = value.lstrip("#")
    target = target.lstrip("#")
    channels = []
    for index in (0, 2, 4):
        left = int(source[index : index + 2], 16)
        right = int(target[index : index + 2], 16)
        channels.append(round(left + (right - left) * amount))
    return "#" + "".join(f"{channel:02X}" for channel in channels)


def set_socket(node, names, value) -> None:
    if isinstance(names, str):
        names = (names,)
    for name in names:
        if name in node.inputs:
            node.inputs[name].default_value = value
            return


def material(name, color, roughness=0.35, coat=0.0, metallic=0.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    set_socket(bsdf, "Base Color", color)
    set_socket(bsdf, "Roughness", roughness)
    set_socket(bsdf, ("Coat Weight", "Clearcoat"), coat)
    set_socket(bsdf, "Metallic", metallic)
    return mat


def marble_material(name, dark, light):
    mat = material(name, dark, roughness=0.20, coat=0.35)
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    bsdf = nodes.get("Principled BSDF")

    noise = nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 3.2
    noise.inputs["Detail"].default_value = 5.0
    noise.inputs["Roughness"].default_value = 0.72
    noise.inputs["Distortion"].default_value = 2.0

    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.28
    ramp.color_ramp.elements[0].color = dark
    ramp.color_ramp.elements[1].position = 0.72
    ramp.color_ramp.elements[1].color = light

    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.12
    bump.inputs["Distance"].default_value = 0.04

    links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(noise.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


def add_box(name, center, size, mat, collection, bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=center)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(mat)

    for old_collection in list(obj.users_collection):
        old_collection.objects.unlink(obj)
    collection.objects.link(obj)

    if bevel > 0:
        modifier = obj.modifiers.new("Rounded edges", "BEVEL")
        modifier.width = bevel
        modifier.segments = 2

    return obj


def append_box(vertices, faces, material_indices, center, size, material_index):
    cx, cy, cz = center
    sx, sy, sz = (value / 2 for value in size)
    start = len(vertices)
    vertices.extend(
        [
            (cx - sx, cy - sy, cz - sz),
            (cx + sx, cy - sy, cz - sz),
            (cx + sx, cy + sy, cz - sz),
            (cx - sx, cy + sy, cz - sz),
            (cx - sx, cy - sy, cz + sz),
            (cx + sx, cy - sy, cz + sz),
            (cx + sx, cy + sy, cz + sz),
            (cx - sx, cy + sy, cz + sz),
        ]
    )
    for face in (
        (0, 3, 2, 1),
        (4, 5, 6, 7),
        (0, 1, 5, 4),
        (1, 2, 6, 5),
        (2, 3, 7, 6),
        (3, 0, 4, 7),
    ):
        faces.append(tuple(start + index for index in face))
        material_indices.append(material_index)


def mesh_from_boxes(name, boxes, mats, collection, bevel=0.0):
    vertices, faces, material_indices = [], [], []
    for center, size, material_index in boxes:
        append_box(vertices, faces, material_indices, center, size, material_index)

    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.validate()
    mesh.update()

    for mat in mats:
        mesh.materials.append(mat)
    for polygon, material_index in zip(mesh.polygons, material_indices):
        polygon.material_index = material_index

    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    if bevel:
        modifier = obj.modifiers.new("Small rounded edges", "BEVEL")
        modifier.width = bevel
        modifier.segments = 2
    return obj


def tile_intervals(minimum, maximum, tile_length, grout, offset=0.0):
    """Return clipped tile intervals that fully cover the bounds."""
    result = []
    step = tile_length + grout
    cursor = minimum + offset
    if offset > 0:
        cursor -= step

    while cursor < maximum:
        lower = max(minimum, cursor)
        upper = min(maximum, cursor + tile_length)
        if upper - lower > max(tile_length * 0.08, 0.004):
            result.append((lower, upper))
        cursor += step

    return result


def grout_intervals(intervals):
    """Return the small spans between consecutive tile intervals."""
    result = []
    for (_, upper), (next_lower, _) in zip(intervals, intervals[1:]):
        if next_lower - upper > 0.00001:
            result.append((upper, next_lower))
    return result


def mesh_from_faces(name, vertices, faces, material_indices, mats, collection):
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.validate()
    mesh.update()

    for mat in mats:
        mesh.materials.append(mat)
    for polygon, material_index in zip(mesh.polygons, material_indices):
        polygon.material_index = material_index

    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    return obj


def append_quad(vertices, faces, material_indices, corners, material_index):
    start = len(vertices)
    vertices.extend(corners)
    faces.append((start, start + 1, start + 2, start + 3))
    material_indices.append(material_index)


def append_wall_surface(
    vertices,
    faces,
    material_indices,
    span_min,
    span_max,
    fixed,
    axis,
    reverse_winding,
):
    """Append one wall as a single, gap-free mosaic of tile and grout faces."""
    row_tiles = tile_intervals(0.0, ROOM_HEIGHT, TILE_HEIGHT, WALL_GROUT)
    row_grout = grout_intervals(row_tiles)

    def add_cell(span_range, z_range, material_index):
        s0, s1 = span_range
        z0, z1 = z_range
        if axis == "x":
            corners = [
                (s0, fixed, z0),
                (s1, fixed, z0),
                (s1, fixed, z1),
                (s0, fixed, z1),
            ]
        else:
            corners = [
                (fixed, s0, z0),
                (fixed, s1, z0),
                (fixed, s1, z1),
                (fixed, s0, z1),
            ]
        if reverse_winding:
            corners.reverse()
        append_quad(vertices, faces, material_indices, corners, material_index)

    for row_index, z_range in enumerate(row_tiles):
        offset = (TILE_WIDTH + WALL_GROUT) / 2 if row_index % 2 else 0.0
        column_tiles = tile_intervals(span_min, span_max, TILE_WIDTH, WALL_GROUT, offset)
        column_grout = grout_intervals(column_tiles)

        for span_range in column_tiles:
            add_cell(span_range, z_range, 0)
        for grout_range in column_grout:
            add_cell(grout_range, z_range, 1)

    for grout_z_range in row_grout:
        add_cell((span_min, span_max), grout_z_range, 1)


def aim(obj, target) -> None:
    obj.rotation_euler = (
        Vector(target) - obj.location
    ).to_track_quat("-Z", "Y").to_euler()


def normalize_angle(angle: float) -> float:
    """Wrap an angle to Blender/Three's conventional [-pi, pi) range."""
    return (angle + math.pi) % (2.0 * math.pi) - math.pi


def horizontal_yaw(direction: Vector) -> float:
    """Return yaw measured from Blender +Y toward +X."""
    return math.atan2(direction.x, direction.y)


def choose_panorama_seam_corner(camera_location) -> tuple[str, Vector, float]:
    """Choose the room corner that produces the least-visible panorama seam.

    The default equirectangular seam points directly behind a camera facing
    Blender +Y. We evaluate all four room corners, choose the one requiring
    the smallest camera rotation, then use physical distance as the tie-break.
    A final stable right-side preference handles perfectly centered rooms.
    """
    camera_point = Vector(camera_location)
    default_seam_yaw = math.pi  # Blender -Y, behind the original +Y view.
    corners = (
        ("entry-right", Vector((ROOM_WIDTH / 2, -ROOM_DEPTH / 2, camera_point.z))),
        ("entry-left", Vector((-ROOM_WIDTH / 2, -ROOM_DEPTH / 2, camera_point.z))),
        ("back-right", Vector((ROOM_WIDTH / 2, ROOM_DEPTH / 2, camera_point.z))),
        ("back-left", Vector((-ROOM_WIDTH / 2, ROOM_DEPTH / 2, camera_point.z))),
    )

    candidates = []
    for order, (name, corner) in enumerate(corners):
        direction = corner - camera_point
        direction.z = 0.0
        corner_yaw = horizontal_yaw(direction)
        rotation_required = abs(normalize_angle(corner_yaw - default_seam_yaw))
        candidates.append(
            (
                round(rotation_required, 12),
                round(direction.length_squared, 12),
                order,
                name,
                corner,
                corner_yaw,
            )
        )

    _, _, _, name, corner, seam_yaw = min(candidates, key=lambda item: item[:3])
    return name, corner, seam_yaw


def orient_camera_seam_to_corner(camera) -> tuple[str, Vector, float, float]:
    """Rotate the panorama camera so its wrap seam passes through a corner.

    Returns the corner name, corner location, Blender camera-forward yaw, and
    the matching Three.js panorama-sphere yaw needed to preserve alignment.
    """
    corner_name, corner, seam_yaw = choose_panorama_seam_corner(camera.location)
    forward_yaw = normalize_angle(seam_yaw - math.pi)
    forward_direction = Vector((math.sin(forward_yaw), math.cos(forward_yaw), 0.0))
    aim(camera, camera.location + forward_direction)

    # The existing +Y-centered render uses -pi/2 in Three.js. Rotating the
    # Blender camera by forward_yaw requires the opposite sphere compensation.
    website_panorama_yaw = normalize_angle(-math.pi / 2.0 - forward_yaw)
    return corner_name, corner, forward_yaw, website_panorama_yaw


def reset_scene() -> bpy.types.Scene:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)

    for collection in list(bpy.data.collections):
        bpy.data.collections.remove(collection)

    for datablocks in (
        bpy.data.meshes,
        bpy.data.curves,
        bpy.data.materials,
        bpy.data.cameras,
        bpy.data.lights,
    ):
        for block in list(datablocks):
            if block.users == 0:
                try:
                    datablocks.remove(block)
                except RuntimeError:
                    pass

    return bpy.context.scene


def configure_render(scene: bpy.types.Scene, settings: RenderSettings, output_file: Path):
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
    scene.render.image_settings.color_mode = "RGB"
    try:
        scene.render.image_settings.color_depth = "8"
    except Exception:
        pass
    scene.render.film_transparent = False
    scene.render.filepath = str(output_file)

    world = bpy.data.worlds.get("World") or bpy.data.worlds.new("World")
    scene.world = world
    world.use_nodes = True
    background = world.node_tree.nodes.get("Background")
    background.inputs["Color"].default_value = (0.09, 0.09, 0.09, 1.0)
    background.inputs["Strength"].default_value = WORLD_LIGHT_STRENGTH


def load_shared_asset_library(blender_root: Path):
    """Load the project-wide reusable asset helper fresh from disk."""
    library_file = blender_root / "shared" / "asset_library.py"
    if not library_file.exists():
        raise FileNotFoundError(
            f"Shared Blender asset library is missing: {library_file}"
        )

    module_name = "hecate_shared_asset_library_live"
    importlib.invalidate_caches()
    sys.modules.pop(module_name, None)

    try:
        pyc_path = Path(importlib.util.cache_from_source(str(library_file)))
        if pyc_path.exists():
            pyc_path.unlink()
    except Exception:
        pass

    spec = importlib.util.spec_from_file_location(module_name, library_file)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load shared asset library: {library_file}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def load_unique_module(unique_file: Path):
    if not unique_file.exists():
        return None

    module_name = f"room_unique_{unique_file.parent.name}"
    spec = importlib.util.spec_from_file_location(module_name, unique_file)
    if spec is None or spec.loader is None:
        return None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def call_unique_hook(module, hook_name: str, context: RoomContext):
    if module is None:
        return
    hook = getattr(module, hook_name, None)
    if callable(hook):
        hook(context)


def hide_interactive_geometry_for_panorama(collection: bpy.types.Collection):
    """Hide browser-only objects while retaining the tagged panorama light.

    Hiding the entire interactive collection would remove the room's shared
    area light. Instead, only objects explicitly tagged ``keep_for_panorama``
    remain render-visible; everything else is temporarily hidden and restored.
    """
    previous_states = []
    for obj in collection.all_objects:
        # The shared room light remains active for the panorama. Any light that
        # belongs to a reusable interactive asset is hidden with that asset so
        # its browser-only lighting is not accidentally baked into the image.
        if obj.type == "LIGHT" and obj.get("keep_for_panorama", False):
            continue
        previous_states.append((obj, obj.hide_render))
        obj.hide_render = True
    return previous_states


def restore_render_visibility(previous_states) -> None:
    """Restore object render flags after the panorama has finished."""
    for obj, was_hidden in previous_states:
        obj.hide_render = was_hidden


def export_interactive_collection(
    main_scene: bpy.types.Scene,
    collection: bpy.types.Collection,
    output_file: Path,
) -> None:
    export_scene = bpy.data.scenes.new("Temporary_Interactive_Export")
    export_scene.collection.children.link(collection)
    previous_scene = bpy.context.window.scene

    try:
        bpy.context.window.scene = export_scene
        bpy.ops.export_scene.gltf(
            filepath=str(output_file),
            export_format="GLB",
            export_lights=True,
            export_cameras=False,
            export_apply=True,
            export_extras=True,
        )
    finally:
        bpy.context.window.scene = previous_scene
        export_scene.collection.children.unlink(collection)
        bpy.data.scenes.remove(export_scene)
        bpy.context.window.scene = main_scene


def build_room(
    definition: RoomDefinition,
    settings: RenderSettings,
    rooms_root: Path,
) -> None:
    random.seed(946)

    output_directory = rooms_root / definition.slug
    output_directory.mkdir(parents=True, exist_ok=True)

    blender_root = rooms_root.parent
    project_root = blender_root.parent
    assets_root = project_root / "public" / "scenes" / "assets"
    asset_library = load_shared_asset_library(blender_root)

    blend_file = output_directory / f"{definition.slug}-room.blend"
    panorama_file = output_directory / f"{definition.slug}-room-panorama.png"
    interactive_file = output_directory / f"{definition.slug}-room-interactive.glb"

    print(f"Room builder version: {ROOM_BUILDER_VERSION}")
    print(f"Room builder source:  {Path(__file__).resolve()}")

    # Never allow an old panorama to masquerade as a successful new render.
    if settings.auto_render and panorama_file.exists():
        panorama_file.unlink()

    scene = reset_scene()
    configure_render(scene, settings, panorama_file)

    static_collection = bpy.data.collections.new("STATIC_ROOM")
    interactive_collection = bpy.data.collections.new("INTERACTIVE_EXPORT")
    scene.collection.children.link(static_collection)
    scene.collection.children.link(interactive_collection)

    lighter_color = mix_hex(definition.color_hex, amount=0.27)

    wall_mat = material(
        f"{definition.title} glossy tile",
        linear_hex(definition.color_hex),
        roughness=0.085,
        coat=0.74,
    )
    grout_mat = material("White grout", linear_hex("#EEF2EC"), roughness=0.76)
    ceiling_mat = material("Plain ceiling", linear_hex("#D8D8D8"), roughness=0.65)
    colored_floor = marble_material(
        f"{definition.title} colored marble",
        linear_hex(definition.color_hex),
        linear_hex(lighter_color),
    )
    white_floor = marble_material(
        "White marble",
        linear_hex("#D5DBD8"),
        linear_hex("#FBFBF7"),
    )

    add_box(
        "Floor substrate",
        (0, 0, -0.045),
        (ROOM_WIDTH, ROOM_DEPTH, 0.09),
        grout_mat,
        static_collection,
    )
    add_box(
        "Ceiling",
        (0, 0, ROOM_HEIGHT + 0.04),
        (ROOM_WIDTH, ROOM_DEPTH, 0.08),
        ceiling_mat,
        static_collection,
    )

    wall_vertices = []
    wall_faces = []
    wall_material_indices = []

    # Back wall inward normal: -Y.
    append_wall_surface(
        wall_vertices,
        wall_faces,
        wall_material_indices,
        -ROOM_WIDTH / 2,
        ROOM_WIDTH / 2,
        ROOM_DEPTH / 2,
        "x",
        False,
    )
    # Entry wall inward normal: +Y.
    append_wall_surface(
        wall_vertices,
        wall_faces,
        wall_material_indices,
        -ROOM_WIDTH / 2,
        ROOM_WIDTH / 2,
        -ROOM_DEPTH / 2,
        "x",
        True,
    )
    # Left wall inward normal: +X.
    append_wall_surface(
        wall_vertices,
        wall_faces,
        wall_material_indices,
        -ROOM_DEPTH / 2,
        ROOM_DEPTH / 2,
        -ROOM_WIDTH / 2,
        "y",
        False,
    )
    # Right wall inward normal: -X.
    append_wall_surface(
        wall_vertices,
        wall_faces,
        wall_material_indices,
        -ROOM_DEPTH / 2,
        ROOM_DEPTH / 2,
        ROOM_WIDTH / 2,
        "y",
        True,
    )

    mesh_from_faces(
        "Wall_Surface_Mosaic",
        wall_vertices,
        wall_faces,
        wall_material_indices,
        [wall_mat, grout_mat],
        static_collection,
    )

    floor_boxes = []
    x_intervals = tile_intervals(-ROOM_WIDTH / 2, ROOM_WIDTH / 2, FLOOR_TILE_SIZE, FLOOR_GAP)
    y_intervals = tile_intervals(-ROOM_DEPTH / 2, ROOM_DEPTH / 2, FLOOR_TILE_SIZE, FLOOR_GAP)
    for ix, x_range in enumerate(x_intervals):
        for iy, y_range in enumerate(y_intervals):
            floor_boxes.append(
                (
                    ((x_range[0] + x_range[1]) / 2, (y_range[0] + y_range[1]) / 2, FLOOR_TILE_DEPTH / 2),
                    (x_range[1] - x_range[0], y_range[1] - y_range[0], FLOOR_TILE_DEPTH),
                    (ix + iy) % 2,
                )
            )

    mesh_from_boxes(
        "Alternating marble floor",
        floor_boxes,
        [colored_floor, white_floor],
        static_collection,
        bevel=FLOOR_BEVEL,
    )

    door_mat = material("Room door", linear_hex("#050505"), roughness=0.24, coat=0.10)
    add_box(
        "Entry_Door_Frame",
        (0, -ROOM_DEPTH / 2 + DOOR_DEPTH * 0.55, (DOOR_HEIGHT + 0.12) / 2),
        (DOOR_WIDTH + 0.14, DOOR_DEPTH, DOOR_HEIGHT + 0.12),
        door_mat,
        static_collection,
    )
    add_box(
        "Entry_Door",
        (0, -ROOM_DEPTH / 2 + DOOR_DEPTH * 1.1, DOOR_HEIGHT / 2),
        (DOOR_WIDTH, DOOR_DEPTH, DOOR_HEIGHT),
        door_mat,
        static_collection,
    )

    light_data = bpy.data.lights.new("Room_Area_Light", type="AREA")
    light_data.energy = AREA_LIGHT_POWER
    light_data.shape = "SQUARE"
    light_data.size = AREA_LIGHT_SIZE
    light = bpy.data.objects.new("Room_Area_Light", light_data)
    interactive_collection.objects.link(light)
    light.location = AREA_LIGHT_LOCATION
    light.rotation_euler = (math.radians(180.0), 0.0, 0.0)
    light["keep_for_panorama"] = True

    interaction_origin = bpy.data.objects.new("Interaction_Origin", None)
    interactive_collection.objects.link(interaction_origin)
    interaction_origin.location = CAMERA_LOCATION

    def asset_path(asset_id, *, file_name=None):
        return asset_library.resolve_asset_path(
            assets_root,
            asset_id,
            file_name=file_name,
        )

    def place_asset(asset_id, *, collection, **placement):
        return asset_library.place_asset(
            assets_root=assets_root,
            asset_id=asset_id,
            collection=collection,
            **placement,
        )

    def place_static_asset(asset_id, **placement):
        return place_asset(
            asset_id,
            collection=static_collection,
            **placement,
        )

    def place_interactive_asset(
        asset_id,
        *,
        name=None,
        grabbable=False,
        extras=None,
        **placement,
    ):
        root_name = name or Path(str(asset_id)).stem or "SharedAsset"
        if grabbable and not root_name.startswith("Grab_"):
            root_name = f"Grab_{root_name}"

        root_extras = dict(extras or {})
        root_extras.setdefault("draggable", bool(grabbable))
        root_extras.setdefault("interaction", "grab" if grabbable else "static")

        return place_asset(
            asset_id,
            collection=interactive_collection,
            name=root_name,
            extras=root_extras,
            **placement,
        )

    context = RoomContext(
        definition=definition,
        output_directory=output_directory,
        scene=scene,
        static_collection=static_collection,
        interactive_collection=interactive_collection,
        wall_material=wall_mat,
        grout_material=grout_mat,
        ceiling_material=ceiling_mat,
        colored_floor_material=colored_floor,
        white_floor_material=white_floor,
        assets_root=assets_root,
        add_box=add_box,
        material=material,
        linear_hex=linear_hex,
        asset_path=asset_path,
        place_asset=place_asset,
        place_static_asset=place_static_asset,
        place_interactive_asset=place_interactive_asset,
    )

    unique_module = load_unique_module(output_directory / "unique.py")
    call_unique_hook(unique_module, "add_static", context)
    call_unique_hook(unique_module, "add_interactive", context)

    camera_data = bpy.data.cameras.new("Panorama_Camera")
    camera = bpy.data.objects.new("Panorama_Camera", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera.location = CAMERA_LOCATION
    camera.data.type = "PANO"

    if hasattr(camera.data, "panorama_type"):
        camera.data.panorama_type = "EQUIRECTANGULAR"
    else:
        cycles_camera = getattr(camera.data, "cycles", None)
        if cycles_camera is not None and hasattr(cycles_camera, "panorama_type"):
            cycles_camera.panorama_type = "EQUIRECTANGULAR"
        else:
            raise RuntimeError(
                "This Blender build does not expose an equirectangular panorama setting."
            )

    seam_corner_name, seam_corner, camera_forward_yaw, website_panorama_yaw = (
        orient_camera_seam_to_corner(camera)
    )
    camera["panorama_seam_corner"] = seam_corner_name
    camera["panorama_forward_yaw"] = camera_forward_yaw
    camera["website_panorama_yaw"] = website_panorama_yaw
    scene["panorama_seam_corner"] = seam_corner_name
    scene["website_panorama_yaw"] = website_panorama_yaw
    interaction_origin["panorama_seam_corner"] = seam_corner_name
    interaction_origin["website_panorama_yaw"] = website_panorama_yaw

    print(
        "Panorama seam:",
        seam_corner_name,
        tuple(round(value, 4) for value in seam_corner),
    )
    print(f"Website panorama yaw: {website_panorama_yaw:.12f} radians")

    bpy.ops.wm.save_as_mainfile(filepath=str(blend_file))

    if settings.auto_render:
        # Keep the area light active, but prevent live GLB objects such as the
        # coffee table from being baked into the panorama behind themselves.
        previous_render_states = hide_interactive_geometry_for_panorama(
            interactive_collection
        )
        try:
            bpy.ops.render.render(write_still=True)
            if not panorama_file.exists():
                raise RuntimeError(f"Panorama render did not create {panorama_file}")
        finally:
            restore_render_visibility(previous_render_states)
    else:
        print(f"Skipped panorama render for {definition.slug}.")

    export_interactive_collection(scene, interactive_collection, interactive_file)
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_file))

    # Copy directly into the website so the browser cannot keep using an old
    # public asset after a successful Blender run.
    project_root = rooms_root.parent.parent
    public_directory = project_root / "public" / "scenes" / "rooms" / definition.slug
    public_directory.mkdir(parents=True, exist_ok=True)
    if settings.auto_render:
        shutil.copy2(panorama_file, public_directory / "panorama.png")
    shutil.copy2(interactive_file, public_directory / "interactive.glb")

    print(f"Built {definition.title}")
    print(f"  Blend:       {blend_file}")
    print(f"  Panorama:    {panorama_file}")
    print(f"  Interactive: {interactive_file}")
    print(f"  Website:     {public_directory}")
