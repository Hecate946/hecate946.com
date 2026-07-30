# Shared Blender assets

Use this folder for editable or procedural sources for objects that can appear
in more than one room or hall. Blender room and hall builders intentionally do
**not** import the GLBs from this source folder. They consume the published
copies under `public/scenes/assets`.

## Folder convention

```text
blender/assets/
  chair/
    chair.blend   # editable master source
    chair.py      # optional procedural source
    chair.glb     # generated staging artifact

public/scenes/assets/
  chair/
    chair.glb     # published copy consumed by room and hall builders
```

Author each asset around `(0, 0, 0)`, place its floor contact at `Z = 0`, use
meters, and make its front face `+Y`. Apply Rotation & Scale before exporting.

After creating or changing any shared GLB, publish all shared assets with:

```bash
npm run assets:sync
```

The sync script recursively copies every `blender/assets/**/*.glb` file to the
matching path beneath `public/scenes/assets`. For example:

```text
blender/assets/chair/chair.glb
    -> public/scenes/assets/chair/chair.glb
```

The room context then resolves `"chair"` to the public copy:

```python
def add_static(context):
    context.place_static_asset(
        "chair",
        name="GreenReadingChair",
        location=(-1.4, 2.6, 0.0),
        rotation_degrees=(0.0, 0.0, 35.0),
    )
```

For a browser-side object, use `place_interactive_asset`. Set `grabbable=True`
to give the exported root the required `Grab_` prefix automatically.

Keep the `.blend` or `.py` source under version control. The GLB beneath
`blender/assets` is the export/staging file, while the synchronized public GLB
is the canonical file consumed by the scene builders.
