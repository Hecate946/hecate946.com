"""
Checkerboard Room V4
--------------------
Creates a dark, glossy, liminal tiled room with:
- Smaller, darker glossy brick wall tiles on all four walls
- Smaller dark-green and ivory checkerboard marble floor with stronger veining
- A warm brass chandelier in a separate CHANDELIER_EXPORT collection
- Soft volumetric haze
- A cinematic camera and Cycles render setup
- Separate WEB_EXPORT, CHANDELIER_EXPORT, and RENDER_RIG collections

Designed to work across Blender 3.6, 4.x, and 5.x where supported.
Run from Blender's Scripting workspace.
"""

import bpy
import bmesh
import math
import random
from mathutils import Matrix, Vector

# =========================================================
# USER SETTINGS
# =========================================================
SEED = 946
ROOM_WIDTH = 6.8
ROOM_DEPTH = 10.0
ROOM_HEIGHT = 3.6

WALL_TILE_WIDTH = 0.34
WALL_TILE_HEIGHT = 0.15
WALL_GAP = 0.010
WALL_TILE_DEPTH = 0.035

FLOOR_TILE_SIZE = 0.46
FLOOR_GAP = 0.008
FLOOR_TILE_DEPTH = 0.045

RENDER_WIDTH = 1600
RENDER_HEIGHT = 1000
CYCLES_SAMPLES = 96

random.seed(SEED)

# =========================================================
# CLEAN SCENE
# =========================================================
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)

for datablocks in (
    bpy.data.meshes,
    bpy.data.curves,
    bpy.data.materials,
    bpy.data.cameras,
    bpy.data.lights,
):
    for block in list(datablocks):
        if block.users == 0:
            datablocks.remove(block)

for collection in list(bpy.data.collections):
    if collection.name != "Collection":
        bpy.data.collections.remove(collection)

root_collection = bpy.context.scene.collection
for child in list(root_collection.children):
    root_collection.children.unlink(child)

web_collection = bpy.data.collections.new("WEB_EXPORT")
chandelier_collection = bpy.data.collections.new("CHANDELIER_EXPORT")
rig_collection = bpy.data.collections.new("RENDER_RIG")
root_collection.children.link(web_collection)
root_collection.children.link(chandelier_collection)
root_collection.children.link(rig_collection)

scene = bpy.context.scene

# Blender renamed Eevee's engine identifier in newer releases. Choose the
# best renderer supported by the installed Blender version instead of assuming
# BLENDER_EEVEE_NEXT exists.
selected_engine = None
for engine_name in (
    "CYCLES",
    "BLENDER_EEVEE_NEXT",
    "BLENDER_EEVEE",
    "BLENDER_WORKBENCH",
):
    try:
        scene.render.engine = engine_name
        selected_engine = engine_name
        break
    except (TypeError, ValueError):
        continue

if selected_engine is None:
    raise RuntimeError("No supported Blender render engine was found.")

if selected_engine == "CYCLES":
    try:
        scene.cycles.samples = CYCLES_SAMPLES
        scene.cycles.use_denoising = True
    except Exception:
        pass

scene.render.resolution_x = RENDER_WIDTH
scene.render.resolution_y = RENDER_HEIGHT
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.film_transparent = False
scene.render.use_file_extension = True

# Color management: AgX is available in newer Blender versions; Filmic is
# the compatible fallback for older releases.
for transform_name in ("AgX", "Filmic", "Standard"):
    try:
        scene.view_settings.view_transform = transform_name
        break
    except (TypeError, ValueError):
        continue

for look_name in (
    "AgX - Medium High Contrast",
    "Medium High Contrast",
    "Medium High Contrast Look",
    "None",
):
    try:
        scene.view_settings.look = look_name
        break
    except (TypeError, ValueError):
        continue
scene.view_settings.exposure = 0.35

# =========================================================
# HELPERS
# =========================================================
def socket(node, *names):
    for name in names:
        if name in node.inputs:
            return node.inputs[name]
    return None


def set_input(node, names, value):
    if isinstance(names, str):
        names = (names,)
    target = socket(node, *names)
    if target is not None:
        target.default_value = value


def move_to_collection(obj, collection):
    for current in list(obj.users_collection):
        current.objects.unlink(obj)
    collection.objects.link(obj)


