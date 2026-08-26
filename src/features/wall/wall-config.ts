export interface WallPaintingSource {
  src: string;
  width: number;
}

export interface WallPainting {
  src: string;
  width: number;
  height: number;
  sources: readonly WallPaintingSource[];
}

export interface WallDestination {
  id: string;
  label: string;
  href: string;
  x: number;
  painting: WallPainting;
}

type WallDestinationDefinition = Omit<WallDestination, 'x'>;

/**
 * Four evenly spaced destinations. A 600px interval keeps the gallery compact
 * while making the 2400px loop divide cleanly into the 96px brick repeat.
 * The floor uses absolute world coordinates and no longer has a CSS repeat
 * seam that the gallery loop needs to accommodate.
 */
const FRAME_SPACING = 600;

/** Primary site order: About -> Projects -> Resume -> Contact. */
const destinationDefinitions = [
  {
    id: 'about',
    label: 'About',
    href: '/about/',
    painting: {
      src: '/paintings/the-stare.webp',
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
    label: 'Resumes',
    href: '/resumes/',
    painting: {
      src: '/paintings/resume-portrait-480.webp',
      width: 480,
      height: 602,
      sources: [
        { src: '/paintings/resume-portrait-480.webp', width: 480 },
        { src: '/paintings/resume-portrait-720.webp', width: 720 },
      ],
    },
  },
  {
    id: 'contact',
    label: 'Contact',
    href: '/contact/',
    painting: {
      src: '/paintings/madame-le-peletier.webp',
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

/**
 * One lap of the hallway gallery, in world units, and therefore the spacing
 * between consecutive paintings once it is divided by the destination count.
 *
 * It lives here, next to the destinations it spaces, because both the Svelte
 * shell (which places the anchors and wraps the camera) and the WebGL gallery
 * (which wraps each frame's corridor position) must agree on it exactly. Two
 * copies of the number silently desynchronised the anchor order from the
 * geometry the moment either was tuned.
 *
 * 11,520 divides cleanly by the 120px brick module and the 240px checker, so
 * a lap still lands on the corridor's native texture phase.
 */
export const HALLWAY_LOOP_DEPTH = 11_520;

/** The door room starts on the backdrop's native brick/checker phase. */
export const WALL_START_X = 0;

export const wallDestinations: readonly WallDestination[] =
  destinationDefinitions.map((destination, index) => ({
    ...destination,
    x: WALL_START_X + FRAME_SPACING * index,
  }));
