"""Build the reusable dark-brown leather wingback armchair asset.

Project convention:

    blender/assets/leather-armchair/leather-armchair.py
    blender/assets/leather-armchair/leather-armchair.blend   (generated)
    blender/assets/leather-armchair/leather-armchair.glb     (generated)

The asset is authored in meters, rests on Z=0, is centered on X=0, and faces
+Y to match ``blender/shared/asset_library.py``. The GLB contains only the chair
hierarchy; generated leather textures are packed and embedded in the GLB.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Iterable, Sequence

import bpy


ASSET_ID = "leather-armchair"
ROOT_NAME = "LeatherArmchair"
TEXTURE_SIZE = 512
TEXTURE_SEED = 946

# Overall target envelope, in meters. The geometry remains centered around X=0,
# touches the floor at Z=0, and presents its front toward +Y.
OVERALL_WIDTH = 1.08
OVERALL_DEPTH = 0.88
OVERALL_HEIGHT = 1.44


# -----------------------------------------------------------------------------
# File / scene helpers
# -----------------------------------------------------------------------------


def script_directory() -> Path:
    """Resolve beside this script in both Text Editor and background mode."""
    try:
        text = bpy.context.space_data.text
        if text and text.filepath:
            return Path(bpy.path.abspath(text.filepath)).resolve().parent
    except (AttributeError, RuntimeError):
        pass

    try:
        return Path(__file__).resolve().parent
    except NameError:
        return Path.cwd().resolve()


def clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)

    # Remove orphaned collections and materials left by a previously opened
    # file so repeated background runs remain deterministic.
    for collection in list(bpy.data.collections):
        if collection.users == 0:
            bpy.data.collections.remove(collection)


def configure_scene() -> None:
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.length_unit = "METERS"
    scene.unit_settings.scale_length = 1.0
    # Eevee was renamed from BLENDER_EEVEE to BLENDER_EEVEE_NEXT in newer
    # Blender releases. Prefer the newer identifier, but remain compatible
    # with Blender versions that expose only the legacy Eevee engine.
    try:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    except TypeError:
        scene.render.engine = "BLENDER_EEVEE"


# -----------------------------------------------------------------------------
# Materials and embedded PBR textures
# -----------------------------------------------------------------------------


def set_socket(node, names: str | Iterable[str], value) -> None:
    if isinstance(names, str):
        names = (names,)
    for name in names:
        socket = node.inputs.get(name)
        if socket is not None:
            socket.default_value = value
            return


def remove_datablock(collection, name: str) -> None:
    existing = collection.get(name)
    if existing is not None:
        collection.remove(existing)


def blur_wrap(values, iterations: int):
    """Small tileable blur using Blender's bundled NumPy."""
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


def create_image(name: str, pixels, *, color_space: str) -> bpy.types.Image:
    import numpy as np

    remove_datablock(bpy.data.images, name)
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

    # Packed generated images are embedded into the exported GLB.
    try:
        image.pack()
    except RuntimeError:
        pass

    return image


