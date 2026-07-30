"""Museum-only objects.

The museum uses the canonical shared hall shell with the doorway on the left.
Only objects created here are exported to museum-objects.glb.
"""


def add_objects(context):
    """Add museum-specific display cases, artwork, benches, and props.

    Use context.objects_collection for every exported object. Parent related
    objects beneath context.objects_root, or beneath a root whose name begins
    with Grab_ when the object should be draggable on the website.
    """
    pass
