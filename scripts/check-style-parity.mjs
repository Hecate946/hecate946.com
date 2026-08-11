import fs from 'node:fs';
import path from 'node:path';

const ROOT = process.cwd();
const SRC = path.join(ROOT, 'src');
const TEXT_EXTENSIONS = new Set(['.astro', '.css', '.js', '.mjs', '.svelte', '.ts', '.tsx']);
const failures = [];

function walk(directory) {
  return fs.readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const absolute = path.join(directory, entry.name);
    if (entry.isDirectory()) return walk(absolute);
    return TEXT_EXTENSIONS.has(path.extname(entry.name)) ? [absolute] : [];
  });
}

function relative(file) {
  return path.relative(ROOT, file).replaceAll('\\', '/');
}

function lineNumber(text, index) {
  return text.slice(0, index).split('\n').length;
}

function stripSvelteScriptsAndStyles(text) {
  return text
    .replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi, '')
    .replace(/<style\b[^>]*>[\s\S]*?<\/style>/gi, '');
}

for (const file of walk(SRC)) {
  const text = fs.readFileSync(file, 'utf8');
  const fileName = relative(file);

  // Svelte's dev server and production CSS extraction do not load dynamically
  // imported component styles in exactly the same way. Keep style-bearing
  // components in the static module graph; defer their rendering/data instead.
  const dynamicSvelteImport = /import\s*\(\s*(['"])[^'"\n]+\.svelte\1\s*\)/g;
  for (const match of text.matchAll(dynamicSvelteImport)) {
    failures.push(
      `${fileName}:${lineNumber(text, match.index ?? 0)} dynamically imports a .svelte component`,
    );
  }

  // A production/dev flag may change endpoints or caching, but it must never
  // select different markup or stylesheet rules. That guarantees both builds
  // feed the same DOM/CSS into the browser.
  if (file.endsWith('.svelte')) {
    const markup = stripSvelteScriptsAndStyles(text);
    if (/import\.meta\.env\.(?:DEV|PROD)/.test(markup)) {
      failures.push(`${fileName} uses a DEV/PROD flag in rendered Svelte markup`);
    }
  }

  if (file.endsWith('.css')) {
    if (/\b(?:localhost|127\.0\.0\.1|0\.0\.0\.0)\b/i.test(text)) {
      failures.push(`${fileName} contains host-specific CSS`);
    }
  }

  for (const match of text.matchAll(/<style\b[^>]*>([\s\S]*?)<\/style>/gi)) {
    const styleText = match[1] ?? '';
    if (/import\.meta\.env\.(?:DEV|PROD)/.test(styleText)) {
      failures.push(`${fileName}:${lineNumber(text, match.index ?? 0)} contains environment-conditioned CSS`);
    }
    if (/\b(?:localhost|127\.0\.0\.1|0\.0\.0\.0)\b/i.test(styleText)) {
      failures.push(`${fileName}:${lineNumber(text, match.index ?? 0)} contains host-specific component CSS`);
    }
  }
}

if (failures.length) {
  console.error('\nStyle parity check failed:\n');
  for (const failure of failures) console.error(`  - ${failure}`);
  console.error('\nKeep visual component imports and CSS identical between dev and production.\n');
  process.exit(1);
}

console.log('Style parity check passed: no dynamic Svelte style chunks or environment-specific styling found.');
