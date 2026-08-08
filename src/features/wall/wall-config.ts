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

/**
 * Five evenly-spaced destinations form one seamless lap. Using a loop width
 * equal to five frame spacings keeps the gap across the wrap identical to all
 * of the interior gaps. 3840 is also evenly divisible by the 96px brick repeat
 * and 120px floor repeat, so decorative textures cannot jump at the loop seam.
 */
export const WALL_LOOP_WIDTH = 3_840;
export const WALL_START_X = 500;

const FRAME_WIDTH = 340;
const FRAME_HEIGHT = 420;
const FRAME_SPACING = 768;
const FRAME_START_X = 500;

const frameX = (index: number) => FRAME_START_X + FRAME_SPACING * index;

/**
 * Left-to-right wall order and artwork are configured here. Painting assets
 * live in /public/paintings so artwork can be swapped without touching the
 * frame renderer.
 */
export const wallDestinations: readonly WallDestination[] = [
  {
    id: 'about',
    label: 'About',
    href: '/about/',
    x: frameX(0),
    width: FRAME_WIDTH,
    height: FRAME_HEIGHT,
    painting: {
      src: '/paintings/the-stare.webp',
      name: 'The Stare',
    },
  },
  {
    id: 'resume',
    label: 'Resume',
    href: '/resume/',
    x: frameX(1),
    width: FRAME_WIDTH,
    height: FRAME_HEIGHT,
    painting: {
      src: '/paintings/ransom.webp',
      name: 'Ransom',
    },
  },
  {
    id: 'projects',
    label: 'Projects',
    href: '/projects/',
    x: frameX(2),
    width: FRAME_WIDTH,
    height: FRAME_HEIGHT,
    painting: {
      src: '/paintings/pastry-chef.webp',
      name: 'Pastry Chef',
    },
  },
  {
    id: 'contact',
    label: 'Contact',
    href: '/contact/',
    x: frameX(3),
    width: FRAME_WIDTH,
    height: FRAME_HEIGHT,
    painting: {
      src: '/paintings/rothko.webp',
      name: 'Rothko',
    },
  },
  {
    id: 'stats',
    label: 'Stats',
    href: '/stats/',
    x: frameX(4),
    width: FRAME_WIDTH,
    height: FRAME_HEIGHT,
    painting: {
      src: '/paintings/madame-le-peletier.webp',
      name: 'Madame Le Peletier',
    },
  },
] as const;
