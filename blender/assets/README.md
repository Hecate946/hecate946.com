# Shared Blender assets

Use this folder for editable object sources that can appear in more than one
room or hall. Blender builders load these assets directly from
`blender/assets`; room- and hall-specific files only provide placement
transforms.

## Folder convention

```text
blender/assets/
  chair/
    asset.json
    chair.blend
    textures/
      ...
    chair.glb       # optional export/staging artifact
```

A shared asset can be a `.blend`, `.glb`, or `.gltf`. The resolver prefers the
file named by `asset.json`, then conventional names such as `chair.blend` and
`chair.glb`.

## Asset metadata

`asset.json` lets the loader standardize a downloaded model without modifying
its mesh destructively:

```json
{
  "label": "Ornate green chess chair",
  "source": "chair.blend",
  "normalize_origin": "floor-center",
  "source_rotation_degrees": [0, 0, 180]
}
```

`normalize_origin: "floor-center"` centers the object's footprint on X/Y and
places its lowest rendered point at Z=0. `source_rotation_degrees` corrects the
source model so the shared project convention remains **front = +Y**.

Relative image paths inside appended `.blend` files are resolved against the
asset folder automatically, so a `textures/` directory can remain beside the
master source.

## Placement

Room hooks use the shared source by asset ID:

```python
def add_interactive(context):
    context.place_interactive_asset(
        "chair",
        name="OrangeRoomChessChair",
        location=(0.0, 1.85, 0.0),
        rotation_degrees=(0.0, 0.0, 180.0),
    )
```

Hall hooks use `context.place_asset(...)` in the same way. The loader creates a
placement root that owns the room/hall transform while preserving the asset's
internal hierarchy and materials.

## Optional standalone GLB publishing

When an asset also has a standalone GLB beneath `blender/assets`, publish it to
the matching website path with:

```bash
npm run assets:sync
```

For example:

```text
blender/assets/chair/chair.glb
    -> public/scenes/assets/chair/chair.glb
```

Room and hall builds do not require this standalone public copy; they embed the
shared source into their generated room/hall GLBs.
