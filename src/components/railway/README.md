# Railway passage

`RailwayPassage.svelte` is a self-contained, reusable scene mounted once in
`BaseLayout.astro`, so every page automatically receives the railway without
page-specific markup or styles.

## Configuration

Edit `src/config/railway.ts` to change:

- the line and service names
- animation duration
- autoplay behavior
- the three destination labels shown on the passenger cars
- destination URLs
- `navigationEnabled`

When `navigationEnabled` is `false`, the passenger cars are decorative. Set it
to `true` to turn each labeled car into a keyboard-accessible link using the
configured destination URLs.

## Isolation

The component owns its markup, CSS, intersection observer, reduced-motion
behavior, replay control, and animation state. The only project-level change is
the single component mount in `BaseLayout.astro`.
