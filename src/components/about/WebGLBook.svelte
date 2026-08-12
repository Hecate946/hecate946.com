<script lang="ts">
  import { onMount } from 'svelte';
  import { BookScene } from './book-scene';
  import type { BookLink, BookSpread, Direction, PageSide } from './book-types';

  export let spreads: BookSpread[] = [];

  let hostElement: HTMLDivElement;
  let canvasElement: HTMLCanvasElement;
  let bookScene: BookScene | null = null;
  let currentSpread = 0;
  let turnDirection: Direction | 0 = 0;
  let turnProgress = 0;
  let isAnimating = false;
  let isDragging = false;
  let ready = false;
  let webglFailed = false;
  let prefersReducedMotion = false;
  let animationFrame = 0;
  let activePointerId: number | null = null;
  let pointerSide: PageSide | null = null;
  let pointerStartX = 0;
  let pointerStartY = 0;
  let pointerStartedAt = 0;
  let pointerTravelWidth = 1;
  let pointerMoved = false;
  let ignoreClicksUntil = 0;

  const clamp01 = (value: number) => Math.min(1, Math.max(0, value));
  const canTurn = (direction: Direction) =>
    direction === 1 ? currentSpread < spreads.length - 1 : currentSpread > 0;
  const smootherstep = (value: number) => {
    const x = clamp01(value);
    return x * x * x * (x * (x * 6 - 15) + 10);
  };

  const renderState = () => bookScene?.setState(currentSpread, turnDirection, turnProgress);

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

  const finishTurn = (direction: Direction, complete: boolean) => {
    if (complete) currentSpread += direction;
    turnDirection = 0;
    turnProgress = 0;
    isAnimating = false;
    isDragging = false;
    animationFrame = 0;
    renderState();
  };

  const settleTurn = (direction: Direction, complete: boolean) => {
    if (!turnDirection || !canTurn(direction)) {
      turnDirection = 0;
      turnProgress = 0;
      isAnimating = false;
      isDragging = false;
      renderState();
      return;
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
      finishTurn(direction, complete);
      return;
    }

    const startedAt = performance.now();
    const duration = Math.max(520, (complete ? 1420 : 980) * distance);

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
      animationFrame = requestAnimationFrame(() => finishTurn(direction, complete));
    };

    animationFrame = requestAnimationFrame(tick);
  };

  const animateTurn = (direction: Direction) => {
    if (!ready || isAnimating || isDragging || !canTurn(direction)) return;
    turnDirection = direction;
    turnProgress = 0;
    renderState();
    animationFrame = requestAnimationFrame(() => settleTurn(direction, true));
  };

  const resetPointer = () => {
    activePointerId = null;
    pointerSide = null;
    pointerMoved = false;
    isDragging = false;
  };

  const handlePointerDown = (event: PointerEvent) => {
    if (!ready || isAnimating || activePointerId !== null || !bookScene) return;
    if (event.pointerType === 'mouse' && event.button !== 0) return;

    const hit = bookScene.pickPage(event.clientX, event.clientY);
    if (!hit) return;
    const direction: Direction = hit.side === 'right' ? 1 : -1;
    if (!canTurn(direction)) return;

    activePointerId = event.pointerId;
    pointerSide = hit.side;
    pointerStartX = event.clientX;
    pointerStartY = event.clientY;
    pointerStartedAt = performance.now();
    const canvasBounds = canvasElement.getBoundingClientRect();
    pointerTravelWidth = Math.max(
      1,
      Math.min(canvasBounds.width * 0.46, canvasBounds.height * 0.58),
    );
    pointerMoved = false;
  };

  const handlePointerMove = (event: PointerEvent) => {
    if (activePointerId !== event.pointerId || !pointerSide || isAnimating) return;
    const dx = event.clientX - pointerStartX;
    const dy = event.clientY - pointerStartY;
    const distance = Math.hypot(dx, dy);
    if (!pointerMoved && distance < 6) return;

    if (!pointerMoved && Math.abs(dy) > Math.abs(dx) * 1.18) {
      resetPointer();
      ignoreClicksUntil = performance.now() + 250;
      return;
    }

    const direction: Direction = pointerSide === 'right' ? 1 : -1;
    const travel = direction === 1 ? -dx : dx;
    if (travel <= 0 || !canTurn(direction)) return;

    if (!pointerMoved) {
      pointerMoved = true;
      isDragging = true;
      turnDirection = direction;
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
    const direction = turnDirection;
    resetPointer();

    if (!moved) {
      if (gestureDistance > 6) ignoreClicksUntil = performance.now() + 260;
      return;
    }
    ignoreClicksUntil = performance.now() + 420;
    if (!direction) return;
    settleTurn(direction, !cancelled && (turnProgress >= 0.34 || velocity >= 0.40));
  };

  const handlePointerCancel = (event: PointerEvent) => releasePointer(event, true);

  const handleClick = (event: MouseEvent) => {
    if (!ready || isAnimating || isDragging || !bookScene || performance.now() < ignoreClicksUntil) return;
    const hit = bookScene.pickPage(event.clientX, event.clientY);
    if (!hit) return;

    if (hit.side === 'right') {
      const link = bookScene.linkAtCurrentRight(hit.uv);
      if (link) {
        followLink(link);
        return;
      }
    }

    animateTurn(hit.side === 'right' ? 1 : -1);
  };

  const updateCursor = (event: PointerEvent) => {
    if (!ready || isAnimating || isDragging || !bookScene) return;
    const hit = bookScene.pickPage(event.clientX, event.clientY);
    if (!hit) {
      canvasElement.style.cursor = 'default';
      return;
    }

    if (hit.side === 'right' && bookScene.linkAtCurrentRight(hit.uv)) {
      canvasElement.style.cursor = 'pointer';
      return;
    }

    const direction: Direction = hit.side === 'right' ? 1 : -1;
    canvasElement.style.cursor = canTurn(direction) ? 'grab' : 'default';
  };

  const isInteractiveTarget = (target: EventTarget | null) =>
    target instanceof Element && Boolean(target.closest('a, button, input, textarea, select'));

  const handleKeyDown = (event: KeyboardEvent) => {
    if (isInteractiveTarget(event.target)) return;
    if (event.key === 'ArrowRight' || event.key === 'PageDown') {
      if (!canTurn(1)) return;
      event.preventDefault();
      animateTurn(1);
    } else if (event.key === 'ArrowLeft' || event.key === 'PageUp') {
      if (!canTurn(-1)) return;
      event.preventDefault();
      animateTurn(-1);
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

  <div class="about-book-accessible">
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
  </div>
</div>
