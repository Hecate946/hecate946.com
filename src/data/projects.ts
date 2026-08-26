export interface ProjectLink {
  label: string;
  href: string;
}

export interface Project {
  slug:
    | '3tap'
    | 'neutra'
    | 'sunset'
    | 'keycad'
    | 'portfolio'
    | 'sketyl'
    | 'webserver';
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
}

export const projects = [
  {
    slug: 'neutra',
    title: 'Neutra',
    tagline:
      'Moderation, analytics, and music tools for large online communities.',
    description:
      'A large Discord platform combining moderation, activity tracking, server analytics, logging, utilities, and music playback across hundreds of commands.',
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
    tagline: 'A modular computer-vision-to-CAD prototype for turning image contours into parametric geometry.',
    description:
      'A modular prototype that extracts a foreground contour from an image, converts it to normalized geometry, and generates a deliberately non-lock-compatible OpenSCAD demonstration model with a Three.js preview.',
    period: '2022–2023; 2026',
    category: 'Computer vision and CAD',
    imageAlt:
      'Impressionist painting of a seated child in a coral-red smock, used as the KeyCAD project image.',
    technologies: [
      'Next.js',
      'TypeScript',
      'FastAPI',
      'OpenCV',
      'OpenSCAD',
      'Three.js',
    ],
    links: [
      {
        label: 'View source',
        href: 'https://github.com/Hecate946/keycad',
      },
    ],
  },
  {
    slug: 'portfolio',
    title: 'Hecate946.com',
    tagline:
      'A hand-built portfolio where every page is part of one interactive room.',
    description:
      'A statically generated Astro and Svelte portfolio built as one continuous room, combining custom CSS environments with a Three.js/WebGL hallway, persistent audio and theme state, and responsive page-specific interfaces.',
    period: '2026–Present',
    category: 'Interactive web experience',
    imageAlt:
      'Portrait of a woman dressed in black beneath a broad black hat, set against an olive-green background, used as the Hecate946.com project image.',
    technologies: [
      'Astro',
      'Svelte',
      'TypeScript',
      'Three.js',
      'WebGL',
      'CSS',
    ],
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
  {
    slug: '3tap',
    title: '3tap',
    tagline:
      'A fast, private three-state habit tracker with no account required.',
    description:
      'A minimal three-state habit grid with anonymous boards, quick thoughts, recovery tools, archiving, and cross-device synchronization.',
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
    slug: 'sketyl',
    title: 'Sketyl',
    tagline:
      'A Spotify analytics site for exploring listening history and music data.',
    description:
      'An asynchronous Spotify statistics site with OAuth, top and recent listening views, liked music, profiles, genres, decades, and other personal listening breakdowns.',
    period: '2022',
    category: 'Music analytics application',
    imageAlt: 'The Sketyl Spotify analytics interface.',
    technologies: ['Python', 'Quart', 'PostgreSQL', 'Spotify API', 'Jinja'],
    links: [
      {
        label: 'View source',
        href: 'https://github.com/Hecate946/Sketyl',
      },
    ],
  },
  {
    slug: 'webserver',
    title: 'C Web Server',
    tagline:
      'A small synchronous HTTP server in C with static-file routing and in-memory caching.',
    description:
      'A from-scratch C web server that accepts socket connections, handles simple GET requests, serves static and binary files with MIME-aware HTTP responses, and caches recently requested content in memory.',
    period: '2023',
    category: 'Systems and networking',
    imageAlt: 'Source code from the C web server project.',
    technologies: ['C', 'POSIX sockets', 'HTTP', 'HTML/CSS'],
    links: [
      {
        label: 'View source',
        href: 'https://github.com/Hecate946/webserver',
      },
    ],
  },
] as const satisfies readonly Project[];

export const indexProjects = projects.map((project) => {
  return {
    title: project.title,
    primaryHref: `/projects/${project.slug}/`,
    description: project.tagline,
  };
}) satisfies readonly ProjectIndexEntry[];