def add_cube(name, location, dimensions, material=None, collection=web_collection, bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    obj = bpy.context.active_object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    move_to_collection(obj, collection)

    if material is not None:
        obj.data.materials.append(material)

    if bevel > 0:
        modifier = obj.modifiers.new("Soft edge", "BEVEL")
        modifier.width = bevel
        modifier.segments = 3
        modifier.limit_method = "ANGLE"

    return obj


def add_cylinder(name, location, radius, depth, material=None, collection=web_collection, vertices=32, bevel=0.0):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=location)
    obj = bpy.context.active_object
    obj.name = name
    move_to_collection(obj, collection)
    if material is not None:
        obj.data.materials.append(material)
    if bevel > 0:
        modifier = obj.modifiers.new("Soft edge", "BEVEL")
        modifier.width = bevel
        modifier.segments = 3
        modifier.limit_method = "ANGLE"
    return obj


def add_uv_sphere(name, location, radius, material=None, collection=web_collection):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=20, radius=radius, location=location)
    obj = bpy.context.active_object
    obj.name = name
    move_to_collection(obj, collection)
    if material is not None:
        obj.data.materials.append(material)
    bpy.ops.object.shade_smooth()
    return obj


def add_tube_between(name, start, end, radius, material, collection):
    start_v = Vector(start)
    end_v = Vector(end)
    midpoint = (start_v + end_v) / 2
    length = (end_v - start_v).length
    obj = add_cylinder(name, midpoint, radius, length, material, collection, vertices=20, bevel=0.006)
    obj.rotation_euler = (end_v - start_v).to_track_quat("Z", "Y").to_euler()
    return obj


def make_principled_material(name, base_color, roughness, coat=0.0, emission=None, emission_strength=0.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    output = nodes.new("ShaderNodeOutputMaterial")
    output.location = (420, 0)
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (100, 0)

    set_input(bsdf, "Base Color", base_color)
    set_input(bsdf, "Roughness", roughness)
    set_input(bsdf, ("Coat Weight", "Clearcoat"), coat)
    set_input(bsdf, ("Coat Roughness", "Clearcoat Roughness"), 0.045)
    set_input(bsdf, "IOR", 1.47)

    if emission is not None:
        set_input(bsdf, ("Emission Color", "Emission"), emission)
        set_input(bsdf, "Emission Strength", emission_strength)

    links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])
    return mat, bsdf, nodes, links


