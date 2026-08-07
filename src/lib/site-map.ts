import siteWorld from '@/content/site-world.json';
import type { NetworkLink, NetworkNode } from '@/components/graphs/types';

export type SiteMapCategory =
  | 'core'
  | 'profile'
  | 'projects'
  | 'spaces'
  | 'experiments';

export type SiteMapRoute = {
  href: string;
  label: string;
  description?: string;
  category?: SiteMapCategory;
};

export type SiteMapGraph = {
  nodes: NetworkNode[];
  links: NetworkLink[];
};

type BuildSiteMapOptions = {
  pageFiles: readonly string[];
  dynamicRoutes?: readonly SiteMapRoute[];
  currentPath: string;
  resolveHref: (href: string) => string;
};

const PAGE_METADATA: Record<
  string,
  Omit<SiteMapRoute, 'href'> & { category: SiteMapCategory }
> = {
  '/': {
    label: 'Home',
    description: 'The center of the site',
    category: 'core',
  },
  '/graph/': {
    label: 'Graph',
    description: 'Interactive map of every site destination',
    category: 'core',
  },
  '/about/': {
    label: 'About',
    description: 'Biography and current work',
    category: 'profile',
  },
  '/resume/': {
    label: 'Resume',
    description: 'Software and music experience',
    category: 'profile',
  },
  '/contact/': {
    label: 'Contact',
    description: 'Ways to get in touch',
    category: 'profile',
  },
  '/stats/': {
    label: 'Stats',
    description: 'Live site and activity statistics',
    category: 'profile',
  },
  '/projects/': {
    label: 'Projects',
    description: 'Selected software and design work',
    category: 'projects',
  },
  '/rooms/': {
    label: 'Rooms',
    description: 'Immersive rooms in the house',
    category: 'spaces',
  },
  '/halls/': {
    label: 'Halls',
    description: 'Large immersive spaces',
    category: 'spaces',
  },
  '/collision-detection/': {
    label: 'Collision Physics',
    description: 'Rapier seasonal-object simulation',
    category: 'experiments',
  },
  '/d3/': {
    label: 'D3 Laboratory',
    description: 'Interactive force and data experiments',
    category: 'experiments',
  },
  '/house-compare/': {
    label: 'House Comparison',
    description: 'House rendering comparisons',
    category: 'experiments',
  },
  '/house-png/': {
    label: 'House PNG',
    description: 'Raster house preview',
    category: 'experiments',
  },
  '/house-svg/': {
    label: 'House SVG',
    description: 'Vector house preview',
    category: 'experiments',
  },
  '/chess-board/': {
    label: 'Chess Board',
    description: 'Interactive chess-board study',
    category: 'experiments',
  },
  '/pickleball/': {
    label: 'Pickleball',
    description: 'Pickleball interaction study',
    category: 'experiments',
  },
  '/picklabell/': {
    label: 'Picklabell',
    description: 'Pickleball prototype',
    category: 'experiments',
  },
};

const CATEGORY_CENTERS: Record<SiteMapCategory, { x: number; y: number }> = {
  core: { x: 0.5, y: 0.5 },
  profile: { x: 0.5, y: 0.2 },
  projects: { x: 0.22, y: 0.59 },
  spaces: { x: 0.78, y: 0.48 },
  experiments: { x: 0.53, y: 0.79 },
};

const CATEGORY_ACCENTS: Record<SiteMapCategory, string> = {
  core: 'var(--accent)',
  profile: 'var(--season-1)',
  projects: 'var(--season-2)',
  spaces: 'var(--season-3)',
  experiments: 'var(--accent-strong)',
};

const clamp = (value: number, minimum: number, maximum: number) =>
  Math.min(maximum, Math.max(minimum, value));

