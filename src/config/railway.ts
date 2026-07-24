export interface RailwayStop {
  id: string;
  label: string;
  shortLabel: string;
  href: string;
}

export interface RailwayConfig {
  lineName: string;
  serviceLabel: string;
  navigationEnabled: boolean;
  autoPlay: boolean;
  durationSeconds: number;
  stops: readonly RailwayStop[];
}

/**
 * The railway is intentionally configured outside the visual component.
 * Set navigationEnabled to true when the train cars should become links.
 */
export const railwayConfig = {
  lineName: 'Line 946',
  serviceLabel: 'Steam service',
  navigationEnabled: false,
  autoPlay: true,
  durationSeconds: 17,
  stops: [
    {
      id: 'home',
      label: 'Home',
      shortLabel: 'HOME',
      href: '/',
    },
    {
      id: 'about',
      label: 'About',
      shortLabel: 'ABOUT',
      href: '/about/',
    },
    {
      id: 'resume',
      label: 'Resume',
      shortLabel: 'RESUME',
      href: '/resume/',
    },
    {
      id: 'work',
      label: 'Work',
      shortLabel: 'WORK',
      href: '/work/',
    },
    {
      id: 'contact',
      label: 'Contact',
      shortLabel: 'CONTACT',
      href: '/contact/',
    },
    {
      id: 'stats',
      label: 'Stats',
      shortLabel: 'STATS',
      href: '/stats/',
    },
  ],
} as const satisfies RailwayConfig;
