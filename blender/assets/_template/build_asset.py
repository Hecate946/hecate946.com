"""Template for a reusable procedural Blender asset.

Copy this folder to ``blender/assets/<asset-id>``, rename this file if desired,
and replace ``build_asset`` with the actual object-generation code. Running the
script in Blender saves the editable ``<asset-id>.blend`` source and exports an
optional standalone ``<asset-id>.glb`` beside it. Room and hall builders load
from ``blender/assets`` directly. Run ``npm run assets:sync`` only when the
standalone GLB should also be published beneath ``public/scenes/assets``.
"""

from __future__ import annotations

from pathlib import Path

import bpy


ASSET_ID = "replace-me"


def script_directory() -> Path:
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


def build_asset() -> None:
    """Replace this sample cube with the reusable asset's real geometry."""
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0.0, 0.0, 0.5))
    bpy.context.object.name = ASSET_ID


def export_asset(output_file: Path) -> None:
    result = bpy.ops.export_scene.gltf(
        filepath=str(output_file),
        export_format="GLB",
        export_apply=True,
        export_cameras=False,
        export_lights=True,
        export_extras=True,
    )
    if "FINISHED" not in result:
        raise RuntimeError(f"GLB export failed: {result}")


def main() -> None:
    output_directory = script_directory()
    output_directory.mkdir(parents=True, exist_ok=True)
    output_file = output_directory / f"{ASSET_ID}.glb"

    clear_scene()
    build_asset()
    export_asset(output_file)
    bpy.ops.wm.save_as_mainfile(
        filepath=str(output_directory / f"{ASSET_ID}.blend")
    )
    print(f"Reusable asset exported to: {output_file}")
    print("Optional: run `npm run assets:sync` to publish the standalone GLB.")


if __name__ == "__main__":
    main()
