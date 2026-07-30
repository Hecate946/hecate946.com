import { createHash } from 'node:crypto';
import {
  copyFileSync,
  existsSync,
  lstatSync,
  mkdirSync,
  mkdtempSync,
  readFileSync,
  readdirSync,
  rmSync,
  statSync,
  writeFileSync,
} from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, extname, join, relative, resolve, sep } from 'node:path';
import { spawnSync } from 'node:child_process';

const ROOT = process.cwd();
const OUTPUT_NAME = 'hecate946-source.zip';
const OUTPUT_PATH = join(ROOT, OUTPUT_NAME);
const SMALL_ASSET_LIMIT = 512 * 1024;
const REFERENCED_ASSET_LIMIT = 3 * 1024 * 1024;
const WITH_ASSETS = process.argv.includes('--with-assets');

const ignoredDirectoryNames = new Set([
  '.git',
  '.astro',
  '.cache',
  '.parcel-cache',
  '.svelte-kit',
  '.vercel',
  '.wrangler',
  '__pycache__',
  'build',
  'coverage',
  'dist',
  'node_modules',
  'out',
]);

const sourceExtensions = new Set([
  '.astro',
  '.cjs',
  '.css',
  '.html',
  '.js',
  '.json',
  '.jsonc',
  '.mjs',
  '.py',
  '.scss',
  '.sql',
  '.svelte',
  '.toml',
  '.ts',
  '.tsx',
  '.xml',
  '.yaml',
  '.yml',
]);

const generatedOrHeavyExtensions = new Set([
  '.blend',
  '.blend1',
  '.exr',
  '.glb',
  '.gltf',
  '.hdr',
  '.map',
  '.mov',
  '.mp4',
  '.psd',
  '.webm',
  '.zip',
]);

const alwaysExcludedNames = new Set([
  '.dev.vars',
  '.env',
  '.env.local',
  '.env.production',
  '.env.development',
  'secrets.txt',
  OUTPUT_NAME,
]);

