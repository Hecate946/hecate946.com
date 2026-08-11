<script lang="ts">
  import { onMount } from 'svelte';
  import { WORLD_MAP_PATH } from '@/data/world-map';
  import { WORLD_INTERNAL_BORDERS_PATH } from '@/data/world-internal-borders';
  import {
    VISITOR_LIGHT_HIT_RADIUS_PX,
    VISITOR_LIGHT_STOPS,
    visitorLightMapDistanceT,
    visitorLightSizePx,
    VISITOR_VIEW_WHEEL_DELTA_CAP,
    VISITOR_VIEW_WHEEL_RATE,
    VISITOR_VIEW_ZOOM_EASING,
  } from '@/lib/visitor-lights';

  interface VisitorLocation {
    city: string | null;
    region: string | null;
    country: string | null;
    countryCode: string | null;
    latitude: number;
    longitude: number;
    pageViews: number;
    estimatedVisitors: number;
    pointIndex?: number;
    pointCount?: number;
  }

  interface ProjectedVisitorLocation extends VisitorLocation {
    x: number;
    y: number;
    count: number;
    label: string;
  }

  interface Point {
    x: number;
    y: number;
  }

  interface PinchState {
    distance: number;
    zoom: number;
  }

  interface ZoomAnchor {
    screenX: number;
    screenY: number;
    worldX: number;
    worldY: number;
  }

  export let locations: VisitorLocation[] = [];
  export let totalVisitors = 0;

  const WIDTH = 1000;
  const HEIGHT = 500;
  const MIN_ZOOM = 1;
  const MAX_ZOOM = 12;
  const WORLD_COPIES = [-1, 0, 1] as const;

  let mapElement!: SVGSVGElement;
  let mapShellElement!: HTMLDivElement;
  let tooltipVisible = false;
  let tooltipX = 0;
  let tooltipY = 0;
  let tooltipText = '';
  let projectedLocations: ProjectedVisitorLocation[] = [];
  let locationSignature = '';
  let visitorScaleBucket = 0;
  let transform = '';
  let zoom = 1;
  let targetZoom = 1;
  let centerX = WIDTH / 2;
  let centerY = HEIGHT / 2;
  let visibleWidthAtZoomOne = WIDTH;
  let visibleHeightAtZoomOne = HEIGHT;
  let viewUnitsPerCssPixel = 1;
  let dragging = false;
  let pinching = false;
  let previousPointer: Point | null = null;
  let pinchState: PinchState | null = null;
  let zoomAnchor: ZoomAnchor | null = null;
  let fittedSignature = '';
  let animationFrame = 0;

  const activePointers = new Map<number, Point>();

  $: projectedLocations = groupLocations(locations).map((location) => ({
    ...location,
    x: wrapX(((location.longitude + 180) / 360) * WIDTH),
    y: ((90 - location.latitude) / 180) * HEIGHT,
  }));

  $: visitorScaleBucket = Math.floor(
    Math.log2(Math.max(1, totalVisitors)),
  );

  $: locationSignature = `${projectedLocations
    .map(
      (location) =>
        `${location.latitude}:${location.longitude}:${location.count}`,
    )
    .sort()
    .join('|')}|visitors:${visitorScaleBucket}`;

  $: if (locationSignature !== fittedSignature) {
    fittedSignature = locationSignature;
    fitLocations();
  }

  $: transform = `translate(${WIDTH / 2} ${HEIGHT / 2}) scale(${zoom}) translate(${-centerX} ${-centerY})`;

  function scheduleZoomAnimation() {
    if (animationFrame || typeof window === 'undefined') return;
    animationFrame = requestAnimationFrame(animateZoom);
  }

  function animateZoom() {
    animationFrame = 0;
    const zoomDelta = targetZoom - zoom;
    if (Math.abs(zoomDelta) > 0.00001) {
      zoom += zoomDelta * VISITOR_VIEW_ZOOM_EASING;
    } else if (zoom !== targetZoom) {
      zoom = targetZoom;
    }

    // When wheel-zooming, keep the geographic point beneath the cursor pinned
    // beneath that cursor for every eased frame.
    if (zoomAnchor) {
      centerX = zoomAnchor.worldX - (zoomAnchor.screenX - WIDTH / 2) / zoom;
      centerY = zoomAnchor.worldY - (zoomAnchor.screenY - HEIGHT / 2) / zoom;
    }

    constrainCamera();

    if (Math.abs(targetZoom - zoom) > 0.00001) {
      scheduleZoomAnimation();
    } else {
      zoom = targetZoom;
      zoomAnchor = null;
    }
  }

  onMount(() => {
    updateVisibleDimensions();
    fitLocations(true);
    const observer = new ResizeObserver(() => {
      updateVisibleDimensions();
      constrainCamera();
    });

    observer.observe(mapElement);

    return () => {
      if (animationFrame) cancelAnimationFrame(animationFrame);
      animationFrame = 0;
      observer.disconnect();
    };
  });

  function clamp(value: number, minimum: number, maximum: number) {
    return Math.min(maximum, Math.max(minimum, value));
  }

  function wrapX(value: number) {
    return ((value % WIDTH) + WIDTH) % WIDTH;
  }


  function locationLabel(location: VisitorLocation) {
    return [location.city, location.region, location.country]
      .filter(Boolean)
      .join(', ') || 'Approximate visitor location';
  }

  function groupLocations(values: VisitorLocation[]) {
    const groups = new Map<string, ProjectedVisitorLocation>();

    for (const location of values) {
      if (
        !Number.isFinite(location.latitude) ||
        !Number.isFinite(location.longitude)
      ) {
        continue;
      }

      const key = `${location.latitude.toFixed(5)}:${location.longitude.toFixed(5)}`;
      const existing = groups.get(key);

      if (existing) {
        existing.count += 1;
        continue;
      }

      groups.set(key, {
        ...location,
        x: 0,
        y: 0,
        count: 1,
        label: locationLabel(location),
      });
    }

    return [...groups.values()];
  }

  function updateVisibleDimensions() {
    if (!mapElement) return;

    const bounds = mapElement.getBoundingClientRect();
    if (bounds.width <= 0 || bounds.height <= 0) return;

    const aspect = bounds.width / bounds.height;
    // xMidYMid slice uses the larger CSS scale on each axis, so the inverse
    // scale is the smaller world-units-per-pixel value. This keeps the shared
    // light sizes exact even when the panel is not precisely 2:1.
    viewUnitsPerCssPixel = Math.min(
      WIDTH / bounds.width,
      HEIGHT / bounds.height,
    );

    // The SVG uses xMidYMid slice. These are the world dimensions visible at 1×.
    visibleWidthAtZoomOne = Math.min(WIDTH, HEIGHT * aspect);
    visibleHeightAtZoomOne = Math.min(HEIGHT, WIDTH / aspect);
  }

  function constrainCamera() {
    centerX = wrapX(centerX);

    const halfVisibleHeight = visibleHeightAtZoomOne / (2 * zoom);
    centerY = clamp(
      centerY,
      halfVisibleHeight,
      HEIGHT - halfVisibleHeight,
    );
  }

  function circularHorizontalBounds(xs: number[]) {
    const sorted = xs.map(wrapX).sort((a, b) => a - b);

    if (sorted.length === 1) {
      return { center: sorted[0], span: 0 };
    }

    let largestGap = -1;
    let gapAfterIndex = 0;

    for (let index = 0; index < sorted.length; index += 1) {
      const current = sorted[index];
      const next =
        index === sorted.length - 1 ? sorted[0] + WIDTH : sorted[index + 1];
      const gap = next - current;

      if (gap > largestGap) {
        largestGap = gap;
        gapAfterIndex = index;
      }
    }

    const startIndex = (gapAfterIndex + 1) % sorted.length;
    const start = sorted[startIndex];
    const span = WIDTH - largestGap;

    return {
      center: wrapX(start + span / 2),
      span,
    };
  }

  function fitLocations(immediate = false) {
    let nextZoom = 1;

    if (projectedLocations.length === 0) {
      centerX = WIDTH / 2;
      centerY = HEIGHT / 2;
    } else {
      const visitorZoomCap = clamp(
        5.2 - Math.log2(totalVisitors + 1) * 0.22,
        1.25,
        5.2,
      );

      if (projectedLocations.length === 1) {
        nextZoom = Math.min(4.5, visitorZoomCap);
        centerX = projectedLocations[0].x;
        centerY = projectedLocations[0].y;
      } else {
        const horizontal = circularHorizontalBounds(
          projectedLocations.map((location) => location.x),
        );
        const ys = projectedLocations.map((location) => location.y);
        const minimumY = Math.min(...ys);
        const maximumY = Math.max(...ys);
        const spanX = Math.max(80, horizontal.span);
        const spanY = Math.max(45, maximumY - minimumY);
        const padding = 110;

        nextZoom = clamp(
          Math.min(
            Math.max(1, visibleWidthAtZoomOne - padding * 2) / spanX,
            Math.max(1, visibleHeightAtZoomOne - padding * 2) / spanY,
            visitorZoomCap,
          ),
          MIN_ZOOM,
          6,
        );
        centerX = horizontal.center;
        centerY = (minimumY + maximumY) / 2;
      }
    }

    zoomAnchor = null;
    targetZoom = clamp(nextZoom, MIN_ZOOM, MAX_ZOOM);
    if (immediate) zoom = targetZoom;
    else scheduleZoomAnimation();
    constrainCamera();
  }

  function viewBoxPoint(clientX: number, clientY: number): Point {
    const point = mapElement.createSVGPoint();
    point.x = clientX;
    point.y = clientY;

    const matrix = mapElement.getScreenCTM();
    if (!matrix) return { x: WIDTH / 2, y: HEIGHT / 2 };

    const transformed = point.matrixTransform(matrix.inverse());
    return { x: transformed.x, y: transformed.y };
  }


  function locationAtClientPoint(clientX: number, clientY: number) {
    const screen = viewBoxPoint(clientX, clientY);
    const worldX = wrapX(centerX + (screen.x - WIDTH / 2) / zoom);
    const worldY = centerY + (screen.y - HEIGHT / 2) / zoom;
    const radius = hitRadius(zoom);
    const radiusSq = radius * radius;
    let best: ProjectedVisitorLocation | null = null;
    let bestDistanceSq = radiusSq;

    for (const location of projectedLocations) {
      let dx = location.x - worldX;
      if (dx > WIDTH / 2) dx -= WIDTH;
      if (dx < -WIDTH / 2) dx += WIDTH;
      const dy = location.y - worldY;
      const distanceSq = dx * dx + dy * dy;

      if (distanceSq <= bestDistanceSq) {
        bestDistanceSq = distanceSq;
        best = location;
      }
    }

    return best;
  }

  function updateTooltip(event: PointerEvent) {
    if (dragging || pinching || activePointers.size > 0 || event.buttons !== 0) {
      tooltipVisible = false;
      return;
    }

    const location = locationAtClientPoint(event.clientX, event.clientY);
    if (!location) {
      tooltipVisible = false;
      return;
    }

    const bounds = mapShellElement.getBoundingClientRect();
    tooltipText = `${location.label}${location.count > 1 ? ` · ${location.count} visitors` : ''}`;
    tooltipX = event.clientX - bounds.left;
    tooltipY = event.clientY - bounds.top;
    tooltipVisible = true;
  }

  function setZoomTarget(nextZoom: number, anchor: ZoomAnchor | null = null) {
    targetZoom = clamp(nextZoom, MIN_ZOOM, MAX_ZOOM);
    zoomAnchor = anchor;
    scheduleZoomAnimation();
  }

  function zoomByDistanceRatio(
    ratio: number,
    anchor: ZoomAnchor | null = null,
  ) {
    // The globe multiplies camera-to-surface distance by this ratio. Flat-map
    // scale is the inverse of that distance, so use the reciprocal here.
    setZoomTarget(targetZoom / ratio, anchor);
  }

  function cursorZoomAnchor(clientX: number, clientY: number): ZoomAnchor {
    const screen = viewBoxPoint(clientX, clientY);
    return {
      screenX: screen.x,
      screenY: screen.y,
      worldX: wrapX(centerX + (screen.x - WIDTH / 2) / zoom),
      worldY: centerY + (screen.y - HEIGHT / 2) / zoom,
    };
  }

  function handleWheel(event: WheelEvent) {
    const pixelDelta =
      event.deltaMode === WheelEvent.DOM_DELTA_LINE
        ? event.deltaY * 16
        : event.deltaMode === WheelEvent.DOM_DELTA_PAGE
          ? event.deltaY * Math.max(320, mapElement.clientHeight)
          : event.deltaY;
    const boundedDelta = clamp(
      pixelDelta,
      -VISITOR_VIEW_WHEEL_DELTA_CAP,
      VISITOR_VIEW_WHEEL_DELTA_CAP,
    );
    const zoomRatio = Math.exp(boundedDelta * VISITOR_VIEW_WHEEL_RATE);

    // Zoom toward the geographic point beneath the cursor, but preserve the
    // globe-matched eased zoom response by moving the center a little on every
    // animation frame instead of jumping it immediately.
    zoomByDistanceRatio(
      zoomRatio,
      cursorZoomAnchor(event.clientX, event.clientY),
    );
  }

  function pointerPair() {
    return Array.from(activePointers.values()).slice(0, 2);
  }

  function distanceBetween(first: Point, second: Point) {
    return Math.hypot(second.x - first.x, second.y - first.y);
  }

  function beginPinch() {
    const [first, second] = pointerPair();
    if (!first || !second) return;

    const distance = Math.max(1, distanceBetween(first, second));

    pinchState = {
      distance,
      zoom: targetZoom,
    };

    pinching = true;
    dragging = false;
    previousPointer = null;
  }

  function updatePinch() {
    const [first, second] = pointerPair();
    if (!first || !second || !pinchState) return;

    const distance = Math.max(1, distanceBetween(first, second));
    setZoomTarget(
      pinchState.zoom * (distance / pinchState.distance),
    );
  }

  function handlePointerDown(event: PointerEvent) {
    if (event.pointerType === 'mouse' && event.button !== 0) return;

    tooltipVisible = false;
    event.preventDefault();
    zoomAnchor = null;
    activePointers.set(
      event.pointerId,
      viewBoxPoint(event.clientX, event.clientY),
    );

    try {
      mapElement.setPointerCapture(event.pointerId);
    } catch {
      // Pointer capture is an enhancement; interaction still works without it.
    }

    if (activePointers.size >= 2) {
      beginPinch();
      return;
    }

    dragging = true;
    pinching = false;
    pinchState = null;
    previousPointer = activePointers.get(event.pointerId) ?? null;
  }

  function handlePointerMove(event: PointerEvent) {
    if (!activePointers.has(event.pointerId)) {
      updateTooltip(event);
      return;
    }

    tooltipVisible = false;
    const current = viewBoxPoint(event.clientX, event.clientY);
    activePointers.set(event.pointerId, current);

    if (activePointers.size >= 2) {
      if (!pinchState) beginPinch();
      updatePinch();
      return;
    }

    if (!dragging || !previousPointer) return;

    centerX -= (current.x - previousPointer.x) / zoom;
    centerY -= (current.y - previousPointer.y) / zoom;
    previousPointer = current;
    constrainCamera();
  }

  function endPointer(event: PointerEvent) {
    activePointers.delete(event.pointerId);

    if (mapElement.hasPointerCapture(event.pointerId)) {
      mapElement.releasePointerCapture(event.pointerId);
    }

    if (activePointers.size >= 2) {
      beginPinch();
      return;
    }

    pinchState = null;
    pinching = false;

    if (activePointers.size === 1) {
      dragging = true;
      previousPointer = Array.from(activePointers.values())[0] ?? null;
      return;
    }

    dragging = false;
    previousPointer = null;
    updateTooltip(event);
  }

  function lightRadius(count: number, currentZoom: number) {
    // currentZoom is passed explicitly so every eased zoom frame updates the
    // rendered SVG radius. The visible light has a firm close-zoom floor.
    const distanceT = visitorLightMapDistanceT(
      currentZoom,
      MIN_ZOOM,
      MAX_ZOOM,
    );
    const diameterPx = visitorLightSizePx(distanceT, count);
    return (diameterPx * 0.5 * viewUnitsPerCssPixel) / currentZoom;
  }

  function hitRadius(currentZoom: number) {
    return (
      VISITOR_LIGHT_HIT_RADIUS_PX * viewUnitsPerCssPixel / currentZoom
    );
  }
