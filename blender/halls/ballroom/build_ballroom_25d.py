"""Build the Hecate946 2.5D ballroom in Blender 4.x.

Visual direction
----------------
A restrained Georgian / Neoclassical architectural maquette: warm ivory plaster,
quiet white trim, a broad matte wood floor, one closed black grand piano, and one
simple brass-and-opal chandelier. The room is deliberately sparse so it belongs
inside the simplified exterior house rather than becoming a photoreal game set.

The script authors two fixed website views in one Blender scene:

    WORLD_CAMERA__ballroom        establishing view
    WORLD_CAMERA__ballroom-piano  closer piano view

Invisible WORLD_HOTSPOT__* objects are projected into browser coordinates by
``blender/world/export_rendered_world.py``. Normally build both website views with:

    npm run ballroom:render

For a fast local preview:

    HECATE_BALLROOM_QUALITY=PREVIEW npm run ballroom:render

Outputs are written beside this file:

    ballroom-25d.blend
    ballroom-25d.png
    ballroom-piano-25d.png

This scene intentionally does not reuse the old shared panorama hall shell.
The old museum pipeline can remain independent while halls migrate to authored
2.5D views one at a time.
"""

from __future__ import annotations

import math
import os
from pathlib import Path
from typing import Iterable, Sequence

import bpy
from mathutils import Vector


# =============================================================================
# EASY SETTINGS
# =============================================================================

SCRIPT_VERSION = "ballroom-25d-v1-2026-08-07"
SCRIPT_DIR = Path(__file__).resolve().parent
BLEND_PATH = SCRIPT_DIR / "ballroom-25d.blend"
ESTABLISHING_RENDER = SCRIPT_DIR / "ballroom-25d.png"
PIANO_RENDER = SCRIPT_DIR / "ballroom-piano-25d.png"

def env_flag(name: str, default: bool) -> bool:
    fallback = "1" if default else "0"
    return os.environ.get(name, fallback).strip().lower() not in {"0", "false", "no"}


QUALITY = str(
    globals().get("QUALITY", os.environ.get("HECATE_BALLROOM_QUALITY", "WEB"))
).strip().upper()
AUTO_RENDER = bool(globals().get("AUTO_RENDER", env_flag("HECATE_BALLROOM_RENDER", True)))
USE_GPU = bool(globals().get("USE_GPU", env_flag("HECATE_BALLROOM_GPU", True)))

QUALITY_PRESETS = {
    "PREVIEW": {"width": 960, "height": 640, "samples": 24},
    "WEB": {"width": 1800, "height": 1200, "samples": 64},
    "FINAL": {"width": 2700, "height": 1800, "samples": 128},
}

if QUALITY not in QUALITY_PRESETS:
    raise ValueError(
        "HECATE_BALLROOM_QUALITY must be PREVIEW, WEB, or FINAL "
        f"(received {QUALITY!r})."
    )

ROOM_WIDTH = 14.0
ROOM_DEPTH = 9.0
ROOM_HEIGHT = 5.4
WALL_THICKNESS = 0.22

PLANK_COUNT = 20


# =============================================================================
# SCENE / COLLECTION HELPERS
# =============================================================================


def clear_scene() -> None:
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)

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

    for collection in list(bpy.data.collections):
        if collection.name != "Collection" and collection.users == 0:
            bpy.data.collections.remove(collection)


def collection(name: str, parent: bpy.types.Collection | None = None) -> bpy.types.Collection:
    existing = bpy.data.collections.get(name)
    if existing is not None:
        return existing
    result = bpy.data.collections.new(name)
    (parent or bpy.context.scene.collection).children.link(result)
    return result


def move_to_collection(obj: bpy.types.Object, target: bpy.types.Collection) -> None:
    for current in list(obj.users_collection):
        current.objects.unlink(obj)
    target.objects.link(obj)


def set_input(node: bpy.types.Node, names: Sequence[str], value) -> None:
    for name in names:
        socket = node.inputs.get(name)
        if socket is not None:
            socket.default_value = value
            return


