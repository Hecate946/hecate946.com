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

/** Destinations exposed through the command palette beyond the header tabs. */
export const navigation = [
  { label: 'Home', href: '/' },
  { label: 'About', href: '/about/' },
  { label: 'Projects', href: '/projects/' },
  { label: 'Contact', href: '/contact/' },
  { label: 'Lab', href: '/lab/' },
  { label: 'Graph', href: '/graph/' },
] as const;
