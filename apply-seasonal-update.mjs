import { readFile, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';

const root = process.cwd();
const selectorPath = resolve(
  root,
  'src/components/islands/SeasonSelector.svelte',
);
const showerPath = resolve(
  root,
  'src/components/islands/SeasonalShower.svelte',
);
const rendererPath = resolve(root, 'src/lib/seasonal/autumnLeaves.ts');

const springBlock = `{#if season.id === 'spring'}
        <svg viewBox="0 0 32 32" aria-hidden="true">
          <g
            fill="none"
            stroke="currentColor"
            stroke-width="1.55"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <ellipse cx="16" cy="8.9" rx="3.85" ry="6.15"></ellipse>
            <ellipse cx="16" cy="8.9" rx="3.85" ry="6.15" transform="rotate(72 16 16)"></ellipse>
            <ellipse cx="16" cy="8.9" rx="3.85" ry="6.15" transform="rotate(144 16 16)"></ellipse>
            <ellipse cx="16" cy="8.9" rx="3.85" ry="6.15" transform="rotate(216 16 16)"></ellipse>
            <ellipse cx="16" cy="8.9" rx="3.85" ry="6.15" transform="rotate(288 16 16)"></ellipse>
            <circle cx="16" cy="16" r="2.65"></circle>
          </g>
        </svg>
      {:else if season.id === 'summer'}`;

function removeFunction(source, functionName) {
  const marker = `function ${functionName}(`;
  const start = source.indexOf(marker);
  if (start === -1) return source;

  const openingBrace = source.indexOf('{', start);
  if (openingBrace === -1) {
    throw new Error(`Could not find the opening brace for ${functionName}.`);
  }

  let depth = 0;
  let end = -1;

  for (let index = openingBrace; index < source.length; index += 1) {
    const character = source[index];
    if (character === '{') depth += 1;
    if (character === '}') {
      depth -= 1;
      if (depth === 0) {
        end = index + 1;
        break;
      }
    }
  }

  if (end === -1) {
    throw new Error(`Could not find the closing brace for ${functionName}.`);
  }

  const lineStart = source.lastIndexOf('\n', start) + 1;
  const before = source
    .slice(0, lineStart)
    .replace(/[ \t]*\n(?:[ \t]*\n)*$/, '\n\n');
  const after = source.slice(end).replace(/^(?:[ \t]*\n)+/, '');
  return before + after;
}

async function updateSelector() {
  const source = await readFile(selectorPath, 'utf8');
  const pattern = /{#if season\.id === 'spring'}[\s\S]*?{:else if season\.id === 'summer'}/;

  if (!pattern.test(source)) {
    throw new Error('Could not locate the spring icon block in SeasonSelector.svelte.');
  }

  await writeFile(selectorPath, source.replace(pattern, springBlock));
}

async function updateShower() {
  let source = await readFile(showerPath, 'utf8');
  await readFile(rendererPath, 'utf8');

  const importLine =
    "import { drawAutumnLeafSprite } from '@/lib/seasonal/autumnLeaves';";

  if (!source.includes(importLine)) {
    const mountImport = "import { onMount } from 'svelte';";
    if (!source.includes(mountImport)) {
      throw new Error('Could not locate the Svelte import in SeasonalShower.svelte.');
    }
    source = source.replace(mountImport, `${mountImport}\n  ${importLine}`);
  }

  const oldCall = "if (season === 'autumn') drawAutumnLeaf(context, variant);";
  const newCall =
    "if (season === 'autumn') drawAutumnLeafSprite(context, variant);";

  if (source.includes(oldCall)) {
    source = source.replace(oldCall, newCall);
  } else if (!source.includes(newCall)) {
    throw new Error('Could not locate the autumn sprite call in SeasonalShower.svelte.');
  }

  source = removeFunction(source, 'drawAutumnLeaf');
  await writeFile(showerPath, source);
}

await updateSelector();
await updateShower();

console.log('Updated the spring selector icon and autumn leaf sprites.');
