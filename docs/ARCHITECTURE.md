# Architecture

## Stable shell

The stable shell is responsible for:

- static routing and metadata
- typed content collections
- page layouts and reusable UI
- navigation, command palette, and accessibility
- seasonal design tokens and user preference
- provider-neutral analytics events
- build-time public statistics

These systems should change slowly.

## Interactive islands

Place stateful Svelte components in `src/components/islands/`. Hydrate them deliberately:

- `client:load` for controls needed immediately, such as the command palette
- `client:visible` for dashboards, boards, maps, and visualizers below the fold
- `client:idle` for low-priority enhancements
- no client directive for static Svelte output

Do not turn a whole page into one island unless shared client state genuinely requires it.

## Experiments

Put unstable animation and visualization code in a feature folder under `src/experiments/` when it is added. A recommended structure is:

```text
src/experiments/
  seasonal-growth/
    engine.ts
    renderer.ts
    cache.ts
    presets/
  audio-field/
  chess-tree/
  court-motion/
```

Each experiment should expose a small mounting API or a Svelte component. Use `src/lib/canvas.ts` for density-aware sizing and visibility-aware animation lifecycles. It should not import layouts or mutate unrelated page markup.

## Content versus presentation

Markdown content belongs in `src/content/`. Rendering logic belongs in pages and components. Avoid embedding major HTML layouts inside Markdown entries.

## Analytics boundary

UI code calls `trackEvent()` from `src/lib/analytics.ts`. A future provider adapter listens for `portfolio:analytics` and forwards only approved events. The public stats dashboard reads sanitized aggregate JSON generated in CI.

## GitHub Pages constraints

The production build is static. Private API credentials must remain in GitHub Actions secrets or a separate serverless endpoint. Browser code must never receive an analytics administration token.
