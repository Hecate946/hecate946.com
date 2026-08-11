<script lang="ts">
  import { onMount } from 'svelte';
  import WallWindow from './WallWindow.svelte';
  import { playNavigationSound } from '@/lib/site-sound';
  import {
    WALL_LOOP_WIDTH,
    WALL_START_X,
    wallDestinations,
    type WallDestination,
  } from './wall-config';

  const loopCopies = [-1, 0, 1] as const;
  const DRAG_THRESHOLD = 7;
  const WHEEL_SCALE = 0.82;
  const IDLE_DRIFT_SPEED = 30; // pixels per second
  const WALL_PATTERN_WIDTH = 96;
  const FLOOR_TILE_SIZE = 120;
  const DIRECTION_THRESHOLD = 36;
  const INERTIA_TIME_CONSTANT = 0.78;
  const MAX_MANUAL_SPEED = 2_400;

  let stage: HTMLElement;
  let wallWorld: HTMLElement;
  let wallTexture: HTMLElement;
  let floorSurface: HTMLElement;
  let cameraX = WALL_START_X;
  let velocity = 0;
  let driftDirection = 1;
  let isPaused = false;
  let dragging = false;
  let activePointerId: number | null = null;
  let pointerX = 0;
  let pointerOriginX = 0;
  let pointerOriginY = 0;
  let lastPointerTime = 0;
  let gestureAxis: 'pending' | 'horizontal' | 'vertical' = 'pending';
  let dragDistance = 0;
  let hasInteracted = false;
  let enteringId: string | null = null;
  let rafId = 0;
  let lastFrame = 0;
  let programmatic = false;
  let cameraAnimationToken = 0;
  let lastRenderedCameraX = Number.NaN;
  let lastLoopBase = Number.NaN;
  let renderDevicePixelRatio = 1;

  const stageStyle = `--loop-width: ${WALL_LOOP_WIDTH}px;`;

  function modulo(value: number, period: number) {
    return ((value % period) + period) % period;
  }

  function loopBase(position: number) {
    return Math.floor(position / WALL_LOOP_WIDTH) * WALL_LOOP_WIDTH;
  }

  function markInteracted() {
    hasInteracted = true;
  }


  function updateDriftDirection(nextVelocity: number) {
    if (nextVelocity > DIRECTION_THRESHOLD) driftDirection = 1;
    else if (nextVelocity < -DIRECTION_THRESHOLD) driftDirection = -1;
  }

  function getDriftVelocity() {
    // The homepage wall is an explicit interactive feature, so its own Play /
    // Pause control is the single source of truth for idle motion. Relying on
    // the OS reduced-motion media query here could leave the wall permanently
    // stationary while the control still appeared to be in its playing state.
    return isPaused ? 0 : driftDirection * IDLE_DRIFT_SPEED;
  }

  function periodicOffset(position: number, period: number) {
    return -modulo(position, period);
  }

  function snapToDevicePixel(value: number) {
    return Math.round(value * renderDevicePixelRatio) / renderDevicePixelRatio;
  }

  function refreshRenderDevicePixelRatio() {
    renderDevicePixelRatio = Math.max(1, window.devicePixelRatio || 1);
    lastRenderedCameraX = Number.NaN;
    lastLoopBase = Number.NaN;
    renderCamera(true);
  }

  function renderCamera(force = false) {
    // Keep physics fully precise, but quantize only the rendered camera to
    // physical pixels so detailed paintings do not shimmer between sampling
    // phases during slow movement.
    const renderedCameraX = snapToDevicePixel(cameraX);
    if (!force && renderedCameraX === lastRenderedCameraX) return;

    // The camera itself never wraps. Instead, the three identical destination
    // strips are recycled around the current lap. This avoids the large
    // compositor transform jump that used to happen once per full rotation.
    const nextLoopBase = loopBase(renderedCameraX);
    if (force || nextLoopBase !== lastLoopBase) {
      wallWorld?.style.setProperty('--loop-base', `${nextLoopBase}px`);
      lastLoopBase = nextLoopBase;
    }

    wallWorld?.style.setProperty('transform', `translate3d(${-renderedCameraX}px, 0, 0)`);

    // Only genuinely repeating texture layers are wrapped at their own small
    // periods. Static wall/floor lighting stays fixed, so these resets are
    // visually exact and cannot create a one-frame lighting jump.
    wallTexture?.style.setProperty(
      'transform',
      `translate3d(${periodicOffset(renderedCameraX, WALL_PATTERN_WIDTH)}px, 0, 0)`,
    );
    floorSurface?.style.setProperty(
      'transform',
      `translate3d(${periodicOffset(renderedCameraX, FLOOR_TILE_SIZE)}px, 0, 0) rotateX(64deg) scaleY(1.28) translateY(14%)`,
    );

    lastRenderedCameraX = renderedCameraX;
  }

  function toggleMotion() {
    isPaused = !isPaused;

    if (isPaused) {
      velocity = 0;
      return;
    }

    // Resume immediately instead of waiting for the inertia easing to crawl
    // back toward the idle speed. Resetting the frame clock also prevents a
    // stale elapsed interval after a backgrounded tab or an Astro page swap.
    velocity = driftDirection * IDLE_DRIFT_SPEED;
    lastFrame = performance.now();
  }

  function cancelCameraAnimation() {
    cameraAnimationToken += 1;
    programmatic = false;
  }

  function moveBy(amount: number) {
    if (enteringId) return;
    cancelCameraAnimation();
    markInteracted();
    cameraX += amount;
  }

  function nearestDelta(targetX: number) {
    let delta = targetX - modulo(cameraX, WALL_LOOP_WIDTH);
    if (delta > WALL_LOOP_WIDTH / 2) delta -= WALL_LOOP_WIDTH;
    if (delta < -WALL_LOOP_WIDTH / 2) delta += WALL_LOOP_WIDTH;
    return delta;
  }

  function animateCameraTo(targetX: number, duration = 460) {
    return new Promise<void>((resolve) => {
      const start = cameraX;
      const delta = nearestDelta(targetX);
      const started = performance.now();
      const token = ++cameraAnimationToken;
      programmatic = true;
      velocity = 0;

      const step = (now: number) => {
        if (token !== cameraAnimationToken) {
          resolve();
          return;
        }

        const progress = Math.min(1, (now - started) / duration);
        const eased = 1 - Math.pow(1 - progress, 4);
        cameraX = start + delta * eased;

        if (progress < 1) {
          requestAnimationFrame(step);
          return;
        }

        programmatic = false;
        velocity = getDriftVelocity();
        resolve();
      };

      requestAnimationFrame(step);
    });
  }

  function focusDestination(_destination: WallDestination) {
    if (dragging) return;
    markInteracted();
  }

  function enterDestination(event: MouseEvent, _destination: WallDestination) {
    // A drag must never accidentally activate the underlying link. For a real
    // click, however, leave the anchor alone so Astro's ClientRouter handles
    // it exactly like the links in the navbar. A hard location.assign() reload
    // destroyed the persistent music element and cut off in-flight SFX.
    if (dragDistance > DRAG_THRESHOLD) {
      event.preventDefault();
      return;
    }

    // Wall links opt out of the global capture-phase sound handler because
    // that handler fires before this component can distinguish a click from a
    // drag. Trigger the same redirect SFX only after the gesture is confirmed
    // as a real navigation click.
    playNavigationSound('redirect');
    markInteracted();
    clearPointerDrag();
  }

  function onWheel(event: WheelEvent) {
    if (enteringId) return;

    // Vertical wheel/trackpad movement belongs to the page so the footer can
    // be reached naturally. Only a clearly horizontal gesture moves the wall.
    if (Math.abs(event.deltaX) <= Math.abs(event.deltaY) || Math.abs(event.deltaX) < 0.5) {
      return;
    }

    event.preventDefault();
    const normalized = Math.max(-190, Math.min(190, event.deltaX));

    moveBy(normalized * WHEEL_SCALE);
    velocity = Math.max(-MAX_MANUAL_SPEED, Math.min(MAX_MANUAL_SPEED, normalized * 8.5));
    updateDriftDirection(velocity);
  }

  function onPointerDown(event: PointerEvent) {
    if (enteringId || event.button !== 0) return;

    // Svelte 5 delegates event handlers while this scene also uses native
    // pointer listeners for low-latency dragging. Ignore the motion button at
    // the scene level so a tap/click can never be mistaken for the beginning
    // of a wall drag before the delegated button handler runs.
    if (event.target instanceof Element && event.target.closest('.wall-motion-toggle')) return;

    cancelCameraAnimation();
    dragging = true;
    activePointerId = event.pointerId;
    pointerX = event.clientX;
    pointerOriginX = event.clientX;
    pointerOriginY = event.clientY;
    lastPointerTime = event.timeStamp;
    gestureAxis = event.pointerType === 'mouse' ? 'horizontal' : 'pending';
    dragDistance = 0;
    velocity = 0;
    markInteracted();
  }

  function captureTouchPointer(event: PointerEvent) {
    if (event.pointerType === 'mouse' || !stage) return;
    try {
      if (!stage.hasPointerCapture(event.pointerId)) stage.setPointerCapture(event.pointerId);
    } catch {
      // Some older mobile browsers can throw if capture races pointercancel.
    }
  }

  function onPointerMove(event: PointerEvent) {
    if (!dragging || activePointerId !== event.pointerId || enteringId) return;

    const deltaX = event.clientX - pointerX;
    if (gestureAxis === 'pending') {
      const totalX = Math.abs(event.clientX - pointerOriginX);
      const totalY = Math.abs(event.clientY - pointerOriginY);
      if (Math.max(totalX, totalY) < 8) return;

      // Use hysteresis on touch. A mostly-horizontal swipe should not get
      // cancelled just because the finger wanders a few pixels vertically.
      if (totalY > totalX * 1.3) {
        gestureAxis = 'vertical';
        dragging = false;
        activePointerId = null;
        velocity = getDriftVelocity();
        return;
      }

      if (totalX <= totalY * 1.12) return;
      gestureAxis = 'horizontal';
      captureTouchPointer(event);
    }

    if (gestureAxis !== 'horizontal') return;
    event.preventDefault();

    const elapsedMs = Math.max(4, Math.min(50, event.timeStamp - lastPointerTime || 16.667));
    lastPointerTime = event.timeStamp;
    pointerX = event.clientX;
    dragDistance += Math.abs(deltaX);
    cameraX -= deltaX;

    const sampledVelocity = Math.max(
      -MAX_MANUAL_SPEED,
      Math.min(MAX_MANUAL_SPEED, (-deltaX / elapsedMs) * 1000),
    );
    velocity = velocity * 0.58 + sampledVelocity * 0.42;
    updateDriftDirection(velocity);
  }

  function clearPointerDrag(pointerId?: number) {
    if (pointerId !== undefined && activePointerId !== pointerId) return;

    const pointerToRelease = activePointerId;
    if (stage && pointerToRelease !== null) {
      try {
        if (stage.hasPointerCapture(pointerToRelease)) stage.releasePointerCapture(pointerToRelease);
      } catch {
        // Pointer capture may already have been released by the browser.
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
    // A mouse drag ends as soon as the pointer leaves the scene/viewport. This
    // prevents the wall from still feeling "attached" when the cursor returns.
    if (event.pointerType === 'mouse' && activePointerId === event.pointerId) {
      clearPointerDrag(event.pointerId);
    }
  }

  function onWindowBlur() {
    clearPointerDrag();
  }

  function onVisibilityChange() {
    if (document.hidden) {
      clearPointerDrag();
      return;
    }

    // rAF is suspended in background tabs. Reset the clock on return so a
    // stale frame interval can never feed a visible velocity jump.
    lastFrame = performance.now();
    lastRenderedCameraX = Number.NaN;
    renderCamera(true);
  }

  function restoreWallAfterHistoryNavigation() {
    cancelCameraAnimation();
    enteringId = null;
    programmatic = false;
    dragging = false;
    activePointerId = null;
    gestureAxis = 'pending';
    dragDistance = 0;
    lastFrame = performance.now();
    velocity = getDriftVelocity();
    lastRenderedCameraX = Number.NaN;
    lastLoopBase = Number.NaN;
    renderCamera(true);
  }

  function onKeydown(event: KeyboardEvent) {
    if (enteringId) return;

    const target = event.target;
    if (
      target instanceof HTMLInputElement ||
      target instanceof HTMLTextAreaElement ||
      target instanceof HTMLSelectElement ||
      target instanceof HTMLButtonElement ||
      target instanceof HTMLAnchorElement
    ) {
      return;
    }

    if (event.key === 'ArrowRight' || event.key.toLowerCase() === 'd') {
      event.preventDefault();
      moveBy(event.shiftKey ? 380 : 150);
      velocity = event.shiftKey ? 660 : 360;
      updateDriftDirection(velocity);
    } else if (event.key === 'ArrowLeft' || event.key.toLowerCase() === 'a') {
      event.preventDefault();
      moveBy(event.shiftKey ? -380 : -150);
      velocity = event.shiftKey ? -660 : -360;
      updateDriftDirection(velocity);
    } else if (event.key === 'Home') {
      event.preventDefault();
      markInteracted();
      void animateCameraTo(WALL_START_X, 420);
    }
  }


  function animationFrame(now: number) {
    const elapsedMs = lastFrame ? Math.min(50, Math.max(0, now - lastFrame)) : 16.667;
    const dt = elapsedMs / 1000;
    lastFrame = now;

    if (!dragging && !programmatic && !enteringId) {
      const driftVelocity = getDriftVelocity();
      const easing = 1 - Math.exp(-dt / INERTIA_TIME_CONSTANT);
      velocity += (driftVelocity - velocity) * easing;
      if (Math.abs(velocity) < 0.01 && driftVelocity === 0) velocity = 0;
      cameraX += velocity * dt;
    }

    // Render exactly once per display frame. Pointer/wheel events only update
    // world state; they no longer force separate Svelte/DOM updates.
    renderCamera();
    rafId = requestAnimationFrame(animationFrame);
  }

  function handleMotionTogglePointerDown(event: PointerEvent) {
    // Keep a button press from ever entering the wall-drag gesture.
    event.stopPropagation();
  }

  function handleMotionToggleClick(event: MouseEvent) {
    event.stopPropagation();
    toggleMotion();
  }

  onMount(() => {
    // Always begin in the moving state. The visible control is the only thing
    // that pauses this scene, which avoids browser/OS preference mismatches
    // producing a frozen wall with a nonfunctional-looking Pause button.
    isPaused = false;
    velocity = driftDirection * IDLE_DRIFT_SPEED;
    lastFrame = performance.now();
    refreshRenderDevicePixelRatio();

    stage.addEventListener('wheel', onWheel, { passive: false });
    stage.addEventListener('pointerdown', onPointerDown);
    stage.addEventListener('pointermove', onPointerMove);
    stage.addEventListener('pointerup', finishPointer);
    stage.addEventListener('pointercancel', finishPointer);
    stage.addEventListener('pointerleave', onPointerLeave);
    window.addEventListener('keydown', onKeydown);
    window.addEventListener('blur', onWindowBlur);
    window.addEventListener('resize', refreshRenderDevicePixelRatio, { passive: true });
    document.addEventListener('visibilitychange', onVisibilityChange);
    window.addEventListener('pageshow', restoreWallAfterHistoryNavigation);
    rafId = requestAnimationFrame(animationFrame);

    return () => {
      stage.removeEventListener('wheel', onWheel);
      stage.removeEventListener('pointerdown', onPointerDown);
      stage.removeEventListener('pointermove', onPointerMove);
      stage.removeEventListener('pointerup', finishPointer);
      stage.removeEventListener('pointercancel', finishPointer);
      stage.removeEventListener('pointerleave', onPointerLeave);
      window.removeEventListener('keydown', onKeydown);
      window.removeEventListener('blur', onWindowBlur);
      window.removeEventListener('resize', refreshRenderDevicePixelRatio);
      document.removeEventListener('visibilitychange', onVisibilityChange);
      window.removeEventListener('pageshow', restoreWallAfterHistoryNavigation);
      cancelAnimationFrame(rafId);
    };
  });

</script>

<section
  bind:this={stage}
  class:wall-stage--dragging={dragging}
  class:wall-stage--interacted={hasInteracted}
  class:wall-stage--entering={Boolean(enteringId)}
  class="wall-stage"
  style={stageStyle}
  aria-label="Infinite navigation wall. Drag or scroll horizontally, then select a lit window to enter a page."
>
  <h1 class="visually-hidden">Cyrus Asasi</h1>

  <div class="wall-stage__wall-surface" aria-hidden="true">
    <div
      bind:this={wallTexture}
      class="wall-stage__brick-pattern"
      style={`transform: translate3d(${periodicOffset(WALL_START_X, WALL_PATTERN_WIDTH)}px, 0, 0);`}
    ></div>
  </div>

  <div class="wall-stage__mortar-light" aria-hidden="true"></div>

  <div
    bind:this={wallWorld}
    class="wall-world"
    aria-label="Website destinations"
    style={`--loop-base: 0px; transform: translate3d(${-WALL_START_X}px, 0, 0);`}
  >
    {#each loopCopies as loopIndex}
      <div
        class="wall-loop"
        aria-hidden={loopIndex !== 0 ? 'true' : undefined}
        style={`--loop-offset: ${loopIndex * WALL_LOOP_WIDTH}px;`}
      >
        <div class="wall-loop__seam wall-loop__seam--a" aria-hidden="true"></div>
        <div class="wall-loop__seam wall-loop__seam--b" aria-hidden="true"></div>

        {#each wallDestinations as destination (destination.id)}
          <WallWindow
            {destination}
            keyboardAccessible={loopIndex === 0}
            entering={enteringId === destination.id}
            onFocus={focusDestination}
            onEnter={enterDestination}
          />
        {/each}
      </div>
    {/each}
  </div>

  <div class="wall-floor" aria-hidden="true">
    <div
      bind:this={floorSurface}
      class="wall-floor__surface"
      style={`transform: translate3d(${periodicOffset(WALL_START_X, FLOOR_TILE_SIZE)}px, 0, 0) rotateX(64deg) scaleY(1.28) translateY(14%);`}
    ></div>
  </div>

  <div class="wall-stage__vignette" aria-hidden="true"></div>
  <div class="wall-floor__baseboard" aria-hidden="true"></div>


  <button
    class="wall-motion-toggle"
    type="button"
    aria-label={isPaused ? 'Play wall animation' : 'Pause wall animation'}
    aria-pressed={isPaused}
    title={isPaused ? 'Play wall animation' : 'Pause wall animation'}
    onpointerdown={handleMotionTogglePointerDown}
    onclick={handleMotionToggleClick}
  >
    {#if isPaused}
      <svg class="wall-motion-toggle__icon" viewBox="0 0 24 24" aria-hidden="true">
        <path d="M8 5.5v13l10-6.5z" fill="currentColor" />
      </svg>
    {:else}
      <svg class="wall-motion-toggle__icon" viewBox="0 0 24 24" aria-hidden="true">
        <rect x="6.5" y="5" width="4" height="14" rx="1" fill="currentColor" />
        <rect x="13.5" y="5" width="4" height="14" rx="1" fill="currentColor" />
      </svg>
    {/if}
  </button>
</section>

<style>
  .wall-stage {
    --floor-height: clamp(5.2rem, 18%, 9.8rem);
    --baseboard-height: clamp(0.62rem, 1.15vw, 0.92rem);
    --window-width: 306px;
    --window-height: 378px;
    --window-offset-x: -153px;
    --window-offset-y: -189px;

    position: relative;
    isolation: isolate;
    width: 100%;
    height: 100%;
    min-height: 25rem;
    overflow: hidden;
    background: var(--wall-dark, #010101);
    color: var(--wall-light, #f4f1e9);
    cursor: grab;
    touch-action: pan-y;
    overscroll-behavior-x: contain;
    user-select: none;
  }

  .wall-stage--dragging {
    cursor: grabbing;
  }

  .wall-stage--entering {
    cursor: default;
  }

  .wall-stage__mortar-light {
    position: absolute;
    z-index: 2;
    inset: 0;
    background:
      radial-gradient(
        ellipse at 50% 8%,
        color-mix(in srgb, var(--wall-light, #f4f1e9) 2.2%, transparent),
        transparent 43%
      ),
      linear-gradient(
        180deg,
        color-mix(in srgb, var(--wall-light, #f4f1e9) 0.35%, transparent),
        transparent 12% 78%,
        rgb(0 0 0 / 24%)
      );
    pointer-events: none;
  }

  .wall-stage__wall-surface {
    position: absolute;
    z-index: 1;
    inset: 0;
    overflow: hidden;
    background-color: var(--wall-dark, #010101);
    background-image: linear-gradient(
      180deg,
      color-mix(in srgb, var(--wall-light, #f4f1e9) 0.7%, transparent),
      transparent 18%,
      rgb(0 0 0 / 14%) 82%,
      rgb(0 0 0 / 22%)
    );
    contain: layout paint style;
    box-shadow:
      inset 0 0 0 1px color-mix(in srgb, var(--wall-light, #f4f1e9) 0.5%, transparent),
      inset 0 -8rem 12rem rgb(0 0 0 / 32%);
    pointer-events: none;
  }

  .wall-stage__brick-pattern {
    position: absolute;
    inset: 0 auto 0 -96px;
    width: calc(100% + 192px);
    background: color-mix(in srgb, var(--wall-light, #f4f1e9) 22%, transparent);
    backface-visibility: hidden;
    content: '';
    -webkit-mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='96' height='48' viewBox='0 0 96 48'%3E%3Cg fill='%23fff'%3E%3Crect x='0' y='0' width='96' height='1'/%3E%3Crect x='0' y='24' width='96' height='1'/%3E%3Crect x='0' y='0' width='1' height='24'/%3E%3Crect x='48' y='0' width='1' height='24'/%3E%3Crect x='24' y='24' width='1' height='24'/%3E%3Crect x='72' y='24' width='1' height='24'/%3E%3C/g%3E%3C/svg%3E");
    -webkit-mask-position: 0 0;
    -webkit-mask-repeat: repeat;
    -webkit-mask-size: 96px 48px;
    mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='96' height='48' viewBox='0 0 96 48'%3E%3Cg fill='%23fff'%3E%3Crect x='0' y='0' width='96' height='1'/%3E%3Crect x='0' y='24' width='96' height='1'/%3E%3Crect x='0' y='0' width='1' height='24'/%3E%3Crect x='48' y='0' width='1' height='24'/%3E%3Crect x='24' y='24' width='1' height='24'/%3E%3Crect x='72' y='24' width='1' height='24'/%3E%3C/g%3E%3C/svg%3E");
    mask-position: 0 0;
    mask-repeat: repeat;
    mask-size: 96px 48px;
    pointer-events: none;
    will-change: transform;
  }

  .wall-stage__wall-surface::after {
    position: absolute;
    inset: 0;
    background: linear-gradient(180deg, transparent, rgb(0 0 0 / 16%) 78%, rgb(0 0 0 / 28%));
    content: '';
    pointer-events: none;
  }

  .wall-world {
    position: absolute;
    z-index: 4;
    top: 0;
    bottom: 0;
    left: 50%;
    width: 100%;
    backface-visibility: hidden;
    contain: layout style;
    /* The destination track is the only moving compositor layer. Frames and
       paintings stay untransformed inside it so they cannot drift against one
       another during slow subpixel motion. */
    will-change: transform;
  }

  .wall-floor {
    position: absolute;
    z-index: 5;
    right: 0;
    bottom: -0.2rem;
    left: 0;
    height: calc(var(--floor-height) + 0.2rem);
    overflow: hidden;
    perspective: 30rem;
    perspective-origin: 50% 0;
    contain: layout paint style;
    pointer-events: none;
  }

  .wall-floor__surface {
    position: absolute;
    top: -0.15rem;
    bottom: 0;
    left: -50%;
    width: 200%;
    background-color: var(--wall-dark, #050505);
    background-image: conic-gradient(
      from 90deg,
      var(--wall-light, #f4f1e9) 0 25%,
      var(--wall-dark, #050505) 0 50%,
      var(--wall-light, #f4f1e9) 0 75%,
      var(--wall-dark, #050505) 0 100%
    );
    background-position: 0 0;
    background-repeat: repeat;
    background-size: 120px 120px;
    backface-visibility: hidden;
    box-shadow:
      inset 0 1rem 1.5rem rgb(0 0 0 / 22%),
      inset 0 -1.1rem 2rem rgb(0 0 0 / 16%);
    transform-origin: 50% 0;
    will-change: transform;
  }

  .wall-floor::after {
    position: absolute;
    z-index: 1;
    inset: 0;
    background:
      linear-gradient(
        180deg,
        color-mix(in srgb, var(--wall-light, #f4f1e9) 8%, transparent),
        transparent 20% 76%,
        rgb(0 0 0 / 16%)
      ),
      linear-gradient(108deg, transparent 0 32%, color-mix(in srgb, var(--wall-light, #f4f1e9) 2.4%, transparent) 41%, transparent 50%) 0 0 / 30rem 100% repeat-x,
      linear-gradient(180deg, color-mix(in srgb, var(--wall-light, #f4f1e9) 1.2%, transparent), transparent 45%);
    content: '';
    opacity: 0.14;
    pointer-events: none;
  }

  .wall-floor__baseboard {
    position: absolute;
    z-index: 11;
    top: calc(100% - var(--floor-height) + var(--floor-top-offset, 0rem) - 0.14rem);
    right: -1px;
    left: -1px;
    height: calc(var(--baseboard-height) + 0.7rem);
    background: linear-gradient(
      180deg,
      color-mix(in srgb, var(--wall-baseboard, var(--wall-dark, #050505)) 92%, var(--wall-light, #f4f1e9)) 0%,
      color-mix(in srgb, var(--wall-baseboard, var(--wall-dark, #050505)) 96%, black) 38%,
      color-mix(in srgb, var(--wall-baseboard, var(--wall-dark, #050505)) 90%, black) 100%
    );
    border-top: 1px solid var(--wall-trim-line-soft, rgb(255 255 255 / 7%));
    border-bottom: 1px solid var(--wall-trim-shadow, rgb(0 0 0 / 42%));
    box-shadow:
      inset 0 1px 0 var(--wall-trim-highlight, rgb(255 255 255 / 4%)),
      inset 0 -1px 0 var(--wall-trim-shadow, rgb(0 0 0 / 42%)),
      0 0.75rem 1rem rgb(0 0 0 / 0.2);
  }

  .wall-floor__baseboard::before {
    position: absolute;
    top: -0.12rem;
    right: 0;
    left: 0;
    height: 0.38rem;
    background: linear-gradient(
      180deg,
      color-mix(in srgb, var(--wall-baseboard, var(--wall-dark, #050505)) 91%, var(--wall-light, #f4f1e9)) 0%,
      color-mix(in srgb, var(--wall-baseboard, var(--wall-dark, #050505)) 97%, var(--wall-light, #f4f1e9)) 30%,
      color-mix(in srgb, var(--wall-baseboard, var(--wall-dark, #050505)) 97%, black) 68%,
      color-mix(in srgb, var(--wall-baseboard, var(--wall-dark, #050505)) 90%, black) 100%
    );
    border: 1px solid var(--wall-trim-line-soft, rgb(255 255 255 / 6%));
    border-top-color: var(--wall-trim-line, rgb(255 255 255 / 10%));
    border-bottom-color: var(--wall-trim-shadow, rgb(0 0 0 / 42%));
    border-radius: 0;
    box-shadow:
      inset 0 1px 0 var(--wall-trim-highlight, rgb(255 255 255 / 4%)),
      0 0.08rem 0.14rem rgb(0 0 0 / 0.16);
    content: '';
  }

  .wall-floor__baseboard::after {
    position: absolute;
    top: 0.5rem;
    right: -1px;
    bottom: 0.18rem;
    left: -1px;
    background: linear-gradient(
      180deg,
      color-mix(in srgb, var(--wall-baseboard, var(--wall-dark, #050505)) 95%, var(--wall-light, #f4f1e9)) 0%,
      color-mix(in srgb, var(--wall-baseboard, var(--wall-dark, #050505)) 99%, black) 28%,
      color-mix(in srgb, var(--wall-baseboard, var(--wall-dark, #050505)) 93%, black) 100%
    );
    border: 1px solid var(--wall-trim-line-soft, rgb(255 255 255 / 6%));
    border-top-color: var(--wall-trim-line, rgb(255 255 255 / 10%));
    border-bottom-color: var(--wall-trim-shadow, rgb(0 0 0 / 42%));
    box-shadow: inset 0 1px 0 var(--wall-trim-highlight, rgb(255 255 255 / 4%));
    content: '';
  }

  .wall-loop {
    position: absolute;
    z-index: 3;
    inset: 0 auto 0 0;
    width: var(--loop-width);
    transform: translate3d(calc(var(--loop-base, 0px) + var(--loop-offset)), 0, 0);
    pointer-events: none;
  }

  .wall-loop :global(.wall-window) {
    pointer-events: auto;
  }

  .wall-loop__seam {
    position: absolute;
    bottom: calc(var(--floor-height) + 1.2rem);
    width: 1px;
    background: linear-gradient(180deg, transparent, color-mix(in srgb, var(--wall-light, #f4f1e9) 5%, transparent) 18% 83%, transparent);
    opacity: 0.32;
  }

  .wall-loop__seam--a {
    left: 10%;
    height: 41%;
  }

  .wall-loop__seam--b {
    left: 88%;
    height: 55%;
  }

  .wall-stage__vignette {
    position: absolute;
    z-index: 10;
    inset: 0;
    background:
      linear-gradient(90deg, rgb(0 0 0 / 48%), transparent 12% 88%, rgb(0 0 0 / 48%)),
      linear-gradient(180deg, rgb(0 0 0 / 20%), transparent 22% 78%, rgb(0 0 0 / 28%));
    pointer-events: none;
  }


  .wall-motion-toggle {
    position: absolute;
    z-index: 13;
    right: clamp(0.9rem, 2.4vw, 1.7rem);
    bottom: clamp(0.76rem, 2vw, 1.3rem);
    display: grid;
    width: 2.2rem;
    height: 2.2rem;
    place-items: center;
    padding: 0;
    border: 1px solid color-mix(in srgb, var(--wall-light, #f4f1e9) 24%, transparent);
    border-radius: 0.56rem;
    outline: 2px solid transparent;
    outline-offset: 1px;
    background: color-mix(in srgb, var(--wall-dark, #050505) 82%, transparent);
    color: color-mix(in srgb, var(--wall-light, #f4f1e9) 48%, transparent);
    cursor: pointer;
    opacity: 0.78;
    transition:
      opacity 160ms ease,
      border-color 160ms ease,
      color 160ms ease,
      outline-color 160ms ease;
  }

  .wall-motion-toggle:hover,
  .wall-motion-toggle:focus-visible {
    border-color: color-mix(in srgb, var(--wall-light, #f4f1e9) 34%, transparent);
    color: color-mix(in srgb, var(--wall-light, #f4f1e9) 70%, transparent);
    opacity: 1;
  }

  .wall-motion-toggle:focus-visible {
    outline: 1px solid currentColor;
    outline-offset: 0.18rem;
  }

  .wall-motion-toggle__icon {
    display: block;
    width: 1.15rem;
    height: 1.15rem;
    overflow: visible;
  }


  @media (min-height: 50rem) and (min-width: 40.001rem) {
    .wall-stage {
      --window-width: 340px;
      --window-height: 420px;
      --window-offset-x: -170px;
      --window-offset-y: -210px;
    }
  }

  @media (max-height: 42rem) and (min-width: 40.001rem) {
    .wall-stage {
      --window-width: 266px;
      --window-height: 328px;
      --window-offset-x: -133px;
      --window-offset-y: -164px;
    }
  }

  @media (max-width: 40rem) {
    .wall-stage {
      --floor-height: 6.4rem;
      --baseboard-height: 0.78rem;
      --floor-top-offset: -0.25rem;
      --window-width: 248px;
      --window-height: 308px;
      --window-offset-x: -124px;
      --window-offset-y: -154px;
    }

    .wall-floor {
      bottom: -0.55rem;
      height: calc(var(--floor-height) + 0.8rem);
    }

    .wall-floor__baseboard {
      height: calc(var(--baseboard-height) + 0.9rem);
    }


    .wall-motion-toggle {
      right: 0.75rem;
      bottom: 0.5rem;
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .wall-motion-toggle {
      transition: none;
    }
  }
</style>
