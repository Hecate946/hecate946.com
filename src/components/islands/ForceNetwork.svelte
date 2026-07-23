<script lang="ts">
  import { onDestroy, onMount } from 'svelte';
  import { trackEvent } from '@/lib/analytics';
  import {
    forceCollide,
    forceLink,
    forceManyBody,
    forceSimulation,
    forceX,
    forceY,
    type Simulation,
    type SimulationLinkDatum,
    type SimulationNodeDatum,
  } from 'd3-force';
  import type { ForceNetworkSettings, NetworkLink, NetworkNode } from './types';

  type SimulationNode = NetworkNode &
    SimulationNodeDatum & {
      anchorX: number;
      anchorY: number;
      baseRadius: number;
      radius: number;
    };

  type SimulationLink = Omit<NetworkLink, 'source' | 'target'> &
    SimulationLinkDatum<SimulationNode> & {
      source: string | SimulationNode;
      target: string | SimulationNode;
      originalSource: string;
      originalTarget: string;
      order: number;
    };

  type RenderedLink = {
    key: string;
    sourceId: string;
    targetId: string;
    kind: 'primary' | 'secondary';
    d: string;
    accent: string;
    x1: number;
    y1: number;
    x2: number;
    y2: number;
  };

  type DragState = {
    nodeId: string;
    pointerId: number;
    startClientX: number;
    startClientY: number;
    moved: boolean;
  };

  export let nodes: NetworkNode[] = [];
  export let links: NetworkLink[] = [];
  export let centerNodeId = '';
  export let ariaLabel = 'Interactive network graph';
  export let height = 'min(68svh, 44rem)';
  export let idPrefix = 'force-network';
  export let showHint = true;
  export let settings: ForceNetworkSettings = {};

  const defaults: Required<ForceNetworkSettings> = {
    layout: 'anchored',
    radialRadius: 0.325,
    radialStartAngle: -Math.PI / 2,
    chargeStrength: -255,
    centerChargeMultiplier: 1.45,
    anchorStrength: 0.085,
    centerAnchorStrength: 0.22,
    collisionPadding: 20,
    linkDistance: 175,
    linkStrength: 0.12,
    velocityDecay: 0.34,
    alphaDecay: 0.045,
    dragAlphaTarget: 0.24,
    entranceRadius: 36,
  };

  let config = { ...defaults, ...settings };
  let containerElement!: HTMLDivElement;
  let svgElement!: SVGSVGElement;
  let width = 760;
  let heightPixels = 620;
  let simulationNodes: SimulationNode[] = [];
  let simulationLinks: SimulationLink[] = [];
  let renderedLinks: RenderedLink[] = [];
  let simulation: Simulation<SimulationNode, SimulationLink> | null = null;
  let resizeObserver: ResizeObserver | null = null;
  let reducedMotionQuery: MediaQueryList | null = null;
  let reducedMotion = false;
  let activeNodeId: string | null = null;
  let dragState: DragState | null = null;
  let suppressedClickId: string | null = null;
  let suppressTimer: ReturnType<typeof setTimeout> | null = null;
  let mounted = false;
  let lastSignature = '';
  let dataSignature = '';

  $: config = { ...defaults, ...settings };
  $: dataSignature = JSON.stringify({ nodes, links, centerNodeId, settings });
  $: if (mounted && dataSignature !== lastSignature) {
    lastSignature = dataSignature;
    queueMicrotask(() => rebuildSimulation(true));
  }

  const clamp = (value: number, minimum: number, maximum: number) =>
    Math.min(maximum, Math.max(minimum, value));

  const safeId = (value: string) => value.replace(/[^a-zA-Z0-9_-]/g, '-');

  const nodeById = (id: string) => simulationNodes.find((node) => node.id === id);

  const resolveNode = (value: string | SimulationNode) =>
    typeof value === 'string' ? nodeById(value) : value;

  const nodeAccent = (node: SimulationNode) => node.accent ?? 'var(--accent, #8b7cff)';

  const nodeRadius = (node: NetworkNode) => node.radius ?? (node.featured ? 72 : 43);

  const graphScale = () => clamp(Math.min(width, heightPixels) / 620, 0.72, 1);

  const linkScale = () => clamp(Math.min(width, heightPixels) / 620, 0.72, 1.08);

  function anchorFor(node: NetworkNode, index: number, total: number) {
    if (node.id === centerNodeId) {
      return { x: width / 2, y: heightPixels / 2 };
    }

    if (config.layout === 'radial') {
      const outerNodes = nodes.filter((item) => item.id !== centerNodeId);
      const outerIndex = Math.max(0, outerNodes.findIndex((item) => item.id === node.id));
      const outerCount = Math.max(1, outerNodes.length);
      const radius = Math.min(width, heightPixels) * config.radialRadius;
      const angle = config.radialStartAngle + (outerIndex * Math.PI * 2) / outerCount;

      return {
        x: width / 2 + Math.cos(angle) * radius,
        y: heightPixels / 2 + Math.sin(angle) * radius,
      };
    }

    if (node.anchor) {
      return {
        x: node.anchor.x * width,
        y: node.anchor.y * heightPixels,
      };
    }

    const hasCenter = nodes.some((item) => item.id === centerNodeId);
    const outerIndex = Math.max(0, index - (hasCenter ? 1 : 0));
    const outerCount = Math.max(1, total - (hasCenter ? 1 : 0));
    const radius = Math.min(width, heightPixels) * 0.325;
    const angle = -Math.PI / 2 + (outerIndex * Math.PI * 2) / outerCount;

    return {
      x: width / 2 + Math.cos(angle) * radius,
      y: heightPixels / 2 + Math.sin(angle) * radius,
    };
  }

  function updateAnchors() {
    simulationNodes.forEach((node, index) => {
      const anchor = anchorFor(node, index, simulationNodes.length);
      node.anchorX = anchor.x;
      node.anchorY = anchor.y;
      node.radius = node.baseRadius * graphScale();
    });
  }

  function createSimulationNodes(animateEntrance: boolean) {
    const centerX = width / 2;
    const centerY = heightPixels / 2;

    simulationNodes = nodes.map((node, index) => {
      const anchor = anchorFor(node, index, nodes.length);
      const angle = index * 2.399963229728653;
      const entranceDistance = animateEntrance && !reducedMotion ? config.entranceRadius : 0;

      return {
        ...node,
        baseRadius: nodeRadius(node),
        radius: nodeRadius(node) * graphScale(),
        anchorX: anchor.x,
        anchorY: anchor.y,
        x: entranceDistance ? centerX + Math.cos(angle) * entranceDistance : anchor.x,
        y: entranceDistance ? centerY + Math.sin(angle) * entranceDistance : anchor.y,
        vx: 0,
        vy: 0,
      };
    });

    simulationLinks = links.map((link, order) => ({
      ...link,
      source: link.source,
      target: link.target,
      originalSource: link.source,
      originalTarget: link.target,
      order,
    }));
  }

  function configureForces() {
    if (!simulation) return;

    const linkForce = forceLink<SimulationNode, SimulationLink>(simulationLinks)
      .id((node) => node.id)
      .distance((link) => {
        if (link.distance !== undefined) return link.distance * linkScale();
        if (config.layout === 'radial') {
          return Math.min(width, heightPixels) * config.radialRadius;
        }
        return config.linkDistance * linkScale();
      })
      .strength((link) => link.strength ?? config.linkStrength);

    const chargeForce = forceManyBody<SimulationNode>().strength((node) =>
      node.id === centerNodeId
        ? config.chargeStrength * config.centerChargeMultiplier
        : config.chargeStrength,
    );

    const xForce = forceX<SimulationNode>((node) => node.anchorX).strength((node) =>
      node.id === centerNodeId ? config.centerAnchorStrength : config.anchorStrength,
    );

    const yForce = forceY<SimulationNode>((node) => node.anchorY).strength((node) =>
      node.id === centerNodeId ? config.centerAnchorStrength : config.anchorStrength,
    );

    simulation
      .nodes(simulationNodes)
      .velocityDecay(config.velocityDecay)
      .alphaDecay(config.alphaDecay)
      .force('link', linkForce)
      .force('charge', chargeForce)
      .force(
        'collision',
        forceCollide<SimulationNode>()
          .radius((node) => node.radius + config.collisionPadding)
          .strength(0.92)
          .iterations(2),
      )
      .force('x', xForce)
      .force('y', yForce)
      .on('tick', () => {
        keepNodesInBounds();
        syncRenderedState();
      });
  }

  function rebuildSimulation(animateEntrance = false) {
    simulation?.stop();
    createSimulationNodes(animateEntrance);
    simulation = forceSimulation<SimulationNode, SimulationLink>(simulationNodes);
    configureForces();
    syncRenderedState();

    if (reducedMotion) {
      simulation.stop();
      for (let index = 0; index < 220; index += 1) simulation.tick();
      keepNodesInBounds();
      syncRenderedState();
      return;
    }

    simulation.alpha(0.7).restart();
  }

  function keepNodesInBounds() {
    for (const node of simulationNodes) {
      const xPadding = node.radius + 12;
      const topPadding = node.radius + 12;
      const bottomPadding = node.radius + (node.description ? 58 : 40);

      if (typeof node.x === 'number') {
        node.x = clamp(node.x, xPadding, Math.max(xPadding, width - xPadding));
      }

      if (typeof node.y === 'number') {
        node.y = clamp(node.y, topPadding, Math.max(topPadding, heightPixels - bottomPadding));
      }
    }
  }

  function updateDimensions() {
    if (!containerElement) return;
    const bounds = containerElement.getBoundingClientRect();
    if (bounds.width < 1 || bounds.height < 1) return;

    const oldWidth = width;
    const oldHeight = heightPixels;
    width = bounds.width;
    heightPixels = bounds.height;

    if (simulationNodes.length === 0) return;

    for (const node of simulationNodes) {
      if (typeof node.x === 'number') node.x *= width / oldWidth;
      if (typeof node.y === 'number') node.y *= heightPixels / oldHeight;
    }

    updateAnchors();
    configureForces();

    if (reducedMotion) {
      simulation?.stop();
      for (let index = 0; index < 100; index += 1) simulation?.tick();
      syncRenderedState();
    } else {
      simulation?.alpha(0.38).restart();
    }
  }

  function pointerPosition(event: PointerEvent) {
    const bounds = svgElement.getBoundingClientRect();
    return {
      x: ((event.clientX - bounds.left) / bounds.width) * width,
      y: ((event.clientY - bounds.top) / bounds.height) * heightPixels,
    };
  }

  function startDrag(event: PointerEvent, node: SimulationNode) {
    if (event.button !== 0) return;
    dragState = {
      nodeId: node.id,
      pointerId: event.pointerId,
      startClientX: event.clientX,
      startClientY: event.clientY,
      moved: false,
    };

    activeNodeId = node.id;
    node.fx = node.x;
    node.fy = node.y;
    (event.currentTarget as SVGAElement).setPointerCapture(event.pointerId);
    simulation?.alphaTarget(config.dragAlphaTarget).restart();
  }

  function moveDrag(event: PointerEvent, node: SimulationNode) {
    if (!dragState || dragState.nodeId !== node.id || dragState.pointerId !== event.pointerId) {
      return;
    }

    const distance = Math.hypot(
      event.clientX - dragState.startClientX,
      event.clientY - dragState.startClientY,
    );

    if (distance > 5) dragState.moved = true;

    const point = pointerPosition(event);
    const xPadding = node.radius + 12;
    const bottomPadding = node.radius + (node.description ? 58 : 40);
    node.fx = clamp(point.x, xPadding, width - xPadding);
    node.fy = clamp(point.y, node.radius + 12, heightPixels - bottomPadding);
  }

  function finishDrag(event: PointerEvent, node: SimulationNode) {
    if (!dragState || dragState.nodeId !== node.id || dragState.pointerId !== event.pointerId) {
      return;
    }

    const moved = dragState.moved;
    dragState = null;

    if ((event.currentTarget as SVGAElement).hasPointerCapture(event.pointerId)) {
      (event.currentTarget as SVGAElement).releasePointerCapture(event.pointerId);
    }

    node.fx = null;
    node.fy = null;

    if (moved) {
      trackEvent('graph_drag', { node: node.id });
      suppressedClickId = node.id;
      if (suppressTimer) clearTimeout(suppressTimer);
      suppressTimer = setTimeout(() => {
        suppressedClickId = null;
      }, 220);
    }

    if (reducedMotion) {
      node.x = node.anchorX;
      node.y = node.anchorY;
      node.vx = 0;
      node.vy = 0;
      syncRenderedState();
    } else {
      simulation?.alphaTarget(0).alpha(0.44).restart();
    }
  }

  function cancelDrag(event: PointerEvent, node: SimulationNode) {
    finishDrag(event, node);
  }

  function handleNodeClick(event: MouseEvent, node: SimulationNode) {
    if (suppressedClickId === node.id || !node.href) {
      event.preventDefault();
      event.stopPropagation();
      return;
    }

    trackEvent('graph_node_opened', { node: node.id });
  }

  function isLinkActive(link: RenderedLink) {
    return (
      activeNodeId !== null &&
      (link.sourceId === activeNodeId || link.targetId === activeNodeId)
    );
  }

  function isNodeConnected(nodeId: string) {
    if (!activeNodeId || nodeId === activeNodeId) return true;
    return simulationLinks.some(
      (link) =>
        (link.originalSource === activeNodeId && link.originalTarget === nodeId) ||
        (link.originalTarget === activeNodeId && link.originalSource === nodeId),
    );
  }

  function renderedLinkPath(link: SimulationLink) {
    const source = resolveNode(link.source);
    const target = resolveNode(link.target);
    if (!source || !target) return '';

    const sourceX = source.x ?? source.anchorX;
    const sourceY = source.y ?? source.anchorY;
    const targetX = target.x ?? target.anchorX;
    const targetY = target.y ?? target.anchorY;
    const dx = targetX - sourceX;
    const dy = targetY - sourceY;
    const distance = Math.max(0.001, Math.hypot(dx, dy));
    const curve = link.curve ?? 0;

    // Edges are intentionally drawn center-to-center. Because the edge group is
    // behind the node group, each solid node masks the portion beneath it and
    // the visible line appears to terminate exactly at the node boundary.
    if (Math.abs(curve) < 0.1) {
      return `M ${sourceX} ${sourceY} L ${targetX} ${targetY}`;
    }

    const midpointX = (sourceX + targetX) / 2;
    const midpointY = (sourceY + targetY) / 2;
    const normalX = -dy / distance;
    const normalY = dx / distance;
    return `M ${sourceX} ${sourceY} Q ${midpointX + normalX * curve} ${midpointY + normalY * curve} ${targetX} ${targetY}`;
  }

  function syncRenderedState() {
    // D3 mutates node/link objects in place. Svelte therefore needs new array
    // identities for both layers on every tick. Previously only the node array
    // was invalidated, which left the edge paths frozen at their entrance
    // coordinates while the nodes continued moving.
    simulationNodes = [...simulationNodes];
    renderedLinks = simulationLinks
      .map((link, index) => {
        const target = nodeById(link.originalTarget);
        const d = renderedLinkPath(link);
        if (!d) return null;

        const source = nodeById(link.originalSource);
        return {
          key: `${link.originalSource}-${link.originalTarget}-${index}`,
          sourceId: link.originalSource,
          targetId: link.originalTarget,
          kind: link.kind ?? 'primary',
          d,
          accent: target ? nodeAccent(target) : 'var(--accent, #8b7cff)',
          x1: source?.x ?? source?.anchorX ?? width / 2,
          y1: source?.y ?? source?.anchorY ?? heightPixels / 2,
          x2: target?.x ?? target?.anchorX ?? width / 2,
          y2: target?.y ?? target?.anchorY ?? heightPixels / 2,
        } satisfies RenderedLink;
      })
      .filter((link): link is RenderedLink => link !== null);
  }

  function labelY(node: SimulationNode) {
    return node.radius + 24;
  }

  function descriptionY(node: SimulationNode) {
    return node.radius + 42;
  }

  function iconSize(node: SimulationNode) {
    return node.featured ? Math.min(44, node.radius * 0.72) : Math.min(36, node.radius * 0.94);
  }

  function targetFor(node: SimulationNode) {
    return node.external ? '_blank' : undefined;
  }

  function relFor(node: SimulationNode) {
    return node.external ? 'noreferrer' : undefined;
  }

  onMount(() => {
    mounted = true;
    lastSignature = dataSignature;
    reducedMotionQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    reducedMotion = reducedMotionQuery.matches;

    const handleReducedMotionChange = (event: MediaQueryListEvent) => {
      reducedMotion = event.matches;
      rebuildSimulation(false);
    };

    reducedMotionQuery.addEventListener('change', handleReducedMotionChange);
    resizeObserver = new ResizeObserver(updateDimensions);
    resizeObserver.observe(containerElement);
    updateDimensions();
    rebuildSimulation(true);

    return () => {
      reducedMotionQuery?.removeEventListener('change', handleReducedMotionChange);
    };
  });

  onDestroy(() => {
    mounted = false;
    simulation?.stop();
    resizeObserver?.disconnect();
    if (suppressTimer) clearTimeout(suppressTimer);
  });
