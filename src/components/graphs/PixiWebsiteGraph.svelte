<script lang="ts">
  import { onDestroy, onMount } from 'svelte';
  import {
    forceLink,
    forceManyBody,
    forceSimulation,
    forceX,
    forceY,
    type Simulation,
    type SimulationLinkDatum,
    type SimulationNodeDatum,
  } from 'd3-force';
  import type { NetworkLink, NetworkNode } from './types';

  type GraphNode = NetworkNode &
    SimulationNodeDatum & {
      radius: number;
      collisionRadius: number;
    };

  type GraphLink = Omit<NetworkLink, 'source' | 'target'> &
    SimulationLinkDatum<GraphNode> & {
      source: string | GraphNode;
      target: string | GraphNode;
    };

  type DragState = {
    pointerId: number;
    node: GraphNode;
    startClientX: number;
    startClientY: number;
    moved: boolean;
  };

  type PanState = {
    pointerId: number;
    lastClientX: number;
    lastClientY: number;
  };

  export let nodes: NetworkNode[] = [];
  export let links: NetworkLink[] = [];
  export let ariaLabel = 'Interactive website graph';

  const MIN_ZOOM = 0.18;
  const MAX_ZOOM = 5;
  const FIT_PADDING = 64;

  let hostElement!: HTMLDivElement;
  let svgElement!: SVGSVGElement;
  let width = 800;
  let height = 560;
  let graphNodes: GraphNode[] = [];
  let graphLinks: GraphLink[] = [];
  let simulation: Simulation<GraphNode, GraphLink> | null = null;
  let resizeObserver: ResizeObserver | null = null;
  let mounted = false;
  let failed = false;
  let hoveredNodeId: string | null = null;
  let dragState: DragState | null = null;
  let panState: PanState | null = null;
  let suppressClickNodeId: string | null = null;
  let viewScale = 1;
  let viewX = width / 2;
  let viewY = height / 2;
  let userMovedView = false;
  let lastSignature = '';

  $: dataSignature = JSON.stringify({ nodes, links });
  $: if (mounted && dataSignature !== lastSignature) {
    lastSignature = dataSignature;
    rebuildGraph();
  }

  const clamp = (value: number, minimum: number, maximum: number) =>
    Math.min(maximum, Math.max(minimum, value));

  function nodeRadius(node: NetworkNode) {
    if (node.current) return 6.5;
    if (node.featured) return 5.75;
    if ((node.radius ?? 0) >= 34) return 5;
    if ((node.radius ?? 0) <= 22) return 3.75;
    return 4.4;
  }

  function labelWidth(label: string) {
    return Math.min(74, Math.max(18, label.length * 3.15));
  }

  function resolveNode(value: string | GraphNode) {
    if (typeof value !== 'string') return value;
    return graphNodes.find((node) => node.id === value);
  }

  function makeGraphData() {
    // Match the official D3 force-directed graph demo: pass nodes without
    // explicit positions so d3-force initializes them with its deterministic
    // phyllotaxis layout. The extra visual fields do not affect physics.
    graphNodes = nodes.map((node) => {
      const radius = nodeRadius(node);

      return {
        ...node,
        radius,
        collisionRadius: Math.max(radius + 8, labelWidth(node.label)),
      };
    });

    // The link force mutates links, so keep the component inputs untouched.
    graphLinks = links.map((link) => ({ ...link }));
  }

  function buildSimulation() {
    simulation?.stop();

    // Match the disjoint force-directed graph demo embedded on d3js.org/d3-force:
    // default link and charge forces, plus default x/y positioning forces.
    // Do not add custom distance, strength, iterations, decay, collision,
    // or centering forces here.
    simulation = forceSimulation<GraphNode, GraphLink>(graphNodes)
      .force(
        'link',
        forceLink<GraphNode, GraphLink>(graphLinks).id((node) => node.id),
      )
      .force('charge', forceManyBody<GraphNode>())
      .force('x', forceX<GraphNode>())
      .force('y', forceY<GraphNode>())
      .on('tick', () => {
        graphNodes = graphNodes;
        graphLinks = graphLinks;
      })
      .on('end', () => {
        if (!userMovedView) fitGraph();
      });
  }

  function rebuildGraph() {
    failed = false;

    try {
      makeGraphData();
      buildSimulation();

      // The official demo starts the simulation immediately with D3's default
      // alpha, alpha decay, and velocity decay. Fit only the camera; do not
      // advance or otherwise modify the simulation.
      fitGraph();
    } catch (error) {
      console.error('Website graph failed to initialize.', error);
      failed = true;
    }
  }

  function fitGraph() {
    if (!graphNodes.length || width <= 0 || height <= 0) return;

    let minX = Number.POSITIVE_INFINITY;
    let minY = Number.POSITIVE_INFINITY;
    let maxX = Number.NEGATIVE_INFINITY;
    let maxY = Number.NEGATIVE_INFINITY;

    for (const node of graphNodes) {
      const x = node.x ?? 0;
      const y = node.y ?? 0;
      const horizontal = Math.max(node.collisionRadius, 24);
      const verticalTop = node.radius + 26;
      const verticalBottom = node.radius + 10;
      minX = Math.min(minX, x - horizontal);
      maxX = Math.max(maxX, x + horizontal);
      minY = Math.min(minY, y - verticalTop);
      maxY = Math.max(maxY, y + verticalBottom);
    }

    const graphWidth = Math.max(1, maxX - minX);
    const graphHeight = Math.max(1, maxY - minY);
    const availableWidth = Math.max(1, width - FIT_PADDING * 2);
    const availableHeight = Math.max(1, height - FIT_PADDING * 2);
    const scale = clamp(
      Math.min(availableWidth / graphWidth, availableHeight / graphHeight),
      MIN_ZOOM,
      2.25,
    );
    const centerX = (minX + maxX) / 2;
    const centerY = (minY + maxY) / 2;

    viewScale = scale;
    viewX = width / 2 - centerX * scale;
    viewY = height / 2 - centerY * scale;
    userMovedView = false;
  }

  export function resetView() {
    fitGraph();
  }

  function updateSize() {
    const rect = hostElement.getBoundingClientRect();
    const nextWidth = Math.max(320, Math.round(rect.width || hostElement.clientWidth || 800));
    const nextHeight = Math.max(260, Math.round(rect.height || hostElement.clientHeight || 560));

    if (nextWidth === width && nextHeight === height) return;

    const oldWidth = width;
    const oldHeight = height;
    width = nextWidth;
    height = nextHeight;

    if (!userMovedView) {
      fitGraph();
    } else {
      viewX += (width - oldWidth) / 2;
      viewY += (height - oldHeight) / 2;
    }
  }

  function screenPoint(event: PointerEvent | WheelEvent) {
    const rect = svgElement.getBoundingClientRect();
    return {
      x: ((event.clientX - rect.left) / Math.max(1, rect.width)) * width,
      y: ((event.clientY - rect.top) / Math.max(1, rect.height)) * height,
    };
  }

  function worldPoint(event: PointerEvent) {
    const point = screenPoint(event);
    return {
      x: (point.x - viewX) / viewScale,
      y: (point.y - viewY) / viewScale,
    };
  }

  function handleWheel(event: WheelEvent) {
    event.preventDefault();
    const point = screenPoint(event);
    const worldX = (point.x - viewX) / viewScale;
    const worldY = (point.y - viewY) / viewScale;
    const zoomFactor = Math.exp(-event.deltaY * 0.0014);
    const nextScale = clamp(viewScale * zoomFactor, MIN_ZOOM, MAX_ZOOM);

    viewScale = nextScale;
    viewX = point.x - worldX * nextScale;
    viewY = point.y - worldY * nextScale;
    userMovedView = true;
  }

  function startPan(event: PointerEvent) {
    if (event.button !== 0 || dragState) return;
    panState = {
      pointerId: event.pointerId,
      lastClientX: event.clientX,
      lastClientY: event.clientY,
    };
    svgElement.setPointerCapture(event.pointerId);
  }

  function startNodeDrag(event: PointerEvent, node: GraphNode) {
    if (event.button !== 0) return;
    event.stopPropagation();
    const point = worldPoint(event);
    node.fx = point.x;
    node.fy = point.y;
    dragState = {
      pointerId: event.pointerId,
      node,
      startClientX: event.clientX,
      startClientY: event.clientY,
      moved: false,
    };
    svgElement.setPointerCapture(event.pointerId);
    simulation?.alphaTarget(0.3).restart();
  }

  function handlePointerMove(event: PointerEvent) {
    if (dragState?.pointerId === event.pointerId) {
      const point = worldPoint(event);
      dragState.node.fx = point.x;
      dragState.node.fy = point.y;
      if (
        Math.hypot(
          event.clientX - dragState.startClientX,
          event.clientY - dragState.startClientY,
        ) > 4
      ) {
        dragState.moved = true;
      }
      return;
    }

    if (panState?.pointerId === event.pointerId) {
      const rect = svgElement.getBoundingClientRect();
      viewX += ((event.clientX - panState.lastClientX) / Math.max(1, rect.width)) * width;
      viewY += ((event.clientY - panState.lastClientY) / Math.max(1, rect.height)) * height;
      panState.lastClientX = event.clientX;
      panState.lastClientY = event.clientY;
      userMovedView = true;
    }
  }

  function endPointer(event: PointerEvent) {
    if (dragState?.pointerId === event.pointerId) {
      const { node, moved } = dragState;
      node.fx = null;
      node.fy = null;
      if (moved) {
        suppressClickNodeId = node.id;
        window.setTimeout(() => {
          if (suppressClickNodeId === node.id) suppressClickNodeId = null;
        }, 0);
      }
      dragState = null;
      simulation?.alphaTarget(0);
    }

    if (panState?.pointerId === event.pointerId) {
      panState = null;
    }

    if (svgElement.hasPointerCapture(event.pointerId)) {
      svgElement.releasePointerCapture(event.pointerId);
    }
  }

  function activateNode(node: GraphNode) {
    if (suppressClickNodeId === node.id || !node.href) return;
    if (node.external) {
      window.open(node.href, '_blank', 'noopener,noreferrer');
    } else {
      window.location.assign(node.href);
    }
  }

  function handleNodeKeydown(event: KeyboardEvent, node: GraphNode) {
    if (event.key !== 'Enter' && event.key !== ' ') return;
    event.preventDefault();
    activateNode(node);
  }

  function isConnected(link: GraphLink, nodeId: string | null) {
    if (!nodeId) return false;
    const source = resolveNode(link.source);
    const target = resolveNode(link.target);
    return source?.id === nodeId || target?.id === nodeId;
  }

  onMount(() => {
    mounted = true;
    lastSignature = dataSignature;
    updateSize();
    rebuildGraph();

    resizeObserver = new ResizeObserver(() => updateSize());
    resizeObserver.observe(hostElement);
  });

  onDestroy(() => {
    mounted = false;
    simulation?.stop();
    simulation = null;
    resizeObserver?.disconnect();
    resizeObserver = null;
  });
