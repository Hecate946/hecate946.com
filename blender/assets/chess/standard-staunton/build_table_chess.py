"""Build the temporary purple-room table + chess interactive asset.

Run through scripts/install-purple-table-chess.mjs. The script opens the supplied
Blender 2.77 Staunton scene, keeps the complete 32-piece board setup, replaces
all external texture dependencies with embedded PBR materials, imports the
existing African-blackwood coffee table GLB, and exports one self-contained
interactive GLB for the purple room.

The table dimensions come from the original project asset:
- 34 in square tabletop
- 31.5 in tabletop height
- 22 in chessboard footprint
"""

from __future__ import annotations

import argparse
import math
import shutil
import sys
from pathlib import Path
from typing import Iterable, Sequence

import bpy
from mathutils import Matrix, Vector

INCH = 0.0254
BOARD_SIZE = 22.0 * INCH
TABLE_HEIGHT = 31.5 * INCH
BOARD_CLEARANCE = 0.003
ASSET_VERSION = "purple-table-chess-v1-2026-08-01"


def parse_args() -> argparse.Namespace:
    argv = sys.argv
    argv = argv[argv.index("--") + 1 :] if "--" in argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--table-glb", required=True)
    return parser.parse_args(argv)


def filter_supported_operator_kwargs(operator, kwargs: dict) -> dict:
    try:
        supported = {
            prop.identifier
            for prop in operator.get_rna_type().properties
            if prop.identifier != "rna_type"
        }
        return {key: value for key, value in kwargs.items() if key in supported}
    except Exception:
        return kwargs


def object_number(name: str, base: str) -> int | None:
    if name == base:
        return 0
    prefix = f"{base}."
    if not name.startswith(prefix):
        return None
    suffix = name[len(prefix) :]
    return int(suffix) if suffix.isdigit() else None


def recursive_collection_objects(collection: bpy.types.Collection) -> list[bpy.types.Object]:
    objects = list(collection.objects)
    for child in collection.children:
        objects.extend(recursive_collection_objects(child))
    return objects


def main_chess_meshes() -> list[bpy.types.Object]:
    """Select the assembled board and 32 pieces, excluding layer-two examples."""
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]

    # The supplied file uses Plane for the board and Circle through Circle.031
    # for the 32 pieces. Circle.032-.037 and Plane.002 are display examples on
    # the old second layer and are intentionally excluded.
    exact: list[bpy.types.Object] = []
    for obj in meshes:
        circle_number = object_number(obj.name, "Circle")
        if obj.name == "Plane" or (circle_number is not None and circle_number <= 31):
            exact.append(obj)
    if len(exact) >= 25:
        return exact

    # Blender may rename objects while converting an old .blend. Prefer a
    # converted collection/group named "chess" when it contains a full set.
    for collection in bpy.data.collections:
        if "chess" not in collection.name.lower():
            continue
        candidates = [
            obj for obj in recursive_collection_objects(collection) if obj.type == "MESH"
        ]
        if len(candidates) >= 25:
            return candidates

    # Last-resort spatial fallback: keep the densest group around the largest
    # board-like mesh and discard isolated example pieces.
    if not meshes:
        raise RuntimeError("The supplied chess .blend contains no mesh objects.")

    def footprint(obj: bpy.types.Object) -> float:
        points = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
        xs = [point.x for point in points]
        ys = [point.y for point in points]
        return max(xs) - min(xs) + max(ys) - min(ys)

    board = max(meshes, key=footprint)
    board_points = [board.matrix_world @ Vector(corner) for corner in board.bound_box]
    min_x = min(point.x for point in board_points)
    max_x = max(point.x for point in board_points)
    min_y = min(point.y for point in board_points)
    max_y = max(point.y for point in board_points)
    pad_x = max((max_x - min_x) * 0.20, 0.01)
    pad_y = max((max_y - min_y) * 0.20, 0.01)

    selected = []
    for obj in meshes:
        center = obj.matrix_world.translation
        if min_x - pad_x <= center.x <= max_x + pad_x and min_y - pad_y <= center.y <= max_y + pad_y:
            selected.append(obj)
    if len(selected) < 20:
        raise RuntimeError(
            "Could not reliably identify the assembled chess set in the supplied .blend."
        )
    return selected


def remove_everything_except(keep: Iterable[bpy.types.Object]) -> None:
    keep_set = set(keep)
    for obj in list(bpy.data.objects):
        if obj in keep_set:
            continue
        bpy.data.objects.remove(obj, do_unlink=True)


