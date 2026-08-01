"""Green-room-only Blender objects.

The shared room builder imports this file and calls ``add_static`` and
``add_interactive``. The coffee table is created inside the existing
``INTERACTIVE_EXPORT`` collection, so it:

- remains out of the baked Cycles panorama to avoid a duplicate overlay,
- is exported inside ``green-room-interactive.glb``, and
- stays aligned with the room's existing Blender/Three.js coordinate system.

Other reusable objects should live once beneath ``blender/assets`` and be
placed here with ``context.place_static_asset`` or
``context.place_interactive_asset`` rather than copied into this file.

The table is deliberately *not* named with the ``Grab_`` prefix, so the current
website drag handler will not let visitors move the entire table. It carries
focus and chessboard anchor nodes for the later click-to-approach interaction.
"""

from __future__ import annotations

import math
from typing import Iterable, Sequence

import bpy
from mathutils import Vector


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

# Room-local placement. The front edge faces the panorama camera at negative Y.
TABLE_LOCATION = (0.0, 0.0, 0.0)

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
    collection = context.interactive_collection
    material = _create_matte_black_material()

    root = bpy.data.objects.new("Focus_GreenCoffeeTable", None)
    collection.objects.link(root)
    root.location = TABLE_LOCATION
    root.empty_display_type = "CUBE"
    root.empty_display_size = 0.22

    # glTF extras make the future interaction discoverable without hard-coding
    # the dimensions or Blender coordinates in the Svelte component.
    root["asset_id"] = "green-coffee-table"
    root["interaction"] = "focus"
    root["draggable"] = False
    root["focus_anchor"] = "GreenCoffeeTable_ApproachAnchor"
    root["focus_target"] = "GreenCoffeeTable_FocusTarget"
    root["board_anchor"] = "GreenCoffeeTable_ChessboardAnchor"

    table = _create_table_mesh(collection, material)
    table.parent = root

    chessboard_anchor = _create_empty(
        "GreenCoffeeTable_ChessboardAnchor",
        (0.0, 0.0, TABLE_HEIGHT + 0.0015),
        collection,
        root,
        display_type="CUBE",
        display_size=CHESSBOARD_SIZE / 2.0,
    )
    chessboard_anchor["board_size_m"] = CHESSBOARD_SIZE
    chessboard_anchor["table_margin_m"] = (TABLE_WIDTH - CHESSBOARD_SIZE) / 2.0

    focus_target_location = (0.0, 0.0, TABLE_HEIGHT + 0.085)
    _create_empty(
        "GreenCoffeeTable_FocusTarget",
        focus_target_location,
        collection,
        root,
        display_type="SPHERE",
        display_size=0.055,
    )

    approach = _create_empty(
        "GreenCoffeeTable_ApproachAnchor",
        (0.0, -1.22, 1.18),
        collection,
        root,
        display_type="ARROWS",
        display_size=0.16,
    )
    _aim_local(approach, focus_target_location)
    approach["recommended_fov_degrees"] = 44.0

    return root


# =============================================================================
# SHARED ROOM BUILDER HOOKS
# =============================================================================


def add_static(context):
    """No green-room-only static geometry is needed yet."""
    del context


def add_interactive(context):
    """Temporarily disable the green-room table while lighting is tuned."""
    del context
