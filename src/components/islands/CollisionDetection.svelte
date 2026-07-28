<script lang="ts">
  import {
    forceCollide,
    forceManyBody,
    forceSimulation,
    forceX,
    forceY,
    type Simulation,
    type SimulationNodeDatum,
  } from 'd3-force';
  import { onMount } from 'svelte';

  type CollisionNode = SimulationNodeDatum & {
    r: number;
    group: number;
    color: string;
  };

  type SeasonPalette = {
    id: string;
    label: string;
    descriptor: string;
    surface: string;
    line: string;
    accent: string;
    colors: readonly string[];
  };

  const NODE_COUNT = 400;
  const GROUP_COUNT = 4;
  const TAU = Math.PI * 2;

  const SEASON_PALETTES: readonly SeasonPalette[] = [
    {
      id: 'spring',
      label: 'Spring',
      descriptor: 'Macaron Pastels',
      surface: '#fbf5f4',
      line: '#ead8d5',
      accent: '#cb7686',
      colors: ['#ffd1dc', '#ffe7a3', '#cfefcb', '#bfd8ff', '#e5d2fa', '#ffd9b8', '#cff5e6'],
    },
    {
      id: 'summer',
      label: 'Summer',
      descriptor: 'Sea Glass & Citrus',
      surface: '#f2f8f5',
      line: '#d5e6df',
      accent: '#248a82',
      colors: ['#6fd3c7', '#7ecbf9', '#ff7f8a', '#ffd65c', '#a7e3a1', '#ffc9a6', '#e6f7f2'],
    },
    {
      id: 'autumn',
      label: 'Autumn',
      descriptor: 'Harvest Glow',
      surface: '#faf4ee',
      line: '#e7d7ca',
      accent: '#c96849',
      colors: ['#d97a64', '#e1a94b', '#b86a7a', '#95a88b', '#f3e7d6', '#7b4b6b', '#c59c78'],
    },
    {
      id: 'winter',
      label: 'Winter',
      descriptor: 'Frost & Twilight',
      surface: '#f5f7fb',
      line: '#d8deeb',
      accent: '#5576a8',
      colors: ['#c7e4ff', '#a8b6ff', '#d6d0f2', '#dce2ea', '#3e6b5c', '#b56a83', '#fafaf4'],
    },
  ] as const;

  let activeSeasonId = 'spring';
  let stage: HTMLDivElement;
  let canvas: HTMLCanvasElement;

  let width = 0;
  let context: CanvasRenderingContext2D | null = null;
  let nodes: CollisionNode[] = [];
  let simulation: Simulation<CollisionNode, undefined> | null = null;

  const currentSeason = () =>
    SEASON_PALETTES.find((palette) => palette.id === activeSeasonId) ?? SEASON_PALETTES[0];

  const applyPalette = () => {
    const palette = currentSeason();

    nodes.forEach((node, index) => {
      node.color = index ? palette.colors[(index - 1) % palette.colors.length] : 'transparent';
    });

    draw();
  };

  const hexToRgb = (hex: string) => {
    const normalized = hex.replace('#', '');
    const value = normalized.length === 3
      ? normalized.split('').map((part) => part + part).join('')
      : normalized;
    const int = Number.parseInt(value, 16);

    return {
      r: (int >> 16) & 255,
      g: (int >> 8) & 255,
      b: int & 255,
    };
  };

  const mixColor = (hex: string, target: { r: number; g: number; b: number }, amount: number) => {
    const base = hexToRgb(hex);
    const mix = (start: number, end: number) => Math.round(start + (end - start) * amount);
    return `rgb(${mix(base.r, target.r)}, ${mix(base.g, target.g)}, ${mix(base.b, target.b)})`;
  };

  const drawFlatCircle = (node: CollisionNode) => {
    if (!context) return;

    const x = node.x ?? 0;
    const y = node.y ?? 0;
    const radius = node.r;

    context.fillStyle = node.color;
    context.beginPath();
    context.arc(x, y, radius, 0, TAU);
    context.fill();

    context.strokeStyle = mixColor(node.color, { r: 74, g: 74, b: 84 }, 0.18);
    context.lineWidth = Math.max(0.9, radius * 0.05);
    context.beginPath();
    context.arc(x, y, radius - Math.max(0.25, radius * 0.025), 0, TAU);
    context.stroke();
  };

  const draw = () => {
    if (!context) return;

    context.clearRect(0, 0, width, width);
    context.save();
    context.translate(width / 2, width / 2);

    for (let index = 1; index < nodes.length; index += 1) {
      drawFlatCircle(nodes[index]);
    }

    context.restore();
  };

  const createSimulation = (nextWidth: number) => {
    if (!context) return;

    simulation?.stop();
    width = nextWidth;

    const devicePixelRatio = Math.max(1, window.devicePixelRatio || 1);
    canvas.width = Math.round(width * devicePixelRatio);
    canvas.height = Math.round(width * devicePixelRatio);
    canvas.style.width = `${width}px`;
    canvas.style.height = `${width}px`;
    context.setTransform(devicePixelRatio, 0, 0, devicePixelRatio, 0, 0);

    const radiusScale = width / 200;
    const randomRadius = () => radiusScale + Math.random() * (radiusScale * 4 - radiusScale);
    const palette = currentSeason();

    nodes = Array.from({ length: NODE_COUNT }, (_, index) => ({
      r: randomRadius(),
      group: index ? (index % GROUP_COUNT) + 1 : 0,
      color: index ? palette.colors[(index - 1) % palette.colors.length] : 'transparent',
    }));

    simulation = forceSimulation(nodes)
      .alphaTarget(0.3)
      .velocityDecay(0.1)
      .force('x', forceX<CollisionNode>().strength(0.01))
      .force('y', forceY<CollisionNode>().strength(0.01))
      .force(
        'collide',
        forceCollide<CollisionNode>()
          .radius((node) => node.r + 1)
          .iterations(3),
      )
      .force(
        'charge',
        forceManyBody<CollisionNode>().strength((_, index) =>
          index ? 0 : (-width * 2) / 3,
        ),
      )
      .on('tick', draw);
  };

  const setSeason = (seasonId: string) => {
    activeSeasonId = seasonId;
    if (nodes.length) applyPalette();
  };

  onMount(() => {
    context = canvas.getContext('2d');
    if (!context) return;

    const moveRepulsor = (event: PointerEvent) => {
      if (!nodes.length) return;

      const bounds = canvas.getBoundingClientRect();
      const x = ((event.clientX - bounds.left) / bounds.width) * width;
      const y = ((event.clientY - bounds.top) / bounds.height) * width;

      nodes[0].fx = x - width / 2;
      nodes[0].fy = y - width / 2;
    };

    const preventTouchScroll = (event: TouchEvent) => {
      event.preventDefault();
    };

    const resizeObserver = new ResizeObserver(([entry]) => {
      const nextWidth = Math.max(1, Math.floor(entry.contentRect.width));
      if (nextWidth !== width) createSimulation(nextWidth);
    });

    canvas.addEventListener('pointermove', moveRepulsor);
    canvas.addEventListener('touchmove', preventTouchScroll, { passive: false });
    resizeObserver.observe(stage);

    return () => {
      canvas.removeEventListener('pointermove', moveRepulsor);
      canvas.removeEventListener('touchmove', preventTouchScroll);
      resizeObserver.disconnect();
      simulation?.stop();
    };
  });
</script>

<div
  class="collision-lab"
  style={`--collision-stage-bg: ${currentSeason().surface}; --collision-stage-line: ${currentSeason().line}; --collision-accent: ${currentSeason().accent};`}
>
  <div class="collision-toolbar" aria-label="Seasonal color palette selector">
    <div class="collision-toolbar__copy">
      <p class="collision-toolbar__eyebrow">Seasonal palettes</p>
      <p class="collision-toolbar__title">{currentSeason().label} · {currentSeason().descriptor}</p>
    </div>

    <div class="collision-toolbar__buttons" role="tablist" aria-label="Season selectors">
      {#each SEASON_PALETTES as season}
        <button
          class:active={season.id === activeSeasonId}
          type="button"
          role="tab"
          aria-selected={season.id === activeSeasonId}
          on:click={() => setSeason(season.id)}
        >
          {season.label}
        </button>
      {/each}
    </div>
  </div>

  <div class="collision-stage" bind:this={stage}>
    <canvas
      bind:this={canvas}
      aria-label={`Four hundred flat circles continuously collide while an invisible repulsor follows the pointer. Active palette: ${currentSeason().label}.`}
      role="img"
    >
      An interactive D3 collision-detection simulation.
    </canvas>
  </div>
</div>
