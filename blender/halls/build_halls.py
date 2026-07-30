"""Build the shared hall shell and one or both hall-specific object files.

This mirrors the second-story room workflow:

- shared/hall_shell.py owns all permanent architecture, materials, and lighting
- ballroom/unique.py owns only ballroom objects
- museum/unique.py owns only museum objects
- the website mirrors only the shared shell for the ballroom

Open this file in Blender's Scripting workspace and edit the EASY SETTINGS
section for normal use.
"""

from __future__ import annotations

from dataclasses import dataclass
import importlib
import importlib.util
from pathlib import Path
import sys

import bpy
from mathutils import Vector


# =============================================================================
# EASY SETTINGS
# =============================================================================
# "BALLROOM", "MUSEUM", or "ALL". A wrapper file can override this value.
HALL_TO_BUILD = globals().get("HALL_TO_BUILD", "ALL")

# Rebuild the canonical shared room before generating object files.
REBUILD_SHARED_SHELL = globals().get("REBUILD_SHARED_SHELL", True)

# Save a Blender preview file for each hall. The preview includes the shared
# shell in its correct orientation, but only the objects collection is exported.
SAVE_OBJECT_PREVIEW_BLEND = globals().get("SAVE_OBJECT_PREVIEW_BLEND", True)

# Optional absolute path to blender/halls. Leave as None for the normal project path.
HALLS_ROOT_OVERRIDE = globals().get("HALLS_ROOT_OVERRIDE", None)


@dataclass(frozen=True)
class HallDefinition:
    slug: str
    title: str
    mirror_shell_x: bool


@dataclass
class HallObjectContext:
    definition: HallDefinition
    output_directory: Path
    scene: bpy.types.Scene
    objects_collection: bpy.types.Collection
    objects_root: bpy.types.Object
    assets_root: Path
    add_box: object
    material: object
    linear_hex: object
    import_glb: object
    asset_path: object
    place_asset: object


def _is_halls_root(path: Path) -> bool:
    """Return True when *path* contains the expected hall source files."""
    return (
        (path / "build_halls.py").is_file()
        and (path / "shared" / "hall_shell.py").is_file()
    )


def _candidate_roots_from_file(file_path: Path):
    """Yield the file's folder and ancestors that could be blender/halls."""
    folder = file_path.parent if file_path.suffix else file_path
    yield folder
    yield from folder.parents


def script_directory() -> Path:
    """Resolve blender/halls reliably inside Blender's Text Editor.

    Blender often exposes an opened text file as ``//build_halls.py``. Passing
    that string directly to ``pathlib`` can incorrectly resolve it as
    ``/build_halls.py`` when the current .blend is unsaved. We therefore verify
    every candidate and retain the known project location as a final fallback.
    """
    candidates: list[Path] = []

    override = globals().get("HALLS_ROOT_OVERRIDE")
    if override:
        candidates.append(Path(override).expanduser())

    try:
        text = bpy.context.space_data.text
        if text and text.filepath:
            text_path = text.filepath
            if text_path.startswith("//"):
                text_path = bpy.path.abspath(text_path)
            candidates.extend(_candidate_roots_from_file(Path(text_path).expanduser()))
    except (AttributeError, RuntimeError):
        pass

    try:
        raw_file = str(__file__)
        if raw_file.startswith("//"):
            raw_file = bpy.path.abspath(raw_file)
        candidates.extend(_candidate_roots_from_file(Path(raw_file).expanduser()))
    except NameError:
        pass

    if bpy.data.filepath:
        candidates.extend(
            _candidate_roots_from_file(Path(bpy.data.filepath).expanduser())
        )

    candidates.extend(_candidate_roots_from_file(Path.cwd()))

    # Normal location for this project. This also makes the script work from a
    # brand-new, unsaved Blender file. Change HALLS_ROOT_OVERRIDE above if the
    # repository is moved somewhere else.
    candidates.append(
        Path.home()
        / "Desktop"
        / "projects"
        / "hecate946.com"
        / "blender"
        / "halls"
    )

    checked: list[str] = []
    for candidate in candidates:
        try:
            candidate = candidate.resolve()
        except OSError:
            continue
        candidate_text = str(candidate)
        if candidate_text in checked:
            continue
        checked.append(candidate_text)
        if _is_halls_root(candidate):
            return candidate

    raise FileNotFoundError(
        "Could not locate blender/halls. Expected build_halls.py and "
        "shared/hall_shell.py in the same hall root.\nChecked:\n  - "
        + "\n  - ".join(checked)
        + "\nSet HALLS_ROOT_OVERRIDE near the top of build_halls.py if your "
        "project is stored elsewhere."
    )


HALLS_ROOT = script_directory()
SHARED_ROOT = HALLS_ROOT / "shared"
SHARED_SCRIPT = SHARED_ROOT / "hall_shell.py"
SHARED_GLB = SHARED_ROOT / "hall-shell.glb"

HALLS = (
    # The canonical shell has its doorway on the left.
    HallDefinition("museum", "The Museum", False),
    # The website and Blender preview mirror only the shell for the ballroom.
    HallDefinition("ballroom", "The Ballroom", True),
)


