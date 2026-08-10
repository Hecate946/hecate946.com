export interface WallPainting {
  src: string;
  name: string;
  objectPosition?: string;
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
 * while making the 2400px loop divide cleanly into both the 96px brick repeat
 * and the 120px floor repeat, so a full revolution remains seamless.
 */
const FRAME_SPACING = 600;

/** Primary site order: About → Projects → Contact → Lab. */
const destinationDefinitions = [
  {
    id: 'about',
    label: 'About',
    href: '/about/',
    painting: {
      src: '/paintings/the-stare.webp',
      name: 'The Stare',
    },
  },
  {
    id: 'projects',
    label: 'Projects',
    href: '/projects/',
    painting: {
      src: '/paintings/pastry-chef.webp',
      name: 'Pastry Chef',
    },
  },
  {
    id: 'contact',
    label: 'Contact',
    href: '/contact/',
    painting: {
      src: '/paintings/rothko.webp',
      name: 'Rothko',
    },
  },
  {
    id: 'lab',
    label: 'Lab',
    href: '/lab/',
    painting: {
      src: '/paintings/madame-le-peletier.webp',
      name: 'Madame Le Peletier',
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