def create_green_tile_material(name, color, roughness):
    mat, bsdf, nodes, links = make_principled_material(
        name,
        color,
        roughness,
        coat=0.72,
    )

    tex = nodes.new("ShaderNodeTexNoise")
    tex.location = (-620, -150)
    tex.inputs["Scale"].default_value = 38.0
    tex.inputs["Detail"].default_value = 5.0
    tex.inputs["Roughness"].default_value = 0.62

    bump = nodes.new("ShaderNodeBump")
    bump.location = (-120, -150)
    bump.inputs["Strength"].default_value = 0.055
    bump.inputs["Distance"].default_value = 0.025

    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.location = (-390, 40)
    ramp.color_ramp.elements[0].color = tuple(max(0.0, c * 0.78) for c in color[:3]) + (1.0,)
    ramp.color_ramp.elements[1].color = tuple(min(1.0, c * 1.08) for c in color[:3]) + (1.0,)

    links.new(tex.outputs["Fac"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], socket(bsdf, "Base Color"))
    links.new(tex.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


def create_marble_material(name, dark, light, roughness=0.16):
    mat, bsdf, nodes, links = make_principled_material(
        name,
        light,
        roughness,
        coat=0.34,
    )

    texcoord = nodes.new("ShaderNodeTexCoord")
    texcoord.location = (-1050, 0)

    mapping = nodes.new("ShaderNodeMapping")
    mapping.location = (-860, 0)
    mapping.inputs["Scale"].default_value = (1.6, 7.2, 1.6)

    noise = nodes.new("ShaderNodeTexNoise")
    noise.location = (-650, 40)
    noise.inputs["Scale"].default_value = 4.6
    noise.inputs["Detail"].default_value = 12.0
    noise.inputs["Roughness"].default_value = 0.7
    noise.inputs["Distortion"].default_value = 4.2

    wave = nodes.new("ShaderNodeTexWave")
    wave.location = (-650, -180)
    wave.wave_type = "BANDS"
    wave.bands_direction = "X"
    wave.inputs["Scale"].default_value = 6.0
    wave.inputs["Distortion"].default_value = 9.0
    wave.inputs["Detail"].default_value = 6.0
    wave.inputs["Detail Scale"].default_value = 1.6

    mix_fac = nodes.new("ShaderNodeMixRGB")
    mix_fac.location = (-390, -30)
    mix_fac.blend_type = "MULTIPLY"
    mix_fac.inputs["Fac"].default_value = 0.75

    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.location = (-130, 60)
    ramp.color_ramp.elements[0].position = 0.44
    ramp.color_ramp.elements[0].color = dark
    ramp.color_ramp.elements[1].position = 0.56
    ramp.color_ramp.elements[1].color = light

    bump = nodes.new("ShaderNodeBump")
    bump.location = (80, -160)
    bump.inputs["Strength"].default_value = 0.045
    bump.inputs["Distance"].default_value = 0.018

    links.new(texcoord.outputs["Generated"], mapping.inputs["Vector"])
    links.new(mapping.outputs["Vector"], noise.inputs["Vector"])
    links.new(mapping.outputs["Vector"], wave.inputs["Vector"])
    links.new(noise.outputs["Fac"], mix_fac.inputs[1])
    links.new(wave.outputs["Color"], mix_fac.inputs[2])
    links.new(mix_fac.outputs["Color"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], socket(bsdf, "Base Color"))
    links.new(mix_fac.outputs["Color"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


def add_box_to_bmesh(bm, location, dimensions, material_index=0):
    transform = Matrix.Translation(Vector(location)) @ Matrix.Diagonal(
        (dimensions[0], dimensions[1], dimensions[2], 1.0)
    )
    result = bmesh.ops.create_cube(bm, size=1.0, matrix=transform)
    new_faces = {face for vert in result["verts"] for face in vert.link_faces}
    for face in new_faces:
        face.material_index = material_index


def finish_bmesh_object(name, bm, materials, collection, bevel_width):
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()

    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    for material in materials:
        obj.data.materials.append(material)

    bevel = obj.modifiers.new("Rounded tile edges", "BEVEL")
    bevel.width = bevel_width
    bevel.segments = 3
    bevel.limit_method = "ANGLE"

    return obj


def clipped_segments(total_length, nominal_length, gap, offset=0.0):
    """Return center/length segments clipped to [-total/2, total/2]."""
    lo = -total_length / 2
    hi = total_length / 2
    module = nominal_length + gap
    start = lo - module + offset
    result = []
    x = start
    while x < hi + module:
        seg_lo = max(lo, x + gap / 2)
        seg_hi = min(hi, x + nominal_length - gap / 2)
        if seg_hi - seg_lo > 0.07:
            result.append(((seg_lo + seg_hi) / 2, seg_hi - seg_lo))
        x += module
    return result


def aim_object(obj, target, track_axis="-Z", up_axis="Y"):
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat(track_axis, up_axis).to_euler()

# =========================================================
# MATERIALS
# =========================================================
green_colors = [
    (0.018, 0.105, 0.058, 1.0),
    (0.024, 0.135, 0.074, 1.0),
    (0.030, 0.165, 0.092, 1.0),
    (0.012, 0.082, 0.047, 1.0),
]
green_materials = [
    create_green_tile_material(f"Wall_Green_{index + 1}", color, 0.075 + index * 0.010)
    for index, color in enumerate(green_colors)
]

floor_green_materials = [
    create_marble_material(
        f"Floor_Green_Marble_{index + 1}",
        (0.008 + index * 0.004, 0.036 + index * 0.008, 0.020 + index * 0.005, 1.0),
        (0.040 + index * 0.008, 0.180 + index * 0.018, 0.105 + index * 0.012, 1.0),
        roughness=0.13 + index * 0.012,
    )
    for index in range(3)
]

floor_white_materials = [
    create_marble_material(
        f"Floor_Ivory_Marble_{index + 1}",
        (0.50 + index * 0.035, 0.52 + index * 0.035, 0.49 + index * 0.035, 1.0),
        (0.93 + index * 0.018, 0.94 + index * 0.018, 0.90 + index * 0.018, 1.0),
        roughness=0.145 + index * 0.01,
    )
    for index in range(3)
]

grout_mat, _, _, _ = make_principled_material(
    "Deep Green Grout",
    (0.012, 0.055, 0.033, 1.0),
    0.48,
)

ceiling_mat, _, _, _ = make_principled_material(
    "Warm Plaster Ceiling",
    (0.57, 0.60, 0.53, 1.0),
    0.72,
)

brass_mat, brass_bsdf, _, _ = make_principled_material(
    "Chandelier Brass",
    (0.34, 0.16, 0.045, 1.0),
    0.22,
    coat=0.22,
)
set_input(brass_bsdf, "Metallic", 0.78)

dark_brass_mat, dark_brass_bsdf, _, _ = make_principled_material(
    "Chandelier Dark Brass",
    (0.075, 0.035, 0.012, 1.0),
    0.30,
    coat=0.12,
)
set_input(dark_brass_bsdf, "Metallic", 0.70)

warm_glass_mat, _, _, _ = make_principled_material(
    "Warm Chandelier Glass",
    (1.0, 0.48, 0.12, 1.0),
    0.16,
    coat=0.42,
    emission=(1.0, 0.28, 0.055, 1.0),
    emission_strength=7.0,
)

# =========================================================
# ROOM SHELL / GROUT BACKING
# =========================================================
add_cube(
    "Floor_Substrate",
    (0, 0, -0.055),
    (ROOM_WIDTH + 0.08, ROOM_DEPTH + 0.08, 0.10),
    grout_mat,
    bevel=0.01,
)
add_cube(
    "Back_Grout",
    (0, ROOM_DEPTH / 2 + 0.018, ROOM_HEIGHT / 2),
    (ROOM_WIDTH + 0.08, 0.08, ROOM_HEIGHT + 0.08),
    grout_mat,
)
add_cube(
    "Front_Grout",
    (0, -ROOM_DEPTH / 2 - 0.018, ROOM_HEIGHT / 2),
    (ROOM_WIDTH + 0.08, 0.08, ROOM_HEIGHT + 0.08),
    grout_mat,
)
add_cube(
    "Left_Grout",
    (-ROOM_WIDTH / 2 - 0.018, 0, ROOM_HEIGHT / 2),
    (0.08, ROOM_DEPTH + 0.08, ROOM_HEIGHT + 0.08),
    grout_mat,
)
add_cube(
    "Right_Grout",
    (ROOM_WIDTH / 2 + 0.018, 0, ROOM_HEIGHT / 2),
    (0.08, ROOM_DEPTH + 0.08, ROOM_HEIGHT + 0.08),
    grout_mat,
)
add_cube(
    "Ceiling",
    (0, 0, ROOM_HEIGHT + 0.04),
    (ROOM_WIDTH + 0.1, ROOM_DEPTH + 0.1, 0.08),
    ceiling_mat,
    bevel=0.01,
)

# =========================================================
# WALL TILE GEOMETRY
# =========================================================
def build_width_wall(name, y_position, inward_sign):
    bm = bmesh.new()
    row_module = WALL_TILE_HEIGHT + WALL_GAP
    rows = math.ceil(ROOM_HEIGHT / row_module) + 1

    for row in range(rows):
        z0 = row * row_module + WALL_GAP / 2
        z1 = min(ROOM_HEIGHT, z0 + WALL_TILE_HEIGHT)
        if z1 - z0 < 0.05:
            continue
        z_center = (z0 + z1) / 2
        tile_h = z1 - z0
        offset = 0.0 if row % 2 == 0 else (WALL_TILE_WIDTH + WALL_GAP) / 2
        for x_center, tile_w in clipped_segments(ROOM_WIDTH, WALL_TILE_WIDTH, WALL_GAP, offset):
            material_index = random.choices(range(len(green_materials)), weights=(4, 6, 3, 2))[0]
            add_box_to_bmesh(
                bm,
                (x_center, y_position + inward_sign * WALL_TILE_DEPTH / 2, z_center),
                (tile_w, WALL_TILE_DEPTH, tile_h),
                material_index,
            )

    return finish_bmesh_object(name, bm, green_materials, web_collection, bevel_width=0.008)


def build_side_wall(name, x_position):
    bm = bmesh.new()
    row_module = WALL_TILE_HEIGHT + WALL_GAP
    rows = math.ceil(ROOM_HEIGHT / row_module) + 1

    for row in range(rows):
        z0 = row * row_module + WALL_GAP / 2
        z1 = min(ROOM_HEIGHT, z0 + WALL_TILE_HEIGHT)
        if z1 - z0 < 0.05:
            continue
        z_center = (z0 + z1) / 2
        tile_h = z1 - z0
        offset = 0.0 if row % 2 == 0 else (WALL_TILE_WIDTH + WALL_GAP) / 2
        for y_center, tile_w in clipped_segments(ROOM_DEPTH, WALL_TILE_WIDTH, WALL_GAP, offset):
            material_index = random.choices(range(len(green_materials)), weights=(4, 6, 3, 2))[0]
            inward = WALL_TILE_DEPTH / 2 if x_position < 0 else -WALL_TILE_DEPTH / 2
            add_box_to_bmesh(
                bm,
                (x_position + inward, y_center, z_center),
                (WALL_TILE_DEPTH, tile_w, tile_h),
                material_index,
            )

    return finish_bmesh_object(name, bm, green_materials, web_collection, bevel_width=0.008)


build_width_wall("Back_Wall_Tiles", ROOM_DEPTH / 2, -1.0)
build_width_wall("Front_Wall_Tiles", -ROOM_DEPTH / 2, 1.0)
build_side_wall("Left_Wall_Tiles", -ROOM_WIDTH / 2)
build_side_wall("Right_Wall_Tiles", ROOM_WIDTH / 2)

# =========================================================
# CHECKERBOARD MARBLE FLOOR GEOMETRY
# =========================================================
bm = bmesh.new()
all_floor_materials = floor_green_materials + floor_white_materials

x_segments = clipped_segments(ROOM_WIDTH, FLOOR_TILE_SIZE, FLOOR_GAP, 0.0)
y_segments = clipped_segments(ROOM_DEPTH, FLOOR_TILE_SIZE, FLOOR_GAP, 0.0)

for ix, (x_center, tile_x) in enumerate(x_segments):
    for iy, (y_center, tile_y) in enumerate(y_segments):
        green = (ix + iy) % 2 == 0
        variant = random.randrange(3)
        material_index = variant if green else 3 + variant
        add_box_to_bmesh(
            bm,
            (x_center, y_center, FLOOR_TILE_DEPTH / 2),
            (tile_x, tile_y, FLOOR_TILE_DEPTH),
            material_index,
        )

finish_bmesh_object(
    "Checkerboard_Marble_Floor",
    bm,
    all_floor_materials,
    web_collection,
    bevel_width=0.007,
)

# =========================================================
# WARM CHANDELIER — SEPARATE WEB COMPONENT
# =========================================================
chandelier_root = bpy.data.objects.new("Warm_Chandelier", None)
chandelier_collection.objects.link(chandelier_root)

def parent_chandelier(obj):
    obj.parent = chandelier_root
    return obj

parent_chandelier(add_cylinder("Chandelier_Canopy", (0, 0, ROOM_HEIGHT - 0.075), 0.29, 0.07, brass_mat, chandelier_collection, bevel=0.015))
parent_chandelier(add_tube_between("Chandelier_Stem", (0, 0, ROOM_HEIGHT - 0.11), (0, 0, 2.56), 0.055, dark_brass_mat, chandelier_collection))
parent_chandelier(add_uv_sphere("Chandelier_Center", (0, 0, 2.52), 0.20, brass_mat, chandelier_collection))
parent_chandelier(add_tube_between("Chandelier_Lower_Stem", (0, 0, 2.62), (0, 0, 2.30), 0.075, brass_mat, chandelier_collection))

for index in range(6):
    angle = index * math.tau / 6
    direction = Vector((math.cos(angle), math.sin(angle), 0))
    p0 = Vector((0, 0, 2.48))
    p1 = direction * 0.43 + Vector((0, 0, 2.34))
    p2 = direction * 0.82 + Vector((0, 0, 2.48))
    parent_chandelier(add_tube_between(f"Chandelier_Arm_{index + 1}_A", p0, p1, 0.035, brass_mat, chandelier_collection))
    parent_chandelier(add_tube_between(f"Chandelier_Arm_{index + 1}_B", p1, p2, 0.032, brass_mat, chandelier_collection))
    parent_chandelier(add_cylinder(f"Chandelier_Cup_{index + 1}", (p2.x, p2.y, 2.51), 0.12, 0.035, brass_mat, chandelier_collection, bevel=0.009))
    parent_chandelier(add_tube_between(f"Chandelier_Candle_{index + 1}", (p2.x, p2.y, 2.50), (p2.x, p2.y, 2.68), 0.045, dark_brass_mat, chandelier_collection))
    parent_chandelier(add_uv_sphere(f"Chandelier_Bulb_{index + 1}", (p2.x, p2.y, 2.76), 0.095, warm_glass_mat, chandelier_collection))

    bulb_data = bpy.data.lights.new(f"Chandelier_Light_{index + 1}", type="POINT")
    bulb_data.energy = 42.0
    bulb_data.color = (1.0, 0.36, 0.11)
    bulb_data.shadow_soft_size = 0.18
    bulb_obj = bpy.data.objects.new(f"Chandelier_Light_{index + 1}", bulb_data)
    rig_collection.objects.link(bulb_obj)
    bulb_obj.location = (p2.x, p2.y, 2.76)

parent_chandelier(add_uv_sphere("Chandelier_Finial", (0, 0, 2.25), 0.105, brass_mat, chandelier_collection))

# Soft ambient fills preserve the liminal green while the chandelier stays warm.
fill_data = bpy.data.lights.new("Room_Green_Fill", type="AREA")
fill_data.energy = 320.0
fill_data.shape = "DISK"
fill_data.size = 4.0
fill_data.color = (0.10, 0.34, 0.19)
fill_obj = bpy.data.objects.new("Room_Green_Fill", fill_data)
rig_collection.objects.link(fill_obj)
fill_obj.location = (0, 0, ROOM_HEIGHT - 0.10)
fill_obj.rotation_euler = (0, 0, 0)

back_data = bpy.data.lights.new("Back_Wall_Wash", type="AREA")
back_data.energy = 180.0
back_data.shape = "RECTANGLE"
back_data.size = 2.2
back_data.size_y = 1.0
back_data.color = (0.08, 0.28, 0.15)
back_obj = bpy.data.objects.new("Back_Wall_Wash", back_data)
rig_collection.objects.link(back_obj)
back_obj.location = (2.15, ROOM_DEPTH / 2 - 1.1, 2.2)
aim_object(back_obj, (0.6, ROOM_DEPTH / 2, 1.8))

# =========================================================
# VOLUMETRIC HAZE (RENDER ONLY)
# =========================================================
volume_mat = bpy.data.materials.new("Liminal Haze")
volume_mat.use_nodes = True
v_nodes = volume_mat.node_tree.nodes
v_links = volume_mat.node_tree.links
v_nodes.clear()

v_out = v_nodes.new("ShaderNodeOutputMaterial")
v_out.location = (280, 0)
volume = v_nodes.new("ShaderNodeVolumePrincipled")
volume.location = (0, 0)
volume.inputs["Density"].default_value = 0.012
volume.inputs["Color"].default_value = (0.20, 0.38, 0.25, 1.0)
volume.inputs["Anisotropy"].default_value = 0.22
v_links.new(volume.outputs["Volume"], v_out.inputs["Volume"])

haze = add_cube(
    "Atmospheric_Haze",
    (0, 0, ROOM_HEIGHT / 2),
    (ROOM_WIDTH - 0.12, ROOM_DEPTH - 0.12, ROOM_HEIGHT - 0.12),
    volume_mat,
    collection=rig_collection,
)
haze.display_type = "WIRE"

# =========================================================
# CAMERA
# =========================================================
camera_data = bpy.data.cameras.new("Camera")
camera = bpy.data.objects.new("Camera", camera_data)
rig_collection.objects.link(camera)
scene.camera = camera

camera.location = (0.0, 0.35, 1.62)
camera.data.lens = 20.0
camera.data.sensor_width = 36.0
camera.data.dof.use_dof = False
aim_object(camera, (0.0, ROOM_DEPTH / 2 - 0.5, 1.52))

# =========================================================
# WORLD / FINAL RENDER SETTINGS
# =========================================================
world = bpy.data.worlds.get("World") or bpy.data.worlds.new("World")
scene.world = world
world.use_nodes = True
background = world.node_tree.nodes.get("Background")
background.inputs["Color"].default_value = (0.0015, 0.0045, 0.0025, 1.0)
background.inputs["Strength"].default_value = 0.045

# Transparent reflections / light transport benefit from modest bounces.
if scene.render.engine == "CYCLES":
    scene.cycles.max_bounces = 8
    scene.cycles.diffuse_bounces = 3
    scene.cycles.glossy_bounces = 4
    scene.cycles.transparent_max_bounces = 4

# Keep only the camera selected at the end.
bpy.ops.object.select_all(action="DESELECT")
camera.select_set(True)
bpy.context.view_layer.objects.active = camera

print(f"Checkerboard Room V4 created successfully using {selected_engine}.")
print("Render with Render > Render Image.")
print("For the web, export WEB_EXPORT as checkerboard-v4.glb and CHANDELIER_EXPORT as warm-chandelier.glb.")
