# Seasonal collision update

Extract this patch into the root of `hecate946.com`.

```bash
unzip -o ~/Downloads/hecate946-seasonal-collision-shared.zip
npm run build
```

## What changed

- `/collision-detection` now renders the exact site artwork for each active season:
  - spring flowers
  - summer beach balls
  - autumn leaves
  - winter snowflakes
- The page renders the real `SeasonSelector.svelte` component rather than a separate palette control.
- The header selector and page selector now synchronize their `aria-pressed` states through the shared `data-season` attribute.
- `SeasonalShower.svelte` and `CollisionDetection.svelte` both use the same cached sprite factory in:
  - `src/lib/seasonal-shower/sprites.ts`
- The actual artwork remains defined once in the existing modular renderers:
  - `spring.ts`
  - `summer.ts`
  - `autumn.ts`
  - `winter.ts`

The collision simulation remains at 400 objects and retains the existing D3 force configuration.
