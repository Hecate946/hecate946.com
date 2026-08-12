export interface WallPaintingSource {
  src: string;
  width: number;
}

export interface WallPainting {
  src: string;
  name: string;
  width: number;
  height: number;
  objectPosition?: string;
  sources?: readonly WallPaintingSource[];
}

export interface WallDestination {
  id: string;
  label: string;
  href: string;
  x: number;
  width: number;
  height: number;
  painting: WallPainting;
}

type WallDestinationDefinition = Omit<WallDestination, 'x' | 'width' | 'height'>;

const FRAME_WIDTH = 340;
const FRAME_HEIGHT = 420;

/**
 * Four evenly spaced destinations. A 600px interval keeps the gallery compact
 * while making the 2400px loop divide cleanly into the 96px brick repeat.
 * The 3D floor uses absolute world coordinates and no longer has a CSS repeat
 * seam that the gallery loop needs to accommodate.
 */
const FRAME_SPACING = 600;

/** Primary site order: About → Projects → Resume → Contact. */
const destinationDefinitions = [
  {
    id: 'about',
    label: 'About',
    href: '/about/',
    painting: {
      src: '/paintings/the-stare.webp',
      name: 'The Stare',
      width: 886,
      height: 1080,
      sources: [
        { src: '/paintings/the-stare-480.webp', width: 480 },
        { src: '/paintings/the-stare.webp', width: 886 },
      ],
    },
  },
  {
    id: 'projects',
    label: 'Projects',
    href: '/projects/',
    painting: {
      src: '/paintings/pastry-chef.webp',
      name: 'Pastry Chef',
      width: 540,
      height: 600,
      sources: [
        { src: '/paintings/pastry-chef-480.webp', width: 480 },
        { src: '/paintings/pastry-chef.webp', width: 540 },
      ],
    },
  },
  {
    id: 'resume',
    label: 'Resume',
    href: '/resumes/',
    painting: {
      src: '/paintings/stats-portrait.webp',
      name: 'Seated Portrait',
      width: 960,
      height: 1203,
      sources: [
        { src: '/paintings/stats-portrait-480.webp', width: 480 },
        { src: '/paintings/stats-portrait-720.webp', width: 720 },
        { src: '/paintings/stats-portrait.webp', width: 960 },
      ],
    },
  },
  {
    id: 'contact',
    label: 'Contact',
    href: '/contact/',
    painting: {
      src: '/paintings/madame-le-peletier.webp',
      name: 'Madame Le Peletier',
      width: 564,
      height: 694,
      sources: [
        { src: '/paintings/madame-le-peletier-480.webp', width: 480 },
        { src: '/paintings/madame-le-peletier.webp', width: 564 },
      ],
    },
  },
] satisfies readonly WallDestinationDefinition[];

/** One lap is exactly one spacing slot per destination. */
export const WALL_LOOP_WIDTH = FRAME_SPACING * destinationDefinitions.length;

/** Put the first painting in the exact middle of the first spacing slot. */
export const WALL_START_X = FRAME_SPACING / 2;

export const wallDestinations: readonly WallDestination[] = destinationDefinitions.map(
  (destination, index) => ({
    ...destination,
    x: WALL_START_X + FRAME_SPACING * index,
    width: FRAME_WIDTH,
    height: FRAME_HEIGHT,
  }),
);
