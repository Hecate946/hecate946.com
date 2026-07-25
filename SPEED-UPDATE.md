# Speed update

Copy the folders and files in this ZIP over the matching paths in the project.

## Changes included

- Defers noncritical Svelte hydration with `client:idle`.
- Defers analytics loading with `requestIdleCallback` and a dynamic import.
- Throttles the header scroll state update with `requestAnimationFrame`.
- Replaces the large About-page images with responsive WebP variants.
- Replaces runtime SVG turbulence with a tiny pre-rendered noise texture.
- Requests Newsreader as one variable weight range.
- Ignores Cloudflare `.wrangler` development data.

## Optional repository cleanup

The following original images are no longer referenced and can be deleted after
confirming the new images display correctly:

- `public/images/pig.png`
- `public/images/about/ucla-pickleball-super-regional.jpg`

Leaving them in place does not make visitors download them; deleting them only
reduces repository and deployment size.

After replacing the files, run:

```bash
npm install
npm run build
```
