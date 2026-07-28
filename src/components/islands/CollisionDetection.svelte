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
  };

  const NODE_COUNT = 200;
  const GROUP_COUNT = 4;
  const TAU = Math.PI * 2;

  let stage: HTMLDivElement;
  let canvas: HTMLCanvasElement;

  onMount(() => {
    const context = canvas.getContext('2d');
    if (!context) return;

    let width = 0;
    let nodes: CollisionNode[] = [];
    let simulation: Simulation<CollisionNode, undefined> | null = null;

    const draw = () => {
      context.clearRect(0, 0, width, width);
      context.save();
      context.translate(width / 2, width / 2);

      // Node zero is intentionally invisible. It is the pointer-controlled
      // repulsor used by the original Observable example.
      for (let index = 1; index < nodes.length; index += 1) {
        const node = nodes[index];
        const x = node.x ?? 0;
        const y = node.y ?? 0;

        context.beginPath();
        context.moveTo(x + node.r, y);
        context.arc(x, y, node.r, 0, TAU);
        context.fillStyle = '#ffffff';
        context.fill();
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
    aria-label="Two hundred differently sized circles continuously collide while an invisible repulsor follows the pointer."
    role="img"
  >
    An interactive D3 collision-detection simulation.
  </canvas>
</div>
