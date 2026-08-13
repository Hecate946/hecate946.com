import { readFile, readdir, stat } from 'node:fs/promises';
import path from 'node:path';
import process from 'node:process';

const root = process.cwd();
const dist = path.join(root, 'dist');
const canonicalOrigin = 'https://hecate946.com';
const errors = [];
const warnings = [];

const normalizeSlashes = (value) => value.replaceAll('\\', '/');

async function exists(file) {
  try {
    await stat(file);
    return true;
  } catch {
    return false;
  }
}

async function walk(directory) {
  const entries = await readdir(directory, { withFileTypes: true });
  const files = [];
  for (const entry of entries) {
    const full = path.join(directory, entry.name);
    if (entry.isDirectory()) files.push(...(await walk(full)));
    else files.push(full);
  }
  return files;
}

function matches(html, expression) {
  return expression.test(html);
}

function capture(html, expression) {
  return html.match(expression)?.[1]?.trim();
}

function routeForHtml(file) {
  const rel = normalizeSlashes(path.relative(dist, file));
  if (rel === 'index.html') return '/';
  if (rel.endsWith('/index.html')) return `/${rel.slice(0, -'/index.html'.length)}/`;
  return `/${rel}`;
}

function assetPathFromUrl(url) {
  const parsed = new URL(url, canonicalOrigin);
  if (parsed.origin !== canonicalOrigin) return null;
  return decodeURIComponent(parsed.pathname);
}

async function resolvesInDist(urlPath) {
  if (!urlPath || urlPath === '/') return exists(path.join(dist, 'index.html'));
  const clean = urlPath.replace(/^\/+/, '');
  const direct = path.join(dist, clean);
  if (await exists(direct)) return true;
  if (await exists(`${direct}.html`)) return true;
  if (await exists(path.join(direct, 'index.html'))) return true;
  return false;
}

function allTags(html, tagName) {
  return [...html.matchAll(new RegExp(`<${tagName}\\b[^>]*>`, 'gi'))].map((match) => match[0]);
}

function attr(tag, name) {
  const match = tag.match(new RegExp(`\\b${name}=["']([^"']*)["']`, 'i'));
  return match?.[1];
}

if (!(await exists(dist))) {
  console.error('Production audit: dist/ does not exist. Run the Astro build first.');
  process.exit(1);
}

const requiredFiles = [
  'robots.txt',
  'sitemap-index.xml',
  'site.webmanifest',
  '.well-known/security.txt',
  'favicon.ico',
  'favicon.png',
  'favicon-48.png',
  'apple-touch-icon.png',
  'icon-192.png',
  'images/social/home.jpg',
];

for (const required of requiredFiles) {
  if (!(await exists(path.join(dist, required)))) errors.push(`Missing production file: /${required}`);
}

const manifestPath = path.join(dist, 'site.webmanifest');
if (await exists(manifestPath)) {
  try {
    const manifest = JSON.parse(await readFile(manifestPath, 'utf8'));
    if (!manifest.name || !manifest.short_name) errors.push('site.webmanifest is missing name/short_name.');
    if (!Array.isArray(manifest.icons) || manifest.icons.length < 2) {
      errors.push('site.webmanifest should advertise both app icon sizes.');
    }
  } catch (error) {
    errors.push(`site.webmanifest is invalid JSON (${error instanceof Error ? error.message : error}).`);
  }
}

