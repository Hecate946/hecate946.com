"""Green-room Cycles furniture, chess set, and click-to-view metadata.

The table and complete Staunton set are permanent scene geometry, so Cycles
renders them with exactly the same materials, shadows, reflections, and pendant
light as the room. The browser receives only one invisible table hitbox whose
metadata requests the ``board`` panorama view.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Iterable, Sequence

import bpy
from mathutils import Matrix, Vector


# =============================================================================
# TABLE SETTINGS
# =============================================================================

INCH = 0.0254

# The 48-inch square top gives the 22-inch tournament chessboard thirteen
# inches of breathing room on every side. A 36-inch height and proportionally
# heavier members make the table read as a large, monolithic centerpiece.
CHESSBOARD_SIZE = 22.0 * INCH
TABLE_WIDTH = 48.0 * INCH
TABLE_DEPTH = 48.0 * INCH
TABLE_HEIGHT = 36.0 * INCH

TOP_THICKNESS = 3.5 * INCH
LEG_THICKNESS = 8.5 * INCH
APRON_HEIGHT = 7.5 * INCH
APRON_THICKNESS = 3.0 * INCH
EDGE_BEVEL = 0.24 * INCH

# The shared pendant is ROOM_DEPTH / 3 (1.90 m) behind the room center. The
# table uses that same X/Y center so the chessboard sits directly beneath it.
TABLE_LOCATION = (0.0, 1.90, 0.0)
BOARD_CLEARANCE = 0.003
BOARD_VIEW_CAMERA_LOCATION = (0.0, 0.62, 1.38)
BOARD_VIEW_TARGET = (0.0, TABLE_LOCATION[1], TABLE_HEIGHT + 0.075)

# One embedded 1K texture set is shared by the whole table mesh. The GLB remains
# lightweight while retaining only a very subtle grain beneath the matte finish.
TEXTURE_SIZE = 1024
TEXTURE_SEED = 946
WOOD_REPEAT_METERS = 0.34


# =============================================================================
# SHADER / TEXTURE HELPERS
# =============================================================================


def _set_socket(node, names: str | Iterable[str], value) -> None:
    if isinstance(names, str):
        names = (names,)
    for name in names:
        if name in node.inputs:
            node.inputs[name].default_value = value
            return


def _remove_existing_datablock(collection, name: str) -> None:
    existing = collection.get(name)
    if existing is not None:
        collection.remove(existing)


def _create_image(name: str, pixels, *, color_space: str) -> bpy.types.Image:
    """Create and pack one generated image so the GLB can embed it."""
    import numpy as np

    _remove_existing_datablock(bpy.data.images, name)

    height, width, channels = pixels.shape
    if channels != 4:
        raise ValueError(f"{name} must contain RGBA pixels.")

    image = bpy.data.images.new(
        name=name,
        width=width,
        height=height,
        alpha=True,
        float_buffer=False,
    )
    image.file_format = "PNG"
    image.pixels.foreach_set(np.asarray(pixels, dtype=np.float32).ravel())
    image.update()

    try:
        image.colorspace_settings.name = color_space
    except Exception:
        pass

    # Packed generated images are embedded by Blender's GLB exporter rather
    # than becoming loose texture dependencies in public/scenes.
    try:
        image.pack()
    except RuntimeError:
        pass

    return image


def _blur_wrap(values, iterations: int = 4):
    """Small tileable blur using only NumPy operations included with Blender."""
    import numpy as np

    result = values
    for _ in range(iterations):
        result = (
            result
            + np.roll(result, 1, axis=0)
            + np.roll(result, -1, axis=0)
            + np.roll(result, 1, axis=1)
            + np.roll(result, -1, axis=1)
        ) / 5.0
    return result


def _create_matte_black_texture_set(size: int = TEXTURE_SIZE):
    """Generate subtle neutral-black PBR maps for a matte wood finish.

    The grain runs in the texture's U direction. Custom UVs rotate that grain
    along the tabletop, aprons, and vertical legs without adding materials or
    draw calls. High roughness and restrained normals keep the result matte.
    """
    import numpy as np

    rng = np.random.default_rng(TEXTURE_SEED)
    u, v = np.meshgrid(
        np.linspace(0.0, 1.0, size, endpoint=False, dtype=np.float32),
        np.linspace(0.0, 1.0, size, endpoint=False, dtype=np.float32),
    )

    # Long, gently wandering fibers. The periodic terms keep the texture
    # tileable when the UV coordinates repeat across the larger surfaces.
    warp = (
        0.020 * np.sin(math.tau * (u * 1.0))
        + 0.010 * np.sin(math.tau * (u * 3.0 + 0.18))
        + 0.005 * np.sin(math.tau * (u * 7.0 - 0.31))
    )
    fibers = (
        0.52 * np.sin(math.tau * (v * 18.0 + warp))
        + 0.26 * np.sin(math.tau * (v * 43.0 + warp * 1.8 + u * 0.35))
        + 0.12 * np.sin(math.tau * (v * 101.0 - warp * 1.2))
    )

    pores = _blur_wrap(rng.normal(0.0, 1.0, (size, size)).astype(np.float32), 3)
    fine = rng.normal(0.0, 1.0, (size, size)).astype(np.float32)

    height = 0.56 + fibers * 0.145 + pores * 0.052 + fine * 0.010
    height = np.clip(height, 0.0, 1.0)

    # Neutral, true black rather than dark brown. The small grayscale range
    # keeps the surface readable without turning the grain into glossy streaks.
    luminance = 0.010 + height * 0.018
    base = np.empty((size, size, 4), dtype=np.float32)
    base[..., 0] = luminance
    base[..., 1] = luminance
    base[..., 2] = luminance
    base[..., 3] = 1.0

    # High roughness is embedded in the GLB, so the table stays matte in Three.js.
    rough = np.clip(0.72 + (1.0 - height) * 0.10 + pores * 0.012, 0.68, 0.86)
    roughness = np.empty((size, size, 4), dtype=np.float32)
    roughness[..., 0] = rough
    roughness[..., 1] = rough
    roughness[..., 2] = rough
    roughness[..., 3] = 1.0

    # Convert the same restrained height field into a tangent-space normal map.
    dv, du = np.gradient(height)
    normal_strength = 1.15
    nx = -du * normal_strength
    ny = -dv * normal_strength
    nz = np.ones_like(nx)
    length = np.sqrt(nx * nx + ny * ny + nz * nz)

    normal = np.empty((size, size, 4), dtype=np.float32)
    normal[..., 0] = nx / length * 0.5 + 0.5
    normal[..., 1] = ny / length * 0.5 + 0.5
    normal[..., 2] = nz / length * 0.5 + 0.5
    normal[..., 3] = 1.0

    return (
        _create_image("GreenTable_MatteBlack_BaseColor", base, color_space="sRGB"),
        _create_image("GreenTable_MatteBlack_Roughness", roughness, color_space="Non-Color"),
        _create_image("GreenTable_MatteBlack_Normal", normal, color_space="Non-Color"),
    )


def _create_matte_black_material() -> bpy.types.Material:
    # Remove both names so repeated builds cannot retain a stale glossy material.
    _remove_existing_datablock(bpy.data.materials, "GreenTable_AfricanBlackwood")
    _remove_existing_datablock(bpy.data.materials, "GreenTable_MatteBlack")
    base_image, roughness_image, normal_image = _create_matte_black_texture_set()

    material = bpy.data.materials.new("GreenTable_MatteBlack")
    material.use_nodes = True
    material.diffuse_color = (0.008, 0.008, 0.008, 1.0)

    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()

    output = nodes.new("ShaderNodeOutputMaterial")
    output.location = (720, 0)

    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (420, 0)
    _set_socket(bsdf, "Roughness", 0.76)
    _set_socket(bsdf, ("Coat Weight", "Clearcoat"), 0.0)
    _set_socket(bsdf, ("Coat Roughness", "Clearcoat Roughness"), 0.65)
    _set_socket(bsdf, ("Specular IOR Level", "Specular"), 0.24)

    base_texture = nodes.new("ShaderNodeTexImage")
    base_texture.name = "Matte black color"
    base_texture.image = base_image
    base_texture.interpolation = "Linear"
    base_texture.extension = "REPEAT"
    base_texture.location = (-520, 150)

    roughness_texture = nodes.new("ShaderNodeTexImage")
    roughness_texture.name = "Matte black roughness"
    roughness_texture.image = roughness_image
    roughness_texture.interpolation = "Linear"
    roughness_texture.extension = "REPEAT"
    roughness_texture.location = (-520, -70)

    normal_texture = nodes.new("ShaderNodeTexImage")
    normal_texture.name = "Matte black normal"
    normal_texture.image = normal_image
    normal_texture.interpolation = "Linear"
    normal_texture.extension = "REPEAT"
    normal_texture.location = (-520, -290)

    normal_map = nodes.new("ShaderNodeNormalMap")
    normal_map.location = (110, -230)
    normal_map.inputs["Strength"].default_value = 0.18

    links.new(base_texture.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(roughness_texture.outputs["Color"], bsdf.inputs["Roughness"])
    links.new(normal_texture.outputs["Color"], normal_map.inputs["Color"])
    links.new(normal_map.outputs["Normal"], bsdf.inputs["Normal"])
    links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])

    return material


# =============================================================================
# GEOMETRY / UV HELPERS
# =============================================================================


_FACE_DEFINITIONS = (
    ("bottom", (0, 3, 2, 1)),
    ("top", (4, 5, 6, 7)),
    ("front", (0, 1, 5, 4)),
    ("right", (1, 2, 6, 5)),
    ("back", (2, 3, 7, 6)),
    ("left", (3, 0, 4, 7)),
)


def _grain_uv(vertex: Sequence[float], face: str, grain_mode: str) -> tuple[float, float]:
    """Map U along the desired visible grain direction for each component."""
    x, y, z = vertex
    scale = WOOD_REPEAT_METERS

    if grain_mode == "vertical":
        if face in {"front", "back"}:
            return z / scale, x / scale
        if face in {"left", "right"}:
            return z / scale, y / scale
        return x / scale, y / scale

    if grain_mode == "x":
        if face in {"front", "back"}:
            return x / scale, z / scale
        if face in {"top", "bottom"}:
            return x / scale, y / scale
        return z / scale, y / scale

    if grain_mode == "y":
        if face in {"left", "right"}:
            return y / scale, z / scale
        if face in {"top", "bottom"}:
            return y / scale, x / scale
        return z / scale, x / scale

    # Tabletop: fibers run left-to-right on the broad surface, then turn around
    # each side edge as they would on a solid wood slab.
    if face in {"top", "bottom"}:
        return x / scale, y / scale
    if face in {"front", "back"}:
        return x / scale, z / scale
    return y / scale, z / scale


def _append_box(
    vertices: list,
    faces: list,
    face_uvs: list,
    center: Sequence[float],
    size: Sequence[float],
    grain_mode: str,
) -> None:
    cx, cy, cz = center
    sx, sy, sz = (dimension / 2.0 for dimension in size)
    start = len(vertices)

    box_vertices = (
        (cx - sx, cy - sy, cz - sz),
        (cx + sx, cy - sy, cz - sz),
        (cx + sx, cy + sy, cz - sz),
        (cx - sx, cy + sy, cz - sz),
        (cx - sx, cy - sy, cz + sz),
        (cx + sx, cy - sy, cz + sz),
        (cx + sx, cy + sy, cz + sz),
        (cx - sx, cy + sy, cz + sz),
    )
    vertices.extend(box_vertices)

    for face_name, indices in _FACE_DEFINITIONS:
        faces.append(tuple(start + index for index in indices))
        face_uvs.append(
            tuple(_grain_uv(box_vertices[index], face_name, grain_mode) for index in indices)
        )


def _create_table_mesh(
    collection: bpy.types.Collection,
    material: bpy.types.Material,
) -> bpy.types.Object:
    """Build the complete table as one efficient, selectable mesh."""
    vertices: list[tuple[float, float, float]] = []
    faces: list[tuple[int, int, int, int]] = []
    face_uvs: list[tuple[tuple[float, float], ...]] = []

    top_bottom = TABLE_HEIGHT - TOP_THICKNESS
    leg_height = top_bottom
    apron_center_z = top_bottom - APRON_HEIGHT / 2.0

    leg_x = TABLE_WIDTH / 2.0 - LEG_THICKNESS / 2.0
    leg_y = TABLE_DEPTH / 2.0 - LEG_THICKNESS / 2.0

    # Flush slab: its outer faces align exactly with the outside leg faces.
    _append_box(
        vertices,
        faces,
        face_uvs,
        (0.0, 0.0, TABLE_HEIGHT - TOP_THICKNESS / 2.0),
        (TABLE_WIDTH, TABLE_DEPTH, TOP_THICKNESS),
        "top",
    )

    for x in (-leg_x, leg_x):
        for y in (-leg_y, leg_y):
            _append_box(
                vertices,
                faces,
                face_uvs,
                (x, y, leg_height / 2.0),
                (LEG_THICKNESS, LEG_THICKNESS, leg_height),
                "vertical",
            )

    apron_span_x = TABLE_WIDTH - 2.0 * LEG_THICKNESS
    apron_span_y = TABLE_DEPTH - 2.0 * LEG_THICKNESS

    for y in (-leg_y, leg_y):
        _append_box(
            vertices,
            faces,
            face_uvs,
            (0.0, y, apron_center_z),
            (apron_span_x, APRON_THICKNESS, APRON_HEIGHT),
            "x",
        )

    for x in (-leg_x, leg_x):
        _append_box(
            vertices,
            faces,
            face_uvs,
            (x, 0.0, apron_center_z),
            (APRON_THICKNESS, apron_span_y, APRON_HEIGHT),
            "y",
        )

    mesh = bpy.data.meshes.new("GreenCoffeeTable_MeshData")
    mesh.from_pydata(vertices, [], faces)
    mesh.validate(verbose=False)
    mesh.update()
    mesh.materials.append(material)

    uv_layer = mesh.uv_layers.new(name="BlackwoodUV")
    for polygon, polygon_uvs in zip(mesh.polygons, face_uvs):
        for loop_index, uv in zip(polygon.loop_indices, polygon_uvs):
            uv_layer.data[loop_index].uv = uv

    table = bpy.data.objects.new("GreenCoffeeTable_Mesh", mesh)
    collection.objects.link(table)

    bevel = table.modifiers.new("Softened handcrafted edges", "BEVEL")
    bevel.width = EDGE_BEVEL
    bevel.segments = 3
    bevel.limit_method = "ANGLE"
    bevel.angle_limit = math.radians(25.0)
    try:
        bevel.harden_normals = True
    except Exception:
        pass

    table["asset_id"] = "green-coffee-table"
    table["surface_height_m"] = TABLE_HEIGHT
    table["width_m"] = TABLE_WIDTH
    table["depth_m"] = TABLE_DEPTH
    table["chessboard_size_m"] = CHESSBOARD_SIZE
    return table


def _create_empty(
    name: str,
    location: Sequence[float],
    collection: bpy.types.Collection,
    parent: bpy.types.Object,
    *,
    display_type: str = "PLAIN_AXES",
    display_size: float = 0.08,
) -> bpy.types.Object:
    empty = bpy.data.objects.new(name, None)
    collection.objects.link(empty)
    empty.parent = parent
    empty.location = location
    empty.empty_display_type = display_type
    empty.empty_display_size = display_size
    return empty


def _aim_local(obj: bpy.types.Object, local_target: Sequence[float]) -> None:
    direction = Vector(local_target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def _add_coffee_table(context) -> bpy.types.Object:
    collection = context.static_collection
    material = _create_matte_black_material()

    root = bpy.data.objects.new("GreenRoom_TableChess", None)
    collection.objects.link(root)
    root.location = TABLE_LOCATION
    root.empty_display_type = "CUBE"
    root.empty_display_size = 0.22
    root["asset_id"] = "green-table-chess"
    root["rendered_by"] = "cycles"

    table = _create_table_mesh(collection, material)
    table.parent = root
    return root


def _object_number(name: str, base: str) -> int | None:
    if name == base:
        return 0
    prefix = f"{base}."
    if not name.startswith(prefix):
        return None
    suffix = name[len(prefix) :]
    return int(suffix) if suffix.isdigit() else None


def _world_bounds(objects: Sequence[bpy.types.Object]) -> tuple[Vector, Vector]:
    points = [
        obj.matrix_world @ Vector(corner)
        for obj in objects
        for corner in obj.bound_box
    ]
    if not points:
        raise RuntimeError("Cannot calculate chess-set bounds from an empty object list.")
    return (
        Vector(
            (
                min(point.x for point in points),
                min(point.y for point in points),
                min(point.z for point in points),
            )
        ),
        Vector(
            (
                max(point.x for point in points),
                max(point.y for point in points),
                max(point.z for point in points),
            )
        ),
    )


def _main_chess_meshes(loaded_objects: Sequence[bpy.types.Object]) -> list[bpy.types.Object]:
    meshes = [obj for obj in loaded_objects if obj and obj.type == "MESH"]

    exact = []
    for obj in meshes:
        circle_number = _object_number(obj.name, "Circle")
        if obj.name == "Plane" or (circle_number is not None and circle_number <= 31):
            exact.append(obj)
    if len(exact) >= 25:
        return exact

    if not meshes:
        raise RuntimeError("The Staunton source file contains no mesh objects.")

    def footprint(obj: bpy.types.Object) -> float:
        points = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
        xs = [point.x for point in points]
        ys = [point.y for point in points]
        return (max(xs) - min(xs)) + (max(ys) - min(ys))

    board = max(meshes, key=footprint)
    board_points = [board.matrix_world @ Vector(corner) for corner in board.bound_box]
    min_x = min(point.x for point in board_points)
    max_x = max(point.x for point in board_points)
    min_y = min(point.y for point in board_points)
    max_y = max(point.y for point in board_points)
    pad_x = max((max_x - min_x) * 0.20, 0.01)
    pad_y = max((max_y - min_y) * 0.20, 0.01)

    selected = [
        obj
        for obj in meshes
        if min_x - pad_x <= obj.matrix_world.translation.x <= max_x + pad_x
        and min_y - pad_y <= obj.matrix_world.translation.y <= max_y + pad_y
    ]
    if len(selected) < 20:
        raise RuntimeError(
            "Could not reliably identify the assembled board and pieces in chess set.blend."
        )
    return selected


def _principled_material(
    name: str,
    color: Sequence[float],
    *,
    roughness: float,
    coat: float = 0.0,
) -> bpy.types.Material:
    material = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    material.use_nodes = True
    material.diffuse_color = (*color[:3], 1.0)

    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    output.location = (320, 0)
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (0, 0)
    _set_socket(bsdf, "Base Color", (*color[:3], 1.0))
    _set_socket(bsdf, "Roughness", roughness)
    _set_socket(bsdf, ("Coat Weight", "Clearcoat"), coat)
    _set_socket(
        bsdf,
        ("Coat Roughness", "Clearcoat Roughness"),
        max(roughness * 0.65, 0.08),
    )
    links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])
    return material


def _replace_chess_materials(chess_objects: Sequence[bpy.types.Object]) -> None:
    dark_piece = _principled_material(
        "MAT_Chess_Dark_Piece", (0.012, 0.009, 0.007), roughness=0.22, coat=0.22
    )
    light_piece = _principled_material(
        "MAT_Chess_Ivory_Piece", (0.72, 0.61, 0.43), roughness=0.25, coat=0.20
    )
    dark_square = _principled_material(
        "MAT_Chess_Dark_Square", (0.025, 0.018, 0.012), roughness=0.28, coat=0.16
    )
    light_square = _principled_material(
        "MAT_Chess_Light_Square", (0.62, 0.50, 0.34), roughness=0.30, coat=0.14
    )
    edge = _principled_material(
        "MAT_Chess_Board_Edge", (0.010, 0.007, 0.005), roughness=0.24, coat=0.20
    )

    def replacement(old_name: str) -> bpy.types.Material:
        lowered = old_name.lower()
        if "black chess" in lowered:
            return dark_piece
        if "white chess" in lowered:
            return light_piece
        if "white square" in lowered:
            return light_square
        if "red squared" in lowered or "dark square" in lowered:
            return dark_square
        if "green edge" in lowered or "edge" in lowered:
            return edge
        if "white" in lowered or "ivory" in lowered:
            return light_piece
        if "black" in lowered or "dark" in lowered:
            return dark_piece
        return edge

    for obj in chess_objects:
        if not obj.material_slots:
            obj.data.materials.append(dark_piece)
            continue
        for slot in obj.material_slots:
            old_name = slot.material.name if slot.material else ""
            slot.material = replacement(old_name)


def _append_chess_set(context, parent: bpy.types.Object) -> None:
    source = (
        Path(context.assets_root)
        / "chess"
        / "standard-staunton"
        / "chess set.blend"
    )
    if not source.is_file():
        raise FileNotFoundError(
            "Missing Staunton source asset. Expected: "
            f"{source}. Keep the original file at that exact path."
        )

    with bpy.data.libraries.load(str(source), link=False) as (data_from, data_to):
        data_to.objects = list(data_from.objects)

    loaded_objects = [obj for obj in data_to.objects if obj is not None]
    for obj in loaded_objects:
        if not obj.users_collection:
            context.static_collection.objects.link(obj)

    chess_objects = _main_chess_meshes(loaded_objects)
    chess_set = set(chess_objects)

    # Detach the selected meshes before deleting cameras, examples, and old
    # helper parents from the source file. Preserve each world transform.
    for obj in chess_objects:
        world = obj.matrix_world.copy()
        obj.parent = None
        obj.matrix_world = world

    for obj in loaded_objects:
        if obj not in chess_set:
            bpy.data.objects.remove(obj, do_unlink=True)

    _replace_chess_materials(chess_objects)

    minimum, maximum = _world_bounds(chess_objects)
    footprint = max(maximum.x - minimum.x, maximum.y - minimum.y)
    if footprint <= 1e-8:
        raise RuntimeError("The appended chess-set footprint is zero.")

    scale = CHESSBOARD_SIZE / footprint
    center_x = (minimum.x + maximum.x) * 0.5
    center_y = (minimum.y + maximum.y) * 0.5
    target_bottom_z = TABLE_HEIGHT + BOARD_CLEARANCE
    transform = (
        Matrix.Translation((TABLE_LOCATION[0], TABLE_LOCATION[1], target_bottom_z))
        @ Matrix.Scale(scale, 4)
        @ Matrix.Translation((-center_x, -center_y, -minimum.z))
    )

    for obj in chess_objects:
        obj.matrix_world = transform @ obj.matrix_world
        world = obj.matrix_world.copy()
        obj.parent = parent
        obj.matrix_world = world
        obj["object_role"] = "chess_piece_or_board"
        obj["rendered_by"] = "cycles"


def _add_table_click_target(context) -> bpy.types.Object:
    hitbox_material = context.material(
        "Browser-only table hitbox",
        (0.0, 0.0, 0.0, 1.0),
        roughness=1.0,
    )
    hitbox = context.add_box(
        "ViewTarget_GreenTable",
        (
            TABLE_LOCATION[0],
            TABLE_LOCATION[1],
            (TABLE_HEIGHT + 0.48) / 2.0,
        ),
        (TABLE_WIDTH * 1.04, TABLE_DEPTH * 1.04, TABLE_HEIGHT + 0.48),
        hitbox_material,
        context.interactive_collection,
        bevel=0.0,
    )
    hitbox["interaction"] = "view"
    hitbox["view_id"] = "board"
    hitbox["label"] = "View chessboard"
    hitbox["browser_only"] = True
    return hitbox


# =============================================================================
# SHARED ROOM BUILDER HOOKS
# =============================================================================


def add_static(context):
    """Bake the black table and complete chess set into every Cycles view."""
    root = _add_coffee_table(context)
    _append_chess_set(context, root)
    context.add_panorama_view(
        "board",
        camera_location=BOARD_VIEW_CAMERA_LOCATION,
        target=BOARD_VIEW_TARGET,
        file_name="green-room-board-panorama.png",
        website_panorama_yaw=-math.pi / 2.0,
    )


def add_interactive(context):
    """Export only an invisible click target; no visible GLB furniture or light."""
    _add_table_click_target(context)
