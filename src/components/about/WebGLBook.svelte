<script lang="ts">
  import { onMount } from 'svelte';
  import { BookScene } from './book-scene';
  import type {
    BookClosedSide,
    BookLink,
    BookMotion,
    BookSpread,
    PageSide,
  } from './book-types';

  export let spreads: BookSpread[] = [];

  let hostElement: HTMLDivElement;
  let canvasElement: HTMLCanvasElement;
  let bookScene: BookScene | null = null;
  let currentSpread = 0;
  let closedSide: BookClosedSide = null;
  let motion: BookMotion | null = null;
  let turnProgress = 0;
  let isAnimating = false;
  let isDragging = false;
  let ready = false;
  let webglFailed = false;
  let prefersReducedMotion = false;
  let animationFrame = 0;
  let activePointerId: number | null = null;
  let pointerMotion: BookMotion | null = null;
  let pointerStartX = 0;
  let pointerStartY = 0;
  let pointerStartedAt = 0;
  let pointerTravelWidth = 1;
  let pointerMoved = false;
  let ignoreClicksUntil = 0;

  const clamp01 = (value: number) => Math.min(1, Math.max(0, value));
  const smootherstep = (value: number) => {
    const x = clamp01(value);
    return x * x * x * (x * (x * 6 - 15) + 10);
  };

  const renderState = () => bookScene?.setState(currentSpread, closedSide, motion, turnProgress);

  const clearAnimation = () => {
    if (!animationFrame) return;
    cancelAnimationFrame(animationFrame);
    animationFrame = 0;
  };

  const followLink = (link: BookLink) => {
    if (link.external) {
      const opened = window.open(link.href, '_blank', 'noopener,noreferrer');
      if (opened) opened.opener = null;
      return;
    }
    window.location.assign(link.href);
  };

  const pageMotionForSide = (side: PageSide): BookMotion => {
    if (side === 'left') {
      return currentSpread === 0
        ? { kind: 'cover', side: 'front', opening: false }
        : { kind: 'page', direction: -1 };
    }

    return currentSpread === spreads.length - 1
      ? { kind: 'cover', side: 'back', opening: false }
      : { kind: 'page', direction: 1 };
  };

  const openMotionForClosedBook = (): BookMotion | null => {
    if (!closedSide) return null;
    return { kind: 'cover', side: closedSide, opening: true };
  };

  const finishMotion = (finishedMotion: BookMotion, complete: boolean) => {
    if (complete) {
      if (finishedMotion.kind === 'page') {
        currentSpread += finishedMotion.direction;
      } else if (finishedMotion.opening) {
        closedSide = null;
      } else {
        closedSide = finishedMotion.side;
      }
    }

    motion = null;
    turnProgress = 0;
    isAnimating = false;
    isDragging = false;
    animationFrame = 0;
    renderState();
  };

  const settleMotion = (activeMotion: BookMotion, complete: boolean) => {
    if (!motion) {
      motion = activeMotion;
      renderState();
    }

    clearAnimation();
    isAnimating = true;
    isDragging = false;
    const start = clamp01(turnProgress);
    const target = complete ? 1 : 0;
    const distance = Math.abs(target - start);

    if (prefersReducedMotion || distance < 0.001) {
      turnProgress = target;
      renderState();
      finishMotion(activeMotion, complete);
      return;
    }

    const startedAt = performance.now();
    const baseDuration = activeMotion.kind === 'cover' ? 1280 : 1420;
    const cancelDuration = activeMotion.kind === 'cover' ? 860 : 980;
    const duration = Math.max(500, (complete ? baseDuration : cancelDuration) * distance);

    const tick = (now: number) => {
      const elapsed = clamp01((now - startedAt) / duration);
      turnProgress = start + (target - start) * smootherstep(elapsed);
      renderState();

      if (elapsed < 1) {
        animationFrame = requestAnimationFrame(tick);
        return;
      }

      turnProgress = target;
      renderState();
      // Keep the exact geometric endpoint on screen for one paint before the
      // logical state changes. This prevents a one-frame pop at the covers too.
      animationFrame = requestAnimationFrame(() => finishMotion(activeMotion, complete));
    };

    animationFrame = requestAnimationFrame(tick);
  };

  const animateMotion = (nextMotion: BookMotion) => {
    if (!ready || isAnimating || isDragging || motion) return;
    motion = nextMotion;
    turnProgress = 0;
    renderState();
    animationFrame = requestAnimationFrame(() => settleMotion(nextMotion, true));
  };

  const resetPointer = () => {
    activePointerId = null;
    pointerMotion = null;
    pointerMoved = false;
    isDragging = false;
  };

  const travelForMotion = (activeMotion: BookMotion, dx: number) => {
    if (activeMotion.kind === 'page') return activeMotion.direction === 1 ? -dx : dx;
    if (activeMotion.side === 'front') return activeMotion.opening ? -dx : dx;
    return activeMotion.opening ? dx : -dx;
  };

  const handlePointerDown = (event: PointerEvent) => {
    if (!ready || isAnimating || motion || activePointerId !== null || !bookScene) return;
    if (event.pointerType === 'mouse' && event.button !== 0) return;

    const hit = bookScene.pickSurface(event.clientX, event.clientY);
    if (!hit) return;

    const nextMotion = hit.target === 'cover' ? openMotionForClosedBook() : pageMotionForSide(hit.side);
    if (!nextMotion) return;

    activePointerId = event.pointerId;
    pointerMotion = nextMotion;
    pointerStartX = event.clientX;
    pointerStartY = event.clientY;
    pointerStartedAt = performance.now();
    const canvasBounds = canvasElement.getBoundingClientRect();
    pointerTravelWidth = Math.max(1, Math.min(canvasBounds.width * 0.46, canvasBounds.height * 0.58));
    pointerMoved = false;
  };

  const handlePointerMove = (event: PointerEvent) => {
    if (activePointerId !== event.pointerId || !pointerMotion || isAnimating) return;
    const dx = event.clientX - pointerStartX;
    const dy = event.clientY - pointerStartY;
    const distance = Math.hypot(dx, dy);
    if (!pointerMoved && distance < 6) return;

    if (!pointerMoved && Math.abs(dy) > Math.abs(dx) * 1.18) {
      resetPointer();
      ignoreClicksUntil = performance.now() + 250;
      return;
    }

    const travel = travelForMotion(pointerMotion, dx);
    if (travel <= 0) return;

    if (!pointerMoved) {
      pointerMoved = true;
      isDragging = true;
      motion = pointerMotion;
      turnProgress = 0;
      renderState();
    }

    if (event.cancelable) event.preventDefault();
    turnProgress = Math.min(0.995, (travel / pointerTravelWidth) * 0.98);
    renderState();
  };

  const releasePointer = (event: PointerEvent, cancelled = false) => {
    if (activePointerId !== event.pointerId) return;
    const dx = event.clientX - pointerStartX;
    const dy = event.clientY - pointerStartY;
    const elapsed = Math.max(1, performance.now() - pointerStartedAt);
    const velocity = Math.abs(dx) / elapsed;
    const moved = pointerMoved;
    const gestureDistance = Math.hypot(dx, dy);
    const activeMotion = pointerMotion;
    resetPointer();

    if (!moved) {
      if (gestureDistance > 6) ignoreClicksUntil = performance.now() + 260;
      return;
    }

    ignoreClicksUntil = performance.now() + 420;
    if (!activeMotion) return;
    settleMotion(activeMotion, !cancelled && (turnProgress >= 0.34 || velocity >= 0.40));
  };

  const handlePointerCancel = (event: PointerEvent) => releasePointer(event, true);

  const handleClick = (event: MouseEvent) => {
    if (
      !ready ||
      isAnimating ||
      isDragging ||
      motion ||
      !bookScene ||
      performance.now() < ignoreClicksUntil
    ) return;

    const hit = bookScene.pickSurface(event.clientX, event.clientY);
    if (!hit) return;

    if (hit.target === 'cover') {
      const openMotion = openMotionForClosedBook();
      if (openMotion) animateMotion(openMotion);
      return;
    }

    if (!closedSide && hit.side === 'right') {
      const link = bookScene.linkAtCurrentRight(hit.uv);
      if (link) {
        followLink(link);
        return;
      }
    }

    animateMotion(pageMotionForSide(hit.side));
  };

  const updateCursor = (event: PointerEvent) => {
    if (!ready || isAnimating || isDragging || motion || !bookScene) return;
    const hit = bookScene.pickSurface(event.clientX, event.clientY);
    if (!hit) {
      canvasElement.style.cursor = 'default';
      return;
    }

    if (hit.target === 'cover') {
      canvasElement.style.cursor = 'grab';
      return;
    }

    if (!closedSide && hit.side === 'right' && bookScene.linkAtCurrentRight(hit.uv)) {
      canvasElement.style.cursor = 'pointer';
      return;
    }

    canvasElement.style.cursor = 'grab';
  };

  const isInteractiveTarget = (target: EventTarget | null) =>
    target instanceof Element && Boolean(target.closest('a, button, input, textarea, select'));

  const handleKeyDown = (event: KeyboardEvent) => {
    if (isInteractiveTarget(event.target) || isAnimating || isDragging || motion) return;

    if (closedSide === 'front') {
      if (event.key === 'ArrowRight' || event.key === 'PageDown') {
        event.preventDefault();
        const openMotion = openMotionForClosedBook();
        if (openMotion) animateMotion(openMotion);
      }
      return;
    }

    if (closedSide === 'back') {
      if (event.key === 'ArrowLeft' || event.key === 'PageUp') {
        event.preventDefault();
        const openMotion = openMotionForClosedBook();
        if (openMotion) animateMotion(openMotion);
      }
      return;
    }

    if (event.key === 'ArrowRight' || event.key === 'PageDown') {
      event.preventDefault();
      animateMotion(pageMotionForSide('right'));
    } else if (event.key === 'ArrowLeft' || event.key === 'PageUp') {
      event.preventDefault();
      animateMotion(pageMotionForSide('left'));
    }
  };

  onMount(() => {
    let disposed = false;
    const motionQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    const updateMotion = () => (prefersReducedMotion = motionQuery.matches);
    updateMotion();

    const initialise = async () => {
      try {
        bookScene = new BookScene(hostElement, canvasElement, spreads);
        await bookScene.initialise();
        if (disposed) return;
        ready = true;
        renderState();
      } catch (error) {
        console.error('Unable to initialise About book WebGL renderer', error);
        webglFailed = true;
      }
    };

    void initialise();

    canvasElement.addEventListener('pointerdown', handlePointerDown);
    canvasElement.addEventListener('pointermove', updateCursor);
    canvasElement.addEventListener('click', handleClick);
    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('pointermove', handlePointerMove, { passive: false });
    window.addEventListener('pointerup', releasePointer);
    window.addEventListener('pointercancel', handlePointerCancel);
    motionQuery.addEventListener('change', updateMotion);

    return () => {
      disposed = true;
      clearAnimation();
      canvasElement.removeEventListener('pointerdown', handlePointerDown);
      canvasElement.removeEventListener('pointermove', updateCursor);
      canvasElement.removeEventListener('click', handleClick);
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('pointermove', handlePointerMove);
      window.removeEventListener('pointerup', releasePointer);
      window.removeEventListener('pointercancel', handlePointerCancel);
      motionQuery.removeEventListener('change', updateMotion);
      bookScene?.dispose();
      bookScene = null;
    };
  });
