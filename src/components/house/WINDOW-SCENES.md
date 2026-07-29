# House window scenes

The house remains a frozen 1672 × 941 PNG. Each interactive scene is SVG art
clipped into the individual dark glass panes, so the original white window
frames and mullions remain visible.

## Current destinations

- Top-left: `/collision-detection/`
- Second upper window: `/chess-board/`
- Center upper window: `/resume/`
- Fourth upper window: `/projects/`
- Top-right: `/contact/`
- Lower-left: `/concert-hall/`

The chess window and chess page share `ChessBoardArtwork.svelte`. The lower-left
window and concert page share `ConcertHallArtwork.svelte`, so edits to the
artwork update both the miniature preview and full-screen room.

## Calibration

Open:

```text
/house-svg/?debug=windows
```

The cyan rectangles show the exact pane clips and the dashed pink rectangle
shows the clickable hit area. Geometry is configured in:

```text
src/config/house-scene.ts
```

Disable all room artwork with:

```text
/house-svg/?scenes=off
```
