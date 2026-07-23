# Hecate Stats Worker

A small Cloudflare Worker + D1 analytics backend for `hecate946.com`.

It intentionally stores lifetime aggregates instead of a permanent raw event log:

- estimated visitors
- sessions
- page views
- daily totals
- page rankings
- interaction totals
- rounded, aggregated visitor locations

It does **not** store IP addresses, exact coordinates, full user agents, or individual browsing histories.

## Commands

```bash
npm install
npx wrangler login
npx wrangler d1 create hecate-stats
```

Copy the returned `database_id` into `wrangler.jsonc`, then run:

```bash
npm run db:init
npx wrangler secret put VISITOR_SALT
npm run deploy
```

For the salt, paste a long random value. One way to generate it is:

```bash
openssl rand -hex 32
```

The deploy command prints a URL similar to:

```text
https://hecate-stats.YOUR-SUBDOMAIN.workers.dev
```

Use that URL as the Astro `PUBLIC_STATS_API_URL` variable.

## Local testing

Initialize the local D1 database:

```bash
npm run db:init:local
npm run dev
```

Then create `.env` in the Astro project root:

```env
PUBLIC_STATS_API_URL=http://localhost:8787
```

## Privacy threshold

`LOCATION_PRIVACY_THRESHOLD` controls how many estimated visitors must be recorded for a location before it appears in the public API.

- `1`: convenient for local testing
- `2`: included production default
- `3` or higher: more conservative

Coordinates are rounded to one decimal place before storage.

## Manual backup

Export the complete database to a portable SQL file whenever you want:

```bash
npm run db:export
```

The Worker also runs a daily cleanup job that removes temporary daily-uniqueness rows and stale session rows. Lifetime totals, visitors, daily aggregates, page totals, interactions, and map locations remain intact.

## Production map check

Cloudflare supplies the latitude and longitude metadata at its production edge, so the map can stay empty during fully local development. For a one-visitor production test, temporarily set `LOCATION_PRIVACY_THRESHOLD` to `1`, deploy, visit the portfolio, then restore it to `2` and deploy again.
