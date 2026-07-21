import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';
import svelte from '@astrojs/svelte';

const site = process.env.SITE_URL || 'https://example.com';
const rawBase = process.env.BASE_PATH || '/';
const base = rawBase === '/' ? '/' : `/${rawBase.replace(/^\/+|\/+$/g, '')}`;

export default defineConfig({
  site,
  base,
  output: 'static',
  integrations: [svelte(), sitemap()],
  build: {
    assets: '_assets',
  },
  vite: {
    build: {
      sourcemap: true,
    },
  },
});
