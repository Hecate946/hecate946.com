export type HouseWindowKind = 'square' | 'round' | 'halfdome';

export type HouseWindowSceneId =
  | 'portfolio'
  | 'about'
  | 'resume'
  | 'projects'
  | 'contact'
  | 'collision'
  | 'chess-rook'
  | 'clarinet'
  | 'ballroom'
  | 'pickleball';

export interface HouseWindowPaneAxis {
  /** Offset from the window glass rectangle's x or y coordinate. */
  offset: number;
  /** Exact pane width or height in house-image pixels. */
  size: number;
}

export interface HouseWindowGeometry {
  /** Full glass area in the current 1536 × 1024 house coordinate system. */
  x: number;
  y: number;
  width: number;
  height: number;
  kind: HouseWindowKind;
  columns: number;
  rows: number;
  mullionX: number;
  mullionY: number;
  /** Optional exact pane measurements for pixel-accurate clipping. */
  paneColumns?: readonly HouseWindowPaneAxis[];
  paneRows?: readonly HouseWindowPaneAxis[];
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
  referenceWidth: 1536,
  referenceHeight: 1024,
  destinations: [
    {
      id: 'collision-window',
      label: 'Collision detection',
      roomLabel: 'The Collision Lab',
      description: 'A live collision-detection playground.',
      href: '/collision-detection/',
      scene: 'collision',
      sceneViewBox: { width: 100, height: 140, fit: 'slice' },
      geometry: {
        x: 272,
        y: 361,
        width: 67,
        height: 124,
        kind: 'square',
        columns: 3,
        rows: 4,
        mullionX: 2,
        mullionY: 2,
        paneColumns: [
          { offset: 0, size: 21 },
          { offset: 23, size: 20 },
          { offset: 45, size: 22 },
        ],
        paneRows: [
          { offset: 0, size: 26 },
          { offset: 29, size: 30 },
          { offset: 61, size: 30 },
          { offset: 93, size: 31 },
        ],
      },
    },
    {
      id: 'chess-window',
      label: 'Chess',
      roomLabel: 'The Chess Room',
      description: 'A full-screen chess board centered on a black rook.',
      href: '/chess-board/',
      scene: 'chess-rook',
      sceneViewBox: { width: 68, height: 124, fit: 'meet' },
      geometry: {
        x: 474,
        y: 361,
        width: 68,
        height: 124,
        kind: 'square',
        columns: 3,
        rows: 4,
        mullionX: 2,
        mullionY: 2,
        paneColumns: [
          { offset: 0, size: 23 },
          { offset: 25, size: 20 },
          { offset: 47, size: 21 },
        ],
        paneRows: [
          { offset: 0, size: 27 },
          { offset: 29, size: 30 },
          { offset: 61, size: 30 },
          { offset: 93, size: 31 },
        ],
      },
    },
    {
      id: 'clarinet-window',
      label: 'Resume',
      roomLabel: 'The Clarinet Room',
      description: 'A detailed clarinet display previewing the resume page.',
      href: '/resume/',
      scene: 'clarinet',
      sceneViewBox: { width: 66, height: 124, fit: 'slice' },
      geometry: {
        x: 759,
        y: 361,
        width: 66,
        height: 124,
        kind: 'square',
        columns: 3,
        rows: 4,
        mullionX: 2,
        mullionY: 2,
        paneColumns: [
          { offset: 0, size: 19 },
          { offset: 21, size: 22 },
          { offset: 45, size: 21 },
        ],
        paneRows: [
          { offset: 0, size: 27 },
          { offset: 29, size: 31 },
          { offset: 62, size: 30 },
          { offset: 94, size: 30 },
        ],
      },
    },
    {
      id: 'pickleball-window',
      label: 'Pickleball',
      roomLabel: 'The Pickleball Court',
      description: 'A top-down pickleball court scene.',
      href: '/pickleball/',
      scene: 'pickleball',
      sceneViewBox: { width: 66, height: 124, fit: 'slice' },
      geometry: {
        x: 1041,
        y: 361,
        width: 66,
        height: 124,
        kind: 'square',
        columns: 3,
        rows: 4,
        mullionX: 2,
        mullionY: 2,
        paneColumns: [
          { offset: 0, size: 20 },
          { offset: 22, size: 21 },
          { offset: 45, size: 21 },
        ],
        paneRows: [
          { offset: 0, size: 26 },
          { offset: 29, size: 30 },
          { offset: 61, size: 30 },
          { offset: 93, size: 31 },
        ],
      },
    },
    {
      id: 'contact-window',
      label: 'Contact',
      roomLabel: 'The Correspondence Room',
      description: 'Get in touch about software, music, or collaboration.',
      href: '/contact/',
      scene: 'contact',
      sceneViewBox: { width: 100, height: 140, fit: 'slice' },
      geometry: {
        x: 1245,
        y: 361,
        width: 65,
        height: 124,
        kind: 'square',
        columns: 3,
        rows: 4,
        mullionX: 2,
        mullionY: 2,
        paneColumns: [
          { offset: 0, size: 20 },
          { offset: 21, size: 23 },
          { offset: 46, size: 19 },
        ],
        paneRows: [
          { offset: 0, size: 26 },
          { offset: 29, size: 30 },
          { offset: 61, size: 30 },
          { offset: 93, size: 31 },
        ],
      },
    },
    {
      id: 'ballroom-window',
      label: 'Ballroom',
      roomLabel: 'The Ballroom',
      description: 'A neoclassical ballroom rendered as an immersive panoramic hall.',
      href: '/halls/ballroom/',
      scene: 'ballroom',
      sceneViewBox: { width: 268, height: 162, fit: 'slice' },
      geometry: {
        x: 268,
        y: 619,
        width: 268,
        height: 162,
        kind: 'square',
        columns: 7,
        rows: 5,
        mullionX: 2,
        mullionY: 2,
        paneColumns: [
          { offset: 0, size: 35 },
          { offset: 37, size: 38 },
          { offset: 77, size: 34 },
          { offset: 113, size: 39 },
          { offset: 155, size: 36 },
          { offset: 193, size: 37 },
          { offset: 232, size: 36 },
        ],
        paneRows: [
          { offset: 0, size: 30 },
          { offset: 32, size: 30 },
          { offset: 65, size: 29 },
          { offset: 96, size: 31 },
          { offset: 129, size: 33 },
        ],
      },
    },
  ],
} as const satisfies HouseSceneConfig;
