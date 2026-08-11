<script lang="ts">
  import { onDestroy, onMount } from 'svelte';
  import {
    forceCollide,
    forceLink,
    forceManyBody,
    forceSimulation,
    forceX,
    forceY,
    type Force,
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
    directed: boolean;
    weight: number;
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
  export let showResetControl = true;
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
    linkCompressionRatio: 0,
    linkCompressionStrength: 0,
    linkCompressionIterations: 1,
    linkStretchRatio: 0,
    linkStretchStrength: 0,
    linkStretchIterations: 1,
    velocityDecay: 0.34,
    alphaDecay: 0.045,
    dragAlphaTarget: 0.24,
    entranceRadius: 36,
  };

  // Fit the settled graph to the full canvas for Reset view, while allowing a
  // substantially wider overview-to-detail range around that fitted state.
  const ABSOLUTE_MIN_ZOOM = 0.08;
  const FIT_ZOOM_FLOOR = 0.48;
  const FIT_ZOOM_CEILING = 2.2;
  const MIN_ZOOM_FACTOR = 0.24;
  const MAX_ZOOM = 12;
  const FIT_PADDING = 56;
  const PAN_EDGE_PADDING = 0;
  const LABEL_GAP = 8;
  const LABEL_VISIBILITY_RATIO = 0.38;
  const LABEL_VISIBILITY_HYSTERESIS = 0.045;

  // Labels live in graph space with their nodes, so one SVG transform moves and
  // scales both together. Font sizes never change during zoom; only visibility
  // is committed after zoom motion settles. This removes the screen-space
  // coordinate rounding and repeated font-size writes that caused text jitter.
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
  let labelsVisible = true;
  let labelZoomOpacity = 1;
  let minimumZoomScale = 1;
  let fitZoomScale = 1;
  let viewportHasBeenFitted = false;
  let viewportWasTouched = false;
  let fitViewportTimer: ReturnType<typeof setTimeout> | null = null;
  let labelVisibilityNeedsCommit = false;
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
  $: labelZoomOpacity =
    appearance === 'obsidian' && zoomable ? (labelsVisible ? 1 : 0) : 1;
  $: if (mounted && dataSignature !== lastSignature) {
    lastSignature = dataSignature;
    queueMicrotask(() => rebuildSimulation(true));
  }

  function clamp(value: number, minimum: number, maximum: number) {
    return Math.min(maximum, Math.max(minimum, value));
  }

  function syncLabelVisibility(scale: number, force = false) {
    if (!(appearance === 'obsidian' && zoomable)) {
      labelsVisible = true;
      return;
    }

    const ratio = scale / Math.max(fitZoomScale, Number.EPSILON);
    if (force) {
      labelsVisible = ratio >= LABEL_VISIBILITY_RATIO;
      return;
    }

    if (
      labelsVisible &&
      ratio < LABEL_VISIBILITY_RATIO - LABEL_VISIBILITY_HYSTERESIS
    ) {
      labelsVisible = false;
    } else if (
      !labelsVisible &&
      ratio > LABEL_VISIBILITY_RATIO + LABEL_VISIBILITY_HYSTERESIS
    ) {
      labelsVisible = true;
    }
  }

  function commitLabelVisibility(scale = zoomScale, force = false) {
    if (!force && !labelVisibilityNeedsCommit) return;
    syncLabelVisibility(scale, force);
    labelVisibilityNeedsCommit = false;
  }

  // Larger graph nodes always receive larger labels. The size is fixed in graph
  // units, so zoom scales the node and its text by the same exact factor.
  function nodeLabelFontSize(node: SimulationNode) {
    return Math.round(clamp(10.5 + node.baseRadius * 1.25, 15, 20));
  }

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

  function linkRestDistance(link: SimulationLink) {
    if (link.distance !== undefined) return link.distance * linkScale();
    if (config.layout === 'radial') {
      return Math.min(width, heightPixels) * config.radialRadius;
    }
    return config.linkDistance * linkScale();
  }

  function createLinkLengthConstraintForce(): Force<
    SimulationNode,
    SimulationLink
  > {
    let nodesById = new Map<string, SimulationNode>();

    const force: Force<SimulationNode, SimulationLink> = () => {
      const minimumRatio = Math.max(
        0,
        Math.min(1, config.linkCompressionRatio),
      );
      const maximumRatio =
        config.linkStretchRatio > 1 ? config.linkStretchRatio : 0;
      const compressionEnabled =
        minimumRatio > 0 && config.linkCompressionStrength > 0;
      const stretchEnabled =
        maximumRatio > 1 && config.linkStretchStrength > 0;
      if (!compressionEnabled && !stretchEnabled) return;

      const iterations = Math.max(
        compressionEnabled
          ? Math.max(1, Math.round(config.linkCompressionIterations))
          : 1,
        stretchEnabled
          ? Math.max(1, Math.round(config.linkStretchIterations))
          : 1,
      );
      // Project out-of-range links directly back into their permitted length
      // band. A velocity-only spring can visibly lag behind a quickly dragged
      // node, which makes the edge feel elastic. Positional projection keeps
      // connected nodes moving together while the ratio band still provides a
      // small, intentional amount of give.
      const compressionStrength = clamp(
        config.linkCompressionStrength,
        0,
        0.98,
      );
      const stretchStrength = clamp(config.linkStretchStrength, 0, 0.98);

      for (let iteration = 0; iteration < iterations; iteration += 1) {
        for (const link of simulationLinks) {
          const source =
            typeof link.source === 'string'
              ? nodesById.get(link.source)
              : link.source;
          const target =
            typeof link.target === 'string'
              ? nodesById.get(link.target)
              : link.target;
          if (!source || !target) continue;

          let deltaX =
            (target.x ?? target.anchorX) + (target.vx ?? 0) -
            ((source.x ?? source.anchorX) + (source.vx ?? 0));
          let deltaY =
            (target.y ?? target.anchorY) + (target.vy ?? 0) -
            ((source.y ?? source.anchorY) + (source.vy ?? 0));
          let distance = Math.hypot(deltaX, deltaY);

          if (distance < 0.0001) {
            const angle = ((link.order + 1) * 2.399963229728653) % (Math.PI * 2);
            deltaX = Math.cos(angle) * 0.0001;
            deltaY = Math.sin(angle) * 0.0001;
            distance = 0.0001;
          }

          const restingDistance = linkRestDistance(link);
          const minimumDistance = restingDistance * minimumRatio;
          const maximumDistance = restingDistance * maximumRatio;
          let correction = 0;

          if (compressionEnabled && distance < minimumDistance) {
            correction =
              (minimumDistance - distance) * compressionStrength;
          } else if (stretchEnabled && distance > maximumDistance) {
            // A negative correction pulls both endpoints back toward each other.
            correction = (maximumDistance - distance) * stretchStrength;
          } else {
            continue;
          }

          const unitX = deltaX / distance;
          const unitY = deltaY / distance;
          const correctionX = unitX * correction;
          const correctionY = unitY * correction;
          const sourceFixed =
            (source.fx !== null && source.fx !== undefined) ||
            (source.fy !== null && source.fy !== undefined);
          const targetFixed =
            (target.fx !== null && target.fx !== undefined) ||
            (target.fy !== null && target.fy !== undefined);

          if (!sourceFixed && !targetFixed) {
            source.x = (source.x ?? source.anchorX) - correctionX * 0.5;
            source.y = (source.y ?? source.anchorY) - correctionY * 0.5;
            target.x = (target.x ?? target.anchorX) + correctionX * 0.5;
            target.y = (target.y ?? target.anchorY) + correctionY * 0.5;
          } else if (sourceFixed && !targetFixed) {
            target.x = (target.x ?? target.anchorX) + correctionX;
            target.y = (target.y ?? target.anchorY) + correctionY;
          } else if (!sourceFixed && targetFixed) {
            source.x = (source.x ?? source.anchorX) - correctionX;
            source.y = (source.y ?? source.anchorY) - correctionY;
          }

          // Remove most of the relative velocity along the edge once it reaches
          // the constraint boundary. Tangential movement remains untouched, so
          // the graph can still flow smoothly instead of behaving like a rigid
          // welded structure.
          const relativeVelocity =
            ((target.vx ?? 0) - (source.vx ?? 0)) * unitX +
            ((target.vy ?? 0) - (source.vy ?? 0)) * unitY;
          const radialDamping = relativeVelocity * 0.72;
          const dampingX = unitX * radialDamping;
          const dampingY = unitY * radialDamping;

          if (!sourceFixed && !targetFixed) {
            source.vx = (source.vx ?? 0) + dampingX * 0.5;
            source.vy = (source.vy ?? 0) + dampingY * 0.5;
            target.vx = (target.vx ?? 0) - dampingX * 0.5;
            target.vy = (target.vy ?? 0) - dampingY * 0.5;
          } else if (sourceFixed && !targetFixed) {
            target.vx = (target.vx ?? 0) - dampingX;
            target.vy = (target.vy ?? 0) - dampingY;
          } else if (!sourceFixed && targetFixed) {
            source.vx = (source.vx ?? 0) + dampingX;
            source.vy = (source.vy ?? 0) + dampingY;
          }
        }
      }
    };

    force.initialize = (nodes) => {
      nodesById = new Map(nodes.map((node) => [node.id, node]));
    };

    return force;
  }

  function configureForces() {
    if (!simulation) return;

    const linkForce = forceLink<SimulationNode, SimulationLink>(simulationLinks)
      .id((node) => node.id)
      .distance(linkRestDistance)
      .strength((link) => link.strength ?? config.linkStrength);

    const linkLengthConstraintForce =
      (config.linkCompressionRatio > 0 && config.linkCompressionStrength > 0) ||
      (config.linkStretchRatio > 1 && config.linkStretchStrength > 0)
        ? createLinkLengthConstraintForce()
        : null;

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
      .force('linkLengthConstraint', linkLengthConstraintForce)
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
      })
      .on('end', () => {
        if (!(appearance === 'obsidian' && zoomable)) return;
        refreshMinimumZoomScale();
        if (!viewportWasTouched) {
          viewportHasBeenFitted = true;
          resetViewport(true);
        }
      });
  }

  function rebuildSimulation(animateEntrance = false) {
    simulation?.stop();
    if (fitViewportTimer) clearTimeout(fitViewportTimer);
    labelVisibilityNeedsCommit = false;
    viewportHasBeenFitted = false;
    viewportWasTouched = false;
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
      if (!(appearance === 'obsidian' && zoomable)) keepNodesInBounds();
      syncRenderedState();
      if (appearance === 'obsidian' && zoomable) resetViewport(false);
      return;
    }

    simulation.alpha(0.7).restart();

    if (appearance === 'obsidian' && zoomable) {
      fitViewportTimer = setTimeout(() => {
        refreshMinimumZoomScale();
        if (!viewportWasTouched && !viewportHasBeenFitted) {
          viewportHasBeenFitted = true;
          resetViewport(false);
        }
      }, 720);
    }
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

    if (zoomable) {
      refreshMinimumZoomScale();
      if (!viewportWasTouched) {
        resetViewport(false);
      } else {
        zoomScale = clamp(zoomScale, minimumZoomScale, MAX_ZOOM);
        zoomTargetScale = clamp(
          zoomTargetScale,
          minimumZoomScale,
          MAX_ZOOM,
        );
        const current = constrainPan(zoomScale, panX, panY);
        const target = constrainPan(
          zoomTargetScale,
          panTargetX,
          panTargetY,
        );
        panX = current.x;
        panY = current.y;
        panTargetX = target.x;
        panTargetY = target.y;
      }
    }

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

  function freezeSimulationForViewport() {
    // Viewport navigation must never alter the graph configuration. Freezing the
    // force simulation at the first zoom or pan input prevents a still-cooling
    // simulation from moving nodes underneath a stationary cursor.
    simulation?.alphaTarget(0);
    simulation?.stop();
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
    commitLabelVisibility();
  }

  function setTargetZoom(
    nextScale: number,
    anchorX: number,
    anchorY: number,
    useCurrentViewport = false,
  ) {
    // A new wheel event is anchored to the transform that is actually visible,
    // not a future target left over from prior inertia. This keeps the exact graph
    // point beneath the cursor fixed for the complete zoom animation.
    const sourceScale = useCurrentViewport ? zoomScale : zoomTargetScale;
    const sourcePanX = useCurrentViewport ? panX : panTargetX;
    const sourcePanY = useCurrentViewport ? panY : panTargetY;
    const graphX = (anchorX - sourcePanX) / sourceScale;
    const graphY = (anchorY - sourcePanY) / sourceScale;

    zoomTargetScale = nextScale;
    panTargetX = anchorX - graphX * nextScale;
    panTargetY = anchorY - graphY * nextScale;
  }

  function animateViewport() {
    viewportAnimationFrame = null;

    if (Math.abs(zoomVelocity) > 0.00004) {
      const nextScale = clamp(
        zoomTargetScale * Math.exp(zoomVelocity),
        minimumZoomScale,
        MAX_ZOOM,
      );

      if (nextScale !== zoomTargetScale) {
        setTargetZoom(nextScale, zoomAnchorX, zoomAnchorY);
      } else {
        zoomVelocity = 0;
      }

      zoomVelocity *= 0.925;
    } else {
      zoomVelocity = 0;
    }

    const easing = 0.105;

    // Scale and translation use the same easing step. Because the target
    // translation was derived from the cursor anchor, this affine interpolation
    // preserves that anchor exactly instead of introducing a drifting recenter.
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
      commitLabelVisibility();
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
      commitLabelVisibility();
      return;
    }

    if (viewportAnimationFrame === null) {
      viewportAnimationFrame = requestAnimationFrame(animateViewport);
    }
  }

  function graphBounds() {
    const positionedNodes = simulationNodes.filter(
      (node) => typeof node.x === 'number' && typeof node.y === 'number',
    );

    if (positionedNodes.length === 0) {
      return {
        minX: 0,
        maxX: width,
        minY: 0,
        maxY: heightPixels,
      };
    }

    return positionedNodes.reduce(
      (result, node) => {
        const x = node.x ?? node.anchorX;
        const y = node.y ?? node.anchorY;
        const radius = node.radius + (appearance === 'obsidian' ? 0 : 10);
        return {
          minX: Math.min(result.minX, x - radius),
          maxX: Math.max(result.maxX, x + radius),
          minY: Math.min(result.minY, y - radius),
          maxY: Math.max(result.maxY, y + radius),
        };
      },
      {
        minX: Number.POSITIVE_INFINITY,
        maxX: Number.NEGATIVE_INFINITY,
        minY: Number.POSITIVE_INFINITY,
        maxY: Number.NEGATIVE_INFINITY,
      },
    );
  }

  function refreshMinimumZoomScale() {
    const bounds = graphBounds();
    const graphWidth = Math.max(1, bounds.maxX - bounds.minX);
    const graphHeight = Math.max(1, bounds.maxY - bounds.minY);
    const availableWidth = Math.max(1, width - FIT_PADDING * 2);
    const availableHeight = Math.max(1, heightPixels - FIT_PADDING * 2);

    fitZoomScale = clamp(
      Math.min(availableWidth / graphWidth, availableHeight / graphHeight),
      FIT_ZOOM_FLOOR,
      FIT_ZOOM_CEILING,
    );
    minimumZoomScale = clamp(
      fitZoomScale * MIN_ZOOM_FACTOR,
      ABSOLUTE_MIN_ZOOM,
      fitZoomScale,
    );
  }

  function graphCenter() {
    const bounds = graphBounds();
    return {
      x: (bounds.minX + bounds.maxX) / 2,
      y: (bounds.minY + bounds.maxY) / 2,
    };
  }

  function constrainPan(scale: number, desiredX: number, desiredY: number) {
    const bounds = graphBounds();

    // Keep the graph inside the live viewport without ever forcing it back to
    // the center. When the graph is smaller than the viewport it may rest
    // anywhere inside it; when larger, the viewport remains covered edge to
    // edge. Zooming around the pointer therefore preserves its visual anchor.
    const leftAlignedX = PAN_EDGE_PADDING - bounds.minX * scale;
    const rightAlignedX =
      width - PAN_EDGE_PADDING - bounds.maxX * scale;
    const topAlignedY = PAN_EDGE_PADDING - bounds.minY * scale;
    const bottomAlignedY =
      heightPixels - PAN_EDGE_PADDING - bounds.maxY * scale;

    return {
      x: clamp(
        desiredX,
        Math.min(leftAlignedX, rightAlignedX),
        Math.max(leftAlignedX, rightAlignedX),
      ),
      y: clamp(
        desiredY,
        Math.min(topAlignedY, bottomAlignedY),
        Math.max(topAlignedY, bottomAlignedY),
      ),
    };
  }

  function resetViewport(animate = true) {
    labelVisibilityNeedsCommit = false;
    refreshMinimumZoomScale();
    const center = graphCenter();
    zoomVelocity = 0;
    zoomTargetScale = fitZoomScale;
    const constrained = constrainPan(
      zoomTargetScale,
      width / 2 - center.x * zoomTargetScale,
      heightPixels / 2 - center.y * zoomTargetScale,
    );
    panTargetX = constrained.x;
    panTargetY = constrained.y;

    if (!animate || reducedMotion) {
      if (viewportAnimationFrame !== null) {
        cancelAnimationFrame(viewportAnimationFrame);
        viewportAnimationFrame = null;
      }
      zoomScale = zoomTargetScale;
      panX = panTargetX;
      panY = panTargetY;
      commitLabelVisibility(zoomScale, true);
      return;
    }

    // Keep label visibility stable throughout the reset animation and commit
    // the fitted visibility once, after the viewport has fully settled.
    labelVisibilityNeedsCommit = true;
    requestViewportAnimation();
  }

  function handleWheel(event: WheelEvent) {
    if (!zoomable) return;
    event.preventDefault();
    viewportWasTouched = true;
    freezeSimulationForViewport();

    const point = viewportPosition(event);
    const normalizedDelta =
      event.deltaMode === WheelEvent.DOM_DELTA_LINE
        ? event.deltaY * 16
        : event.deltaMode === WheelEvent.DOM_DELTA_PAGE
          ? event.deltaY * heightPixels
          : event.deltaY;

    zoomAnchorX = point.x;
    zoomAnchorY = point.y;

    // Each wheel/trackpad event advances the target around the graph point
    // currently under the cursor. Label visibility commits only after motion
    // settles; label geometry itself never changes.
    const nextTargetScale = clamp(
      zoomTargetScale * Math.exp(-normalizedDelta * 0.00112),
      minimumZoomScale,
      MAX_ZOOM,
    );
    setTargetZoom(nextTargetScale, zoomAnchorX, zoomAnchorY, true);
    labelVisibilityNeedsCommit = true;

    // Preserve a restrained inertial tail for the graph itself without
    // continuously recalculating label geometry.
    zoomVelocity = clamp(
      zoomVelocity - normalizedDelta * 0.000035,
      -0.018,
      0.018,
    );
    requestViewportAnimation();
  }

  function startPan(event: PointerEvent) {
    if (!zoomable || event.button !== 0) return;
    const target = event.target as Element | null;
    if (target?.closest('.force-network__node')) return;
    viewportWasTouched = true;
    freezeSimulationForViewport();

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
        minimumZoomScale,
        MAX_ZOOM,
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
    const constrained = constrainPan(
      zoomScale,
      panState.startPanX + point.x - panState.startX,
      panState.startPanY + point.y - panState.startY,
    );
    panX = constrained.x;
    panY = constrained.y;
    panTargetX = panX;
    panTargetY = panY;
  }

  function finishPan(event: PointerEvent) {
    if (!viewportPointers.has(event.pointerId)) return;
    const wasPinching = pinchState !== null;
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
      if (wasPinching) {
        labelVisibilityNeedsCommit = true;
        commitLabelVisibility();
      }
    }
  }

  function handleCanvasDoubleClick(event: MouseEvent) {
    if (!zoomable) return;
    const target = event.target as Element | null;
    if (target?.closest('.force-network__node')) return;
    resetViewport();
  }

  function visibleNodeDragBounds(node: SimulationNode) {
    const safeScale = Math.max(zoomScale, Number.EPSILON);
    const left = -panX / safeScale + node.radius;
    const right = (width - panX) / safeScale - node.radius;
    const top = -panY / safeScale + node.radius;
    const bottom = (heightPixels - panY) / safeScale - node.radius;

    return {
      minX: Math.min(left, right),
      maxX: Math.max(left, right),
      minY: Math.min(top, bottom),
      maxY: Math.max(top, bottom),
    };
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

    if (appearance === 'obsidian' && zoomable) {
      // Drag bounds are derived from the currently visible viewport in graph
      // coordinates. A node can touch each viewport edge exactly, regardless
      // of zoom or pan, but can never be dragged beyond the canvas.
      const bounds = visibleNodeDragBounds(node);
      node.fx = clamp(point.x, bounds.minX, bounds.maxX);
      node.fy = clamp(point.y, bounds.minY, bounds.maxY);
      return;
    }

    const edgePadding = 12;
    const xPadding = node.radius + edgePadding;
    const bottomPadding = node.radius + (node.description ? 58 : 40);
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
      const anchor = event.currentTarget as SVGAElement;
      anchor.dataset.siteSoundSuppressClick = 'true';
      if (suppressTimer) clearTimeout(suppressTimer);
      suppressTimer = setTimeout(() => {
        suppressedClickId = null;
        delete anchor.dataset.siteSoundSuppressClick;
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

    // Ordinary links remain center-to-center because the node surfaces mask the
    // hidden portions. Directed links stop just outside each node so the arrow
    // tip remains visible instead of disappearing underneath the target circle.
    if (link.directed) {
      const unitX = dx / distance;
      const unitY = dy / distance;
      const sourcePadding = source.radius + 3;
      const targetPadding = target.radius + 8;
      const startX = sourceX + unitX * sourcePadding;
      const startY = sourceY + unitY * sourcePadding;
      const endX = targetX - unitX * targetPadding;
      const endY = targetY - unitY * targetPadding;

      if (Math.abs(curve) < 0.1) {
        return `M ${startX} ${startY} L ${endX} ${endY}`;
      }

      const midpointX = (startX + endX) / 2;
      const midpointY = (startY + endY) / 2;
      const normalX = -dy / distance;
      const normalY = dx / distance;
      return `M ${startX} ${startY} Q ${midpointX + normalX * curve} ${midpointY + normalY * curve} ${endX} ${endY}`;
    }

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
          directed: Boolean(link.directed),
          weight: clamp(Number(link.weight ?? 0), 0, 1),
          x1: source?.x ?? source?.anchorX ?? width / 2,
          y1: source?.y ?? source?.anchorY ?? heightPixels / 2,
          x2: target?.x ?? target?.anchorX ?? width / 2,
          y2: target?.y ?? target?.anchorY ?? heightPixels / 2,
        } satisfies RenderedLink;
      })
      .filter((link): link is RenderedLink => link !== null);
  }

  function labelY(node: SimulationNode) {
    return node.radius + (appearance === 'obsidian' ? LABEL_GAP : 24);
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

  export function resetView() {
    resetViewport(true);
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
    if (fitViewportTimer) clearTimeout(fitViewportTimer);
  });
