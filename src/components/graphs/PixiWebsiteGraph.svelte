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
      labelHalfWidth: number;
      labelHeight: number;
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
  const HOVER_EASE = 1.45;
  const FIT_SIDE_PADDING = 38;
  const FIT_TOP_PADDING = 68;
  const FIT_BOTTOM_PADDING = 34;
  const LABEL_BASE_GAP = 3;
  const LABEL_HOVER_DROP = 12;
  const COLLISION_PADDING = 2.5;
  const DRAG_COLLISION_PADDING = 5;
  const DRAG_COLLISION_PASSES = 12;

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
      muted: dark ? '#aeb5bc' : '#6f7780',
      line: dark ? '#c6cdd4' : '#4a535d',
      lineAlpha: dark ? 0.3 : 0.46,
      accent: read('--accent', '#2aaea0'),
    };
  }

  function resolveNode(value: string | GraphNode) {
    if (typeof value !== 'string') return value;
    return graphNodes.find((node) => node.id === value);
  }

  function makeGraphData() {
    // Keep semantic anchors close together. Collision—not oversized link
    // lengths—provides the minimum safe spacing between rendered content.
    const width = 520;
    const height = 390;

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
        labelHalfWidth: 0,
        labelHeight: 0,
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
    return Math.max(node.radius + 5, 10);
  }

  function compoundBounds(node: GraphNode) {
    const hitRadius = interactionRadius(node);
    const labelHalfWidth = Math.max(
      node.labelHalfWidth || node.label.length * node.labelSize * 0.28,
      node.radius,
    );
    const labelHeight = node.labelHeight || node.labelSize * 1.2;
    const top = -hitRadius;
    const bottom =
      node.radius + LABEL_BASE_GAP + LABEL_HOVER_DROP + labelHeight + 3;

    return {
      halfWidth: Math.max(hitRadius, labelHalfWidth + 3),
      halfHeight: (bottom - top) / 2,
      centerYOffset: (top + bottom) / 2,
    };
  }

  function separateInitialOverlaps() {
    for (let pass = 0; pass < 28; pass += 1) {
      let moved = false;

      for (let index = 0; index < graphNodes.length; index += 1) {
        const first = graphNodes[index];
        const firstBounds = compoundBounds(first);

        for (let nextIndex = index + 1; nextIndex < graphNodes.length; nextIndex += 1) {
          const second = graphNodes[nextIndex];
          const secondBounds = compoundBounds(second);
          const deltaX = (second.x ?? 0) - (first.x ?? 0);
          const deltaY =
            (second.y ?? 0) + secondBounds.centerYOffset -
            ((first.y ?? 0) + firstBounds.centerYOffset);
          const overlapX =
            firstBounds.halfWidth + secondBounds.halfWidth + 2 - Math.abs(deltaX);
          const overlapY =
            firstBounds.halfHeight + secondBounds.halfHeight + 2 - Math.abs(deltaY);
          if (overlapX <= 0 || overlapY <= 0) continue;

          moved = true;
          if (overlapX < overlapY) {
            const direction = deltaX === 0
              ? (index + nextIndex) % 2 === 0 ? 1 : -1
              : Math.sign(deltaX);
            const shift = overlapX / 2 + 0.75;
            first.x = (first.x ?? 0) - direction * shift;
            second.x = (second.x ?? 0) + direction * shift;
          } else {
            const direction = deltaY === 0
              ? (index + nextIndex) % 2 === 0 ? 1 : -1
              : Math.sign(deltaY);
            const shift = overlapY / 2 + 0.75;
            first.y = (first.y ?? 0) - direction * shift;
            second.y = (second.y ?? 0) + direction * shift;
          }
        }
      }

      if (!moved) break;
    }
  }

  function createCompoundCollisionForce() {
    let forceNodes: GraphNode[] = [];

    const force: any = (_alpha: number) => {
      for (let iteration = 0; iteration < 8; iteration += 1) {
        for (let index = 0; index < forceNodes.length; index += 1) {
          const first = forceNodes[index];
          const firstBounds = compoundBounds(first);

          for (let nextIndex = index + 1; nextIndex < forceNodes.length; nextIndex += 1) {
            const second = forceNodes[nextIndex];
            const secondBounds = compoundBounds(second);
            const deltaX = (second.x ?? 0) - (first.x ?? 0);
            const deltaY =
              (second.y ?? 0) + secondBounds.centerYOffset -
              ((first.y ?? 0) + firstBounds.centerYOffset);
            const overlapX =
              firstBounds.halfWidth + secondBounds.halfWidth + COLLISION_PADDING - Math.abs(deltaX);
            const overlapY =
              firstBounds.halfHeight + secondBounds.halfHeight + COLLISION_PADDING - Math.abs(deltaY);
            if (overlapX <= 0 || overlapY <= 0) continue;

            if (overlapX < overlapY) {
              const direction = deltaX === 0
                ? (index + nextIndex) % 2 === 0 ? 1 : -1
                : Math.sign(deltaX);
              const firstFixed = first.fx != null;
              const secondFixed = second.fx != null;
              const correction = overlapX + 0.75;

              if (firstFixed && !secondFixed) {
                second.x = (second.x ?? 0) + direction * correction;
              } else if (!firstFixed && secondFixed) {
                first.x = (first.x ?? 0) - direction * correction;
              } else if (!firstFixed && !secondFixed) {
                first.x = (first.x ?? 0) - direction * correction / 2;
                second.x = (second.x ?? 0) + direction * correction / 2;
              }

              if (direction > 0) {
                first.vx = Math.min(first.vx ?? 0, 0);
                second.vx = Math.max(second.vx ?? 0, 0);
              } else {
                first.vx = Math.max(first.vx ?? 0, 0);
                second.vx = Math.min(second.vx ?? 0, 0);
              }
            } else {
              const direction = deltaY === 0
                ? (index + nextIndex) % 2 === 0 ? 1 : -1
                : Math.sign(deltaY);
              const firstFixed = first.fy != null;
              const secondFixed = second.fy != null;
              const correction = overlapY + 0.75;

              if (firstFixed && !secondFixed) {
                second.y = (second.y ?? 0) + direction * correction;
              } else if (!firstFixed && secondFixed) {
                first.y = (first.y ?? 0) - direction * correction;
              } else if (!firstFixed && !secondFixed) {
                first.y = (first.y ?? 0) - direction * correction / 2;
                second.y = (second.y ?? 0) + direction * correction / 2;
              }

              if (direction > 0) {
                first.vy = Math.min(first.vy ?? 0, 0);
                second.vy = Math.max(second.vy ?? 0, 0);
              } else {
                first.vy = Math.max(first.vy ?? 0, 0);
                second.vy = Math.min(second.vy ?? 0, 0);
              }
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
          .distance((link) => link.kind === 'secondary' ? 72 : 94)
          .strength((link) => link.kind === 'secondary' ? 0.24 : 0.18),
      )
      .force(
        'charge',
        forceManyBody<GraphNode>()
          .strength((node) =>
            node.id === '/'
              ? -430
              : node.degree >= 3
                ? -330
                : node.depth === 1
                  ? -235
                  : -165,
          )
          .distanceMin(22)
          .theta(0.76),
      )
      .force(
        'x',
        forceX<GraphNode>((node) => node.anchorX).strength((node) => node.depth > 1 ? 0.06 : 0.035),
      )
      .force(
        'y',
        forceY<GraphNode>((node) => node.anchorY).strength((node) => node.depth > 1 ? 0.06 : 0.035),
      )
      .force(
        'collision',
        forceCollide<GraphNode>()
          .radius((node) => interactionRadius(node) + 3)
          .strength(1)
          .iterations(10),
      )
      .force('compoundCollision', createCompoundCollisionForce())
      .velocityDecay(0.42)
      .alphaDecay(0.018);
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
      resolution: Math.min(Math.max((window.devicePixelRatio || 1) * 4, 5), 8),
    });
    label.anchor.set(0.5, 0);
    label.position.set(0, node.radius + LABEL_BASE_GAP);
    // High-resolution text textures stay sharp through camera scaling.
    // Subpixel positioning avoids the stair-step motion caused by pixel snapping.
    label.roundPixels = false;
    node.labelHalfWidth = label.width / 2;
    node.labelHeight = label.height;

    container.addChild(base, highlight, label);
    nodeLayer.addChild(container);
    node.view = { container, base, highlight, label };

    container.on('pointerover', () => setActiveNode(node));
    container.on('pointerout', () => {
      if (draggedNode !== node) setActiveNode(null);
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

  function separateDraggedNodeImmediately(node: GraphNode) {
    for (let pass = 0; pass < DRAG_COLLISION_PASSES; pass += 1) {
      let moved = false;

      for (let index = 0; index < graphNodes.length; index += 1) {
        const first = graphNodes[index];
        const firstBounds = compoundBounds(first);

        for (let nextIndex = index + 1; nextIndex < graphNodes.length; nextIndex += 1) {
          const second = graphNodes[nextIndex];
          const secondBounds = compoundBounds(second);
          const firstX = first === node ? (node.fx ?? node.x ?? 0) : (first.x ?? 0);
          const firstY = first === node ? (node.fy ?? node.y ?? 0) : (first.y ?? 0);
          const secondX = second === node ? (node.fx ?? node.x ?? 0) : (second.x ?? 0);
          const secondY = second === node ? (node.fy ?? node.y ?? 0) : (second.y ?? 0);
          const deltaX = secondX - firstX;
          const deltaY =
            secondY + secondBounds.centerYOffset -
            (firstY + firstBounds.centerYOffset);
          const overlapX =
            firstBounds.halfWidth + secondBounds.halfWidth + DRAG_COLLISION_PADDING -
            Math.abs(deltaX);
          const overlapY =
            firstBounds.halfHeight + secondBounds.halfHeight + DRAG_COLLISION_PADDING -
            Math.abs(deltaY);
          if (overlapX <= 0 || overlapY <= 0) continue;

          moved = true;
          const firstFixed = first === node;
          const secondFixed = second === node;

          if (overlapX < overlapY) {
            const direction = deltaX === 0
              ? (index + nextIndex) % 2 === 0 ? 1 : -1
              : Math.sign(deltaX);
            const correction = overlapX + 1;

            if (firstFixed && !secondFixed) {
              second.x = secondX + direction * correction;
              second.vx = direction * Math.max(Math.abs(second.vx ?? 0), 2.4);
            } else if (!firstFixed && secondFixed) {
              first.x = firstX - direction * correction;
              first.vx = -direction * Math.max(Math.abs(first.vx ?? 0), 2.4);
            } else if (!firstFixed && !secondFixed) {
              first.x = firstX - direction * correction / 2;
              second.x = secondX + direction * correction / 2;
              first.vx = -direction * Math.max(Math.abs(first.vx ?? 0), 1.2);
              second.vx = direction * Math.max(Math.abs(second.vx ?? 0), 1.2);
            }
          } else {
            const direction = deltaY === 0
              ? (index + nextIndex) % 2 === 0 ? 1 : -1
              : Math.sign(deltaY);
            const correction = overlapY + 1;

            if (firstFixed && !secondFixed) {
              second.y = secondY + direction * correction;
              second.vy = direction * Math.max(Math.abs(second.vy ?? 0), 2.4);
            } else if (!firstFixed && secondFixed) {
              first.y = firstY - direction * correction;
              first.vy = -direction * Math.max(Math.abs(first.vy ?? 0), 2.4);
            } else if (!firstFixed && !secondFixed) {
              first.y = firstY - direction * correction / 2;
              second.y = secondY + direction * correction / 2;
              first.vy = -direction * Math.max(Math.abs(first.vy ?? 0), 1.2);
              second.vy = direction * Math.max(Math.abs(second.vy ?? 0), 1.2);
            }
          }
        }
      }

      if (!moved) break;
    }
  }

  function beginNodeDrag(node: GraphNode, event: any) {
    event.stopPropagation();
    setActiveNode(node);
    draggedNode = node;
    draggedPointerId = event.pointerId;
    dragStartX = event.global.x;
    dragStartY = event.global.y;
    dragMoved = false;
    node.fx = node.x;
    node.fy = node.y;
    simulation?.alpha(0.5).alphaTarget(0.34).restart();
    addWindowDragListeners();
  }

  function handleNodeDrag(event: PointerEvent) {
    if (!draggedNode || draggedPointerId !== event.pointerId || !app) return;
    event.preventDefault();
    const pointer = clientToCanvas(event.clientX, event.clientY);
    const worldPoint = screenToWorld(pointer.x, pointer.y);
    const radius = draggedNode.radius;
    const minX = (0 - camera.x) / camera.scale + radius;
    const maxX = (app.screen.width - camera.x) / camera.scale - radius;
    const minY = (0 - camera.y) / camera.scale + radius;
    const maxY = (app.screen.height - camera.y) / camera.scale - radius;

    draggedNode.fx = clamp(worldPoint.x, Math.min(minX, maxX), Math.max(minX, maxX));
    draggedNode.fy = clamp(worldPoint.y, Math.min(minY, maxY), Math.max(minY, maxY));
    draggedNode.x = draggedNode.fx;
    draggedNode.y = draggedNode.fy;
    draggedNode.vx = 0;
    draggedNode.vy = 0;
    separateDraggedNodeImmediately(draggedNode);
    simulation?.alpha(Math.max(simulation.alpha(), 0.42)).alphaTarget(0.34).restart();
    dragMoved ||= Math.hypot(pointer.x - dragStartX, pointer.y - dragStartY) > 4;
  }

  function finishNodeDrag(event: PointerEvent) {
    if (!draggedNode || draggedPointerId !== event.pointerId) return;
    const node = draggedNode;
    const shouldNavigate = !dragMoved && Boolean(node.href);

    node.fx = null;
    node.fy = null;
    simulation?.alphaTarget(0);
    draggedNode = null;
    draggedPointerId = null;
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
        const nodeBounds = compoundBounds(node);
        const x = node.x ?? 0;
        const centerY = (node.y ?? 0) + nodeBounds.centerYOffset;
        bounds.minX = Math.min(bounds.minX, x - nodeBounds.halfWidth);
        bounds.maxX = Math.max(bounds.maxX, x + nodeBounds.halfWidth);
        bounds.minY = Math.min(bounds.minY, centerY - nodeBounds.halfHeight);
        bounds.maxY = Math.max(bounds.maxY, centerY + nodeBounds.halfHeight);
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
    // Align the top of the fitted graph with the Center button instead of
    // vertically centering it in a large empty field.
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
    const lineWidth = 1.15 / Math.max(camera.scale, Number.EPSILON);
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
      resolution: Math.min((window.devicePixelRatio || 1) * 2, 4),
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
    separateInitialOverlaps();
    for (const node of graphNodes) {
      node.view?.container.position.set(node.x ?? 0, node.y ?? 0);
    }
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
