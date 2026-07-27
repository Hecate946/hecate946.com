# Frozen house SVG implementation

This patch freezes the approved PNG and rebuilds the house as native inline SVG.

## Preview routes

- `/house-png/` shows the frozen 1672 × 941 PNG.
- `/house-svg/` shows the interactive SVG implementation using the same 1672 × 941 viewBox.
- Press `P` or `V` to switch formats.

## What changed

- Replaced the old cottage shell with the approved two-story elevation.
- Rebuilt the roof, pediment, oculus, cornices, wall divisions, seven rectangular windows, arched entrance, and steps as SVG geometry.
- Preserved the five upper windows as interactive navigation targets without letting the interaction layer alter the frozen architecture.
- Added a standalone SVG reference at `public/images/house/house-outline-current.svg`.
- Updated the homepage and preview aspect ratios to `1672 / 941`.

The broad lower windows reproduce the pane count visible in the frozen PNG: seven columns by five rows.