</script>

<div
  class="force-network"
  class:force-network--obsidian={appearance === 'obsidian'}
  class:force-network--zoomable={zoomable}
  class:force-network--panning={panState !== null || pinchState !== null}
  bind:this={containerElement}
  style={`--network-height: ${height}; --network-label-zoom-opacity: ${labelZoomOpacity};`}
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


      {#each (appearance === 'default' ? renderedLinks.filter((link) => link.directed) : []) as link (link.key)}
        <marker
          id={`${idPrefix}-${safeId(link.key)}-arrow`}
          viewBox="0 0 8 8"
          refX="7.2"
          refY="4"
          markerWidth={5.2 + link.weight * 2.2}
          markerHeight={5.2 + link.weight * 2.2}
          markerUnits="userSpaceOnUse"
          orient="auto"
        >
          <path d="M0 0 8 4 0 8Z" fill={link.accent} />
        </marker>
      {/each}
    </defs>

    <g
      class="force-network__viewport"
      transform={`translate(${panX} ${panY}) scale(${zoomScale})`}
    >
    <g class="force-network__links" aria-hidden="true">
      {#each renderedLinks as link (link.key)}
        {#if appearance === 'obsidian'}
          <line
            x1={link.x1}
            y1={link.y1}
            x2={link.x2}
            y2={link.y2}
            class:force-network__link--primary={link.kind === 'primary'}
            class:force-network__link--secondary={link.kind === 'secondary'}
            class:force-network__link--active={isLinkActive(link)}
            class:force-network__link--muted={activeNodeId !== null &&
              !isLinkActive(link)}
            class="force-network__link"
            style={`--link-accent: ${link.accent};`}
          />
        {:else}
          <path
            d={link.d}
            class:force-network__link--primary={link.kind === 'primary'}
            class:force-network__link--secondary={link.kind === 'secondary'}
            class:force-network__link--weighted={link.weight > 0}
            class:force-network__link--directed={link.directed}
            class:force-network__link--active={isLinkActive(link)}
            class:force-network__link--muted={activeNodeId !== null &&
              !isLinkActive(link)}
            class="force-network__link"
            marker-end={link.directed
              ? `url(#${idPrefix}-${safeId(link.key)}-arrow)`
              : undefined}
            style={`--link-accent: ${link.accent}; --link-weight: ${link.weight}; --link-width: ${1.15 + link.weight * 2.65}px; --link-active-width: ${1.9 + link.weight * 3}px; --link-opacity: ${0.42 + link.weight * 0.48}; stroke: url(#${idPrefix}-${safeId(link.key)}-gradient);`}
          />
        {/if}
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

          {#if appearance === 'obsidian'}
            <text
              class="force-network__label force-network__label--graph"
              class:force-network__label--active={activeNodeId === node.id}
              y={labelY(node)}
              dominant-baseline="hanging"
              style={`--node-label-font-size: ${nodeLabelFontSize(node)}px;`}
            >{node.label}</text
            >
          {:else}
            <text class="force-network__label" y={labelY(node)}>{node.label}</text
            >
          {/if}
          {#if appearance !== 'obsidian' && node.description}
            <text
              class="force-network__description"
              class:force-network__description--visible={node.descriptionAlwaysVisible ||
                activeNodeId === node.id}
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

  {#if zoomable && appearance === 'obsidian' && showResetControl}
    <button
      type="button"
      class="force-network__reset-view"
      aria-label="Reset graph view"
      title="Reset view"
      on:click|stopPropagation={() => resetViewport()}
    >
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M8 3H3v5M16 3h5v5M21 16v5h-5M3 16v5h5" />
        <circle cx="12" cy="12" r="2.25" />
      </svg>
      <span class="force-network__visually-hidden">Reset view</span>
    </button>
  {/if}

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
    position: relative;
    z-index: 1;
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

  .force-network__link {
    fill: none;
    stroke-linecap: round;
    vector-effect: non-scaling-stroke;
    shape-rendering: geometricPrecision;
    transition: opacity 140ms ease;
  }

  .force-network__link--primary {
    stroke-width: 2.5;
    opacity: 0.78;
  }


  .force-network__link--weighted {
    stroke-width: var(--link-width, 1.15px);
    opacity: var(--link-opacity, 0.42);
  }

  .force-network__link--weighted.force-network__link--active {
    stroke-width: var(--link-active-width, 1.9px);
    opacity: 1;
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
    --network-canvas: var(--bg);
    --network-edge-start: color-mix(in srgb, var(--text) 34%, transparent);
    --network-edge-primary-opacity: 0.82;
    --network-edge-secondary-opacity: 0.64;
    --network-node-dot: color-mix(in srgb, var(--text) 62%, var(--bg));
    --network-highlight: var(--accent);
    --network-highlight-ring: var(--accent-strong);
    --network-obsidian-label: var(--muted);
    --network-obsidian-label-strong: var(--text);
    --network-obsidian-font: system-ui, -apple-system, BlinkMacSystemFont,
      "Segoe UI", Ubuntu, Roboto, "Noto Sans", "Helvetica Neue", Arial,
      sans-serif;
    --network-motion-duration: 520ms;
    --network-motion-ease: cubic-bezier(0.22, 1, 0.36, 1);

    min-height: 0;
    border: 0;
    border-radius: 0;
    background-color: var(--network-canvas);
    background-image: none;
  }

  .force-network--obsidian .force-network__link {
    stroke: var(--network-edge-start);
    stroke-width: 1.5;
    stroke-linecap: round;
    vector-effect: non-scaling-stroke;
    shape-rendering: geometricPrecision;
    transition:
      opacity var(--network-motion-duration) var(--network-motion-ease),
      stroke var(--network-motion-duration) var(--network-motion-ease);
  }

  .force-network--obsidian .force-network__link--primary {
    opacity: var(--network-edge-primary-opacity);
  }

  .force-network--obsidian .force-network__link--secondary {
    opacity: var(--network-edge-secondary-opacity);
  }

  .force-network--obsidian .force-network__link--active {
    stroke: var(--network-highlight);
    opacity: 0.96;
  }

  .force-network--obsidian .force-network__link--muted {
    opacity: 0.16;
  }

  .force-network--obsidian .force-network__node {
    transition: opacity var(--network-motion-duration) var(--network-motion-ease);
  }

  .force-network--obsidian .force-network__node-hit-area {
    fill: transparent;
    stroke: none;
  }

  .force-network--obsidian .force-network__node-surface {
    fill: var(--network-node-dot);
    stroke: none;
    transition:
      fill var(--network-motion-duration) var(--network-motion-ease),
      stroke var(--network-motion-duration) var(--network-motion-ease),
      stroke-width var(--network-motion-duration) var(--network-motion-ease),
      opacity var(--network-motion-duration) var(--network-motion-ease);
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
    font-size: var(--node-label-font-size, 15px);
    font-synthesis: none;
    font-weight: 400;
    letter-spacing: 0;
    opacity: var(--network-label-zoom-opacity, 1);
    stroke: none;
    paint-order: normal;
    pointer-events: none;
    text-rendering: geometricPrecision;
    transform: translateY(0);
    transform-box: fill-box;
    transform-origin: center top;
    transition:
      fill var(--network-motion-duration) var(--network-motion-ease),
      opacity var(--network-motion-duration) var(--network-motion-ease),
      transform var(--network-motion-duration) var(--network-motion-ease);
  }

  .force-network--obsidian .force-network__label--active {
    fill: var(--network-obsidian-label-strong);
    opacity: 1;
    transform: translateY(4px);
  }

  .force-network__reset-view {
    position: absolute;
    z-index: 2;
    right: 0.8rem;
    bottom: 0.8rem;
    display: grid;
    width: 2rem;
    height: 2rem;
    padding: 0;
    place-items: center;
    color: var(--network-obsidian-label);
    border: 1px solid color-mix(in srgb, var(--network-edge-start) 72%, transparent);
    border-radius: 0.35rem;
    background: color-mix(in srgb, var(--network-canvas) 88%, transparent);
    cursor: pointer;
    opacity: 0.56;
    transition:
      color var(--network-motion-duration) var(--network-motion-ease),
      border-color var(--network-motion-duration) var(--network-motion-ease),
      background-color var(--network-motion-duration) var(--network-motion-ease),
      opacity var(--network-motion-duration) var(--network-motion-ease);
  }

  .force-network__reset-view:hover,
  .force-network__reset-view:focus-visible {
    color: var(--network-obsidian-label-strong);
    border-color: var(--network-edge-start);
    background: var(--network-canvas);
    opacity: 0.94;
  }

  .force-network__reset-view svg {
    width: 1rem;
    height: 1rem;
    fill: none;
    stroke: currentColor;
    stroke-linecap: round;
    stroke-linejoin: round;
    stroke-width: 1.55;
  }

  .force-network__visually-hidden {
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    overflow: hidden;
    clip: rect(0 0 0 0);
    white-space: nowrap;
    border: 0;
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
      font-size: var(--node-label-font-size, 14px);
    }
    .force-network__description {
      display: none;
    }
    .force-network__hint {
      font-size: 0.58rem;
    }
  }
</style>
