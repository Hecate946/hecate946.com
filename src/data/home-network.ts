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
  interests: icon(
    'M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.6l-1-1a5.5 5.5 0 0 0-7.8 7.8l1 1L12 21l7.8-7.6 1-1a5.5 5.5 0 0 0 0-7.8Z',
  ),
  stats: icon('M4 20V11', 'M10 20V4', 'M16 20v-7', 'M22 20H2'),
};

/**
 * In radial layout mode, the outer-node array order is the clockwise order.
 * Starting at the top: About → Résumé → Contact → Interests → Stats.
 */
export const homeNetworkNodes: NetworkNode[] = [
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
    id: 'contact',
    label: 'Contact',
    description: 'Let’s connect',
    href: 'mailto:cyrusasasi@gmail.com',
    icon: icons.contact,
    accent: '#d66b8b',
    radius: 36,
  },
  {
    id: 'interests',
    label: 'Interests',
    description: 'Beyond the work',
    href: withBase('/interests/'),
    icon: icons.interests,
    accent: '#c88d31',
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

// The homepage is intentionally a clean hub-and-spoke graph. The reusable
// component still supports secondary links for graphs elsewhere on the site.
export const homeNetworkLinks: NetworkLink[] = [
  primary('about'),
  primary('resume'),
  primary('contact'),
  primary('interests'),
  primary('stats'),
];
