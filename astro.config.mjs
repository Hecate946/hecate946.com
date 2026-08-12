import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';
import svelte from '@astrojs/svelte';
import { localStatsDevPlugin } from './scripts/local-stats-dev.mjs';

export default defineConfig({
  site: 'https://hecate946.com',
  output: 'static',
  // Only the five primary navigation links opt into eager preparation. This
  // keeps project/PDF/external links cheap while making room-to-room switches
  // hit already-prepared documents whenever the browser supports it.
  prefetch: {
    prefetchAll: false,
    defaultStrategy: 'hover',
  },
  integrations: [
    svelte(),
    sitemap({
      filter: (page) =>
        !page.endsWith('/404/') &&
        !page.endsWith('/404.html') &&
        !page.endsWith('/pdf/'),
    }),
  ],
  vite: {
    plugins: [localStatsDevPlugin()],
  },
  devToolbar: {
    enabled: false,
  },
});
