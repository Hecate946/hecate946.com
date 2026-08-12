export type AboutPaperVisual = {
  src: string;
  alt: string;
  caption?: string;
};

export type AboutPaperPage = {
  id: 'about' | 'software' | 'music' | 'elsewhere';
  eyebrow: string;
  title: string;
  subtitle?: string;
  paragraphs: string[];
  visual?: AboutPaperVisual;
};

export type AboutPaperAssets = {
  portraitUrl: string;
};

/**
 * Primary About-page copy lives here.
 * Edit this file to change the paper stack's text.
 */
export const createAboutPaperPages = (assets: AboutPaperAssets): AboutPaperPage[] => [
  {
    id: 'about',
    eyebrow: 'ABOUT',
    title: 'Cyrus Asasi',
    subtitle: 'clarinetist + software engineer',
    paragraphs: [
      "I spend most of my time between code and music. I studied computer science and clarinet performance at UCLA, and I'm back there now for a master's in clarinet.",
      'I like patient work: learning a difficult piece, figuring out a strange system, or refining a visual detail until it finally feels right.',
    ],
    visual: {
      src: assets.portraitUrl,
      alt: 'Portrait of Cyrus Asasi',
      caption: 'Los Angeles, California',
    },
  },
  {
    id: 'software',
    eyebrow: 'SOFTWARE',
    title: 'I like figuring things out',
    paragraphs: [
      "A lot of my software work starts with curiosity. I'll notice something awkward, pull it apart to see how it works, and then try to rebuild it in a cleaner or more useful way.",
      'I especially like web projects that feel tactile or precise—interfaces with strong visual language, a little restraint, and some unusual interaction hiding underneath.',
    ],
  },
  {
    id: 'music',
    eyebrow: 'MUSIC',
    title: 'Music has always anchored me',
    paragraphs: [
      "Clarinet has been the constant for most of my life. In 2026 I got to solo with the UCLA Philharmonia after winning the All-Stars Competition, which was a really meaningful moment for me.",
      'I also spend a lot of time at the piano because I love chamber music and collaboration. Brahms, Ravel, and Kapustin are almost always somewhere in the background.',
    ],
  },
  {
    id: 'elsewhere',
    eyebrow: 'ELSEWHERE',
    title: 'A few other things',
    paragraphs: [
      "Outside of all that, I'm competitive in pickleball and still think about chess more often than I probably should.",
      'Both of them scratch the same itch for me: pattern recognition, pressure, timing, and the feeling that there is always another layer to understand.',
    ],
  },
];
