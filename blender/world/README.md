# Rendered world pipeline

The website treats Blender as an authoring tool and the browser as a very small
2D viewer. Blender owns composition, lighting, cameras, and interaction regions.
The browser only displays rendered images and the hotspot rectangles exported
from the active camera.

## Naming / metadata

A camera may set `world_view_id = "exterior"`.
A non-rendering object may set `world_hotspot_id = "about"`.

`blender/house/house.py` creates these metadata objects automatically for the
existing house. For future rooms, add simple cubes or planes around clickable
objects and assign the same custom property.

The semantic destination, label, and relationship live in exactly one file:

    src/content/site-world.json

The website graph also uses that file for parent relationships.

## One-command workflow

    npm run world:render -- exterior

That command:

1. runs the view's Blender build script when configured;
2. opens the generated `.blend` file;
3. projects hotspot object bounds through the configured camera;
4. writes `blender/world/build/exterior.json`;
5. publishes the rendered image and generated manifest into `public/scenes/world/`.

During normal frontend development you do not need Blender. The checked-in
manifest contains bootstrap bounds and falls back to the existing house render.