</script>

<div
  class="force-network"
  bind:this={containerElement}
  style={`--network-height: ${height};`}
  data-active={activeNodeId ?? undefined}
>
  <svg
    bind:this={svgElement}
    class="force-network__canvas"
    viewBox={`0 0 ${width} ${heightPixels}`}
    role="img"
    aria-label={ariaLabel}
    preserveAspectRatio="xMidYMid meet"
  >
    <defs>
      {#each simulationNodes.filter((node) => node.imageSrc) as node (node.id)}
        <clipPath id={`${idPrefix}-${safeId(node.id)}-clip`}>
          <circle r={Math.max(1, node.radius - 3)} />
        </clipPath>
      {/each}

      {#each renderedLinks as link (link.key)}
        <linearGradient
          id={`${idPrefix}-${safeId(link.key)}-gradient`}
          gradientUnits="userSpaceOnUse"
          x1={link.x1}
          y1={link.y1}
          x2={link.x2}
          y2={link.y2}
        >
          <stop offset="0%" stop-color="var(--network-edge-start)" stop-opacity="0.72" />
          <stop offset="100%" stop-color={link.accent} stop-opacity="0.88" />
        </linearGradient>
      {/each}
    </defs>

    <g class="force-network__links" aria-hidden="true">
      {#each renderedLinks as link (link.key)}
        <path
          d={link.d}
          class:force-network__link--primary={link.kind === 'primary'}
          class:force-network__link--secondary={link.kind === 'secondary'}
          class:force-network__link--active={isLinkActive(link)}
          class:force-network__link--muted={activeNodeId !== null && !isLinkActive(link)}
          class="force-network__link"
          style={`--link-accent: ${link.accent}; stroke: url(#${idPrefix}-${safeId(link.key)}-gradient);`}
        />
      {/each}
    </g>

    <g class="force-network__nodes">
      {#each simulationNodes as node (node.id)}
        <a
          href={node.href}
          target={targetFor(node)}
          rel={relFor(node)}
          class="force-network__node"
          class:force-network__node--featured={node.featured}
          class:force-network__node--active={activeNodeId === node.id}
          class:force-network__node--connected={activeNodeId !== null && isNodeConnected(node.id)}
          class:force-network__node--muted={activeNodeId !== null && !isNodeConnected(node.id)}
          class:force-network__node--dragging={dragState?.nodeId === node.id}
          transform={`translate(${node.x ?? node.anchorX} ${node.y ?? node.anchorY})`}
          style={`--node-accent: ${nodeAccent(node)};`}
          aria-label={node.description ? `${node.label}: ${node.description}` : node.label}
          on:pointerdown={(event) => startDrag(event, node)}
          on:pointermove={(event) => moveDrag(event, node)}
          on:pointerup={(event) => finishDrag(event, node)}
          on:pointercancel={(event) => cancelDrag(event, node)}
          on:pointerenter={() => (activeNodeId = node.id)}
          on:pointerleave={() => {
            if (dragState?.nodeId !== node.id) activeNodeId = null;
          }}
          on:focus={() => (activeNodeId = node.id)}
          on:blur={() => (activeNodeId = null)}
          on:click={(event) => handleNodeClick(event, node)}
          on:dragstart={(event) => event.preventDefault()}
        >
          <title>{node.description ? `${node.label} — ${node.description}` : node.label}</title>
          <circle class="force-network__node-surface" r={node.radius} />

          {#if node.imageSrc}
            <image
              href={node.imageSrc}
              x={-node.radius + 4}
              y={-node.radius + 4}
              width={(node.radius - 4) * 2}
              height={(node.radius - 4) * 2}
              preserveAspectRatio="xMidYMid slice"
              clip-path={`url(#${idPrefix}-${safeId(node.id)}-clip)`}
              draggable="false"
            />
          {:else if node.icon}
            {@const size = iconSize(node)}
            <svg
              class="force-network__icon"
              x={-size / 2}
              y={-size / 2}
              width={size}
              height={size}
              viewBox={node.icon.viewBox ?? '0 0 24 24'}
              aria-hidden="true"
            >
              {#each node.icon.paths as path}
                <path d={path} />
              {/each}
            </svg>
          {/if}

          <text class="force-network__label" y={labelY(node)}>{node.label}</text>
          {#if node.description}
            <text
              class="force-network__description"
              class:force-network__description--visible={activeNodeId === node.id}
              y={descriptionY(node)}
            >
              {node.description}
            </text>
          {/if}
        </a>
      {/each}
    </g>
  </svg>

  {#if showHint}
    <p class="force-network__hint">Drag the nodes · select one to explore</p>
  {/if}
</div>

<style>
  .force-network {
    --network-canvas: #ffffff;
    --network-grid: rgba(15, 23, 42, 0.055);
    --network-edge-start: #64748b;
    --network-node-fill: #f4f5f7;
    --network-node-fill-hover: #e9edf2;
    --network-node-border: #cbd2dc;
    --network-label: #111827;
    --network-muted: #687184;

    position: relative;
    width: 100%;
    height: var(--network-height, min(68svh, 44rem));
    min-height: 25rem;
    overflow: hidden;
    border: 1px solid var(--network-node-border);
    border-radius: 0.65rem;
    background-color: var(--network-canvas);
    background-image:
      linear-gradient(var(--network-grid) 1px, transparent 1px),
      linear-gradient(90deg, var(--network-grid) 1px, transparent 1px);
    background-position: center;
    background-size: 2.25rem 2.25rem;
    isolation: isolate;
    contain: layout paint style;
  }

  :global([data-theme='dark']) .force-network,
  :global([data-color-scheme='dark']) .force-network,
  :global(.dark) .force-network {
    --network-canvas: #000000;
    --network-grid: rgba(255, 255, 255, 0.065);
    --network-edge-start: #94a3b8;
    --network-node-fill: #111316;
    --network-node-fill-hover: #1b1f24;
    --network-node-border: #343b45;
    --network-label: #f8fafc;
    --network-muted: #9aa4b2;
  }

  :global([data-theme='light']) .force-network,
  :global([data-color-scheme='light']) .force-network,
  :global(.light) .force-network {
    --network-canvas: #ffffff;
    --network-grid: rgba(15, 23, 42, 0.055);
    --network-edge-start: #64748b;
    --network-node-fill: #f4f5f7;
    --network-node-fill-hover: #e9edf2;
    --network-node-border: #cbd2dc;
    --network-label: #111827;
    --network-muted: #687184;
  }

  @media (prefers-color-scheme: dark) {
    :global(html:not([data-theme='light']):not([data-color-scheme='light']):not(.light)) .force-network {
      --network-canvas: #000000;
      --network-grid: rgba(255, 255, 255, 0.065);
      --network-edge-start: #94a3b8;
      --network-node-fill: #111316;
      --network-node-fill-hover: #1b1f24;
      --network-node-border: #343b45;
      --network-label: #f8fafc;
      --network-muted: #9aa4b2;
    }
  }

  .force-network__canvas {
    display: block;
    width: 100%;
    height: 100%;
    overflow: visible;
    touch-action: none;
  }

  .force-network__link {
    fill: none;
    stroke-linecap: round;
    vector-effect: non-scaling-stroke;
    transition: opacity 140ms ease, stroke-width 140ms ease;
  }

  .force-network__link--primary {
    stroke-width: 2.5;
    opacity: 0.78;
  }

  .force-network__link--secondary {
    stroke-width: 1.1;
    opacity: 0.28;
  }

  .force-network__link--active {
    stroke-width: 3.25;
    opacity: 1;
  }

  .force-network__link--muted { opacity: 0.1; }

  .force-network__node {
    color: inherit;
    cursor: grab;
    outline: none;
    text-decoration: none;
    touch-action: none;
    user-select: none;
    -webkit-tap-highlight-color: transparent;
    transition: opacity 140ms ease;
  }

  .force-network__node--dragging { cursor: grabbing; }
  .force-network__node--muted { opacity: 0.3; }

  .force-network__node-surface {
    fill: var(--network-node-fill);
    stroke: var(--network-node-border);
    stroke-width: 1.5;
    vector-effect: non-scaling-stroke;
    transition: fill 140ms ease, stroke 140ms ease, stroke-width 140ms ease;
  }

  .force-network__node--featured .force-network__node-surface {
    stroke: color-mix(in srgb, var(--node-accent) 48%, var(--network-node-border));
    stroke-width: 2;
  }

  .force-network__node:hover .force-network__node-surface,
  .force-network__node:focus-visible .force-network__node-surface,
  .force-network__node--active .force-network__node-surface,
  .force-network__node--dragging .force-network__node-surface {
    fill: var(--network-node-fill-hover);
    stroke: var(--node-accent);
    stroke-width: 2.25;
  }

  .force-network__node:focus-visible .force-network__node-surface { stroke-width: 3; }

  .force-network__icon {
    overflow: visible;
    fill: none;
    stroke: var(--node-accent);
    stroke-linecap: round;
    stroke-linejoin: round;
    stroke-width: 1.85;
    vector-effect: non-scaling-stroke;
    pointer-events: none;
  }

  .force-network__label,
  .force-network__description {
    fill: var(--network-label);
    font-family: var(--font-sans, system-ui, sans-serif);
    text-anchor: middle;
    pointer-events: none;
  }

  .force-network__label {
    font-size: 0.8rem;
    font-weight: 650;
    letter-spacing: 0.005em;
  }

  .force-network__description {
    fill: var(--network-muted);
    font-size: 0.65rem;
    opacity: 0;
    transition: opacity 140ms ease;
  }

  .force-network__description--visible { opacity: 1; }

  .force-network__hint {
    position: absolute;
    right: 0;
    bottom: 0;
    left: 0;
    margin: 0;
    padding: 0.65rem 1rem;
    color: var(--network-muted);
    font-family: var(--font-sans, system-ui, sans-serif);
    font-size: 0.64rem;
    letter-spacing: 0.025em;
    text-align: center;
    opacity: 0.72;
    pointer-events: none;
  }

  @media (max-width: 640px) {
    .force-network {
      min-height: 28rem;
      border-radius: 0.5rem;
      background-size: 1.8rem 1.8rem;
    }

    .force-network__label { font-size: 0.74rem; }
    .force-network__description { display: none; }
    .force-network__hint { font-size: 0.58rem; }
  }
</style>
