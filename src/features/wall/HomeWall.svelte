<script lang="ts">
  import { onMount } from 'svelte';
  import { withBase } from '@/lib/paths';
  import type { HallwayScene } from './hallway-scene';
  import type { PaintingSpec } from './hallway-paintings';
  import { HALLWAY_LOOP_DEPTH, wallDestinations } from './wall-config';

  export let active = true;

  const destinations = wallDestinations;
  // The lap length is shared with the WebGL gallery via wall-config so the
  // anchors and the geometry can never wrap at different points.
  const PAINTING_SPACING = HALLWAY_LOOP_DEPTH / destinations.length;
  const PAINTING_START = 700;
  const DRAG_THRESHOLD = 8;
  const WHEEL_SCALE = 1.15;
  const POINTER_SCALE = 1.4;
  // Paintings sit 2,880 units apart, so the drift has a long way to travel
  // between them; this is the cruising speed of the corridor when idle.
  const IDLE_DRIFT_SPEED = 265;
  const DIRECTION_THRESHOLD = 42;
  const INERTIA_TIME_CONSTANT = 0.72;
  const MAX_MANUAL_SPEED = 2_500;

  type GestureAxis = 'pending' | 'horizontal' | 'vertical';

  const paintings = destinations.map((destination, index) => ({
    destination,
    index,
    side: index % 2 === 0 ? ('left' as const) : ('right' as const),
    z: PAINTING_START + PAINTING_SPACING * index,
  }));

  const paintingSpecs: PaintingSpec[] = paintings.map((painting) => ({
    label: painting.destination.label,
    side: painting.side,
    z: painting.z,
    src: withBase(
      [...painting.destination.painting.sources].sort(
        (a, b) => b.width - a.width,
      )[0].src,
    ),
  }));

  let stage: HTMLElement;
  let hallwayViewport: HTMLElement;
  let hallwayCanvas: HTMLCanvasElement;
  let hallwayProbe: HTMLElement;
  let hallwayFrameProbe: HTMLElement;
  let floorSeamProbe: HTMLElement;
  let hallway: HallwayScene | null = null;
  let destinationLinks: HTMLAnchorElement[] = [];
  let hoveredPainting = -1;
  let sceneReady = false;
  let cameraZ = 0;
  let velocity = 0;
  let driftDirection = 1;
  let motionStarted = true;
  let isPaused = false;
  let dragging = false;
  let activePointerId: number | null = null;
  let pointerX = 0;
  let pointerY = 0;
  let pointerOriginX = 0;
  let pointerOriginY = 0;
  let lastPointerTime = 0;
  let gestureAxis: GestureAxis = 'pending';
  let dragDistance = 0;
  let hasInteracted = false;
  let rafId = 0;
  let lastFrame = 0;
  let programmatic = false;
  let programmaticStart = 0;
  let programmaticDelta = 0;
  let programmaticStarted = 0;
  let programmaticDuration = 0;
  let programmaticResolve: (() => void) | null = null;
  let lastRenderedCameraZ = Number.NaN;
  let mounted = false;
  let released = false;
  let reducedMotion = false;
  let revealFrame = 0;
  let themeRefreshFrame = 0;

  function modulo(value: number, period: number) {
    return ((value % period) + period) % period;
  }

  function markInteracted() {
    hasInteracted = true;
  }

  function beginUserMotion() {
    markInteracted();
    motionStarted = true;
    if (!reducedMotion) isPaused = false;
  }

  function updateDriftDirection(nextVelocity: number) {
    if (nextVelocity > DIRECTION_THRESHOLD) driftDirection = 1;
    else if (nextVelocity < -DIRECTION_THRESHOLD) driftDirection = -1;
  }

  function getDriftVelocity() {
    if (!motionStarted || isPaused || reducedMotion) return 0;
    return driftDirection * IDLE_DRIFT_SPEED;
  }

  function renderCamera(force = false) {
    if (!force && cameraZ === lastRenderedCameraZ && !programmatic) return;
    hallway?.render(cameraZ);
    lastRenderedCameraZ = cameraZ;
  }

  function refreshRenderState() {
    hallway?.resize();
    lastRenderedCameraZ = Number.NaN;
    renderCamera(true);
  }

  function scheduleThemeRefresh() {
    cancelAnimationFrame(themeRefreshFrame);
    themeRefreshFrame = requestAnimationFrame(() => {
      themeRefreshFrame = 0;
      // Responsive custom properties and the theme variables can change in
      // the same browser frame. Measure first, then repaint from the settled
      // palette so a resize cannot restore the previous wall colours.
      hallway?.resize();
      hallway?.refreshTheme();
      lastRenderedCameraZ = Number.NaN;
      renderCamera(true);
    });
  }

  function ensureAnimationLoop() {
    if (rafId || document.hidden || !active || !sceneReady) return;
    lastFrame = performance.now();
    rafId = requestAnimationFrame(animationFrame);
  }

  function syncActiveState() {
    if (!mounted) return;
    if (!active) {
      if (rafId) cancelAnimationFrame(rafId);
      rafId = 0;
      clearPointerDrag();
      return;
    }

    lastFrame = performance.now();
    refreshRenderState();
    if (Math.abs(velocity) > 0.01 || programmatic) ensureAnimationLoop();
  }

  $: (active, syncActiveState());

  function toggleMotion() {
    if (!sceneReady) return;
    isPaused = !isPaused;

    if (isPaused) {
      velocity = 0;
      renderCamera(true);
      return;
    }

    motionStarted = true;
    markInteracted();
    velocity = getDriftVelocity();
    ensureAnimationLoop();
  }

  function cancelCameraAnimation() {
    if (!programmatic) return;
    programmatic = false;
    const resolve = programmaticResolve;
    programmaticResolve = null;
    resolve?.();
  }

  function moveBy(amount: number) {
    if (!sceneReady) return;
    cancelCameraAnimation();
    cameraZ += amount;
    ensureAnimationLoop();
  }

  function nearestDelta(targetZ: number) {
    let delta = targetZ - modulo(cameraZ, HALLWAY_LOOP_DEPTH);
    if (delta > HALLWAY_LOOP_DEPTH / 2) delta -= HALLWAY_LOOP_DEPTH;
    if (delta < -HALLWAY_LOOP_DEPTH / 2) delta += HALLWAY_LOOP_DEPTH;
    return delta;
  }

  function animateCameraTo(targetZ: number, duration = 560) {
    if (!sceneReady) return Promise.resolve();
    cancelCameraAnimation();
    programmaticStart = cameraZ;
    programmaticDelta = nearestDelta(targetZ);
    programmaticStarted = performance.now();
    programmaticDuration = reducedMotion ? 1 : Math.max(1, duration);
    programmatic = true;
    velocity = 0;
    markInteracted();
    ensureAnimationLoop();

    return new Promise<void>((resolve) => {
      programmaticResolve = resolve;
    });
  }

  function focusDestination(event: FocusEvent, index: number) {
    if (dragging) markInteracted();
    if (dragging || !sceneReady) return;
    if (
      !(event.currentTarget instanceof HTMLElement) ||
      !event.currentTarget.matches(':focus-visible')
    )
      return;

    const painting = paintings[index];
    if (painting) void animateCameraTo(painting.z - 400, 640);
  }

  function updateHover(event: PointerEvent) {
    if (!hallway || !sceneReady || dragging) return;
    const next = hallway.pickPainting(event.clientX, event.clientY);
    if (next === hoveredPainting) return;
    hoveredPainting = next;
    hallway.setHoveredPainting(next);
    renderCamera(true);
  }

  function enterDestination(event: PointerEvent) {
    if (!hallway || !sceneReady || dragDistance > DRAG_THRESHOLD) return;
    const index = hallway.pickPainting(event.clientX, event.clientY);
    if (index < 0) return;

    markInteracted();
    destinationLinks[index]?.click();
  }

  function onWheel(event: WheelEvent) {
    if (!sceneReady) return;
    event.preventDefault();
    beginUserMotion();

    const dominantDelta =
      Math.abs(event.deltaY) >= Math.abs(event.deltaX)
        ? event.deltaY
        : event.deltaX;
    const normalized = Math.max(-210, Math.min(210, -dominantDelta));
    moveBy(normalized * WHEEL_SCALE);
    velocity = reducedMotion
      ? 0
      : Math.max(-MAX_MANUAL_SPEED, Math.min(MAX_MANUAL_SPEED, normalized * 9));
    updateDriftDirection(velocity);
    if (reducedMotion) renderCamera(true);
  }

  function onPointerDown(event: PointerEvent) {
    if (!sceneReady || event.button !== 0) return;
    if (
      event.target instanceof Element &&
      event.target.closest('.wall-corner-control')
    )
      return;

    cancelCameraAnimation();
    dragging = true;
    activePointerId = event.pointerId;
    pointerX = event.clientX;
    pointerY = event.clientY;
    pointerOriginX = event.clientX;
    pointerOriginY = event.clientY;
    lastPointerTime = event.timeStamp;
    gestureAxis = 'pending';
    dragDistance = 0;
    velocity = 0;
  }

  function capturePointer(event: PointerEvent) {
    if (!stage) return;
    try {
      if (!stage.hasPointerCapture(event.pointerId))
        stage.setPointerCapture(event.pointerId);
    } catch {
      // Pointer capture can race pointercancel on older mobile browsers.
    }
  }

  function onPointerMove(event: PointerEvent) {
    if (!dragging || activePointerId !== event.pointerId) {
      updateHover(event);
      return;
    }

    const deltaX = event.clientX - pointerX;
    const deltaY = event.clientY - pointerY;

    if (gestureAxis === 'pending') {
      const totalX = Math.abs(event.clientX - pointerOriginX);
      const totalY = Math.abs(event.clientY - pointerOriginY);
      if (Math.max(totalX, totalY) < 7) return;
      gestureAxis = totalY >= totalX ? 'vertical' : 'horizontal';
      capturePointer(event);
      beginUserMotion();
      ensureAnimationLoop();
    }

    event.preventDefault();
    const movement = gestureAxis === 'vertical' ? deltaY : deltaX;
    const elapsedMs = Math.max(
      4,
      Math.min(50, event.timeStamp - lastPointerTime || 16.667),
    );
    const worldMovement = movement * POINTER_SCALE;

    lastPointerTime = event.timeStamp;
    pointerX = event.clientX;
    pointerY = event.clientY;
    dragDistance += Math.hypot(deltaX, deltaY);
    cameraZ += worldMovement;

    const sampledVelocity = reducedMotion
      ? 0
      : Math.max(
          -MAX_MANUAL_SPEED,
          Math.min(MAX_MANUAL_SPEED, (worldMovement / elapsedMs) * 1000),
        );
    velocity = reducedMotion ? 0 : velocity * 0.58 + sampledVelocity * 0.42;
    updateDriftDirection(velocity);
    if (reducedMotion) renderCamera(true);
  }

  function clearPointerDrag(pointerId?: number) {
    if (pointerId !== undefined && activePointerId !== pointerId) return;

    const pointerToRelease = activePointerId;
    if (stage && pointerToRelease !== null) {
      try {
        if (stage.hasPointerCapture(pointerToRelease))
          stage.releasePointerCapture(pointerToRelease);
      } catch {
        // Capture may already have been released by the browser.
      }
    }

    dragging = false;
    activePointerId = null;
    gestureAxis = 'pending';
    window.setTimeout(() => {
      dragDistance = 0;
    }, 0);
  }

  function finishPointer(event: PointerEvent) {
    if (event.type === 'pointerup') enterDestination(event);
    clearPointerDrag(event.pointerId);
  }

  function onPointerLeave(event: PointerEvent) {
    if (event.pointerType === 'mouse' && activePointerId === event.pointerId)
      clearPointerDrag(event.pointerId);
  }

  function onWindowBlur() {
    clearPointerDrag();
  }

  function onVisibilityChange() {
    if (document.hidden) {
      clearPointerDrag();
      if (rafId) cancelAnimationFrame(rafId);
      rafId = 0;
      return;
    }

    lastFrame = performance.now();
    refreshRenderState();
    if (Math.abs(velocity) > 0.01 || programmatic) ensureAnimationLoop();
  }

  function restoreHallwayAfterHistoryNavigation() {
    cancelCameraAnimation();
    clearPointerDrag();
    lastFrame = performance.now();
    velocity = getDriftVelocity();
    refreshRenderState();
    if (Math.abs(velocity) > 0.01) ensureAnimationLoop();
  }

  function onKeydown(event: KeyboardEvent) {
    const target = event.target;
    if (
      target instanceof HTMLInputElement ||
      target instanceof HTMLTextAreaElement ||
      target instanceof HTMLSelectElement ||
      target instanceof HTMLButtonElement ||
      target instanceof HTMLAnchorElement
    )
      return;

    const key = event.key.toLowerCase();
    if (
      event.key === 'ArrowDown' ||
      event.key === 'ArrowRight' ||
      key === 's' ||
      key === 'd'
    ) {
      event.preventDefault();
      beginUserMotion();
      moveBy(event.shiftKey ? 420 : 170);
      velocity = reducedMotion ? 0 : event.shiftKey ? 720 : 380;
      updateDriftDirection(velocity);
    } else if (
      event.key === 'ArrowUp' ||
      event.key === 'ArrowLeft' ||
      key === 'w' ||
      key === 'a'
    ) {
      event.preventDefault();
      beginUserMotion();
      moveBy(event.shiftKey ? -420 : -170);
      velocity = reducedMotion ? 0 : event.shiftKey ? -720 : -380;
      updateDriftDirection(velocity);
    } else if (event.key === 'Home') {
      event.preventDefault();
      void animateCameraTo(0, 520);
    }
  }

  function animationFrame(now: number) {
    rafId = 0;
    if (!active || !sceneReady) return;

    const elapsedMs = lastFrame
      ? Math.min(50, Math.max(0, now - lastFrame))
      : 16.667;
    const dt = elapsedMs / 1000;
    lastFrame = now;

    if (programmatic) {
      const progress = Math.min(
        1,
        (now - programmaticStarted) / programmaticDuration,
      );
      const eased = 1 - Math.pow(1 - progress, 4);
      cameraZ = programmaticStart + programmaticDelta * eased;

      if (progress >= 1) {
        programmatic = false;
        velocity = getDriftVelocity();
        const resolve = programmaticResolve;
        programmaticResolve = null;
        resolve?.();
      }
    } else if (!dragging) {
      const driftVelocity = getDriftVelocity();
      const easing = 1 - Math.exp(-dt / INERTIA_TIME_CONSTANT);
      velocity += (driftVelocity - velocity) * easing;
      if (Math.abs(velocity) < 0.01 && driftVelocity === 0) velocity = 0;
      cameraZ += velocity * dt;
    }

    lastRenderedCameraZ = Number.NaN;
    renderCamera();

    if (
      (isPaused || reducedMotion || !motionStarted) &&
      !dragging &&
      !programmatic &&
      Math.abs(velocity) < 0.01
    ) {
      velocity = 0;
      return;
    }

    rafId = requestAnimationFrame(animationFrame);
  }

  function handleMotionTogglePointerDown(event: PointerEvent) {
    event.stopPropagation();
  }

  function handleMotionToggleClick(event: MouseEvent) {
    event.stopPropagation();
    toggleMotion();
  }

  onMount(() => {
    mounted = true;
    reducedMotion = window.matchMedia(
      '(prefers-reduced-motion: reduce)',
    ).matches;

    void (async () => {
      try {
        const { createHallwayScene } = await import('./hallway-scene');
        if (released) return;
        hallway = createHallwayScene({
          canvas: hallwayCanvas,
          viewport: hallwayViewport,
          probe: hallwayProbe,
          frameProbe: hallwayFrameProbe,
          floorSeam: floorSeamProbe,
          paintings: paintingSpecs,
          onReady: () => {
            if (released) return;
            renderCamera(true);
            cancelAnimationFrame(revealFrame);
            revealFrame = requestAnimationFrame(() => {
              if (released) return;
              sceneReady = true;
              velocity = getDriftVelocity();
              if (Math.abs(velocity) > 0.01) ensureAnimationLoop();
            });
          },
          onTextureUpdate: () => renderCamera(true),
        });
        refreshRenderState();
      } catch (error) {
        console.warn('Hallway renderer unavailable', error);
      }
    })();

    const themeObserver = new MutationObserver(scheduleThemeRefresh);
    themeObserver.observe(document.documentElement, {
      attributeFilter: ['data-theme'],
    });
    document.addEventListener('hecate:theme-change', scheduleThemeRefresh);

    stage.addEventListener('wheel', onWheel, { passive: false });
    stage.addEventListener('pointerdown', onPointerDown);
    stage.addEventListener('pointermove', onPointerMove);
    stage.addEventListener('pointerup', finishPointer);
    stage.addEventListener('pointercancel', finishPointer);
    stage.addEventListener('pointerleave', onPointerLeave);
    window.addEventListener('keydown', onKeydown);
    window.addEventListener('blur', onWindowBlur);
    window.addEventListener('resize', refreshRenderState, { passive: true });
    document.addEventListener('visibilitychange', onVisibilityChange);
    window.addEventListener('pageshow', restoreHallwayAfterHistoryNavigation);

    return () => {
      mounted = false;
      released = true;
      sceneReady = false;
      stage.removeEventListener('wheel', onWheel);
      stage.removeEventListener('pointerdown', onPointerDown);
      stage.removeEventListener('pointermove', onPointerMove);
      stage.removeEventListener('pointerup', finishPointer);
      stage.removeEventListener('pointercancel', finishPointer);
      stage.removeEventListener('pointerleave', onPointerLeave);
      window.removeEventListener('keydown', onKeydown);
      window.removeEventListener('blur', onWindowBlur);
      window.removeEventListener('resize', refreshRenderState);
      document.removeEventListener('visibilitychange', onVisibilityChange);
      window.removeEventListener(
        'pageshow',
        restoreHallwayAfterHistoryNavigation,
      );
      cancelAnimationFrame(rafId);
      cancelAnimationFrame(revealFrame);
      cancelAnimationFrame(themeRefreshFrame);
      themeObserver.disconnect();
      document.removeEventListener('hecate:theme-change', scheduleThemeRefresh);
      hallway?.dispose();
      hallway = null;
    };
  });