def principled_material(
    name: str,
    color: Sequence[float],
    *,
    roughness: float,
    coat: float = 0.0,
    metallic: float = 0.0,
) -> bpy.types.Material:
    material = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    material.use_nodes = True
    material.diffuse_color = (*color[:3], 1.0)
    material.metallic = metallic
    material.roughness = roughness

    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    output.location = (320, 0)
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (0, 0)
    bsdf.inputs["Base Color"].default_value = (*color[:3], 1.0)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    if "IOR" in bsdf.inputs:
        bsdf.inputs["IOR"].default_value = 1.47
    for socket_name in ("Coat Weight", "Clearcoat"):
        if socket_name in bsdf.inputs:
            bsdf.inputs[socket_name].default_value = coat
            break
    for socket_name in ("Coat Roughness", "Clearcoat Roughness"):
        if socket_name in bsdf.inputs:
            bsdf.inputs[socket_name].default_value = max(roughness * 0.65, 0.08)
            break
    links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])
    material["embedded_pbr"] = True
    return material


def replace_chess_materials(chess_objects: Sequence[bpy.types.Object]) -> None:
    dark_piece = principled_material(
        "MAT_Chess_Dark_Piece", (0.012, 0.009, 0.007), roughness=0.22, coat=0.22
    )
    light_piece = principled_material(
        "MAT_Chess_Ivory_Piece", (0.72, 0.61, 0.43), roughness=0.25, coat=0.20
    )
    dark_square = principled_material(
        "MAT_Chess_Dark_Square", (0.025, 0.018, 0.012), roughness=0.28, coat=0.16
    )
    light_square = principled_material(
        "MAT_Chess_Light_Square", (0.62, 0.50, 0.34), roughness=0.30, coat=0.14
    )
    edge = principled_material(
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
        slots = obj.material_slots
        if not slots:
            # The original pieces normally have materials. This fallback keeps
            # converted meshes visible if a slot is lost during old-file import.
            obj.data.materials.append(dark_piece)
            continue
        for slot in slots:
            old_name = slot.material.name if slot.material else ""
            slot.material = replacement(old_name)

    # Remove orphaned image-based materials/textures so the exported GLB has no
    # references to the missing //68707_Cycles_Wood_Material files.
    for image in list(bpy.data.images):
        if image.users == 0:
            bpy.data.images.remove(image)
    for material in list(bpy.data.materials):
        if material.users == 0:
            bpy.data.materials.remove(material)


def world_bounds(objects: Sequence[bpy.types.Object]) -> tuple[Vector, Vector]:
    points = [
        obj.matrix_world @ Vector(corner)
        for obj in objects
        for corner in obj.bound_box
    ]
    if not points:
        raise RuntimeError("Cannot calculate bounds for an empty object list.")
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


def normalize_chess_set(chess_objects: Sequence[bpy.types.Object]) -> None:
    minimum, maximum = world_bounds(chess_objects)
    width = maximum.x - minimum.x
    depth = maximum.y - minimum.y
    footprint = max(width, depth)
    if footprint <= 1e-8:
        raise RuntimeError("Chess-set footprint is zero; cannot normalize it.")

    scale = BOARD_SIZE / footprint
    center_x = (minimum.x + maximum.x) * 0.5
    center_y = (minimum.y + maximum.y) * 0.5
    target_bottom_z = TABLE_HEIGHT + BOARD_CLEARANCE

    transform = (
        Matrix.Translation((0.0, 0.0, target_bottom_z))
        @ Matrix.Scale(scale, 4)
        @ Matrix.Translation((-center_x, -center_y, -minimum.z))
    )
    for obj in chess_objects:
        obj.matrix_world = transform @ obj.matrix_world
        obj["object_role"] = "chess_piece_or_board"
        obj["interaction_group"] = "purple-room-table-chess"


def import_table(table_glb: Path) -> list[bpy.types.Object]:
    before = set(bpy.data.objects)
    options = filter_supported_operator_kwargs(
        bpy.ops.import_scene.gltf,
        {"filepath": str(table_glb), "import_pack_images": True},
    )
    result = bpy.ops.import_scene.gltf(**options)
    if "FINISHED" not in result:
        raise RuntimeError(f"Could not import coffee table GLB: {result}")
    imported = [obj for obj in bpy.data.objects if obj not in before]
    if not imported:
        raise RuntimeError("Coffee table import created no Blender objects.")
    return imported


def roots(objects: Sequence[bpy.types.Object]) -> list[bpy.types.Object]:
    object_set = set(objects)
    return [obj for obj in objects if obj.parent not in object_set]


def create_combined_root(
    table_objects: Sequence[bpy.types.Object],
    chess_objects: Sequence[bpy.types.Object],
) -> bpy.types.Object:
    root = bpy.data.objects.new("PurpleRoom_TableChess", None)
    bpy.context.scene.collection.objects.link(root)
    root["asset_type"] = "interactive_table_chess"
    root["asset_version"] = ASSET_VERSION
    root["temporary_room"] = "purple"
    root["intended_room"] = "green"
    root["table_top_height_m"] = TABLE_HEIGHT
    root["chessboard_size_m"] = BOARD_SIZE
    root["click_target"] = True

    for obj in roots(table_objects):
        world = obj.matrix_world.copy()
        obj.parent = root
        obj.matrix_world = world
    for obj in roots(chess_objects):
        world = obj.matrix_world.copy()
        obj.parent = root
        obj.matrix_world = world

    focus = bpy.data.objects.new("ChessFocusTarget", None)
    bpy.context.scene.collection.objects.link(focus)
    focus.location = (0.0, 0.0, TABLE_HEIGHT + 0.08)
    focus.empty_display_type = "SPHERE"
    focus.empty_display_size = 0.045
    focus.parent = root
    focus["anchor_type"] = "camera_look_target"

    approach = bpy.data.objects.new("ChessApproachAnchor", None)
    bpy.context.scene.collection.objects.link(approach)
    approach.location = (0.0, -1.15, 1.30)
    approach.empty_display_type = "CONE"
    approach.empty_display_size = 0.08
    approach.parent = root
    approach["anchor_type"] = "suggested_camera_position"
    approach["look_target_node"] = "ChessFocusTarget"
    return root


def select_hierarchy(root: bpy.types.Object) -> list[bpy.types.Object]:
    selected: list[bpy.types.Object] = []

    def visit(obj: bpy.types.Object) -> None:
        selected.append(obj)
        for child in obj.children:
            visit(child)

    visit(root)
    bpy.ops.object.select_all(action="DESELECT")
    for obj in selected:
        obj.hide_set(False)
        obj.hide_viewport = False
        obj.select_set(True)
    bpy.context.view_layer.objects.active = root
    return selected


def export_glb(root: bpy.types.Object, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    select_hierarchy(root)
    options = {
        "filepath": str(output),
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


def save_blend(output: Path, root: bpy.types.Object) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    select_hierarchy(root)
    bpy.ops.wm.save_as_mainfile(filepath=str(output), check_existing=False)


def configure_scene() -> None:
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.length_unit = "METERS"
    scene.unit_settings.scale_length = 1.0
    scene.render.film_transparent = True
    try:
        scene.view_settings.look = "AgX - Medium High Contrast"
    except Exception:
        pass


def main() -> None:
    args = parse_args()
    repo_root = Path(args.repo_root).expanduser().resolve()
    table_glb = Path(args.table_glb).expanduser().resolve()
    if not table_glb.is_file():
        raise FileNotFoundError(f"Coffee table GLB not found: {table_glb}")

    configure_scene()
    chess_objects = main_chess_meshes()
    remove_everything_except(chess_objects)
    replace_chess_materials(chess_objects)
    normalize_chess_set(chess_objects)

    table_objects = import_table(table_glb)
    root = create_combined_root(table_objects, chess_objects)

    source_glb = repo_root / "blender" / "rooms" / "purple" / "interactive.glb"
    public_glb = repo_root / "public" / "scenes" / "rooms" / "purple" / "interactive.glb"
    blend_output = (
        repo_root
        / "blender"
        / "rooms"
        / "purple"
        / "objects"
        / "table-chess"
        / "table_chess.blend"
    )

    export_glb(root, source_glb)
    public_glb.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_glb, public_glb)
    save_blend(blend_output, root)

    print("\nPurple-room table + chess asset created successfully.")
    print(f"Table source: {table_glb}")
    print(f"Board footprint: {BOARD_SIZE:.4f} m (22 in)")
    print(f"Board bottom Z: {TABLE_HEIGHT + BOARD_CLEARANCE:.4f} m")
    print(f"Source GLB: {source_glb}")
    print(f"Public GLB: {public_glb}")
    print(f"Editable blend: {blend_output}")


if __name__ == "__main__":
    main()
