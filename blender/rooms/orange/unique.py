"""Orange-room-only Blender objects.

The leather armchair is authored once as the shared asset
``blender/assets/leather-armchair/leather-armchair.glb`` and published to
``public/scenes/assets/leather-armchair/leather-armchair.glb`` with
``npm run assets:sync``.

It is placed in the room's interactive collection rather than baked into the
panorama. This keeps the chair as real GLB geometry in the browser and avoids a
second, baked copy appearing behind it. The chair is intentionally not marked
as grabbable yet.
"""

from __future__ import annotations


# The room is 6.8 m wide and 10 m deep. The chair sits near the center of the
# back wall, with enough clearance behind it, and rotates 180 degrees because
# the shared asset's authored front direction is +Y while the room camera is
# near the entry wall looking toward +Y.
ARMCHAIR_LOCATION = (0.0, 3.85, 0.0)
ARMCHAIR_ROTATION_DEGREES = (0.0, 0.0, 180.0)
ARMCHAIR_SCALE = 1.0


def add_static(context):
    """Add orange-room geometry that should be baked into the panorama."""
    pass


def add_interactive(context):
    """Place the reusable leather armchair in the live room GLB."""
    context.place_interactive_asset(
        "leather-armchair",
        name="OrangeRoomLeatherArmchair",
        grabbable=False,
        location=ARMCHAIR_LOCATION,
        rotation_degrees=ARMCHAIR_ROTATION_DEGREES,
        scale=ARMCHAIR_SCALE,
        extras={
            "category": "furniture/seating",
            "room": "orange",
        },
    )