</script>

<section
  bind:this={stage}
  class:wall-stage--scene-ready={sceneReady}
  class:wall-stage--dragging={dragging}
  class:wall-stage--interacted={hasInteracted}
  class:wall-stage--inactive={!active}
  class="wall-stage wall-stage--home wall-stage--hallway wall-room-host"
  aria-hidden={!active ? 'true' : undefined}
  aria-label="Interactive portfolio hallway"
>
  <h1 class="visually-hidden">Cyrus Asasi</h1>

  <span bind:this={hallwayProbe} class="hallway-metrics" aria-hidden="true">
    <span bind:this={hallwayFrameProbe} class="hallway-metrics__frame"></span>
  </span>
  <span bind:this={floorSeamProbe} class="home-floor-seam-probe"></span>

  <div bind:this={hallwayViewport} class="hallway-scene" aria-hidden="true">
    <canvas bind:this={hallwayCanvas} class="hallway-canvas" aria-hidden="true"
    ></canvas>

    <nav class="hallway-destinations" aria-label="Portfolio destinations">
      <ul>
        {#each paintings as painting, index (painting.destination.id)}
          <li>
            <a
              bind:this={destinationLinks[index]}
              href={withBase(painting.destination.href)}
              data-astro-prefetch
              onfocus={(event) => focusDestination(event, index)}
            >
              {painting.destination.label}
            </a>
          </li>
        {/each}
      </ul>
    </nav>
  </div>

  <p class="wall-navigation-hint" aria-live="polite">
    Scroll or drag to explore · click a painting
  </p>

  {#if sceneReady && !reducedMotion}
    <button
      class="wall-motion-toggle wall-corner-control"
      type="button"
      aria-label={isPaused
        ? 'Play hallway animation'
        : 'Pause hallway animation'}
      aria-pressed={isPaused}
      title={isPaused ? 'Play hallway animation' : 'Pause hallway animation'}
      onpointerdown={handleMotionTogglePointerDown}
      onclick={handleMotionToggleClick}
    >
      {#if isPaused}
        <svg
          class="wall-corner-control__icon"
          viewBox="0 0 24 24"
          aria-hidden="true"
          width="24"
          height="24"
          focusable="false"
        >
          <path d="M8 5.5v13l10-6.5z" fill="currentColor" />
        </svg>
      {:else}
        <svg
          class="wall-corner-control__icon"
          viewBox="0 0 24 24"
          aria-hidden="true"
          width="24"
          height="24"
          focusable="false"
        >
          <rect
            x="6.5"
            y="5"
            width="4"
            height="14"
            rx="1"
            fill="currentColor"
          />
          <rect
            x="13.5"
            y="5"
            width="4"
            height="14"
            rx="1"
            fill="currentColor"
          />
        </svg>
      {/if}
    </button>
  {/if}
</section>
