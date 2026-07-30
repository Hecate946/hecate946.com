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
  | 'pickleball'
  | 'museum';

export interface HouseWindowPaneAxis {
  /** Offset from the window glass rectangle's x or y coordinate. */
  offset: number;
  /** Exact pane width or height in native house-image pixels. */
  size: number;
}

export interface HouseWindowGeometry {
  /** Full glass area in the native 1800 × 1200 house coordinate system. */
  x: number;
  y: number;
  width: number;
  height: number;
  kind: HouseWindowKind;
  columns: number;
  rows: number;
  mullionX: number;
  mullionY: number;
  /** Exact pane measurements used to keep artwork behind the existing mullions. */
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

/**
 * These measurements are calibrated directly against public/scenes/house/shell.png.
 * Keeping the SVG in the PNG's native coordinate system prevents window drift at
 * every responsive size; the browser scales the house and overlays together.
 */
export const houseScene = {
  enabled: true,
  navigationEnabled: true,
  showHint: true,
  referenceWidth: 1800,
  referenceHeight: 1200,
  destinations: [
    {
      id: 'red-room-window',
      label: 'Red Room',
      roomLabel: 'The Red Room',
      description: 'An immersive fixed-viewpoint red tiled room.',
      href: '/rooms/red/',
      scene: 'collision',
      sceneViewBox: { width: 100, height: 140, fit: 'slice' },
      geometry: {
        x: 247,
        y: 402,
        width: 95,
        height: 169,
        kind: 'square',
        columns: 3,
        rows: 4,
        mullionX: 5,
        mullionY: 6,
        paneColumns: [
          { offset: 0, size: 29 },
          { offset: 34, size: 26 },
          { offset: 66, size: 29 },
        ],
        paneRows: [
          { offset: 0, size: 39 },
          { offset: 45, size: 37 },
          { offset: 87, size: 38 },
          { offset: 130, size: 39 },
        ],
      },
    },
    {
      id: 'green-room-window',
      label: 'Green Room',
      roomLabel: 'The Green Room',
      description: 'An immersive fixed-viewpoint green tiled room.',
      href: '/rooms/green/',
      scene: 'chess-rook',
      sceneViewBox: { width: 68, height: 124, fit: 'slice' },
      geometry: {
        x: 480,
        y: 402,
        width: 95,
        height: 169,
        kind: 'square',
        columns: 3,
        rows: 4,
        mullionX: 5,
        mullionY: 6,
        paneColumns: [
          { offset: 0, size: 29 },
          { offset: 34, size: 27 },
          { offset: 66, size: 29 },
        ],
        paneRows: [
          { offset: 0, size: 40 },
          { offset: 45, size: 37 },
          { offset: 87, size: 38 },
          { offset: 130, size: 39 },
        ],
      },
    },
    {
      id: 'orange-room-window',
      label: 'Orange Room',
      roomLabel: 'The Orange Room',
      description: 'An immersive fixed-viewpoint orange tiled room.',
      href: '/rooms/orange/',
      scene: 'clarinet',
      sceneViewBox: { width: 66, height: 124, fit: 'slice' },
      geometry: {
        x: 852,
        y: 401,
        width: 96,
        height: 171,
        kind: 'square',
        columns: 3,
        rows: 4,
        mullionX: 4,
        mullionY: 4,
        paneColumns: [
          { offset: 0, size: 30 },
          { offset: 34, size: 28 },
          { offset: 66, size: 30 },
        ],
        paneRows: [
          { offset: 0, size: 41 },
          { offset: 45, size: 39 },
          { offset: 87, size: 40 },
          { offset: 130, size: 41 },
        ],
      },
    },
    {
      id: 'blue-room-window',
      label: 'Blue Room',
      roomLabel: 'The Blue Room',
      description: 'An immersive fixed-viewpoint blue tiled room.',
      href: '/rooms/blue/',
      scene: 'pickleball',
      sceneViewBox: { width: 66, height: 124, fit: 'slice' },
      geometry: {
        x: 1225,
        y: 402,
        width: 95,
        height: 169,
        kind: 'square',
        columns: 3,
        rows: 4,
        mullionX: 5,
        mullionY: 6,
        paneColumns: [
          { offset: 0, size: 29 },
          { offset: 34, size: 27 },
          { offset: 66, size: 29 },
        ],
        paneRows: [
          { offset: 0, size: 40 },
          { offset: 45, size: 37 },
          { offset: 87, size: 38 },
          { offset: 130, size: 39 },
        ],
      },
    },
    {
      id: 'purple-room-window',
      label: 'Purple Room',
      roomLabel: 'The Purple Room',
      description: 'An immersive fixed-viewpoint purple tiled room.',
      href: '/rooms/purple/',
      scene: 'contact',
      sceneViewBox: { width: 100, height: 140, fit: 'slice' },
      geometry: {
        x: 1459,
        y: 402,
        width: 94,
        height: 169,
        kind: 'square',
        columns: 3,
        rows: 4,
        mullionX: 6,
        mullionY: 6,
        paneColumns: [
          { offset: 0, size: 28 },
          { offset: 34, size: 26 },
          { offset: 65, size: 29 },
        ],
        paneRows: [
          { offset: 0, size: 40 },
          { offset: 45, size: 37 },
          { offset: 87, size: 38 },
          { offset: 130, size: 39 },
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
        x: 247,
        y: 714,
        width: 328,
        height: 192,
        kind: 'square',
        columns: 8,
        rows: 4,
        mullionX: 5,
        mullionY: 5,
        paneColumns: [
          { offset: 0, size: 38 },
          { offset: 43, size: 37 },
          { offset: 84, size: 37 },
          { offset: 125, size: 37 },
          { offset: 166, size: 37 },
          { offset: 207, size: 37 },
          { offset: 248, size: 37 },
          { offset: 289, size: 39 },
        ],
        paneRows: [
          { offset: 0, size: 46 },
          { offset: 51, size: 43 },
          { offset: 99, size: 43 },
          { offset: 147, size: 45 },
        ],
      },
    },
    {
      id: 'museum-window',
      label: 'Museum',
      roomLabel: 'The Museum',
      description: 'An immersive museum hall on the ground floor.',
      href: '/halls/museum/',
      scene: 'museum',
      sceneViewBox: { width: 268, height: 162, fit: 'slice' },
      geometry: {
        x: 1225,
        y: 714,
        width: 328,
        height: 192,
        kind: 'square',
        columns: 8,
        rows: 4,
        mullionX: 5,
        mullionY: 5,
        paneColumns: [
          { offset: 0, size: 38 },
          { offset: 43, size: 37 },
          { offset: 84, size: 37 },
          { offset: 125, size: 37 },
          { offset: 166, size: 37 },
          { offset: 207, size: 37 },
          { offset: 248, size: 37 },
          { offset: 289, size: 39 },
        ],
        paneRows: [
          { offset: 0, size: 46 },
          { offset: 51, size: 43 },
          { offset: 99, size: 43 },
          { offset: 147, size: 45 },
        ],
      },
    },
  ],
} as const satisfies HouseSceneConfig;
