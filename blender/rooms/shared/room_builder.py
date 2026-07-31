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


ROOM_BUILDER_VERSION = "2026-07-30-v47-tubular-gold-handle"

ROOM_WIDTH = 3.99
ROOM_DEPTH = 5.70
ROOM_HEIGHT = 3.1
ENTRY_CLEARANCE = 1.95
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

DOOR_WIDTH = 0.88
DOOR_HEIGHT = 2.28
DOOR_DEPTH = 0.055
DOOR_FRAME_WIDTH = 0.095
DOOR_FRAME_DEPTH = 0.07

PENDANT_SOURCE_RIM_HEIGHT = 2.48
PENDANT_RIM_HEIGHT = 2.06
PENDANT_FIXTURE_SCALE = 0.50
PENDANT_LIGHT_POWER = 190.0
PENDANT_LIGHT_SIZE = 1.85
PENDANT_LIGHT_COLOR = (1.0, 0.84, 0.72)
WORLD_LIGHT_STRENGTH = 0.01
PENDANT_OFFSET_Y = ROOM_DEPTH / 3


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


def wood_material(name, dark, light, roughness=0.30, coat=0.18):
    """Create subtle, vertically grained black-stained wood."""
    mat = material(name, dark, roughness=roughness, coat=coat)
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    bsdf = nodes.get("Principled BSDF")

    texture_coordinates = nodes.new("ShaderNodeTexCoord")
    mapping = nodes.new("ShaderNodeMapping")
    mapping.inputs["Scale"].default_value = (7.0, 2.0, 0.65)

    noise = nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 3.5
    noise.inputs["Detail"].default_value = 5.0
    noise.inputs["Roughness"].default_value = 0.68
    noise.inputs["Distortion"].default_value = 0.18

    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.24
    ramp.color_ramp.elements[0].color = dark
    ramp.color_ramp.elements[1].position = 0.78
    ramp.color_ramp.elements[1].color = light

    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.13
    bump.inputs["Distance"].default_value = 0.025

    links.new(texture_coordinates.outputs["Generated"], mapping.inputs["Vector"])
    links.new(mapping.outputs["Vector"], noise.inputs["Vector"])
    links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(noise.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


def chrome_material(name):
    """Create a realistic brushed blackened-steel finish for the pendant parts."""
    mat = material(
        name,
        linear_hex("#2C3032"),
        roughness=0.085,
        coat=0.22,
        metallic=1.0,
    )
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    bsdf = nodes.get("Principled BSDF")
    set_socket(bsdf, "Anisotropic", 0.92)
    set_socket(bsdf, "Anisotropic Rotation", 0.14)

    texture_coordinates = nodes.new("ShaderNodeTexCoord")
    mapping = nodes.new("ShaderNodeMapping")
    mapping.inputs["Scale"].default_value = (1.0, 56.0, 1.0)

    wave = nodes.new("ShaderNodeTexWave")
    wave.wave_type = "BANDS"
    wave.bands_direction = "Y"
    wave.inputs["Scale"].default_value = 215.0
    wave.inputs["Distortion"].default_value = 0.20
    wave.inputs["Detail"].default_value = 1.0
    wave.inputs["Detail Scale"].default_value = 2.0

    noise = nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 10.0
    noise.inputs["Detail"].default_value = 4.0
    noise.inputs["Roughness"].default_value = 0.28

    multiply = nodes.new("ShaderNodeMixRGB")
    multiply.blend_type = "MULTIPLY"
    multiply.inputs["Fac"].default_value = 0.12

    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.0026
    bump.inputs["Distance"].default_value = 0.00075

    links.new(texture_coordinates.outputs["Object"], mapping.inputs["Vector"])
    links.new(mapping.outputs["Vector"], wave.inputs["Vector"])
    links.new(mapping.outputs["Vector"], noise.inputs["Vector"])
    links.new(wave.outputs["Color"], multiply.inputs[1])
    links.new(noise.outputs["Color"], multiply.inputs[2])
    links.new(multiply.outputs["Color"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


def gold_material(name):
    """Create a realistic brushed-polished gold finish for the door hardware."""
    mat = material(
        name,
        linear_hex("#C9A13A"),
        roughness=0.10,
        coat=0.18,
        metallic=1.0,
    )
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    bsdf = nodes.get("Principled BSDF")
    set_socket(bsdf, "Anisotropic", 0.55)
    set_socket(bsdf, "Anisotropic Rotation", 0.08)

    noise = nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 55.0
    noise.inputs["Detail"].default_value = 3.0
    noise.inputs["Roughness"].default_value = 0.30

    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.30
    ramp.color_ramp.elements[0].color = linear_hex("#8D6A15")
    ramp.color_ramp.elements[1].position = 0.78
    ramp.color_ramp.elements[1].color = linear_hex("#E2C15E")

    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.0015
    bump.inputs["Distance"].default_value = 0.0010

    links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(noise.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


def diffuser_material(name):
    """Soft white glass-like diffuser with a restrained visible glow."""
    glow = linear_hex("#F3E6D3")
    mat = material(name, glow, roughness=0.62, coat=0.02)
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    set_socket(bsdf, ("Emission Color", "Emission"), glow)
    set_socket(bsdf, "Emission Strength", 0.002)
    return mat


def image_marble_material(name, image_path, *, roughness=0.48, coat=0.06, bump_strength=0.035):
    """Create a repeating image-based marble material from the provided texture."""
    if not Path(image_path).exists():
        raise FileNotFoundError(f"Missing marble texture: {image_path}")

    mat = material(name, linear_hex("#8A8A8A"), roughness=roughness, coat=coat)
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    bsdf = nodes.get("Principled BSDF")

    texture_coordinates = nodes.new("ShaderNodeTexCoord")
    mapping = nodes.new("ShaderNodeMapping")
    mapping.inputs["Scale"].default_value = (
        1.0 / FLOOR_TILE_SIZE,
        1.0 / FLOOR_TILE_SIZE,
        1.0,
    )

    image_texture = nodes.new("ShaderNodeTexImage")
    image_texture.image = bpy.data.images.load(str(image_path), check_existing=True)
    image_texture.extension = "REPEAT"
    image_texture.interpolation = "Linear"

    luminance = nodes.new("ShaderNodeRGBToBW")
    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = bump_strength
    bump.inputs["Distance"].default_value = 0.02

    links.new(texture_coordinates.outputs["Object"], mapping.inputs["Vector"])
    links.new(mapping.outputs["Vector"], image_texture.inputs["Vector"])
    links.new(image_texture.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(image_texture.outputs["Color"], luminance.inputs["Color"])
    links.new(luminance.outputs["Val"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


def checker_floor_material(
    name,
    image_path,
    dark_tile_hex,
    *,
    roughness=0.44,
    coat=0.05,
    bump_strength=0.024,
):
    """Create a repeating 2x2 checker texture whose dark tiles match the wall color."""
    if not Path(image_path).exists():
        raise FileNotFoundError(f"Missing checker texture: {image_path}")

    mat = material(name, linear_hex(dark_tile_hex), roughness=roughness, coat=coat)
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    bsdf = nodes.get("Principled BSDF")

    texture_coordinates = nodes.new("ShaderNodeTexCoord")
    mapping = nodes.new("ShaderNodeMapping")
    mapping.inputs["Scale"].default_value = (
        1.0 / (FLOOR_TILE_SIZE * 2.0),
        1.0 / (FLOOR_TILE_SIZE * 2.0),
        1.0,
    )

    image_texture = nodes.new("ShaderNodeTexImage")
    image_texture.image = bpy.data.images.load(str(image_path), check_existing=True)
    image_texture.extension = "REPEAT"
    image_texture.interpolation = "Linear"

    luminance = nodes.new("ShaderNodeRGBToBW")

    # Separate the bright white tiles from the dark tiles using the full checker
    # reference image as a mask, then recolor the dark half to match the wall.
    tile_mask = nodes.new("ShaderNodeValToRGB")
    tile_mask.color_ramp.elements[0].position = 0.36
    tile_mask.color_ramp.elements[0].color = (0.0, 0.0, 0.0, 1.0)
    tile_mask.color_ramp.elements[1].position = 0.56
    tile_mask.color_ramp.elements[1].color = (1.0, 1.0, 1.0, 1.0)

    dark_variation = nodes.new("ShaderNodeValToRGB")
    dark_variation.color_ramp.elements[0].position = 0.0
    dark_variation.color_ramp.elements[0].color = linear_hex(mix_hex(dark_tile_hex, target="#000000", amount=0.18))
    dark_variation.color_ramp.elements[1].position = 1.0
    dark_variation.color_ramp.elements[1].color = linear_hex(mix_hex(dark_tile_hex, target="#FFFFFF", amount=0.08))

    mix_color = nodes.new("ShaderNodeMixRGB")
    mix_color.inputs["Fac"].default_value = 0.0

    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = bump_strength
    bump.inputs["Distance"].default_value = 0.010

    links.new(texture_coordinates.outputs["Object"], mapping.inputs["Vector"])
    links.new(mapping.outputs["Vector"], image_texture.inputs["Vector"])
    links.new(image_texture.outputs["Color"], luminance.inputs["Color"])
    links.new(luminance.outputs["Val"], tile_mask.inputs["Fac"])
    links.new(luminance.outputs["Val"], dark_variation.inputs["Fac"])
    links.new(tile_mask.outputs["Color"], mix_color.inputs["Fac"])
    links.new(dark_variation.outputs["Color"], mix_color.inputs[1])
    links.new(image_texture.outputs["Color"], mix_color.inputs[2])
    links.new(mix_color.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(luminance.outputs["Val"], bump.inputs["Height"])
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


def add_cylinder(
    name,
    center,
    radius,
    depth,
    mat,
    collection,
    rotation=(0.0, 0.0, 0.0),
    bevel=0.0,
):
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=48,
        radius=radius,
        depth=depth,
        location=center,
        rotation=rotation,
    )
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(mat)

    for polygon in obj.data.polygons:
        polygon.use_smooth = True

    for old_collection in list(obj.users_collection):
        old_collection.objects.unlink(obj)
    collection.objects.link(obj)

    if bevel > 0:
        modifier = obj.modifiers.new("Rounded edges", "BEVEL")
        modifier.width = bevel
        modifier.segments = 3

    return obj


def add_revolved_profile(
    name,
    profile,
    mat,
    collection,
    *,
    segments=128,
    closed_profile=True,
):
    """Build a smooth lathed mesh from ``(radius, z)`` profile coordinates."""
    vertices = []
    faces = []
    profile_count = len(profile)

    for radius, z_value in profile:
        for segment in range(segments):
            angle = math.tau * segment / segments
            vertices.append(
                (
                    radius * math.cos(angle),
                    radius * math.sin(angle),
                    z_value,
                )
            )

    edge_count = profile_count if closed_profile else profile_count - 1
    for profile_index in range(edge_count):
        next_profile = (profile_index + 1) % profile_count
        for segment in range(segments):
            next_segment = (segment + 1) % segments
            current = profile_index * segments + segment
            current_next = profile_index * segments + next_segment
            adjacent = next_profile * segments + segment
            adjacent_next = next_profile * segments + next_segment
            faces.append((current, adjacent, adjacent_next, current_next))

    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.validate()
    mesh.update()

    obj = bpy.data.objects.new(name, mesh)
    obj.data.materials.append(mat)
    collection.objects.link(obj)
    for polygon in obj.data.polygons:
        polygon.use_smooth = True
    return obj


def add_torus(
    name,
    center,
    major_radius,
    minor_radius,
    mat,
    collection,
):
    bpy.ops.mesh.primitive_torus_add(
        major_radius=major_radius,
        minor_radius=minor_radius,
        major_segments=128,
        minor_segments=20,
        location=center,
    )
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(mat)
    for polygon in obj.data.polygons:
        polygon.use_smooth = True

    for old_collection in list(obj.users_collection):
        old_collection.objects.unlink(obj)
    collection.objects.link(obj)
    return obj


def add_center_pendant(static_collection, interactive_collection):
    """Add the single shared pendant, shifted deeper into the larger room."""
    chrome_mat = chrome_material("Pendant blackened steel")
    cord_mat = material(
        "Pendant black suspension cord",
        linear_hex("#070707"),
        roughness=0.40,
    )
    diffuser_mat = diffuser_material("Pendant warm white diffuser")

    def fixture_radius(source_radius: float) -> float:
        return source_radius * PENDANT_FIXTURE_SCALE

    def fixture_z(source_z: float) -> float:
        return PENDANT_RIM_HEIGHT + (
            source_z - PENDANT_SOURCE_RIM_HEIGHT
        ) * PENDANT_FIXTURE_SCALE

    def shift_back(obj):
        obj.location.y += PENDANT_OFFSET_Y
        return obj

    # Add a larger filled circular ceiling canopy so the suspension cord clearly
    # terminates into a proper blackened-steel ceiling fixture.
    canopy_radius = fixture_radius(0.165)
    canopy_height = fixture_radius(0.060)
    canopy_z = ROOM_HEIGHT - canopy_height / 2
    shift_back(
        add_cylinder(
            "Center_Pendant_Ceiling_Canopy",
            (0.0, 0.0, canopy_z),
            canopy_radius,
            canopy_height,
            chrome_mat,
            static_collection,
            bevel=fixture_radius(0.012),
        )
    )

    # Tighten the silhouette so the pendant reads more crisply: a clearer upper
    # shoulder, a straighter sidewall, and a more defined rolled lower rim.
    shade_profile = tuple(
        (fixture_radius(radius), fixture_z(z))
        for radius, z in (
            (0.180, 3.008),
            (0.220, 2.998),
            (0.300, 2.980),
            (0.415, 2.940),
            (0.545, 2.885),
            (0.655, 2.805),
            (0.730, 2.710),
            (0.778, 2.612),
            (0.805, 2.540),
            (0.814, 2.490),
            (0.812, 2.458),
            (0.795, 2.438),
            (0.760, 2.430),
            (0.736, 2.448),
            (0.724, 2.490),
            (0.720, 2.560),
            (0.690, 2.655),
            (0.618, 2.752),
            (0.500, 2.842),
            (0.372, 2.910),
            (0.252, 2.955),
            (0.180, 2.980),
        )
    )
    shift_back(
        add_revolved_profile(
            "Center_Pendant_Chrome_Shade",
            shade_profile,
            chrome_mat,
            static_collection,
        )
    )

    socket_profile = tuple(
        (fixture_radius(radius), fixture_z(z))
        for radius, z in (
            (0.088, 3.315),
            (0.120, 3.310),
            (0.152, 3.286),
            (0.172, 3.235),
            (0.184, 3.145),
            (0.190, 3.070),
            (0.178, 3.030),
            (0.212, 3.006),
            (0.258, 2.986),
            (0.292, 2.952),
            (0.286, 2.918),
            (0.248, 2.894),
            (0.105, 2.894),
            (0.088, 3.315),
        )
    )
    shift_back(
        add_revolved_profile(
            "Center_Pendant_Stepped_Socket",
            socket_profile,
            chrome_mat,
            static_collection,
        )
    )

    shift_back(
        add_torus(
            "Center_Pendant_Crown_Ring",
            (0.0, 0.0, fixture_z(2.955)),
            fixture_radius(0.268),
            fixture_radius(0.022),
            chrome_mat,
            static_collection,
        )
    )
    shift_back(
        add_torus(
            "Center_Pendant_Rolled_Rim",
            (0.0, 0.0, fixture_z(2.454)),
            fixture_radius(0.792),
            fixture_radius(0.019),
            chrome_mat,
            static_collection,
        )
    )

    shift_back(
        add_cylinder(
            "Center_Pendant_Diffuser",
            (0.0, 0.0, fixture_z(2.436)),
            fixture_radius(0.736),
            fixture_radius(0.018),
            diffuser_mat,
            static_collection,
            bevel=fixture_radius(0.010),
        )
    )

    cord_bottom = fixture_z(3.285)
    cord_top = ROOM_HEIGHT - fixture_radius(0.060)
    shift_back(
        add_cylinder(
            "Center_Pendant_Cord",
            (0.0, 0.0, (cord_bottom + cord_top) / 2),
            0.010,
            cord_top - cord_bottom,
            cord_mat,
            static_collection,
            bevel=0.002,
        )
    )

    light_data = bpy.data.lights.new("Center_Pendant_Light", type="AREA")
    light_data.energy = PENDANT_LIGHT_POWER
    light_data.color = PENDANT_LIGHT_COLOR
    light_data.shape = "DISK"
    light_data.size = PENDANT_LIGHT_SIZE
    if hasattr(light_data, "spread"):
        light_data.spread = math.radians(125.0)

    light = bpy.data.objects.new("Center_Pendant_Light", light_data)
    interactive_collection.objects.link(light)
    light.location = (0.0, PENDANT_OFFSET_Y, fixture_z(2.505))
    # Blender area lights emit along local -Z, so the default rotation aims
    # the warm area source downward from the bottom opening of the pendant.
    light.rotation_euler = (0.0, 0.0, 0.0)
    light["keep_for_panorama"] = True
    light["fixture"] = "center_chrome_pendant"
    return light


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
    """Hide browser-only objects while retaining the tagged pendant light.

    Hiding the entire interactive collection would remove the room's shared
    pendant light. Instead, only objects explicitly tagged ``keep_for_panorama``
    remain render-visible; everything else is temporarily hidden and restored.
    """
    previous_states = []
    for obj in collection.all_objects:
        # The shared pendant light remains active for the panorama. Any light that
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
    texture_directory = Path(__file__).resolve().parent / "textures"
    checker_texture = texture_directory / "checker-texture.png"

    wall_mat = material(
        f"{definition.title} glossy tile",
        linear_hex(definition.color_hex),
        roughness=0.18,
        coat=0.26,
    )
    grout_mat = material("White grout", linear_hex("#EEF2EC"), roughness=0.76)
    ceiling_mat = material("Plain ceiling", linear_hex("#9EA5AE"), roughness=0.54)
    checker_floor = checker_floor_material(
        f"{definition.title} full checker marble",
        checker_texture,
        definition.color_hex,
        roughness=0.78,
        coat=0.0,
        bump_strength=0.012,
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

    add_box(
        "Checker marble floor",
        (0, 0, FLOOR_TILE_DEPTH / 2),
        (ROOM_WIDTH, ROOM_DEPTH, FLOOR_TILE_DEPTH),
        checker_floor,
        static_collection,
        bevel=FLOOR_BEVEL,
    )

    # A very restrained dark baseboard helps ground the room and makes the door
    # opening feel more integrated with the walls.
    baseboard_mat = material(
        "Minimal charcoal baseboard",
        linear_hex("#111211"),
        roughness=0.46,
        coat=0.05,
    )
    baseboard_height = 0.105
    baseboard_depth = 0.012
    baseboard_z = baseboard_height / 2
    add_box(
        "Baseboard_Back",
        (0, ROOM_DEPTH / 2 - baseboard_depth / 2, baseboard_z),
        (ROOM_WIDTH, baseboard_depth, baseboard_height),
        baseboard_mat,
        static_collection,
        bevel=0.003,
    )
    add_box(
        "Baseboard_Left",
        (-ROOM_WIDTH / 2 + baseboard_depth / 2, 0, baseboard_z),
        (baseboard_depth, ROOM_DEPTH, baseboard_height),
        baseboard_mat,
        static_collection,
        bevel=0.003,
    )
    add_box(
        "Baseboard_Right",
        (ROOM_WIDTH / 2 - baseboard_depth / 2, 0, baseboard_z),
        (baseboard_depth, ROOM_DEPTH, baseboard_height),
        baseboard_mat,
        static_collection,
        bevel=0.003,
    )
    entry_segment_width = (ROOM_WIDTH - (DOOR_WIDTH + DOOR_FRAME_WIDTH * 2)) / 2
    add_box(
        "Baseboard_Entry_Left",
        (-(ROOM_WIDTH / 2) + entry_segment_width / 2, -ROOM_DEPTH / 2 + baseboard_depth / 2, baseboard_z),
        (entry_segment_width, baseboard_depth, baseboard_height),
        baseboard_mat,
        static_collection,
        bevel=0.003,
    )
    add_box(
        "Baseboard_Entry_Right",
        ((ROOM_WIDTH / 2) - entry_segment_width / 2, -ROOM_DEPTH / 2 + baseboard_depth / 2, baseboard_z),
        (entry_segment_width, baseboard_depth, baseboard_height),
        baseboard_mat,
        static_collection,
        bevel=0.003,
    )

    door_mat = wood_material(
        "Black-stained wood door",
        linear_hex("#010101"),
        linear_hex("#100C08"),
        roughness=0.44,
        coat=0.06,
    )
    brass_mat = gold_material("Warm realistic gold")

    entry_wall_y = -ROOM_DEPTH / 2
    # Keep the frame slightly proud of the tiled wall, but set the slab mostly
    # within the wall plane so the door reads normally instead of floating in
    # front of the wall.
    frame_y = entry_wall_y + DOOR_FRAME_DEPTH * 0.32
    door_y = entry_wall_y + 0.002
    door_front_y = door_y + DOOR_DEPTH / 2

    # A three-piece casing reads as a real frame instead of the previous
    # oversized black rectangle behind the door slab.
    add_box(
        "Entry_Door_Frame_Left",
        (-(DOOR_WIDTH + DOOR_FRAME_WIDTH) / 2, frame_y, DOOR_HEIGHT / 2),
        (DOOR_FRAME_WIDTH, DOOR_FRAME_DEPTH, DOOR_HEIGHT),
        door_mat,
        static_collection,
        bevel=0.012,
    )
    add_box(
        "Entry_Door_Frame_Right",
        ((DOOR_WIDTH + DOOR_FRAME_WIDTH) / 2, frame_y, DOOR_HEIGHT / 2),
        (DOOR_FRAME_WIDTH, DOOR_FRAME_DEPTH, DOOR_HEIGHT),
        door_mat,
        static_collection,
        bevel=0.012,
    )
    add_box(
        "Entry_Door_Frame_Top",
        (0, frame_y, DOOR_HEIGHT + DOOR_FRAME_WIDTH / 2),
        (DOOR_WIDTH + DOOR_FRAME_WIDTH * 2, DOOR_FRAME_DEPTH, DOOR_FRAME_WIDTH),
        door_mat,
        static_collection,
        bevel=0.012,
    )

    add_box(
        "Entry_Door",
        (0, door_y, DOOR_HEIGHT / 2),
        (DOOR_WIDTH, DOOR_DEPTH, DOOR_HEIGHT),
        door_mat,
        static_collection,
        bevel=0.018,
    )

    # Keep the slab visually simpler by removing the former raised-panel boxes.
    # The black-stained wood grain now reads cleanly across the full door face.

    handle_x = DOOR_WIDTH * 0.39
    handle_z = DOOR_HEIGHT / 2
    handle_surface_y = door_front_y + 0.012

    # Match the new reference more closely: a slightly taller rectangular gold
    # plate on the door, with a clean tubular lever all the way through.
    add_box(
        "Entry_Door_Handle_Backplate",
        (handle_x, handle_surface_y, handle_z),
        (0.082, 0.024, 0.235),
        brass_mat,
        static_collection,
        bevel=0.010,
    )
    add_cylinder(
        "Entry_Door_Handle_Rosette",
        (handle_x, handle_surface_y + 0.016, handle_z),
        0.032,
        0.018,
        brass_mat,
        static_collection,
        rotation=(math.radians(90.0), 0.0, 0.0),
        bevel=0.004,
    )
    add_cylinder(
        "Entry_Door_Handle_Neck",
        (handle_x - 0.024, handle_surface_y + 0.038, handle_z),
        0.013,
        0.054,
        brass_mat,
        static_collection,
        rotation=(0.0, math.radians(90.0), 0.0),
        bevel=0.003,
    )
    add_cylinder(
        "Entry_Door_Handle_Lever",
        (handle_x - 0.095, handle_surface_y + 0.038, handle_z),
        0.013,
        0.142,
        brass_mat,
        static_collection,
        rotation=(0.0, math.radians(90.0), 0.0),
        bevel=0.003,
    )

    add_center_pendant(static_collection, interactive_collection)

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
        # Preserve the existing RoomContext API for room-specific hooks. The
        # new floor uses one complete checker texture, so both compatibility
        # fields intentionally point to the same material.
        colored_floor_material=checker_floor,
        white_floor_material=checker_floor,
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
        # Keep the pendant light active, but prevent live GLB objects such as the
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
