"""Build one or all five second-story rooms from one shared design.

Open this file in Blender's Scripting workspace and edit only the EASY SETTINGS
section for normal use.
"""

from pathlib import Path
import sys

import bpy


# =============================================================================
# EASY SETTINGS
# =============================================================================
# "RED", "GREEN", "ORANGE", "BLUE", "PURPLE", or "ALL"
ROOM_TO_BUILD = "GREEN"

# True renders the panorama immediately. False builds/saves/exports without
# waiting for the Cycles panorama render.
AUTO_RENDER_PANORAMA = False

# "FAST", "SLOW", or "CRISP"
RENDER_QUALITY = "FAST"

# True requests Cycles GPU Compute. Enable the GPU once in:
# Edit > Preferences > System > Cycles Render Devices.
USE_GPU = True


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
        return Path(bpy.data.filepath).resolve().parent

    return Path.cwd().resolve()


ROOMS_ROOT = script_directory()
if str(ROOMS_ROOT) not in sys.path:
    sys.path.insert(0, str(ROOMS_ROOT))

from shared.room_builder import RoomDefinition, RenderSettings, build_room


ROOMS = (
    RoomDefinition("red", "The Red Room", "Room 001", "#4A1F24"),
    RoomDefinition("green", "The Green Room", "Room 002", "#1C3A2F"),
    RoomDefinition("orange", "The Orange Room", "Room 003", "#5A2F18"),
    RoomDefinition("blue", "The Blue Room", "Room 004", "#18344C"),
    RoomDefinition("purple", "The Purple Room", "Room 005", "#35213F"),
)

quality_name = RENDER_QUALITY.strip().upper()
if quality_name not in QUALITY_PRESETS:
    raise ValueError('RENDER_QUALITY must be "FAST", "SLOW", or "CRISP".')

quality = QUALITY_PRESETS[quality_name]
render_settings = RenderSettings(
    width=quality["width"],
    height=quality["height"],
    samples=quality["samples"],
    use_gpu=USE_GPU,
    auto_render=AUTO_RENDER_PANORAMA,
)

selection = ROOM_TO_BUILD.strip().lower()
if selection == "all":
    rooms_to_build = ROOMS
else:
    rooms_to_build = tuple(room for room in ROOMS if room.slug == selection)
    if not rooms_to_build:
        valid = ", ".join(room.slug.upper() for room in ROOMS)
        raise ValueError(f"ROOM_TO_BUILD must be {valid}, or ALL.")

print("=" * 72)
print("Five-room builder")
print(f"Rooms:          {', '.join(room.slug for room in rooms_to_build)}")
print(f"Quality:        {quality_name}")
print(f"Resolution:     {render_settings.width} x {render_settings.height}")
print(f"Cycles samples: {render_settings.samples}")
print(f"Auto render:    {render_settings.auto_render}")
print(f"Cycles device:  {'GPU' if render_settings.use_gpu else 'CPU'}")
print("=" * 72)

for room in rooms_to_build:
    build_room(room, render_settings, ROOMS_ROOT)

print("All requested rooms finished.")
