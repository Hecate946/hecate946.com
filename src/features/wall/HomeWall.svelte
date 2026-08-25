<script lang="ts">
  import { onMount } from 'svelte';
  import { withBase } from '@/lib/paths';
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
  const OPENING_DURATION = 980;

  type SceneMode = 'entrance' | 'opening' | 'hallway';
  type GestureAxis = 'pending' | 'horizontal' | 'vertical';

  const paintings = destinations.map((destination, index) => ({
    destination,
    index,
    side: index % 2 === 0 ? ('left' as const) : ('right' as const),
    z: PAINTING_START + PAINTING_SPACING * index,
    indexLabel: String(index + 1).padStart(2, '0'),
    srcset: destination.painting.sources
      .map((source) => `${withBase(source.src)} ${source.width}w`)
      .join(', '),
  }));

  let stage: HTMLElement;
  let hallwayWorld: HTMLElement;
  let leftWallTexture: HTMLElement;
  let rightWallTexture: HTMLElement;
  let floorSurface: HTMLElement;
  let paintingNodes: HTMLElement[] = [];
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
  let openingTimeout = 0;
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

  function collectSceneNodes() {
    if (!stage) return;
    paintingNodes = Array.from(
      stage.querySelectorAll<HTMLElement>('[data-hallway-painting]'),
    );
  }

  function renderCamera(force = false) {
    if (
      !hallwayWorld ||
      !leftWallTexture ||
      !rightWallTexture ||
      !floorSurface
    )
      return;
    if (!force && cameraZ === lastRenderedCameraZ && !programmatic) return;

    // Recycle only one 240px tile of travel. The geometry stays fixed while
    // these three compositor layers provide continuous forward motion without
    // ever exposing an edge or rasterizing another full-length corridor.
    const texturePhase = Math.round(modulo(cameraZ, 240) * 4) / 4;
    leftWallTexture.style.transform = `translate3d(${-texturePhase}px, 0, 0)`;
    rightWallTexture.style.transform = `translate3d(${texturePhase}px, 0, 0)`;
    floorSurface.style.backgroundPosition = `0 ${texturePhase}px, 0 0`;

    for (const [index, node] of paintingNodes.entries()) {
      const painting = paintings[index];
      if (!painting) continue;

      const distance =
        modulo(
          painting.z - cameraZ + PAINTING_BEHIND_ALLOWANCE,
          HALLWAY_LOOP_DEPTH,
        ) - PAINTING_BEHIND_ALLOWANCE;
      const nearOpacity = smoothstep(80, 240, distance);
      const farOpacity = Math.max(
        0.02,
        1 - smoothstep(2_650, HALLWAY_LOOP_DEPTH - 250, distance),
      );
      const depthOpacity = nearOpacity * farOpacity;
      const renderedDistance = Math.round(distance * 4) / 4;

      node.style.transform = `translate3d(var(--painting-side-x), -26px, ${-renderedDistance}px) rotateY(var(--painting-turn))`;
      node.style.opacity = depthOpacity.toFixed(3);
      node.style.pointerEvents =
        mode === 'hallway' && distance > 180 && distance < 2_450
          ? 'auto'
          : 'none';
    }

    lastRenderedCameraZ = cameraZ;
  }

  function refreshRenderState() {
    collectSceneNodes();
    lastRenderedCameraZ = Number.NaN;
    renderCamera(true);
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
    cameraZ = 0;
    velocity = reducedMotion ? 0 : 180;
    mode = reducedMotion ? 'hallway' : 'opening';
    lastFrame = performance.now();
    refreshRenderState();

    if (reducedMotion) return;

    ensureAnimationLoop();
    openingTimeout = window.setTimeout(() => {
      mode = 'hallway';
      velocity = IDLE_DRIFT_SPEED;
      lastFrame = performance.now();
      ensureAnimationLoop();
    }, OPENING_DURATION);
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

  function enterDestination(event: MouseEvent) {
    if (dragDistance > DRAG_THRESHOLD) {
      event.preventDefault();
      return;
    }

    markInteracted();
    clearPointerDrag();
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
      event.target.closest('.wall-corner-control, .hallway-painting')
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
    if (!dragging || activePointerId !== event.pointerId) return;

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
      const driftVelocity = mode === 'opening' ? 180 : getDriftVelocity();
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
    resetSharedBackdrop();
    collectSceneNodes();
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
      window.clearTimeout(openingTimeout);
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

  <div
    class="hallway-scene"
    aria-hidden={mode === 'entrance' ? 'true' : undefined}
  >
    <div bind:this={hallwayWorld} class="hallway-world">
      <div class="hallway-tunnel" aria-hidden="true">
        <div class="hallway-surface hallway-surface--left">
          <span
            bind:this={leftWallTexture}
            class="hallway-texture hallway-texture--wall"
          ></span>
          <span class="hallway-baseboard"></span>
        </div>
        <div class="hallway-surface hallway-surface--right">
          <span
            bind:this={rightWallTexture}
            class="hallway-texture hallway-texture--wall"
          ></span>
          <span class="hallway-baseboard"></span>
        </div>
        <div
          bind:this={floorSurface}
          class="hallway-surface hallway-surface--floor"
        ></div>
        <div class="hallway-surface hallway-surface--ceiling"></div>
      </div>

      {#each paintings as painting, index (painting.destination.id)}
        <a
          class:hallway-painting--left={painting.side === 'left'}
          class:hallway-painting--right={painting.side === 'right'}
          class="hallway-painting"
          href={withBase(painting.destination.href)}
          aria-label={`Enter ${painting.destination.label}`}
          data-hallway-painting={painting.destination.id}
          data-astro-prefetch
          draggable="false"
          onfocus={(event) => focusDestination(event, index)}
          onclick={enterDestination}
        >
          <span class="hallway-painting__frame" aria-hidden="true">
            <span class="hallway-painting__glass">
              <img
                class="hallway-painting__image"
                src={withBase(painting.destination.painting.src)}
                srcset={painting.srcset}
                sizes="(max-width: 40rem) 210px, 300px"
                alt=""
                width={painting.destination.painting.width}
                height={painting.destination.painting.height}
                draggable="false"
                decoding="async"
                loading={index === 0 ? 'eager' : 'lazy'}
                fetchpriority={index === 0 ? 'high' : 'low'}
              />
              <span class="hallway-painting__reflection"></span>
            </span>
          </span>
          <span class="hallway-painting__sill" aria-hidden="true"></span>
          <span class="hallway-painting__label">
            <span class="hallway-painting__index">{painting.indexLabel}</span>
            <span class="hallway-painting__name">
              {painting.destination.label}
            </span>
            <span class="hallway-painting__arrow" aria-hidden="true">
              <svg
                viewBox="0 0 16 16"
                width="16"
                height="16"
                aria-hidden="true"
                focusable="false"
              >
                <path d="M4 12 12 4M6.25 4H12v5.75" />
              </svg>
            </span>
          </span>
        </a>
      {/each}
    </div>

    <div class="hallway-depth-fog" aria-hidden="true"></div>
    <div class="hallway-vignette" aria-hidden="true"></div>
  </div>

  <div
    class="home-entrance"
    aria-hidden={mode === 'hallway' ? 'true' : undefined}
  >
    <div class="home-door-frame">
      <div class="home-doorway" aria-hidden="true"></div>
      <button
        class="home-door"
        type="button"
        aria-label="Open the door and enter the portfolio hallway"
        disabled={mode !== 'entrance'}
        onclick={enterHallway}
      >
        <span class="home-door__panel home-door__panel--top"></span>
        <span class="home-door__panel home-door__panel--middle"></span>
        <span class="home-door__panel home-door__panel--bottom"></span>
        <span class="home-door__number">946</span>
        <span class="home-door__knob" aria-hidden="true"></span>
      </button>
      <span class="home-door-frame__threshold" aria-hidden="true"></span>
    </div>
  </div>

  <p class="wall-navigation-hint" aria-live="polite">
    {mode === 'entrance'
      ? 'Click the door to enter'
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
