import type {
  NetworkIcon,
  NetworkLink,
  NetworkNode,
} from '@/components/graphs/types';
import { withBase } from '@/lib/paths';

const icon = (...paths: string[]): NetworkIcon => ({ paths });


/** Shared observatory palette: Home keeps the current site accent. */
export const navigationRainbowAccents: Readonly<Record<string, string>> = {
  about: '#d75a5a',
  projects: '#d9863f',
  contact: '#c4a12e',
  lab: '#4f9864',
  graph: '#4c7fbd',
  stats: '#8266c2',
};

export function navigationRainbowAccent(id: string, fallback?: string) {
  return id === 'home'
    ? fallback ?? 'var(--accent, #8b7cff)'
    : navigationRainbowAccents[id] ?? fallback ?? 'var(--accent, #8b7cff)';
}

const icons = {
  about: icon('M20 21a8 8 0 0 0-16 0', 'M12 13a4 4 0 1 0 0-8 4 4 0 0 0 0 8'),
  contact: icon('M4 5h16v14H4Z', 'm4 7 8 6 8-6'),
  projects: icon(
    'M4 7h16v12H4Z',
    'M9 7V4h6v3',
    'M4 12h16',
    'M10 12v2h4v-2',
  ),
  lab: icon('M9 3h6', 'M10 3v5l-5 9a2 2 0 0 0 1.8 3h10.4a2 2 0 0 0 1.8-3l-5-9V3', 'M8 14h8'),
  graph: icon('M6 7.5 12 4l6 3.5', 'M6 7.5v8L12 20l6-4.5v-8', 'M6 15.5 12 12l6 3.5', 'M12 4v8'),
  stats: icon('M5 19V11', 'M10 19V6', 'M15 19v-5', 'M20 19V9'),
};

/** In radial layout mode, outer nodes run clockwise around Home. */
export const navigationNetworkNodes: NetworkNode[] = [
  {
    id: 'home',
    label: 'Home',
    description: 'Cyrus Asasi',
    href: withBase('/'),
    imageSrc: withBase('/images/cat.jpeg'),
    accent: 'var(--accent, #8274e8)',
    radius: 62,
    featured: true,
  },
  {
    id: 'about',
    label: 'About',
    description: 'Background & story',
    href: withBase('/about/'),
    icon: icons.about,
    accent: '#8b7be0',
    radius: 36,
  },
  {
    id: 'projects',
    label: 'Projects',
    description: 'Projects & practice',
    href: withBase('/projects/'),
    icon: icons.projects,
    accent: '#c88d31',
    radius: 36,
  },
  {
    id: 'contact',
    label: 'Contact',
    description: 'Let\'s connect',
    href: withBase('/contact/'),
    icon: icons.contact,
    accent: '#d66b8b',
    radius: 36,
  },
  {
    id: 'lab',
    label: 'Lab',
    description: 'Experiments & spaces',
    href: withBase('/lab/'),
    icon: icons.lab,
    accent: '#8274e8',
    radius: 36,
  },
  {
    id: 'graph',
    label: 'Graph',
    description: 'Website graph',
    href: withBase('/graph/'),
    icon: icons.graph,
    accent: '#5c9ca8',
    radius: 36,
  },
  {
    id: 'stats',
    label: 'Stats',
    description: 'Website observed',
    href: withBase('/stats/'),
    icon: icons.stats,
    accent: '#9b7f68',
    radius: 36,
  },
];

const primary = (target: string): NetworkLink => ({
  source: 'home',
  target,
  kind: 'primary',
  strength: 0.2,
});

export const navigationNetworkLinks: NetworkLink[] = [
  primary('about'),
  primary('projects'),
  primary('contact'),
  primary('lab'),
  primary('graph'),
  primary('stats'),
];