export function normalizeSitePath(value: string) {
  const clean = value.split(/[?#]/, 1)[0]?.replace(/\/{2,}/g, '/') || '/';
  const withLeadingSlash = clean.startsWith('/') ? clean : `/${clean}`;
  if (withLeadingSlash === '/') return '/';
  return `${withLeadingSlash.replace(/\/+$/, '')}/`;
}

function humanizeSegment(value: string) {
  return value
    .replace(/[-_]+/g, ' ')
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

function categoryForPath(path: string): SiteMapCategory {
  if (path === '/') return 'core';
  if (/^\/(about|resume|contact|stats)\//.test(path)) return 'profile';
  if (path.startsWith('/projects/')) return 'projects';
  if (path.startsWith('/rooms/') || path.startsWith('/halls/')) return 'spaces';
  return 'experiments';
}

function labelForPath(path: string) {
  const metadata = PAGE_METADATA[path];
  if (metadata) return metadata.label;
  const segments = path.split('/').filter(Boolean);
  return humanizeSegment(segments.at(-1) ?? 'Home');
}

function pageFileToRoute(pageFile: string): string | null {
  let relative = pageFile
    .replace(/^.*?\/src\/pages\//, '')
    .replace(/\.(astro|md|mdx)$/i, '');

  if (!relative || relative === 'index') return '/';
  if (relative === '404' || relative.split('/').some((segment) => segment.startsWith('_'))) {
    return null;
  }

  // Dynamic route files are expanded from their actual content catalogs in
  // the Website Graph page. Rendering a literal "[slug]" node would create a dead URL.
  if (relative.includes('[') || relative.includes(']')) return null;

  relative = relative.replace(/\/index$/, '');
  return normalizeSitePath(`/${relative}`);
}

const WORLD_PARENT_BY_HREF = new Map(
  siteWorld.nodes
    .filter((node) => node.parent)
    .map((node) => {
      const parent = siteWorld.nodes.find((candidate) => candidate.id === node.parent);
      return [normalizeSitePath(node.href), normalizeSitePath(parent?.href ?? '/')] as const;
    }),
);

function parentPath(path: string, knownPaths: Set<string>) {
  if (path === '/') return null;

  const worldParent = WORLD_PARENT_BY_HREF.get(normalizeSitePath(path));
  if (worldParent && knownPaths.has(worldParent)) return worldParent;

  const segments = path.split('/').filter(Boolean);
  if (segments.length <= 1) return '/';

  const candidate = normalizeSitePath(`/${segments.slice(0, -1).join('/')}`);
  return knownPaths.has(candidate) ? candidate : '/';
}

function routeDepth(path: string) {
  return path === '/' ? 0 : path.split('/').filter(Boolean).length;
}

function anchorForRoute(
  route: SiteMapRoute & { category: SiteMapCategory },
  routeIndex: number,
  categoryRoutes: readonly (SiteMapRoute & { category: SiteMapCategory })[],
) {
  const center = CATEGORY_CENTERS[route.category];
  if (route.href === '/') return center;

  const depth = routeDepth(route.href);
  const categoryIndex = categoryRoutes.findIndex((item) => item.href === route.href);
  const index = categoryIndex >= 0 ? categoryIndex : routeIndex;
  const count = Math.max(1, categoryRoutes.length);
  const angle = -Math.PI / 2 + (index * Math.PI * 2) / count;
  const baseRadius =
    route.category === 'profile'
      ? 0.12
      : route.category === 'projects'
        ? 0.145
        : route.category === 'spaces'
          ? 0.17
          : 0.18;
  const radius = depth > 1 ? baseRadius : baseRadius * 0.55;

  return {
    x: clamp(center.x + Math.cos(angle) * radius, 0.08, 0.92),
    y: clamp(center.y + Math.sin(angle) * radius, 0.09, 0.9),
  };
}

export function buildSiteMapGraph({
  pageFiles,
  dynamicRoutes = [],
  currentPath,
  resolveHref,
}: BuildSiteMapOptions): SiteMapGraph {
  const discoveredRoutes: SiteMapRoute[] = pageFiles
    .map(pageFileToRoute)
    .filter((path): path is string => Boolean(path))
    .map((href) => ({
      href,
      label: PAGE_METADATA[href]?.label ?? labelForPath(href),
      description: PAGE_METADATA[href]?.description,
      category: PAGE_METADATA[href]?.category ?? categoryForPath(href),
    }));

  const routes = Array.from(
    new Map(
      [...discoveredRoutes, ...dynamicRoutes].map((route) => {
        const href = normalizeSitePath(route.href);
        const category = route.category ?? categoryForPath(href);
        const metadata = PAGE_METADATA[href];
        return [
          href,
          {
            href,
            label: route.label || metadata?.label || labelForPath(href),
            description: route.description ?? metadata?.description,
            category,
          } satisfies SiteMapRoute & { category: SiteMapCategory },
        ];
      }),
    ).values(),
  ).sort((left, right) => {
    const depthDifference = routeDepth(left.href) - routeDepth(right.href);
    if (depthDifference !== 0) return depthDifference;
    return left.label.localeCompare(right.label);
  });

  const normalizedCurrentPath = normalizeSitePath(currentPath);
  const categoryRoutes = new Map<
    SiteMapCategory,
    (SiteMapRoute & { category: SiteMapCategory })[]
  >();

  for (const category of Object.keys(CATEGORY_CENTERS) as SiteMapCategory[]) {
    categoryRoutes.set(
      category,
      routes.filter((route) => route.category === category),
    );
  }

  const nodes: NetworkNode[] = routes.map((route, index) => {
    const depth = routeDepth(route.href);
    const isSection = ['/projects/', '/rooms/', '/halls/'].includes(route.href);
    const isCurrent = route.href === normalizedCurrentPath;
    const group = categoryRoutes.get(route.category) ?? [];

    return {
      id: route.href,
      label: route.label,
      description: route.description ?? route.href,
      href: resolveHref(route.href),
      accent: CATEGORY_ACCENTS[route.category],
      radius:
        route.href === '/'
          ? 44
          : isSection
            ? 34
            : depth > 1
              ? 22
              : 27,
      anchor: anchorForRoute(route, index, group),
      featured: route.href === '/',
      current: isCurrent,
    };
  });

  const knownPaths = new Set(routes.map((route) => route.href));
  const links: NetworkLink[] = routes
    .filter((route) => route.href !== '/')
    .map((route) => ({
      source: parentPath(route.href, knownPaths) ?? '/',
      target: route.href,
      kind: routeDepth(route.href) > 1 ? 'secondary' : 'primary',
      distance: routeDepth(route.href) > 1 ? 112 : 150,
      strength: routeDepth(route.href) > 1 ? 0.22 : 0.12,
    }));

  return { nodes, links };
}
