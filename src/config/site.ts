export const siteConfig = {
  name: 'Cyrus Asasi',
  shortName: 'Cyrus',
  title: 'Cyrus Asasi — Software Engineer & Classical Musician',
  description:
    'Personal portfolio of Cyrus Asasi, a software engineer and classical musician, featuring projects, performances, live site statistics, and contact information.',
  email: 'cyrusasasi@gmail.com',
  locale: 'en-US',
  social: {
    github: 'https://github.com/Hecate946/',
    linkedin: 'https://www.linkedin.com/in/cyrus-asasi/',
  },
  ui: {
    // Toggle the vertical “elevator” page-change animation for the top nav.
    // Set this to true whenever you want those transitions back on.
    enableElevatorTabAnimations: false,

    // Keep the About-page magnifier implementation available without loading
    // its Three.js/Rapier feature chunk until this is explicitly enabled.
    enableMagnifyingGlass: false,
  },
} as const;
