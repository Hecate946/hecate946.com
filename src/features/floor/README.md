# Floor scene contract

`FloorScene.svelte` is the only owner of the room's WebGL renderer. The wall remains DOM/Svelte, while the floor and future spatial objects live in this scene.

- The wall controller owns `cameraX` and calls `FloorScene.setCameraX()` once per rendered camera update.
- At the wall/floor seam, one Three.js world unit projects to one CSS pixel. This keeps the 2D wall and 3D floor on the same horizontal coordinate system.
- `x` follows wall coordinates, `y` is height above the floor, and `z` starts at the wall and increases toward the viewer.
- Checker tiles are true `84 x 84` world-unit squares. Perspective, not texture distortion, creates their on-screen trapezoids.
- The WebGL canvas spans the room so objects may extend above the baseboard. The floor plane itself starts at the baseboard's lower edge.
- Descendant Svelte components can use `FLOOR_SCENE_CONTEXT` to register `THREE.Object3D` instances. Registration is safe before the renderer finishes loading.
- The CSS checkerboard is a progressive fallback only. If Three.js or WebGL fails, the room remains visually usable.

Keep camera ownership outside this feature. New floor objects should register with the scene rather than creating additional renderers or animation loops.
