# Adding a page

## A normal section page

1. Create `src/pages/new-section/index.astro`.
2. Wrap the content in `PageLayout`.
3. Add the route to `navigation` in `src/config/site.ts` when it belongs in primary navigation.
4. Use shared `Section`, `CardGrid`, and `ContentCard` components before creating new primitives.

## A content-driven section

1. Add a collection or extend a schema in `src/content.config.ts`.
2. Add Markdown entries in `src/content/<collection>/`.
3. Query them with `getCollection()` in the index page.
4. Add a static `[...id].astro` route for individual entries.

## An interactive feature

1. Create the component in `src/components/islands/` or an experiment folder.
2. Keep essential written content outside the island.
3. Choose the least aggressive client directive that works.
4. Respect reduced motion and keyboard navigation.
5. Call `trackEvent()` only for meaningful, documented interactions.
