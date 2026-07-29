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
  | 'concert-hall'
  | 'pickleball';

export interface HouseWindowPaneAxis {
  /** Offset from the window glass rectangle's x or y coordinate. */
  offset: number;
  /** Exact pane width or height in house-image pixels. */
  size: number;
}

export interface HouseWindowGeometry {
  /** Full artwork-mapping area in the current 1800 × 1200 house coordinate system. */
  x: number;
  y: number;
  width: number;
  height: number;
  kind: HouseWindowKind;
  columns: number;
  rows: number;
  mullionX: number;
  mullionY: number;
  /** Exact visible pane measurements measured from the Blender render. */
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

const upperOuterColumns = [
  { offset: 0, size: 30 },
  { offset: 35, size: 27 },
  { offset: 66, size: 30 },
] as const;

const upperInnerColumns = [
  { offset: 0, size: 29 },
  { offset: 34, size: 27 },
  { offset: 66, size: 29 },
] as const;

const upperRows = [
  { offset: 0, size: 41 },
  { offset: 45, size: 38 },
  { offset: 88, size: 38 },
  { offset: 130, size: 41 },
] as const;

const centerColumns = [
  { offset: 0, size: 30 },
  { offset: 35, size: 26 },
  { offset: 66, size: 30 },
] as const;

const centerRows = [
  { offset: 0, size: 40 },
  { offset: 45, size: 37 },
  { offset: 87, size: 38 },
  { offset: 130, size: 40 },
] as const;

const lowerLeftColumns = [
  { offset: 0, size: 39 },
  { offset: 43, size: 37 },
  { offset: 84, size: 37 },
  { offset: 125, size: 37 },
  { offset: 166, size: 37 },
  { offset: 207, size: 37 },
  { offset: 248, size: 37 },
  { offset: 289, size: 39 },
] as const;

const lowerRows = [
  { offset: 0, size: 46 },
  { offset: 50, size: 44 },
  { offset: 98, size: 44 },
  { offset: 146, size: 46 },
] as const;

export const houseScene = {
  enabled: true,
  navigationEnabled: true,
  showHint: true,
  referenceWidth: 1800,
  referenceHeight: 1200,
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
        x: 246,
        y: 401,
        width: 96,
        height: 171,
        kind: 'square',
        columns: 3,
        rows: 4,
        mullionX: 4,
        mullionY: 4,
        paneColumns: upperOuterColumns,
        paneRows: upperRows,
      },
    },
    {
      id: 'chess-window',
      label: 'Chess',
      roomLabel: 'The Checkerboard Room',
      description: 'An immersive three-dimensional checkerboard room.',
      href: '/rooms/checkerboard/',
      scene: 'chess-rook',
      sceneViewBox: { width: 68, height: 124, fit: 'meet' },
      geometry: {
        x: 480,
        y: 401,
        width: 95,
        height: 171,
        kind: 'square',
        columns: 3,
        rows: 4,
        mullionX: 4,
        mullionY: 4,
        paneColumns: upperInnerColumns,
        paneRows: upperRows,
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
        x: 852,
        y: 402,
        width: 96,
        height: 170,
        kind: 'square',
        columns: 3,
        rows: 4,
        mullionX: 4,
        mullionY: 4,
        paneColumns: centerColumns,
        paneRows: centerRows,
      },
    },
    {
      id: 'pickleball-window',
      label: 'Pickleball',
      roomLabel: 'The Pickleball Court',
      description: 'A purple pickleball-court scene.',
      href: '/pickleball/',
      scene: 'pickleball',
      sceneViewBox: { width: 66, height: 124, fit: 'slice' },
      geometry: {
        x: 1225,
        y: 401,
        width: 95,
        height: 171,
        kind: 'square',
        columns: 3,
        rows: 4,
        mullionX: 4,
        mullionY: 4,
        paneColumns: upperInnerColumns,
        paneRows: upperRows,
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
        x: 1458,
        y: 401,
        width: 96,
        height: 171,
        kind: 'square',
        columns: 3,
        rows: 4,
        mullionX: 4,
        mullionY: 4,
        paneColumns: upperOuterColumns,
        paneRows: upperRows,
      },
    },
    {
      id: 'concert-window',
      label: 'Concert hall',
      roomLabel: 'The Concert Hall',
      description: 'A nine-foot concert grand framed by red velvet curtains.',
      href: '/concert-hall/',
      scene: 'concert-hall',
      sceneViewBox: { width: 268, height: 162, fit: 'slice' },
      geometry: {
        x: 247,
        y: 714,
        width: 328,
        height: 192,
        kind: 'square',
        columns: 8,
        rows: 4,
        mullionX: 4,
        mullionY: 4,
        paneColumns: lowerLeftColumns,
        paneRows: lowerRows,
      },
    },
  ],
} as const satisfies HouseSceneConfig;
