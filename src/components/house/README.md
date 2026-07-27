# Homepage house

The house is a modular SVG feature mounted by `HouseScene.astro` beneath the
homepage force graph.

## Master switch

Edit `src/config/house-scene.ts`:

```ts
enabled: false,
```

That removes the entire house section from the page.

## Structure

- `HouseScene.astro` mounts the feature and applies base-path-safe links.
- `HouseExperience.svelte` is the client-side wrapper.
- `HouseIllustration.svelte` owns shared SVG definitions.
- `HouseShell.svelte` draws only the flat, straight-on architecture.
- `HouseWindow.svelte` draws one reusable clickable window.
- `src/config/house-scene.ts` controls destinations and every window position.
- `src/styles/house-scene.css` owns the visual treatment.

The shell contains no navigation logic. The windows contain no fixed page
choices. This separation makes it safe to redesign the architecture, change a
link, or later add a room-transition layer without rewriting the whole feature.

## Window alignment

The three upper square windows use the same `y`, `width`, and `height`, with a
constant 60-unit horizontal gap. The large half-dome and tall door share the
same baseline. All geometry is front-facing; the shell intentionally contains
no side wall, skew, or perspective transform.

## Navigation

Windows are ordinary anchor links and navigate directly. Set
`navigationEnabled: false` to retain the visual feature while disabling clicks.
