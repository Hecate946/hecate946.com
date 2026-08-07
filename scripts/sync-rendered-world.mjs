import { access, copyFile, mkdir, readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const sourcePath = path.join(root, 'src', 'content', 'site-world.json');
const buildRoot = path.join(root, 'blender', 'world', 'build');
const publicRoot = path.join(root, 'public', 'scenes', 'world');

async function exists(file) {
  try { await access(file); return true; } catch { return false; }
}

const world = JSON.parse(await readFile(sourcePath, 'utf8'));
const manifest = {
  version: world.version,
  startView: world.startView,
  views: [],
};

await mkdir(path.join(publicRoot, 'views'), { recursive: true });

for (const view of world.views) {
  const projectionFile = path.join(buildRoot, `${view.id}.json`);
  let projected = new Map();
  if (await exists(projectionFile)) {
    const data = JSON.parse(await readFile(projectionFile, 'utf8'));
    projected = new Map((data.hotspots ?? []).map((item) => [item.id, item.bounds]));
  }

  const blender = view.blender ?? {};
  let image = view.image;
  if (blender.sourceImage) {
    const sourceImage = path.join(root, blender.sourceImage);
    if (await exists(sourceImage)) {
      const extension = path.extname(sourceImage) || '.png';
      const destinationName = `${view.id}${extension}`;
      const destination = path.join(publicRoot, 'views', destinationName);
      await copyFile(sourceImage, destination);
      image = `/scenes/world/views/${destinationName}`;
      console.log(`Published ${path.relative(root, destination)}`);
    } else if (view.fallbackImage) {
      image = view.fallbackImage;
    }
  }

  manifest.views.push({
    id: view.id,
    label: view.label,
    description: view.description,
    image,
    fallbackImage: view.fallbackImage,
    width: view.width,
    height: view.height,
    hotspots: view.hotspots.map((hotspot) => ({
      id: hotspot.id,
      label: hotspot.label,
      href: hotspot.href,
      targetView: hotspot.targetView,
      bounds: projected.get(hotspot.id) ?? hotspot.bootstrapBounds,
    })),
  });
}

await mkdir(publicRoot, { recursive: true });
await writeFile(path.join(publicRoot, 'manifest.json'), `${JSON.stringify(manifest, null, 2)}\n`);
console.log(`Published ${path.relative(root, path.join(publicRoot, 'manifest.json'))}`);