def create_leather_texture_set(size: int = TEXTURE_SIZE):
    """Generate subtle, tileable dark-brown leather PBR maps."""
    import numpy as np

    rng = np.random.default_rng(TEXTURE_SEED)
    u, v = np.meshgrid(
        np.linspace(0.0, 1.0, size, endpoint=False, dtype=np.float32),
        np.linspace(0.0, 1.0, size, endpoint=False, dtype=np.float32),
    )

    coarse = blur_wrap(
        rng.normal(0.0, 1.0, (size, size)).astype(np.float32),
        13,
    )
    medium = blur_wrap(
        rng.normal(0.0, 1.0, (size, size)).astype(np.float32),
        4,
    )
    fine = rng.normal(0.0, 1.0, (size, size)).astype(np.float32)

    # Irregular pebble grain and tiny pores. Integer frequencies keep the map
    # tileable while the noise prevents a synthetic repeating appearance.
    pebble = (
        np.sin(math.tau * (u * 31.0 + medium * 0.045))
        * np.sin(math.tau * (v * 27.0 - medium * 0.035))
    )
    pores = np.sin(math.tau * (u * 83.0 + v * 7.0)) * np.sin(
        math.tau * (v * 79.0 - u * 5.0)
    )

    height = 0.52 + coarse * 0.13 + medium * 0.075 + pebble * 0.025 + pores * 0.010
    height += fine * 0.007
    height = np.clip(height, 0.0, 1.0)

    # Rich espresso brown: dark enough for the requested appearance, while
    # retaining warm highlights and readable tufting under room lights.
    base = np.empty((size, size, 4), dtype=np.float32)
    base[..., 0] = np.clip(0.135 + height * 0.135, 0.13, 0.30)
    base[..., 1] = np.clip(0.043 + height * 0.064, 0.038, 0.12)
    base[..., 2] = np.clip(0.022 + height * 0.034, 0.018, 0.068)
    base[..., 3] = 1.0

    rough_value = np.clip(0.225 + (1.0 - height) * 0.15 + medium * 0.016, 0.20, 0.40)
    roughness = np.empty((size, size, 4), dtype=np.float32)
    roughness[..., 0] = rough_value
    roughness[..., 1] = rough_value
    roughness[..., 2] = rough_value
    roughness[..., 3] = 1.0

    dv, du = np.gradient(height)
    strength = 4.0
    nx = -du * strength
    ny = -dv * strength
    nz = np.ones_like(nx)
    length = np.sqrt(nx * nx + ny * ny + nz * nz)

    normal = np.empty((size, size, 4), dtype=np.float32)
    normal[..., 0] = nx / length * 0.5 + 0.5
    normal[..., 1] = ny / length * 0.5 + 0.5
    normal[..., 2] = nz / length * 0.5 + 0.5
    normal[..., 3] = 1.0

    return (
        create_image("Armchair_Leather_BaseColor", base, color_space="sRGB"),
        create_image("Armchair_Leather_Roughness", roughness, color_space="Non-Color"),
        create_image("Armchair_Leather_Normal", normal, color_space="Non-Color"),
    )


def create_leather_material() -> bpy.types.Material:
    remove_datablock(bpy.data.materials, "Armchair_DarkBrownLeather")
    base_image, roughness_image, normal_image = create_leather_texture_set()

    material = bpy.data.materials.new("Armchair_DarkBrownLeather")
    material.use_nodes = True
    material.diffuse_color = (0.22, 0.072, 0.034, 1.0)

    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()

    output = nodes.new("ShaderNodeOutputMaterial")
    output.location = (720, 0)

    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (420, 0)
    set_socket(bsdf, "Metallic", 0.0)
    set_socket(bsdf, "Roughness", 0.27)
    set_socket(bsdf, ("Specular IOR Level", "Specular"), 0.50)
    set_socket(bsdf, ("Coat Weight", "Clearcoat"), 0.12)
    set_socket(bsdf, ("Coat Roughness", "Clearcoat Roughness"), 0.18)

    base_node = nodes.new("ShaderNodeTexImage")
    base_node.name = "Leather Base Color"
    base_node.image = base_image
    base_node.location = (-360, 150)
    links.new(base_node.outputs["Color"], bsdf.inputs["Base Color"])

    rough_node = nodes.new("ShaderNodeTexImage")
    rough_node.name = "Leather Roughness"
    rough_node.image = roughness_image
    rough_node.location = (-360, -40)
    links.new(rough_node.outputs["Color"], bsdf.inputs["Roughness"])

    normal_texture = nodes.new("ShaderNodeTexImage")
    normal_texture.name = "Leather Normal"
    normal_texture.image = normal_image
    normal_texture.location = (-360, -240)

    normal_map = nodes.new("ShaderNodeNormalMap")
    normal_map.location = (80, -210)
    normal_map.inputs["Strength"].default_value = 0.24
    links.new(normal_texture.outputs["Color"], normal_map.inputs["Color"])
    links.new(normal_map.outputs["Normal"], bsdf.inputs["Normal"])

    links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])
    return material


def create_plain_material(
    name: str,
    color: Sequence[float],
    *,
    roughness: float,
    specular: float = 0.38,
) -> bpy.types.Material:
    remove_datablock(bpy.data.materials, name)
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    material.diffuse_color = tuple(color)

    bsdf = material.node_tree.nodes.get("Principled BSDF")
    if bsdf is not None:
        set_socket(bsdf, "Base Color", tuple(color))
        set_socket(bsdf, "Metallic", 0.0)
        set_socket(bsdf, "Roughness", roughness)
        set_socket(bsdf, ("Specular IOR Level", "Specular"), specular)
    return material