function normalizePath(path) {
  return path.split(sep).join('/').replace(/^\.\//, '');
}

function run(command, args, options = {}) {
  return spawnSync(command, args, {
    cwd: ROOT,
    encoding: 'utf8',
    stdio: options.stdio ?? 'pipe',
    ...options,
  });
}

function hasCommand(command) {
  const result = spawnSync('bash', ['-lc', `command -v ${command}`], {
    encoding: 'utf8',
    stdio: 'ignore',
  });
  return result.status === 0;
}

function isSensitive(path) {
  const normalized = normalizePath(path).toLowerCase();
  const basename = normalized.split('/').at(-1) ?? normalized;

  if (alwaysExcludedNames.has(basename)) return true;
  if (basename.startsWith('.env.') && basename !== '.env.example') return true;
  if (/\.(key|pem|p12|pfx)$/i.test(basename)) return true;
  if (/(^|[-_.])(secret|secrets|credential|credentials|token|tokens)([-_.]|$)/i.test(basename)) {
    return true;
  }
  return false;
}

function shouldIgnoreDirectory(path) {
  return normalizePath(path)
    .split('/')
    .some((part) => ignoredDirectoryNames.has(part));
}

function walkFallback(directory, base = directory, files = []) {
  for (const entry of readdirSync(directory, { withFileTypes: true })) {
    const absolute = join(directory, entry.name);
    const rel = normalizePath(relative(base, absolute));

    if (entry.isDirectory()) {
      if (!shouldIgnoreDirectory(rel)) walkFallback(absolute, base, files);
      continue;
    }

    if (entry.isFile()) files.push(rel);
  }
  return files;
}

function getCandidateFiles() {
  const gitResult = run('git', [
    'ls-files',
    '--cached',
    '--others',
    '--exclude-standard',
    '-z',
  ]);

  if (gitResult.status === 0 && gitResult.stdout) {
    return gitResult.stdout
      .split('\0')
      .map((path) => normalizePath(path.trim()))
      .filter(Boolean);
  }

  return walkFallback(ROOT);
}

function collectSearchableSource(candidateFiles) {
  const chunks = [];

  for (const path of candidateFiles) {
    const extension = extname(path).toLowerCase();
    if (!sourceExtensions.has(extension)) continue;
    if (shouldIgnoreDirectory(path) || isSensitive(path)) continue;

    const absolute = join(ROOT, path);
    if (!existsSync(absolute)) continue;

    const size = statSync(absolute).size;
    if (size > 5 * 1024 * 1024) continue;

    try {
      chunks.push(readFileSync(absolute, 'utf8').toLowerCase());
    } catch {
      // A source-like file that is not valid UTF-8 is simply not searched.
    }
  }

  return chunks.join('\n');
}

function isPublicAssetReferenced(path, sourceText) {
  if (!path.startsWith('public/')) return false;
  const publicRelative = path.slice('public/'.length).toLowerCase();
  return (
    sourceText.includes(`/${publicRelative}`) ||
    sourceText.includes(`'${publicRelative}'`) ||
    sourceText.includes(`\"${publicRelative}\"`)
  );
}

function hasSmallerSibling(path) {
  const extension = extname(path).toLowerCase();
  if (!['.png', '.jpg', '.jpeg'].includes(extension)) return false;

  const stem = path.slice(0, -extension.length);
  return ['.webp', '.avif'].some((candidateExtension) =>
    existsSync(join(ROOT, `${stem}${candidateExtension}`)),
  );
}

function classify(path, sourceText) {
  const normalized = normalizePath(path);
  const extension = extname(normalized).toLowerCase();
  const absolute = join(ROOT, normalized);

  if (!existsSync(absolute)) return { include: false, reason: 'missing' };
  if (!lstatSync(absolute).isFile()) return { include: false, reason: 'not a regular file' };
  if (shouldIgnoreDirectory(normalized)) return { include: false, reason: 'generated/dependency directory' };
  if (isSensitive(normalized)) return { include: false, reason: 'secret or environment file' };
  if (extension === '.md' || extension === '.markdown') {
    if (normalized.startsWith('blender/assets/')) {
      return { include: true, reason: 'shared Blender asset documentation' };
    }
    return { include: false, reason: 'markdown intentionally excluded' };
  }
  if (generatedOrHeavyExtensions.has(extension)) {
    return { include: false, reason: 'generated or heavyweight binary' };
  }

  // Blender source is useful; rendered/exported Blender outputs are not.
  if (
    normalized.startsWith('blender/') &&
    extension !== '.py' &&
    !normalized.startsWith('blender/assets/')
  ) {
    return { include: false, reason: 'Blender output; Python source retained' };
  }

  const size = statSync(absolute).size;

  // All website, build, configuration, deployment, and Blender Python source is retained.
  if (sourceExtensions.has(extension) || extension === '' || normalized === '.nvmrc') {
    return { include: true, reason: 'source/configuration' };
  }

  // In full-asset mode, retain public assets except types explicitly excluded above.
  if (WITH_ASSETS && normalized.startsWith('public/')) {
    return { include: true, reason: 'public asset (--with-assets)' };
  }

  if (normalized.startsWith('public/')) {
    const referenced = isPublicAssetReferenced(normalized, sourceText);

    if (hasSmallerSibling(normalized) && !referenced) {
      return { include: false, reason: 'larger duplicate with WebP/AVIF sibling' };
    }

    if (size <= SMALL_ASSET_LIMIT) {
      return { include: true, reason: 'small public asset' };
    }

    if (referenced && size <= REFERENCED_ASSET_LIMIT) {
      return { include: true, reason: 'referenced public asset' };
    }

    return {
      include: false,
      reason: referenced
        ? `referenced asset exceeds ${REFERENCED_ASSET_LIMIT} bytes`
        : `unreferenced asset exceeds ${SMALL_ASSET_LIMIT} bytes`,
    };
  }

  // Keep other small project files, such as lockfiles, PDFs, and text data.
  if (size <= SMALL_ASSET_LIMIT) {
    return { include: true, reason: 'small project file' };
  }

  return { include: false, reason: 'large non-source file' };
}

function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 ** 2) return `${(bytes / 1024).toFixed(1)} KiB`;
  if (bytes < 1024 ** 3) return `${(bytes / 1024 ** 2).toFixed(1)} MiB`;
  return `${(bytes / 1024 ** 3).toFixed(2)} GiB`;
}

function sha256(path) {
  const hash = createHash('sha256');
  hash.update(readFileSync(path));
  return hash.digest('hex');
}