def load_module(module_name: str, file_path: Path):
    """Load a Python module fresh from disk, bypassing Blender/Python caches."""
    file_path = Path(file_path).expanduser().resolve()
    if not file_path.exists():
        raise FileNotFoundError(f"Blender module does not exist: {file_path}")

    # Refresh Python's import-system caches.
    importlib.invalidate_caches()

    # Remove a module with the same name from this Blender session.
    sys.modules.pop(module_name, None)

    # Remove the compiled bytecode cache. This avoids stale .pyc files when a
    # source file is replaced quickly and keeps the same timestamp or size.
    try:
        pyc_path = Path(importlib.util.cache_from_source(str(file_path)))
        if pyc_path.exists():
            pyc_path.unlink()
    except (NotImplementedError, OSError, ValueError):
        pass

    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load Blender module: {file_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module

    try:
        spec.loader.exec_module(module)
    except Exception:
        # Do not leave a partially initialized module cached after a failure.
        sys.modules.pop(module_name, None)
        raise

    print(f"Loaded fresh module from: {file_path}")
    return module


def reset_scene() -> bpy.types.Scene:
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")

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
        bpy.data.images,
    ):
        for block in list(datablocks):
            if block.users == 0:
                try:
                    datablocks.remove(block)
                except RuntimeError:
                    pass

    return bpy.context.scene


def linear_hex(value: str):
    value = value.lstrip("#")
    rgb = [int(value[index : index + 2], 16) / 255.0 for index in (0, 2, 4)]

    def linear(channel: float) -> float:
        if channel <= 0.04045:
            return channel / 12.92
        return ((channel + 0.055) / 1.055) ** 2.4

    return (*[linear(channel) for channel in rgb], 1.0)


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


def move_to_collection(obj: bpy.types.Object, collection: bpy.types.Collection) -> None:
    for old_collection in list(obj.users_collection):
        old_collection.objects.unlink(obj)
    collection.objects.link(obj)


def add_box(
    name,
    center,
    size,
    mat,
    collection,
    bevel=0.0,
    parent=None,
):
    bpy.ops.mesh.primitive_cube_add(size=1, location=center)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if mat is not None:
        obj.data.materials.append(mat)
    move_to_collection(obj, collection)

    if parent is not None:
        obj.parent = parent

    if bevel > 0:
        modifier = obj.modifiers.new("Rounded edges", "BEVEL")
        modifier.width = bevel
        modifier.segments = 2

    return obj


def import_glb(file_path, collection, parent=None, name_prefix=""):
    """Import an external GLB and move its imported roots into the object export."""
    file_path = Path(file_path).expanduser().resolve()
    if not file_path.exists():
        raise FileNotFoundError(f"Object GLB does not exist: {file_path}")

    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(file_path))
    imported = [obj for obj in bpy.data.objects if obj not in before]
    imported_set = set(imported)

    for obj in imported:
        if name_prefix:
            obj.name = f"{name_prefix}{obj.name}"
        move_to_collection(obj, collection)

    for obj in imported:
        if obj.parent not in imported_set and parent is not None:
            matrix_world = obj.matrix_world.copy()
            obj.parent = parent
            obj.matrix_world = matrix_world

    return imported


def export_collection(
    main_scene: bpy.types.Scene,
    collection: bpy.types.Collection,
    output_file: Path,
) -> None:
    output_file.parent.mkdir(parents=True, exist_ok=True)
    export_scene = bpy.data.scenes.new("Temporary_Hall_Objects_Export")
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


def import_shell_preview(scene: bpy.types.Scene, mirror_x: bool) -> bpy.types.Object:
    if not SHARED_GLB.exists():
        raise FileNotFoundError(
            f"Shared hall shell is missing: {SHARED_GLB}\n"
            "Run shared/hall_shell.py or enable REBUILD_SHARED_SHELL."
        )

    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(SHARED_GLB))
    imported = [obj for obj in bpy.data.objects if obj not in before]
    imported_set = set(imported)

    shell_root = bpy.data.objects.new("Shared_Hall_Shell_Preview", None)
    scene.collection.objects.link(shell_root)

    for obj in imported:
        if obj.parent not in imported_set:
            matrix_world = obj.matrix_world.copy()
            obj.parent = shell_root
            obj.matrix_world = matrix_world

    if mirror_x:
        shell_root.scale.x = -1.0
        shell_root["website_shell_scale_x"] = -1.0
    else:
        shell_root["website_shell_scale_x"] = 1.0

    shell_root["preview_only"] = True
    shell_root["exported_separately"] = True
    bpy.context.view_layer.update()

    camera_data = bpy.data.cameras.new("Hall_Object_Preview_Camera")
    preview_camera = bpy.data.objects.new("Hall_Object_Preview_Camera", camera_data)
    scene.collection.objects.link(preview_camera)
    preview_camera.location = (0.0, 0.0, 1.68)
    preview_camera.rotation_euler = (
        Vector((0.0, 1.0, 1.68)) - preview_camera.location
    ).to_track_quat("-Z", "Y").to_euler()
    camera_data.lens = 24.0
    scene.camera = preview_camera

    return shell_root


