"""Convention-based reusable GLB asset placement for the Blender project.

Room and hall builders consume published shared object files beneath
``public/scenes/assets``. The recommended project layout is::

    blender/assets/chair/chair.blend       # editable master source
    blender/assets/chair/chair.py          # optional procedural generator
    blender/assets/chair/chair.glb          # generated staging artifact
    public/scenes/assets/chair/chair.glb    # published copy consumed by builders

Run ``npm run assets:sync`` after exporting or updating a reusable GLB. Room and
hall builders can then place the same published asset at any transform without
copying its geometry code into each space-specific ``unique.py`` file.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import math
import re
from typing import Any, Iterable, Mapping, Sequence

try:
    import bpy
except ModuleNotFoundError:  # Allows path-resolution tests outside Blender.
    bpy = None


SUPPORTED_ASSET_EXTENSIONS = (".glb", ".gltf")


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


def resolve_asset_path(
    assets_root: str | Path,
    asset_id: str | Path,
    *,
    file_name: str | None = None,
) -> Path:
    """Resolve an asset ID to a GLB/glTF file using project conventions.

    ``chair`` resolves primarily to ``<assets_root>/chair/chair.glb`` where
    ``assets_root`` is normally ``public/scenes/assets``. Nested IDs such as
    ``furniture/chair`` are also supported. A direct GLB path can be supplied
    when an exceptional asset does not follow convention.
    """
    root = Path(assets_root).expanduser().resolve()
    requested = Path(asset_id).expanduser()
    candidates: list[Path] = []

    if requested.suffix.lower() in SUPPORTED_ASSET_EXTENSIONS:
        candidates.append(requested if requested.is_absolute() else root / requested)
    else:
        asset_folder = root / requested
        leaf_name = requested.name
        if file_name:
            candidates.append(asset_folder / file_name)
        candidates.extend(
            [
                asset_folder / f"{leaf_name}.glb",
                asset_folder / f"{leaf_name}.gltf",
                asset_folder / "asset.glb",
                asset_folder / "asset.gltf",
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
    raise FileNotFoundError(
        f"Shared Blender asset '{asset_id}' was not found.\n"
        f"Expected the normal layout: {root / str(asset_id) / (Path(str(asset_id)).name + '.glb')}\n"
        f"Checked:\n  - {checked_text}"
    )


def _move_to_collection(obj: Any, collection: Any) -> None:
    for old_collection in list(obj.users_collection):
        old_collection.objects.unlink(obj)
    collection.objects.link(obj)


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
    """Import one shared GLB and place it under a transform root.

    The asset should be authored around world origin, with its floor contact at
    Z=0 and its forward direction documented consistently (the project uses +Y).
    The generated root owns the room-specific position, Euler rotation in
    degrees, and scale, while preserving the asset's internal hierarchy.
    """
    if bpy is None:
        raise RuntimeError("place_asset() must run inside Blender.")
    if collection is None:
        raise ValueError("A destination Blender collection is required.")

    source_path = resolve_asset_path(assets_root, asset_id, file_name=file_name)
    resolved_root = Path(assets_root).expanduser().resolve()
    asset_key = str(asset_id).replace("\\", "/")
    default_name = _safe_name(Path(asset_key).stem or Path(asset_key).name)
    root_name = name or default_name

    before_objects = set(bpy.data.objects)
    result = bpy.ops.import_scene.gltf(filepath=str(source_path))
    if "FINISHED" not in result:
        raise RuntimeError(f"Blender could not import shared asset: {source_path}")

    imported = tuple(obj for obj in bpy.data.objects if obj not in before_objects)
    if not imported:
        raise RuntimeError(f"Shared asset imported no objects: {source_path}")

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

    # Parent only top-level imported objects. Existing internal GLB parenting is
    # retained, and world matrices are preserved before applying the placement.
    for obj in imported:
        if obj.parent not in imported_set:
            matrix_world = obj.matrix_world.copy()
            obj.parent = placement_root
            obj.matrix_world = matrix_world

    placement_root.location = _vector3(location, label="location")
    placement_root.rotation_euler = tuple(
        math.radians(value)
        for value in _vector3(rotation_degrees, label="rotation_degrees")
    )
    placement_root.scale = _vector3(scale, label="scale")

    placement_root["shared_asset"] = True
    placement_root["asset_id"] = asset_key
    if _inside(source_path, resolved_root):
        placement_root["asset_source"] = source_path.relative_to(resolved_root).as_posix()
    else:
        placement_root["asset_source"] = str(source_path)

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
