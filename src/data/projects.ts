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
  role: string;
  status: string;
  image: string;
  imageAlt: string;
  technologies: readonly string[];
  highlights: readonly string[];
  challenge: string;
  approach: string;
  result: string;
  links?: readonly ProjectLink[];
}

/**
 * The Projects index and every /projects/[slug] case study are generated from this
 * one file. Add a project here once and it appears everywhere automatically.
 */
export const projects = [
  {
    slug: 'neutra',
    title: 'Neutra',
    tagline: 'Moderation, analytics, and music tools for large online communities.',
    description:
      'A 320-command community platform that combined configurable moderation, server analytics, security insights, and music playback in one system.',
    period: '2019–2021',
    category: 'Community platform',
    role: 'Creator and engineer',
    status: 'Complete',
    image: '/images/projects/neutra.webp',
    imageAlt:
      'Pastel pencil artwork showing a Discord logo, line graph, bar chart, and pie chart for Neutra.',
    technologies: ['Python', 'PostgreSQL', 'FFmpeg', 'Git'],
    highlights: [
      'Built a 320-command moderation and analytics platform.',
      'Designed the PostgreSQL schema and the workflows behind message, user, and security insights.',
      'Added music playback with custom FFmpeg effects and documented the complete command set.',
    ],
    challenge:
      'Large communities needed moderation, analytics, and entertainment tools that could work together without forcing administrators to manage a collection of disconnected bots.',
    approach:
      'I designed Neutra as one extensible platform, with a shared data model and command system that let moderation rules, analytics, security features, and media tools build on the same foundation.',
    result:
      'Neutra grew into a 320-command platform used by 500,000 people and became my first experience operating software at meaningful scale.',
  },
  {
    slug: 'sunset',
    title: 'Sunset',
    tagline: 'Automated UCLA Recreation reservations at the exact release window.',
    description:
      'A multi-user scheduling system that reverse engineered authenticated UCLA Recreation workflows and reliably booked tennis and pickleball courts when inventory opened.',
    period: '2025–Present',
    category: 'Automation system',
    role: 'Creator and engineer',
    status: 'Active',
    image: '/images/projects/sunset.webp',
    imageAlt:
      'Pastel pencil artwork showing reverse-engineered code, a reservation countdown, and a pickleball court at sunset.',
    technologies: ['Python', 'Playwright', 'HTTP', 'systemd', 'Vultr'],
    highlights: [
      'Reverse engineered authenticated availability and reservation workflows.',
      'Built a multi-user scheduler with persistent sessions and sub-second retries.',
      'Added keep-alive monitoring, structured logs, and automatic process recovery.',
    ],
    challenge:
      'Popular campus courts were released on a strict 72-hour schedule and disappeared almost immediately, making the manual reservation process frustrating and unreliable.',
    approach:
      'I mapped the authenticated booking flow, then built a persistent scheduler that could maintain sessions, watch release times, retry quickly, and recover automatically when a process or browser failed.',
    result:
      'Sunset turned a timing-sensitive manual workflow into a dependable service that could coordinate reservations for multiple users.',
  },
  {
    slug: 'keycad',
    title: 'KeyCAD',
    tagline: 'An image-to-CAD pipeline for parameterized key models.',
    description:
      'A computer-vision and CAD experiment that translated measurements from photographs into dimensionally accurate, 3D-printable key geometry.',
    period: '2022–2023',
    category: 'Computer vision and CAD',
    role: 'Creator and engineer',
    status: 'Complete',
    image: '/images/projects/keycad.webp',
    imageAlt:
      'Pastel pencil artwork showing a horizontal brass key with CAD measurements, model data, and a bitting profile.',
    technologies: ['Python', 'OpenCV', 'OpenSCAD', 'Git'],
    highlights: [
      'Created 19 parameterized key-blank models from manufacturer specifications.',
      'Built an OpenCV pipeline that measured positions and depths from photographs.',
      'Generated dimensionally accurate STL geometry from the corresponding parameterized model.',
    ],
    challenge:
      'Turning a flat photograph into useful physical geometry required a consistent way to correct scale, locate measurement points, and map those measurements onto a precise 3D model.',
    approach:
      'I separated the system into two parts: a library of parameterized OpenSCAD blanks and a Python/OpenCV measurement pipeline that selected and modified the matching model.',
    result:
      'The finished pipeline connected image analysis and procedural CAD into a repeatable end-to-end workflow across 19 key profiles.',
  },
  {
    slug: 'portfolio',
    title: 'Hecate946.com',
    tagline: 'An interactive portfolio built as a small, seasonal world.',
    description:
      'A statically generated Astro site with selectively hydrated Svelte components, typed content, interactive Canvas scenes, and careful custom-domain deployment.',
    period: '2026–Present',
    category: 'Interactive web experience',
    role: 'Designer and engineer',
    status: 'Active',
    image: '/images/projects/portfolio.webp',
    imageAlt:
      'Pastel pencil artwork showing the Hecate946.com seasonal interface across spring, summer, autumn, and winter.',
    technologies: ['Astro', 'Svelte', 'TypeScript', 'Canvas', 'CSS'],
    highlights: [
      'Built a statically generated Astro site with selectively hydrated Svelte components.',
      'Created interactive seasonal Canvas animations, a command palette, and typed content systems.',
      'Implemented responsive layouts, reduced-motion support, path-safe deployment, and GitHub Actions publishing.',
    ],
    challenge:
      'The site needed to feel personal and animated without becoming slow, inaccessible, or difficult to maintain as new visual systems and pages were added.',
    approach:
      'I kept the document structure static wherever possible, isolated interactive behavior into focused Svelte islands, and organized visual systems into reusable components and configuration files.',
    result:
      'The portfolio now acts as both a professional showcase and an ongoing playground for animation, interface design, and modular front-end architecture.',
    links: [
      { label: 'Visit live site', href: '/' },
      { label: 'View source', href: 'https://github.com/Hecate946/hecate946.com' },
    ],
  },
] as const satisfies readonly Project[];

export type ProjectSlug = (typeof projects)[number]['slug'];

export function getProjectBySlug(slug: string) {
  return projects.find((project) => project.slug === slug);
}
