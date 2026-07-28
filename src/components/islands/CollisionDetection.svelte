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
  import SeasonSelector from '@/components/islands/SeasonSelector.svelte';
  import { VALID_SEASONS } from '@/lib/seasonal-shower/seasons';
  import { seasonSprites } from '@/lib/seasonal-shower/sprites';
  import type { Season } from '@/lib/seasonal-shower/types';

  type CollisionNode = SimulationNodeDatum & {
    r: number;
    group: number;
    sprite: HTMLCanvasElement;
  };

  const NODE_COUNT = 400;
  const GROUP_COUNT = 4;

  // The seasonal drawings occupy slightly different amounts of their shared
  // 180 x 180 sprite canvas. These display scales make the visible artwork
  // approximately match each node's circular collision radius.
  const SPRITE_DISPLAY_SCALE: Record<Season, number> = {
    spring: 1.38,
    summer: 1.46,
    autumn: 1.2,
    winter: 1.42,
  };

  let activeSeason: Season = 'summer';
  let stage!: HTMLDivElement;
  let canvas!: HTMLCanvasElement;

  let width = 0;
  let context: CanvasRenderingContext2D | null = null;
  let nodes: CollisionNode[] = [];
  let simulation: Simulation<CollisionNode, undefined> | null = null;

  function readSeason(): Season {
    const season = document.documentElement.dataset.season;
    return VALID_SEASONS.includes(season as Season) ? (season as Season) : 'summer';
  }

  function applySeason(nextSeason: Season) {
    activeSeason = nextSeason;
    const sprites = seasonSprites(nextSeason);

    nodes.forEach((node, index) => {
      node.sprite = sprites[index % sprites.length]!;
    });

    draw();
  }

  function draw() {
    if (!context) return;

    context.clearRect(0, 0, width, width);
    context.save();
    context.translate(width / 2, width / 2);

    const displayScale = SPRITE_DISPLAY_SCALE[activeSeason];

    // Node zero stays invisible because it is the pointer-controlled repulsor.
    for (let index = 1; index < nodes.length; index += 1) {
      const node = nodes[index];
      const x = node.x ?? 0;
      const y = node.y ?? 0;
      const halfSize = node.r * displayScale;

      context.drawImage(
        node.sprite,
        x - halfSize,
        y - halfSize,
        halfSize * 2,
        halfSize * 2,
      );
    }

    context.restore();
  }

  function createSimulation(nextWidth: number) {
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
    const randomRadius = () =>
      radiusScale + Math.random() * (radiusScale * 4 - radiusScale);
    const sprites = seasonSprites(activeSeason);

    nodes = Array.from({ length: NODE_COUNT }, (_, index) => ({
      r: randomRadius(),
      group: index ? (index % GROUP_COUNT) + 1 : 0,
      sprite: sprites[index % sprites.length]!,
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
  }

  onMount(() => {
    context = canvas.getContext('2d');
    if (!context) return;

    activeSeason = readSeason();

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

    const seasonObserver = new MutationObserver(() => {
      const nextSeason = readSeason();
      if (nextSeason !== activeSeason) applySeason(nextSeason);
    });

    canvas.addEventListener('pointermove', moveRepulsor);
    canvas.addEventListener('touchmove', preventTouchScroll, { passive: false });
    resizeObserver.observe(stage);
    seasonObserver.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['data-season'],
    });

    return () => {
      canvas.removeEventListener('pointermove', moveRepulsor);
      canvas.removeEventListener('touchmove', preventTouchScroll);
      resizeObserver.disconnect();
      seasonObserver.disconnect();
      simulation?.stop();
    };
  });
</script>

<div class="collision-lab">
  <div class="collision-season-selector">
    <SeasonSelector />
  </div>

  <div class="collision-stage" bind:this={stage}>
    <canvas
      bind:this={canvas}
      aria-label="Four hundred seasonal objects continuously collide while an invisible repulsor follows the pointer. Use the seasonal selector to switch among spring flowers, summer beach balls, autumn leaves, and winter snowflakes."
      role="img"
    >
      An interactive D3 collision-detection simulation.
    </canvas>
  </div>
</div>
