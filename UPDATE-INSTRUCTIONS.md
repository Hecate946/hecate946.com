# Navbar + seasonal color system update

This folder contains only the files that changed.

## Apply it

From the root of your existing Astro project, copy this folder's contents over
it while preserving the included paths. Existing files with the same names
should be replaced; `ColorModeToggle.svelte` is new.

Example:

```bash
cp -R /path/to/cyrus-navbar-season-update/. .
npm run check
npm run dev
```

## Included behavior

- Responsive desktop/mobile navbar modeled after the supplied reference.
- Header navigation: **About**, **Interests**, and **Stats**.
- Four illustrated season buttons: spring, summer, autumn, and winter.
- Independent light/dark mode toggle for every season.
- Theme and season choices persist in `localStorage`.
- First-time visitors start on the real-world season and their operating-system
  light/dark preference.
- Eight complete semantic color palettes live in `src/styles/themes.css`.
- The TypeScript configuration now uses Astro's stable `strict` preset, limits
  editor scope to actual source/config files, and excludes generated/dependency
  directories.

Contact remains available from the About page and footer so the persistent
header stays uncluttered.
