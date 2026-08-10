<script lang="ts">
  import { onDestroy, onMount } from 'svelte';
  import { Delaunay } from 'd3-delaunay';
  import {
    forceCenter,
    forceLink,
    forceManyBody,
    forceSimulation,
    type Simulation,
    type SimulationLinkDatum,
    type SimulationNodeDatum,
  } from 'd3-force';
  import { WEBSITE_GRAPH_GROUP_COLORS } from '@/config/graph';
  import type { NetworkLink, NetworkNode } from './types';

  type GraphNode = NetworkNode & SimulationNodeDatum;
  type GraphLink = Omit<NetworkLink, 'source' | 'target'> &
    SimulationLinkDatum<GraphNode> & {
      source: string | GraphNode;
      target: string | GraphNode;
    };

  type CanvasPoint = { x: number; y: number };

  type LabelPlacement = {
    x: number;
    y: number;
    anchor: 'start' | 'middle' | 'end';
    baseline: 'auto' | 'middle' | 'hanging';
  };

  export let nodes: NetworkNode[] = [];
  export let links: NetworkLink[] = [];
  export let ariaLabel = 'Interactive website graph';
  export let theme: 'light' | 'dark' | null = null;

  const NODE_RADIUS = 5;
  const LABEL_GAP = 7;

  let hostElement!: HTMLDivElement;
  let svgElement!: SVGSVGElement;
  let width = 960;
  let height = 640;
  let graphNodes: GraphNode[] = [];
  let graphLinks: GraphLink[] = [];
  let labelPlacements = new Map<string, LabelPlacement>();
  let simulation: Simulation<GraphNode, GraphLink> | null = null;
  let resizeObserver: ResizeObserver | null = null;
  let mounted = false;
  let failed = false;
  let lastSignature = '';
  let dragNodeId: string | null = null;
  let dragStartX = 0;
  let dragStartY = 0;
  let dragMoved = false;
  let suppressClickNodeId: string | null = null;

  // Camera transform for the entire graph canvas. The force simulation stays in
  // world coordinates; pan/zoom only changes how those coordinates are viewed.
  let viewX = 0;
  let viewY = 0;
  let viewScale = 1;
  let isPanning = false;
  let canvasPointers = new Map<number, CanvasPoint>();
  let panStartPointer: CanvasPoint | null = null;
  let panStartView: CanvasPoint | null = null;
  let pinchStartDistance = 1;
  let pinchStartScale = 1;
  let pinchWorldMidpoint: CanvasPoint | null = null;
  let viewAnimationFrame = 0;

  $: dataSignature = JSON.stringify({ nodes, links });
  $: if (mounted && dataSignature !== lastSignature) {
    lastSignature = dataSignature;
    rebuildGraph();
  }

  function resolveNode(value: string | GraphNode) {
    if (typeof value !== 'string') return value;
    return graphNodes.find((node) => node.id === value);
  }

  function groupForNode(node: GraphNode): keyof typeof WEBSITE_GRAPH_GROUP_COLORS {
    const path = node.id.toLowerCase();
    if (path === '/' || path === '/graph/' || path === '/graph') return 'core';
    if (/^\/(about|contact)\/?$/.test(path)) return 'profile';
    if (path.startsWith('/projects/')) return 'projects';
    if (path.startsWith('/rooms/') || path.startsWith('/halls/')) return 'spaces';
    return 'experiments';
  }

  function nodeColor(node: GraphNode) {
    return WEBSITE_GRAPH_GROUP_COLORS[groupForNode(node)];
  }

  function polygonCentroid(polygon: ArrayLike<[number, number]>) {
    let area = 0;
    let x = 0;
    let y = 0;

    for (let i = 0; i < polygon.length; i += 1) {
      const current = polygon[i];
      const next = polygon[(i + 1) % polygon.length];
      const cross = current[0] * next[1] - next[0] * current[1];
      area += cross;
      x += (current[0] + next[0]) * cross;
      y += (current[1] + next[1]) * cross;
    }

    if (Math.abs(area) < 1e-6) return [polygon[0][0], polygon[0][1]] as const;
    return [x / (3 * area), y / (3 * area)] as const;
  }

  function defaultLabel(node: GraphNode): LabelPlacement {
    return {
      x: (node.x ?? 0) + NODE_RADIUS + 2,
      y: (node.y ?? 0) + 1,
      anchor: 'start',
      baseline: 'middle',
    };
  }

  function recomputeVoronoiLabels() {
    if (!graphNodes.length) {
      labelPlacements = new Map();
      return;
    }

    if (graphNodes.length === 1) {
      labelPlacements = new Map([[graphNodes[0].id, defaultLabel(graphNodes[0])]]);
      return;
    }

    try {
      const points = graphNodes.map((node) => [node.x ?? width / 2, node.y ?? height / 2] as [number, number]);
      const delaunay = Delaunay.from(points);
      const voronoi = delaunay.voronoi([0, 0, width, height]);
      const placements = new Map<string, LabelPlacement>();

      graphNodes.forEach((node, index) => {
        const polygon = voronoi.cellPolygon(index);
        if (!polygon || polygon.length < 3) {
          placements.set(node.id, defaultLabel(node));
          return;
        }

        const [cx, cy] = polygonCentroid(polygon);
        const nx = node.x ?? width / 2;
        const ny = node.y ?? height / 2;
        const dx = cx - nx;
        const dy = cy - ny;

        // Use the Voronoi cell only to choose the clearest side for the label.
        // Keeping the label close to the node preserves the compact Observable look.
        if (Math.abs(dx) >= Math.abs(dy)) {
          const right = dx >= 0;
          placements.set(node.id, {
            x: nx + (right ? NODE_RADIUS + 2 : -(NODE_RADIUS + 2)),
            y: ny + 1,
            anchor: right ? 'start' : 'end',
            baseline: 'middle',
          });
        } else {
          const below = dy >= 0;
          placements.set(node.id, {
            x: nx,
            y: ny + (below ? NODE_RADIUS + LABEL_GAP : -(NODE_RADIUS + LABEL_GAP)),
            anchor: 'middle',
            baseline: below ? 'hanging' : 'auto',
          });
        }
      });

      labelPlacements = placements;
    } catch {
      labelPlacements = new Map(graphNodes.map((node) => [node.id, defaultLabel(node)]));
    }
  }

  function rebuildGraph() {
    failed = false;
    simulation?.stop();

    try {
      graphNodes = nodes.map((node) => ({ ...node }));
      graphLinks = links.map((link) => ({ ...link }));

      // This intentionally mirrors Guillermo Garcia's Observable example:
      // default forceLink, default forceManyBody, and forceCenter.
      simulation = forceSimulation<GraphNode, GraphLink>(graphNodes)
        .force(
          'link',
          forceLink<GraphNode, GraphLink>(graphLinks).id((node) => node.id),
        )
        .force('charge', forceManyBody<GraphNode>())
        .force('center', forceCenter(width / 2, height / 2))
        .on('tick', () => {
          recomputeVoronoiLabels();
          graphNodes = graphNodes;
          graphLinks = graphLinks;
        });

      recomputeVoronoiLabels();
    } catch (error) {
      console.error('Website graph failed to initialize.', error);
      failed = true;
    }
  }

  function updateSize() {
    const rect = hostElement.getBoundingClientRect();
    const nextWidth = Math.max(320, Math.round(rect.width || hostElement.clientWidth || 960));
    const nextHeight = Math.max(320, Math.round(rect.height || hostElement.clientHeight || 640));
    if (nextWidth === width && nextHeight === height) return;

    width = nextWidth;
    height = nextHeight;
    simulation?.force('center', forceCenter(width / 2, height / 2));
    simulation?.alpha(0.35).restart();
    recomputeVoronoiLabels();
  }

  function clampViewScale(scale: number) {
    return Math.min(8, Math.max(0.2, scale));
  }

  function clientToCanvas(clientX: number, clientY: number): CanvasPoint {
    const rect = svgElement.getBoundingClientRect();
    return {
      x: ((clientX - rect.left) / Math.max(1, rect.width)) * width,
      y: ((clientY - rect.top) / Math.max(1, rect.height)) * height,
    };
  }

  function canvasToWorld(point: CanvasPoint): CanvasPoint {
    return {
      x: (point.x - viewX) / viewScale,
      y: (point.y - viewY) / viewScale,
    };
  }

  function stopViewAnimation() {
    if (!viewAnimationFrame) return;
    cancelAnimationFrame(viewAnimationFrame);
    viewAnimationFrame = 0;
  }

  function animateViewTo(targetX: number, targetY: number, targetScale: number) {
    stopViewAnimation();
    const startX = viewX;
    const startY = viewY;
    const startScale = viewScale;
    const startTime = performance.now();
    const duration = 260;

    const step = (now: number) => {
      const raw = Math.min(1, (now - startTime) / duration);
      const eased = 1 - Math.pow(1 - raw, 3);
      viewX = startX + (targetX - startX) * eased;
      viewY = startY + (targetY - startY) * eased;
      viewScale = startScale + (targetScale - startScale) * eased;

      if (raw < 1) {
        viewAnimationFrame = requestAnimationFrame(step);
      } else {
        viewAnimationFrame = 0;
      }
    };

    viewAnimationFrame = requestAnimationFrame(step);
  }

  export function resetView() {
    animateViewTo(0, 0, 1);
  }

  function handleWheel(event: WheelEvent) {
    event.preventDefault();
    stopViewAnimation();

    const pointer = clientToCanvas(event.clientX, event.clientY);
    const world = canvasToWorld(pointer);
    const nextScale = clampViewScale(viewScale * Math.exp(-event.deltaY * 0.0015));

    viewX = pointer.x - world.x * nextScale;
    viewY = pointer.y - world.y * nextScale;
    viewScale = nextScale;
  }

  function beginPinchGesture() {
    const points = Array.from(canvasPointers.values()).slice(0, 2);
    if (points.length < 2) return;
    const [a, b] = points;
    const midpoint = { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 };
    pinchStartDistance = Math.max(1, Math.hypot(b.x - a.x, b.y - a.y));
    pinchStartScale = viewScale;
    pinchWorldMidpoint = canvasToWorld(midpoint);
  }

  function canvasPointerDown(event: PointerEvent) {
    if (event.pointerType === 'mouse' && event.button !== 0) return;
    stopViewAnimation();

    const target = event.currentTarget as SVGSVGElement;
    target.setPointerCapture(event.pointerId);
    const point = clientToCanvas(event.clientX, event.clientY);
    canvasPointers.set(event.pointerId, point);
    isPanning = true;

    if (canvasPointers.size === 1) {
      panStartPointer = point;
      panStartView = { x: viewX, y: viewY };
    } else if (canvasPointers.size === 2) {
      beginPinchGesture();
    }
  }

  function canvasPointerMove(event: PointerEvent) {
    if (!canvasPointers.has(event.pointerId)) return;
    const point = clientToCanvas(event.clientX, event.clientY);
    canvasPointers.set(event.pointerId, point);

    if (canvasPointers.size >= 2 && pinchWorldMidpoint) {
      const points = Array.from(canvasPointers.values()).slice(0, 2);
      const [a, b] = points;
      const midpoint = { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 };
      const distance = Math.max(1, Math.hypot(b.x - a.x, b.y - a.y));
      const nextScale = clampViewScale(pinchStartScale * (distance / pinchStartDistance));
      viewX = midpoint.x - pinchWorldMidpoint.x * nextScale;
      viewY = midpoint.y - pinchWorldMidpoint.y * nextScale;
      viewScale = nextScale;
      return;
    }

    if (canvasPointers.size === 1 && panStartPointer && panStartView) {
      viewX = panStartView.x + (point.x - panStartPointer.x);
      viewY = panStartView.y + (point.y - panStartPointer.y);
    }
  }

  function canvasPointerEnd(event: PointerEvent) {
    const target = event.currentTarget as SVGSVGElement;
    if (target.hasPointerCapture(event.pointerId)) {
      target.releasePointerCapture(event.pointerId);
    }
    canvasPointers.delete(event.pointerId);

    if (canvasPointers.size === 1) {
      const remaining = Array.from(canvasPointers.values())[0];
      panStartPointer = remaining;
      panStartView = { x: viewX, y: viewY };
      pinchWorldMidpoint = null;
    } else if (canvasPointers.size === 0) {
      isPanning = false;
      panStartPointer = null;
      panStartView = null;
      pinchWorldMidpoint = null;
    } else {
      beginPinchGesture();
    }
  }

  function dragStarted(event: PointerEvent, node: GraphNode) {
    if (event.button !== 0 || !event.isPrimary) return;
    event.stopPropagation();
    const target = event.currentTarget as SVGElement;
    target.setPointerCapture(event.pointerId);
    dragNodeId = node.id;
    dragStartX = event.clientX;
    dragStartY = event.clientY;
    dragMoved = false;
    simulation?.alphaTarget(0.3).restart();
    node.fx = node.x;
    node.fy = node.y;
  }

  function dragged(event: PointerEvent, node: GraphNode) {
    if (dragNodeId !== node.id) return;
    const world = canvasToWorld(clientToCanvas(event.clientX, event.clientY));
    node.fx = world.x;
    node.fy = world.y;
    if (Math.hypot(event.clientX - dragStartX, event.clientY - dragStartY) > 3) {
      dragMoved = true;
    }
  }

  function dragEnded(event: PointerEvent, node: GraphNode) {
    const target = event.currentTarget as SVGElement;
    if (target.hasPointerCapture(event.pointerId)) {
      target.releasePointerCapture(event.pointerId);
    }
    if (dragMoved) {
      suppressClickNodeId = node.id;
      window.setTimeout(() => {
        if (suppressClickNodeId === node.id) suppressClickNodeId = null;
      }, 0);
    }
    dragNodeId = null;
    dragMoved = false;
    simulation?.alphaTarget(0);
    node.fx = null;
    node.fy = null;
  }

  function activateNode(node: GraphNode) {
    if (!node.href || suppressClickNodeId === node.id) return;
    if (node.external) {
      window.open(node.href, '_blank', 'noopener,noreferrer');
    } else {
      window.location.assign(node.href);
    }
  }

  function handleNodeClick(event: MouseEvent, node: GraphNode) {
    event.preventDefault();
    activateNode(node);
  }

  function placementFor(node: GraphNode) {
    return labelPlacements.get(node.id) ?? defaultLabel(node);
  }

  onMount(() => {
    mounted = true;
    lastSignature = dataSignature;
    updateSize();
    rebuildGraph();
    resizeObserver = new ResizeObserver(updateSize);
    resizeObserver.observe(hostElement);

    // Pan/zoom are canvas gestures, not control semantics. Register them
    // imperatively so the SVG stays a graphics container while graph nodes
    // remain native keyboard-accessible links.
    svgElement.addEventListener('wheel', handleWheel, { passive: false });
    svgElement.addEventListener('pointerdown', canvasPointerDown);
    svgElement.addEventListener('pointermove', canvasPointerMove);
    svgElement.addEventListener('pointerup', canvasPointerEnd);
    svgElement.addEventListener('pointercancel', canvasPointerEnd);
  });

  onDestroy(() => {
    mounted = false;
    stopViewAnimation();
    simulation?.stop();
    simulation = null;
    resizeObserver?.disconnect();
    resizeObserver = null;

    if (svgElement) {
      svgElement.removeEventListener('wheel', handleWheel);
      svgElement.removeEventListener('pointerdown', canvasPointerDown);
      svgElement.removeEventListener('pointermove', canvasPointerMove);
      svgElement.removeEventListener('pointerup', canvasPointerEnd);
      svgElement.removeEventListener('pointercancel', canvasPointerEnd);
    }
  });
