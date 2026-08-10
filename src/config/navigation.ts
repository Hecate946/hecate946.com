export interface HeaderNavItem {
  label: string;
  href: string;
  /** Additional routes that should mark this item as current. */
  match?: readonly string[];
}

/** Primary navigation order. */
export const headerNavigation = [
  { label: 'About', href: '/about/' },
  {
    label: 'Projects',
    href: '/projects/',
    match: ['/code/', '/clarinet/', '/piano/'],
  },
  { label: 'Contact', href: '/contact/' },
  { label: 'Lab', href: '/lab/' },
] as const satisfies readonly HeaderNavItem[];
