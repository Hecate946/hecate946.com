"""Build one or both first-story halls from one shared design.

Open this file in Blender's Scripting workspace and edit only the EASY SETTINGS
section for normal use.
"""

from pathlib import Path
import importlib
import importlib.util
import runpy
import sys

import bpy


# =============================================================================
# EASY SETTINGS
# =============================================================================
# "MUSEUM", "BALLROOM", or "ALL"
HALL_TO_BUILD = globals().get("HALL_TO_BUILD", "BALLROOM")

# True renders a panorama preview immediately. False builds/saves/exports
# without waiting for the Cycles panorama render.
AUTO_RENDER_PANORAMA = globals().get("AUTO_RENDER_PANORAMA", True)

# "FAST", "SLOW", or "CRISP"
RENDER_QUALITY = globals().get("RENDER_QUALITY", "FAST")

# True requests Cycles GPU Compute. Enable the GPU once in:
# Edit > Preferences > System > Cycles Render Devices.
USE_GPU = globals().get("USE_GPU", True)


QUALITY_PRESETS = {
    "FAST": {
        "width": 2048,
        "height": 1024,
        "samples": 32,
    },
    "SLOW": {
        "width": 4096,
        "height": 2048,
        "samples": 128,
    },
    "CRISP": {
        "width": 6144,
        "height": 3072,
        "samples": 48,
    },
}


def script_directory() -> Path:
    """Resolve the actual directory containing this external Python file."""
    try:
        text = bpy.context.space_data.text
        if text and text.filepath:
            path = Path(bpy.path.abspath(text.filepath)).resolve()
            if path.suffix.lower() == ".py":
                return path.parent
    except (AttributeError, RuntimeError):
        pass

    try:
        path = Path(__file__).resolve()
        if path.suffix.lower() == ".py":
            return path.parent
    except NameError:
        pass

    if bpy.data.filepath:
        blend_directory = Path(bpy.data.filepath).resolve().parent
        for candidate in (blend_directory, *blend_directory.parents):
            if (
                (candidate / "build_halls.py").is_file()
                and (candidate / "shared" / "hall_shell.py").is_file()
            ):
                return candidate

    cwd = Path.cwd().resolve()
    for candidate in (cwd, *cwd.parents):
        if (
            (candidate / "build_halls.py").is_file()
            and (candidate / "shared" / "hall_shell.py").is_file()
        ):
            return candidate

    fallback = (
        Path.home()
        / "Desktop"
        / "projects"
        / "hecate946.com"
        / "blender"
        / "halls"
    )
    if (
        (fallback / "build_halls.py").is_file()
        and (fallback / "shared" / "hall_shell.py").is_file()
    ):
        return fallback.resolve()

    raise FileNotFoundError(
        "Could not find blender/halls. Open build_halls.py from the project or "
        "run Blender from the repository root."
    )


def load_live_hall_builder(builder_file: Path):
    """Force-load the shared hall builder fresh from disk every run."""
    module_name = "hecate_hall_builder_live"

    importlib.invalidate_caches()
    sys.modules.pop(module_name, None)

    try:
        pyc_path = Path(importlib.util.cache_from_source(str(builder_file)))
        if pyc_path.exists():
            pyc_path.unlink()
    except Exception:
        pass

    spec = importlib.util.spec_from_file_location(module_name, builder_file)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load shared hall builder: {builder_file}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


HALLS_ROOT = script_directory()
if str(HALLS_ROOT) not in sys.path:
    sys.path.insert(0, str(HALLS_ROOT))

# The ballroom has migrated to the authored 2.5D rendered-world pipeline. Keep
# this familiar entry point useful without allowing it to rebuild the retired
# shared-shell ballroom by accident.
requested_selection = str(HALL_TO_BUILD).strip().upper()
if requested_selection in {"BALLROOM", "ALL"}:
    ballroom_builder = HALLS_ROOT / "ballroom" / "build_ballroom_25d.py"
    print(f"Building current 2.5D ballroom from: {ballroom_builder}")
    ballroom_quality = {"FAST": "PREVIEW", "SLOW": "WEB", "CRISP": "FINAL"}.get(
        str(RENDER_QUALITY).strip().upper(),
        "WEB",
    )
    runpy.run_path(
        str(ballroom_builder),
        run_name="__main__",
        init_globals={
            "QUALITY": ballroom_quality,
            "AUTO_RENDER": bool(AUTO_RENDER_PANORAMA),
            "USE_GPU": bool(USE_GPU),
        },
    )
    if requested_selection == "BALLROOM":
        raise SystemExit(0)
    HALL_TO_BUILD = "MUSEUM"

builder_file = HALLS_ROOT / "shared" / "hall_shell.py"
hall_builder = load_live_hall_builder(builder_file)

HallDefinition = hall_builder.HallDefinition
RenderSettings = hall_builder.RenderSettings
build_halls = hall_builder.build_halls

print(f"Loaded hall builder from: {builder_file.resolve()}")
print(f"Hall builder version:    {hall_builder.HALL_BUILDER_VERSION}")
print(f"Shared asset directory:  {(HALLS_ROOT.parent / 'assets').resolve()}")


HALLS = (
    # The canonical shared shell has its doorway on the left.
    HallDefinition("museum", "The Museum", False),
    # The website and Blender preview mirror only the shell for the ballroom.
    HallDefinition("ballroom", "The Ballroom", True),
)

quality_name = str(RENDER_QUALITY).strip().upper()
if quality_name not in QUALITY_PRESETS:
    raise ValueError('RENDER_QUALITY must be "FAST", "SLOW", or "CRISP".')

quality = QUALITY_PRESETS[quality_name]
render_settings = RenderSettings(
    width=quality["width"],
    height=quality["height"],
    samples=quality["samples"],
    use_gpu=bool(USE_GPU),
    auto_render=bool(AUTO_RENDER_PANORAMA),
)

selection = str(HALL_TO_BUILD).strip().lower()
if selection == "all":
    halls_to_build = HALLS
else:
    halls_to_build = tuple(hall for hall in HALLS if hall.slug == selection)
    if not halls_to_build:
        valid = ", ".join(hall.slug.upper() for hall in HALLS)
        raise ValueError(f"HALL_TO_BUILD must be {valid}, or ALL.")

print("=" * 72)
print("Two-hall builder")
print(f"Halls:          {', '.join(hall.slug for hall in halls_to_build)}")
print(f"Quality:        {quality_name}")
print(f"Resolution:     {render_settings.width} x {render_settings.height}")
print(f"Cycles samples: {render_settings.samples}")
print(f"Auto render:    {render_settings.auto_render}")
print(f"Cycles device:  {'GPU' if render_settings.use_gpu else 'CPU'}")
print("=" * 72)

build_halls(halls_to_build, render_settings, HALLS_ROOT)
