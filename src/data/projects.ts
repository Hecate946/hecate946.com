export interface ProjectLink {
  label: string;
  href: string;
}

export interface Project {
  slug: 'neutra' | 'sunset' | 'keycad' | 'portfolio';
  title: string;
  tagline: string;
  description: string;
  period: string;
  category: string;
  imageAlt: string;
  technologies: readonly string[];
  links?: readonly ProjectLink[];
}

export interface ProjectIndexEntry {
  id: string;
  title: string;
  tagline: string;
  period: string;
  category: string;
  technologies: readonly string[];
  primaryHref: string;
  links: readonly ProjectLink[];
}

export interface MiscProject {
  title: string;
  note: string;
  href: string;
}

export const projects = [
  {
    slug: 'neutra',
    title: 'Neutra',
    tagline:
      'Moderation, analytics, and music tools for large online communities.',
    description:
      'A 320-command community platform that combined configurable moderation, server analytics, security insights, and music playback in one system.',
    period: '2019–2021',
    category: 'Community platform',
    imageAlt:
      'Pastel pencil artwork showing a Discord logo, line graph, bar chart, and pie chart for Neutra.',
    technologies: ['Python', 'PostgreSQL', 'FFmpeg', 'Git'],
  },
  {
    slug: 'sunset',
    title: 'Sunset',
    tagline:
      'Automated UCLA Recreation reservations at the exact release window.',
    description:
      'A multi-user scheduling system that reverse engineered authenticated UCLA Recreation workflows and reliably booked tennis and pickleball courts when inventory opened.',
    period: '2025–Present',
    category: 'Automation system',
    imageAlt:
      'Pastel pencil artwork showing reverse-engineered code, a reservation countdown, and a pickleball court at sunset.',
    technologies: ['Python', 'Playwright', 'HTTP', 'systemd', 'Vultr'],
  },
  {
    slug: 'keycad',
    title: 'KeyCAD',
    tagline: 'An image-to-CAD pipeline for parameterized key models.',
    description:
      'A computer-vision and CAD experiment that translated measurements from photographs into dimensionally accurate, 3D-printable key geometry.',
    period: '2022–2023',
    category: 'Computer vision and CAD',
    imageAlt:
      'Impressionist painting of a seated child in a coral-red smock, used as the KeyCAD project image.',
    technologies: ['Python', 'OpenCV', 'OpenSCAD', 'Git'],
  },
  {
    slug: 'portfolio',
    title: 'Hecate946.com',
    tagline: 'An interactive portfolio built as a small, seasonal world.',
    description:
      'A statically generated Astro site with selectively hydrated Svelte components, typed content, interactive room scenes, and careful custom-domain deployment.',
    period: '2026–Present',
    category: 'Interactive web experience',
    imageAlt:
      'Portrait of a woman dressed in black beneath a broad black hat, set against an olive-green background, used as the Hecate946.com project image.',
    technologies: ['Astro', 'Svelte', 'TypeScript', 'CSS'],
    links: [
      {
        label: 'View source',
        href: 'https://github.com/Hecate946/hecate946.com',
      },
    ],
  },
] as const satisfies readonly Project[];

export const indexProjects = [
  {
    id: '3tap',
    title: '3tap',
    tagline:
      'A deliberately minimal three-state habit tracker with instant local interaction and reliable cross-device sync.',
    period: '2026–Present',
    category: 'Flagship product',
    technologies: ['SvelteKit', 'TypeScript', 'Supabase', 'Cloudflare'],
    primaryHref: 'https://3tap.cc',
    links: [
      { label: 'Live site', href: 'https://3tap.cc' },
      { label: 'Source', href: 'https://github.com/Hecate946/3tap' },
    ],
  },
  {
    id: projects[2].slug,
    title: projects[2].title,
    tagline: projects[2].tagline,
    period: projects[2].period,
    category: projects[2].category,
    technologies: projects[2].technologies,
    primaryHref: '/projects/keycad/',
    links: [
      { label: 'Case study', href: '/projects/keycad/' },
      { label: 'Source', href: 'https://github.com/Hecate946/keycad' },
    ],
  },
  {
    id: projects[1].slug,
    title: projects[1].title,
    tagline: projects[1].tagline,
    period: projects[1].period,
    category: projects[1].category,
    technologies: projects[1].technologies,
    primaryHref: '/projects/sunset/',
    links: [{ label: 'Case study', href: '/projects/sunset/' }],
  },
  {
    id: projects[0].slug,
    title: projects[0].title,
    tagline: projects[0].tagline,
    period: projects[0].period,
    category: projects[0].category,
    technologies: projects[0].technologies,
    primaryHref: '/projects/neutra/',
    links: [
      { label: 'Case study', href: '/projects/neutra/' },
      { label: 'Source', href: 'https://github.com/Hecate946/Neutra' },
    ],
  },
  {
    id: projects[3].slug,
    title: projects[3].title,
    tagline: projects[3].tagline,
    period: projects[3].period,
    category: projects[3].category,
    technologies: projects[3].technologies,
    primaryHref: '/projects/portfolio/',
    links: [
      { label: 'Case study', href: '/projects/portfolio/' },
      { label: 'Source', href: 'https://github.com/Hecate946/hecate946.com' },
    ],
  },
] as const satisfies readonly ProjectIndexEntry[];

export const miscProjects = [
  {
    title: 'Muses',
    note: 'Music discovery platform',
    href: 'https://github.com/Hecate946/Muses',
  },
  {
    title: 'GitHub archive',
    note: 'Older builds and experiments',
    href: 'https://github.com/Hecate946?tab=repositories',
  },
] as const satisfies readonly MiscProject[];
