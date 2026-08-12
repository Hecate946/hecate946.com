import type { WallDestination } from './wall-config';

const FRAME_WIDTH = 340;
const FRAME_HEIGHT = 420;
const FRAME_SPACING = 600;

const resumeDefinitions = [
  {
    id: 'software-resume',
    label: 'Software Engineering',
    href: '/resumes/cyrus-asasi-software-engineering-resume.pdf',
    painting: {
      src: '/images/resume/cyrus-asasi-software-engineering-resume.webp',
      name: 'Software engineering resume preview',
      width: 1454,
      height: 2048,
      objectPosition: '50% 50%',
      objectFit: 'contain',
    },
  },
  {
    id: 'clarinet-resume',
    label: 'Clarinet Performance',
    href: '/resumes/cyrus-asasi-clarinet-performance-resume.pdf',
    painting: {
      src: '/images/resume/cyrus-asasi-clarinet-performance-resume.webp',
      name: 'Clarinet performance resume preview',
      width: 1338,
      height: 1885,
      objectPosition: '50% 50%',
      objectFit: 'contain',
    },
  },
] as const;

export const RESUME_LOOP_WIDTH = FRAME_SPACING * resumeDefinitions.length;
export const RESUME_START_X = FRAME_SPACING / 2;

export const resumeDestinations: readonly WallDestination[] = resumeDefinitions.map(
  (resume, index) => ({
    ...resume,
    x: RESUME_START_X + FRAME_SPACING * index,
    width: FRAME_WIDTH,
    height: FRAME_HEIGHT,
  }),
);
