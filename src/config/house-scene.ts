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
  referenceWidth: 1400,
  referenceHeight: 820,
  destinations: [
    {
      id: 'portfolio-oculus',
      label: 'Hecate946.com',
      roomLabel: 'The Oculus',
      description: 'How this interactive portfolio was designed and built.',
      href: '/projects/portfolio/',
      geometry: {
        x: 249,
        y: 185,
        width: 104,
        height: 104,
        kind: 'round',
      },
    },
    {
      id: 'about-room',
      label: 'About',
      roomLabel: 'The Sitting Room',
      description: 'Software, music, pickleball, chess, and the person connecting them.',
      href: '/about/',
      geometry: {
        x: 595,
        y: 345,
        width: 128,
        height: 128,
        kind: 'square',
      },
    },
    {
      id: 'resume-room',
      label: 'Resume',
      roomLabel: 'The Study',
      description: 'Education, experience, technical skills, performances, and awards.',
      href: '/resume/',
      geometry: {
        x: 798,
        y: 345,
        width: 128,
        height: 128,
        kind: 'square',
      },
    },
    {
      id: 'projects-room',
      label: 'Projects',
      roomLabel: 'The Workshop',
      description: 'Software projects, experiments, and interactive systems.',
      href: '/projects/',
      geometry: {
        x: 1001,
        y: 345,
        width: 128,
        height: 128,
        kind: 'square',
      },
    },
    {
      id: 'contact-room',
      label: 'Contact',
      roomLabel: 'The Great Room',
      description: 'Get in touch about software, music, or collaboration.',
      href: '/contact/',
      geometry: {
        x: 528,
        y: 510,
        width: 654,
        height: 186,
        kind: 'halfdome',
      },
    },
  ],
} as const satisfies HouseSceneConfig;