</script>

<div class="pixi-website-graph" bind:this={hostElement}>
  {#if failed}
    <p class="pixi-website-graph__fallback" role="status">
      The website graph could not be loaded.
    </p>
  {:else if graphNodes.length === 0}
    <p class="pixi-website-graph__fallback" role="status">
      No graph destinations were found.
    </p>
  {:else}
    <svg
      bind:this={svgElement}
      class="pixi-website-graph__svg"
      viewBox={`0 0 ${width} ${height}`}
      role="img"
      aria-label={ariaLabel}
      on:wheel={handleWheel}
      on:pointerdown={startPan}
      on:pointermove={handlePointerMove}
      on:pointerup={endPointer}
      on:pointercancel={endPointer}
    >
      <rect class="pixi-website-graph__background" width={width} height={height}></rect>

      <g transform={`translate(${viewX} ${viewY}) scale(${viewScale})`}>
        <g class="pixi-website-graph__edges" aria-hidden="true">
          {#each graphLinks as link}
            {@const source = resolveNode(link.source)}
            {@const target = resolveNode(link.target)}
            {#if source && target}
              <line
                class:pixi-website-graph__edge--active={isConnected(link, hoveredNodeId)}
                class:pixi-website-graph__edge--muted={hoveredNodeId !== null && !isConnected(link, hoveredNodeId)}
                x1={source.x ?? 0}
                y1={source.y ?? 0}
                x2={target.x ?? 0}
                y2={target.y ?? 0}
              ></line>
            {/if}
          {/each}
        </g>

        <g class="pixi-website-graph__nodes">
          {#each graphNodes as node (node.id)}
            <g
              class="pixi-website-graph__node"
              class:pixi-website-graph__node--active={hoveredNodeId === node.id}
              class:pixi-website-graph__node--current={node.current}
              transform={`translate(${node.x ?? 0} ${node.y ?? 0})`}
              role={node.href ? 'link' : 'group'}
              tabindex={node.href ? 0 : undefined}
              aria-label={node.description ? `${node.label}. ${node.description}` : node.label}
              on:pointerdown={(event) => startNodeDrag(event, node)}
              on:pointerenter={() => (hoveredNodeId = node.id)}
              on:pointerleave={() => (hoveredNodeId = null)}
              on:click={() => activateNode(node)}
              on:keydown={(event) => handleNodeKeydown(event, node)}
            >
              <circle class="pixi-website-graph__hit-area" r={node.radius}></circle>
              <circle class="pixi-website-graph__dot" r={node.radius}></circle>
              <text
                class="pixi-website-graph__label"
                y={-(node.radius + 13)}
                text-anchor="middle"
                dominant-baseline="middle"
              >{node.label}</text>
            </g>
          {/each}
        </g>
      </g>
    </svg>
  {/if}
</div>

<style>
  .pixi-website-graph {
    position: relative;
    width: 100%;
    height: 100%;
    min-width: 0;
    min-height: 0;
    overflow: hidden;
    background: var(--graph-bg, var(--bg));
    color: var(--graph-text, var(--text));
    touch-action: none;
    user-select: none;
    -webkit-user-select: none;
  }

  .pixi-website-graph__svg {
    display: block;
    width: 100%;
    height: 100%;
    overflow: hidden;
    cursor: grab;
    touch-action: none;
  }

  .pixi-website-graph__svg:active {
    cursor: grabbing;
  }

  .pixi-website-graph__background {
    fill: var(--graph-bg, var(--bg));
  }

  .pixi-website-graph__edges line {
    opacity: 0.72;
    stroke: var(--graph-edge, color-mix(in srgb, var(--text) 24%, transparent));
    stroke-width: 1;
    vector-effect: non-scaling-stroke;
    transition:
      stroke 220ms cubic-bezier(0.22, 1, 0.36, 1),
      opacity 220ms cubic-bezier(0.22, 1, 0.36, 1);
  }

  .pixi-website-graph__edges line.pixi-website-graph__edge--active {
    opacity: 1;
    stroke: var(--graph-hover, #0b6f69);
  }

  .pixi-website-graph__edges line.pixi-website-graph__edge--muted {
    opacity: 0.13;
  }

  .pixi-website-graph__node {
    color: var(--graph-node, color-mix(in srgb, var(--text) 68%, var(--bg)));
    cursor: pointer;
    opacity: 1;
    outline: none;
    transition: color 220ms cubic-bezier(0.22, 1, 0.36, 1);
  }

  .pixi-website-graph__hit-area {
    fill: transparent;
    stroke: none;
    pointer-events: all;
  }

  .pixi-website-graph__dot {
    pointer-events: none;
    fill: currentColor;
    stroke: var(--graph-node-ring, var(--graph-bg, var(--bg)));
    stroke-width: 1.25;
    vector-effect: non-scaling-stroke;
    transform-box: fill-box;
    transform-origin: center;
    transition:
      fill 220ms cubic-bezier(0.22, 1, 0.36, 1),
      stroke 220ms cubic-bezier(0.22, 1, 0.36, 1),
      transform 220ms cubic-bezier(0.22, 1, 0.36, 1);
  }

  .pixi-website-graph__node--current .pixi-website-graph__dot {
    fill: var(--graph-node-current, var(--graph-node, currentColor));
  }

  .pixi-website-graph__label {
    opacity: 0;
    fill: var(--graph-label, var(--graph-text, var(--text)));
    stroke: none;
    font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Ubuntu,
      Roboto, "Noto Sans", "Helvetica Neue", Arial, sans-serif;
    font-size: 12px;
    font-weight: 600;
    font-kerning: normal;
    font-synthesis: none;
    letter-spacing: -0.005em;
    text-rendering: geometricPrecision;
    -webkit-font-smoothing: antialiased;
    pointer-events: none;
    transform: translateY(-2px);
    transform-box: fill-box;
    transform-origin: center;
    transition:
      opacity 180ms cubic-bezier(0.22, 1, 0.36, 1),
      transform 220ms cubic-bezier(0.22, 1, 0.36, 1),
      fill 220ms cubic-bezier(0.22, 1, 0.36, 1);
  }

  .pixi-website-graph__node--active,
  .pixi-website-graph__node:focus-visible {
    color: var(--graph-hover, #0b6f69);
    opacity: 1;
  }

  .pixi-website-graph__node--active .pixi-website-graph__dot,
  .pixi-website-graph__node:focus-visible .pixi-website-graph__dot {
    fill: var(--graph-hover, #0b6f69);
    stroke: var(--graph-hover-ring, var(--graph-bg, var(--bg)));
    transform: scale(1.28);
  }

  .pixi-website-graph__node--active .pixi-website-graph__label,
  .pixi-website-graph__node:focus-visible .pixi-website-graph__label {
    opacity: 1;
    fill: var(--graph-label-active, var(--graph-text, var(--text)));
    transform: translateY(0);
  }

  .pixi-website-graph__fallback {
    position: absolute;
    inset: 0;
    display: grid;
    place-items: center;
    margin: 0;
    padding: 2rem;
    color: var(--graph-muted, var(--muted));
    font-size: 0.88rem;
    text-align: center;
  }

  @media (prefers-reduced-motion: reduce) {
    .pixi-website-graph__edges line,
    .pixi-website-graph__node,
    .pixi-website-graph__dot,
    .pixi-website-graph__label {
      transition: none;
    }
  }
</style>
