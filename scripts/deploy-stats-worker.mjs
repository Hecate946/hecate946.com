import { spawn } from 'node:child_process';
import { mkdtemp, readFile, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const projectRoot = path.resolve(scriptDir, '..');
const workerDir = path.join(projectRoot, 'cloudflare', 'stats-worker');
const statsApiFile = path.join(projectRoot, 'src', 'lib', 'stats-api.ts');

const tempDirectory = await mkdtemp(path.join(tmpdir(), 'hecate-wrangler-'));
const outputFile = path.join(tempDirectory, 'deploy.ndjson');

try {
  console.log('Deploying the production stats Worker to workers.dev…');

  const exitCode = await run('npx', ['wrangler', 'deploy'], {
    cwd: workerDir,
    env: {
      ...process.env,
      WRANGLER_OUTPUT_FILE_PATH: outputFile,
    },
  });

  if (exitCode !== 0) {
    process.exitCode = exitCode;
    throw new Error('Wrangler deployment failed. The site source was not changed.');
  }

  const workerUrl = await readWorkersDevTarget(outputFile);
  await updateProductionStatsApi(workerUrl);

  console.log(`\nProduction stats endpoint: ${workerUrl}`);
  console.log('Updated src/lib/stats-api.ts automatically.');
  console.log('Localhost remains on /__local-stats and never uses this URL.');
} finally {
  await rm(tempDirectory, { recursive: true, force: true });
}

function run(command, args, options) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, {
      ...options,
      stdio: 'inherit',
    });

    child.once('error', reject);
    child.once('close', (code) => resolve(code ?? 1));
  });
}

async function readWorkersDevTarget(filename) {
  let contents;
  try {
    contents = await readFile(filename, 'utf8');
  } catch (error) {
    throw new Error(
      `Wrangler deployed, but its structured output could not be read: ${error instanceof Error ? error.message : String(error)}`,
    );
  }

  const targets = [];
  for (const line of contents.split(/\r?\n/)) {
    if (!line.trim()) continue;
    try {
      const entry = JSON.parse(line);
      if (entry?.type === 'deploy' && Array.isArray(entry.targets)) {
        targets.push(...entry.targets);
      }
    } catch {
      // Ignore non-JSON/truncated lines and continue looking for the deploy record.
    }
  }

  const workerUrl = targets.find(
    (target) =>
      typeof target === 'string' &&
      /^https:\/\/[a-z0-9.-]+\.workers\.dev\/?$/i.test(target.trim()),
  );

  if (!workerUrl) {
    throw new Error(
      'Wrangler deployed, but no workers.dev target was reported. Ensure workers.dev is enabled for your Cloudflare account and run `npm run stats:deploy` again.',
    );
  }

  return workerUrl.trim().replace(/\/$/, '');
}

async function updateProductionStatsApi(workerUrl) {
  const source = await readFile(statsApiFile, 'utf8');
  const pattern = /export const PROD_STATS_API_BASE = '[^']*';/;

  if (!pattern.test(source)) {
    throw new Error(
      'Could not find PROD_STATS_API_BASE in src/lib/stats-api.ts. The Worker deployed, but the website endpoint was not updated.',
    );
  }

  const nextSource = source.replace(
    pattern,
    `export const PROD_STATS_API_BASE = '${workerUrl}';`,
  );

  await writeFile(statsApiFile, nextSource);
}
