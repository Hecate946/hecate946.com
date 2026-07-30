import { access, copyFile, mkdir } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const projectRoot = path.resolve(scriptDirectory, '..');
const publicRoot = path.join(projectRoot, 'public', 'scenes');

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
    required: true,
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
