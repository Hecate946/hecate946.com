import { access, copyFile, mkdir, rename, rm, stat } from 'node:fs/promises';
import { spawn, spawnSync } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const projectRoot = path.resolve(scriptDirectory, '..');
const publicRoot = path.join(projectRoot, 'public', 'scenes');

const roomSlugs = ['red', 'green', 'orange', 'blue', 'purple'];
const hallSlugs = ['ballroom', 'museum'];
const webpQuality = Number.parseInt(process.env.SCENE_WEBP_QUALITY ?? '82', 10);

if (!Number.isInteger(webpQuality) || webpQuality < 1 || webpQuality > 100) {
  throw new Error('SCENE_WEBP_QUALITY must be an integer from 1 to 100.');
}

let copied = 0;
let encoded = 0;
let skipped = 0;
let missingRequired = 0;
let missingOptional = 0;

async function exists(filePath) {
  try {
    await access(filePath);
    return true;
  } catch {
    return false;
  }
}

function commandWorks(command) {
  const result = spawnSync(command, ['-version'], {
    stdio: 'ignore',
  });
  return !result.error && result.status === 0;
}

function findWebpEncoder() {
  if (commandWorks('cwebp')) return { command: 'cwebp', kind: 'cwebp' };
  if (commandWorks('magick')) return { command: 'magick', kind: 'imagemagick' };
  if (commandWorks('convert')) return { command: 'convert', kind: 'imagemagick' };
  return null;
}

function run(command, args) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, {
      cwd: projectRoot,
      stdio: ['ignore', 'ignore', 'pipe'],
    });

    let stderr = '';
    child.stderr.setEncoding('utf8');
    child.stderr.on('data', (chunk) => {
      stderr += chunk;
    });

    child.on('error', reject);
    child.on('close', (code) => {
      if (code === 0) {
        resolve();
        return;
      }

      reject(
        new Error(
          `${command} exited with code ${code}${stderr.trim() ? `:\n${stderr.trim()}` : ''}`,
        ),
      );
    });
  });
}

async function recordMissing({ source, required, label }) {
  const relative = path.relative(projectRoot, source);
  if (required) {
    console.warn(`Missing required ${label}: ${relative}`);
    missingRequired += 1;
  } else {
    missingOptional += 1;
  }
}

async function copyAsset({ source, destination, required = false, label }) {
  if (!(await exists(source))) {
    await recordMissing({ source, required, label });
    return;
  }

  await mkdir(path.dirname(destination), { recursive: true });
  await copyFile(source, destination);
  console.log(`Copied ${path.relative(projectRoot, destination)}`);
  copied += 1;
}

async function isDestinationCurrent(source, destination) {
  if (!(await exists(destination))) return false;

  const [sourceStats, destinationStats] = await Promise.all([
    stat(source),
    stat(destination),
  ]);

  return destinationStats.mtimeMs >= sourceStats.mtimeMs;
}

async function encodeWebpAsset({
  source,
  destination,
  legacyPngDestination,
  required = false,
  label,
  encoder,
}) {
  if (!(await exists(source))) {
    await recordMissing({ source, required, label });
    return;
  }

  await mkdir(path.dirname(destination), { recursive: true });

  if (await isDestinationCurrent(source, destination)) {
    await rm(legacyPngDestination, { force: true });
    console.log(`Up to date ${path.relative(projectRoot, destination)}`);
    skipped += 1;
    return;
  }

  const temporaryDestination = `${destination}.tmp.webp`;
  await rm(temporaryDestination, { force: true });

  const args =
    encoder.kind === 'cwebp'
      ? [
          '-quiet',
          '-mt',
          '-q',
          String(webpQuality),
          '-m',
          '6',
          source,
          '-o',
          temporaryDestination,
        ]
      : [
          source,
          '-strip',
          '-quality',
          String(webpQuality),
          '-define',
          'webp:method=6',
          temporaryDestination,
        ];

  try {
    await run(encoder.command, args);
    await rename(temporaryDestination, destination);
    await rm(legacyPngDestination, { force: true });
    console.log(`Encoded ${path.relative(projectRoot, destination)}`);
    encoded += 1;
  } catch (error) {
    await rm(temporaryDestination, { force: true });
    throw new Error(`Failed to encode ${label}: ${error.message}`, { cause: error });
  }
}

const webpEncoder = findWebpEncoder();
if (!webpEncoder) {
  console.error(
    [
      'No WebP encoder was found.',
      'On Ubuntu, install one with:',
      '  sudo apt update && sudo apt install webp',
      'Then run npm run assets:sync again.',
    ].join('\n'),
  );
  process.exit(1);
}

console.log(`Using ${webpEncoder.command} for WebP encoding at quality ${webpQuality}.\n`);

await copyAsset({
  source: path.join(projectRoot, 'blender', 'house', 'house.png'),
  destination: path.join(publicRoot, 'house', 'shell.png'),
  required: true,
  label: 'house shell render',
});

await copyAsset({
  source: path.join(projectRoot, 'blender', 'house', 'house.glb'),
  destination: path.join(publicRoot, 'house', 'shell.glb'),
  label: 'house shell model',
});

for (const slug of roomSlugs) {
  const sourceRoot = path.join(projectRoot, 'blender', 'rooms', slug);
  const destinationRoot = path.join(publicRoot, 'rooms', slug);

  await encodeWebpAsset({
    source: path.join(sourceRoot, `${slug}-room-panorama.png`),
    destination: path.join(destinationRoot, 'panorama.webp'),
    legacyPngDestination: path.join(destinationRoot, 'panorama.png'),
    required: true,
    label: `${slug} room panorama`,
    encoder: webpEncoder,
  });

  await copyAsset({
    source: path.join(sourceRoot, `${slug}-room-interactive.glb`),
    destination: path.join(destinationRoot, 'interactive.glb'),
    required: true,
    label: `${slug} room interactive model`,
  });
}

for (const slug of hallSlugs) {
  const sourceRoot = path.join(projectRoot, 'blender', 'halls', slug);
  const destinationRoot = path.join(publicRoot, 'halls', slug);
  const implemented = slug === 'ballroom';

  await encodeWebpAsset({
    source: path.join(sourceRoot, `${slug}.png`),
    destination: path.join(destinationRoot, 'panorama.webp'),
    legacyPngDestination: path.join(destinationRoot, 'panorama.png'),
    required: implemented,
    label: `${slug} panorama`,
    encoder: webpEncoder,
  });

  await copyAsset({
    source: path.join(sourceRoot, `${slug}.glb`),
    destination: path.join(destinationRoot, 'scene.glb'),
    label: `${slug} complete model`,
  });

  await copyAsset({
    source: path.join(sourceRoot, `${slug}-interactive.glb`),
    destination: path.join(destinationRoot, 'interactive.glb'),
    label: `${slug} interactive model`,
  });
}

console.log(
  `\nScene asset sync complete: ${encoded} WebP encoded, ${copied} copied, ${skipped} already current.`,
);
if (missingRequired > 0) {
  console.warn(
    `${missingRequired} required asset(s) are missing. Render/export them in Blender and run this command again.`,
  );
}
if (missingOptional > 0) {
  console.log(`${missingOptional} optional asset(s) are not present yet.`);
}

process.exitCode = missingRequired > 0 ? 1 : 0;
