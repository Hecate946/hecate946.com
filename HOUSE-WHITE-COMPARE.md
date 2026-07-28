# White house PNG / SVG comparison

This patch adds the frozen 1672 × 941 white-house reference and three preview routes:

- `/house-png/` — full-screen PNG reference
- `/house-svg/` — the website SVG coordinate layer with aligned interactive-window geometry
- `/house-compare/` — PNG and SVG displayed side by side

Keyboard shortcuts on the preview pages:

- `P` — PNG
- `V` — SVG
- `C` — comparison

## Important implementation detail

The visual source of truth remains the frozen PNG. The SVG presentation embeds that PNG inside the exact same 1672 × 941 SVG coordinate system, then places the interactive window shapes in that coordinate system. This guarantees pixel-identical visuals and prevents responsive overlay drift, but the house artwork itself is not converted into independently editable vector paths.
