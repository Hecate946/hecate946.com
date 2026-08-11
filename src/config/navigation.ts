export interface HeaderNavItem {
  label: string;
  href: string;
}

/** Primary navigation order. */
export const headerNavigation = [
  { label: 'About', href: '/about/' },
  { label: 'Projects', href: '/projects/' },
  { label: 'Resumes', href: '/resumes/' },
  { label: 'Contact', href: '/contact/' },
] as const satisfies readonly HeaderNavItem[];
