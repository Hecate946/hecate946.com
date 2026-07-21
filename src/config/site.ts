export const siteConfig = {
  name: 'Cyrus Asasi',
  shortName: 'Cyrus',
  title: 'Cyrus Asasi — Music, Software, Strategy, and Motion',
  description:
    'The personal portfolio of Cyrus Asasi: computer science, clarinet, piano, chess, and pickleball.',
  email: 'replace-me@example.com',
  locale: 'en-US',
  social: {
    github: 'https://github.com/replace-me',
    linkedin: 'https://www.linkedin.com/in/replace-me',
    youtube: 'https://www.youtube.com/@replace-me',
  },
} as const;

export const navigation = [
  { label: 'Home', href: '/' },
  { label: 'Code', href: '/code/' },
  { label: 'Clarinet', href: '/clarinet/' },
  { label: 'Piano', href: '/piano/' },
  { label: 'Chess', href: '/chess/' },
  { label: 'Pickleball', href: '/pickleball/' },
  { label: 'Lab', href: '/lab/' },
  { label: 'Stats', href: '/stats/' },
  { label: 'About', href: '/about/' },
] as const;

export const interests = [
  {
    id: 'code',
    title: 'Computer Science',
    eyebrow: 'Systems & experiments',
    description:
      'Software projects, technical writing, and interactive prototypes.',
    href: '/code/',
    symbol: '</>',
  },
  {
    id: 'clarinet',
    title: 'Clarinet',
    eyebrow: 'Air & resonance',
    description: 'Performances, repertoire, recordings, and musical research.',
    href: '/clarinet/',
    symbol: '♩',
  },
  {
    id: 'piano',
    title: 'Piano',
    eyebrow: 'Harmony & collaboration',
    description:
      'Chamber music, sight-reading, collaborative work, and recordings.',
    href: '/piano/',
    symbol: '⌨',
  },
  {
    id: 'chess',
    title: 'Chess',
    eyebrow: 'Decisions & lookahead',
    description:
      'Games, positions, puzzles, and analysis of thought processes.',
    href: '/chess/',
    symbol: '♞',
  },
  {
    id: 'pickleball',
    title: 'Pickleball',
    eyebrow: 'Movement & reaction',
    description:
      'Strategy, training notes, match data, and motion experiments.',
    href: '/pickleball/',
    symbol: '◉',
  },
] as const;

export type InterestId = (typeof interests)[number]['id'];
