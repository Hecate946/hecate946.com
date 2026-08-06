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
  import type { NetworkLink, NetworkNode } from './types';

  type GraphNode = NetworkNode &
    SimulationNodeDatum & {
      radius: number;
      labelSize: number;
      labelPriority: 0 | 1 | 2 | 3;
      degree: number;
      depth: number;
      anchorX: number;
      anchorY: number;
      hover: number;
      hoverTarget: number;
      focus: number;
      focusTarget: number;
      view?: NodeView;
    };

  type GraphLink = Omit<NetworkLink, 'source' | 'target'> &
    SimulationLinkDatum<GraphNode> & {
      source: string | GraphNode;
      target: string | GraphNode;
    };

  type NodeView = {
    container: any;
    base: any;
    highlight: any;
    label: any;
  };

  type ThemeColors = {
    background: string;
    text: string;
    muted: string;
    line: string;
    lineAlpha: number;
    accent: string;
  };

  type Camera = {
    scale: number;
    x: number;
    y: number;
    targetScale: number;
    targetX: number;
    targetY: number;
    zooming: boolean;
    anchorScreenX: number;
    anchorScreenY: number;
    anchorWorldX: number;
    anchorWorldY: number;
  };

  export let nodes: NetworkNode[] = [];
  export let links: NetworkLink[] = [];
  export let ariaLabel = 'Interactive website graph';

  const PIXI_URLS = [
    'https://cdn.jsdelivr.net/npm/pixi.js@8.19.0/dist/pixi.min.mjs',
    'https://cdn.jsdelivr.net/npm/pixi.js@8.19.0/+esm',
  ] as const;
  const MIN_ZOOM = 0.12;
  const MAX_ZOOM = 8;
  const CAMERA_EASE = 12;
  const HOVER_EASE = 1.65;
  const FIT_SIDE_PADDING = 44;
  const FIT_TOP_PADDING = 68;
  const FIT_BOTTOM_PADDING = 38;
  const LABEL_BASE_GAP = 3;
  const LABEL_HOVER_DROP = 12;
  const NODE_COLLISION_GAP = 2;
  const DRAG_ALPHA_TARGET = 0.085;
  const DRAG_LOOKAHEAD_MAX = 34;
  const DRAG_COLLISION_PASSES = 2;

  let hostElement!: HTMLDivElement;
  let ready = false;
  let failed = false;
  let failureMessage = 'The website graph could not start.';
  let hasCompletedInitialFit = false;
  let canvasElement: HTMLCanvasElement | null = null;
  let app: any = null;
  let world: any = null;
  let edgeLayer: any = null;
  let activeEdgeLayer: any = null;
  let nodeLayer: any = null;
  let simulation: Simulation<GraphNode, GraphLink> | null = null;
  let graphNodes: GraphNode[] = [];
  let graphLinks: GraphLink[] = [];
  let adjacency = new Map<string, Set<string>>();
  let resizeObserver: ResizeObserver | null = null;
  let themeObserver: MutationObserver | null = null;
  let destroyed = false;
  let activeNode: GraphNode | null = null;
  let edgeFocusNode: GraphNode | null = null;
  let panPointerId: number | null = null;
  let panLastX = 0;
  let panLastY = 0;
  let draggedNode: GraphNode | null = null;
  let draggedPointerId: number | null = null;
  let dragStartX = 0;
  let dragStartY = 0;
  let dragMoved = false;
  let dragTargetX = 0;
  let dragTargetY = 0;
  let dragProcessedX = 0;
  let dragProcessedY = 0;
  let dragVelocityX = 0;
  let dragVelocityY = 0;
  let dragLastInputTime = 0;
  let pinchState: { distance: number; scale: number; worldX: number; worldY: number } | null = null;
  const touchPointers = new Map<number, { x: number; y: number }>();
  let colors: ThemeColors = {
    background: '#ffffff',
    text: '#202124',
    muted: '#8b9098',
    line: '#59636e',
    lineAlpha: 0.42,
    accent: '#2aaea0',
  };

  const camera: Camera = {
    scale: 1,
    x: 0,
    y: 0,
    targetScale: 1,
    targetX: 0,
    targetY: 0,
    zooming: false,
    anchorScreenX: 0,
    anchorScreenY: 0,
    anchorWorldX: 0,
    anchorWorldY: 0,
  };

  const clamp = (value: number, minimum: number, maximum: number) =>
    Math.min(maximum, Math.max(minimum, value));

  const smoothstep = (minimum: number, maximum: number, value: number) => {
    const normalized = clamp((value - minimum) / (maximum - minimum), 0, 1);
    return normalized * normalized * (3 - 2 * normalized);
  };

  function routeDepth(id: string) {
    return id === '/' ? 0 : id.split('/').filter(Boolean).length;
  }

  function nodeRadius(node: NetworkNode, degree: number, depth: number) {
    if (node.id === '/') return 8.5;
    if ((node.radius ?? 0) >= 34 || degree >= 3) return 6.25;
    if (depth === 1) return 4.35;
    return 3.35;
  }

  function nodeLabelPriority(node: NetworkNode, degree: number, depth: number): 0 | 1 | 2 | 3 {
    if (node.id === '/') return 3;
    if ((node.radius ?? 0) >= 34 || degree >= 3) return 2;
    if (depth === 1) return 1;
    return 0;
  }

  function nodeLabelSize(radius: number, priority: 0 | 1 | 2 | 3) {
    const base = priority === 3 ? 15.5 : priority === 2 ? 13.5 : priority === 1 ? 11.75 : 10.75;
    return Math.round((base + radius * 0.18) * 2) / 2;
  }

  function labelVisibility(node: GraphNode) {
    const screenFontSize = node.labelSize * camera.scale;
    const thresholds =
      node.labelPriority === 3
        ? [4.5, 6.5]
        : node.labelPriority === 2
          ? [7.5, 10]
          : node.labelPriority === 1
            ? [10.5, 13]
            : [12.5, 15.5];
    return smoothstep(thresholds[0], thresholds[1], screenFontSize);
  }

  function readThemeColors(): ThemeColors {
    const styles = getComputedStyle(document.documentElement);
    const read = (name: string, fallback: string) =>
      styles.getPropertyValue(name).trim() || fallback;
    const background = read('--bg', '#ffffff');
    const hex = background.match(/^#([0-9a-f]{6})$/i)?.[1];
    const luminance = hex
      ? (Number.parseInt(hex.slice(0, 2), 16) * 0.2126 +
          Number.parseInt(hex.slice(2, 4), 16) * 0.7152 +
          Number.parseInt(hex.slice(4, 6), 16) * 0.0722) /
        255
      : 1;
    const dark = luminance < 0.48;

    return {
      background,
      text: read('--text', dark ? '#f1f3f4' : '#202124'),
      // Obsidian-like neutral graph colors stay gray; only hover uses the
      // current theme accent.
      muted: dark ? '#a7afb8' : '#737b84',
      line: dark ? '#b8c0c8' : '#46515c',
      lineAlpha: dark ? 0.28 : 0.44,
      accent: read('--accent', '#2aaea0'),
    };
  }

  function resolveNode(value: string | GraphNode) {
    if (typeof value !== 'string') return value;
    return graphNodes.find((node) => node.id === value);
  }

  function makeGraphData() {
    const width = 760;
    const height = 540;

    adjacency = new Map(nodes.map((node) => [node.id, new Set<string>()]));
    for (const link of links) {
      adjacency.get(link.source)?.add(link.target);
      adjacency.get(link.target)?.add(link.source);
    }

    graphNodes = nodes.map((node, index) => {
      const depth = routeDepth(node.id);
      const degree = adjacency.get(node.id)?.size ?? 0;
      const radius = nodeRadius(node, degree, depth);
      const priority = nodeLabelPriority(node, degree, depth);
      const angle = (index / Math.max(1, nodes.length)) * Math.PI * 2;
      const anchorX = node.anchor?.x ?? 0.5 + Math.cos(angle) * 0.28;
      const anchorY = node.anchor?.y ?? 0.5 + Math.sin(angle) * 0.28;
      const worldAnchorX = (anchorX - 0.5) * width;
      const worldAnchorY = (anchorY - 0.5) * height;

      return {
        ...node,
        radius,
        labelSize: nodeLabelSize(radius, priority),
        labelPriority: priority,
        degree,
        depth,
        anchorX: worldAnchorX,
        anchorY: worldAnchorY,
        hover: 0,
        hoverTarget: 0,
        focus: 1,
        focusTarget: 1,
        x: worldAnchorX,
        y: worldAnchorY,
      };
    });

    graphLinks = links.map((link) => ({ ...link }));
  }

  function interactionRadius(node: GraphNode) {
    // Keep Pixi hit areas disjoint as well as the visible circles. This means
    // pointer hover can only belong to one node at a time.
    return Math.max(node.radius + 5, 10);
  }

  function setNodeInteractionLocked(locked: boolean) {
    for (const node of graphNodes) {
      const container = node.view?.container;
      if (!container) continue;
      container.eventMode = locked && node !== draggedNode ? 'none' : 'static';
    }
  }

  function closestPointOnSegment(
    pointX: number,
    pointY: number,
    startX: number,
    startY: number,
    endX: number,
    endY: number,
  ) {
    const segmentX = endX - startX;
    const segmentY = endY - startY;
    const lengthSquared = segmentX * segmentX + segmentY * segmentY;
    if (lengthSquared < 0.000001) return { x: endX, y: endY };
    const amount = clamp(
      ((pointX - startX) * segmentX + (pointY - startY) * segmentY) / lengthSquared,
      0,
      1,
    );
    return {
      x: startX + segmentX * amount,
      y: startY + segmentY * amount,
    };
  }

  function removeInwardVelocity(node: GraphNode, outwardX: number, outwardY: number) {
    const velocityX = node.vx ?? 0;
    const velocityY = node.vy ?? 0;
    const inwardAmount = velocityX * outwardX + velocityY * outwardY;
    if (inwardAmount >= 0) return;
    node.vx = velocityX - outwardX * inwardAmount;
    node.vy = velocityY - outwardY * inwardAmount;
  }

  function resolveCircularOverlaps(fixedNode: GraphNode | null, passes = 1) {
    for (let pass = 0; pass < passes; pass += 1) {
      let moved = false;

      for (let index = 0; index < graphNodes.length; index += 1) {
        const first = graphNodes[index];
        for (let nextIndex = index + 1; nextIndex < graphNodes.length; nextIndex += 1) {
          const second = graphNodes[nextIndex];
          const firstX = first === fixedNode ? (first.fx ?? first.x ?? 0) : (first.x ?? 0);
          const firstY = first === fixedNode ? (first.fy ?? first.y ?? 0) : (first.y ?? 0);
          const secondX = second === fixedNode ? (second.fx ?? second.x ?? 0) : (second.x ?? 0);
          const secondY = second === fixedNode ? (second.fy ?? second.y ?? 0) : (second.y ?? 0);
          let deltaX = secondX - firstX;
          let deltaY = secondY - firstY;
          let distance = Math.hypot(deltaX, deltaY);
          const minimumDistance =
            interactionRadius(first) + interactionRadius(second) + NODE_COLLISION_GAP;

          if (distance >= minimumDistance) continue;
          if (distance < 0.001) {
            const angle = (index * 31 + nextIndex * 17 + 1) * 2.399963229728653;
            deltaX = Math.cos(angle);
            deltaY = Math.sin(angle);
            distance = 1;
          }

          const normalX = deltaX / distance;
          const normalY = deltaY / distance;
          const overlap = minimumDistance - distance;
          const firstFixed = first === fixedNode;
          const secondFixed = second === fixedNode;

          if (firstFixed && !secondFixed) {
            second.x = secondX + normalX * overlap;
            second.y = secondY + normalY * overlap;
            removeInwardVelocity(second, normalX, normalY);
          } else if (!firstFixed && secondFixed) {
            first.x = firstX - normalX * overlap;
            first.y = firstY - normalY * overlap;
            removeInwardVelocity(first, -normalX, -normalY);
          } else {
            const half = overlap / 2;
            first.x = firstX - normalX * half;
            first.y = firstY - normalY * half;
            second.x = secondX + normalX * half;
            second.y = secondY + normalY * half;
            removeInwardVelocity(first, -normalX, -normalY);
            removeInwardVelocity(second, normalX, normalY);
          }

          moved = true;
        }
      }

      if (!moved) break;
    }
  }

  function pushNodesOutOfDragPath(node: GraphNode, startX: number, startY: number, endX: number, endY: number) {
    const speed = Math.hypot(dragVelocityX, dragVelocityY);
    const movementX = endX - startX;
    const movementY = endY - startY;
    const movementDistance = Math.hypot(movementX, movementY);
    const directionX = movementDistance > 0.001 ? movementX / movementDistance : 0;
    const directionY = movementDistance > 0.001 ? movementY / movementDistance : 0;
    const lookahead = clamp(speed * 0.018, 0, DRAG_LOOKAHEAD_MAX);
    const pathEndX = endX + directionX * lookahead;
    const pathEndY = endY + directionY * lookahead;
    const dynamicGap = clamp(speed * 0.0035, 0, 7);

    for (const other of graphNodes) {
      if (other === node) continue;
      const otherX = other.x ?? 0;
      const otherY = other.y ?? 0;
      const closest = closestPointOnSegment(
        otherX,
        otherY,
        startX,
        startY,
        pathEndX,
        pathEndY,
      );
      let deltaX = otherX - closest.x;
      let deltaY = otherY - closest.y;
      let distance = Math.hypot(deltaX, deltaY);
      const minimumDistance =
        interactionRadius(node) + interactionRadius(other) + NODE_COLLISION_GAP + dynamicGap;

      if (distance >= minimumDistance) continue;
      if (distance < 0.001) {
        // Choose a stable side of the drag path when the centers are exactly aligned.
        deltaX = -directionY || 1;
        deltaY = directionX;
        distance = Math.hypot(deltaX, deltaY);
      }

      const normalX = deltaX / distance;
      const normalY = deltaY / distance;
      const overlap = minimumDistance - distance;
      const displacement = overlap * (speed > 320 ? 1 : 0.82);
      other.x = otherX + normalX * displacement;
      other.y = otherY + normalY * displacement;

      // A short-lived local impulse creates the Obsidian-like "move out of the way"
      // response without increasing resting charge or making the graph stiffer.
      const impulse = Math.min(5.5, 0.45 + speed * 0.0035 + overlap * 0.055);
      other.vx = (other.vx ?? 0) + normalX * impulse + directionX * Math.min(1.4, speed * 0.0012);
      other.vy = (other.vy ?? 0) + normalY * impulse + directionY * Math.min(1.4, speed * 0.0012);
    }
  }

  function updateDraggedNode(deltaSeconds: number) {
    const node = draggedNode;
    if (!node) return;

    const startX = dragProcessedX;
    const startY = dragProcessedY;
    const endX = dragTargetX;
    const endY = dragTargetY;

    pushNodesOutOfDragPath(node, startX, startY, endX, endY);
    node.fx = endX;
    node.fy = endY;
    node.x = endX;
    node.y = endY;
    node.vx = 0;
    node.vy = 0;
    dragProcessedX = endX;
    dragProcessedY = endY;

    // One frame-based circular projection prevents tunneling at any pointer speed.
    // It runs only while dragging and never moves the pointer-controlled node.
    resolveCircularOverlaps(node, DRAG_COLLISION_PASSES);

    // Velocity is only a short-lived predictor. It fades rapidly when the pointer
    // pauses so the resting graph never inherits extra repulsion.
    const velocityDecay = Math.exp(-15 * deltaSeconds);
    dragVelocityX *= velocityDecay;
    dragVelocityY *= velocityDecay;
  }

  function createLabelCollisionForce() {
    let forceNodes: GraphNode[] = [];

    const force: any = (alpha: number) => {
      for (let iteration = 0; iteration < 2; iteration += 1) {
        for (let index = 0; index < forceNodes.length; index += 1) {
          const first = forceNodes[index];
          const firstX = first.x ?? 0;
          const firstY = first.y ?? 0;
          const firstHalfWidth = Math.max(
            first.radius + 5,
            first.label.length * first.labelSize * (first.labelPriority >= 2 ? 0.27 : 0.235) + 5,
          );
          const firstTop = -first.radius - 3;
          const firstBottom = first.radius + 9 + first.labelSize * 1.18;
          const firstHalfHeight = (firstBottom - firstTop) / 2;
          const firstCenterY = firstY + (firstTop + firstBottom) / 2;

          for (let nextIndex = index + 1; nextIndex < forceNodes.length; nextIndex += 1) {
            const second = forceNodes[nextIndex];
            const secondX = second.x ?? 0;
            const secondY = second.y ?? 0;
            const secondHalfWidth = Math.max(
              second.radius + 5,
              second.label.length * second.labelSize * (second.labelPriority >= 2 ? 0.27 : 0.235) + 5,
            );
            const secondTop = -second.radius - 3;
            const secondBottom = second.radius + 9 + second.labelSize * 1.18;
            const secondHalfHeight = (secondBottom - secondTop) / 2;
            const secondCenterY = secondY + (secondTop + secondBottom) / 2;

            const deltaX = secondX - firstX;
            const deltaY = secondCenterY - firstCenterY;
            const overlapX = firstHalfWidth + secondHalfWidth - Math.abs(deltaX);
            const overlapY = firstHalfHeight + secondHalfHeight - Math.abs(deltaY);
            if (overlapX <= 0 || overlapY <= 0) continue;

            if (overlapX < overlapY) {
              const direction = deltaX === 0
                ? (index + nextIndex) % 2 === 0
                  ? 1
                  : -1
                : Math.sign(deltaX);
              const push = overlapX * 0.22 * alpha;
              first.vx = (first.vx ?? 0) - direction * push;
              second.vx = (second.vx ?? 0) + direction * push;
            } else {
              const direction = deltaY === 0
                ? (index + nextIndex) % 2 === 0
                  ? 1
                  : -1
                : Math.sign(deltaY);
              const push = overlapY * 0.3 * alpha;
              first.vy = (first.vy ?? 0) - direction * push;
              second.vy = (second.vy ?? 0) + direction * push;
            }
          }
        }
      }
    };

    force.initialize = (nextNodes: GraphNode[]) => {
      forceNodes = nextNodes;
    };

    return force;
  }

  function buildSimulation() {
    simulation = forceSimulation<GraphNode, GraphLink>(graphNodes)
      .force(
        'link',
        forceLink<GraphNode, GraphLink>(graphLinks)
          .id((node) => node.id)
          .distance((link) => link.kind === 'secondary' ? 96 : 132)
          .strength((link) => link.kind === 'secondary' ? 0.2 : 0.145),
      )
      .force(
        'charge',
        forceManyBody<GraphNode>()
          .strength((node) => node.id === '/' ? -245 : node.degree >= 3 ? -175 : -112)
          .distanceMin(14)
          .theta(0.86),
      )
      .force('labelCollision', createLabelCollisionForce())
      .force(
        'x',
        forceX<GraphNode>((node) => node.anchorX).strength((node) => node.depth > 1 ? 0.052 : 0.024),
      )
      .force(
        'y',
        forceY<GraphNode>((node) => node.anchorY).strength((node) => node.depth > 1 ? 0.052 : 0.024),
      )
      .force(
        'collision',
        forceCollide<GraphNode>()
          .radius((node) => interactionRadius(node) + NODE_COLLISION_GAP / 2)
          .strength(1)
          .iterations(4),
      )
      .velocityDecay(0.34)
      .alphaDecay(0.023);
  }

  function createNodeView(node: GraphNode, PIXI: any) {
    const container = new PIXI.Container();
    container.position.set(node.x ?? 0, node.y ?? 0);
    container.eventMode = 'static';
    container.cursor = node.href ? 'pointer' : 'grab';
    container.hitArea = new PIXI.Circle(0, 0, interactionRadius(node));

    const base = new PIXI.Graphics()
      .circle(0, 0, node.radius)
      .fill({ color: colors.muted });

    const highlight = new PIXI.Graphics()
      .circle(0, 0, node.radius)
      .fill({ color: colors.accent });
    highlight.alpha = 0;

    const label = new PIXI.Text({
      text: node.label,
      style: {
        fontFamily: 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Ubuntu, Roboto, "Noto Sans", sans-serif',
        fontSize: node.labelSize,
        fontWeight: '400',
        fill: colors.text,
        align: 'center',
      },
      resolution: Math.min((window.devicePixelRatio || 1) * 3, 6),
    });
    label.anchor.set(0.5, 0);
    label.roundPixels = false;
    label.position.set(0, node.radius + LABEL_BASE_GAP);

    container.addChild(base, highlight, label);
    nodeLayer.addChild(container);
    node.view = { container, base, highlight, label };

    container.on('pointerover', () => {
      if (draggedNode) {
        setActiveNode(draggedNode);
        return;
      }
      setActiveNode(node);
    });
    container.on('pointerout', () => {
      if (!draggedNode) setActiveNode(null);
    });
    container.on('pointerdown', (event: any) => beginNodeDrag(node, event));
  }

  function rebuildNodeColors() {
    for (const node of graphNodes) {
      const view = node.view;
      if (!view) continue;
      view.base.clear().circle(0, 0, node.radius).fill({ color: colors.muted });
      view.highlight.clear().circle(0, 0, node.radius).fill({ color: colors.accent });
      view.label.style.fill = colors.text;
    }
  }

  function setActiveNode(node: GraphNode | null) {
    activeNode = node;
    edgeFocusNode = node;
    const neighbors = node ? adjacency.get(node.id) : null;

    for (const item of graphNodes) {
      item.hoverTarget = item === node ? 1 : 0;
      item.focusTarget = !node || item === node || Boolean(neighbors?.has(item.id)) ? 1 : 0.24;
    }
  }

  function updateCameraTransform() {
    if (!world) return;
    world.scale.set(camera.scale);
    world.position.set(camera.x, camera.y);
  }

  function screenToWorld(screenX: number, screenY: number) {
    return {
      x: (screenX - camera.x) / camera.scale,
      y: (screenY - camera.y) / camera.scale,
    };
  }

  function clientToCanvas(clientX: number, clientY: number) {
    const rect = canvasElement?.getBoundingClientRect();
    if (!rect) return { x: clientX, y: clientY };
    return { x: clientX - rect.left, y: clientY - rect.top };
  }

  function coolLayoutForNavigation() {
    simulation?.alphaTarget(0);
  }

  function handleWheel(event: WheelEvent) {
    if (!canvasElement) return;
    event.preventDefault();
    coolLayoutForNavigation();

    const pointer = clientToCanvas(event.clientX, event.clientY);
    const worldPoint = screenToWorld(pointer.x, pointer.y);
    const delta = event.deltaMode === 1 ? event.deltaY * 16 : event.deltaY;
    const factor = Math.exp(-delta * 0.00135);

    camera.anchorScreenX = pointer.x;
    camera.anchorScreenY = pointer.y;
    camera.anchorWorldX = worldPoint.x;
    camera.anchorWorldY = worldPoint.y;
    camera.targetScale = clamp(camera.targetScale * factor, MIN_ZOOM, MAX_ZOOM);
    camera.zooming = true;
  }

  function touchDistance() {
    const points = Array.from(touchPointers.values());
    if (points.length < 2) return 0;
    return Math.hypot(points[1].x - points[0].x, points[1].y - points[0].y);
  }

  function touchCenter() {
    const points = Array.from(touchPointers.values());
    return {
      x: (points[0].x + points[1].x) / 2,
      y: (points[0].y + points[1].y) / 2,
    };
  }

  function handleTouchPointerDown(event: PointerEvent) {
    if (event.pointerType !== 'touch') return;
    const point = clientToCanvas(event.clientX, event.clientY);
    touchPointers.set(event.pointerId, point);
    if (touchPointers.size === 2) {
      coolLayoutForNavigation();
      panPointerId = null;
      const center = touchCenter();
      const worldPoint = screenToWorld(center.x, center.y);
      pinchState = {
        distance: Math.max(1, touchDistance()),
        scale: camera.scale,
        worldX: worldPoint.x,
        worldY: worldPoint.y,
      };
    }
  }

  function handleTouchPointerMove(event: PointerEvent) {
    if (event.pointerType !== 'touch' || !touchPointers.has(event.pointerId)) return;
    touchPointers.set(event.pointerId, clientToCanvas(event.clientX, event.clientY));
    if (!pinchState || touchPointers.size < 2) return;
    event.preventDefault();
    const center = touchCenter();
    const scale = clamp(
      pinchState.scale * (touchDistance() / pinchState.distance),
      MIN_ZOOM,
      MAX_ZOOM,
    );
    camera.zooming = false;
    camera.scale = scale;
    camera.targetScale = scale;
    camera.x = center.x - pinchState.worldX * scale;
    camera.y = center.y - pinchState.worldY * scale;
    camera.targetX = camera.x;
    camera.targetY = camera.y;
    updateCameraTransform();
  }

  function handleTouchPointerUp(event: PointerEvent) {
    if (event.pointerType !== 'touch') return;
    touchPointers.delete(event.pointerId);
    if (touchPointers.size < 2) pinchState = null;
  }

  function beginPan(event: any) {
    if (event.target !== app.stage || draggedNode || touchPointers.size > 1) return;
    coolLayoutForNavigation();
    panPointerId = event.pointerId;
    panLastX = event.global.x;
    panLastY = event.global.y;
    camera.zooming = false;
    camera.targetScale = camera.scale;
    camera.targetX = camera.x;
    camera.targetY = camera.y;
    canvasElement?.setPointerCapture?.(event.pointerId);
  }

  function continuePan(event: any) {
    if (panPointerId !== event.pointerId || draggedNode) return;
    const nextX = event.global.x;
    const nextY = event.global.y;
    camera.x += nextX - panLastX;
    camera.y += nextY - panLastY;
    camera.targetX = camera.x;
    camera.targetY = camera.y;
    panLastX = nextX;
    panLastY = nextY;
    updateCameraTransform();
  }

  function finishPan(event: any) {
    if (panPointerId !== event.pointerId) return;
    panPointerId = null;
    canvasElement?.releasePointerCapture?.(event.pointerId);
  }

  function addWindowDragListeners() {
    if (typeof window === 'undefined') return;
    window.addEventListener('pointermove', handleNodeDrag, { passive: false });
    window.addEventListener('pointerup', finishNodeDrag, { passive: false });
    window.addEventListener('pointercancel', finishNodeDrag, { passive: false });
  }

  function removeWindowDragListeners() {
    if (typeof window === 'undefined') return;
    window.removeEventListener('pointermove', handleNodeDrag);
    window.removeEventListener('pointerup', finishNodeDrag);
    window.removeEventListener('pointercancel', finishNodeDrag);
  }

  function beginNodeDrag(node: GraphNode, event: any) {
    event.stopPropagation();
    setActiveNode(node);
    draggedNode = node;
    draggedPointerId = event.pointerId;
    dragStartX = event.global.x;
    dragStartY = event.global.y;
    dragMoved = false;
    dragTargetX = node.x ?? 0;
    dragTargetY = node.y ?? 0;
    dragProcessedX = dragTargetX;
    dragProcessedY = dragTargetY;
    dragVelocityX = 0;
    dragVelocityY = 0;
    dragLastInputTime = performance.now();
    node.fx = dragTargetX;
    node.fy = dragTargetY;
    setNodeInteractionLocked(true);
    simulation?.alpha(Math.max(simulation.alpha(), 0.24)).alphaTarget(DRAG_ALPHA_TARGET).restart();
    addWindowDragListeners();
  }

  function handleNodeDrag(event: PointerEvent) {
    if (!draggedNode || draggedPointerId !== event.pointerId || !app) return;
    event.preventDefault();

    const samples = typeof event.getCoalescedEvents === 'function'
      ? event.getCoalescedEvents()
      : [event];
    const sample = samples.length ? samples[samples.length - 1] : event;
    const pointer = clientToCanvas(sample.clientX, sample.clientY);
    const worldPoint = screenToWorld(pointer.x, pointer.y);
    const radius = draggedNode.radius;
    const minX = (0 - camera.x) / camera.scale + radius;
    const maxX = (app.screen.width - camera.x) / camera.scale - radius;
    const minY = (0 - camera.y) / camera.scale + radius;
    const maxY = (app.screen.height - camera.y) / camera.scale - radius;
    const nextX = clamp(worldPoint.x, Math.min(minX, maxX), Math.max(minX, maxX));
    const nextY = clamp(worldPoint.y, Math.min(minY, maxY), Math.max(minY, maxY));
    const now = performance.now();
    const elapsed = clamp((now - dragLastInputTime) / 1000, 1 / 240, 0.08);
    const instantaneousX = (nextX - dragTargetX) / elapsed;
    const instantaneousY = (nextY - dragTargetY) / elapsed;
    const velocityBlend = 0.72;
    dragVelocityX += (instantaneousX - dragVelocityX) * velocityBlend;
    dragVelocityY += (instantaneousY - dragVelocityY) * velocityBlend;
    dragTargetX = nextX;
    dragTargetY = nextY;
    dragLastInputTime = now;
    dragMoved ||= Math.hypot(pointer.x - dragStartX, pointer.y - dragStartY) > 4;
  }

  function finishNodeDrag(event: PointerEvent) {
    if (!draggedNode || draggedPointerId !== event.pointerId) return;
    const node = draggedNode;
    const shouldNavigate = !dragMoved && Boolean(node.href);

    updateDraggedNode(1 / 60);
    node.x = dragTargetX;
    node.y = dragTargetY;
    node.fx = null;
    node.fy = null;
    simulation?.alphaTarget(0);
    draggedNode = null;
    draggedPointerId = null;
    setNodeInteractionLocked(false);
    removeWindowDragListeners();

    if (shouldNavigate && node.href && typeof window !== 'undefined') {
      if (node.external) window.open(node.href, '_blank', 'noopener,noreferrer');
      else window.location.assign(node.href);
    }
  }

  function graphBounds() {
    if (!graphNodes.length) return { minX: -1, minY: -1, maxX: 1, maxY: 1 };
    return graphNodes.reduce(
      (bounds, node) => {
        const x = node.x ?? 0;
        const y = node.y ?? 0;
        const labelWidth = node.labelPriority >= 2
          ? Math.max(0, node.label.length * node.labelSize * 0.27)
          : 0;
        bounds.minX = Math.min(bounds.minX, x - Math.max(node.radius, labelWidth));
        bounds.maxX = Math.max(bounds.maxX, x + Math.max(node.radius, labelWidth));
        bounds.minY = Math.min(bounds.minY, y - node.radius);
        bounds.maxY = Math.max(bounds.maxY, y + node.radius + node.labelSize + 8);
        return bounds;
      },
      { minX: Infinity, minY: Infinity, maxX: -Infinity, maxY: -Infinity },
    );
  }

  function centerGraph(immediate = false) {
    if (!app || !world) return;
    const bounds = graphBounds();
    const graphWidth = Math.max(1, bounds.maxX - bounds.minX);
    const graphHeight = Math.max(1, bounds.maxY - bounds.minY);
    const scale = clamp(
      Math.min(
        (app.screen.width - FIT_SIDE_PADDING * 2) / graphWidth,
        (app.screen.height - FIT_TOP_PADDING - FIT_BOTTOM_PADDING) / graphHeight,
      ),
      MIN_ZOOM,
      2.1,
    );
    const centerX = (bounds.minX + bounds.maxX) / 2;

    camera.zooming = false;
    camera.targetScale = scale;
    camera.targetX = app.screen.width / 2 - centerX * scale;
    camera.targetY = FIT_TOP_PADDING - bounds.minY * scale;

    if (immediate) {
      camera.scale = camera.targetScale;
      camera.x = camera.targetX;
      camera.y = camera.targetY;
      updateCameraTransform();
    }
  }

  export function resetView() {
    coolLayoutForNavigation();
    centerGraph(false);
  }

  function redrawEdges() {
    if (!edgeLayer || !activeEdgeLayer) return;
    edgeLayer.clear();
    activeEdgeLayer.clear();
    const lineWidth = 1.08 / Math.max(camera.scale, Number.EPSILON);
    const edgeProgress = edgeFocusNode ? clamp(edgeFocusNode.hover, 0, 1) : 0;

    for (const link of graphLinks) {
      const source = resolveNode(link.source);
      const target = resolveNode(link.target);
      if (!source || !target) continue;
      const connected = Boolean(
        edgeFocusNode && (source.id === edgeFocusNode.id || target.id === edgeFocusNode.id),
      );
      const focusedAlpha = connected ? colors.lineAlpha * 0.72 : colors.lineAlpha * 0.16;
      const baseAlpha = edgeFocusNode
        ? colors.lineAlpha + (focusedAlpha - colors.lineAlpha) * edgeProgress
        : colors.lineAlpha;

      edgeLayer
        .moveTo(source.x ?? 0, source.y ?? 0)
        .lineTo(target.x ?? 0, target.y ?? 0)
        .stroke({ color: colors.line, width: lineWidth, alpha: baseAlpha });

      if (connected && edgeFocusNode && edgeProgress > 0.001) {
        activeEdgeLayer
          .moveTo(source.x ?? 0, source.y ?? 0)
          .lineTo(target.x ?? 0, target.y ?? 0)
          .stroke({
            color: colors.accent,
            width: lineWidth,
            alpha: 0.95 * edgeProgress,
          });
      }
    }
  }

  function updateNodeViews(deltaSeconds: number) {
    const transition = 1 - Math.exp(-HOVER_EASE * deltaSeconds);
    const activeNeighbors = activeNode ? adjacency.get(activeNode.id) : null;

    for (const node of graphNodes) {
      const view = node.view;
      if (!view) continue;
      node.hover += (node.hoverTarget - node.hover) * transition;
      node.focus += (node.focusTarget - node.focus) * transition;
      view.container.position.set(node.x ?? 0, node.y ?? 0);
      view.base.alpha = node.focus;
      view.highlight.alpha = node.hover;
      view.label.y = node.radius + LABEL_BASE_GAP + node.hover * LABEL_HOVER_DROP;

      const isNeighbor = Boolean(activeNeighbors?.has(node.id));
      const baseVisibility = labelVisibility(node);
      const contextualVisibility = node === activeNode ? 1 : isNeighbor ? 0.92 : baseVisibility;
      const dimmedVisibility = activeNode && node !== activeNode && !isNeighbor
        ? contextualVisibility * 0.16
        : contextualVisibility;
      view.label.alpha += (Math.max(dimmedVisibility, node.hover) - view.label.alpha) * transition;
    }

  }

  function updateCamera(deltaSeconds: number) {
    const transition = 1 - Math.exp(-CAMERA_EASE * deltaSeconds);

    if (camera.zooming) {
      camera.scale += (camera.targetScale - camera.scale) * transition;
      // Recompute the camera origin from the same world point every frame. This
      // keeps the exact graph location under the cursor throughout the easing.
      camera.x = camera.anchorScreenX - camera.anchorWorldX * camera.scale;
      camera.y = camera.anchorScreenY - camera.anchorWorldY * camera.scale;

      if (Math.abs(camera.targetScale - camera.scale) < 0.0003) {
        camera.scale = camera.targetScale;
        camera.x = camera.anchorScreenX - camera.anchorWorldX * camera.scale;
        camera.y = camera.anchorScreenY - camera.anchorWorldY * camera.scale;
        camera.targetX = camera.x;
        camera.targetY = camera.y;
        camera.zooming = false;
      }
    } else if (panPointerId === null) {
      camera.scale += (camera.targetScale - camera.scale) * transition;
      camera.x += (camera.targetX - camera.x) * transition;
      camera.y += (camera.targetY - camera.y) * transition;
    }

    updateCameraTransform();
  }

  function updateFrame(ticker: any) {
    const deltaSeconds = Math.min(0.05, ticker.deltaMS / 1000);
    updateCamera(deltaSeconds);
    updateDraggedNode(deltaSeconds);
    updateNodeViews(deltaSeconds);
    redrawEdges();
  }

  function hostSize() {
    const rect = hostElement.getBoundingClientRect();
    return {
      width: Math.max(1, Math.round(rect.width)),
      height: Math.max(1, Math.round(rect.height)),
    };
  }

  async function waitForHostSize() {
    for (let frame = 0; frame < 12; frame += 1) {
      const size = hostSize();
      if (size.width > 1 && size.height > 1) return size;
      await new Promise<void>((resolve) => requestAnimationFrame(() => resolve()));
    }
    return hostSize();
  }

  async function loadPixi() {
    let lastError: unknown = null;

    for (const url of PIXI_URLS) {
      try {
        return (await import(/* @vite-ignore */ url)) as any;
      } catch (error) {
        lastError = error;
      }
    }

    throw lastError instanceof Error
      ? lastError
      : new Error('PixiJS could not be loaded.');
  }

  function handleResize(PIXI: any, initial = false) {
    if (!app || destroyed) return;
    const { width, height } = hostSize();
    app.renderer.resize(width, height);
    app.stage.hitArea = new PIXI.Rectangle(0, 0, width, height);

    if (initial || !hasCompletedInitialFit) {
      centerGraph(true);
      hasCompletedInitialFit = true;
    }
  }

  async function initialize() {
    failed = false;
    ready = false;
    const { width, height } = await waitForHostSize();
    const PIXI = await loadPixi();
    if (destroyed) return;

    colors = readThemeColors();
    makeGraphData();

    app = new PIXI.Application();
    await app.init({
      width,
      height,
      antialias: true,
      autoDensity: true,
      resolution: Math.min(window.devicePixelRatio || 1, 2),
      backgroundAlpha: 0,
      preference: 'webgl',
    });
    if (destroyed) {
      app.destroy(true);
      return;
    }

    canvasElement = app.canvas;
    canvasElement.className = 'pixi-website-graph__canvas';
    canvasElement.setAttribute('aria-label', ariaLabel);
    canvasElement.setAttribute('role', 'img');
    hostElement.appendChild(canvasElement);

    world = new PIXI.Container();
    edgeLayer = new PIXI.Graphics();
    activeEdgeLayer = new PIXI.Graphics();
    nodeLayer = new PIXI.Container();
    world.addChild(edgeLayer, activeEdgeLayer, nodeLayer);
    app.stage.addChild(world);

    app.stage.eventMode = 'static';
    app.stage.hitArea = new PIXI.Rectangle(0, 0, app.screen.width, app.screen.height);
    app.stage.on('pointerdown', beginPan);
    app.stage.on('globalpointermove', continuePan);
    app.stage.on('pointerup', finishPan);
    app.stage.on('pointerupoutside', finishPan);

    for (const node of graphNodes) createNodeView(node, PIXI);
    // Start the force layout only after the canvas exists so reloading shows the
    // graph naturally arranging itself instead of revealing a pre-settled layout.
    buildSimulation();

    canvasElement.addEventListener('wheel', handleWheel, { passive: false });
    canvasElement.addEventListener('pointerdown', handleTouchPointerDown);
    canvasElement.addEventListener('pointermove', handleTouchPointerMove, { passive: false });
    canvasElement.addEventListener('pointerup', handleTouchPointerUp);
    canvasElement.addEventListener('pointercancel', handleTouchPointerUp);
    app.ticker.add(updateFrame);
    handleResize(PIXI, true);
    redrawEdges();
    updateNodeViews(1);
    ready = true;

    resizeObserver = new ResizeObserver(() => handleResize(PIXI));
    resizeObserver.observe(hostElement);

    themeObserver = new MutationObserver(() => {
      colors = readThemeColors();
      rebuildNodeColors();
      redrawEdges();
    });
    themeObserver.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['class', 'data-theme', 'data-season', 'style'],
    });
  }

  onMount(() => {
    initialize().catch((error) => {
      console.error('Unable to initialize Website Graph renderer.', error);
      failureMessage =
        error instanceof Error && error.message
          ? `The website graph could not start: ${error.message}`
          : 'The website graph could not start in this browser.';
      failed = true;
      ready = false;
    });
  });

  onDestroy(() => {
    destroyed = true;
    simulation?.alpha(0);
    resizeObserver?.disconnect();
    themeObserver?.disconnect();
    canvasElement?.removeEventListener('wheel', handleWheel);
    canvasElement?.removeEventListener('pointerdown', handleTouchPointerDown);
    canvasElement?.removeEventListener('pointermove', handleTouchPointerMove);
    canvasElement?.removeEventListener('pointerup', handleTouchPointerUp);
    canvasElement?.removeEventListener('pointercancel', handleTouchPointerUp);
    removeWindowDragListeners();
    app?.destroy(true);
    app = null;
  });
