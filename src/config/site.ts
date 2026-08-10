export const siteConfig = {
  name: 'Cyrus Asasi',
  shortName: 'Cyrus',
  title: 'Cyrus Asasi — Software Engineer & Classical Musician',
  description:
    'Personal portfolio of Cyrus Asasi, a software engineer and classical musician, featuring projects, performances, experiments, and contact information.',
  email: 'cyrusasasi@gmail.com',
  locale: 'en-US',
  social: {
    github: 'https://github.com/Hecate946/',
    linkedin: 'https://www.linkedin.com/in/cyrus-asasi/',
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