const robotsPath = path.join(dist, 'robots.txt');
if (await exists(robotsPath)) {
  const robots = await readFile(robotsPath, 'utf8');
  if (!/User-agent:\s*\*/i.test(robots)) errors.push('robots.txt has no wildcard user-agent.');
  if (!/Allow:\s*\//i.test(robots)) errors.push('robots.txt does not allow the public site.');
  if (!/Sitemap:\s*https:\/\/hecate946\.com\/sitemap-index\.xml/i.test(robots)) {
    errors.push('robots.txt does not advertise the canonical sitemap-index.xml URL.');
  }
}

const securityPath = path.join(dist, '.well-known/security.txt');
if (await exists(securityPath)) {
  const security = await readFile(securityPath, 'utf8');
  for (const field of ['Contact:', 'Expires:', 'Canonical:', 'Preferred-Languages:']) {
    if (!security.includes(field)) errors.push(`security.txt is missing ${field}`);
  }
  const expiry = security.match(/^Expires:\s*(.+)$/im)?.[1]?.trim();
  if (expiry && Number.isFinite(Date.parse(expiry))) {
    const daysRemaining = (Date.parse(expiry) - Date.now()) / 86_400_000;
    if (daysRemaining < 30) warnings.push('security.txt expires in fewer than 30 days.');
  }
}

const files = await walk(dist);
const sitemapFiles = files.filter((file) => /sitemap(?:-\d+)?\.xml$/i.test(file));
for (const sitemapFile of sitemapFiles) {
  const sitemap = await readFile(sitemapFile, 'utf8');
  if (/http:\/\/(?:www\.)?hecate946\.com/i.test(sitemap)) {
    errors.push(`${path.basename(sitemapFile)} contains a non-HTTPS canonical-domain URL.`);
  }
  for (const forbidden of ['/404/', '/pdf/']) {
    if (sitemap.includes(`${canonicalOrigin}${forbidden}`)) {
      errors.push(`${path.basename(sitemapFile)} contains non-canonical/noindex route ${forbidden}.`);
    }
  }
}

const htmlFiles = files.filter((file) => file.endsWith('.html'));
const seenTitles = new Map();
const seenDescriptions = new Map();

for (const file of htmlFiles) {
  const html = await readFile(file, 'utf8');
  const route = routeForHtml(file);
  const label = route;
  const noindex = /<meta\s+name=["']robots["'][^>]*content=["'][^"']*noindex/i.test(html);

  if (!/<html\b[^>]*\blang=["']en-US["']/i.test(html)) {
    errors.push(`${label}: missing the expected html lang="en-US".`);
  }

  if (/\b(?:localhost|127\.0\.0\.1)(?::\d+)?\b/i.test(html)) {
    errors.push(`${label}: contains a localhost/127.0.0.1 production reference.`);
  }
  if (/http:\/\/(?:www\.)?hecate946\.com/i.test(html)) {
    errors.push(`${label}: contains a non-HTTPS canonical-domain reference.`);
  }

  const title = capture(html, /<title>([^<]+)<\/title>/i);
  const description = capture(
    html,
    /<meta\s+name=["']description["']\s+content=["']([^"']+)["'][^>]*>/i,
  );
  const canonical = capture(
    html,
    /<link\s+rel=["']canonical["']\s+href=["']([^"']+)["'][^>]*>/i,
  );

  if (!title) errors.push(`${label}: missing <title>.`);
  if (!description) errors.push(`${label}: missing meta description.`);
  if (!canonical) errors.push(`${label}: missing canonical URL.`);

  if (!noindex) {
    const expectedCanonical = new URL(route, canonicalOrigin).href;
    if (canonical && canonical !== expectedCanonical) {
      errors.push(`${label}: canonical is ${canonical}; expected ${expectedCanonical}.`);
    }

    for (const [name, expression] of [
      ['og:title', /<meta\s+property=["']og:title["'][^>]*>/i],
      ['og:description', /<meta\s+property=["']og:description["'][^>]*>/i],
      ['og:url', /<meta\s+property=["']og:url["'][^>]*>/i],
      ['og:image', /<meta\s+property=["']og:image["'][^>]*>/i],
      ['og:image:width', /<meta\s+property=["']og:image:width["'][^>]*>/i],
      ['og:image:height', /<meta\s+property=["']og:image:height["'][^>]*>/i],
      ['twitter:card', /<meta\s+name=["']twitter:card["'][^>]*>/i],
      ['twitter:title', /<meta\s+name=["']twitter:title["'][^>]*>/i],
      ['twitter:description', /<meta\s+name=["']twitter:description["'][^>]*>/i],
      ['twitter:image', /<meta\s+name=["']twitter:image["'][^>]*>/i],
    ]) {
      if (!matches(html, expression)) errors.push(`${label}: missing ${name} social metadata.`);
    }

    if (!/<meta\s+name=["']twitter:card["']\s+content=["']summary["'][^>]*>/i.test(html)) {
      errors.push(`${label}: Twitter card is not the compact summary format.`);
    }

    if (!/<h1\b/i.test(html)) errors.push(`${label}: indexable page has no <h1>.`);

    const ogImage = capture(
      html,
      /<meta\s+property=["']og:image["']\s+content=["']([^"']+)["'][^>]*>/i,
    );
    if (ogImage) {
      try {
        const ogImageUrl = new URL(ogImage, canonicalOrigin);
        if (ogImageUrl.origin === canonicalOrigin && !(await resolvesInDist(decodeURIComponent(ogImageUrl.pathname)))) {
          errors.push(`${label}: og:image does not resolve in dist (${ogImageUrl.pathname}).`);
        }
      } catch {
        errors.push(`${label}: og:image is not a valid URL (${ogImage}).`);
      }
    }

    const jsonLdScripts = [
      ...html.matchAll(/<script\s+[^>]*type=["']application\/ld\+json["'][^>]*>([\s\S]*?)<\/script>/gi),
    ];
    if (jsonLdScripts.length === 0) {
      errors.push(`${label}: missing JSON-LD structured data.`);
    } else {
      for (const script of jsonLdScripts) {
        try {
          JSON.parse(script[1]);
        } catch (error) {
          errors.push(`${label}: invalid JSON-LD (${error instanceof Error ? error.message : error}).`);
        }
      }
    }

    if (title) {
      const existing = seenTitles.get(title);
      if (existing && existing !== route) warnings.push(`Duplicate title: ${title} (${existing}, ${route}).`);
      else seenTitles.set(title, route);
    }
    if (description) {
      const existing = seenDescriptions.get(description);
      if (existing && existing !== route) warnings.push(`Duplicate description on ${existing} and ${route}.`);
      else seenDescriptions.set(description, route);
    }
  }

  for (const tag of allTags(html, 'img')) {
    if (attr(tag, 'alt') === undefined) {
      errors.push(`${label}: <img> is missing an alt attribute (${tag.slice(0, 120)}...).`);
    }
  }

  for (const tag of allTags(html, 'a')) {
    const href = attr(tag, 'href');
    if (!href || href.startsWith('#') || href.startsWith('mailto:') || href.startsWith('tel:') || href.startsWith('javascript:')) continue;

    const target = attr(tag, 'target')?.toLowerCase();
    const rel = attr(tag, 'rel') ?? '';
    if (target === '_blank' && !/\bnoopener\b/i.test(rel)) {
      errors.push(`${label}: target="_blank" link lacks rel="noopener" (${href}).`);
    }

    let parsed;
    try {
      parsed = new URL(href, canonicalOrigin);
    } catch {
      errors.push(`${label}: invalid link URL (${href}).`);
      continue;
    }
    if (parsed.origin !== canonicalOrigin) continue;
    const internalPath = decodeURIComponent(parsed.pathname);
    if (!(await resolvesInDist(internalPath))) {
      errors.push(`${label}: broken internal link ${internalPath}.`);
    }
  }

  for (const tagName of ['img', 'source', 'script', 'link']) {
    for (const tag of allTags(html, tagName)) {
      // <link rel="canonical"> identifies the preferred document URL; it is
      // not a downloadable local asset. In particular, Astro emits the custom
      // 404 document as /404.html while its logical route can be /404/. The
      // canonical itself is validated separately above, so exclude canonical
      // links from this resource-existence pass.
      if (tagName === 'link') {
        const rel = (attr(tag, 'rel') ?? '').toLowerCase().split(/\s+/);
        if (rel.includes('canonical')) continue;
      }

      const url = attr(tag, tagName === 'link' ? 'href' : 'src');
      if (!url || url.startsWith('data:')) continue;
      let internalPath;
      try {
        internalPath = assetPathFromUrl(url);
      } catch {
        continue;
      }
      if (!internalPath) continue;
      if (!(await resolvesInDist(internalPath))) {
        errors.push(`${label}: missing local ${tagName} resource ${internalPath}.`);
      }
    }
  }
}

const astroConfig = await readFile(path.join(root, 'astro.config.mjs'), 'utf8');
if (/clientPrerender\s*:/i.test(astroConfig)) {
  errors.push('astro.config.mjs re-enabled experimental clientPrerender; this previously caused production blank-room failures.');
}

for (const warning of warnings) console.warn(`WARN  ${warning}`);
for (const error of errors) console.error(`ERROR ${error}`);

if (errors.length) {
  console.error(`\nProduction audit failed with ${errors.length} error(s) and ${warnings.length} warning(s).`);
  process.exit(1);
}

console.log(`Production audit passed: ${htmlFiles.length} HTML pages, ${warnings.length} warning(s).`);
