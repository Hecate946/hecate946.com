<script lang="ts">
  import { onMount } from 'svelte';
  import { withBase } from '@/lib/paths';
  import type { HallwayScene } from './hallway-scene';
  import type { PaintingSpec } from './hallway-paintings';
  import { wallDestinations } from './wall-config';

  export let active = true;

  const destinations = wallDestinations;
  const HALLWAY_LOOP_DEPTH = 5_760;
  const PAINTING_SPACING = HALLWAY_LOOP_DEPTH / destinations.length;
  const PAINTING_START = 700;
  const PAINTING_BEHIND_ALLOWANCE = 360;
  const DRAG_THRESHOLD = 8;
  const WHEEL_SCALE = 1.05;
  const POINTER_SCALE = 1.3;
  const IDLE_DRIFT_SPEED = 74;
  const DIRECTION_THRESHOLD = 42;
  const INERTIA_TIME_CONSTANT = 0.72;
  const MAX_MANUAL_SPEED = 2_500;
  /** Doors swing, then the camera walks through. One timeline, two beats. */
  const OPENING_DURATION = 1_900;
  const SWING_FRACTION = 0.46;
  const DOLLY_DELAY = 0.3;
  /** Fixed architectural size until the viewport is genuinely too small. */
  const DOOR_DESIGN_HEIGHT = 680;
  const DOOR_ASPECT = 0.5385;
  const DOOR_VIEWPORT_GUTTER = 24;
  const DOOR_TOP_GAP = 16;

  type SceneMode = 'entrance' | 'opening' | 'hallway';
  type GestureAxis = 'pending' | 'horizontal' | 'vertical';

  const paintings = destinations.map((destination, index) => ({
    destination,
    index,
    side: index % 2 === 0 ? ('left' as const) : ('right' as const),
    z: PAINTING_START + PAINTING_SPACING * index,
    indexLabel: String(index + 1).padStart(2, '0'),
  }));

  /** The renderer takes the widest source; these are all small webp files. */
  const paintingSpecs: PaintingSpec[] = paintings.map((painting) => ({
    id: painting.destination.id,
    label: painting.destination.label,
    indexLabel: painting.indexLabel,
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
  let doorAnchor: HTMLElement;
  let floorSeamProbe: HTMLElement;
  let hallway: HallwayScene | null = null;
  let destinationLinks: HTMLAnchorElement[] = [];
  let hoveredPainting = -1;
  let mode: SceneMode = 'entrance';
  let cameraZ = 0;
  let velocity = 0;
  let driftDirection = 1;
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
  let openingStarted = 0;
  let doorOpen = 0;
  let entryDistance = 0;
  let doorRect = { left: 0, top: 0, width: 0, height: 0 };
  let programmatic = false;
  let programmaticStart = 0;
  let programmaticDelta = 0;
  let programmaticStarted = 0;
  let programmaticDuration = 0;
  let programmaticResolve: (() => void) | null = null;
  let lastRenderedCameraZ = Number.NaN;
  let mounted = false;
  let reducedMotion = false;

  function modulo(value: number, period: number) {
    return ((value % period) + period) % period;
  }

  function smoothstep(edge0: number, edge1: number, value: number) {
    const progress = Math.max(
      0,
      Math.min(1, (value - edge0) / (edge1 - edge0)),
    );
    return progress * progress * (3 - 2 * progress);
  }

  function easeOutCubic(progress: number) {
    return 1 - Math.pow(1 - progress, 3);
  }

  function easeInOutCubic(progress: number) {
    return progress < 0.5
      ? 4 * progress * progress * progress
      : 1 - Math.pow(-2 * progress + 2, 3) / 2;
  }

  function clamp01(value: number) {
    return Math.min(1, Math.max(0, value));
  }

  function markInteracted() {
    hasInteracted = true;
  }

  function updateDriftDirection(nextVelocity: number) {
    if (nextVelocity > DIRECTION_THRESHOLD) driftDirection = 1;
    else if (nextVelocity < -DIRECTION_THRESHOLD) driftDirection = -1;
  }

  function getDriftVelocity() {
    if (mode !== 'hallway' || isPaused || reducedMotion) return 0;
    return driftDirection * IDLE_DRIFT_SPEED;
  }

  type RoomCameraWindow = Window & {
    __hecateRoomCameraX?: number;
    __hecateSetRoomCameraX?: (cameraX: number) => void;
  };

  function resetSharedBackdrop() {
    const roomWindow = window as RoomCameraWindow;
    roomWindow.__hecateRoomCameraX = 0;
    roomWindow.__hecateSetRoomCameraX?.(0);
  }

  function renderCamera(force = false) {
    if (!force && cameraZ === lastRenderedCameraZ && !programmatic) return;

    hallway?.setDoor(doorOpen, mode !== 'hallway');
    hallway?.render(cameraZ);
    lastRenderedCameraZ = cameraZ;
  }

  function layoutDoorAnchor() {
    if (!stage || !doorAnchor || !floorSeamProbe) return;

    const stageRect = stage.getBoundingClientRect();
    const floorTop = floorSeamProbe.getBoundingClientRect().top - stageRect.top;
    const headerBottom = Math.max(
      0,
      (document.querySelector('.site-header')?.getBoundingClientRect().bottom ??
        stageRect.top) - stageRect.top,
    );
    const availableHeight = Math.max(1, floorTop - headerBottom - DOOR_TOP_GAP);
    const availableWidth = Math.max(1, stageRect.width - DOOR_VIEWPORT_GUTTER);
    const height = Math.min(
      DOOR_DESIGN_HEIGHT,
      availableHeight,
      availableWidth / DOOR_ASPECT,
    );
    const width = height * DOOR_ASPECT;

    doorAnchor.style.width = `${width}px`;
    doorAnchor.style.height = `${height}px`;
    doorAnchor.style.top = `${floorTop - height}px`;
    document.body.style.setProperty(
      '--home-door-cutout-half',
      `${width / 2}px`,
    );
  }

  function refreshRenderState() {
    layoutDoorAnchor();
    hallway?.resize();

    if (hallway) {
      entryDistance = hallway.getEntryDistance();
      // At the entrance the camera stands back from the door by exactly the
      // distance it will travel, so the corridor lands on its usual origin
      // the moment we arrive and the paintings keep their spacing.
      if (mode === 'entrance') cameraZ = -entryDistance;
    }

    lastRenderedCameraZ = Number.NaN;
    renderCamera(true);
    if (hallway && mode === 'entrance') doorRect = hallway.getDoorRect();
  }

  function ensureAnimationLoop() {
    if (rafId || document.hidden || !active || mode === 'entrance') return;
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

    resetSharedBackdrop();
    lastFrame = performance.now();
    refreshRenderState();
    if (mode !== 'entrance') ensureAnimationLoop();
  }

  $: (active, syncActiveState());

  function enterHallway() {
    if (mode !== 'entrance') return;
    markInteracted();
    isPaused = false;
    driftDirection = 1;

    if (reducedMotion) {
      mode = 'hallway';
      cameraZ = 0;
      velocity = 0;
      doorOpen = 1;
      refreshRenderState();
      return;
    }

    openingStarted = performance.now();
    lastFrame = openingStarted;
    mode = 'opening';
    velocity = 0;
    ensureAnimationLoop();
  }

  function toggleMotion() {
    if (mode !== 'hallway') return;
    isPaused = !isPaused;

    if (isPaused) {
      velocity = 0;
      renderCamera(true);
      return;
    }

    velocity = driftDirection * IDLE_DRIFT_SPEED;
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
    if (mode !== 'hallway') return;
    cancelCameraAnimation();
    markInteracted();
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
    if (mode !== 'hallway') return Promise.resolve();
    cancelCameraAnimation();
    programmaticStart = cameraZ;
    programmaticDelta = nearestDelta(targetZ);
    programmaticStarted = performance.now();
    programmaticDuration = reducedMotion ? 1 : Math.max(1, duration);
    programmatic = true;
    velocity = 0;
    ensureAnimationLoop();

    return new Promise<void>((resolve) => {
      programmaticResolve = resolve;
    });
  }

  function focusDestination(event: FocusEvent, index: number) {
    if (dragging || mode !== 'entrance') markInteracted();
    if (dragging || mode !== 'hallway') return;
    if (
      !(event.currentTarget instanceof HTMLElement) ||
      !event.currentTarget.matches(':focus-visible')
    )
      return;

    markInteracted();
    const painting = paintings[index];
    if (painting) void animateCameraTo(painting.z - 400, 640);
  }

  function updateHover(event: PointerEvent) {
    if (!hallway || mode !== 'hallway' || dragging) return;
    const next = hallway.pickPainting(event.clientX, event.clientY);
    if (next === hoveredPainting) return;
    hoveredPainting = next;
    hallway.setHoveredPainting(next);
    renderCamera(true);
  }

  function enterDestination(event: PointerEvent) {
    if (!hallway || mode !== 'hallway') return;
    if (dragDistance > DRAG_THRESHOLD) return;

    const index = hallway.pickPainting(event.clientX, event.clientY);
    if (index < 0) return;

    markInteracted();
    // Click the real anchor rather than assigning location: that keeps
    // Astro's client router, prefetching, and history exactly as they were.
    destinationLinks[index]?.click();
  }

  function onWheel(event: WheelEvent) {
    if (mode !== 'hallway') return;
    event.preventDefault();

    const dominantDelta =
      Math.abs(event.deltaY) >= Math.abs(event.deltaX)
        ? event.deltaY
        : event.deltaX;
    const normalized = Math.max(-210, Math.min(210, dominantDelta));
    moveBy(normalized * WHEEL_SCALE);
    velocity = Math.max(
      -MAX_MANUAL_SPEED,
      Math.min(MAX_MANUAL_SPEED, normalized * 9),
    );
    updateDriftDirection(velocity);
  }

  function onPointerDown(event: PointerEvent) {
    if (mode !== 'hallway' || event.button !== 0) return;
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
    markInteracted();
    ensureAnimationLoop();
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
    }

    event.preventDefault();
    const movement = gestureAxis === 'vertical' ? -deltaY : -deltaX;
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

    const sampledVelocity = Math.max(
      -MAX_MANUAL_SPEED,
      Math.min(MAX_MANUAL_SPEED, (worldMovement / elapsedMs) * 1000),
    );
    velocity = velocity * 0.58 + sampledVelocity * 0.42;
    updateDriftDirection(velocity);
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
    if (mode !== 'entrance') ensureAnimationLoop();
  }

  function restoreHallwayAfterHistoryNavigation() {
    cancelCameraAnimation();
    dragging = false;
    activePointerId = null;
    gestureAxis = 'pending';
    dragDistance = 0;
    lastFrame = performance.now();
    velocity = getDriftVelocity();
    resetSharedBackdrop();
    refreshRenderState();
    if (mode !== 'entrance') ensureAnimationLoop();
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
      moveBy(event.shiftKey ? 420 : 170);
      velocity = event.shiftKey ? 720 : 380;
      updateDriftDirection(velocity);
    } else if (
      event.key === 'ArrowUp' ||
      event.key === 'ArrowLeft' ||
      key === 'w' ||
      key === 'a'
    ) {
      event.preventDefault();
      moveBy(event.shiftKey ? -420 : -170);
      velocity = event.shiftKey ? -720 : -380;
      updateDriftDirection(velocity);
    } else if (event.key === 'Home') {
      event.preventDefault();
      markInteracted();
      void animateCameraTo(0, 520);
    }
  }

  function animationFrame(now: number) {
    rafId = 0;
    if (!active || mode === 'entrance') return;

    const elapsedMs = lastFrame
      ? Math.min(50, Math.max(0, now - lastFrame))
      : 16.667;
    const dt = elapsedMs / 1000;
    lastFrame = now;

    if (mode === 'opening') {
      const progress = clamp01((now - openingStarted) / OPENING_DURATION);

      // The leaves finish swinging before the walk-through completes, and
      // the camera starts moving while they are still opening -- the overlap
      // is what makes it read as walking in rather than two cutscenes.
      doorOpen = easeOutCubic(clamp01(progress / SWING_FRACTION));
      const dolly = easeInOutCubic(
        clamp01((progress - DOLLY_DELAY) / (1 - DOLLY_DELAY)),
      );
      cameraZ = entryDistance * (dolly - 1);

      if (progress >= 1) {
        mode = 'hallway';
        cameraZ = 0;
        doorOpen = 1;
        velocity = IDLE_DRIFT_SPEED;
      }
    } else if (programmatic) {
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
      mode === 'hallway' &&
      (isPaused || reducedMotion) &&
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

    // Three.js is loaded off the critical path: the entrance renders first and
    // the corridor attaches a moment later, behind the still-closed door.
    let released = false;
    void (async () => {
      try {
        const { createHallwayScene } = await import('./hallway-scene');
        if (released) return;
        hallway = createHallwayScene({
          canvas: hallwayCanvas,
          viewport: hallwayViewport,
          probe: hallwayProbe,
          frameProbe: hallwayFrameProbe,
          doorAnchor,
          paintings: paintingSpecs,
          onReady: () => renderCamera(true),
        });
        refreshRenderState();
      } catch (error) {
        // No WebGL: the scene's own background stands in for the corridor and
        // every painting, link, and control keeps working.
        console.warn('Hallway renderer unavailable', error);
      }
    })();

    // The corridor's palette comes from the theme, so repaint on a mode swap.
    const themeObserver = new MutationObserver(() => {
      hallway?.refreshTheme();
      renderCamera(true);
    });
    themeObserver.observe(document.documentElement, {
      attributeFilter: ['data-theme'],
    });

    resetSharedBackdrop();
    refreshRenderState();

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
      themeObserver.disconnect();
      released = true;
      document.body.style.removeProperty('--home-door-cutout-half');
      hallway?.dispose();
      hallway = null;
    };
  });
