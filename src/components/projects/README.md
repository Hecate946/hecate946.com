# Project showcase

The project system is intentionally data-driven:

- Edit project names, descriptions, dates, technologies, and case-study copy in `src/data/projects.ts`.
- The Projects page reads that data through `ProjectCard.astro`.
- `src/pages/projects/[slug].astro` automatically creates one page per project.
- `ProjectShowcase.astro` is the shared case-study layout.
- Project artwork lives in `public/images/projects/`; update each project's `image` field when adding final screenshots or renders.

To add a project, add one object to `projects` in `src/data/projects.ts` and expand the `Project['slug']` union. Its URL will be `/projects/<slug>/`.
