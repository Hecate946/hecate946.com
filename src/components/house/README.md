# Homepage house

The house is a modular inline-SVG feature mounted by `HouseScene.astro` beneath
the homepage force graph.

## Frozen reference

The current architectural pass is frozen against a **1672 × 941** PNG:

- PNG: `public/images/house/house-outline-current.png`
- Static SVG reference: `public/images/house/house-outline-current.svg`
- Interactive inline SVG: `HouseIllustration.svelte` + `HouseShell.svelte`

Both `/house-png/` and `/house-svg/` use this same native coordinate system, so
switching between the routes compares like-for-like without rescaling the
geometry to a different aspect ratio.

## Master switch

Edit `src/config/house-scene.ts`:

```ts
enabled: false,
```

That removes the entire house section from the homepage.

## Structure

- `HouseScene.astro` mounts the feature and applies base-path-safe links.
- `HouseExperience.svelte` is the client-side wrapper.
- `HouseIllustration.svelte` owns shared gradients and SVG filters.
- `HouseShell.svelte` draws the complete frozen architectural elevation.
- `HouseWindow.svelte` is now a transparent interaction layer over the five upper windows; it does not redraw or distort the architecture.
- `src/config/house-scene.ts` controls destinations and clickable hit areas.
- `src/styles/house-scene.css` owns the line-art treatment and hover states.

## Measured geometry

- Canvas: `1672 × 941`
- Building dark-pixel bounds: approximately `x=141…1558`, `y=92…833`
- Upper wall: `y=281…496`
- Lower wall: `y=515…808`
- Center portico: `x=689…1007`
- Upper windows: aligned from `y=307`; four side windows are `≈86 × 132`, and the center window is `86 × 147`
- Broad lower windows: `299 × 181` and `305 × 181`
- The frozen PNG visually resolves each broad lower window as a `7 × 5` pane grid, which the SVG reproduces exactly.

## Navigation

The five upper windows are ordinary anchor links. Set
`navigationEnabled: false` to retain the visual feature while disabling clicks.