def load_unique_module(unique_file: Path):
    if not unique_file.exists():
        return None
    return load_module(f"hall_unique_{unique_file.parent.name}", unique_file)


def call_unique_hook(module, context: HallObjectContext) -> None:
    if module is None:
        return

    hook = getattr(module, "add_objects", None)
    if callable(hook):
        hook(context)


def build_shared_shell() -> None:
    if not SHARED_SCRIPT.exists():
        raise FileNotFoundError(f"Shared hall generator is missing: {SHARED_SCRIPT}")

    module = load_module("shared_hall_shell", SHARED_SCRIPT)
    module.OUTPUT_DIRECTORY = SHARED_ROOT
    module.PYTHON_OUTPUT_PATH = SHARED_SCRIPT
    module.GLB_OUTPUT_PATH = SHARED_GLB
    module.PNG_OUTPUT_PATH = SHARED_ROOT / "hall-shell.png"
    module.BLEND_OUTPUT_PATH = SHARED_ROOT / "hall-shell.blend"
    module.AUTO_EXPORT_GLB = True
    module.AUTO_RENDER = False
    module.AUTO_SAVE_BLEND = True
    module.build_scene()


def build_hall_objects(definition: HallDefinition) -> None:
    output_directory = HALLS_ROOT / definition.slug
    output_directory.mkdir(parents=True, exist_ok=True)

    objects_file = output_directory / f"{definition.slug}-objects.glb"
    preview_file = output_directory / f"{definition.slug}-objects.blend"

    scene = reset_scene()
    shell_root = import_shell_preview(scene, definition.mirror_shell_x)

    objects_collection = bpy.data.collections.new("HALL_OBJECTS_EXPORT")
    scene.collection.children.link(objects_collection)

    objects_root = bpy.data.objects.new(f"{definition.slug.title()}_Objects_Root", None)
    objects_collection.objects.link(objects_root)
    objects_root["hall_slug"] = definition.slug
    objects_root["shell_mirrored_x"] = definition.mirror_shell_x

    blender_root = HALLS_ROOT.parent
    project_root = blender_root.parent
    assets_root = project_root / "public" / "scenes" / "assets"
    asset_library = load_module(
        "hecate_shared_asset_library_halls",
        blender_root / "shared" / "asset_library.py",
    )

    def asset_path(asset_id, *, file_name=None):
        return asset_library.resolve_asset_path(
            assets_root,
            asset_id,
            file_name=file_name,
        )

    def place_asset(asset_id, *, name=None, extras=None, **placement):
        placed = asset_library.place_asset(
            assets_root=assets_root,
            asset_id=asset_id,
            collection=objects_collection,
            name=name,
            extras=extras,
            **placement,
        )
        matrix_world = placed.root.matrix_world.copy()
        placed.root.parent = objects_root
        placed.root.matrix_world = matrix_world
        return placed

    context = HallObjectContext(
        definition=definition,
        output_directory=output_directory,
        scene=scene,
        objects_collection=objects_collection,
        objects_root=objects_root,
        assets_root=assets_root,
        add_box=add_box,
        material=material,
        linear_hex=linear_hex,
        import_glb=import_glb,
        asset_path=asset_path,
        place_asset=place_asset,
    )

    unique_module = load_unique_module(output_directory / "unique.py")
    call_unique_hook(unique_module, context)

    # Keep authoring metadata in the preview without exporting the preview shell.
    shell_root["hall_slug"] = definition.slug

    export_collection(scene, objects_collection, objects_file)

    if SAVE_OBJECT_PREVIEW_BLEND:
        bpy.ops.wm.save_as_mainfile(filepath=str(preview_file))

    print(f"Built {definition.title} objects")
    print(f"  Shared shell: {SHARED_GLB}")
    print(f"  Mirrored X:   {definition.mirror_shell_x}")
    print(f"  Objects GLB:  {objects_file}")
    if SAVE_OBJECT_PREVIEW_BLEND:
        print(f"  Preview:      {preview_file}")


selection = str(HALL_TO_BUILD).strip().lower()
if selection == "all":
    halls_to_build = HALLS
else:
    halls_to_build = tuple(hall for hall in HALLS if hall.slug == selection)
    if not halls_to_build:
        raise ValueError('HALL_TO_BUILD must be "BALLROOM", "MUSEUM", or "ALL".')

print("=" * 72)
print("Shared hall and hall-object builder")
print(f"Halls:                {', '.join(hall.slug for hall in halls_to_build)}")
print(f"Rebuild shared shell: {REBUILD_SHARED_SHELL}")
print(f"Save previews:        {SAVE_OBJECT_PREVIEW_BLEND}")
print("=" * 72)

if REBUILD_SHARED_SHELL:
    build_shared_shell()

for hall_definition in halls_to_build:
    build_hall_objects(hall_definition)

print("All requested hall assets finished.")