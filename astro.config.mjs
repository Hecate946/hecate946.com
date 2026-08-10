import { execFile } from 'node:child_process';
import path from 'node:path';
import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';
import svelte from '@astrojs/svelte';
import { localStatsDevPlugin } from './scripts/local-stats-dev.mjs';

function codeStatsDevPlugin() {
  const root = process.cwd();
  const generator = path.join(root, 'scripts', 'generate-code-stats.mjs');
  const generatedFile = path.join(root, 'public', 'generated', 'code-stats.json');
  let timer = null;
  let running = false;
  let rerun = false;

  const generate = () => {
    if (running) {
      rerun = true;
      return;
    }

    running = true;
    execFile(process.execPath, [generator], { cwd: root }, (error) => {
      running = false;
      if (error) console.error('[code-stats] regeneration failed:', error.message);
      if (rerun) {
        rerun = false;
        generate();
      }
    });
  };

  const schedule = () => {
    if (timer) clearTimeout(timer);
    timer = setTimeout(() => {
      timer = null;
      generate();
    }, 120);
  };

  const shouldRegenerate = (file) => {
    const absolute = path.resolve(file);
    if (absolute === generatedFile) return false;

    const relative = path.relative(root, absolute).replaceAll('\\', '/');
    return !(
      relative.startsWith('node_modules/') ||
      relative.startsWith('.git/') ||
      relative.startsWith('.astro/') ||
      relative.startsWith('.cache/') ||
      relative.startsWith('dist/') ||
      relative.startsWith('public/generated/')
    );
  };

  return {
    name: 'hecate-code-stats-dev',
    apply: 'serve',
    configureServer(server) {
      generate();
      server.watcher.on('all', (_event, file) => {
        if (shouldRegenerate(file)) schedule();
      });
    },
  };
}

export default defineConfig({
  site: 'https://hecate946.com',
  output: 'static',
  integrations: [
    svelte(),
    sitemap({
      filter: (page) =>
        !page.endsWith('/navigation/') && !page.endsWith('/pdfs/'),
    }),
  ],
  vite: {
    plugins: [codeStatsDevPlugin(), localStatsDevPlugin()],
  },
  devToolbar: {
    enabled: false,
  },
});
