"""Compatibility entry point for building the museum assets.

The architectural source lives in ../shared/hall_shell.py. Run this file when
only the shared shell and museum object file should be rebuilt.
"""

from pathlib import Path
import runpy

import bpy


# Set this to an absolute blender/halls path only if the repository is moved.
HALLS_ROOT_OVERRIDE = None


def find_halls_root() -> Path:
    candidates = []

    if HALLS_ROOT_OVERRIDE:
        candidates.append(Path(HALLS_ROOT_OVERRIDE).expanduser())

    try:
        text = bpy.context.space_data.text
        if text and text.filepath:
            value = text.filepath
            if value.startswith("//"):
                value = bpy.path.abspath(value)
            folder = Path(value).expanduser().parent
            candidates.extend((folder, folder.parent, folder.parent.parent))
    except (AttributeError, RuntimeError):
        pass

    try:
        value = str(__file__)
        if value.startswith("//"):
            value = bpy.path.abspath(value)
        folder = Path(value).expanduser().parent
        candidates.extend((folder, folder.parent, folder.parent.parent))
    except NameError:
        pass

    candidates.append(
        Path.home()
        / "Desktop"
        / "projects"
        / "hecate946.com"
        / "blender"
        / "halls"
    )

    for candidate in candidates:
        candidate = candidate.resolve()
        if (
            (candidate / "build_halls.py").is_file()
            and (candidate / "shared" / "hall_shell.py").is_file()
        ):
            return candidate

    raise FileNotFoundError(
        "Could not find blender/halls. Set HALLS_ROOT_OVERRIDE in this file."
    )


HALLS_ROOT = find_halls_root()
runpy.run_path(
    str(HALLS_ROOT / "build_halls.py"),
    run_name="__main__",
    init_globals={
        "HALL_TO_BUILD": "MUSEUM",
        "REBUILD_SHARED_SHELL": True,
        "HALLS_ROOT_OVERRIDE": str(HALLS_ROOT),
    },
)
