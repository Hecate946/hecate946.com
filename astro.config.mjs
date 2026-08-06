import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';
import svelte from '@astrojs/svelte';

export default defineConfig({
  site: 'https://hecate946.com',
  output: 'static',
  integrations: [
    svelte(),
    sitemap({
      filter: (page) => !page.endsWith('/navigation/'),
    }),
  ],
  devToolbar: {
    enabled: false,
  },
});