def material(
    name: str,
    color: tuple[float, float, float, float],
    *,
    roughness: float = 0.55,
    metallic: float = 0.0,
) -> bpy.types.Material:
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf is None:
        return mat
    set_input(bsdf, ("Base Color",), color)
    set_input(bsdf, ("Roughness",), roughness)
    set_input(bsdf, ("Metallic",), metallic)
    set_input(bsdf, ("Specular IOR Level", "Specular"), 0.32)
    return mat


def add_bevel(obj: bpy.types.Object, width: float, segments: int = 3) -> None:
    modifier = obj.modifiers.new("Soft architectural edges", "BEVEL")
    modifier.width = width
    modifier.segments = segments
    modifier.limit_method = "ANGLE"


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
    obj.data.materials.append(mat)
    if bevel > 0:
        add_bevel(obj, bevel)
    move_to_collection(obj, target)
    return obj


def add_cylinder(
    name: str,
    location: tuple[float, float, float],
    radius: float,
    depth: float,
    mat: bpy.types.Material,
    target: bpy.types.Collection,
    *,
    vertices: int = 32,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=vertices,
        radius=radius,
        depth=depth,
        location=location,
    )
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(mat)
    move_to_collection(obj, target)
    return obj


def add_uv_sphere(
    name: str,
    location: tuple[float, float, float],
    radius: float,
    mat: bpy.types.Material,
    target: bpy.types.Collection,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=32,
        ring_count=16,
        radius=radius,
        location=location,
    )
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(mat)
    move_to_collection(obj, target)
    return obj


