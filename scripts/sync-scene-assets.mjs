import { access, copyFile, mkdir, readdir } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const projectRoot = path.resolve(scriptDirectory, '..');
const publicRoot = path.join(projectRoot, 'public', 'scenes');
const blenderSharedAssetsRoot = path.join(projectRoot, 'blender', 'assets');
const publicSharedAssetsRoot = path.join(publicRoot, 'assets');

const roomSlugs = ['red', 'green', 'orange', 'blue', 'purple'];
const hallSlugs = ['ballroom', 'museum'];

let copied = 0;
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

async function copyAsset({ source, destination, required = false, label }) {
  if (!(await exists(source))) {
    const relative = path.relative(projectRoot, source);
    if (required) {
      console.warn(`Missing required ${label}: ${relative}`);
      missingRequired += 1;
    } else {
      missingOptional += 1;
    }
    return;
  }

  await mkdir(path.dirname(destination), { recursive: true });
  await copyFile(source, destination);
  console.log(`Copied ${path.relative(projectRoot, destination)}`);
  copied += 1;
}

async function findGlbFiles(directory) {
  let entries;
  try {
    entries = await readdir(directory, { withFileTypes: true });
  } catch (error) {
    if (error?.code === 'ENOENT') return [];
    throw error;
  }

  const files = [];
  for (const entry of entries) {
    const absolute = path.join(directory, entry.name);
    if (entry.isDirectory()) {
      files.push(...(await findGlbFiles(absolute)));
    } else if (entry.isFile() && path.extname(entry.name).toLowerCase() === '.glb') {
      files.push(absolute);
    }
  }

  return files.sort((left, right) => left.localeCompare(right));
}

async function syncSharedGlbs() {
  const sharedGlbs = await findGlbFiles(blenderSharedAssetsRoot);

  if (sharedGlbs.length === 0) {
    console.log('No reusable GLBs found beneath blender/assets.');
    return;
  }

  console.log(`Publishing ${sharedGlbs.length} reusable shared GLB(s)...`);
  for (const source of sharedGlbs) {
    const relativeAssetPath = path.relative(blenderSharedAssetsRoot, source);
    await copyAsset({
      source,
      destination: path.join(publicSharedAssetsRoot, relativeAssetPath),
      required: true,
      label: `shared asset ${relativeAssetPath}`,
    });
  }
}

await syncSharedGlbs();

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

  await copyAsset({
    source: path.join(sourceRoot, `${slug}-room-panorama.png`),
    destination: path.join(destinationRoot, 'panorama.png'),
    required: true,
    label: `${slug} room panorama`,
  });

  await copyAsset({
    source: path.join(sourceRoot, `${slug}-room-interactive.glb`),
    destination: path.join(destinationRoot, 'interactive.glb'),
    required: true,
    label: `${slug} room interactive model`,
  });
}

await copyAsset({
  source: path.join(projectRoot, 'blender', 'halls', 'shared', 'hall-shell.glb'),
  destination: path.join(publicRoot, 'halls', 'shared', 'shell.glb'),
  required: true,
  label: 'shared hall shell model',
});

for (const slug of hallSlugs) {
  const sourceRoot = path.join(projectRoot, 'blender', 'halls', slug);
  const destinationRoot = path.join(publicRoot, 'halls', slug);

  await copyAsset({
    source: path.join(sourceRoot, `${slug}-objects.glb`),
    destination: path.join(destinationRoot, 'objects.glb'),
    required: slug !== 'ballroom',
    label: `${slug} object model`,
  });
}

console.log(`\nScene asset sync complete: ${copied} copied.`);
if (missingRequired > 0) {
  console.warn(`${missingRequired} required asset(s) are missing. Render/export them in Blender and run this command again.`);
}
if (missingOptional > 0) {
  console.log(`${missingOptional} optional asset(s) are not present yet.`);
}

process.exitCode = missingRequired > 0 ? 1 : 0;
