<script lang="ts">
  import { onMount } from 'svelte';
  import WallWindow from './WallWindow.svelte';
  import {
    WALL_LOOP_WIDTH,
    WALL_START_X,
    wallDestinations,
  } from './wall-config';

  export let active = true;

  const destinations = wallDestinations;
  const loopWidth = WALL_LOOP_WIDTH;
  const startX = WALL_START_X;

  const loopCopies = [-1, 0, 1] as const;
  const DRAG_THRESHOLD = 7;
  const WHEEL_SCALE = 0.82;
  const IDLE_DRIFT_SPEED = 30; // pixels per second
  const DIRECTION_THRESHOLD = 36;
  const INERTIA_TIME_CONSTANT = 0.78;
  const MAX_MANUAL_SPEED = 2_400;

  let stage: HTMLElement;
  let wallWorld: HTMLElement;
  let cameraX = startX;
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
  let rafId = 0;
  let lastFrame = 0;
  let programmatic = false;
  let programmaticStart = 0;
  let programmaticDelta = 0;
  let programmaticStarted = 0;
  let programmaticDuration = 0;
  let programmaticResolve: (() => void) | null = null;
  let lastRenderedCameraX = Number.NaN;
  let lastLoopBase = Number.NaN;
  let mounted = false;

  $: stageStyle = `--loop-width: ${loopWidth}px;`;

  function modulo(value: number, period: number) {
    return ((value % period) + period) % period;
  }

  function loopBase(position: number) {
    return Math.floor(position / loopWidth) * loopWidth;
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

  type RoomCameraWindow = Window & {
    __hecateRoomCameraX?: number;
    __hecateSetRoomCameraX?: (cameraX: number) => void;
  };

  function syncSharedBackdrop(cameraX: number) {
    const roomWindow = window as RoomCameraWindow;
    roomWindow.__hecateRoomCameraX = cameraX;
    roomWindow.__hecateSetRoomCameraX?.(cameraX);
  }

  function renderCamera(force = false) {
    // Keep the camera fully subpixel-precise. Device-pixel quantization made
    // slow motion visibly step on 60/90/120Hz displays. The browser compositor
    // is better at sampling the transformed painting track continuously.
    const renderedCameraX = cameraX;
    if (!force && renderedCameraX === lastRenderedCameraX) return;

    // The camera itself never wraps. Instead, the three identical destination
    // strips are recycled around the current lap. This avoids a compositor
    // transform jump once per full rotation.
    const nextLoopBase = loopBase(renderedCameraX);
    if (force || nextLoopBase !== lastLoopBase) {
      wallWorld?.style.setProperty('--loop-base', `${nextLoopBase}px`);
      lastLoopBase = nextLoopBase;
    }

    wallWorld?.style.setProperty(
      'transform',
      `translate3d(${-renderedCameraX}px, 0, 0)`,
    );

    // The Home wall is the only place that drives the shared backdrop camera.
    // Every other room resets that backdrop to its static default phase.
    syncSharedBackdrop(renderedCameraX);

    lastRenderedCameraX = renderedCameraX;
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
    ensureAnimationLoop();
  }

  $: (active, syncActiveState());

  function refreshRenderState() {
    lastRenderedCameraX = Number.NaN;
    lastLoopBase = Number.NaN;
    renderCamera(true);
  }

  function ensureAnimationLoop() {
    if (rafId || document.hidden || !active) return;
    lastFrame = performance.now();
    rafId = requestAnimationFrame(animationFrame);
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
    cancelCameraAnimation();
    markInteracted();
    cameraX += amount;
    ensureAnimationLoop();
  }

  function nearestDelta(targetX: number) {
    let delta = targetX - modulo(cameraX, loopWidth);
    if (delta > loopWidth / 2) delta -= loopWidth;
    if (delta < -loopWidth / 2) delta += loopWidth;
    return delta;
  }

  function animateCameraTo(targetX: number, duration = 460) {
    cancelCameraAnimation();
    programmaticStart = cameraX;
    programmaticDelta = nearestDelta(targetX);
    programmaticStarted = performance.now();
    programmaticDuration = Math.max(1, duration);
    programmatic = true;
    velocity = 0;
    ensureAnimationLoop();

    return new Promise<void>((resolve) => {
      programmaticResolve = resolve;
    });
  }

  function focusDestination() {
    if (dragging) return;
    markInteracted();
  }

  function enterDestination(event: MouseEvent) {
    // A drag must never accidentally activate the underlying link. For a real
    // click, leave the anchor alone so Astro's ClientRouter handles navigation
    // exactly like the links in the navbar.
    if (dragDistance > DRAG_THRESHOLD) {
      event.preventDefault();
      return;
    }

    markInteracted();
    clearPointerDrag();
  }

  function onWheel(event: WheelEvent) {
    // Vertical wheel/trackpad movement belongs to the page so the footer can
    // be reached naturally. Only a clearly horizontal gesture moves the wall.
    if (
      Math.abs(event.deltaX) <= Math.abs(event.deltaY) ||
      Math.abs(event.deltaX) < 0.5
    ) {
      return;
    }

    event.preventDefault();
    const normalized = Math.max(-190, Math.min(190, event.deltaX));

    moveBy(normalized * WHEEL_SCALE);
    velocity = Math.max(
      -MAX_MANUAL_SPEED,
      Math.min(MAX_MANUAL_SPEED, normalized * 8.5),
    );
    updateDriftDirection(velocity);
  }

  function onPointerDown(event: PointerEvent) {
    if (event.button !== 0) return;

    // Svelte 5 delegates event handlers while this scene also uses native
    // pointer listeners for low-latency dragging. Ignore the motion button at
    // the scene level so a tap/click can never be mistaken for the beginning
    // of a wall drag before the delegated button handler runs.
    if (
      event.target instanceof Element &&
      event.target.closest('.wall-corner-control')
    )
      return;

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
    ensureAnimationLoop();
  }

  function captureTouchPointer(event: PointerEvent) {
    if (event.pointerType === 'mouse' || !stage) return;
    try {
      if (!stage.hasPointerCapture(event.pointerId))
        stage.setPointerCapture(event.pointerId);
    } catch {
      // Some older mobile browsers can throw if capture races pointercancel.
    }
  }

  function onPointerMove(event: PointerEvent) {
    if (!dragging || activePointerId !== event.pointerId) return;

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

    const elapsedMs = Math.max(
      4,
      Math.min(50, event.timeStamp - lastPointerTime || 16.667),
    );
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
        if (stage.hasPointerCapture(pointerToRelease))
          stage.releasePointerCapture(pointerToRelease);
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
    refreshRenderState();
    if (!isPaused) ensureAnimationLoop();
  }

  function restoreWallAfterHistoryNavigation() {
    cancelCameraAnimation();
    programmatic = false;
    dragging = false;
    activePointerId = null;
    gestureAxis = 'pending';
    dragDistance = 0;
    lastFrame = performance.now();
    velocity = getDriftVelocity();
    refreshRenderState();
    if (!isPaused) ensureAnimationLoop();
  }

  function onKeydown(event: KeyboardEvent) {
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
      void animateCameraTo(startX, 420);
    }
  }

  function animationFrame(now: number) {
    rafId = 0;
    if (!active) return;

    // requestAnimationFrame already follows the display's refresh cadence.
    // Do not add a second software frame limiter; doing so causes uneven frame
    // pacing on 90/120/144Hz screens and makes the checkerboard appear to jump.
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
      cameraX = programmaticStart + programmaticDelta * eased;

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
      cameraX += velocity * dt;
    }

    renderCamera();

    // When the user explicitly pauses the conveyor, stop scheduling frames
    // entirely once residual inertia has settled. Input restarts it on demand.
    if (isPaused && !dragging && !programmatic && Math.abs(velocity) < 0.01) {
      velocity = 0;
      return;
    }

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
    mounted = true;
    // Always begin in the moving state. The visible control is the only thing
    // that pauses this scene, which avoids browser/OS preference mismatches
    // producing a frozen wall with a nonfunctional-looking Pause button.
    isPaused = false;
    velocity = driftDirection * IDLE_DRIFT_SPEED;
    lastFrame = performance.now();
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
    window.addEventListener('pageshow', restoreWallAfterHistoryNavigation);
    ensureAnimationLoop();

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
      window.removeEventListener('pageshow', restoreWallAfterHistoryNavigation);
      cancelAnimationFrame(rafId);
    };
  });
