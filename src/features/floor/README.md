# Floor scene

`FloorScene.svelte` is the only owner of the room's WebGL renderer. The wall remains DOM/Svelte, while the floor and future spatial objects live in this scene.

## Coordinate contract

- At the wall/floor seam, one Three.js world unit projects to one CSS pixel. This keeps the 2D wall and 3D floor on the same horizontal coordinate system.
- `x` follows wall coordinates, `y` is height above the floor, and `z` starts at the wall and increases toward the viewer.
- `cameraX` is owned by the room/wall controller and passed to the floor imperatively. The floor never starts a competing animation loop.
- The WebGL canvas spans the room so objects may extend above the baseboard. The floor plane itself starts at the shared `--floor-seam-top` geometry boundary.

## Loading and failure behavior

Three.js is bundled with the floor island rather than dynamically imported after hydration, avoiding a second network/loading step before initialization. Server-rendered markup contains only a solid dark underlay below the floor seam; there is no legacy CSS checkerboard renderer. Once WebGL paints, the real 3D floor appears directly over that underlay. If WebGL is unavailable or the context is lost, the underlay remains as a quiet non-checkered floor instead of flashing an obsolete implementation.

## Future objects

Use `floor-scene-context.ts` to register Three.js objects with the existing scene. New floor-object components should not create their own renderer or animation loop.
