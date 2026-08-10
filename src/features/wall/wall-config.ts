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
 * Center-to-center frame spacing. Keeping the gap equal to one full-size frame
 * makes the gallery a little denser without feeling crowded. With five
 * destinations this also produces a 3360px lap, exactly divisible by both
 * the 96px brick repeat and 120px floor repeat.
 */
const FRAME_SPACING = 672;

/**
 * Left-to-right wall order and artwork. The loop width is derived from this
 * array, so adding/removing a destination automatically resizes one complete
 * wall lap while preserving perfectly even spacing across the wrap.
 */
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
    id: 'resume',
    label: 'Resume',
    href: '/resume/',
    painting: {
      src: '/paintings/ransom.webp',
      name: 'Ransom',
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
    id: 'stats',
    label: 'Stats',
    href: '/stats/',
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
