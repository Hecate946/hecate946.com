<script lang="ts">
  import { onMount } from 'svelte';
  import WallWindow from './WallWindow.svelte';
  import {
    WALL_LOOP_WIDTH,
    WALL_START_X,
    wallDestinations,
    type WallDestination,
  } from './wall-config';
  import { withBase } from '@/lib/paths';

  const loopCopies = [-1, 0, 1] as const;
  const DRAG_THRESHOLD = 7;
  const WHEEL_SCALE = 0.82;
  const IDLE_DRIFT_SPEED = 24; // pixels per second
  const DIRECTION_THRESHOLD = 36;
  const INERTIA_TIME_CONSTANT = 0.78;
  const MAX_MANUAL_SPEED = 2_400;

  let stage: HTMLElement;
  let cameraX = WALL_START_X;
  let velocity = 0;
  let driftDirection = 1;
  let isPaused = false;
  let prefersReducedMotion = false;
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

  const stageStyle = `--camera-x: ${WALL_START_X}px; --loop-width: ${WALL_LOOP_WIDTH}px; --world-left: -${WALL_LOOP_WIDTH}px; --world-span: ${WALL_LOOP_WIDTH * 3}px;`;

  function wrapCamera() {
    while (cameraX < 0) cameraX += WALL_LOOP_WIDTH;
    while (cameraX >= WALL_LOOP_WIDTH) cameraX -= WALL_LOOP_WIDTH;
  }

  function markInteracted() {
    hasInteracted = true;
  }


  function updateDriftDirection(nextVelocity: number) {
    if (nextVelocity > DIRECTION_THRESHOLD) driftDirection = 1;
    else if (nextVelocity < -DIRECTION_THRESHOLD) driftDirection = -1;
  }

  function getDriftVelocity() {
    return isPaused || prefersReducedMotion ? 0 : driftDirection * IDLE_DRIFT_SPEED;
  }

  function renderCamera() {
    stage?.style.setProperty('--camera-x', `${cameraX}px`);
  }

  function toggleMotion() {
    isPaused = !isPaused;
    velocity = isPaused ? 0 : getDriftVelocity();
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
    wrapCamera();
  }

  function nearestDelta(targetX: number) {
    let delta = targetX - cameraX;
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

        wrapCamera();
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

  function enterDestination(event: MouseEvent, destination: WallDestination) {
    event.preventDefault();

    if (dragDistance > DRAG_THRESHOLD) return;

    markInteracted();
    clearPointerDrag();
    window.location.assign(withBase(destination.href));
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
    wrapCamera();
  }

  function clearPointerDrag(pointerId?: number) {
    if (pointerId !== undefined && activePointerId !== pointerId) return;
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
      wrapCamera();
    }

    // Render exactly once per display frame. Pointer/wheel events only update
    // world state; they no longer force separate Svelte/DOM updates.
    renderCamera();
    rafId = requestAnimationFrame(animationFrame);
  }

  onMount(() => {
    const reducedMotionQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    const onReducedMotionChange = () => {
      prefersReducedMotion = reducedMotionQuery.matches;
      if (prefersReducedMotion) velocity = 0;
    };
    prefersReducedMotion = reducedMotionQuery.matches;
    reducedMotionQuery.addEventListener('change', onReducedMotionChange);
    velocity = getDriftVelocity();
    renderCamera();

    stage.addEventListener('wheel', onWheel, { passive: false });
    stage.addEventListener('pointerdown', onPointerDown);
    stage.addEventListener('pointermove', onPointerMove);
    stage.addEventListener('pointerup', finishPointer);
    stage.addEventListener('pointercancel', finishPointer);
    stage.addEventListener('pointerleave', onPointerLeave);
    window.addEventListener('keydown', onKeydown);
    window.addEventListener('blur', onWindowBlur);
    window.addEventListener('pageshow', restoreWallAfterHistoryNavigation);
    rafId = requestAnimationFrame(animationFrame);

    return () => {
      reducedMotionQuery.removeEventListener('change', onReducedMotionChange);
      stage.removeEventListener('wheel', onWheel);
      stage.removeEventListener('pointerdown', onPointerDown);
      stage.removeEventListener('pointermove', onPointerMove);
      stage.removeEventListener('pointerup', finishPointer);
      stage.removeEventListener('pointercancel', finishPointer);
      stage.removeEventListener('pointerleave', onPointerLeave);
      window.removeEventListener('keydown', onKeydown);
      window.removeEventListener('blur', onWindowBlur);
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

  <div class="wall-stage__mortar-light" aria-hidden="true"></div>

  <div class="wall-world" aria-label="Website destinations">
    <div class="wall-world__wall-surface" aria-hidden="true"></div>

    <div class="wall-world__floor" aria-hidden="true">
      <div class="wall-world__floor-surface"></div>
      <div class="wall-world__baseboard"></div>
    </div>

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

  <div class="wall-stage__vignette" aria-hidden="true"></div>


  <button
    class="wall-motion-toggle"
    type="button"
    aria-label={isPaused ? 'Play wall animation' : 'Pause wall animation'}
    aria-pressed={isPaused}
    title={isPaused ? 'Play wall animation' : 'Pause wall animation'}
    onpointerdown={(event) => event.stopPropagation()}
    onclick={(event) => {
      event.stopPropagation();
      toggleMotion();
    }}
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
    --window-scale: 0.9;

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

  .wall-world {
    position: absolute;
    z-index: 4;
    inset: 0;
    transform: translate3d(calc(50vw - var(--camera-x)), 0, 0);
    backface-visibility: hidden;
    will-change: transform;
  }

  .wall-world__wall-surface {
    position: absolute;
    z-index: 0;
    top: 0;
    bottom: 0;
    left: var(--world-left);
    width: var(--world-span);
    background-color: var(--wall-dark, #010101);
    background-image: linear-gradient(
      180deg,
      color-mix(in srgb, var(--wall-light, #f4f1e9) 0.7%, transparent),
      transparent 18%,
      rgb(0 0 0 / 14%) 82%,
      rgb(0 0 0 / 22%)
    );
    box-shadow:
      inset 0 0 0 1px color-mix(in srgb, var(--wall-light, #f4f1e9) 0.5%, transparent),
      inset 0 -8rem 12rem rgb(0 0 0 / 32%);
  }

  .wall-world__wall-surface::before {
    position: absolute;
    inset: 0;
    background: color-mix(in srgb, var(--wall-light, #f4f1e9) 22%, transparent);
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
  }

  .wall-world__wall-surface::after {
    position: absolute;
    inset: 0;
    background:
      linear-gradient(90deg, rgb(0 0 0 / 18%), transparent 12% 88%, rgb(0 0 0 / 18%)),
      linear-gradient(180deg, transparent, rgb(0 0 0 / 16%) 78%, rgb(0 0 0 / 28%));
    content: '';
    pointer-events: none;
  }

  .wall-world__floor {
    position: absolute;
    z-index: 1;
    bottom: -0.2rem;
    left: var(--world-left);
    width: var(--world-span);
    height: calc(var(--floor-height) + 0.2rem);
    overflow: hidden;
    pointer-events: none;
  }

  .wall-world__floor-surface {
    position: absolute;
    inset: -0.15rem 0 0;
    backface-visibility: hidden;
    will-change: transform;
    background-color: var(--wall-dark, #050505);
    background-image:
      linear-gradient(
        180deg,
        color-mix(in srgb, var(--wall-light, #f4f1e9) 8%, transparent),
        transparent 20% 76%,
        rgb(0 0 0 / 16%)
      ),
      conic-gradient(
        from 90deg,
        var(--wall-light, #f4f1e9) 0 25%,
        var(--wall-dark, #050505) 0 50%,
        var(--wall-light, #f4f1e9) 0 75%,
        var(--wall-dark, #050505) 0 100%
      );
    background-position: 0 0, 0 0;
    background-repeat: no-repeat, repeat;
    background-size: 100% 100%, 120px 120px;
    box-shadow:
      inset 0 1rem 1.5rem rgb(0 0 0 / 22%),
      inset 0 -1.1rem 2rem rgb(0 0 0 / 16%);
    transform: perspective(30rem) rotateX(64deg) scaleY(1.28) translateY(14%);
    transform-origin: calc(var(--camera-x) + var(--loop-width)) 0;
  }

  .wall-world__floor-surface::after {
    position: absolute;
    inset: 0;
    background:
      linear-gradient(108deg, transparent 0 32%, color-mix(in srgb, var(--wall-light, #f4f1e9) 3%, transparent) 41%, transparent 50%) 0 0 / 30rem 100% repeat-x,
      linear-gradient(180deg, color-mix(in srgb, var(--wall-light, #f4f1e9) 1.5%, transparent), transparent 45%);
    content: '';
    mix-blend-mode: screen;
    opacity: 0.18;
  }

  .wall-world__baseboard {
    position: absolute;
    z-index: 2;
    top: 0;
    right: 0;
    left: 0;
    height: calc(var(--baseboard-height) + 0.7rem);
    background: linear-gradient(
      180deg,
      color-mix(in srgb, var(--wall-dark, #050505) 86%, black) 0%,
      color-mix(in srgb, var(--wall-dark, #050505) 94%, black) 34%,
      color-mix(in srgb, var(--wall-dark, #050505) 100%, black) 100%
    );
    border-top: 1px solid color-mix(in srgb, var(--wall-light, #f4f1e9) 10%, transparent);
    border-bottom: 1px solid rgb(0 0 0 / 72%);
    box-shadow:
      inset 0 1px 0 rgb(255 255 255 / 0.04),
      inset 0 -1px 0 rgb(0 0 0 / 0.6),
      0 0.75rem 1rem rgb(0 0 0 / 0.22);
    transform: translateY(-0.14rem);
  }

  .wall-world__baseboard::before {
    position: absolute;
    top: -0.12rem;
    right: -0.05rem;
    left: -0.05rem;
    height: 0.38rem;
    background: linear-gradient(
      180deg,
      color-mix(in srgb, var(--wall-dark, #050505) 74%, var(--wall-light, #f4f1e9)) 0%,
      color-mix(in srgb, var(--wall-dark, #050505) 88%, black) 58%,
      color-mix(in srgb, var(--wall-dark, #050505) 100%, black) 100%
    );
    border: 1px solid rgb(0 0 0 / 0.56);
    border-bottom-color: rgb(0 0 0 / 0.72);
    border-radius: 999px / 0.34rem;
    box-shadow:
      inset 0 1px 0 rgb(255 255 255 / 0.05),
      0 0.08rem 0.14rem rgb(0 0 0 / 0.12);
    content: '';
  }

  .wall-world__baseboard::after {
    position: absolute;
    inset: 0.5rem 0.4rem 0.18rem;
    background: linear-gradient(
      180deg,
      color-mix(in srgb, var(--wall-dark, #050505) 88%, var(--wall-light, #f4f1e9)) 0%,
      color-mix(in srgb, var(--wall-dark, #050505) 96%, black) 24%,
      color-mix(in srgb, var(--wall-dark, #050505) 100%, black) 100%
    );
    border: 1px solid rgb(0 0 0 / 0.58);
    box-shadow: inset 0 0 0 1px rgb(255 255 255 / 0.006);
    content: '';
  }

  .wall-loop {
    position: absolute;
    z-index: 3;
    inset: 0 auto 0 var(--loop-offset);
    width: var(--loop-width);
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
    left: 340px;
    height: 41%;
  }

  .wall-loop__seam--b {
    left: 3340px;
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
      --window-scale: 1;
    }
  }

  @media (max-height: 42rem) and (min-width: 40.001rem) {
    .wall-stage {
      --window-scale: 0.78;
    }
  }

  @media (max-width: 40rem) {
    .wall-stage {
      --floor-height: 6.4rem;
      --baseboard-height: 0.78rem;
      --window-scale: 0.73;
    }

    .wall-world__floor {
      bottom: -0.55rem;
      height: calc(var(--floor-height) + 0.8rem);
    }

    .wall-world__baseboard {
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
