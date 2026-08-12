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
      src: '/images/resume/cyrus-asasi-software-engineering-resume-480.webp',
      name: 'Software engineering resume preview',
      width: 480,
      height: 676,
      objectPosition: '50% 50%',
      objectFit: 'contain',
      sources: [
        { src: '/images/resume/cyrus-asasi-software-engineering-resume-480.webp', width: 480 },
        { src: '/images/resume/cyrus-asasi-software-engineering-resume-720.webp', width: 720 },
      ],
    },
  },
  {
    id: 'clarinet-resume',
    label: 'Clarinet Performance',
    href: '/resumes/cyrus-asasi-clarinet-performance-resume.pdf',
    painting: {
      src: '/images/resume/cyrus-asasi-clarinet-performance-resume-480.webp',
      name: 'Clarinet performance resume preview',
      width: 480,
      height: 676,
      objectPosition: '50% 50%',
      objectFit: 'contain',
      sources: [
        { src: '/images/resume/cyrus-asasi-clarinet-performance-resume-480.webp', width: 480 },
        { src: '/images/resume/cyrus-asasi-clarinet-performance-resume-720.webp', width: 720 },
      ],
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
