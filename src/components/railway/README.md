# Line 946 railway

The railway is intentionally isolated from the rest of the site and split into small components.

## Components

- `RailwayPassage.svelte` — journey timing, arrival/dwell/departure state, countdown data, replay, and responsive positioning.
- `RailwayTrain.svelte` — the steam locomotive, tender, one passenger car per configured page, smoke, wheels, and train-only styles.
- `RailwayStation.svelte` — the rustic wooden depot, page-aware station sign, supported wooden signposts, lamps, platform, and digital arrival board.
- `RailwayTrack.svelte` — black gravel ballast, wooden sleepers, and aligned rails.
- `src/config/railway.ts` — line name, timing, page cars, links, and the future navigation switch.
- `src/layouts/BaseLayout.astro` — mounts the railway once and passes the current page name to the station.

## Current behavior

Line 946 approaches from the left at a constant speed, stops by the station, waits for four seconds, and continues to the right at the same speed. The total journey is controlled by `durationSeconds` in `src/config/railway.ts`.

The station sign contains only `[Current Page] Station` and the `946` badge. The train section is framed by two thin horizontal rules with equal exterior spacing above and below.

Set `navigationEnabled: true` in `src/config/railway.ts` when the passenger cars should become page links.