</script>

<section
  bind:this={stage}
  class:wall-stage--entrance={mode === 'entrance'}
  class:wall-stage--opening={mode === 'opening'}
  class:wall-stage--hallway={mode === 'hallway'}
  class:wall-stage--dragging={dragging}
  class:wall-stage--interacted={hasInteracted}
  class:wall-stage--inactive={!active}
  class="wall-stage wall-stage--home wall-room-host"
  aria-hidden={!active ? 'true' : undefined}
  aria-label={mode === 'entrance'
    ? 'Entrance to Cyrus Asasi portfolio'
    : 'Interactive portfolio hallway'}
>
  <h1 class="visually-hidden">Cyrus Asasi</h1>

  <span bind:this={hallwayProbe} class="hallway-metrics" aria-hidden="true">
    <span bind:this={hallwayFrameProbe} class="hallway-metrics__frame"></span>
  </span>
  <span bind:this={floorSeamProbe} class="home-floor-seam-probe"></span>
  <span bind:this={doorAnchor} class="home-door-anchor"></span>

  <div
    bind:this={hallwayViewport}
    class="hallway-scene"
    aria-hidden={mode === 'entrance' ? 'true' : undefined}
  >
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

  {#if mode !== 'hallway'}
    <button
      class="home-entrance-hit"
      type="button"
      style={`left:${doorRect.left}px;top:${doorRect.top}px;width:${doorRect.width}px;height:${doorRect.height}px;`}
      aria-label="Open the doors and enter the portfolio hallway"
      disabled={mode !== 'entrance'}
      onclick={enterHallway}
    ></button>
  {/if}

  <p class="wall-navigation-hint" aria-live="polite">
    {mode === 'entrance'
      ? 'Click the doors to enter'
      : 'Scroll or drag to explore · click a painting'}
  </p>

  {#if mode === 'hallway'}
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
