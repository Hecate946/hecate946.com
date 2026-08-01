"""Reusable Blender asset placement from project-owned source files.

Room and hall builders load shared objects directly from ``blender/assets``.
Each asset lives in one folder and may use an editable ``.blend`` source, an
exported ``.glb``/``.gltf``, or both::

    blender/assets/chair/
      asset.json
      chair.blend
      textures/...
      chair.glb              # optional staging/export artifact

``asset.json`` can correct a downloaded model's source orientation and origin
without destructively changing its geometry. A typical configuration is::

    {
      "source": "chair.blend",
      "normalize_origin": "floor-center",
      "source_rotation_degrees": [0, 0, 180]
    }

The placement root owns room- or hall-specific transforms. Source correction is
kept beneath that root so every use of the asset behaves consistently.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import math
from pathlib import Path
import re
from typing import Any, Mapping, Sequence

try:
    import bpy
    from mathutils import Vector
except ModuleNotFoundError:  # Allows path-resolution tests outside Blender.
    bpy = None
    Vector = None


SUPPORTED_ASSET_EXTENSIONS = (".blend", ".glb", ".gltf")
ASSET_METADATA_FILE = "asset.json"
DEFAULT_EXCLUDED_BLEND_OBJECT_TYPES = frozenset({"CAMERA", "LIGHT", "LIGHT_PROBE"})


@dataclass(frozen=True)
class PlacedAsset:
    """The root and imported objects created for one reusable asset placement."""

    asset_id: str
    source_path: Path
    root: Any
    objects: tuple[Any, ...]


def _safe_name(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9_]+", "_", value.strip())
    return value.strip("_") or "SharedAsset"


def _vector3(value: float | Sequence[float], *, label: str) -> tuple[float, float, float]:
    if isinstance(value, (int, float)):
        number = float(value)
        return (number, number, number)

    values = tuple(float(item) for item in value)
    if len(values) != 3:
        raise ValueError(f"{label} must be one number or exactly three numbers.")
    return values


def _inside(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def _read_metadata(asset_folder: Path) -> dict[str, Any]:
    metadata_path = asset_folder / ASSET_METADATA_FILE
    if not metadata_path.is_file():
        return {}

    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"Invalid shared asset metadata: {metadata_path}") from error

    if not isinstance(metadata, dict):
        raise ValueError(f"Shared asset metadata must contain a JSON object: {metadata_path}")
    return metadata


def resolve_asset_path(
    assets_root: str | Path,
    asset_id: str | Path,
    *,
    file_name: str | None = None,
) -> Path:
    """Resolve an asset ID to a project-owned ``.blend`` or glTF source file.

    ``chair`` resolves primarily through ``blender/assets/chair/asset.json`` and
    otherwise falls back to conventional names such as ``chair.blend`` and
    ``chair.glb``. Nested IDs such as ``furniture/chair`` are supported.
    """
    root = Path(assets_root).expanduser().resolve()
    requested = Path(asset_id).expanduser()
    candidates: list[Path] = []

    if requested.suffix.lower() in SUPPORTED_ASSET_EXTENSIONS:
        candidates.append(requested if requested.is_absolute() else root / requested)
    else:
        asset_folder = (root / requested).resolve()
        leaf_name = requested.name

        if _inside(asset_folder, root):
            metadata = _read_metadata(asset_folder)
            metadata_source = metadata.get("source")
            if metadata_source:
                if not isinstance(metadata_source, str):
                    raise ValueError(
                        f"'source' must be a string in {asset_folder / ASSET_METADATA_FILE}"
                    )
                candidates.append(asset_folder / metadata_source)

        if file_name:
            candidates.append(asset_folder / file_name)

        candidates.extend(
            [
                asset_folder / f"{leaf_name}.blend",
                asset_folder / "asset.blend",
                asset_folder / f"{leaf_name}.glb",
                asset_folder / f"{leaf_name}.gltf",
                asset_folder / "asset.glb",
                asset_folder / "asset.gltf",
                root / f"{requested}.blend",
                root / f"{requested}.glb",
                root / f"{requested}.gltf",
            ]
        )

    checked: list[Path] = []
    for candidate in candidates:
        resolved = candidate.expanduser().resolve()
        if resolved in checked:
            continue
        checked.append(resolved)
        if resolved.is_file():
            return resolved

    checked_text = "\n  - ".join(str(path) for path in checked)
    normal_path = root / str(asset_id) / f"{Path(str(asset_id)).name}.blend"
    raise FileNotFoundError(
        f"Shared Blender asset '{asset_id}' was not found.\n"
        f"Expected the normal layout: {normal_path}\n"
        f"Checked:\n  - {checked_text}"
    )


def _move_to_collection(obj: Any, collection: Any) -> None:
    for old_collection in list(obj.users_collection):
        old_collection.objects.unlink(obj)
    if obj.name not in collection.objects:
        collection.objects.link(obj)


def _repair_appended_image_paths(source_path: Path, before_images: set[Any]) -> None:
    """Make relative image paths remain valid after appending from a .blend."""
    for image in bpy.data.images:
        if image in before_images or image.source != "FILE" or not image.filepath:
            continue

        original = image.filepath
        if original.startswith("//"):
            resolved = (source_path.parent / original[2:]).resolve()
            if resolved.is_file():
                image.filepath = str(resolved)
                image.filepath_raw = str(resolved)
                try:
                    image.reload()
                except RuntimeError:
                    pass
            else:
                print(f"Warning: shared asset texture was not found: {resolved}")


def _append_blend_objects(source_path: Path, metadata: Mapping[str, Any]) -> tuple[Any, ...]:
    before_images = set(bpy.data.images)

    with bpy.data.libraries.load(str(source_path), link=False) as (data_from, data_to):
        data_to.objects = list(data_from.objects)

    loaded = tuple(obj for obj in data_to.objects if obj is not None)
    if not loaded:
        raise RuntimeError(f"Shared .blend asset contains no objects: {source_path}")

    excluded_types = set(DEFAULT_EXCLUDED_BLEND_OBJECT_TYPES)
    configured_exclusions = metadata.get("exclude_object_types", ())
    if configured_exclusions:
        if not isinstance(configured_exclusions, list) or not all(
            isinstance(value, str) for value in configured_exclusions
        ):
            raise ValueError(
                f"'exclude_object_types' must be a string array in "
                f"{source_path.parent / ASSET_METADATA_FILE}"
            )
        excluded_types.update(value.upper() for value in configured_exclusions)

    imported = tuple(obj for obj in loaded if obj.type not in excluded_types)
    imported_set = set(imported)

    # Preserve children of discarded cameras/lights by detaching them while
    # keeping their world transform. The chair source is a single mesh, but this
    # makes the loader safe for more elaborate future shared assets.
    for obj in imported:
        if obj.parent is not None and obj.parent not in imported_set:
            matrix_world = obj.matrix_world.copy()
            obj.parent = None
            obj.matrix_world = matrix_world

    for obj in loaded:
        if obj in imported_set:
            continue
        if obj.users == 0:
            bpy.data.objects.remove(obj)

    _repair_appended_image_paths(source_path, before_images)
    return imported


def _import_gltf_objects(source_path: Path) -> tuple[Any, ...]:
    before_objects = set(bpy.data.objects)
    result = bpy.ops.import_scene.gltf(filepath=str(source_path))
    if "FINISHED" not in result:
        raise RuntimeError(f"Blender could not import shared asset: {source_path}")

    imported = tuple(obj for obj in bpy.data.objects if obj not in before_objects)
    if not imported:
        raise RuntimeError(f"Shared asset imported no objects: {source_path}")
    return imported


def _object_bounds(objects: Sequence[Any]) -> tuple[float, float, float, float, float, float] | None:
    if Vector is None:
        return None

    points = []
    for obj in objects:
        if obj.type not in {"MESH", "CURVE", "SURFACE", "META", "FONT"}:
            continue
        try:
            points.extend(obj.matrix_world @ Vector(corner) for corner in obj.bound_box)
        except (AttributeError, TypeError):
            continue

    if not points:
        return None

    return (
        min(point.x for point in points),
        max(point.x for point in points),
        min(point.y for point in points),
        max(point.y for point in points),
        min(point.z for point in points),
        max(point.z for point in points),
    )


def _source_adjustments(metadata: Mapping[str, Any]) -> tuple[str | None, tuple[float, float, float]]:
    normalize_origin = metadata.get("normalize_origin")
    if normalize_origin is True:
        normalize_origin = "floor-center"
    if normalize_origin in (False, None, "none"):
        normalize_origin = None
    if normalize_origin not in (None, "floor-center"):
        raise ValueError("'normalize_origin' must be 'floor-center', true, false, or null.")

    source_rotation = _vector3(
        metadata.get("source_rotation_degrees", (0.0, 0.0, 0.0)),
        label="source_rotation_degrees",
    )
    return normalize_origin, source_rotation


def place_asset(
    *,
    assets_root: str | Path,
    asset_id: str | Path,
    collection: Any,
    name: str | None = None,
    location: Sequence[float] = (0.0, 0.0, 0.0),
    rotation_degrees: Sequence[float] = (0.0, 0.0, 0.0),
    scale: float | Sequence[float] = (1.0, 1.0, 1.0),
    file_name: str | None = None,
    child_name_prefix: str | None = None,
    extras: Mapping[str, Any] | None = None,
) -> PlacedAsset:
    """Load one shared source asset beneath a reusable placement root."""
    if bpy is None:
        raise RuntimeError("place_asset() must run inside Blender.")
    if collection is None:
        raise ValueError("A destination Blender collection is required.")

    source_path = resolve_asset_path(assets_root, asset_id, file_name=file_name)
    resolved_root = Path(assets_root).expanduser().resolve()
    metadata = _read_metadata(source_path.parent)

    asset_key = str(asset_id).replace("\\", "/")
    default_name = _safe_name(Path(asset_key).stem or Path(asset_key).name)
    root_name = name or default_name

    if source_path.suffix.lower() == ".blend":
        imported = _append_blend_objects(source_path, metadata)
    else:
        imported = _import_gltf_objects(source_path)

    imported_set = set(imported)
    prefix = child_name_prefix
    if prefix is None:
        prefix = f"{_safe_name(root_name)}__"

    for obj in imported:
        if prefix:
            obj.name = f"{prefix}{obj.name}"
        _move_to_collection(obj, collection)

    placement_root = bpy.data.objects.new(root_name, None)
    collection.objects.link(placement_root)
    placement_root.empty_display_type = "PLAIN_AXES"
    placement_root.empty_display_size = 0.18

    normalize_origin, source_rotation = _source_adjustments(metadata)
    needs_source_root = normalize_origin is not None or any(
        abs(value) > 1e-9 for value in source_rotation
    )

    parent_root = placement_root
    geometry_root = None
    if needs_source_root:
        alignment_root = bpy.data.objects.new(f"{root_name}__SourceAlignment", None)
        collection.objects.link(alignment_root)
        alignment_root.parent = placement_root
        alignment_root.rotation_euler = tuple(math.radians(value) for value in source_rotation)

        geometry_root = bpy.data.objects.new(f"{root_name}__SourceGeometry", None)
        collection.objects.link(geometry_root)
        geometry_root.parent = alignment_root
        parent_root = geometry_root

    # Parent only top-level imported objects. Existing internal hierarchy is
    # retained and world matrices are preserved before source correction.
    for obj in imported:
        if obj.parent not in imported_set:
            matrix_world = obj.matrix_world.copy()
            obj.parent = parent_root
            obj.matrix_world = matrix_world

    if normalize_origin == "floor-center" and geometry_root is not None:
        bounds = _object_bounds(imported)
        if bounds is None:
            raise RuntimeError(
                f"Could not calculate floor-centered bounds for shared asset: {source_path}"
            )
        min_x, max_x, min_y, max_y, min_z, _max_z = bounds
        geometry_root.location = (
            -((min_x + max_x) / 2.0),
            -((min_y + max_y) / 2.0),
            -min_z,
        )

    placement_root.location = _vector3(location, label="location")
    placement_root.rotation_euler = tuple(
        math.radians(value)
        for value in _vector3(rotation_degrees, label="rotation_degrees")
    )
    placement_root.scale = _vector3(scale, label="scale")

    placement_root["shared_asset"] = True
    placement_root["asset_id"] = asset_key
    placement_root["asset_format"] = source_path.suffix.lower().lstrip(".")
    if _inside(source_path, resolved_root):
        placement_root["asset_source"] = source_path.relative_to(resolved_root).as_posix()
    else:
        placement_root["asset_source"] = str(source_path)

    label = metadata.get("label")
    if isinstance(label, str) and label.strip():
        placement_root["asset_label"] = label.strip()

    for key, value in (extras or {}).items():
        placement_root[str(key)] = value

    print(
        f"Placed shared asset '{asset_key}' as '{placement_root.name}' "
        f"from {source_path}"
    )
    return PlacedAsset(
        asset_id=asset_key,
        source_path=source_path,
        root=placement_root,
        objects=imported,
    )
