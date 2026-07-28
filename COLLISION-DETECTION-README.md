# D3 collision detection page

Adds a standalone page at:

- `/collision-detection`

Files added:

- `src/pages/collision-detection.astro`
- `src/components/islands/CollisionDetection.svelte`
- `src/styles/collision-detection.css`

The force configuration matches the linked Observable notebook:

- 200 nodes
- `alphaTarget(0.3)`
- `velocityDecay(0.1)`
- x/y force strength `0.01`
- collision radius `r + 1`
- 3 collision iterations
- one invisible pointer-controlled node with charge `-width * 2 / 3`

No navigation files are changed.
