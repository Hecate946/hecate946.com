<script lang="ts">
  import { onDestroy, onMount } from 'svelte';
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
  import { playNetworkCollisionNote, unlockSiteSound } from '@/lib/site-sound';
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

  type PanState = {
    pointerId: number;
    startX: number;
    startY: number;
    startPanX: number;
    startPanY: number;
  };

  type PinchState = {
    startDistance: number;
    startScale: number;
    graphCenterX: number;
    graphCenterY: number;
  };

  export let nodes: NetworkNode[] = [];
  export let links: NetworkLink[] = [];
  export let centerNodeId = '';
  export let ariaLabel = 'Interactive network graph';
  export let height = 'min(68svh, 44rem)';
  export let idPrefix = 'force-network';
  export let showHint = true;
  export let appearance: 'default' | 'obsidian' = 'default';
  export let collisionSounds = false;
  export let zoomable = false;
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
  let activeCollisionPairs = new Set<string>();
  let collisionSoundsArmed = false;
  let zoomScale = 1;
  let panX = 0;
  let panY = 0;
  let zoomTargetScale = 1;
  let panTargetX = 0;
  let panTargetY = 0;
  let zoomVelocity = 0;
  let zoomAnchorX = 0;
  let zoomAnchorY = 0;
  let viewportAnimationFrame: number | null = null;
  let panState: PanState | null = null;
  let pinchState: PinchState | null = null;
  const viewportPointers = new Map<number, { x: number; y: number }>();

  $: config = { ...defaults, ...settings };
  $: dataSignature = JSON.stringify({
    nodes,
    links,
    centerNodeId,
    settings,
    appearance,
    zoomable,
  });
  $: if (mounted && dataSignature !== lastSignature) {
    lastSignature = dataSignature;
    queueMicrotask(() => rebuildSimulation(true));
  }

  const clamp = (value: number, minimum: number, maximum: number) =>
    Math.min(maximum, Math.max(minimum, value));

  const safeId = (value: string) => value.replace(/[^a-zA-Z0-9_-]/g, '-');

  const nodeById = (id: string) =>
    simulationNodes.find((node) => node.id === id);

  const resolveNode = (value: string | SimulationNode) =>
    typeof value === 'string' ? nodeById(value) : value;

  const nodeAccent = (node: SimulationNode) =>
    appearance === 'obsidian'
      ? 'var(--network-highlight, #135e5f)'
      : node.accent ?? 'var(--accent, #8b7cff)';

  const nodeRadius = (node: NetworkNode) => {
    if (appearance === 'obsidian') {
      if (node.current) return 7;
      if (node.featured) return 6;
      if ((node.radius ?? 0) >= 34) return 5;
      if ((node.radius ?? 0) <= 22) return 3.25;
      return 4;
    }

    return node.radius ?? (node.featured ? 72 : 43);
  };

  const graphScale = () =>
    appearance === 'obsidian'
      ? clamp(Math.min(width, heightPixels) / 620, 0.86, 1.12)
      : clamp(Math.min(width, heightPixels) / 620, 0.72, 1);

  const linkScale = () =>
    clamp(Math.min(width, heightPixels) / 620, 0.72, 1.08);

  function anchorFor(node: NetworkNode, index: number, total: number) {
    if (node.id === centerNodeId) {
      return { x: width / 2, y: heightPixels / 2 };
    }

    if (config.layout === 'radial') {
      const outerNodes = nodes.filter((item) => item.id !== centerNodeId);
      const outerIndex = Math.max(
        0,
        outerNodes.findIndex((item) => item.id === node.id),
      );
      const outerCount = Math.max(1, outerNodes.length);
      const radius = Math.min(width, heightPixels) * config.radialRadius;
      const angle =
        config.radialStartAngle + (outerIndex * Math.PI * 2) / outerCount;

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
      const entranceDistance =
        animateEntrance && !reducedMotion ? config.entranceRadius : 0;

      return {
        ...node,
        baseRadius: nodeRadius(node),
        radius: nodeRadius(node) * graphScale(),
        anchorX: anchor.x,
        anchorY: anchor.y,
        x: entranceDistance
          ? centerX + Math.cos(angle) * entranceDistance
          : anchor.x,
        y: entranceDistance
          ? centerY + Math.sin(angle) * entranceDistance
          : anchor.y,
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

  const collisionPairKey = (firstId: string, secondId: string) =>
    firstId < secondId ? `${firstId}:${secondId}` : `${secondId}:${firstId}`;

  function detectNodeCollisions() {
    if (!collisionSounds) {
      activeCollisionPairs.clear();
      return;
    }

    const nextCollisionPairs = new Set<string>();

    for (let firstIndex = 0; firstIndex < simulationNodes.length; firstIndex += 1) {
      const firstNode = simulationNodes[firstIndex];
      const firstX = firstNode.x ?? firstNode.anchorX;
      const firstY = firstNode.y ?? firstNode.anchorY;

      for (
        let secondIndex = firstIndex + 1;
        secondIndex < simulationNodes.length;
        secondIndex += 1
      ) {
        const secondNode = simulationNodes[secondIndex];
        const secondX = secondNode.x ?? secondNode.anchorX;
        const secondY = secondNode.y ?? secondNode.anchorY;
        const collisionDistance =
          firstNode.radius +
          secondNode.radius +
          config.collisionPadding * 2;
        const distance = Math.hypot(secondX - firstX, secondY - firstY);
        const pairKey = collisionPairKey(firstNode.id, secondNode.id);
        const wasColliding = activeCollisionPairs.has(pairKey);
        const separationTolerance = wasColliding ? 9 : 1.5;

        if (distance > collisionDistance + separationTolerance) continue;

        nextCollisionPairs.add(pairKey);

        if (collisionSounds && collisionSoundsArmed && !wasColliding) {
          void playNetworkCollisionNote();
        }
      }
    }

    activeCollisionPairs = nextCollisionPairs;
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

    // Obsidian's local graph behaves like one free cluster held together by
    // link tension, repulsion, and a very soft pull toward the viewport center.
    // The default/homepage graph keeps its authored per-node anchors.
    const xForce =
      appearance === 'obsidian'
        ? forceX<SimulationNode>(width / 2).strength(config.anchorStrength)
        : forceX<SimulationNode>((node) => node.anchorX).strength((node) =>
            node.id === centerNodeId
              ? config.centerAnchorStrength
              : config.anchorStrength,
          );

    const yForce =
      appearance === 'obsidian'
        ? forceY<SimulationNode>(heightPixels / 2).strength(
            config.anchorStrength,
          )
        : forceY<SimulationNode>((node) => node.anchorY).strength((node) =>
            node.id === centerNodeId
              ? config.centerAnchorStrength
              : config.anchorStrength,
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
        // A zoomable Obsidian-style graph is an unbounded plane. Clamping it to
        // the initial viewport makes clusters bunch up against invisible walls.
        if (!(appearance === 'obsidian' && zoomable)) keepNodesInBounds();
        detectNodeCollisions();
        syncRenderedState();
      });
  }

  function rebuildSimulation(animateEntrance = false) {
    simulation?.stop();
    activeCollisionPairs = new Set();
    collisionSoundsArmed = false;
    createSimulationNodes(animateEntrance);
    simulation = forceSimulation<SimulationNode, SimulationLink>(
      simulationNodes,
    );
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
      const edgePadding = appearance === 'obsidian' ? 18 : 12;
      const xPadding = node.radius + edgePadding;
      const topPadding = node.radius + edgePadding;
      const bottomPadding =
        appearance === 'obsidian'
          ? node.radius + 22
          : node.radius + (node.description ? 58 : 40);

      if (typeof node.x === 'number') {
        node.x = clamp(node.x, xPadding, Math.max(xPadding, width - xPadding));
      }

      if (typeof node.y === 'number') {
        node.y = clamp(
          node.y,
          topPadding,
          Math.max(topPadding, heightPixels - bottomPadding),
        );
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

    if (zoomable && oldWidth > 0 && oldHeight > 0) {
      const widthRatio = width / oldWidth;
      const heightRatio = heightPixels / oldHeight;
      panX *= widthRatio;
      panY *= heightRatio;
      panTargetX *= widthRatio;
      panTargetY *= heightRatio;
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

  function viewportPosition(event: PointerEvent | WheelEvent | MouseEvent) {
    const bounds = svgElement.getBoundingClientRect();
    return {
      x: ((event.clientX - bounds.left) / bounds.width) * width,
      y: ((event.clientY - bounds.top) / bounds.height) * heightPixels,
    };
  }

  function pointerPosition(event: PointerEvent) {
    const point = viewportPosition(event);
    return {
      x: (point.x - panX) / zoomScale,
      y: (point.y - panY) / zoomScale,
    };
  }

  function stopViewportAnimation() {
    if (viewportAnimationFrame !== null) {
      cancelAnimationFrame(viewportAnimationFrame);
      viewportAnimationFrame = null;
    }
    zoomVelocity = 0;
    zoomTargetScale = zoomScale;
    panTargetX = panX;
    panTargetY = panY;
  }

  function setTargetZoom(nextScale: number, anchorX: number, anchorY: number) {
    const graphX = (anchorX - panTargetX) / zoomTargetScale;
    const graphY = (anchorY - panTargetY) / zoomTargetScale;
    zoomTargetScale = nextScale;
    panTargetX = anchorX - graphX * nextScale;
    panTargetY = anchorY - graphY * nextScale;
  }

  function animateViewport() {
    viewportAnimationFrame = null;

    if (Math.abs(zoomVelocity) > 0.00004) {
      const nextScale = clamp(
        zoomTargetScale * Math.exp(zoomVelocity),
        0.42,
        3.4,
      );

      if (nextScale !== zoomTargetScale) {
        setTargetZoom(nextScale, zoomAnchorX, zoomAnchorY);
      } else {
        zoomVelocity = 0;
      }

      zoomVelocity *= 0.865;
    } else {
      zoomVelocity = 0;
    }

    const easing = 0.205;
    zoomScale += (zoomTargetScale - zoomScale) * easing;
    panX += (panTargetX - panX) * easing;
    panY += (panTargetY - panY) * easing;

    const settled =
      zoomVelocity === 0 &&
      Math.abs(zoomTargetScale - zoomScale) < 0.00015 &&
      Math.abs(panTargetX - panX) < 0.035 &&
      Math.abs(panTargetY - panY) < 0.035;

    if (settled) {
      zoomScale = zoomTargetScale;
      panX = panTargetX;
      panY = panTargetY;
      return;
    }

    viewportAnimationFrame = requestAnimationFrame(animateViewport);
  }

  function requestViewportAnimation() {
    if (reducedMotion) {
      zoomVelocity = 0;
      zoomScale = zoomTargetScale;
      panX = panTargetX;
      panY = panTargetY;
      return;
    }

    if (viewportAnimationFrame === null) {
      viewportAnimationFrame = requestAnimationFrame(animateViewport);
    }
  }

  function resetViewport(animate = true) {
    zoomVelocity = 0;
    zoomTargetScale = 1;
    panTargetX = 0;
    panTargetY = 0;

    if (!animate || reducedMotion) {
      stopViewportAnimation();
      zoomScale = 1;
      panX = 0;
      panY = 0;
      zoomTargetScale = 1;
      panTargetX = 0;
      panTargetY = 0;
      return;
    }

    requestViewportAnimation();
  }

  function handleWheel(event: WheelEvent) {
    if (!zoomable) return;
    event.preventDefault();

    const point = viewportPosition(event);
    const normalizedDelta =
      event.deltaMode === WheelEvent.DOM_DELTA_LINE
        ? event.deltaY * 16
        : event.deltaMode === WheelEvent.DOM_DELTA_PAGE
          ? event.deltaY * heightPixels
          : event.deltaY;

    zoomAnchorX = point.x;
    zoomAnchorY = point.y;
    zoomVelocity = clamp(
      zoomVelocity - normalizedDelta * 0.000235,
      -0.082,
      0.082,
    );
    requestViewportAnimation();
  }

  function startPan(event: PointerEvent) {
    if (!zoomable || event.button !== 0) return;
    const target = event.target as Element | null;
    if (target?.closest('.force-network__node')) return;

    stopViewportAnimation();
    const point = viewportPosition(event);
    viewportPointers.set(event.pointerId, point);
    svgElement.setPointerCapture(event.pointerId);

    if (viewportPointers.size === 1) {
      panState = {
        pointerId: event.pointerId,
        startX: point.x,
        startY: point.y,
        startPanX: panX,
        startPanY: panY,
      };
      pinchState = null;
      return;
    }

    if (viewportPointers.size === 2) {
      const [first, second] = Array.from(viewportPointers.values());
      const centerX = (first.x + second.x) / 2;
      const centerY = (first.y + second.y) / 2;
      pinchState = {
        startDistance: Math.max(
          1,
          Math.hypot(second.x - first.x, second.y - first.y),
        ),
        startScale: zoomScale,
        graphCenterX: (centerX - panX) / zoomScale,
        graphCenterY: (centerY - panY) / zoomScale,
      };
      panState = null;
    }
  }

  function movePan(event: PointerEvent) {
    if (!zoomable || !viewportPointers.has(event.pointerId)) return;
    const point = viewportPosition(event);
    viewportPointers.set(event.pointerId, point);

    if (pinchState && viewportPointers.size >= 2) {
      const [first, second] = Array.from(viewportPointers.values());
      const centerX = (first.x + second.x) / 2;
      const centerY = (first.y + second.y) / 2;
      const distance = Math.max(
        1,
        Math.hypot(second.x - first.x, second.y - first.y),
      );
      const nextScale = clamp(
        pinchState.startScale * (distance / pinchState.startDistance),
        0.42,
        3.4,
      );

      panX = centerX - pinchState.graphCenterX * nextScale;
      panY = centerY - pinchState.graphCenterY * nextScale;
      zoomScale = nextScale;
      zoomTargetScale = nextScale;
      panTargetX = panX;
      panTargetY = panY;
      return;
    }

    if (!panState || panState.pointerId !== event.pointerId) return;
    panX = panState.startPanX + point.x - panState.startX;
    panY = panState.startPanY + point.y - panState.startY;
    panTargetX = panX;
    panTargetY = panY;
  }

  function finishPan(event: PointerEvent) {
    if (!viewportPointers.has(event.pointerId)) return;
    viewportPointers.delete(event.pointerId);

    if (svgElement.hasPointerCapture(event.pointerId)) {
      svgElement.releasePointerCapture(event.pointerId);
    }

    pinchState = null;
    const remaining = Array.from(viewportPointers.entries())[0];

    if (remaining) {
      const [pointerId, point] = remaining;
      panState = {
        pointerId,
        startX: point.x,
        startY: point.y,
        startPanX: panX,
        startPanY: panY,
      };
    } else {
      panState = null;
    }
  }

  function handleCanvasDoubleClick(event: MouseEvent) {
    if (!zoomable) return;
    const target = event.target as Element | null;
    if (target?.closest('.force-network__node')) return;
    resetViewport();
  }

  function startDrag(event: PointerEvent, node: SimulationNode) {
    if (event.button !== 0) return;
    collisionSoundsArmed = collisionSounds;
    if (collisionSounds) unlockSiteSound();
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
    if (
      !dragState ||
      dragState.nodeId !== node.id ||
      dragState.pointerId !== event.pointerId
    ) {
      return;
    }

    const distance = Math.hypot(
      event.clientX - dragState.startClientX,
      event.clientY - dragState.startClientY,
    );

    if (distance > 5) dragState.moved = true;

    const point = pointerPosition(event);
    const edgePadding = appearance === 'obsidian' ? 18 : 12;
    const xPadding = node.radius + edgePadding;
    const bottomPadding =
      appearance === 'obsidian'
        ? node.radius + 22
        : node.radius + (node.description ? 58 : 40);
    node.fx = clamp(point.x, xPadding, width - xPadding);
    node.fy = clamp(
      point.y,
      node.radius + edgePadding,
      heightPixels - bottomPadding,
    );
  }

  function finishDrag(event: PointerEvent, node: SimulationNode) {
    if (
      !dragState ||
      dragState.nodeId !== node.id ||
      dragState.pointerId !== event.pointerId
    ) {
      return;
    }

    const moved = dragState.moved;
    dragState = null;

    if (
      (event.currentTarget as SVGAElement).hasPointerCapture(event.pointerId)
    ) {
      (event.currentTarget as SVGAElement).releasePointerCapture(
        event.pointerId,
      );
    }

    node.fx = null;
    node.fy = null;

    if (moved) {
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
    }
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
        (link.originalSource === activeNodeId &&
          link.originalTarget === nodeId) ||
        (link.originalTarget === activeNodeId &&
          link.originalSource === nodeId),
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
    return node.radius + (appearance === 'obsidian' ? 12 : 24);
  }

  function descriptionY(node: SimulationNode) {
    return node.radius + 42;
  }

  function iconSize(node: SimulationNode) {
    return node.featured
      ? Math.min(44, node.radius * 0.72)
      : Math.min(36, node.radius * 0.94);
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
      reducedMotionQuery?.removeEventListener(
        'change',
        handleReducedMotionChange,
      );
    };
  });

  onDestroy(() => {
    mounted = false;
    simulation?.stop();
    if (viewportAnimationFrame !== null) {
      cancelAnimationFrame(viewportAnimationFrame);
      viewportAnimationFrame = null;
    }
    resizeObserver?.disconnect();
    activeCollisionPairs.clear();
    viewportPointers.clear();
    if (suppressTimer) clearTimeout(suppressTimer);
  });
</script>

<div
  class="force-network"
  class:force-network--obsidian={appearance === 'obsidian'}
  class:force-network--zoomable={zoomable}
  class:force-network--panning={panState !== null || pinchState !== null}
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
    on:wheel={handleWheel}
    on:pointerdown={startPan}
    on:pointermove={movePan}
    on:pointerup={finishPan}
    on:pointercancel={finishPan}
    on:dblclick={handleCanvasDoubleClick}
  >
    <defs>
      {#if zoomable}
        <pattern
          id={`${idPrefix}-grid`}
          width="32"
          height="32"
          patternUnits="userSpaceOnUse"
        >
          <path d="M 32 0 L 0 0 0 32" class="force-network__grid-line" />
        </pattern>
      {/if}

      {#each simulationNodes.filter((node) => appearance !== 'obsidian' && node.imageSrc) as node (node.id)}
        <clipPath id={`${idPrefix}-${safeId(node.id)}-clip`}>
          <circle r={Math.max(1, node.radius - 3)} />
        </clipPath>
      {/each}

      {#each (appearance === 'default' ? renderedLinks : []) as link (link.key)}
        <linearGradient
          id={`${idPrefix}-${safeId(link.key)}-gradient`}
          gradientUnits="userSpaceOnUse"
          x1={link.x1}
          y1={link.y1}
          x2={link.x2}
          y2={link.y2}
        >
          <stop
            offset="0%"
            stop-color="var(--network-edge-start)"
            stop-opacity="0.72"
          />
          <stop offset="100%" stop-color={link.accent} stop-opacity="0.88" />
        </linearGradient>
      {/each}
    </defs>

    {#if zoomable}
      <rect
        class="force-network__grid-surface"
        x="0"
        y="0"
        width={width}
        height={heightPixels}
        fill={`url(#${idPrefix}-grid)`}
        aria-hidden="true"
      />
    {/if}

    <g
      class="force-network__viewport"
      transform={`translate(${panX} ${panY}) scale(${zoomScale})`}
    >
    <g class="force-network__links" aria-hidden="true">
      {#each renderedLinks as link (link.key)}
        <path
          d={link.d}
          class:force-network__link--primary={link.kind === 'primary'}
          class:force-network__link--secondary={link.kind === 'secondary'}
          class:force-network__link--active={isLinkActive(link)}
          class:force-network__link--muted={activeNodeId !== null &&
            !isLinkActive(link)}
          class="force-network__link"
          style={appearance === 'obsidian'
            ? `--link-accent: ${link.accent};`
            : `--link-accent: ${link.accent}; stroke: url(#${idPrefix}-${safeId(link.key)}-gradient);`}
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
          class:force-network__node--current={node.current}
          class:force-network__node--active={activeNodeId === node.id}
          class:force-network__node--connected={activeNodeId !== null &&
            isNodeConnected(node.id)}
          class:force-network__node--muted={activeNodeId !== null &&
            !isNodeConnected(node.id)}
          class:force-network__node--dragging={dragState?.nodeId === node.id}
          transform={`translate(${node.x ?? node.anchorX} ${node.y ?? node.anchorY})`}
          style={`--node-accent: ${nodeAccent(node)};`}
          aria-label={node.description
            ? `${node.label}: ${node.description}`
            : node.label}
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
          <title
            >{node.description
              ? `${node.label} — ${node.description}`
              : node.label}</title
          >
          {#if appearance === 'obsidian'}
            <circle
              class="force-network__node-hit-area"
              r={Math.max(14, node.radius + 9)}
            />
          {/if}
          <circle class="force-network__node-surface" r={node.radius} />

          {#if appearance !== 'obsidian' && node.imageSrc}
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
          {:else if appearance !== 'obsidian' && node.icon}
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

          <text class="force-network__label" y={labelY(node)}>{node.label}</text
          >
          {#if appearance !== 'obsidian' && node.description}
            <text
              class="force-network__description"
              class:force-network__description--visible={activeNodeId ===
                node.id}
              y={descriptionY(node)}
            >
              {node.description}
            </text>
          {/if}
        </a>
      {/each}
    </g>
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
    :global(
        html:not([data-theme='light']):not([data-color-scheme='light']):not(
            .light
          )
      )
      .force-network {
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

  .force-network--zoomable .force-network__canvas {
    cursor: grab;
  }

  .force-network--panning .force-network__canvas {
    cursor: grabbing;
  }

  .force-network__grid-surface {
    pointer-events: all;
  }

  .force-network__grid-line {
    fill: none;
    stroke: var(--network-grid);
    stroke-width: 1;
    vector-effect: non-scaling-stroke;
    shape-rendering: crispEdges;
  }

  .force-network__link {
    fill: none;
    stroke-linecap: round;
    vector-effect: non-scaling-stroke;
    transition:
      opacity 140ms ease,
      stroke-width 140ms ease;
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

  .force-network__link--muted {
    opacity: 0.1;
  }

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

  .force-network__node--dragging {
    cursor: grabbing;
  }
  .force-network__node--muted {
    opacity: 0.3;
  }

  .force-network__node-surface {
    fill: var(--network-node-fill);
    stroke: var(--network-node-border);
    stroke-width: 1.5;
    vector-effect: non-scaling-stroke;
    transition:
      fill 140ms ease,
      stroke 140ms ease,
      stroke-width 140ms ease;
  }

  .force-network__node--current .force-network__node-surface {
    fill: color-mix(in srgb, var(--node-accent) 14%, var(--network-node-fill));
    stroke: var(--node-accent);
    stroke-width: 2.6;
  }

  .force-network__node--featured .force-network__node-surface {
    stroke: color-mix(
      in srgb,
      var(--node-accent) 48%,
      var(--network-node-border)
    );
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

  .force-network__node:focus-visible .force-network__node-surface {
    stroke-width: 3;
  }

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

  .force-network__description--visible {
    opacity: 1;
  }

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

  .force-network--obsidian {
    --network-edge-start: #c7ccd1;
    --network-node-dot: #d7dade;
    --network-highlight: #135e5f;
    --network-highlight-ring: #135e5f;
    --network-obsidian-label: #d4d6d9;
    --network-obsidian-label-connected: #747a80;
    --network-obsidian-label-strong: #25292d;
    --network-obsidian-font: system-ui, -apple-system, BlinkMacSystemFont,
      "Segoe UI", Ubuntu, Roboto, "Noto Sans", "Helvetica Neue", Arial,
      sans-serif;

    min-height: 0;
    border: 0;
    border-radius: 0;
    background-color: var(--network-canvas);
    background-image: none;
  }

  :global([data-theme='dark']) .force-network--obsidian,
  :global([data-color-scheme='dark']) .force-network--obsidian,
  :global(.dark) .force-network--obsidian {
    --network-edge-start: #394047;
    --network-node-dot: #b8c0c8;
    --network-highlight: #105354;
    --network-highlight-ring: #7ee8ea;
    --network-obsidian-label: #7d858a;
    --network-obsidian-label-connected: #899196;
    --network-obsidian-label-strong: #f1f4f5;
  }

  :global([data-theme='light']) .force-network--obsidian,
  :global([data-color-scheme='light']) .force-network--obsidian,
  :global(.light) .force-network--obsidian {
    --network-edge-start: #c7ccd1;
    --network-node-dot: #d7dade;
    --network-highlight: #135e5f;
    --network-highlight-ring: #135e5f;
    --network-obsidian-label: #d4d6d9;
    --network-obsidian-label-connected: #747a80;
    --network-obsidian-label-strong: #25292d;
  }

  @media (prefers-color-scheme: dark) {
    :global(
        html:not([data-theme='light']):not([data-color-scheme='light']):not(
            .light
          )
      )
      .force-network--obsidian {
      --network-edge-start: #394047;
      --network-node-dot: #b8c0c8;
      --network-highlight: #105354;
      --network-highlight-ring: #7ee8ea;
      --network-obsidian-label: #7d858a;
      --network-obsidian-label-connected: #899196;
      --network-obsidian-label-strong: #f1f4f5;
    }
  }

  .force-network--obsidian .force-network__link {
    stroke: var(--network-edge-start);
  }

  .force-network--obsidian .force-network__link--primary,
  .force-network--obsidian .force-network__link--secondary {
    stroke-width: 1.08;
    opacity: 0.46;
  }

  .force-network--obsidian .force-network__link--active {
    stroke: var(--network-highlight);
    stroke-width: 1.34;
    opacity: 0.94;
  }

  .force-network--obsidian .force-network__link--muted {
    opacity: 0.13;
  }

  .force-network--obsidian .force-network__node-hit-area {
    fill: transparent;
    stroke: none;
  }

  .force-network--obsidian .force-network__node-surface {
    fill: var(--network-node-dot);
    stroke: none;
    transition:
      fill 135ms ease,
      stroke 135ms ease,
      stroke-width 135ms ease,
      opacity 135ms ease;
  }

  .force-network--obsidian
    .force-network__node:hover
    .force-network__node-surface,
  .force-network--obsidian
    .force-network__node:focus-visible
    .force-network__node-surface,
  .force-network--obsidian
    .force-network__node--active
    .force-network__node-surface,
  .force-network--obsidian
    .force-network__node--dragging
    .force-network__node-surface {
    fill: var(--network-highlight);
    stroke: var(--network-highlight-ring);
    stroke-width: 1.15;
  }

  .force-network--obsidian .force-network__node--muted {
    opacity: 1;
  }

  .force-network--obsidian .force-network__label {
    fill: var(--network-obsidian-label);
    font-family: var(--network-obsidian-font);
    font-size: 0.66rem;
    font-weight: 400;
    letter-spacing: 0;
    stroke: none;
    transform: translateY(0);
    transition:
      fill 135ms ease,
      opacity 135ms ease,
      transform 180ms cubic-bezier(0.2, 0.8, 0.2, 1);
  }

  .force-network--obsidian
    .force-network__node:hover
    .force-network__label,
  .force-network--obsidian
    .force-network__node:focus-visible
    .force-network__label,
  .force-network--obsidian
    .force-network__node--active
    .force-network__label,
  .force-network--obsidian
    .force-network__node--dragging
    .force-network__label {
    fill: var(--network-obsidian-label-strong);
    transform: translateY(2.5px);
  }

  @media (max-width: 640px) {
    .force-network {
      min-height: 28rem;
      border-radius: 0.5rem;
      background-size: 1.8rem 1.8rem;
    }

    .force-network__label {
      font-size: 0.74rem;
    }

    .force-network--obsidian {
      min-height: 0;
      border-radius: 0;
    }

    .force-network--obsidian .force-network__label {
      font-size: 0.54rem;
    }
    .force-network__description {
      display: none;
    }
    .force-network__hint {
      font-size: 0.58rem;
    }
  }
</style>
