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

  const NODE_COUNT = 400;
  const GROUP_COUNT = 4;
  const TAU = Math.PI * 2;
  const BUBBLE_COLORS = [
    '#ecb4c3', // blush
    '#efd594', // butter
    '#c6dfaf', // pistachio
    '#bfd8ea', // powder blue
    '#d0c1e9', // lavender
    '#edc4a7', // peach
    '#bfded6', // mint
    '#e4bfd0', // rosewater
  ] as const;

  let stage: HTMLDivElement;
  let canvas: HTMLCanvasElement;

  onMount(() => {
    const context = canvas.getContext('2d');
    if (!context) return;

    let width = 0;
    let nodes: CollisionNode[] = [];
    let simulation: Simulation<CollisionNode, undefined> | null = null;

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

    const drawBubble = (node: CollisionNode) => {
      const x = node.x ?? 0;
      const y = node.y ?? 0;
      const radius = node.r;
      const outerRadius = radius + Math.max(0.8, radius * 0.12);
      const gradient = context.createRadialGradient(
        x - radius * 0.35,
        y - radius * 0.38,
        Math.max(1, radius * 0.14),
        x,
        y,
        radius * 1.03,
      );
      const innerColor = mixColor(node.color, { r: 255, g: 255, b: 255 }, 0.24);
      const midColor = mixColor(node.color, { r: 255, g: 255, b: 255 }, 0.08);
      const edgeColor = mixColor(node.color, { r: 68, g: 63, b: 88 }, 0.12);

      context.save();
      context.fillStyle = 'rgba(255, 255, 255, 0.12)';
      context.beginPath();
      context.arc(x, y, outerRadius, 0, TAU);
      context.fill();

      context.shadowColor = 'rgba(78, 67, 92, 0.12)';
      context.shadowBlur = Math.max(2, radius * 0.9);
      context.shadowOffsetY = Math.max(0.5, radius * 0.12);

      gradient.addColorStop(0, innerColor);
      gradient.addColorStop(0.55, midColor);
      gradient.addColorStop(1, edgeColor);
      context.fillStyle = gradient;
      context.beginPath();
      context.arc(x, y, radius, 0, TAU);
      context.fill();
      context.restore();

      context.strokeStyle = 'rgba(92, 78, 108, 0.22)';
      context.lineWidth = Math.max(0.9, radius * 0.06);
      context.beginPath();
      context.arc(x, y, radius - Math.max(0.35, radius * 0.03), 0, TAU);
      context.stroke();

      context.strokeStyle = 'rgba(255, 255, 255, 0.34)';
      context.lineWidth = Math.max(0.8, radius * 0.045);
      context.beginPath();
      context.arc(x - radius * 0.08, y - radius * 0.08, radius * 0.76, Math.PI * 1.1, Math.PI * 1.72);
      context.stroke();

      context.fillStyle = 'rgba(255, 255, 255, 0.38)';
      context.beginPath();
      context.arc(
        x - radius * 0.32,
        y - radius * 0.34,
        Math.max(1, radius * 0.2),
        0,
        TAU,
      );
      context.fill();
    };

    const draw = () => {
      context.clearRect(0, 0, width, width);
      context.save();
      context.translate(width / 2, width / 2);

      // Node zero is intentionally invisible. It is the pointer-controlled
      // repulsor used by the original Observable example.
      for (let index = 1; index < nodes.length; index += 1) {
        drawBubble(nodes[index]);
      }

      context.restore();
    };

    const createSimulation = (nextWidth: number) => {
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

      nodes = Array.from({ length: NODE_COUNT }, (_, index) => ({
        r: randomRadius(),
        group: index ? (index % GROUP_COUNT) + 1 : 0,
        color: index ? BUBBLE_COLORS[(index - 1) % BUBBLE_COLORS.length] : 'transparent',
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

<div class="collision-stage" bind:this={stage}>
  <canvas
    bind:this={canvas}
    aria-label="Four hundred softly colored pastel circles continuously collide while an invisible repulsor follows the pointer."
    role="img"
  >
    An interactive D3 collision-detection simulation.
  </canvas>
</div>
