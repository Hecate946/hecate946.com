import { spawn } from 'node:child_process';
import { readdir, stat, unlink } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const projectRoot = path.resolve(scriptDirectory, '..');

// Keep this archive intentionally source-focused: enough to reproduce and
// understand the website, without build output, dependencies, caches, secrets,
// local analytics state, or old source archives.
const ROOT_FILES = [
  '.gitignore',
  '.nvmrc',
  '.prettierignore',
  '.prettierrc.mjs',
  'astro.config.mjs',
  'package.json',
  'package-lock.json',
  'svelte.config.js',
  'tsconfig.json',
];

const SOURCE_DIRECTORIES = [
  '.github',
  'cloudflare',
  'public',
  'scripts',
  'src',
];

const EXCLUDED_BASENAMES = new Set([
  '.DS_Store',
  'Thumbs.db',
]);

const EXCLUDED_RELATIVE_PATHS = new Set([
  'public/generated/code-stats.json',
]);

const EXCLUDED_SUFFIXES = [
  '.log',
  '.pyc',
  '.pyo',
  '~',
];

function normalize(relativePath) {
  return relativePath.split(path.sep).join('/');
}

function shouldInclude(relativePath) {
  const normalized = normalize(relativePath);
  const baseName = path.basename(normalized);

  if (EXCLUDED_BASENAMES.has(baseName)) return false;
  if (EXCLUDED_RELATIVE_PATHS.has(normalized)) return false;
  if (EXCLUDED_SUFFIXES.some((suffix) => baseName.endsWith(suffix))) return false;
  if (/^hecate946-source.*\.zip$/i.test(baseName)) return false;
  return true;
}

async function collectFiles(relativeDirectory) {
  const absoluteDirectory = path.join(projectRoot, relativeDirectory);
  let entries;
  try {
    entries = await readdir(absoluteDirectory, { withFileTypes: true });
  } catch (error) {
    if (error?.code === 'ENOENT') return [];
    throw error;
  }

  const files = [];
  for (const entry of entries) {
    const relativePath = path.join(relativeDirectory, entry.name);
    if (!shouldInclude(relativePath)) continue;

    if (entry.isDirectory()) {
      files.push(...await collectFiles(relativePath));
    } else if (entry.isFile()) {
      files.push(normalize(relativePath));
    }
  }
  return files;
}

async function runZip(outputPath, files) {
  await unlink(outputPath).catch((error) => {
    if (error?.code !== 'ENOENT') throw error;
  });

  return new Promise((resolve, reject) => {
    const child = spawn('zip', ['-q', '-9', outputPath, '-@'], {
      cwd: projectRoot,
      stdio: ['pipe', 'inherit', 'inherit'],
    });

    child.once('error', (error) => {
      if (error?.code === 'ENOENT') {
        reject(new Error('The `zip` command is not installed. Install it, then run `npm run site:zip` again.'));
      } else {
        reject(error);
      }
    });
    child.once('close', (code) => {
      if (code === 0) resolve();
      else reject(new Error(`zip exited with status ${code ?? 'unknown'}.`));
    });

    child.stdin.end(`${files.join('\n')}\n`);
  });
}

const files = [];
for (const rootFile of ROOT_FILES) {
  const absolute = path.join(projectRoot, rootFile);
  try {
    if ((await stat(absolute)).isFile() && shouldInclude(rootFile)) files.push(rootFile);
  } catch (error) {
    if (error?.code !== 'ENOENT') throw error;
  }
}

for (const directory of SOURCE_DIRECTORIES) {
  files.push(...await collectFiles(directory));
}

files.sort((a, b) => a.localeCompare(b));

if (!files.length) throw new Error('No source files were found to archive.');

const outputName = 'hecate946-source.zip';
const outputPath = path.join(projectRoot, outputName);
await runZip(outputPath, files);

const archiveSize = (await stat(outputPath)).size;
const megabytes = (archiveSize / (1024 * 1024)).toFixed(2);

console.log(`Created ${outputName}`);
console.log(`Included ${files.length} source/config/public files (${megabytes} MB).`);
console.log('Excluded dependencies, build output, caches, secrets, local analytics data, code stats, and previous source ZIPs.');