def extruded_xy_polygon(
    name: str,
    points: Sequence[tuple[float, float]],
    center: tuple[float, float, float],
    depth: float,
    mat: bpy.types.Material,
    target: bpy.types.Collection,
) -> bpy.types.Object:
    """Create a simple prism from an XY outline, extruded along Z."""
    z0 = center[2] - depth / 2
    z1 = center[2] + depth / 2
    count = len(points)
    vertices = [(center[0] + x, center[1] + y, z0) for x, y in points]
    vertices += [(center[0] + x, center[1] + y, z1) for x, y in points]

    faces: list[tuple[int, ...]] = []
    faces.append(tuple(range(count - 1, -1, -1)))
    faces.append(tuple(range(count, count * 2)))
    for index in range(count):
        nxt = (index + 1) % count
        faces.append((index, nxt, count + nxt, count + index))

    mesh = bpy.data.meshes.new(f"{name}Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    target.objects.link(obj)
    obj.data.materials.append(mat)
    return obj


def extruded_arch_xz(
    name: str,
    center_x: float,
    center_y: float,
    bottom_z: float,
    width: float,
    straight_height: float,
    depth: float,
    mat: bpy.types.Material,
    target: bpy.types.Collection,
    *,
    segments: int = 24,
) -> bpy.types.Object:
    """Create an arched panel facing the camera, extruded along Y."""
    half = width / 2
    points: list[tuple[float, float]] = [(-half, 0.0), (half, 0.0), (half, straight_height)]
    for index in range(1, segments + 1):
        angle = math.pi * index / segments
        points.append((math.cos(angle) * half, straight_height + math.sin(angle) * half))

    y0 = center_y - depth / 2
    y1 = center_y + depth / 2
    count = len(points)
    vertices = [(center_x + x, y0, bottom_z + z) for x, z in points]
    vertices += [(center_x + x, y1, bottom_z + z) for x, z in points]

    faces: list[tuple[int, ...]] = [
        tuple(range(count - 1, -1, -1)),
        tuple(range(count, count * 2)),
    ]
    for index in range(count):
        nxt = (index + 1) % count
        faces.append((index, nxt, count + nxt, count + index))

    mesh = bpy.data.meshes.new(f"{name}Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    target.objects.link(obj)
    obj.data.materials.append(mat)
    return obj


def target_object(obj: bpy.types.Object, point: Iterable[float]) -> None:
    direction = Vector(point) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


# =============================================================================
# ARCHITECTURE
# =============================================================================


def add_panel_molding_back(
    x: float,
    width: float,
    lower: float,
    upper: float,
    trim_mat: bpy.types.Material,
    target: bpy.types.Collection,
) -> None:
    y = ROOM_DEPTH / 2 - WALL_THICKNESS / 2 - 0.03
    thickness = 0.075
    depth = 0.055
    add_box(
        f"Back panel L {x:+.2f}",
        (x - width / 2, y, (lower + upper) / 2),
        (thickness, depth, upper - lower),
        trim_mat,
        target,
        bevel=0.015,
    )
    add_box(
        f"Back panel R {x:+.2f}",
        (x + width / 2, y, (lower + upper) / 2),
        (thickness, depth, upper - lower),
        trim_mat,
        target,
        bevel=0.015,
    )
    add_box(
        f"Back panel B {x:+.2f}",
        (x, y, lower),
        (width, depth, thickness),
        trim_mat,
        target,
        bevel=0.015,
    )
    add_box(
        f"Back panel T {x:+.2f}",
        (x, y, upper),
        (width, depth, thickness),
        trim_mat,
        target,
        bevel=0.015,
    )


def add_side_panel_molding(
    side: int,
    y: float,
    span: float,
    lower: float,
    upper: float,
    trim_mat: bpy.types.Material,
    target: bpy.types.Collection,
) -> None:
    x = side * (ROOM_WIDTH / 2 - WALL_THICKNESS / 2 - 0.03)
    thickness = 0.075
    depth = 0.055
    add_box(
        f"Side panel near {side:+d} {y:+.2f}",
        (x, y - span / 2, (lower + upper) / 2),
        (depth, thickness, upper - lower),
        trim_mat,
        target,
        bevel=0.015,
    )
    add_box(
        f"Side panel far {side:+d} {y:+.2f}",
        (x, y + span / 2, (lower + upper) / 2),
        (depth, thickness, upper - lower),
        trim_mat,
        target,
        bevel=0.015,
    )
    add_box(
        f"Side panel lower {side:+d} {y:+.2f}",
        (x, y, lower),
        (depth, span, thickness),
        trim_mat,
        target,
        bevel=0.015,
    )
    add_box(
        f"Side panel upper {side:+d} {y:+.2f}",
        (x, y, upper),
        (depth, span, thickness),
        trim_mat,
        target,
        bevel=0.015,
    )


def build_architecture(
    background: bpy.types.Collection,
    foreground: bpy.types.Collection,
    plaster: bpy.types.Material,
    plaster_inset: bpy.types.Material,
    trim: bpy.types.Material,
    wood_a: bpy.types.Material,
    wood_b: bpy.types.Material,
    door_wood: bpy.types.Material,
    brass: bpy.types.Material,
) -> None:
    # Shell. The front wall is intentionally absent: the camera observes a composed set.
    add_box(
        "Back wall",
        (0, ROOM_DEPTH / 2 + WALL_THICKNESS / 2, ROOM_HEIGHT / 2),
        (ROOM_WIDTH, WALL_THICKNESS, ROOM_HEIGHT),
        plaster,
        background,
    )
    add_box(
        "Left wall",
        (-ROOM_WIDTH / 2 - WALL_THICKNESS / 2, 0, ROOM_HEIGHT / 2),
        (WALL_THICKNESS, ROOM_DEPTH, ROOM_HEIGHT),
        plaster,
        background,
    )
    add_box(
        "Right wall",
        (ROOM_WIDTH / 2 + WALL_THICKNESS / 2, 0, ROOM_HEIGHT / 2),
        (WALL_THICKNESS, ROOM_DEPTH, ROOM_HEIGHT),
        plaster,
        background,
    )
    add_box(
        "Ceiling",
        (0, 0, ROOM_HEIGHT + 0.10),
        (ROOM_WIDTH + WALL_THICKNESS, ROOM_DEPTH + WALL_THICKNESS, 0.20),
        trim,
        background,
    )

    # Broad floorboards: enough material variation to read as wood, not a texture demo.
    plank_width = ROOM_WIDTH / PLANK_COUNT
    for index in range(PLANK_COUNT):
        x = -ROOM_WIDTH / 2 + plank_width * (index + 0.5)
        mat = wood_a if index % 3 else wood_b
        add_box(
            f"Floor plank {index + 1:02d}",
            (x, 0, -0.025),
            (plank_width - 0.018, ROOM_DEPTH, 0.05),
            mat,
            foreground,
            bevel=0.006,
        )

    # Shared baseboard + cornice vocabulary.
    for side in (-1, 1):
        x = side * (ROOM_WIDTH / 2 - 0.045)
        add_box(
            f"Side baseboard {side:+d}",
            (x, 0, 0.21),
            (0.09, ROOM_DEPTH, 0.34),
            trim,
            background,
            bevel=0.02,
        )
        add_box(
            f"Side cornice {side:+d}",
            (x, 0, ROOM_HEIGHT - 0.18),
            (0.12, ROOM_DEPTH, 0.28),
            trim,
            background,
            bevel=0.02,
        )

    back_y = ROOM_DEPTH / 2 - 0.04
    add_box(
        "Back baseboard",
        (0, back_y, 0.21),
        (ROOM_WIDTH, 0.09, 0.34),
        trim,
        background,
        bevel=0.02,
    )
    add_box(
        "Back cornice",
        (0, back_y, ROOM_HEIGHT - 0.18),
        (ROOM_WIDTH, 0.12, 0.28),
        trim,
        background,
        bevel=0.02,
    )

    # Restrained panel rhythm around the central arched door.
    for x in (-5.05, -2.65, 2.65, 5.05):
        add_box(
            f"Back panel inset {x:+.2f}",
            (x, ROOM_DEPTH / 2 - 0.08, 2.65),
            (1.88, 0.045, 3.38),
            plaster_inset,
            background,
        )
        add_panel_molding_back(x, 1.95, 0.92, 4.34, trim, background)

    for side in (-1, 1):
        for y in (-2.35, 0.25, 2.85):
            add_side_panel_molding(side, y, 1.92, 0.92, 4.30, trim, background)

    # One familiar arched dark-wood door links the room back to the house exterior.
    door_y = ROOM_DEPTH / 2 - 0.18
    extruded_arch_xz(
        "Door frame",
        0,
        door_y + 0.035,
        0.14,
        2.95,
        2.58,
        0.10,
        trim,
        background,
    )
    extruded_arch_xz(
        "Ballroom door",
        0,
        door_y - 0.025,
        0.14,
        2.48,
        2.39,
        0.075,
        door_wood,
        background,
    )
    add_box(
        "Door center seam",
        (0, door_y - 0.07, 1.67),
        (0.035, 0.025, 3.02),
        wood_b,
        background,
    )
    for x in (-0.19, 0.19):
        add_cylinder(
            f"Door handle {x:+.2f}",
            (x, door_y - 0.13, 1.42),
            0.042,
            0.18,
            brass,
            background,
            vertices=24,
        ).rotation_euler.x = math.radians(90)


# =============================================================================
# FOCAL OBJECTS
# =============================================================================


def build_piano(
    midground: bpy.types.Collection,
    piano_black: bpy.types.Material,
    ivory: bpy.types.Material,
    dark_detail: bpy.types.Material,
) -> None:
    # Closed-lid silhouette: sculptural and immediately readable, with almost no microdetail.
    center_x = -2.85
    center_y = 0.55
    outline = [
        (-1.55, -0.92),
        (1.28, -0.92),
        (1.46, -0.46),
        (1.34, 0.08),
        (1.02, 0.62),
        (0.52, 1.10),
        (-0.18, 1.42),
        (-1.55, 1.42),
    ]
    body = extruded_xy_polygon(
        "Closed grand piano body",
        outline,
        (center_x, center_y, 1.02),
        0.20,
        piano_black,
        midground,
    )
    add_bevel(body, 0.045, 4)

    add_box(
        "Piano keyboard surround",
        (center_x - 0.08, center_y - 0.94, 0.97),
        (2.72, 0.34, 0.19),
        piano_black,
        midground,
        bevel=0.035,
    )
    add_box(
        "Piano keys",
        (center_x - 0.08, center_y - 1.115, 0.995),
        (2.36, 0.08, 0.085),
        ivory,
        midground,
        bevel=0.01,
    )
    add_box(
        "Piano key shadow",
        (center_x - 0.08, center_y - 1.16, 1.045),
        (2.36, 0.035, 0.035),
        dark_detail,
        midground,
    )

    for index, (x, y) in enumerate(
        (
            (center_x - 1.18, center_y - 0.58),
            (center_x + 1.02, center_y - 0.56),
            (center_x - 1.15, center_y + 1.02),
        ),
        start=1,
    ):
        add_cylinder(
            f"Piano leg {index}",
            (x, y, 0.50),
            0.065,
            0.88,
            piano_black,
            midground,
            vertices=24,
        )

    # One simple bench; no additional furniture is necessary.
    add_box(
        "Piano bench seat",
        (center_x - 0.10, center_y - 1.72, 0.53),
        (1.18, 0.42, 0.15),
        piano_black,
        midground,
        bevel=0.045,
    )
    for x in (center_x - 0.48, center_x + 0.28):
        add_cylinder(
            "Bench leg",
            (x, center_y - 1.72, 0.27),
            0.045,
            0.48,
            piano_black,
            midground,
            vertices=20,
        )


def build_chandelier(
    midground: bpy.types.Collection,
    brass: bpy.types.Material,
    opal: bpy.types.Material,
) -> None:
    center = (0.0, 0.45, 4.42)
    add_cylinder(
        "Chandelier stem",
        (center[0], center[1], 4.86),
        0.035,
        0.72,
        brass,
        midground,
        vertices=24,
    )
    bpy.ops.mesh.primitive_torus_add(
        major_radius=1.12,
        minor_radius=0.034,
        major_segments=64,
        minor_segments=12,
        location=center,
    )
    ring = bpy.context.object
    ring.name = "Chandelier brass ring"
    ring.data.materials.append(brass)
    move_to_collection(ring, midground)

    for index in range(8):
        angle = 2 * math.pi * index / 8
        x = center[0] + math.cos(angle) * 1.12
        y = center[1] + math.sin(angle) * 1.12
        add_cylinder(
            f"Globe drop {index + 1}",
            (x, y, 4.30),
            0.018,
            0.23,
            brass,
            midground,
            vertices=16,
        )
        add_uv_sphere(
            f"Opal globe {index + 1}",
            (x, y, 4.14),
            0.115,
            opal,
            midground,
        )


# =============================================================================
# LIGHTING / CAMERAS / INTERACTION
# =============================================================================


def add_area_light(
    name: str,
    location: tuple[float, float, float],
    target: tuple[float, float, float],
    power: float,
    size: float,
    color: tuple[float, float, float],
    lights: bpy.types.Collection,
) -> bpy.types.Object:
    data = bpy.data.lights.new(name=name, type="AREA")
    data.energy = power
    data.shape = "DISK"
    data.size = size
    data.color = color
    obj = bpy.data.objects.new(name, data)
    lights.objects.link(obj)
    obj.location = location
    target_object(obj, target)
    return obj


def build_lighting(lights: bpy.types.Collection) -> None:
    # Invisible sources shape the room; the visible chandelier remains visually simple.
    add_area_light(
        "Soft room key",
        (0.0, -1.6, 4.75),
        (0.0, 0.75, 0.8),
        920,
        5.2,
        (1.0, 0.82, 0.62),
        lights,
    )
    add_area_light(
        "Front architectural fill",
        (0.0, -6.4, 3.55),
        (0.0, 1.3, 2.1),
        620,
        6.5,
        (0.92, 0.95, 1.0),
        lights,
    )
    add_area_light(
        "Left soft fill",
        (-6.1, -0.8, 3.4),
        (-1.0, 1.0, 1.8),
        300,
        3.6,
        (0.90, 0.94, 1.0),
        lights,
    )


def make_camera(
    name: str,
    location: tuple[float, float, float],
    target: tuple[float, float, float],
    lens: float,
    view_id: str,
    cameras: bpy.types.Collection,
) -> bpy.types.Object:
    data = bpy.data.cameras.new(name)
    data.lens = lens
    data.sensor_width = 36.0
    data.dof.use_dof = False
    obj = bpy.data.objects.new(name, data)
    cameras.objects.link(obj)
    obj.location = location
    target_object(obj, target)
    obj["world_view_id"] = view_id
    return obj


def add_hotspot(
    hotspot_id: str,
    location: tuple[float, float, float],
    dimensions: tuple[float, float, float],
    interactions: bpy.types.Collection,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=location)
    obj = bpy.context.object
    obj.name = f"WORLD_HOTSPOT__{hotspot_id}"
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    move_to_collection(obj, interactions)
    obj.display_type = "WIRE"
    obj.hide_render = True
    obj["world_hotspot_id"] = hotspot_id
    return obj


def build_cameras_and_hotspots(
    cameras: bpy.types.Collection,
    interactions: bpy.types.Collection,
) -> tuple[bpy.types.Object, bpy.types.Object]:
    establishing = make_camera(
        "WORLD_CAMERA__ballroom",
        (0.0, -12.25, 2.62),
        (0.0, 0.70, 2.20),
        58.0,
        "ballroom",
        cameras,
    )
    piano = make_camera(
        "WORLD_CAMERA__ballroom-piano",
        (2.20, -6.75, 1.92),
        (-2.75, 0.52, 1.02),
        64.0,
        "ballroom-piano",
        cameras,
    )

    door_center = (0.0, ROOM_DEPTH / 2 - 0.35, 1.82)
    add_hotspot("ballroom-exit", door_center, (2.48, 0.34, 3.42), interactions)
    # Same architectural door is the natural way back from the closer authored view.
    add_hotspot("ballroom-return", door_center, (2.48, 0.30, 3.42), interactions)
    add_hotspot(
        "ballroom-piano",
        (-2.85, 0.38, 0.92),
        (3.35, 2.85, 1.55),
        interactions,
    )
    return establishing, piano


# =============================================================================
# RENDER SETTINGS
# =============================================================================


def configure_cycles_device(scene: bpy.types.Scene) -> None:
    """Use an available compute device when possible, otherwise stay on CPU."""
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
        gpu_devices = [device for device in devices if getattr(device, "type", "CPU") != "CPU"]
        if not gpu_devices:
            print("No Cycles GPU device detected; using CPU.")
            return
        for device in devices:
            device.use = device in gpu_devices
        scene.cycles.device = "GPU"
        print("Cycles GPU devices: " + ", ".join(device.name for device in gpu_devices))
    except Exception as exc:
        scene.cycles.device = "CPU"
        print(f"Cycles GPU setup warning; using CPU: {exc}")


def configure_eevee_engine(scene: bpy.types.Scene) -> str:
    """Select the Eevee engine name supported by this Blender build.

    Blender exposes the same renderer as ``BLENDER_EEVEE`` in older builds and
    ``BLENDER_EEVEE_NEXT`` in newer ones.  Assigning an unsupported enum raises
    immediately, so probe the two names instead of assuming a Blender version.
    """
    errors: list[str] = []
    for engine in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            scene.render.engine = engine
            print(f"Preview render engine: {engine}")
            return engine
        except (TypeError, ValueError) as exc:
            errors.append(f"{engine}: {exc}")

    raise RuntimeError(
        "No supported Eevee render engine is available in this Blender build. "
        + " | ".join(errors)
    )


def configure_cycles(scene: bpy.types.Scene) -> None:
    preset = QUALITY_PRESETS[QUALITY]

    # PREVIEW deliberately uses Eevee so composition changes can be reviewed in
    # seconds.  The enum changed names across Blender releases, so select it
    # dynamically. WEB/FINAL go straight to Cycles and therefore never depend on
    # an Eevee enum being present.
    if QUALITY == "PREVIEW":
        configure_eevee_engine(scene)
    else:
        try:
            scene.render.engine = "CYCLES"
            scene.cycles.samples = preset["samples"]
            scene.cycles.use_denoising = True
            scene.cycles.preview_samples = min(32, preset["samples"] )
            scene.cycles.use_adaptive_sampling = True
            scene.cycles.adaptive_threshold = 0.025 if QUALITY == "WEB" else 0.015
            configure_cycles_device(scene)
        except Exception as exc:
            print(f"Cycles setup warning; falling back to Eevee: {exc}")
            configure_eevee_engine(scene)

    scene.render.resolution_x = preset["width"]
    scene.render.resolution_y = preset["height"]
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = False

    # AgX is intentionally restrained; choose a medium look if this Blender build exposes it.
    try:
        scene.view_settings.view_transform = "AgX"
    except Exception:
        pass
    try:
        looks = {item.name for item in scene.bl_rna.properties["view_settings"].fixed_type.properties["look"].enum_items}
        if "AgX - Medium High Contrast" in looks:
            scene.view_settings.look = "AgX - Medium High Contrast"
    except Exception:
        try:
            scene.view_settings.look = "AgX - Medium High Contrast"
        except Exception:
            pass
    scene.view_settings.exposure = 0.15

    world = scene.world or bpy.data.worlds.new("Ballroom world")
    scene.world = world
    world.use_nodes = True
    background = world.node_tree.nodes.get("Background")
    if background:
        background.inputs["Color"].default_value = (0.055, 0.045, 0.034, 1.0)
        background.inputs["Strength"].default_value = 0.24


def render_view(scene: bpy.types.Scene, camera: bpy.types.Object, output: Path) -> None:
    scene.camera = camera
    scene.render.filepath = str(output)
    bpy.ops.render.render(write_still=True)
    print(f"Rendered {camera.name} -> {output}")


# =============================================================================
# BUILD
# =============================================================================


def main() -> None:
    clear_scene()
    scene = bpy.context.scene
    scene.name = "Hecate946 Ballroom 2.5D"
    scene["hecate_scene_style"] = "restrained-neoclassical-maquette"
    scene["hecate_scene_version"] = SCRIPT_VERSION
    scene["hecate_scene_thesis"] = "space / rhythm / symmetry"

    root = collection("WORLD__ballroom")
    background = collection("WORLD_BACKGROUND", root)
    midground = collection("WORLD_MIDGROUND", root)
    foreground = collection("WORLD_FOREGROUND", root)
    interactions = collection("WORLD_INTERACTION", root)
    cameras = collection("WORLD_CAMERAS", root)
    lights = collection("WORLD_LIGHTS", root)

    # Palette is intentionally low-frequency and matte.
    plaster = material("Warm ivory plaster", (0.72, 0.69, 0.63, 1.0), roughness=0.73)
    plaster_inset = material("Quiet plaster inset", (0.66, 0.63, 0.58, 1.0), roughness=0.76)
    trim = material("Soft white trim", (0.84, 0.82, 0.76, 1.0), roughness=0.66)
    wood_a = material("Warm matte oak A", (0.25, 0.16, 0.10, 1.0), roughness=0.56)
    wood_b = material("Warm matte oak B", (0.20, 0.125, 0.075, 1.0), roughness=0.60)
    door_wood = material("Dark door wood", (0.105, 0.050, 0.032, 1.0), roughness=0.52)
    piano_black = material("Piano charcoal", (0.022, 0.024, 0.025, 1.0), roughness=0.34)
    dark_detail = material("Dark detail", (0.012, 0.012, 0.013, 1.0), roughness=0.45)
    ivory = material("Key ivory", (0.78, 0.76, 0.70, 1.0), roughness=0.50)
    brass = material("Muted brass", (0.33, 0.20, 0.065, 1.0), roughness=0.35, metallic=0.72)
    opal = material("Opal glass", (0.92, 0.82, 0.64, 1.0), roughness=0.28)

    build_architecture(
        background,
        foreground,
        plaster,
        plaster_inset,
        trim,
        wood_a,
        wood_b,
        door_wood,
        brass,
    )
    build_piano(midground, piano_black, ivory, dark_detail)
    build_chandelier(midground, brass, opal)
    build_lighting(lights)
    establishing, piano_camera = build_cameras_and_hotspots(cameras, interactions)
    configure_cycles(scene)

    SCRIPT_DIR.mkdir(parents=True, exist_ok=True)
    scene.camera = establishing
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH))
    print(f"Saved ballroom scene -> {BLEND_PATH}")

    if AUTO_RENDER:
        render_view(scene, establishing, ESTABLISHING_RENDER)
        render_view(scene, piano_camera, PIANO_RENDER)
        scene.camera = establishing
        bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH))

    print("=" * 72)
    print("Hecate946 ballroom 2.5D build complete")
    print(f"Version: {SCRIPT_VERSION}")
    print(f"Quality: {QUALITY}")
    print(f"Blend:   {BLEND_PATH}")
    if AUTO_RENDER:
        print(f"View 1:  {ESTABLISHING_RENDER}")
        print(f"View 2:  {PIANO_RENDER}")
    print("=" * 72)


if __name__ == "__main__":
    main()