function getGitMetadata() {
  const branch = run('git', ['branch', '--show-current']);
  const commit = run('git', ['rev-parse', 'HEAD']);
  const status = run('git', ['status', '--short']);

  return {
    branch: branch.status === 0 ? branch.stdout.trim() : 'unavailable',
    commit: commit.status === 0 ? commit.stdout.trim() : 'unavailable',
    status: status.status === 0 && status.stdout.trim() ? status.stdout.trim() : 'clean or unavailable',
  };
}

function copyIntoStaging(path, stagingRoot) {
  const source = join(ROOT, path);
  const destination = join(stagingRoot, path);
  mkdirSync(dirname(destination), { recursive: true });
  copyFileSync(source, destination);
}

function main() {
  if (!existsSync(join(ROOT, 'package.json')) || !existsSync(join(ROOT, 'src'))) {
    throw new Error('Run this command from the hecate946.com repository root.');
  }

  if (!hasCommand('zip')) {
    throw new Error('The `zip` command is required. Install it with: sudo apt install zip');
  }

  const candidates = [...new Set(getCandidateFiles())].sort();
  const sourceText = collectSearchableSource(candidates);
  const included = [];
  const omitted = [];

  for (const path of candidates) {
    const decision = classify(path, sourceText);
    const absolute = join(ROOT, path);
    const size = existsSync(absolute) && statSync(absolute).isFile() ? statSync(absolute).size : 0;

    if (decision.include) {
      included.push({ path, size, reason: decision.reason });
    } else if (decision.reason !== 'missing') {
      omitted.push({ path, size, reason: decision.reason });
    }
  }

  const stagingRoot = mkdtempSync(join(tmpdir(), 'hecate946-source-'));

  try {
    for (const entry of included) copyIntoStaging(entry.path, stagingRoot);

    const git = getGitMetadata();
    const manifestLines = [
      'HECATE946 SOURCE PACKAGE',
      `Generated: ${new Date().toISOString()}`,
      `Mode: ${WITH_ASSETS ? 'source plus public assets' : 'lean source'}`,
      `Git branch: ${git.branch}`,
      `Git commit: ${git.commit}`,
      '',
      'GIT STATUS',
      git.status,
      '',
      `INCLUDED FILES (${included.length})`,
      ...included.map((entry) => `${String(entry.size).padStart(12)}  ${entry.path}`),
      '',
      `OMITTED FILES (${omitted.length})`,
      ...omitted.map((entry) => {
        const absolute = join(ROOT, entry.path);
        const digest = existsSync(absolute) && statSync(absolute).isFile() ? sha256(absolute) : '-';
        return `${String(entry.size).padStart(12)}  ${entry.path}  [${entry.reason}]  sha256:${digest}`;
      }),
      '',
      'NOTES',
      '- Markdown, secrets, dependencies, build output, Git history, Blender binaries, GLBs, and rendered panoramas are intentionally excluded.',
      '- Omitted asset paths, byte sizes, and hashes are listed above so the project structure remains visible.',
      '- Run with --with-assets to include ordinary public assets; heavyweight 3D/render types remain excluded.',
      '',
    ];

    writeFileSync(join(stagingRoot, 'PROJECT_MANIFEST.txt'), manifestLines.join('\n'), 'utf8');

    rmSync(OUTPUT_PATH, { force: true });
    const zipResult = spawnSync('zip', ['-9', '-q', '-X', '-r', OUTPUT_PATH, '.'], {
      cwd: stagingRoot,
      encoding: 'utf8',
    });

    if (zipResult.status !== 0) {
      throw new Error(zipResult.stderr || zipResult.stdout || 'zip failed');
    }

    const includedBytes = included.reduce((sum, entry) => sum + entry.size, 0);
    const zipBytes = statSync(OUTPUT_PATH).size;

    console.log(`Created ${OUTPUT_PATH}`);
    console.log(`Included ${included.length} files (${formatBytes(includedBytes)} before compression).`);
    console.log(`Omitted ${omitted.length} files; details are in PROJECT_MANIFEST.txt.`);
    console.log(`ZIP size: ${formatBytes(zipBytes)}.`);
  } finally {
    rmSync(stagingRoot, { recursive: true, force: true });
  }
}

try {
  main();
} catch (error) {
  console.error(`\nSource package failed: ${error instanceof Error ? error.message : String(error)}`);
  process.exitCode = 1;
}