</script>

<div
  class="voronoi-website-graph"
  data-graph-theme={theme ?? undefined}
  bind:this={hostElement}
>
  {#if failed}
    <p class="voronoi-website-graph__fallback" role="status">The website graph could not be loaded.</p>
  {:else}
    <svg
      bind:this={svgElement}
      class:voronoi-website-graph__svg--panning={isPanning}
      class="voronoi-website-graph__svg"
      viewBox={`0 0 ${width} ${height}`}
    >
      <title>{ariaLabel}</title>

      <rect
        class="voronoi-website-graph__background"
        width={width}
        height={height}
      ></rect>

      <g class="voronoi-website-graph__viewport" transform={`translate(${viewX} ${viewY}) scale(${viewScale})`}>
      <g class="voronoi-website-graph__links" aria-hidden="true">
        {#each graphLinks as link}
          {@const source = resolveNode(link.source)}
          {@const target = resolveNode(link.target)}
          {#if source && target}
            <line
              x1={source.x ?? 0}
              y1={source.y ?? 0}
              x2={target.x ?? 0}
              y2={target.y ?? 0}
            ></line>
          {/if}
        {/each}
      </g>

      <g class="voronoi-website-graph__nodes">
        {#each graphNodes as node (node.id)}
          {@const label = placementFor(node)}
          {#if node.href}
            <a
              class="voronoi-website-graph__node"
              href={node.href}
              target={node.external ? '_blank' : undefined}
              rel={node.external ? 'noopener noreferrer' : undefined}
              aria-label={node.description ? `${node.label}. ${node.description}` : node.label}
              on:pointerdown={(event) => dragStarted(event, node)}
              on:pointermove={(event) => dragged(event, node)}
              on:pointerup={(event) => dragEnded(event, node)}
              on:pointercancel={(event) => dragEnded(event, node)}
              on:click={(event) => handleNodeClick(event, node)}
            >
              <circle
                class="voronoi-website-graph__dot"
                cx={node.x ?? 0}
                cy={node.y ?? 0}
                r={NODE_RADIUS}
                fill={nodeColor(node)}
              ></circle>

              <text
                class="voronoi-website-graph__label"
                x={label.x}
                y={label.y}
                text-anchor={label.anchor}
                dominant-baseline={label.baseline}
              >{node.label}</text>
            </a>
          {:else}
            <g
              class="voronoi-website-graph__node"
              role="group"
              aria-label={node.description ? `${node.label}. ${node.description}` : node.label}
            >
              <circle
                class="voronoi-website-graph__dot"
                cx={node.x ?? 0}
                cy={node.y ?? 0}
                r={NODE_RADIUS}
                fill={nodeColor(node)}
              ></circle>

              <text
                class="voronoi-website-graph__label"
                x={label.x}
                y={label.y}
                text-anchor={label.anchor}
                dominant-baseline={label.baseline}
              >{node.label}</text>
            </g>
          {/if}
        {/each}
      </g>
      </g>
    </svg>
  {/if}
</div>

<style>
  .voronoi-website-graph {
    position: relative;
    width: 100%;
    height: 100%;
    overflow: hidden;
    background: #fff;
    touch-action: none;
    user-select: none;
    -webkit-user-select: none;
  }

  .voronoi-website-graph[data-graph-theme='dark'] {
    background: #000;
  }

  :global(html[data-theme='dark']) .voronoi-website-graph:not([data-graph-theme]) {
    background: #000;
  }

  .voronoi-website-graph__svg {
    display: block;
    width: 100%;
    height: 100%;
    overflow: hidden;
    cursor: grab;
  }

  .voronoi-website-graph__svg--panning {
    cursor: grabbing;
  }

  .voronoi-website-graph__background {
    fill: #fff;
    pointer-events: all;
  }

  .voronoi-website-graph[data-graph-theme='dark'] .voronoi-website-graph__background {
    fill: #000;
  }

  :global(html[data-theme='dark']) .voronoi-website-graph:not([data-graph-theme]) .voronoi-website-graph__background {
    fill: #000;
  }

  .voronoi-website-graph__links {
    pointer-events: none;
  }

  .voronoi-website-graph__links line {
    stroke: #999;
    stroke-opacity: 0.6;
    stroke-width: 1px;
  }

  .voronoi-website-graph__node {
    outline: none;
  }

  .voronoi-website-graph__dot {
    stroke: none;
    cursor: pointer;
  }

  .voronoi-website-graph__node:focus-visible .voronoi-website-graph__dot {
    stroke: currentColor;
    stroke-width: 1.5px;
  }

  .voronoi-website-graph__label {
    fill: #000;
    stroke: none;
    pointer-events: none;
    font-family: "Times New Roman", Times, serif;
    font-size: 10px;
    font-weight: 400;
    letter-spacing: 0;
    text-rendering: geometricPrecision;
  }

  .voronoi-website-graph[data-graph-theme='dark'] .voronoi-website-graph__label {
    fill: #fff;
  }

  :global(html[data-theme='dark']) .voronoi-website-graph:not([data-graph-theme]) .voronoi-website-graph__label {
    fill: #fff;
  }

  .voronoi-website-graph__fallback {
    position: absolute;
    inset: 0;
    display: grid;
    place-items: center;
    margin: 0;
    color: #000;
    font-size: 12px;
  }

  .voronoi-website-graph[data-graph-theme='dark'] .voronoi-website-graph__fallback {
    color: #fff;
  }

  :global(html[data-theme='dark']) .voronoi-website-graph:not([data-graph-theme]) .voronoi-website-graph__fallback {
    color: #fff;
  }
</style>
