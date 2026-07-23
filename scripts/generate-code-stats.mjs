import { execFileSync } from 'node:child_process';
import { promises as fs } from 'node:fs';
import path from 'node:path';
import process from 'node:process';

const ROOT = process.cwd();
const OUTPUT = path.join(ROOT, 'public', 'generated', 'code-stats.json');

const EXCLUDED_PREFIXES = [
  '.git/',
  '.astro/',
  '.wrangler/',
  'dist/',
  'node_modules/',
  'public/generated/',
  'coverage/',
];

const EXCLUDED_BASENAMES = new Set([
  'package-lock.json',
  'pnpm-lock.yaml',
  'yarn.lock',
  'bun.lock',
  'bun.lockb',
]);

const LANGUAGE_BY_EXTENSION = new Map([
  ['.astro', 'Astro'],
  ['.svelte', 'Svelte'],
  ['.ts', 'TypeScript'],
  ['.tsx', 'TypeScript'],
  ['.js', 'JavaScript'],
  ['.jsx', 'JavaScript'],
  ['.mjs', 'JavaScript'],
  ['.cjs', 'JavaScript'],
  ['.css', 'CSS'],
  ['.scss', 'SCSS'],
  ['.html', 'HTML'],
  ['.md', 'Markdown'],
  ['.mdx', 'MDX'],
  ['.json', 'JSON'],
  ['.jsonc', 'JSON'],
  ['.yaml', 'YAML'],
  ['.yml', 'YAML'],
  ['.sh', 'Shell'],
  ['.bash', 'Shell'],
  ['.py', 'Python'],
  ['.sql', 'SQL'],
]);

function git(args, fallback = '') {
  try {
    return execFileSync('git', args, {
      cwd: ROOT,
      encoding: 'utf8',
      stdio: ['ignore', 'pipe', 'ignore'],
    }).trim();
  } catch {
    return fallback;
  }
}

async function walk(directory, relative = '') {
  const entries = await fs.readdir(directory, { withFileTypes: true });
  const files = [];

  for (const entry of entries) {
    const childRelative = path.posix.join(relative, entry.name);
    const childAbsolute = path.join(directory, entry.name);

    if (entry.isDirectory()) {
      if (EXCLUDED_PREFIXES.some((prefix) => `${childRelative}/`.startsWith(prefix))) {
        continue;
      }
      files.push(...(await walk(childAbsolute, childRelative)));
    } else if (entry.isFile()) {
      files.push(childRelative);
    }
  }

  return files;
}

function shouldIncludeFile(file) {
  const normalized = file.replaceAll('\\', '/');
  if (EXCLUDED_PREFIXES.some((prefix) => normalized.startsWith(prefix))) return false;
  if (EXCLUDED_BASENAMES.has(path.posix.basename(normalized))) return false;
  return true;
}

function isProbablyText(buffer) {
  const sample = buffer.subarray(0, Math.min(buffer.length, 8_000));
  return !sample.includes(0);
}

async function countLines(file) {
  try {
    const buffer = await fs.readFile(path.join(ROOT, file));
    if (!isProbablyText(buffer)) return null;

    const text = buffer.toString('utf8');
    const lines = text.length === 0 ? [] : text.split(/\r?\n/);
    const nonEmpty = lines.reduce(
      (count, line) => count + (line.trim().length > 0 ? 1 : 0),
      0,
    );

    return {
      total: lines.length,
      nonEmpty,
    };
  } catch {
    return null;
  }
}

const gitFiles = git(['ls-files', '-z']);
const discoveredFiles = gitFiles
  ? gitFiles.split('\0').filter(Boolean)
  : await walk(ROOT);
const files = discoveredFiles.filter(shouldIncludeFile);

const directories = new Set(
  discoveredFiles
    .map((file) => path.posix.dirname(file.replaceAll('\\', '/')))
    .filter((directory) => directory !== '.'),
);

const languageTotals = new Map();
let totalLines = 0;
let sourceLines = 0;

for (const file of files) {
  const extension = path.extname(file).toLowerCase();
  const language = LANGUAGE_BY_EXTENSION.get(extension);
  if (!language) continue;

  const counts = await countLines(file);
  if (!counts) continue;

  totalLines += counts.total;
  sourceLines += counts.nonEmpty;

  const current = languageTotals.get(language) ?? { files: 0, lines: 0 };
  current.files += 1;
  current.lines += counts.nonEmpty;
  languageTotals.set(language, current);
}

const languages = Array.from(languageTotals, ([name, values]) => ({
  name,
  files: values.files,
  lines: values.lines,
  percentage: sourceLines === 0 ? 0 : (values.lines / sourceLines) * 100,
})).sort((a, b) => b.lines - a.lines || a.name.localeCompare(b.name));

const normalizedFiles = files.map((file) => file.replaceAll('\\', '/'));
const countWithin = (prefix, extensions = null) =>
  normalizedFiles.filter((file) => {
    if (!file.startsWith(prefix)) return false;
    if (!extensions) return true;
    return extensions.includes(path.posix.extname(file).toLowerCase());
  }).length;

const latestSha = git(['rev-parse', 'HEAD'], null);
const commitCount = Number.parseInt(git(['rev-list', '--count', 'HEAD'], '0'), 10) || 0;
const latestDate = git(['log', '-1', '--format=%cI'], null);
const latestMessage = git(['log', '-1', '--format=%s'], null);
const firstDate = git(['log', '--reverse', '--format=%cI'], '')
  .split('\n')
  .filter(Boolean)[0] ?? null;

const result = {
  generatedAt: new Date().toISOString(),
  commit: {
    count: commitCount,
    latestSha,
    latestDate,
    latestMessage,
    firstDate,
  },
  repository: {
    files: discoveredFiles.length,
    countedFiles: normalizedFiles.length,
    directories: directories.size,
    totalLines,
    sourceLines,
  },
  site: {
    pages: countWithin('src/pages/', ['.astro', '.md', '.mdx']),
    components: countWithin('src/components/', [
      '.astro',
      '.svelte',
      '.tsx',
      '.jsx',
    ]),
    layouts: countWithin('src/layouts/', ['.astro']),
    assets: countWithin('public/'),
  },
  languages,
};

await fs.mkdir(path.dirname(OUTPUT), { recursive: true });
await fs.writeFile(OUTPUT, `${JSON.stringify(result, null, 2)}\n`, 'utf8');
console.log(`Generated ${path.relative(ROOT, OUTPUT)} from ${normalizedFiles.length} counted files.`);
