# Cyrus Asasi Portfolio Starter

A modular Astro portfolio foundation for computer science, clarinet, piano, chess, and pickleball. It is designed to remain a fast content site while supporting app-like interactive islands, seasonal visual systems, and a public statistics observatory.

## Included

- Astro 7 static site configured for GitHub Pages
- strict TypeScript
- Svelte islands for focused stateful interfaces
- typed content collections for projects, music, chess, pickleball, and notes
- shared layouts, cards, page introductions, and section primitives
- automatic and manual seasonal themes
- native cross-document view transitions
- keyboard command palette (`⌘K`, `Ctrl+K`, or `/`)
- provider-neutral analytics event boundary
- build-time public stats JSON and starter dashboard
- GitHub Actions for quality checks and Pages deployment
- reduced-motion and keyboard-accessible defaults

## Start locally

```bash
npm install
cp .env.example .env
npm run dev
```

Open the local URL printed by Astro.

## Important first edits

1. Update `src/config/site.ts` with real email and social links.
2. Replace the sample Markdown entries in `src/content/`.
3. Set `SITE_URL` and `BASE_PATH` in `.env` locally.
4. Set repository variables with the same names in GitHub Actions.

### Base path examples

Custom domain or `username.github.io` repository:

```env
SITE_URL=https://cyrusasasi.com
BASE_PATH=/
```

Project repository served at `username.github.io/portfolio`:

```env
SITE_URL=https://username.github.io
BASE_PATH=/portfolio
```

## Commands

```bash
npm run dev
npm run build
npm run preview
npm run check
npm run format
npm run content:new -- projects my-project
npm run stats:generate
```

## Directory map

```text
src/
  components/
    core/       persistent site systems
    islands/    focused Svelte interactivity
    ui/         reusable presentation primitives
  experiments/  isolated Canvas/WebGL/audio prototypes
  config/       identity, navigation, and season contracts
  content/      editable Markdown data
  data/         generated public data snapshots
  layouts/      page and entry shells
  lib/          shared logic, motion, canvas, and provider boundaries
  pages/        URL routes
  styles/       global tokens, reset, and seasonal themes
scripts/        content and data generation utilities
docs/           architecture and build guidance
```

Read `docs/ARCHITECTURE.md` before introducing a major animation system or third-party state library.

## GitHub Pages

The included deploy workflow builds on pushes to `main`. In the repository settings, choose **GitHub Actions** as the Pages source. Add repository variables:

- `SITE_URL`
- `BASE_PATH`
- later, `ANALYTICS_SITE_ID`

Add provider keys only as encrypted repository secrets, such as `ANALYTICS_API_KEY`.

## Stats architecture

`src/pages/stats/index.astro` imports `src/data/stats.json`. During deployment, `scripts/generate-stats.mjs` runs before the build. Replace its placeholder function with a server-side provider request using GitHub Actions secrets. The generated JSON must contain anonymous aggregates only.

## Design rule

The static page should always make sense before an interactive island loads. Visual experiments enhance the content; they do not own the content.
