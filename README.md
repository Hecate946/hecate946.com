# D3 Lab SSR fix

Copy these files into the matching locations in the `hecate946.com` repository.

This revision fixes the Astro SSR crash caused by calling the browser-only
`cancelAnimationFrame` global from Svelte's `onDestroy` hook during server rendering.
All browser cleanup now lives inside the cleanup function returned by `onMount`.

From the repository root:

```bash
unzip -o ~/Downloads/hecate946-d3-lab-ssr-fix.zip
npm run build
```

Files included:

- `src/pages/d3.astro`
- `src/components/islands/D3Playground.svelte`
- `src/styles/d3.css`
