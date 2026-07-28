export type HouseWindowKind = 'square' | 'round' | 'halfdome';

export interface HouseWindowGeometry {
  x: number;
  y: number;
  width: number;
  height: number;
  kind: HouseWindowKind;
}

export interface HouseDestination {
  id: string;
  label: string;
  roomLabel: string;
  description: string;
  href: string;
  geometry: HouseWindowGeometry;
}

export interface HouseSceneConfig {
  enabled: boolean;
  navigationEnabled: boolean;
  showHint: boolean;
  referenceWidth: number;
  referenceHeight: number;
  destinations: readonly HouseDestination[];
}

/**
 * Complete control panel for the homepage house.
 *
 * Set `enabled` to false to remove the entire feature from the homepage.
 * Window destinations and geometry live here so the SVG components stay
 * presentation-only and can be redesigned without touching page code.
 */
export const houseScene = {
  // Change this one flag to hide or restore the house everywhere it is mounted.
  enabled: false,
  navigationEnabled: true,
  showHint: true,
  referenceWidth: 1672,
  referenceHeight: 941,
  destinations: [
    {
      id: 'portfolio-window',
      label: 'Hecate946.com',
      roomLabel: 'The Portfolio Room',
      description: 'How this interactive portfolio was designed and built.',
      href: '/projects/portfolio/',
      geometry: {
        x: 278,
        y: 282,
        width: 81,
        height: 140,
        kind: 'square',
      },
    },
    {
      id: 'about-window',
      label: 'About',
      roomLabel: 'The Sitting Room',
      description: 'Software, music, pickleball, chess, and the person connecting them.',
      href: '/about/',
      geometry: {
        x: 491,
        y: 282,
        width: 77,
        height: 140,
        kind: 'square',
      },
    },
    {
      id: 'resume-window',
      label: 'Resume',
      roomLabel: 'The Study',
      description: 'Education, experience, technical skills, performances, and awards.',
      href: '/resume/',
      geometry: {
        x: 783,
        y: 282,
        width: 77,
        height: 140,
        kind: 'square',
      },
    },
    {
      id: 'projects-window',
      label: 'Projects',
      roomLabel: 'The Workshop',
      description: 'Software projects, experiments, and interactive systems.',
      href: '/projects/',
      geometry: {
        x: 1079,
        y: 282,
        width: 77,
        height: 140,
        kind: 'square',
      },
    },
    {
      id: 'contact-window',
      label: 'Contact',
      roomLabel: 'The Correspondence Room',
      description: 'Get in touch about software, music, or collaboration.',
      href: '/contact/',
      geometry: {
        x: 1292,
        y: 282,
        width: 77,
        height: 140,
        kind: 'square',
      },
    },
  ],
} as const satisfies HouseSceneConfig;
