"""Ballroom-only objects.

The shared hall shell is never duplicated here. The Blender preview mirrors
that shared shell on X so objects can be authored exactly where they will
appear on the website. Only this file's objects are exported to
ballroom-objects.glb.
"""


def add_objects(context):
    """Add ballroom-specific furniture, sculptures, instruments, and props.

    Use context.objects_collection for every exported object. Parent related
    objects beneath context.objects_root, or beneath a root whose name begins
    with Grab_ when the object should be draggable on the website.

    Example:
        gold = context.material(
            "Ballroom gold",
            context.linear_hex("#B79A5D"),
            roughness=0.24,
            metallic=0.35,
        )
        context.add_box(
            "Ballroom_Platform",
            (0.0, 2.7, 0.12),
            (4.8, 2.2, 0.24),
            gold,
            context.objects_collection,
            bevel=0.04,
            parent=context.objects_root,
        )
    """
    pass
