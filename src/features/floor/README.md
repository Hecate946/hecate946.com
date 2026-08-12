# Floor scene

`FloorScene.svelte` is the production room floor. It reproduces the original Three.js camera projection with a tiny 2D checkerboard renderer, so normal rooms do not create a WebGL context or download/parse Three.js just to display flat floor tiles.

## Coordinate contract

- At the wall/floor seam, one floor world unit projects to one CSS pixel, matching the wall controller exactly.
- `x` follows wall coordinates and `z` starts at the wall and increases toward the viewer.
- `cameraX` is owned by the room/wall controller and passed to the floor imperatively. The floor never starts a competing animation loop.
- The camera/FOV/seam math intentionally matches the old Three.js floor so the visible tile geometry remains unchanged.

## Magnifier compatibility

The magnifying-glass experiment still needs a real Three.js floor scene because it registers 3D/Rapier objects through `floor-scene-context.ts`. The previous implementation is retained as `LegacyFloorScene.svelte` and is dynamically loaded by `AboutFloor.svelte` only when the global `enableMagnifyingGlass` feature switch is turned back on.

With the feature disabled, neither the legacy floor nor Rapier/Three magnifier code enters the active About-page runtime.
