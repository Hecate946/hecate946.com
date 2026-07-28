# House artwork files

## Current aliases

- `house-white-current.png` — current complete 1672 × 941 house PNG.
- `house-white-current.svg` — self-contained full-house SVG mirror of the current PNG. The PNG is embedded inside the SVG so it works independently and cannot lose its image reference.

The website's live house is rendered by:

- `src/components/house/HouseIllustration.svelte`

The side-by-side comparison page renders that live Svelte component directly. It does **not** use `house-white-current.svg` for the comparison.

## Preserved versions

- `versions/house-outline-v1.png`
- `versions/house-outline-v1.svg`
- `versions/house-white-low-roof-v2.png`
- `versions/house-white-low-roof-v2.svg`
- `versions/house-white-raised-roof-v3.png`
- `versions/house-white-raised-roof-v3.svg` — self-contained full-house mirror of the v3 PNG.

New accepted versions should be added with a new version number instead of replacing older files. The `house-white-current.*` aliases may then be updated to duplicate the newest accepted version.
