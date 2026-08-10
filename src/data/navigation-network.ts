import type {
  NetworkIcon,
  NetworkLink,
  NetworkNode,
} from '@/components/graphs/types';
import { withBase } from '@/lib/paths';

const icon = (...paths: string[]): NetworkIcon => ({ paths });

const icons = {
  about: icon('M20 21a8 8 0 0 0-16 0', 'M12 13a4 4 0 1 0 0-8 4 4 0 0 0 0 8'),
  resume: icon(
    'M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z',
    'M14 2v6h6',
    'M8 13h8',
    'M8 17h8',
  ),
  contact: icon('M4 5h16v14H4Z', 'm4 7 8 6 8-6'),
  projects: icon(
    'M4 7h16v12H4Z',
    'M9 7V4h6v3',
    'M4 12h16',
    'M10 12v2h4v-2',
  ),
  stats: icon('M4 20V11', 'M10 20V4', 'M16 20v-7', 'M22 20H2'),
  lab: icon('M9 3h6', 'M10 3v5l-5 9a2 2 0 0 0 1.8 3h10.4a2 2 0 0 0 1.8-3l-5-9V3', 'M8 14h8'),
};

/**
 * In radial layout mode, the outer-node array order is the clockwise order.
 * Starting at the top: About → Résumé → Projects → Lab → Contact → Stats.
 */
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
    id: 'resume',
    label: 'Résumé',
    description: 'Experience & skills',
    href: withBase('/resume/'),
    icon: icons.resume,
    accent: '#3b91d6',
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
    id: 'lab',
    label: 'Lab',
    description: 'Experiments & spaces',
    href: withBase('/lab/'),
    icon: icons.lab,
    accent: '#8274e8',
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
    id: 'stats',
    label: 'Stats',
    description: 'Activity & metrics',
    href: withBase('/stats/'),
    icon: icons.stats,
    accent: '#469b73',
    radius: 36,
  },
];

const primary = (target: string): NetworkLink => ({
  source: 'home',
  target,
  kind: 'primary',
  strength: 0.2,
});

// The hidden navigation page uses a clean hub-and-spoke graph. The reusable
// component still supports secondary links for graphs elsewhere on the site.
export const navigationNetworkLinks: NetworkLink[] = [
  primary('about'),
  primary('resume'),
  primary('projects'),
  primary('lab'),
  primary('contact'),
  primary('stats'),
];