</script>

<section
  bind:this={stage}
  class:wall-stage--dragging={dragging}
  class:wall-stage--interacted={hasInteracted}
  class:wall-stage--inactive={!active}
  class="wall-stage wall-stage--home wall-room-host"
  aria-hidden={!active ? 'true' : undefined}
  style={stageStyle}
  aria-label="Interactive navigation wall"
>
  <h1 class="visually-hidden">Cyrus Asasi</h1>

  <div
    bind:this={wallWorld}
    class="wall-world"
    aria-label="Website destinations"
    style={`--loop-base: 0px; transform: translate3d(${-startX}px, 0, 0);`}
  >
    {#each loopCopies as loopIndex}
      <div
        class="wall-loop"
        aria-hidden={loopIndex !== 0 ? 'true' : undefined}
        style={`--loop-offset: ${loopIndex * loopWidth}px;`}
      >
        <div
          class="wall-loop__seam wall-loop__seam--a"
          aria-hidden="true"
        ></div>
        <div
          class="wall-loop__seam wall-loop__seam--b"
          aria-hidden="true"
        ></div>

        {#each destinations as destination, destinationIndex (destination.id)}
          <WallWindow
            {destination}
            primary={loopIndex === 0}
            eager={loopIndex === 0 && destinationIndex === 0}
            onFocus={focusDestination}
            onEnter={enterDestination}
            indexLabel={String(destinationIndex + 1).padStart(2, '0')}
          />
        {/each}
      </div>
    {/each}
  </div>

  <p class="wall-navigation-hint">Click a painting to navigate</p>

  <button
    class="wall-motion-toggle wall-corner-control"
    type="button"
    aria-label={isPaused ? 'Play wall animation' : 'Pause wall animation'}
    aria-pressed={isPaused}
    title={isPaused ? 'Play wall animation' : 'Pause wall animation'}
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
        <rect x="6.5" y="5" width="4" height="14" rx="1" fill="currentColor" />
        <rect x="13.5" y="5" width="4" height="14" rx="1" fill="currentColor" />
      </svg>
    {/if}
  </button>
</section>
