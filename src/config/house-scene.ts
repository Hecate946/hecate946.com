export type HouseWindowKind = 'square' | 'round' | 'halfdome';

export type HouseWindowSceneId =
  | 'portfolio'
  | 'about'
  | 'resume'
  | 'projects'
  | 'contact'
  | 'collision'
  | 'chess-rook'
  | 'concert-hall'
  | 'pickleball';

export interface HouseWindowGeometry {
  /** Glass area only, in the frozen house's 1672 × 941 coordinate system. */
  x: number;
  y: number;
  width: number;
  height: number;
  kind: HouseWindowKind;
  columns: number;
  rows: number;
  mullionX: number;
  mullionY: number;
}

export interface HouseWindowSceneViewBox {
  width: number;
  height: number;
  fit?: 'meet' | 'slice';
}

export interface HouseDestination {
  id: string;
  label: string;
  roomLabel: string;
  description: string;
  href: string;
  scene: HouseWindowSceneId;
  geometry: HouseWindowGeometry;
  sceneViewBox?: HouseWindowSceneViewBox;
}

export interface HouseSceneConfig {
  enabled: boolean;
  navigationEnabled: boolean;
  showHint: boolean;
  referenceWidth: number;
  referenceHeight: number;
  destinations: readonly HouseDestination[];
}

export const houseScene = {
  enabled: false,
  navigationEnabled: true,
  showHint: true,
  referenceWidth: 1672,
  referenceHeight: 941,
  destinations: [
    {
      id: 'collision-window',
      label: 'Collision detection',
      roomLabel: 'The Collision Lab',
      description: 'A live collision-detection playground.',
      href: '/collision-detection/',
      scene: 'collision',
      geometry: {
        x: 306,
        y: 315,
        width: 73,
        height: 131,
        kind: 'square',
        columns: 3,
        rows: 4,
        mullionX: 3,
        mullionY: 3,
      },
    },
    {
      id: 'chess-window',
      label: 'Chess',
      roomLabel: 'The Chess Room',
      description: 'A full-screen chess board centered on a black rook.',
      href: '/chess-board/',
      scene: 'chess-rook',
      sceneViewBox: {
        width: 1600,
        height: 900,
        fit: 'slice',
      },
      geometry: {
        x: 514,
        y: 315,
        width: 73,
        height: 131,
        kind: 'square',
        columns: 3,
        rows: 4,
        mullionX: 3,
        mullionY: 3,
      },
    },
    {
      id: 'resume-window',
      label: 'Resume',
      roomLabel: 'The Study',
      description: 'Education, experience, technical skills, performances, and awards.',
      href: '/resume/',
      scene: 'resume',
      geometry: {
        x: 797,
        y: 315,
        width: 73,
        height: 131,
        kind: 'square',
        columns: 3,
        rows: 4,
        mullionX: 3,
        mullionY: 3,
      },
    },
    {
      id: 'projects-window',
      label: 'Projects',
      roomLabel: 'The Workshop',
      description: 'Software projects, experiments, and interactive systems.',
      href: '/projects/',
      scene: 'projects',
      geometry: {
        x: 1084,
        y: 315,
        width: 71,
        height: 131,
        kind: 'square',
        columns: 3,
        rows: 4,
        mullionX: 3,
        mullionY: 3,
      },
    },
    {
      id: 'contact-window',
      label: 'Contact',
      roomLabel: 'The Correspondence Room',
      description: 'Get in touch about software, music, or collaboration.',
      href: '/contact/',
      scene: 'contact',
      geometry: {
        x: 1290,
        y: 315,
        width: 73,
        height: 131,
        kind: 'square',
        columns: 3,
        rows: 4,
        mullionX: 3,
        mullionY: 3,
      },
    },
    {
      id: 'concert-window',
      label: 'Concert hall',
      roomLabel: 'The Concert Hall',
      description: 'A nine-foot concert grand framed by red velvet curtains.',
      href: '/concert-hall/',
      scene: 'concert-hall',
      sceneViewBox: {
        width: 279,
        height: 172,
        fit: 'meet',
      },
      geometry: {
        x: 302,
        y: 581,
        width: 279,
        height: 172,
        kind: 'square',
        columns: 7,
        rows: 5,
        mullionX: 4,
        mullionY: 4,
      },
    },
    {
      id: 'pickleball-window',
      label: 'Picklabell',
      roomLabel: 'The Picklabell Court',
      description: 'A top-down pickleball court scene.',
      href: '/picklabell/',
      scene: 'pickleball',
      sceneViewBox: {
        width: 279,
        height: 172,
        fit: 'meet',
      },
      geometry: {
        x: 1090,
        y: 581,
        width: 279,
        height: 172,
        kind: 'square',
        columns: 7,
        rows: 5,
        mullionX: 4,
        mullionY: 4,
      },
    },
  ],
} as const satisfies HouseSceneConfig;