</script>

<div class="pixi-website-graph" bind:this={hostElement} aria-busy={!ready && !failed}>
  {#if !ready && !failed}
    <p class="pixi-website-graph__status" role="status">Loading graph…</p>
  {:else if failed}
    <p class="pixi-website-graph__status pixi-website-graph__status--failed" role="alert">
      {failureMessage}
    </p>
  {/if}

  <nav class="pixi-website-graph__links" aria-label="Website graph links">
    {#each nodes as node}
      {#if node.href}
        <a href={node.href}>{node.label}</a>
      {/if}
    {/each}
  </nav>
</div>

<style>
  .pixi-website-graph {
    position: relative;
    width: 100%;
    height: 100%;
    min-width: 0;
    min-height: 0;
    overflow: hidden;
    background: var(--bg);
    cursor: grab;
    touch-action: none;
    user-select: none;
    overscroll-behavior: none;
  }

  .pixi-website-graph:active {
    cursor: grabbing;
  }

  .pixi-website-graph :global(.pixi-website-graph__canvas) {
    display: block;
    width: 100%;
    height: 100%;
    outline: none;
  }

  .pixi-website-graph__status {
    position: absolute;
    inset: 0;
    z-index: 1;
    display: grid;
    place-items: center;
    padding: 2rem;
    margin: 0;
    color: var(--muted);
    pointer-events: none;
    text-align: center;
  }

  .pixi-website-graph__status--failed {
    pointer-events: auto;
  }

  .pixi-website-graph__links {
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip: rect(0 0 0 0);
    white-space: nowrap;
    border: 0;
  }
</style>
