"""Unique Blender additions for the purple room.

The shared builder calls add_static() before the Cycles panorama render and
add_interactive() before the lightweight interactive GLB export.
"""


def add_static(context):
    """Add permanent room-specific objects that should appear in the panorama.

    Example:
        accent = context.material(
            "Purple accent",
            context.linear_hex("#FFFFFF"),
            roughness=0.4,
        )
        context.add_box(
            "Purple shelf",
            (0.0, 4.6, 1.2),
            (2.0, 0.25, 0.12),
            accent,
            context.static_collection,
            bevel=0.03,
        )
    """
    pass


def add_interactive(context):
    """Add movable objects exported to the room's interactive GLB.

    Name a grabbable root with the prefix Grab_, such as Grab_PurpleBook.
    """
    pass
