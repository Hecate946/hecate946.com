"""Unique Blender additions for the orange room.

Reusable sources belong in ``blender/assets/<asset-id>`` and are published to
``public/scenes/assets/<asset-id>`` by ``npm run assets:sync``. They can be placed here
with room-specific transforms. The shared builder calls ``add_static`` before
the panorama render and ``add_interactive`` before interactive GLB export.
"""


def add_static(context):
    """Add permanent orange-room objects that are baked into the panorama.

    Example shared chair placement::

        context.place_static_asset(
            "chair",
            name="OrangeReadingChair",
            location=(-1.4, 2.6, 0.0),
            rotation_degrees=(0.0, 0.0, 35.0),
            scale=1.0,
        )

    The asset ID ``chair`` resolves to
    ``public/scenes/assets/chair/chair.glb``.
    """
    pass


def add_interactive(context):
    """Add browser-side orange-room objects to the interactive GLB.

    Example movable shared chair placement::

        context.place_interactive_asset(
            "chair",
            name="OrangeMovableChair",
            grabbable=True,
            location=(1.2, 2.1, 0.0),
            rotation_degrees=(0.0, 0.0, -25.0),
        )

    ``grabbable=True`` automatically prefixes the exported root with ``Grab_``.
    Interactive objects are hidden while the panorama renders, preventing a
    baked duplicate from remaining after the visitor moves the live object.
    """
    pass
