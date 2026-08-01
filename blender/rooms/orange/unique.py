"""Orange-room-only Blender objects.

The ornate chess chair is authored once as the shared source asset at
``blender/assets/chair/chair.blend``. Room and hall builders append that same
source through ``blender/shared/asset_library.py`` so its geometry, materials,
and textures never need to be copied into individual ``unique.py`` files.

It is placed in the room's interactive collection rather than baked into the
panorama. This keeps the chair as real GLB geometry in the browser and avoids a
second baked copy appearing behind it. The chair is intentionally not marked
as grabbable yet.
"""

from __future__ import annotations


# The room is 3.99 m wide and 5.70 m deep. The chair sits near the center of the
# back wall. The shared asset is normalized to face +Y, so it rotates 180 degrees
# here to face the entry-side camera.
CHAIR_LOCATION = (0.0, 1.85, 0.0)
CHAIR_ROTATION_DEGREES = (0.0, 0.0, 180.0)
CHAIR_SCALE = 1.0


def add_static(context):
    """Add orange-room geometry that should be baked into the panorama."""
    pass


def add_interactive(context):
    """Place the reusable ornate chess chair in the live room GLB."""
    context.place_interactive_asset(
        "chair",
        name="OrangeRoomChessChair",
        grabbable=False,
        location=CHAIR_LOCATION,
        rotation_degrees=CHAIR_ROTATION_DEGREES,
        scale=CHAIR_SCALE,
        extras={
            "category": "furniture/seating",
            "role": "chess-chair",
            "room": "orange",
        },
    )
