import { access, readFile } from 'node:fs/promises';
import { spawnSync } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const world = JSON.parse(await readFile(path.join(root, 'src/content/site-world.json'), 'utf8'));
const requested = process.argv.slice(2).filter((arg) => !arg.startsWith('-'));
const selected = requested.length ? world.views.filter((view) => requested.includes(view.id)) : world.views;
if (!selected.length) {
  console.error(`No matching views. Available: ${world.views.map((view) => view.id).join(', ')}`);
  process.exit(1);
}

const blenderBin = process.env.BLENDER_BIN || 'blender';

function run(args, label) {
  console.log(`\n${label}`);
  const result = spawnSync(blenderBin, args, { cwd: root, stdio: 'inherit' });
  if (result.error?.code === 'ENOENT') {
    console.error(`Blender executable not found. Set BLENDER_BIN or install Blender so \`${blenderBin}\` is available.`);
    process.exit(1);
  }
  if (result.status !== 0) process.exit(result.status ?? 1);
}

for (const view of selected) {
  const config = view.blender;
  if (!config) continue;
  if (config.buildScript) {
    run(['--background', '--python', config.buildScript], `Building Blender source for ${view.id}...`);
  }
  const blendFile = path.join(root, config.blendFile);
  try { await access(blendFile); } catch {
    console.error(`Missing ${config.blendFile}; its build step did not create the expected Blender file.`);
    process.exit(1);
  }
  run([
    '--background', config.blendFile,
    '--python', 'blender/world/export_rendered_world.py',
    '--', '--view', view.id,
  ], `Exporting camera-space hotspots for ${view.id}...`);
}

const sync = spawnSync(process.execPath, ['scripts/sync-rendered-world.mjs'], { cwd: root, stdio: 'inherit' });
process.exit(sync.status ?? 0);
