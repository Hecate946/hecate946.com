export type AboutTVLink = {
  href: string;
  label: string;
  external?: boolean;
};

export type AboutTVChannel = {
  id: 'about' | 'software' | 'music' | 'pickleball' | 'chess';
  label: string;
  title: string;
  subtitle?: string;
  paragraphs: string[];
  links?: AboutTVLink[];
  portrait?: {
    src: string;
    alt: string;
  };
};

export type AboutTVAssets = {
  portraitUrl: string;
  softwareResumeUrl: string;
  projectsUrl: string;
  musicResumeUrl: string;
  musicVideoUrl: string;
  pickleballArticleUrl: string;
  chessProfileUrl: string;
};

/**
 * Edit the About TV copy and links here. Animation and layout live in
 * separate files so content changes cannot disturb the TV/channel behavior.
 */
export const createAboutTVChannels = (
  assets: AboutTVAssets,
): AboutTVChannel[] => [
  {
    id: 'about',
    label: 'About',
    title: 'Cyrus Asasi',
    subtitle: 'clarinetist + software engineer',
    paragraphs: [
      "Hi, I'm Cyrus. I'm a software engineer and classical musician who enjoys mastering difficult skills. Whether it's reverse engineering complex systems, performing concertos, or building interactive web experiences, I'm happiest when I'm learning something challenging.",
      "Outside of work, you'll usually find me practicing the clarinet or piano, competing in pickleball tournaments, or playing chess.",
      "I recently completed dual bachelor's degrees in Computer Science and Music Performance at UCLA and am now pursuing a Master's in Music Performance while continuing to build software projects.",
    ],
    portrait: {
      src: assets.portraitUrl,
      alt: 'Portrait of Cyrus Asasi',
    },
  },
  {
    id: 'software',
    label: 'Software',
    title: 'Software',
    paragraphs: [
      "I love building software that's functional, efficient, and enjoyable to use.",
      'Professionally, much of my experience has been in reverse engineering, where I enjoy understanding complex systems and rebuilding them in cleaner, more useful ways. Outside of work, I build web applications, developer tools, and whatever projects solve problems I encounter.',
    ],
    links: [
      {
        href: assets.projectsUrl,
        label: 'View projects',
      },
      {
        href: assets.softwareResumeUrl,
        label: 'Software engineering resume',
        external: true,
      },
    ],
  },
  {
    id: 'music',
    label: 'Music',
    title: 'Music',
    paragraphs: [
      'Music has been a lifelong passion.',
      "I'm a clarinetist and pianist currently pursuing a Master's in Music Performance at UCLA. In 2026, I won UCLA's All-Stars Competition, giving me the opportunity to perform as a concerto soloist with the UCLA Philharmonia.",
      'Beyond performing, I love listening. I almost exclusively listen to classical music, with my current favorites being Brahms, Ravel, and Kapustin.',
    ],
    links: [
      {
        href: assets.musicVideoUrl,
        label: 'Watch the performance',
        external: true,
      },
      {
        href: assets.musicResumeUrl,
        label: 'Clarinet performance resume',
        external: true,
      },
    ],
  },
  {
    id: 'pickleball',
    label: 'Pickleball',
    title: 'Pickleball',
    paragraphs: [
      'I grew up playing tennis, but eventually found myself drawn to pickleball because of its strategic depth.',
      "I've competed for around four years at the 5.0 level and currently serve as captain of the UCLA Pickleball Team. One highlight was winning the California Collegiate Super Regional Championship, where our team took home the title and a $2,500 prize.",
    ],
    links: [
      {
        href: assets.pickleballArticleUrl,
        label: 'Tournament recap',
        external: true,
      },
    ],
  },
  {
    id: 'chess',
    label: 'Chess',
    title: 'Chess',
    paragraphs: [
      'Chess has been an obsession ever since middle school.',
      'After discovering Chess.com in seventh grade, I spent far too many hours studying openings, tactics, and endgames, eventually reaching a peak online rating of 2450.',
      'I still enjoy the game because it rewards the same type of analytical thinking and pattern recognition that drew me toward computer science.',
    ],
    links: [
      {
        href: assets.chessProfileUrl,
        label: 'View live Chess.com rating',
        external: true,
      },
    ],
  },
];