</script>

<div class="visitor-map-shell" bind:this={mapShellElement}>
  <svg
    bind:this={mapElement}
    class="visitor-map"
    data-dragging={dragging || pinching}
    viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
    width={WIDTH}
    height={HEIGHT}
    preserveAspectRatio="xMidYMid slice"
    role="img"
    aria-label="Zoomable, horizontally wrapping map of approximate visitor lights"
    on:wheel|preventDefault={handleWheel}
    on:pointerdown={handlePointerDown}
    on:pointermove={handlePointerMove}
    on:pointerup={endPointer}
    on:pointercancel={endPointer}
    on:pointerleave={() => (tooltipVisible = false)}
  >
    <defs>
      <!-- One continuous accent-colored light profile. A single radial falloff
           avoids the concentric-ring look of separately-sized glow layers. -->
      <radialGradient id="visitor-light" cx="50%" cy="50%" r="50%">
        {#each VISITOR_LIGHT_STOPS as stop}
          <stop
            offset={`${stop.offset}%`}
            stop-color="var(--accent-strong)"
            stop-opacity={stop.opacity}
          />
        {/each}
      </radialGradient>
    </defs>

    <g {transform}>
      {#each WORLD_COPIES as copy}
        <g transform={`translate(${copy * WIDTH} 0)`}>
          <path class="map-land" d={WORLD_MAP_PATH} />
          <path
            class="map-country-border"
            d={WORLD_INTERNAL_BORDERS_PATH}
          />

          {#each projectedLocations as location}
            <g class="map-light">
              <circle
                class="map-light-visual"
                cx={location.x}
                cy={location.y}
                r={lightRadius(location.count, zoom)}
              />
              <circle
                class="map-light-hit"
                cx={location.x}
                cy={location.y}
                r={hitRadius(zoom)}
              />
            </g>
          {/each}
        </g>
      {/each}
    </g>
  </svg>

  <div class="map-controls" role="group" aria-label="Map controls">
    <button type="button" aria-label="Zoom in" on:click={() => zoomByDistanceRatio(1 / 1.5)}>
      +
    </button>
    <button type="button" aria-label="Zoom out" on:click={() => zoomByDistanceRatio(1.5)}>
      −
    </button>
    <button type="button" on:click={() => fitLocations(false)}>Fit</button>
  </div>

  {#if tooltipVisible}
    <div
      class="map-tooltip"
      style={`left:${tooltipX}px;top:${tooltipY}px;`}
      aria-hidden="true"
    >{tooltipText}</div>
  {/if}
</div>

<style>
  .map-tooltip {
    position: absolute;
    z-index: 2;
    max-width: min(17rem, calc(100% - 2rem));
    padding: 0.38rem 0.5rem;
    border: 1px solid var(--line);
    background: var(--bg);
    color: var(--text);
    font-size: 0.72rem;
    line-height: 1.35;
    transform: translate(0.7rem, calc(-100% - 0.7rem));
    pointer-events: none;
  }
</style>
