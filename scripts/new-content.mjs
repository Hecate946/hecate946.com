import { mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';

const [collection, rawSlug] = process.argv.slice(2);

if (!collection || !rawSlug) {
  console.error(
    'Usage: npm run content:new -- <projects|music|chess|pickleball|notes> <slug>',
  );
  process.exit(1);
}

const slug = rawSlug
  .trim()
  .toLowerCase()
  .replace(/[^a-z0-9]+/g, '-')
  .replace(/^-|-$/g, '');

const today = new Date().toISOString().slice(0, 10);
const templates = {
  projects: `---\ntitle: New Project\ndescription: Replace this description.\npublishedAt: ${today}\nstatus: idea\ntechnologies: []\ntags: []\n---\n\nStart writing here.\n`,
  music: `---\ntitle: New Music Entry\ndescription: Replace this description.\npublishedAt: ${today}\ninstrument: clarinet\ncomposer: Replace me\nwork: Replace me\ntags: []\n---\n\nStart writing here.\n`,
  chess: `---\ntitle: New Chess Entry\ndescription: Replace this description.\npublishedAt: ${today}\nresult: study\ntags: []\n---\n\nStart writing here.\n`,
  pickleball: `---\ntitle: New Pickleball Entry\ndescription: Replace this description.\npublishedAt: ${today}\nkind: training\ntags: []\n---\n\nStart writing here.\n`,
  notes: `---\ntitle: New Note\ndescription: Replace this description.\npublishedAt: ${today}\ncategory: general\ntags: []\n---\n\nStart writing here.\n`,
};

if (!Object.hasOwn(templates, collection)) {
  console.error(
    'Unknown collection. Use projects, music, chess, pickleball, or notes.',
  );
  process.exit(1);
}

const collectionKey = /** @type {keyof typeof templates} */ (collection);
const directory = path.join('src', 'content', collectionKey);
const destination = path.join(directory, `${slug}.md`);
await mkdir(directory, { recursive: true });
await writeFile(destination, templates[collectionKey], { flag: 'wx' });
console.log(`Created ${destination}`);
