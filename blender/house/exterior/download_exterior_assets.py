"""
Download the professional CC0 assets used by the house exterior.

Target: Blender 5.2.0 LTS
No third-party Python packages required.

Source: Poly Haven
License: CC0 for the downloaded assets.

The build uses Poly Haven's public API only at asset-install time. Assets are
cached locally under blender/assets/exterior/polyhaven, so normal rendering and
the website never depend on the network.

Chosen assets
-------------
tree_small_02             realistic broadleaf framing tree
grass_bermuda_01          efficient realistic lawn/grass patch
shrub_04                  compact leafy shrub
shrub_sorrel_01           tiny pink-flowered ground cover
concrete_floor_01         PBR path/stone surface
kloppenheim_01_puresky    calm low-contrast pure-sky HDRI

The downloader deliberately requests 1K model textures and a 2K HDRI/PBR path
texture. At website render size this is enough, while keeping the local asset
cache reasonable.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[2]
ASSET_ROOT = PROJECT_ROOT / "blender" / "assets" / "exterior" / "polyhaven"
USER_AGENT = "hecate946-exterior-builder/2.0"
API_ROOT = "https://api.polyhaven.com"


@dataclass(frozen=True)
class AssetSpec:
    asset_id: str
    kind: str
    resolution: str


ASSETS = (
    AssetSpec("tree_small_02", "model", "1k"),
    AssetSpec("grass_bermuda_01", "model", "1k"),
    AssetSpec("shrub_04", "model", "1k"),
    AssetSpec("shrub_sorrel_01", "model", "1k"),
    AssetSpec("concrete_floor_01", "texture", "2k"),
    AssetSpec("kloppenheim_01_puresky", "hdri", "2k"),
)


def request_json(url: str) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=90) as response:
        return json.load(response)


def flatten_manifest(
    value: Any,
    path: tuple[str, ...] = (),
) -> list[tuple[tuple[str, ...], dict[str, Any]]]:
    result: list[tuple[tuple[str, ...], dict[str, Any]]] = []

    if isinstance(value, dict):
        if isinstance(value.get("url"), str):
            result.append((path, value))
        for key, child in value.items():
            result.extend(flatten_manifest(child, path + (str(key),)))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            result.extend(flatten_manifest(child, path + (str(index),)))

    return result


def extension_of(url: str) -> str:
    return Path(urllib.parse.urlparse(url).path).suffix.lower()


def searchable(path: tuple[str, ...], entry: dict[str, Any]) -> str:
    return " ".join(path).lower() + " " + str(entry.get("url", "")).lower()


def choose_best(
    entries: list[tuple[tuple[str, ...], dict[str, Any]]],
    *,
    extensions: tuple[str, ...],
    wanted: tuple[str, ...],
    preferred_resolution: str,
) -> tuple[tuple[str, ...], dict[str, Any]] | None:
    candidates = []
    for path, entry in entries:
        url = entry.get("url")
        if not isinstance(url, str):
            continue
        ext = extension_of(url)
        if ext not in extensions:
            continue

        hay = searchable(path, entry)
        score = 0
        if preferred_resolution in hay:
            score += 100
        elif "1k" in hay or "2k" in hay:
            score += 35

        for token in wanted:
            if token in hay:
                score += 35

        # Prefer jpg for color/roughness maps; png remains useful for alpha.
        if ext == ".jpg":
            score += 5
        if ext == ".hdr":
            score += 10
        candidates.append((score, path, entry))

    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0], reverse=True)
    _, path, entry = candidates[0]
    return path, entry


def md5(path: Path) -> str:
    h = hashlib.md5()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def download_entry(
    entry: dict[str, Any],
    destination: Path,
    *,
    force: bool,
) -> Path:
    url = entry["url"]
    expected_md5 = str(entry.get("md5", "")).lower().strip()

    if destination.exists() and not force:
        if expected_md5 and md5(destination) == expected_md5:
            print(f"cached  {destination.relative_to(PROJECT_ROOT)}")
            return destination
        if not expected_md5:
            print(f"cached  {destination.relative_to(PROJECT_ROOT)}")
            return destination

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".part")

    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    print(f"fetch   {url}")
    with urllib.request.urlopen(request, timeout=180) as response, temporary.open("wb") as out:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            out.write(chunk)

    temporary.replace(destination)

    if expected_md5:
        actual = md5(destination)
        if actual != expected_md5:
            destination.unlink(missing_ok=True)
            raise RuntimeError(
                f"Checksum mismatch for {destination.name}: "
                f"expected {expected_md5}, received {actual}"
            )

    print(f"saved   {destination.relative_to(PROJECT_ROOT)}")
    return destination


def basename_for(entry: dict[str, Any]) -> str:
    url_path = urllib.parse.urlparse(entry["url"]).path
    return urllib.parse.unquote(Path(url_path).name)


def download_hdri(spec: AssetSpec, entries, out_dir: Path, force: bool) -> dict:
    selected = choose_best(
        entries,
        extensions=(".hdr", ".exr"),
        wanted=("hdri",),
        preferred_resolution=spec.resolution,
    )
    if selected is None:
        raise RuntimeError(f"No HDRI file found for {spec.asset_id}")

    _, entry = selected
    local = download_entry(entry, out_dir / basename_for(entry), force=force)
    return {"environment": str(local.relative_to(PROJECT_ROOT))}


def download_texture(spec: AssetSpec, entries, out_dir: Path, force: bool) -> dict:
    channels = {
        "diffuse": ("diff", "diffuse", "albedo"),
        "normal": ("nor_gl", "normal gl", "normal"),
        "roughness": ("rough", "roughness"),
        "displacement": ("disp", "displacement", "height"),
    }

    result = {}
    for channel, tokens in channels.items():
        selected = choose_best(
            entries,
            extensions=(".jpg", ".png", ".exr"),
            wanted=tokens,
            preferred_resolution=spec.resolution,
        )
        if selected is None:
            continue
        _, entry = selected
        local = download_entry(entry, out_dir / basename_for(entry), force=force)
        result[channel] = str(local.relative_to(PROJECT_ROOT))

    if "diffuse" not in result:
        raise RuntimeError(f"No diffuse map found for {spec.asset_id}")
    return result


def download_model(spec: AssetSpec, entries, out_dir: Path, force: bool) -> dict:
    blend = choose_best(
        entries,
        extensions=(".blend",),
        wanted=("blend",),
        preferred_resolution=spec.resolution,
    )
    if blend is None:
        raise RuntimeError(f"No Blender model file found for {spec.asset_id}")

    _, blend_entry = blend
    blend_local = download_entry(
        blend_entry,
        out_dir / basename_for(blend_entry),
        force=force,
    )

    # Download the model's 1K texture dependencies. Blender files from asset
    # libraries often retain their original relative image paths; the builder
    # relinks them by basename after append, so a flat local cache is sufficient.
    dependency_files = []
    seen_urls = set()

    for path, entry in entries:
        url = entry.get("url")
        if not isinstance(url, str) or url in seen_urls:
            continue

        ext = extension_of(url)
        if ext not in (".jpg", ".png"):
            continue

        hay = searchable(path, entry)
        if spec.resolution not in hay:
            continue

        seen_urls.add(url)
        local = download_entry(entry, out_dir / basename_for(entry), force=force)
        dependency_files.append(str(local.relative_to(PROJECT_ROOT)))

    return {
        "blend": str(blend_local.relative_to(PROJECT_ROOT)),
        "dependencies": dependency_files,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    ASSET_ROOT.mkdir(parents=True, exist_ok=True)
    local_manifest = {
        "source": "Poly Haven",
        "license": "CC0",
        "user_agent": USER_AGENT,
        "assets": {},
    }

    for spec in ASSETS:
        print(f"\n[{spec.asset_id}]")
        manifest = request_json(f"{API_ROOT}/files/{spec.asset_id}")
        entries = flatten_manifest(manifest)
        out_dir = ASSET_ROOT / spec.asset_id
        out_dir.mkdir(parents=True, exist_ok=True)

        if spec.kind == "model":
            resolved = download_model(spec, entries, out_dir, args.force)
        elif spec.kind == "texture":
            resolved = download_texture(spec, entries, out_dir, args.force)
        elif spec.kind == "hdri":
            resolved = download_hdri(spec, entries, out_dir, args.force)
        else:
            raise RuntimeError(f"Unknown asset kind: {spec.kind}")

        local_manifest["assets"][spec.asset_id] = {
            "kind": spec.kind,
            "resolution": spec.resolution,
            **resolved,
        }

    manifest_path = ASSET_ROOT / "manifest.local.json"
    manifest_path.write_text(json.dumps(local_manifest, indent=2) + "\n")
    print(f"\nAsset manifest: {manifest_path.relative_to(PROJECT_ROOT)}")
    print("All professional exterior assets are installed.")


if __name__ == "__main__":
    main()
