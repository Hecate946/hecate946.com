export interface ProjectLink {
  label: string;
  href: string;
}

export interface Project {
  slug: '3tap' | 'neutra' | 'sunset' | 'keycad' | 'portfolio';
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
  title: string;
  primaryHref: string;
  description: string;
  stack: readonly string[];
  sourceHref?: string;
}

export const projects = [
  {
    slug: '3tap',
    title: '3tap',
    tagline:
      'A fast, private three-state habit tracker with no account required.',
    description:
      'A minimal habit tracker built around instant three-state input, anonymous boards, device recovery, and reliable cross-device synchronization.',
    period: '2026–Present',
    category: 'Habit tracking application',
    imageAlt: 'The minimal three-state habit grid used by 3tap.',
    technologies: ['SvelteKit', 'TypeScript', 'Supabase', 'Cloudflare Workers'],
    links: [
      {
        label: 'Visit 3tap',
        href: 'https://3tap.cc',
      },
      {
        label: 'View source',
        href: 'https://github.com/Hecate946/3tap',
      },
    ],
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
    links: [
      {
        label: 'View source',
        href: 'https://github.com/Hecate946/keycad',
      },
    ],
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
    links: [
      {
        label: 'View source',
        href: 'https://github.com/Hecate946/Neutra',
      },
    ],
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
        label: 'Visit site',
        href: 'https://hecate946.com',
      },
      {
        label: 'View source',
        href: 'https://github.com/Hecate946/hecate946.com',
      },
    ],
  },
] as const satisfies readonly Project[];

export const indexProjects = projects.map((project) => {
  const projectRecord: Project = project;

  return {
    title: project.title,
    primaryHref: `/projects/${project.slug}/`,
    description: project.tagline,
    stack: project.technologies,
    sourceHref: projectRecord.links?.find((link) => /source/i.test(link.label))
      ?.href,
  };
}) satisfies readonly ProjectIndexEntry[];
