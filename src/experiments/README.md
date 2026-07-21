# Experiments

Put unstable Canvas, WebGL, audio, physics, and visualization systems here.

A feature should expose either:

- a Svelte component mounted with an Astro client directive, or
- a small `mount(element, options)` function that returns a cleanup function.

Use `src/lib/canvas.ts` for display-density resizing and visibility-aware animation loops. Keep cached/static rendering separate from actively animated growth or interaction layers.
