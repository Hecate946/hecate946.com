export interface HeaderNavItem {
  label: string;
  href: string;
  /** Additional routes that should mark this item as current. */
  match?: readonly string[];
}

/**
 * Add, remove, or reorder navigation tabs here.
 * The header automatically redistributes the available tab space.
 */
export const headerNavigation = [
  { label: 'About', href: '/about/' },
  { label: 'Resume', href: '/resume/' },
  {
    label: 'Work',
    href: '/work/',
    match: ['/code/', '/clarinet/', '/piano/', '/lab/', '/projects/'],
  },
  { label: 'Stats', href: '/stats/' },
] as const satisfies readonly HeaderNavItem[];
