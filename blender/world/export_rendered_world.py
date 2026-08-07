"""Export camera-space hotspots from a Blender scene for the rendered website world.

The visual scene remains authored in Blender. Interaction regions are ordinary
non-rendering Blender objects with a ``world_hotspot_id`` custom property.
Their projected camera bounds are written to ``blender/world/build/<view>.json``.

Typical direct use:
    blender --background blender/house/house.blend \\
      --python blender/world/export_rendered_world.py -- --view exterior

Normally use ``npm run world:render -- exterior`` instead; it runs the scene's
build script first, exports metadata, and publishes the result to /public.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

PROJECT_ROOT = Path(__file__).resolve().parents[2]
WORLD_FILE = PROJECT_ROOT / "src" / "content" / "site-world.json"
BUILD_ROOT = PROJECT_ROOT / "blender" / "world" / "build"


def parse_args() -> argparse.Namespace:
    argv = sys.argv
    argv = argv[argv.index("--") + 1 :] if "--" in argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--view", required=True)
    return parser.parse_args(argv)


def load_world() -> dict:
    return json.loads(WORLD_FILE.read_text())


def view_config(world: dict, view_id: str) -> dict:
    for view in world.get("views", []):
        if view.get("id") == view_id:
            return view
    raise RuntimeError(f"Unknown world view: {view_id}")


def camera_for(view: dict) -> bpy.types.Object:
    configured = view.get("blender", {}).get("camera")
    if configured and configured in bpy.data.objects:
        camera = bpy.data.objects[configured]
        if camera.type == "CAMERA":
            return camera
    for obj in bpy.data.objects:
        if obj.type == "CAMERA" and obj.get("world_view_id") == view.get("id"):
            return obj
    if bpy.context.scene.camera is not None:
        return bpy.context.scene.camera
    raise RuntimeError(f"No camera found for world view {view.get('id')}")


def projected_bounds(scene: bpy.types.Scene, camera: bpy.types.Object, obj: bpy.types.Object) -> dict | None:
    points = []
    for corner in obj.bound_box:
        world_corner = obj.matrix_world @ Vector(corner)
        point = world_to_camera_view(scene, camera, world_corner)
        if point.z <= 0:
            continue
        points.append(point)
    if not points:
        return None

    xs = [min(1.0, max(0.0, p.x)) for p in points]
    # Blender's normalized camera y increases upward; CSS y increases downward.
    ys = [min(1.0, max(0.0, 1.0 - p.y)) for p in points]
    left, right = min(xs), max(xs)
    top, bottom = min(ys), max(ys)
    if right <= left or bottom <= top:
        return None
    return {
        "x": round(left, 6),
        "y": round(top, 6),
        "width": round(right - left, 6),
        "height": round(bottom - top, 6),
    }


def export_view(view: dict) -> Path:
    scene = bpy.context.scene
    camera = camera_for(view)
    scene.camera = camera

    hotspots_by_id = {hotspot.get("id"): hotspot for hotspot in view.get("hotspots", [])}
    exported = []
    for obj in bpy.data.objects:
        hotspot_id = obj.get("world_hotspot_id")
        if not hotspot_id:
            continue
        source = hotspots_by_id.get(str(hotspot_id))
        if source is None:
            print(f"Ignoring Blender hotspot not present in site-world.json: {hotspot_id}")
            continue
        bounds = projected_bounds(scene, camera, obj)
        if bounds is None:
            print(f"Hotspot is outside camera view: {hotspot_id}")
            continue
        exported.append({"id": hotspot_id, "bounds": bounds})

    BUILD_ROOT.mkdir(parents=True, exist_ok=True)
    output = BUILD_ROOT / f"{view['id']}.json"
    output.write_text(
        json.dumps(
            {
                "version": 1,
                "view": view["id"],
                "camera": camera.name,
                "hotspots": exported,
            },
            indent=2,
        )
        + "\n"
    )
    print(f"Exported {len(exported)} hotspot(s) -> {output}")
    return output


def main() -> None:
    args = parse_args()
    world = load_world()
    export_view(view_config(world, args.view))


if __name__ == "__main__":
    main()
