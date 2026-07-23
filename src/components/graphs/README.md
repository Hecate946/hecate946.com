# Reusable force network

`ForceNetwork.svelte` renders a custom SVG network powered by `d3-force`. The component owns physics, dragging, rendering, focus states, click-versus-drag detection, responsiveness, and reduced-motion handling; a page only supplies nodes and links.

## Basic use

```astro
---
import ForceNetwork from '@/components/graphs/ForceNetwork.svelte';
import type { NetworkNode, NetworkLink } from '@/components/graphs/types';

const nodes: NetworkNode[] = [
  {
    id: 'center',
    label: 'Center',
    href: '/',
    featured: true,
    anchor: { x: 0.5, y: 0.5 },
  },
  {
    id: 'project-a',
    label: 'Project A',
    href: '/projects/a/',
    anchor: { x: 0.25, y: 0.3 },
  },
];

const links: NetworkLink[] = [
  { source: 'center', target: 'project-a', kind: 'primary' },
];
---

<ForceNetwork
  client:visible
  {nodes}
  {links}
  centerNodeId="center"
  idPrefix="projects-network"
  height="34rem"
/>
```

## Node options

- `anchor` is a normalized resting position from `0` to `1`.
- `imageSrc` renders a clipped circular image.
- `icon.paths` renders SVG path strings using a 24 × 24 viewBox.
- `accent` accepts any CSS color, including CSS variables.
- `featured` increases the default node size.
- `href` makes the node a normal accessible link.

## Link options

- `kind: 'primary'` produces a stronger edge.
- `kind: 'secondary'` produces a quieter edge.
- `distance` and `strength` override the force defaults.
- `curve` bends an SVG edge by the given number of graph units.

## Rendering behavior

D3 mutates simulation objects in place. The component converts those mutable links into a fresh `renderedLinks` array on every tick. This keeps the SVG edge geometry synchronized with the node layer during dragging and settling.

## Multiple graphs on one page

Give each instance a unique `idPrefix` so its SVG clip paths remain isolated.

## Radial layouts

Set `settings.layout` to `radial` to place every non-center node on a true regular polygon. The order of those nodes in the `nodes` array becomes their clockwise order.

```astro
<ForceNetwork
  nodes={nodes}
  links={links}
  centerNodeId="center"
  settings={{
    layout: 'radial',
    radialRadius: 0.325,
    radialStartAngle: -Math.PI / 2,
    entranceRadius: 0,
  }}
/>
```

`radialRadius` is measured against the shorter canvas dimension, so the polygon remains geometrically regular on wide and tall canvases.