</script>

<div
  class="about-webgl-book"
  class:is-ready={ready}
  class:is-dragging={isDragging}
  class:is-closed={Boolean(closedSide)}
  bind:this={hostElement}
>
  <canvas
    bind:this={canvasElement}
    aria-hidden="true"
  ></canvas>

  {#if webglFailed}
    <div class="about-webgl-book__fallback">
      <h1>{spreads[currentSpread]?.title}</h1>
      {#each spreads[currentSpread]?.paragraphs ?? [] as paragraph}
        <p>{paragraph}</p>
      {/each}
    </div>
  {/if}

  <div class="about-book-accessible" aria-live="polite">
    {#if closedSide}
      <p>About book closed at the {closedSide} cover.</p>
    {:else}
      <h1>{spreads[currentSpread]?.title}</h1>
      {#each spreads[currentSpread]?.paragraphs ?? [] as paragraph}
        <p>{paragraph}</p>
      {/each}
      {#if spreads[currentSpread]?.link}
        <a
          href={spreads[currentSpread].link?.href}
          target={spreads[currentSpread].link?.external ? '_blank' : undefined}
          rel={spreads[currentSpread].link?.external ? 'noopener noreferrer' : undefined}
        >{spreads[currentSpread].link?.label}</a>
      {/if}
      {#each spreads[currentSpread]?.interests ?? [] as interest}
        <h2>{interest.title}</h2>
        <p>{interest.body}</p>
        <a
          href={interest.link.href}
          target={interest.link.external ? '_blank' : undefined}
          rel={interest.link.external ? 'noopener noreferrer' : undefined}
        >{interest.link.label}</a>
      {/each}
    {/if}
  </div>
</div>
