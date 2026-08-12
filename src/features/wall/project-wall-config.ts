import type { WallDestination } from './wall-config';

const FRAME_WIDTH = 340;
const FRAME_HEIGHT = 420;
const FRAME_SPACING = 600;

const projectDefinitions = [
  {
    id: 'neutra',
    label: 'Neutra',
    href: '/projects/neutra/',
    painting: {
      src: '/images/project-gallery/neutra-480.webp',
      name: 'Project painting',
      width: 480,
      height: 582,
      objectPosition: '50% 50%',
      sources: [
        { src: '/images/project-gallery/neutra-480.webp', width: 480 },
        { src: '/images/project-gallery/neutra.webp', width: 627 },
      ],
    },
  },
  {
    id: 'sunset',
    label: 'Sunset',
    href: '/projects/sunset/',
    painting: {
      src: '/images/project-gallery/sunset-480.webp',
      name: 'Project painting',
      width: 480,
      height: 589,
      objectPosition: '50% 50%',
      sources: [
        { src: '/images/project-gallery/sunset-480.webp', width: 480 },
        { src: '/images/project-gallery/sunset-720.webp', width: 720 },
      ],
    },
  },
  {
    id: 'keycad',
    label: 'KeyCAD',
    href: '/projects/keycad/',
    painting: {
      src: '/images/project-gallery/keycad.webp',
      name: 'Shuttlecock painting',
      width: 534,
      height: 640,
      objectPosition: '56% 43%',
      sources: [
        { src: '/images/project-gallery/keycad-480.webp', width: 480 },
        { src: '/images/project-gallery/keycad.webp', width: 534 },
      ],
    },
  },
  {
    id: 'portfolio',
    label: 'Hecate946.com',
    href: '/projects/portfolio/',
    painting: {
      src: '/images/project-gallery/portfolio.webp',
      name: 'Madonna variant',
      width: 589,
      height: 800,
      objectPosition: '50% 36%',
      sources: [
        { src: '/images/project-gallery/portfolio-480.webp', width: 480 },
        { src: '/images/project-gallery/portfolio.webp', width: 589 },
      ],
    },
  },
] as const;

export const PROJECT_LOOP_WIDTH = FRAME_SPACING * projectDefinitions.length;
export const PROJECT_START_X = FRAME_SPACING / 2;

export const projectDestinations: readonly WallDestination[] = projectDefinitions.map(
  (project, index) => ({
    ...project,
    x: PROJECT_START_X + FRAME_SPACING * index,
    width: FRAME_WIDTH,
    height: FRAME_HEIGHT,
  }),
);
