"""
Green Room African Blackwood Coffee Table Generator — Blender 4.x
=================================================================

This standalone generator creates the tall, heavy square table designed for the
interactive green room. The table is intentionally modular and web-ready:

- 34 in × 34 in tabletop
- 31.5 in overall height
- exactly 12 in wider than the intended 22 in chessboard
- thick 6.25 in square legs
- tabletop edges flush with the outside faces of the legs
- substantial apron directly beneath the top
- nearly black African-blackwood appearance with subtle directional grain
- one joined table mesh and one shared material for efficient web rendering
- origin centered on the floor beneath the table
- exported helper anchors for the future chessboard/camera interaction

Run this file from Blender's Scripting workspace. By default it writes:

    ~/Desktop/projects/hecate946.com/blender/rooms/green-room/objects/coffee-table/
        coffee_table.glb
        coffee_table.blend
        coffee_table.png       (only when AUTO_RENDER is True)
        textures/

The GLB contains only the production table asset and helper empties. The preview
camera and lights remain in the .blend but are excluded from the GLB.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Iterable, Sequence

import bpy
from mathutils import Vector


SCRIPT_VERSION = "green-room-coffee-table-v1-2026-07-30"


# =============================================================================
# USER SETTINGS
# =============================================================================

INCH = 0.0254

# The tabletop is exactly twelve inches wider than a standard 22-inch board.
CHESSBOARD_SIZE_IN = 22.0
TABLE_WIDTH_IN = CHESSBOARD_SIZE_IN + 12.0
TABLE_DEPTH_IN = 34.0
TABLE_HEIGHT_IN = 31.5

TOP_THICKNESS_IN = 2.75
LEG_THICKNESS_IN = 6.25
APRON_HEIGHT_IN = 6.0
APRON_THICKNESS_IN = 2.0
APRON_FACE_INSET_IN = 0.45

EDGE_BEVEL_IN = 0.20
TOP_EDGE_BEVEL_IN = 0.24

TABLE_WIDTH = TABLE_WIDTH_IN * INCH
TABLE_DEPTH = TABLE_DEPTH_IN * INCH
TABLE_HEIGHT = TABLE_HEIGHT_IN * INCH
TOP_THICKNESS = TOP_THICKNESS_IN * INCH
LEG_THICKNESS = LEG_THICKNESS_IN * INCH
APRON_HEIGHT = APRON_HEIGHT_IN * INCH
APRON_THICKNESS = APRON_THICKNESS_IN * INCH
APRON_FACE_INSET = APRON_FACE_INSET_IN * INCH
EDGE_BEVEL = EDGE_BEVEL_IN * INCH
TOP_EDGE_BEVEL = TOP_EDGE_BEVEL_IN * INCH
CHESSBOARD_SIZE = CHESSBOARD_SIZE_IN * INCH

TEXTURE_SIZE = 1024
TEXTURE_SEED = 946

OUTPUT_DIRECTORY = (
    Path.home()
    / "Desktop"
    / "projects"
    / "hecate946.com"
    / "blender"
    / "rooms"
    / "green-room"
    / "objects"
    / "coffee-table"
)

PYTHON_OUTPUT_PATH = OUTPUT_DIRECTORY / "coffee_table.py"
GLB_OUTPUT_PATH = OUTPUT_DIRECTORY / "coffee_table.glb"
PNG_OUTPUT_PATH = OUTPUT_DIRECTORY / "coffee_table.png"
BLEND_OUTPUT_PATH = OUTPUT_DIRECTORY / "coffee_table.blend"
TEXTURE_DIRECTORY = OUTPUT_DIRECTORY / "textures"

# The asset GLB and editable .blend are generated automatically.
AUTO_EXPORT_GLB = True
AUTO_SAVE_BLEND = True
AUTO_RENDER = False

# Cycles produces the best transparent product preview. Set False for Eevee.
USE_CYCLES = True
CYCLES_SAMPLES = 128
RENDER_RESOLUTION = (1400, 1400)

# This is a standalone object generator. Leave True unless intentionally adding
# the asset to an already-open Blender scene by modifying the script first.
CLEAR_EXISTING_SCENE = True


# =============================================================================
# OUTPUT / COMPATIBILITY HELPERS
# =============================================================================


def ensure_output_directories() -> None:
    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)
    TEXTURE_DIRECTORY.mkdir(parents=True, exist_ok=True)


def filter_supported_operator_kwargs(operator, kwargs: dict) -> dict:
    """Pass only properties supported by the current Blender operator."""
    try:
        supported = {
            prop.identifier
            for prop in operator.get_rna_type().properties
            if prop.identifier != "rna_type"
        }
        return {key: value for key, value in kwargs.items() if key in supported}
    except Exception:
        return kwargs


def available_render_engines(scene: bpy.types.Scene) -> set[str]:
    try:
        return {
            item.identifier
            for item in scene.bl_rna.properties["render"].fixed_type.properties[
                "engine"
            ].enum_items
        }
    except Exception:
        try:
            return {
                item.identifier
                for item in scene.render.bl_rna.properties["engine"].enum_items
            }
        except Exception:
            return {"CYCLES", "BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"}


def set_render_engine(scene: bpy.types.Scene) -> str:
    engines = available_render_engines(scene)

    if USE_CYCLES and "CYCLES" in engines:
        scene.render.engine = "CYCLES"
        scene.cycles.samples = CYCLES_SAMPLES
        scene.cycles.use_denoising = True
        try:
            scene.cycles.preview_samples = min(32, CYCLES_SAMPLES)
        except Exception:
            pass
        return "CYCLES"

    for engine in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        if engine in engines:
            scene.render.engine = engine
            return engine

    # Blender always exposes at least one engine; preserve the current one if a
    # future version renames the known identifiers.
    return scene.render.engine


# =============================================================================
# SCENE / COLLECTION HELPERS
# =============================================================================


def clear_scene() -> None:
    if not CLEAR_EXISTING_SCENE:
        return

    if bpy.context.object is not None and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")

    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)

    for collection in list(bpy.data.collections):
        bpy.data.collections.remove(collection)

    for datablocks in (
        bpy.data.meshes,
        bpy.data.curves,
        bpy.data.cameras,
        bpy.data.lights,
        bpy.data.materials,
    ):
        for datablock in list(datablocks):
            if datablock.users == 0:
                datablocks.remove(datablock)


def create_collection(name: str) -> bpy.types.Collection:
    collection = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(collection)
    return collection


def move_object_to_collection(
    obj: bpy.types.Object,
    collection: bpy.types.Collection,
) -> None:
    for existing in list(obj.users_collection):
        existing.objects.unlink(obj)
    collection.objects.link(obj)


def create_empty(
    name: str,
    location: Sequence[float],
    collection: bpy.types.Collection,
    *,
    display_type: str = "PLAIN_AXES",
    display_size: float = 0.08,
) -> bpy.types.Object:
    obj = bpy.data.objects.new(name, None)
    obj.location = location
    obj.empty_display_type = display_type
    obj.empty_display_size = display_size
    collection.objects.link(obj)
    return obj


def select_only(objects: Iterable[bpy.types.Object]) -> None:
    bpy.ops.object.select_all(action="DESELECT")
    active = None
    for obj in objects:
        if obj is None or obj.name not in bpy.context.view_layer.objects:
            continue
        obj.hide_set(False)
        obj.hide_viewport = False
        obj.select_set(True)
        active = obj
    if active is not None:
        bpy.context.view_layer.objects.active = active


# =============================================================================
# TEXTURE GENERATION
# =============================================================================


def save_generated_image(
    name: str,
    rgba_pixels,
    path: Path,
    *,
    color_space: str,
) -> bpy.types.Image:
    """Create a Blender image from a NumPy RGBA array and save it as PNG."""
    import numpy as np

    height, width, channels = rgba_pixels.shape
    if channels != 4:
        raise ValueError("Generated texture must contain four RGBA channels.")

    old = bpy.data.images.get(name)
    if old is not None:
        bpy.data.images.remove(old)

    image = bpy.data.images.new(
        name=name,
        width=width,
        height=height,
        alpha=True,
        float_buffer=False,
    )
    image.pixels.foreach_set(np.asarray(rgba_pixels, dtype=np.float32).ravel())
    image.update()

    try:
        image.colorspace_settings.name = color_space
    except Exception:
        pass

    image.filepath_raw = str(path)
    image.file_format = "PNG"
    image.save()
    image.pack()
    return image


def generate_blackwood_textures(size: int = TEXTURE_SIZE) -> tuple:
    """
    Generate subtle, directional near-black wood textures.

    The grain is deliberately restrained: the table should read as black first,
    with wood character appearing in highlights and close camera views.
    """
    import numpy as np

    rng = np.random.default_rng(TEXTURE_SEED)
    y, x = np.mgrid[0:size, 0:size].astype(np.float32)
    x /= float(size)
    y /= float(size)

    # Long fibers run in the U direction. Multiple warped frequencies avoid an
    # obviously procedural single-wave pattern.
    warp = (
        0.020 * np.sin(2.0 * math.pi * (x * 1.4 + y * 0.35))
        + 0.010 * np.sin(2.0 * math.pi * (x * 4.1 - y * 0.6))
    )
    grain = (
        0.52 * np.sin(2.0 * math.pi * (y * 21.0 + warp))
        + 0.27 * np.sin(2.0 * math.pi * (y * 51.0 + x * 0.8))
        + 0.13 * np.sin(2.0 * math.pi * (y * 113.0 - x * 1.7))
    )

    coarse_noise = rng.normal(0.0, 1.0, (size // 8 + 1, size // 8 + 1))
    coarse_noise = np.repeat(np.repeat(coarse_noise, 8, axis=0), 8, axis=1)
    coarse_noise = coarse_noise[:size, :size]
    fine_noise = rng.normal(0.0, 1.0, (size, size))

    height = 0.58 + 0.16 * grain + 0.055 * coarse_noise + 0.020 * fine_noise
    height = np.clip(height, 0.0, 1.0)

    # Very dark brown-black rather than neutral printer black. This preserves
    # visible volume under realistic lighting without looking painted gray.
    base = np.zeros((size, size, 4), dtype=np.float32)
    base[..., 0] = 0.007 + height * 0.022
    base[..., 1] = 0.006 + height * 0.016
    base[..., 2] = 0.005 + height * 0.011
    base[..., 3] = 1.0

    roughness = np.zeros((size, size, 4), dtype=np.float32)
    rough = np.clip(0.24 + (1.0 - height) * 0.17 + fine_noise * 0.012, 0.20, 0.48)
    roughness[..., :3] = rough[..., None]
    roughness[..., 3] = 1.0

    # Convert the subtle height field into a tangent-space normal texture.
    dy, dx = np.gradient(height)
    strength = 2.2
    nx = -dx * strength
    ny = -dy * strength
    nz = np.ones_like(nx)
    length = np.sqrt(nx * nx + ny * ny + nz * nz)
    nx /= length
    ny /= length
    nz /= length

    normal = np.zeros((size, size, 4), dtype=np.float32)
    normal[..., 0] = nx * 0.5 + 0.5
    normal[..., 1] = ny * 0.5 + 0.5
    normal[..., 2] = nz * 0.5 + 0.5
    normal[..., 3] = 1.0

    base_image = save_generated_image(
        "AfricanBlackwood_BaseColor",
        base,
        TEXTURE_DIRECTORY / "african_blackwood_basecolor.png",
        color_space="sRGB",
    )
    roughness_image = save_generated_image(
        "AfricanBlackwood_Roughness",
        roughness,
        TEXTURE_DIRECTORY / "african_blackwood_roughness.png",
        color_space="Non-Color",
    )
    normal_image = save_generated_image(
        "AfricanBlackwood_Normal",
        normal,
        TEXTURE_DIRECTORY / "african_blackwood_normal.png",
        color_space="Non-Color",
    )

    return base_image, roughness_image, normal_image


# =============================================================================
# MATERIALS
# =============================================================================


def principled_input(node: bpy.types.Node, *names: str):
    for name in names:
        socket = node.inputs.get(name)
        if socket is not None:
            return socket
    return None


def create_blackwood_material() -> bpy.types.Material:
    base_image, roughness_image, normal_image = generate_blackwood_textures()

    material = bpy.data.materials.new("MAT_AfricanBlackwood_BlackPolished")
    material.use_nodes = True
    material.diffuse_color = (0.012, 0.009, 0.006, 1.0)
    material.metallic = 0.0
    material.roughness = 0.30

    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()

    output = nodes.new("ShaderNodeOutputMaterial")
    output.location = (620, 40)

    principled = nodes.new("ShaderNodeBsdfPrincipled")
    principled.location = (300, 40)
    principled.label = "Black polished African blackwood"

    base_socket = principled_input(principled, "Base Color")
    if base_socket is not None:
        base_socket.default_value = (0.012, 0.009, 0.006, 1.0)

    metallic_socket = principled_input(principled, "Metallic")
    if metallic_socket is not None:
        metallic_socket.default_value = 0.0

    roughness_socket = principled_input(principled, "Roughness")
    if roughness_socket is not None:
        roughness_socket.default_value = 0.30

    ior_socket = principled_input(principled, "IOR")
    if ior_socket is not None:
        ior_socket.default_value = 1.47

    coat_socket = principled_input(principled, "Coat Weight", "Clearcoat")
    if coat_socket is not None:
        coat_socket.default_value = 0.16

    coat_roughness_socket = principled_input(
        principled,
        "Coat Roughness",
        "Clearcoat Roughness",
    )
    if coat_roughness_socket is not None:
        coat_roughness_socket.default_value = 0.20

    base_texture = nodes.new("ShaderNodeTexImage")
    base_texture.name = "AfricanBlackwood_BaseColor_Texture"
    base_texture.image = base_image
    base_texture.interpolation = "Linear"
    base_texture.location = (-520, 190)

    roughness_texture = nodes.new("ShaderNodeTexImage")
    roughness_texture.name = "AfricanBlackwood_Roughness_Texture"
    roughness_texture.image = roughness_image
    roughness_texture.interpolation = "Linear"
    roughness_texture.location = (-520, -30)

    normal_texture = nodes.new("ShaderNodeTexImage")
    normal_texture.name = "AfricanBlackwood_Normal_Texture"
    normal_texture.image = normal_image
    normal_texture.interpolation = "Linear"
    normal_texture.location = (-520, -250)

    normal_map = nodes.new("ShaderNodeNormalMap")
    normal_map.location = (-120, -230)
    normal_map.inputs["Strength"].default_value = 0.24

    if base_socket is not None:
        links.new(base_texture.outputs["Color"], base_socket)
    if roughness_socket is not None:
        links.new(roughness_texture.outputs["Color"], roughness_socket)
    normal_socket = principled_input(principled, "Normal")
    if normal_socket is not None:
        links.new(normal_texture.outputs["Color"], normal_map.inputs["Color"])
        links.new(normal_map.outputs["Normal"], normal_socket)

    links.new(principled.outputs["BSDF"], output.inputs["Surface"])

    material["wood_species"] = "African blackwood"
    material["finish"] = "black satin-polished"
    material["web_shared_material"] = True
    return material


# =============================================================================
# MESH BUILDING
# =============================================================================


def unwrap_box(obj: bpy.types.Object) -> None:
    select_only([obj])
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    try:
        kwargs = filter_supported_operator_kwargs(
            bpy.ops.uv.smart_project,
            {
                "angle_limit": math.radians(66.0),
                "island_margin": 0.018,
                "area_weight": 0.0,
                "correct_aspect": True,
                "scale_to_bounds": False,
            },
        )
        bpy.ops.uv.smart_project(**kwargs)
    except Exception:
        bpy.ops.uv.smart_project()
    bpy.ops.object.mode_set(mode="OBJECT")


def add_box(
    name: str,
    dimensions: Sequence[float],
    location: Sequence[float],
    collection: bpy.types.Collection,
    material: bpy.types.Material,
    *,
    bevel_width: float,
    bevel_segments: int = 3,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=location)
    obj = bpy.context.active_object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    move_object_to_collection(obj, collection)

    if len(obj.data.materials) == 0:
        obj.data.materials.append(material)
    else:
        obj.data.materials[0] = material

    unwrap_box(obj)

    bevel = obj.modifiers.new(name="Small softened furniture edges", type="BEVEL")
    bevel.width = min(bevel_width, min(dimensions) * 0.18)
    bevel.segments = bevel_segments
    bevel.limit_method = "ANGLE"
    bevel.angle_limit = math.radians(30.0)
    try:
        bevel.harden_normals = True
    except Exception:
        pass

    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.modifier_apply(modifier=bevel.name)

    try:
        weighted = obj.modifiers.new(name="Weighted corner normals", type="WEIGHTED_NORMAL")
        weighted.keep_sharp = True
        weighted.weight = 50
        bpy.ops.object.modifier_apply(modifier=weighted.name)
    except Exception:
        pass

    return obj


def join_meshes(
    objects: Sequence[bpy.types.Object],
    name: str,
) -> bpy.types.Object:
    if not objects:
        raise ValueError("At least one mesh object is required.")

    select_only(objects)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.object.join()
    joined = bpy.context.active_object
    joined.name = name
    joined.data.name = f"{name}_Geometry"
    return joined


def build_table(
    export_collection: bpy.types.Collection,
    material: bpy.types.Material,
) -> tuple[bpy.types.Object, bpy.types.Object, list[bpy.types.Object]]:
    root = create_empty(
        "GreenRoom_CoffeeTable",
        (0.0, 0.0, 0.0),
        export_collection,
        display_type="CUBE",
        display_size=0.16,
    )

    root["asset_type"] = "interactive_coffee_table"
    root["asset_version"] = SCRIPT_VERSION
    root["units"] = "meters"
    root["table_width_m"] = TABLE_WIDTH
    root["table_depth_m"] = TABLE_DEPTH
    root["table_height_m"] = TABLE_HEIGHT
    root["table_width_in"] = TABLE_WIDTH_IN
    root["table_depth_in"] = TABLE_DEPTH_IN
    root["table_height_in"] = TABLE_HEIGHT_IN
    root["recommended_chessboard_size_m"] = CHESSBOARD_SIZE
    root["recommended_chessboard_size_in"] = CHESSBOARD_SIZE_IN
    root["top_surface_z_m"] = TABLE_HEIGHT
    root["click_target"] = True

    leg_height = TABLE_HEIGHT - TOP_THICKNESS
    leg_center_z = leg_height * 0.5
    top_center_z = TABLE_HEIGHT - TOP_THICKNESS * 0.5

    leg_x = TABLE_WIDTH * 0.5 - LEG_THICKNESS * 0.5
    leg_y = TABLE_DEPTH * 0.5 - LEG_THICKNESS * 0.5

    parts: list[bpy.types.Object] = []

    # Thick slab with no overhang: its outside edge is exactly flush with the
    # outside faces of all four legs.
    parts.append(
        add_box(
            "CoffeeTable_Top",
            (TABLE_WIDTH, TABLE_DEPTH, TOP_THICKNESS),
            (0.0, 0.0, top_center_z),
            export_collection,
            material,
            bevel_width=TOP_EDGE_BEVEL,
            bevel_segments=4,
        )
    )

    leg_specs = (
        ("CoffeeTable_Leg_FrontLeft", -leg_x, -leg_y),
        ("CoffeeTable_Leg_FrontRight", leg_x, -leg_y),
        ("CoffeeTable_Leg_BackLeft", -leg_x, leg_y),
        ("CoffeeTable_Leg_BackRight", leg_x, leg_y),
    )

    for name, x, y in leg_specs:
        parts.append(
            add_box(
                name,
                (LEG_THICKNESS, LEG_THICKNESS, leg_height),
                (x, y, leg_center_z),
                export_collection,
                material,
                bevel_width=EDGE_BEVEL,
                bevel_segments=3,
            )
        )

    apron_center_z = leg_height - APRON_HEIGHT * 0.5
    inner_width = TABLE_WIDTH - 2.0 * LEG_THICKNESS
    inner_depth = TABLE_DEPTH - 2.0 * LEG_THICKNESS

    front_y = -TABLE_DEPTH * 0.5 + APRON_FACE_INSET + APRON_THICKNESS * 0.5
    back_y = TABLE_DEPTH * 0.5 - APRON_FACE_INSET - APRON_THICKNESS * 0.5
    left_x = -TABLE_WIDTH * 0.5 + APRON_FACE_INSET + APRON_THICKNESS * 0.5
    right_x = TABLE_WIDTH * 0.5 - APRON_FACE_INSET - APRON_THICKNESS * 0.5

    parts.extend(
        [
            add_box(
                "CoffeeTable_Apron_Front",
                (inner_width, APRON_THICKNESS, APRON_HEIGHT),
                (0.0, front_y, apron_center_z),
                export_collection,
                material,
                bevel_width=EDGE_BEVEL * 0.55,
                bevel_segments=2,
            ),
            add_box(
                "CoffeeTable_Apron_Back",
                (inner_width, APRON_THICKNESS, APRON_HEIGHT),
                (0.0, back_y, apron_center_z),
                export_collection,
                material,
                bevel_width=EDGE_BEVEL * 0.55,
                bevel_segments=2,
            ),
            add_box(
                "CoffeeTable_Apron_Left",
                (APRON_THICKNESS, inner_depth, APRON_HEIGHT),
                (left_x, 0.0, apron_center_z),
                export_collection,
                material,
                bevel_width=EDGE_BEVEL * 0.55,
                bevel_segments=2,
            ),
            add_box(
                "CoffeeTable_Apron_Right",
                (APRON_THICKNESS, inner_depth, APRON_HEIGHT),
                (right_x, 0.0, apron_center_z),
                export_collection,
                material,
                bevel_width=EDGE_BEVEL * 0.55,
                bevel_segments=2,
            ),
        ]
    )

    table_mesh = join_meshes(parts, "CoffeeTable_Mesh")
    table_mesh.parent = root
    table_mesh["click_target"] = True
    table_mesh["interaction_group"] = "green-room-table"
    table_mesh["material_description"] = "black polished African blackwood"

    # Helper nodes are exported as glTF nodes. They make the later chessboard
    # placement and click-to-approach behavior deterministic in Three.js.
    board_anchor = create_empty(
        "ChessBoardAnchor",
        (0.0, 0.0, TABLE_HEIGHT + 0.003),
        export_collection,
        display_type="CUBE",
        display_size=CHESSBOARD_SIZE * 0.5,
    )
    board_anchor.parent = root
    board_anchor["anchor_type"] = "chessboard_center"
    board_anchor["board_size_m"] = CHESSBOARD_SIZE

    focus_target = create_empty(
        "ChessFocusTarget",
        (0.0, 0.0, TABLE_HEIGHT + 0.07),
        export_collection,
        display_type="SPHERE",
        display_size=0.055,
    )
    focus_target.parent = root
    focus_target["anchor_type"] = "camera_look_target"

    approach_anchor = create_empty(
        "ChessApproachAnchor",
        (0.0, -TABLE_DEPTH * 0.5 - 0.88, TABLE_HEIGHT + 0.54),
        export_collection,
        display_type="CONE",
        display_size=0.09,
    )
    approach_anchor.parent = root
    approach_anchor["anchor_type"] = "suggested_camera_position"
    approach_anchor["look_target_node"] = "ChessFocusTarget"

    return root, table_mesh, [board_anchor, focus_target, approach_anchor]


# =============================================================================
# PREVIEW RIG
# =============================================================================


def aim_object(obj: bpy.types.Object, target: Sequence[float]) -> None:
    direction = Vector(target) - obj.location
    if direction.length == 0.0:
        return
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def create_preview_rig(
    preview_collection: bpy.types.Collection,
) -> bpy.types.Camera:
    scene = bpy.context.scene

    camera_data = bpy.data.cameras.new("CoffeeTable_PreviewCamera_Data")
    camera = bpy.data.objects.new("CoffeeTable_PreviewCamera", camera_data)
    preview_collection.objects.link(camera)
    camera.location = (0.0, -1.88, 1.55)
    camera.data.lens = 55.0
    camera.data.sensor_width = 36.0
    camera.data.dof.use_dof = False
    aim_object(camera, (0.0, 0.0, TABLE_HEIGHT * 0.62))
    scene.camera = camera

    def area_light(
        name: str,
        location: Sequence[float],
        target: Sequence[float],
        energy: float,
        size: float,
        color: Sequence[float],
    ) -> bpy.types.Object:
        data = bpy.data.lights.new(name=f"{name}_Data", type="AREA")
        data.energy = energy
        data.shape = "DISK"
        data.size = size
        data.color = color
        obj = bpy.data.objects.new(name, data)
        obj.location = location
        preview_collection.objects.link(obj)
        aim_object(obj, target)
        return obj

    target = (0.0, 0.0, TABLE_HEIGHT * 0.66)
    area_light(
        "Preview_Key",
        (-1.20, -1.25, 2.10),
        target,
        920.0,
        1.25,
        (1.0, 0.91, 0.82),
    )
    area_light(
        "Preview_Fill",
        (1.15, -0.75, 1.35),
        target,
        520.0,
        1.05,
        (0.78, 0.86, 1.0),
    )
    area_light(
        "Preview_Rim",
        (0.25, 1.35, 1.70),
        target,
        760.0,
        0.85,
        (1.0, 0.95, 0.88),
    )

    return camera


# =============================================================================
# SCENE CONFIGURATION / EXPORT
# =============================================================================


def configure_scene(scene: bpy.types.Scene) -> str:
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.length_unit = "METERS"
    scene.unit_settings.scale_length = 1.0

    selected_engine = set_render_engine(scene)

    scene.render.resolution_x = RENDER_RESOLUTION[0]
    scene.render.resolution_y = RENDER_RESOLUTION[1]
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = True
    scene.render.filepath = str(PNG_OUTPUT_PATH)

    try:
        scene.render.image_settings.color_depth = "8"
    except Exception:
        pass

    # Use whichever modern display transform is exposed by this Blender build.
    try:
        scene.view_settings.look = "AgX - Medium High Contrast"
    except Exception:
        try:
            scene.view_settings.look = "Medium High Contrast"
        except Exception:
            pass

    scene.view_settings.exposure = 0.45

    world = bpy.data.worlds.get("World") or bpy.data.worlds.new("World")
    scene.world = world
    world.use_nodes = True
    background = world.node_tree.nodes.get("Background")
    if background is not None:
        background.inputs["Color"].default_value = (0.055, 0.050, 0.045, 1.0)
        background.inputs["Strength"].default_value = 0.20

    return selected_engine


def all_collection_objects_recursive(
    collection: bpy.types.Collection,
) -> list[bpy.types.Object]:
    objects = list(collection.objects)
    for child in collection.children:
        objects.extend(all_collection_objects_recursive(child))
    return objects


def export_glb(export_collection: bpy.types.Collection) -> Path:
    ensure_output_directories()
    export_objects = all_collection_objects_recursive(export_collection)
    select_only(export_objects)

    options = {
        "filepath": str(GLB_OUTPUT_PATH),
        "export_format": "GLB",
        "use_selection": True,
        "export_apply": True,
        "export_cameras": False,
        "export_lights": False,
        "export_materials": "EXPORT",
        "export_yup": True,
        "export_extras": True,
        "export_texcoords": True,
        "export_normals": True,
        "export_tangents": True,
        "export_attributes": True,
    }
    options = filter_supported_operator_kwargs(bpy.ops.export_scene.gltf, options)

    result = bpy.ops.export_scene.gltf(**options)
    if "FINISHED" not in result:
        raise RuntimeError(f"GLB export did not finish successfully: {result}")

    print(f"GLB exported to: {GLB_OUTPUT_PATH}")
    return GLB_OUTPUT_PATH


def save_blend() -> Path:
    ensure_output_directories()
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_OUTPUT_PATH), check_existing=False)
    print(f"Blend file saved to: {BLEND_OUTPUT_PATH}")
    return BLEND_OUTPUT_PATH


def render_preview() -> Path:
    ensure_output_directories()
    bpy.context.scene.render.filepath = str(PNG_OUTPUT_PATH)
    bpy.ops.render.render(write_still=True)
    print(f"Transparent preview rendered to: {PNG_OUTPUT_PATH}")
    return PNG_OUTPUT_PATH


# =============================================================================
# MAIN
# =============================================================================


def main() -> None:
    ensure_output_directories()
    clear_scene()

    scene = bpy.context.scene
    selected_engine = configure_scene(scene)

    export_collection = create_collection("WEB_EXPORT")
    preview_collection = create_collection("PREVIEW_RIG")

    material = create_blackwood_material()
    root, table_mesh, helper_nodes = build_table(export_collection, material)
    create_preview_rig(preview_collection)

    # Useful object-level bounds and labels for later Three.js logic.
    table_mesh["bounds_width_m"] = TABLE_WIDTH
    table_mesh["bounds_depth_m"] = TABLE_DEPTH
    table_mesh["bounds_height_m"] = TABLE_HEIGHT
    table_mesh["top_surface_z_m"] = TABLE_HEIGHT
    table_mesh["object_role"] = "clickable_table"

    # Hide the non-export rig from accidental viewport selection while retaining
    # it for transparent product renders inside the .blend file.
    for obj in preview_collection.objects:
        obj.hide_select = True

    if AUTO_EXPORT_GLB:
        export_glb(export_collection)

    if AUTO_RENDER:
        render_preview()

    if AUTO_SAVE_BLEND:
        save_blend()

    select_only([root])

    print("\nGreen room coffee table created successfully.")
    print(f"Script version: {SCRIPT_VERSION}")
    print(f"Renderer: {selected_engine}")
    print(
        "Dimensions: "
        f"{TABLE_WIDTH_IN:.1f} in W × {TABLE_DEPTH_IN:.1f} in D × "
        f"{TABLE_HEIGHT_IN:.1f} in H"
    )
    print(f"Leg thickness: {LEG_THICKNESS_IN:.2f} in square")
    print(
        "Chessboard allowance: "
        f"{TABLE_WIDTH_IN - CHESSBOARD_SIZE_IN:.1f} in total extra width"
    )
    print(f"Output directory: {OUTPUT_DIRECTORY}")
    print("WEB_EXPORT contains only the production table and interaction anchors.")


if __name__ == "__main__":
    main()
