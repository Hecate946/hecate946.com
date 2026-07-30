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
from typing import Callable

import bpy
from mathutils import Vector


ROOM_WIDTH = 6.8
ROOM_DEPTH = 10.0
ROOM_HEIGHT = 3.6
CAMERA_LOCATION = (0.0, -3.8, 1.65)

TILE_WIDTH = 0.205
TILE_HEIGHT = 0.074
TILE_GAP = 0.005
TILE_DEPTH = 0.024
TILE_BEVEL = 0.0035

FLOOR_TILE_SIZE = 0.285
FLOOR_GAP = 0.005
FLOOR_TILE_DEPTH = 0.036

POINT_LIGHT_POWER = 650.0
POINT_LIGHT_LOCATION = (0.0, -0.8, 3.0)


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
    add_box: Callable
    material: Callable
    linear_hex: Callable


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


def spans(total, length, gap, offset=0.0):
    """Return clipped spans with proper half-tiles at staggered wall edges."""
    result = []
    step = length + gap

    # One module before the boundary means an offset row clips into a true
    # half-tile instead of exposing a vertical strip of grout in the corner.
    cursor = -total / 2 + offset - step
    while cursor < total / 2:
        lower = max(-total / 2, cursor)
        upper = min(total / 2, cursor + length)
        clipped_width = upper - lower
        if clipped_width > max(length * 0.08, 0.012):
            result.append(((lower + upper) / 2, clipped_width))
        cursor += step
    return result


def aim(obj, target) -> None:
    obj.rotation_euler = (
        Vector(target) - obj.location
    ).to_track_quat("-Z", "Y").to_euler()


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
    background.inputs["Color"].default_value = (0.05, 0.05, 0.05, 1.0)
    background.inputs["Strength"].default_value = 1.0


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

    blend_file = output_directory / f"{definition.slug}-room.blend"
    panorama_file = output_directory / f"{definition.slug}-room-panorama.png"
    interactive_file = output_directory / f"{definition.slug}-room-interactive.glb"

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
        "Back grout",
        (0, ROOM_DEPTH / 2 + 0.02, ROOM_HEIGHT / 2),
        (ROOM_WIDTH, 0.06, ROOM_HEIGHT),
        grout_mat,
        static_collection,
    )
    add_box(
        "Front grout",
        (0, -ROOM_DEPTH / 2 - 0.02, ROOM_HEIGHT / 2),
        (ROOM_WIDTH, 0.06, ROOM_HEIGHT),
        grout_mat,
        static_collection,
    )
    add_box(
        "Left grout",
        (-ROOM_WIDTH / 2 - 0.02, 0, ROOM_HEIGHT / 2),
        (0.06, ROOM_DEPTH, ROOM_HEIGHT),
        grout_mat,
        static_collection,
    )
    add_box(
        "Right grout",
        (ROOM_WIDTH / 2 + 0.02, 0, ROOM_HEIGHT / 2),
        (0.06, ROOM_DEPTH, ROOM_HEIGHT),
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

    wall_boxes = []
    row_step = TILE_HEIGHT + TILE_GAP
    row_count = math.ceil(ROOM_HEIGHT / row_step)

    for row in range(row_count):
        z_lower = row * row_step + TILE_GAP / 2
        z_upper = min(ROOM_HEIGHT, z_lower + TILE_HEIGHT)
        tile_height = z_upper - z_lower
        if tile_height <= TILE_HEIGHT * 0.20:
            continue

        z = (z_lower + z_upper) / 2
        stagger = (TILE_WIDTH + TILE_GAP) / 2 if row % 2 else 0.0

        for x, width in spans(ROOM_WIDTH, TILE_WIDTH, TILE_GAP, stagger):
            wall_boxes.append(
                (
                    (x, ROOM_DEPTH / 2 - TILE_DEPTH / 2, z),
                    (width, TILE_DEPTH, tile_height),
                    0,
                )
            )
            wall_boxes.append(
                (
                    (x, -ROOM_DEPTH / 2 + TILE_DEPTH / 2, z),
                    (width, TILE_DEPTH, tile_height),
                    0,
                )
            )

        for y, width in spans(ROOM_DEPTH, TILE_WIDTH, TILE_GAP, stagger):
            wall_boxes.append(
                (
                    (-ROOM_WIDTH / 2 + TILE_DEPTH / 2, y, z),
                    (TILE_DEPTH, width, tile_height),
                    0,
                )
            )
            wall_boxes.append(
                (
                    (ROOM_WIDTH / 2 - TILE_DEPTH / 2, y, z),
                    (TILE_DEPTH, width, tile_height),
                    0,
                )
            )

    mesh_from_boxes(
        "Glazed wall tiles",
        wall_boxes,
        [wall_mat],
        static_collection,
        bevel=TILE_BEVEL,
    )

    floor_boxes = []
    xs = spans(ROOM_WIDTH, FLOOR_TILE_SIZE, FLOOR_GAP)
    ys = spans(ROOM_DEPTH, FLOOR_TILE_SIZE, FLOOR_GAP)
    for ix, (x, width) in enumerate(xs):
        for iy, (y, depth) in enumerate(ys):
            floor_boxes.append(
                (
                    (x, y, FLOOR_TILE_DEPTH / 2),
                    (width, depth, FLOOR_TILE_DEPTH),
                    (ix + iy) % 2,
                )
            )

    mesh_from_boxes(
        "Alternating marble floor",
        floor_boxes,
        [colored_floor, white_floor],
        static_collection,
        bevel=0.001,
    )

    light_data = bpy.data.lights.new("Room_Default_Point", type="POINT")
    light_data.energy = POINT_LIGHT_POWER
    light_data.shadow_soft_size = 0.25
    light = bpy.data.objects.new("Room_Default_Point", light_data)
    interactive_collection.objects.link(light)
    light.location = POINT_LIGHT_LOCATION

    interaction_origin = bpy.data.objects.new("Interaction_Origin", None)
    interactive_collection.objects.link(interaction_origin)
    interaction_origin.location = CAMERA_LOCATION

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
        add_box=add_box,
        material=material,
        linear_hex=linear_hex,
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

    aim(
        camera,
        (
            CAMERA_LOCATION[0],
            CAMERA_LOCATION[1] + 1.0,
            CAMERA_LOCATION[2],
        ),
    )

    bpy.ops.wm.save_as_mainfile(filepath=str(blend_file))

    if settings.auto_render:
        bpy.ops.render.render(write_still=True)
    else:
        print(f"Skipped panorama render for {definition.slug}.")

    export_interactive_collection(scene, interactive_collection, interactive_file)
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_file))

    print(f"Built {definition.title}")
    print(f"  Blend:       {blend_file}")
    print(f"  Panorama:    {panorama_file}")
    print(f"  Interactive: {interactive_file}")