# -----------------------------------------------------------------------------
# Geometry helpers
# -----------------------------------------------------------------------------


def assign_material(obj: bpy.types.Object, material: bpy.types.Material) -> None:
    if obj.data is not None and hasattr(obj.data, "materials"):
        obj.data.materials.clear()
        obj.data.materials.append(material)


def smooth_mesh(obj: bpy.types.Object) -> None:
    if obj.type != "MESH":
        return
    for polygon in obj.data.polygons:
        polygon.use_smooth = True


def add_rounded_box(
    name: str,
    location: Sequence[float],
    dimensions: Sequence[float],
    bevel: float,
    material: bpy.types.Material,
    *,
    rotation: Sequence[float] = (0.0, 0.0, 0.0),
    bevel_segments: int = 5,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=location, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    modifier = obj.modifiers.new(name="Soft Upholstery Edges", type="BEVEL")
    modifier.width = min(bevel, min(dimensions) * 0.48)
    modifier.segments = bevel_segments
    modifier.limit_method = "ANGLE"
    modifier.harden_normals = True

    smooth_mesh(obj)
    assign_material(obj, material)
    return obj


def add_uv_sphere(
    name: str,
    location: Sequence[float],
    scale: Sequence[float],
    material: bpy.types.Material,
    *,
    rotation: Sequence[float] = (0.0, 0.0, 0.0),
    segments: int = 48,
    rings: int = 24,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=segments,
        ring_count=rings,
        radius=1.0,
        location=location,
        rotation=rotation,
    )
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    smooth_mesh(obj)
    assign_material(obj, material)
    return obj


def add_tapered_leg(
    name: str,
    location: Sequence[float],
    material: bpy.types.Material,
    *,
    height: float = 0.28,
    top_radius: float = 0.055,
    bottom_radius: float = 0.035,
    rotation: Sequence[float] = (0.0, 0.0, 0.0),
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cone_add(
        vertices=32,
        radius1=bottom_radius,
        radius2=top_radius,
        depth=height,
        end_fill_type="NGON",
        location=location,
        rotation=rotation,
    )
    obj = bpy.context.object
    obj.name = name

    modifier = obj.modifiers.new(name="Leg Edge Softening", type="BEVEL")
    modifier.width = 0.008
    modifier.segments = 3
    modifier.limit_method = "ANGLE"
    modifier.harden_normals = True

    smooth_mesh(obj)
    assign_material(obj, material)
    return obj



def add_tapered_box_leg(
    name: str,
    location: Sequence[float],
    material: bpy.types.Material,
    *,
    height: float = 0.30,
    top_size: Sequence[float] = (0.078, 0.082),
    bottom_size: Sequence[float] = (0.047, 0.050),
    rotation: Sequence[float] = (0.0, 0.0, 0.0),
) -> bpy.types.Object:
    """Create the slim, square-tapered wooden legs visible in the reference."""
    tx, ty = top_size[0] / 2.0, top_size[1] / 2.0
    bx, by = bottom_size[0] / 2.0, bottom_size[1] / 2.0
    hz = height / 2.0
    vertices = [
        (-bx, -by, -hz), (bx, -by, -hz), (bx, by, -hz), (-bx, by, -hz),
        (-tx, -ty, hz), (tx, -ty, hz), (tx, ty, hz), (-tx, ty, hz),
    ]
    faces = [
        (0, 3, 2, 1), (4, 5, 6, 7),
        (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7),
    ]
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()

    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = location
    obj.rotation_euler = rotation

    bevel = obj.modifiers.new(name="Rounded Wooden Edges", type="BEVEL")
    bevel.width = 0.009
    bevel.segments = 3
    bevel.limit_method = "ANGLE"
    bevel.harden_normals = True
    assign_material(obj, material)
    return obj


def add_torus(
    name: str,
    location: Sequence[float],
    major_radius: float,
    minor_radius: float,
    material: bpy.types.Material,
    *,
    rotation: Sequence[float] = (0.0, 0.0, 0.0),
    scale: Sequence[float] = (1.0, 1.0, 1.0),
) -> bpy.types.Object:
    """Create a smooth upholstered ring used for the rolled arm fronts."""
    bpy.ops.mesh.primitive_torus_add(
        major_segments=64,
        minor_segments=20,
        major_radius=major_radius,
        minor_radius=minor_radius,
        location=location,
        rotation=rotation,
    )
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    smooth_mesh(obj)
    assign_material(obj, material)
    return obj


def add_planar_uv(mesh: bpy.types.Mesh) -> None:
    """Give custom front-facing upholstery meshes stable texture coordinates."""
    if not mesh.vertices or not mesh.polygons:
        return
    min_x = min(vertex.co.x for vertex in mesh.vertices)
    max_x = max(vertex.co.x for vertex in mesh.vertices)
    min_z = min(vertex.co.z for vertex in mesh.vertices)
    max_z = max(vertex.co.z for vertex in mesh.vertices)
    span_x = max(max_x - min_x, 1e-6)
    span_z = max(max_z - min_z, 1e-6)
    uv_layer = mesh.uv_layers.new(name="UVMap")
    for polygon in mesh.polygons:
        for loop_index in polygon.loop_indices:
            coordinate = mesh.vertices[mesh.loops[loop_index].vertex_index].co
            uv_layer.data[loop_index].uv = (
                (coordinate.x - min_x) / span_x,
                (coordinate.z - min_z) / span_z,
            )


def add_profiled_panel(
    name: str,
    location: Sequence[float],
    outline: Sequence[Sequence[float]],
    depth: float,
    material: bpy.types.Material,
    *,
    rotation: Sequence[float] = (0.0, 0.0, 0.0),
    bevel_width: float = 0.035,
) -> bpy.types.Object:
    """Extrude an X/Z outline into a softly beveled upholstered panel."""
    count = len(outline)
    back = [(x, -depth / 2.0, z) for x, z in outline]
    front = [(x, depth / 2.0, z) for x, z in outline]
    vertices = back + front
    faces: list[tuple[int, ...]] = [
        tuple(reversed(range(count))),
        tuple(range(count, count * 2)),
    ]
    for index in range(count):
        next_index = (index + 1) % count
        faces.append((index, next_index, count + next_index, count + index))

    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    add_planar_uv(mesh)

    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = location
    obj.rotation_euler = rotation

    bevel = obj.modifiers.new(name="Soft Profile Edges", type="BEVEL")
    bevel.width = bevel_width
    bevel.segments = 6
    bevel.limit_method = "ANGLE"
    bevel.harden_normals = True
    assign_material(obj, material)
    return obj


def add_diamond_puff(
    name: str,
    local_center: Sequence[float],
    *,
    back_center: Sequence[float],
    rotation_x: float,
    width: float,
    height: float,
    depth: float,
    material: bpy.types.Material,
) -> bpy.types.Object:
    """Create one rounded diamond-shaped leather tuft with a soft center bulge."""
    segment_count = 20
    ring_scales = (0.34, 0.68, 1.0)
    vertices: list[tuple[float, float, float]] = [(0.0, depth, 0.0)]

    # A rounded diamond is a superellipse with an exponent close to one.
    shape_power = 1.30
    exponent = 2.0 / shape_power
    for ring in ring_scales:
        ring_depth = depth * (1.0 - ring ** 1.65)
        for index in range(segment_count):
            angle = math.tau * index / segment_count
            cosine = math.cos(angle)
            sine = math.sin(angle)
            x = (
                math.copysign(abs(cosine) ** exponent, cosine)
                * width
                * 0.5
                * ring
            )
            z = (
                math.copysign(abs(sine) ** exponent, sine)
                * height
                * 0.5
                * ring
            )
            vertices.append((x, ring_depth, z))

    faces: list[tuple[int, ...]] = []
    for index in range(segment_count):
        faces.append((0, 1 + index, 1 + (index + 1) % segment_count))
    for ring_index in range(len(ring_scales) - 1):
        current_start = 1 + ring_index * segment_count
        next_start = current_start + segment_count
        for index in range(segment_count):
            following = (index + 1) % segment_count
            faces.append(
                (
                    current_start + index,
                    next_start + index,
                    next_start + following,
                    current_start + following,
                )
            )

    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    add_planar_uv(mesh)

    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = back_local_to_world(
        local_center,
        center=back_center,
        rotation_x=rotation_x,
    )
    obj.rotation_euler = (rotation_x, 0.0, 0.0)
    smooth_mesh(obj)

    solidify = obj.modifiers.new(name="Tuft Edge Thickness", type="SOLIDIFY")
    solidify.thickness = 0.012
    solidify.offset = -1.0
    assign_material(obj, material)
    return obj


def add_curve_tube(
    name: str,
    points: Sequence[Sequence[float]],
    radius: float,
    material: bpy.types.Material,
    *,
    cyclic: bool = False,
    resolution: int = 10,
    bevel_resolution: int = 5,
) -> bpy.types.Object:
    curve = bpy.data.curves.new(name=f"{name}_Curve", type="CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = resolution
    curve.bevel_depth = radius
    curve.bevel_resolution = bevel_resolution
    curve.resolution_u = resolution
    curve.use_fill_caps = True

    spline = curve.splines.new("BEZIER")
    spline.bezier_points.add(len(points) - 1)
    spline.use_cyclic_u = cyclic
    for point, coordinate in zip(spline.bezier_points, points):
        point.co = coordinate
        point.handle_left_type = "AUTO"
        point.handle_right_type = "AUTO"

    obj = bpy.data.objects.new(name, curve)
    bpy.context.scene.collection.objects.link(obj)
    assign_material(obj, material)

    # glTF exports meshes rather than native Blender curves.
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.convert(target="MESH")
    obj = bpy.context.object
    obj.name = name
    smooth_mesh(obj)
    return obj


def rounded_rectangle_points(
    center: Sequence[float],
    width: float,
    depth: float,
    radius: float,
    *,
    z: float,
    samples_per_corner: int = 6,
) -> list[tuple[float, float, float]]:
    cx, cy = center[0], center[1]
    radius = min(radius, width / 2.0, depth / 2.0)
    corners = (
        (cx + width / 2.0 - radius, cy + depth / 2.0 - radius, 0.0),
        (cx - width / 2.0 + radius, cy + depth / 2.0 - radius, 90.0),
        (cx - width / 2.0 + radius, cy - depth / 2.0 + radius, 180.0),
        (cx + width / 2.0 - radius, cy - depth / 2.0 + radius, 270.0),
    )

    points: list[tuple[float, float, float]] = []
    for corner_x, corner_y, start_degrees in corners:
        for index in range(samples_per_corner):
            angle = math.radians(start_degrees + index * 90.0 / samples_per_corner)
            points.append(
                (
                    corner_x + math.cos(angle) * radius,
                    corner_y + math.sin(angle) * radius,
                    z,
                )
            )
    return points


def back_local_to_world(
    local: Sequence[float],
    *,
    center: Sequence[float],
    rotation_x: float,
) -> tuple[float, float, float]:
    x, y, z = local
    cosine = math.cos(rotation_x)
    sine = math.sin(rotation_x)
    return (
        center[0] + x,
        center[1] + y * cosine - z * sine,
        center[2] + y * sine + z * cosine,
    )


def add_back_plane_curve(
    name: str,
    local_points: Sequence[Sequence[float]],
    *,
    center: Sequence[float],
    rotation_x: float,
    radius: float,
    material: bpy.types.Material,
    cyclic: bool = False,
) -> bpy.types.Object:
    points = [
        back_local_to_world(point, center=center, rotation_x=rotation_x)
        for point in local_points
    ]
    return add_curve_tube(
        name,
        points,
        radius,
        material,
        cyclic=cyclic,
        resolution=5,
        bevel_resolution=3,
    )


# -----------------------------------------------------------------------------
# Chair construction
# -----------------------------------------------------------------------------


def build_armchair() -> bpy.types.Object:
    leather = create_leather_material()
    leather_dark = create_plain_material(
        "Armchair_DeepSeamLeather",
        (0.075, 0.020, 0.009, 1.0),
        roughness=0.31,
        specular=0.38,
    )
    piping = create_plain_material(
        "Armchair_LeatherPiping",
        (0.105, 0.031, 0.014, 1.0),
        roughness=0.25,
        specular=0.48,
    )
    wood = create_plain_material(
        "Armchair_DarkWood",
        (0.026, 0.009, 0.005, 1.0),
        roughness=0.24,
        specular=0.44,
    )

    created: list[bpy.types.Object] = []

    # Slim, square-tapered legs closely match the clean wooden legs in the
    # approved reference image. The front pair has a subtle outward splay.
    created.extend(
        [
            add_tapered_box_leg(
                "FrontLeg_L",
                (-0.382, 0.255, 0.150),
                wood,
                rotation=(0.0, math.radians(-3.0), math.radians(1.5)),
            ),
            add_tapered_box_leg(
                "FrontLeg_R",
                (0.382, 0.255, 0.150),
                wood,
                rotation=(0.0, math.radians(3.0), math.radians(-1.5)),
            ),
            add_tapered_box_leg(
                "RearLeg_L",
                (-0.345, -0.235, 0.145),
                wood,
                height=0.29,
                top_size=(0.070, 0.075),
                bottom_size=(0.043, 0.047),
                rotation=(math.radians(-3.0), math.radians(-2.0), 0.0),
            ),
            add_tapered_box_leg(
                "RearLeg_R",
                (0.345, -0.235, 0.145),
                wood,
                height=0.29,
                top_size=(0.070, 0.075),
                bottom_size=(0.043, 0.047),
                rotation=(math.radians(-3.0), math.radians(2.0), 0.0),
            ),
        ]
    )

    # Upholstered frame. The narrower body and taller back correct the squat,
    # skeletal proportions of the earlier version.
    created.append(
        add_rounded_box(
            "UpholsteredBase",
            (0.0, 0.005, 0.365),
            (0.84, 0.61, 0.245),
            0.052,
            leather,
            bevel_segments=7,
        )
    )
    created.append(
        add_rounded_box(
            "FrontRailSoftPanel",
            (0.0, 0.306, 0.414),
            (0.68, 0.070, 0.175),
            0.030,
            leather,
            bevel_segments=6,
        )
    )

    # Full side bodies and front uprights make each arm feel substantial and
    # continuous rather than like a tube floating above the seat.
    for side, x in (("L", -0.430), ("R", 0.430)):
        created.append(
            add_rounded_box(
                f"ArmSideBody_{side}",
                (x, -0.010, 0.535),
                (0.205, 0.615, 0.475),
                0.058,
                leather,
                bevel_segments=7,
            )
        )
        created.append(
            add_rounded_box(
                f"ArmFrontUpright_{side}",
                (x, 0.255, 0.515),
                (0.205, 0.180, 0.420),
                0.055,
                leather,
                bevel_segments=7,
            )
        )

    # Thick removable cushion, nearly filling the space between the arm rolls.
    created.append(
        add_rounded_box(
            "SeatCushion",
            (0.0, 0.055, 0.575),
            (0.645, 0.545, 0.175),
            0.062,
            leather,
            bevel_segments=8,
        )
    )
    created.append(
        add_curve_tube(
            "SeatCushion_Piping",
            rounded_rectangle_points(
                (0.0, 0.055),
                0.615,
                0.515,
                0.055,
                z=0.653,
                samples_per_corner=8,
            ),
            0.0065,
            piping,
            cyclic=True,
            resolution=4,
            bevel_resolution=3,
        )
    )

    # Central back has the gently arched crown and flared shoulders from the
    # reference instead of a rectangular board with a separate top block.
    back_center = (0.0, -0.285, 0.995)
    back_rotation_x = math.radians(7.0)
    back_outline = (
        (-0.350, -0.385),
        (-0.375, 0.185),
        (-0.340, 0.305),
        (-0.205, 0.365),
        (0.000, 0.390),
        (0.205, 0.365),
        (0.340, 0.305),
        (0.375, 0.185),
        (0.350, -0.385),
    )
    created.append(
        add_profiled_panel(
            "TuftedBack_Underlay",
            back_center,
            back_outline,
            0.172,
            leather_dark,
            rotation=(back_rotation_x, 0.0, 0.0),
            bevel_width=0.040,
        )
    )

    # The previous black crossing tubes are replaced by eighteen individually
    # modeled, softly bulging diamond tufts. The exposed underlay forms natural
    # recessed seams, while the small covered buttons sit below the puff crowns.
    puff_rows = (
        (-0.275, (-0.240, -0.080, 0.080, 0.240), 0.170, 0.160),
        (-0.138, (-0.160, 0.000, 0.160), 0.190, 0.160),
        (0.000, (-0.240, -0.080, 0.080, 0.240), 0.170, 0.160),
        (0.138, (-0.160, 0.000, 0.160), 0.190, 0.160),
        (0.275, (-0.240, -0.080, 0.080, 0.240), 0.170, 0.160),
    )
    puff_index = 0
    for local_z, x_values, puff_width, puff_height in puff_rows:
        for local_x in x_values:
            puff_index += 1
            created.append(
                add_diamond_puff(
                    f"BackTuft_Puff_{puff_index:02d}",
                    (local_x, 0.092, local_z),
                    back_center=back_center,
                    rotation_x=back_rotation_x,
                    width=puff_width,
                    height=puff_height,
                    depth=0.047,
                    material=leather,
                )
            )

    button_rows = (
        (-0.205, (-0.160, 0.000, 0.160)),
        (-0.069, (-0.240, -0.080, 0.080, 0.240)),
        (0.069, (-0.160, 0.000, 0.160)),
        (0.205, (-0.240, -0.080, 0.080, 0.240)),
    )
    button_index = 0
    for local_z, x_values in button_rows:
        for local_x in x_values:
            button_index += 1
            dimple_location = back_local_to_world(
                (local_x, 0.099, local_z),
                center=back_center,
                rotation_x=back_rotation_x,
            )
            button_location = back_local_to_world(
                (local_x, 0.106, local_z),
                center=back_center,
                rotation_x=back_rotation_x,
            )
            created.append(
                add_uv_sphere(
                    f"Tuft_Dimple_{button_index:02d}",
                    dimple_location,
                    (0.027, 0.007, 0.027),
                    leather_dark,
                    rotation=(back_rotation_x, 0.0, 0.0),
                    segments=32,
                    rings=16,
                )
            )
            created.append(
                add_uv_sphere(
                    f"Tuft_Button_{button_index:02d}",
                    button_location,
                    (0.0115, 0.0075, 0.0115),
                    piping,
                    rotation=(back_rotation_x, 0.0, 0.0),
                    segments=24,
                    rings=12,
                )
            )

    back_outline_curve = [
        (x, 0.101, z) for x, z in back_outline
    ]
    created.append(
        add_back_plane_curve(
            "Back_Cushion_Piping",
            back_outline_curve,
            center=back_center,
            rotation_x=back_rotation_x,
            radius=0.0065,
            material=piping,
            cyclic=True,
        )
    )

    # Broad, clean wing panels with curled upholstered outer rolls. No studs,
    # patterned side fabric, or carved decoration are used anywhere.
    for side, x, inward in (("L", -0.445, 1.0), ("R", 0.445, -1.0)):
        created.append(
            add_rounded_box(
                f"WingPanel_{side}",
                (x, -0.270, 1.045),
                (0.205, 0.245, 0.710),
                0.072,
                leather,
                rotation=(back_rotation_x, 0.0, math.radians(1.5 * inward)),
                bevel_segments=8,
            )
        )
        created.append(
            add_curve_tube(
                f"WingOuterRoll_{side}",
                (
                    (x + 0.020 * inward, -0.235, 0.710),
                    (x + 0.025 * inward, -0.270, 0.995),
                    (x + 0.018 * inward, -0.300, 1.255),
                    (x - 0.020 * inward, -0.282, 1.365),
                    (x - 0.075 * inward, -0.235, 1.330),
                ),
                0.068,
                leather,
                resolution=14,
                bevel_resolution=6,
            )
        )
        created.append(
            add_curve_tube(
                f"WingInnerPiping_{side}",
                (
                    (x - 0.088 * inward, -0.135, 0.720),
                    (x - 0.086 * inward, -0.158, 0.995),
                    (x - 0.078 * inward, -0.180, 1.245),
                    (x - 0.108 * inward, -0.158, 1.320),
                ),
                0.0065,
                piping,
                resolution=10,
                bevel_resolution=3,
            )
        )

    # Rolled arms terminate in real upholstered rings instead of flattened
    # spheres. A padded center and vertical welt complete the scroll profile.
    for side, x, outward in (("L", -0.430, -1.0), ("R", 0.430, 1.0)):
        created.append(
            add_curve_tube(
                f"ArmRoll_{side}",
                (
                    (x, -0.185, 0.720),
                    (x, -0.020, 0.726),
                    (x, 0.165, 0.718),
                    (x, 0.285, 0.700),
                ),
                0.102,
                leather,
                resolution=14,
                bevel_resolution=7,
            )
        )
        created.append(
            add_torus(
                f"ArmFrontScroll_{side}",
                (x, 0.342, 0.698),
                0.069,
                0.043,
                leather,
                rotation=(math.radians(90.0), 0.0, 0.0),
                scale=(1.08, 1.0, 1.0),
            )
        )
        created.append(
            add_uv_sphere(
                f"ArmFrontCenter_{side}",
                (x, 0.390, 0.698),
                (0.067, 0.022, 0.064),
                piping,
                segments=40,
                rings=20,
            )
        )
        created.append(
            add_curve_tube(
                f"ArmFrontVerticalPiping_{side}",
                (
                    (x + 0.086 * outward, 0.349, 0.635),
                    (x + 0.090 * outward, 0.348, 0.520),
                    (x + 0.087 * outward, 0.342, 0.335),
                ),
                0.0055,
                piping,
                resolution=6,
                bevel_resolution=3,
            )
        )

    root = bpy.data.objects.new(ROOT_NAME, None)
    bpy.context.scene.collection.objects.link(root)
    root.empty_display_type = "PLAIN_AXES"
    root.empty_display_size = 0.18
    root["shared_asset"] = True
    root["asset_id"] = ASSET_ID
    root["front_direction"] = "+Y"
    root["units"] = "meters"
    root["overall_width_m"] = OVERALL_WIDTH
    root["overall_depth_m"] = OVERALL_DEPTH
    root["overall_height_m"] = OVERALL_HEIGHT
    root["category"] = "furniture/seating"

    for obj in created:
        obj.parent = root
        obj["armchair_part"] = obj.name

    return root


# -----------------------------------------------------------------------------
# Export
# -----------------------------------------------------------------------------


def descendants(root: bpy.types.Object) -> list[bpy.types.Object]:
    result: list[bpy.types.Object] = []
    stack = list(root.children)
    while stack:
        obj = stack.pop()
        result.append(obj)
        stack.extend(obj.children)
    return result


def export_asset(root: bpy.types.Object, output_file: Path) -> None:
    bpy.ops.object.select_all(action="DESELECT")
    root.select_set(True)
    for obj in descendants(root):
        obj.select_set(True)
    bpy.context.view_layer.objects.active = root

    result = bpy.ops.export_scene.gltf(
        filepath=str(output_file),
        export_format="GLB",
        use_selection=True,
        export_apply=True,
        export_cameras=False,
        export_lights=False,
        export_extras=True,
        export_texcoords=True,
        export_normals=True,
        export_materials="EXPORT",
        export_animations=False,
    )
    if "FINISHED" not in result:
        raise RuntimeError(f"GLB export failed: {result}")


def main() -> None:
    output_directory = script_directory()
    output_directory.mkdir(parents=True, exist_ok=True)
    blend_file = output_directory / f"{ASSET_ID}.blend"
    glb_file = output_directory / f"{ASSET_ID}.glb"

    clear_scene()
    configure_scene()
    root = build_armchair()

    bpy.ops.wm.save_as_mainfile(filepath=str(blend_file))
    export_asset(root, glb_file)

    print("\nLeather armchair shared asset complete.")
    print(f"Blend master: {blend_file}")
    print(f"Staging GLB:  {glb_file}")
    print("Front direction: +Y | Floor contact: Z=0 | Units: meters")
    print("Publish for room/hall builders with: npm run assets:sync")


if __name__ == "__main__":
    main()
