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
      hover: number;
      hoverTarget: number;
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

  const PIXI_URL = 'https://cdn.jsdelivr.net/npm/pixi.js@8.19.0/+esm';
  const MIN_ZOOM = 0.12;
  const MAX_ZOOM = 8;
  const CAMERA_EASE = 13;
  const HOVER_EASE = 9;
  const LABEL_FADE_START = 8;
  const LABEL_FADE_END = 11;
  const FIT_PADDING = 72;

  let hostElement!: HTMLDivElement;
  let canvasElement: HTMLCanvasElement | null = null;
  let app: any = null;
  let world: any = null;
  let edgeLayer: any = null;
  let activeEdgeLayer: any = null;
  let nodeLayer: any = null;
  let simulation: Simulation<GraphNode, GraphLink> | null = null;
  let graphNodes: GraphNode[] = [];
  let graphLinks: GraphLink[] = [];
  let resizeObserver: ResizeObserver | null = null;
  let themeObserver: MutationObserver | null = null;
  let destroyed = false;
  let failed = false;
  let activeNodeId: string | null = null;
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
    line: '#b7bbc2',
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

  function nodeRadius(node: NetworkNode) {
    if (node.current) return 7;
    if (node.featured) return 6;
    if ((node.radius ?? 0) >= 34) return 5;
    if ((node.radius ?? 0) <= 22) return 3.5;
    return 4.25;
  }

  function nodeLabelSize(radius: number) {
    return Math.round(11.5 + radius * 0.45);
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
      muted: dark ? '#a9adb3' : '#858a91',
      line: dark ? 'rgba(190, 194, 201, 0.42)' : 'rgba(92, 98, 107, 0.32)',
      accent: read('--accent', '#2aaea0'),
    };
  }

  function resolveNode(value: string | GraphNode) {
    if (typeof value !== 'string') return value;
    return graphNodes.find((node) => node.id === value);
  }

  function makeGraphData() {
    const width = 780;
    const height = 560;

    graphNodes = nodes.map((node, index) => {
      const radius = nodeRadius(node);
      const angle = (index / Math.max(1, nodes.length)) * Math.PI * 2;
      const anchorX = node.anchor?.x ?? 0.5 + Math.cos(angle) * 0.28;
      const anchorY = node.anchor?.y ?? 0.5 + Math.sin(angle) * 0.28;

      return {
        ...node,
        radius,
        labelSize: nodeLabelSize(radius),
        hover: 0,
        hoverTarget: 0,
        x: (anchorX - 0.5) * width,
        y: (anchorY - 0.5) * height,
      };
    });

    graphLinks = links.map((link) => ({ ...link }));
  }

  function buildSimulation() {
    simulation?.stop();

    // Use D3's native degree-based link strength, default many-body charge,
    // velocity decay, and alpha decay. A very weak x/y force is the only
    // containment added: unlike forceCenter, it prevents disconnected site
    // sections from drifting so far apart that the fitted graph becomes tiny.
    const linkForce = forceLink<GraphNode, GraphLink>(graphLinks)
      .id((node) => node.id)
      .distance((link) => link.distance ?? (link.kind === 'secondary' ? 78 : 108))
      .iterations(2);

    simulation = forceSimulation<GraphNode, GraphLink>(graphNodes)
      .force('link', linkForce)
      .force('charge', forceManyBody<GraphNode>())
      .force(
        'collision',
        forceCollide<GraphNode>()
          .radius((node) => node.radius + 5)
          .iterations(1),
      )
      .force('x', forceX<GraphNode>(0).strength(0.018))
      .force('y', forceY<GraphNode>(0).strength(0.018))
      .stop();

    simulation.tick(260);
  }

  function createNodeView(node: GraphNode, PIXI: any) {
    const container = new PIXI.Container();
    container.position.set(node.x ?? 0, node.y ?? 0);
    container.eventMode = 'static';
    container.cursor = node.href ? 'pointer' : 'grab';
    container.hitArea = new PIXI.Circle(0, 0, Math.max(node.radius + 6, 12));

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
        fontWeight: node.current || node.featured ? '500' : '400',
        fill: colors.text,
        align: 'center',
      },
      resolution: Math.min((window.devicePixelRatio || 1) * 2, 4),
    });
    label.anchor.set(0.5, 0);
    label.position.set(0, node.radius + 7);
    label.roundPixels = true;

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
    activeNodeId = node?.id ?? null;
    if (node) edgeFocusNode = node;
    for (const item of graphNodes) item.hoverTarget = item === node ? 1 : 0;
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

  function stopLayoutForNavigation() {
    simulation?.stop();
    simulation?.alphaTarget(0);
  }

  function handleWheel(event: WheelEvent) {
    if (!canvasElement) return;
    event.preventDefault();
    stopLayoutForNavigation();

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
      stopLayoutForNavigation();
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
    stopLayoutForNavigation();
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
    node.fx = node.x;
    node.fy = node.y;
    simulation?.alpha(0.24).alphaTarget(0.16).restart();
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
        const x = node.x ?? 0;
        const y = node.y ?? 0;
        const labelWidth = Math.max(0, node.label.length * node.labelSize * 0.28);
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
        (app.screen.width - FIT_PADDING * 2) / graphWidth,
        (app.screen.height - FIT_PADDING * 2) / graphHeight,
      ),
      MIN_ZOOM,
      2.1,
    );
    const centerX = (bounds.minX + bounds.maxX) / 2;
    const centerY = (bounds.minY + bounds.maxY) / 2;

    camera.zooming = false;
    camera.targetScale = scale;
    camera.targetX = app.screen.width / 2 - centerX * scale;
    camera.targetY = app.screen.height / 2 - centerY * scale;

    if (immediate) {
      camera.scale = camera.targetScale;
      camera.x = camera.targetX;
      camera.y = camera.targetY;
      updateCameraTransform();
    }
  }

  export function resetView() {
    stopLayoutForNavigation();
    centerGraph(false);
  }

  function redrawEdges() {
    if (!edgeLayer || !activeEdgeLayer) return;
    edgeLayer.clear();
    activeEdgeLayer.clear();
    const lineWidth = 1.35 / Math.max(camera.scale, Number.EPSILON);

    for (const link of graphLinks) {
      const source = resolveNode(link.source);
      const target = resolveNode(link.target);
      if (!source || !target) continue;
      edgeLayer
        .moveTo(source.x ?? 0, source.y ?? 0)
        .lineTo(target.x ?? 0, target.y ?? 0)
        .stroke({ color: colors.line, width: lineWidth, alpha: 0.78 });

      if (edgeFocusNode && (source.id === edgeFocusNode.id || target.id === edgeFocusNode.id)) {
        activeEdgeLayer
          .moveTo(source.x ?? 0, source.y ?? 0)
          .lineTo(target.x ?? 0, target.y ?? 0)
          .stroke({
            color: colors.accent,
            width: lineWidth,
            alpha: 0.92 * edgeFocusNode.hover,
          });
      }
    }
  }

  function updateNodeViews(deltaSeconds: number) {
    const transition = 1 - Math.exp(-HOVER_EASE * deltaSeconds);

    for (const node of graphNodes) {
      const view = node.view;
      if (!view) continue;
      node.hover += (node.hoverTarget - node.hover) * transition;
      view.container.position.set(node.x ?? 0, node.y ?? 0);
      view.highlight.alpha = node.hover;
      view.label.y = node.radius + 7;

      const screenFontSize = node.labelSize * camera.scale;
      const visibility = smoothstep(LABEL_FADE_START, LABEL_FADE_END, screenFontSize);
      view.label.alpha = Math.max(visibility * 0.82, node.hover);
    }

    if (edgeFocusNode && edgeFocusNode.hover < 0.002 && activeNodeId !== edgeFocusNode.id) {
      edgeFocusNode = null;
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

    if (simulation && simulation.alpha() < 0.012 && draggedNode === null) {
      simulation.stop();
    }
  }

  function handleResize(PIXI: any) {
    if (!app) return;
    app.stage.hitArea = new PIXI.Rectangle(0, 0, app.screen.width, app.screen.height);
  }

  async function initialize() {
    const PIXI = (await import(/* @vite-ignore */ PIXI_URL)) as any;
    if (destroyed) return;

    colors = readThemeColors();
    makeGraphData();
    buildSimulation();

    app = new PIXI.Application();
    await app.init({
      resizeTo: hostElement,
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

    canvasElement.addEventListener('wheel', handleWheel, { passive: false });
    canvasElement.addEventListener('pointerdown', handleTouchPointerDown);
    canvasElement.addEventListener('pointermove', handleTouchPointerMove, { passive: false });
    canvasElement.addEventListener('pointerup', handleTouchPointerUp);
    canvasElement.addEventListener('pointercancel', handleTouchPointerUp);
    app.ticker.add(updateFrame);
    centerGraph(true);
    redrawEdges();
    updateNodeViews(1);

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
      failed = true;
    });
  });

  onDestroy(() => {
    destroyed = true;
    simulation?.stop();
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

<div class:failed class="pixi-website-graph" bind:this={hostElement}>
  <p class="pixi-website-graph__fallback">
    The website graph requires WebGL and JavaScript.
  </p>

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

  .pixi-website-graph__fallback,
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

  .pixi-website-graph__fallback {
    display: none;
  }

  .pixi-website-graph.failed .pixi-website-graph__fallback {
    inset: 0;
    display: grid;
    width: auto;
    height: auto;
    place-items: center;
    padding: 2rem;
    margin: 0;
    overflow: visible;
    clip: auto;
    color: var(--muted);
    white-space: normal;
    text-align: center;
  }
</style>
