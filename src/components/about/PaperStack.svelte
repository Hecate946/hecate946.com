<script lang="ts">
  import { onMount } from 'svelte';
  import type { AboutPaperPage } from './about-book-content';

  export let pages: AboutPaperPage[] = [];

  type TurnDirection = 1 | -1;

  let stackElement: HTMLDivElement;
  let currentIndex = 0;
  let turnDirection: TurnDirection | null = null;
  let turnProgress = 0;
  let isDragging = false;
  let isAnimating = false;
  let prefersReducedMotion = false;
  let animationFrame = 0;
  let pointerId: number | null = null;
  let pointerStartX = 0;
  let pointerStartY = 0;
  let pointerMoved = false;
  let pointerStartedAt = 0;
  let pointerThreshold = 1;
  let ignoreClicksUntil = 0;

  const clamp01 = (value: number) => Math.min(1, Math.max(0, value));
  const smootherstep = (value: number) => {
    const x = clamp01(value);
    return x * x * x * (x * (x * 6 - 15) + 10);
  };

  $: pageCount = pages.length;
  $: currentPage = pages[currentIndex];
  $: targetPage =
    turnDirection === 1
      ? pages[Math.min(pageCount - 1, currentIndex + 1)]
      : turnDirection === -1
        ? pages[Math.max(0, currentIndex - 1)]
        : currentPage;
  $: turningPage = turnDirection === -1 ? targetPage : currentPage;

  const canGoNext = () => currentIndex < pageCount - 1;
  const canGoPrev = () => currentIndex > 0;

  const clearAnimation = () => {
    if (!animationFrame) return;
    cancelAnimationFrame(animationFrame);
    animationFrame = 0;
  };

  const pageNumberFor = (page: AboutPaperPage | undefined) => {
    if (!page) return '00';
    const index = pages.findIndex((candidate) => candidate.id === page.id);
    return String(index + 1).padStart(2, '0');
  };

  const dragAmountFor = (direction: TurnDirection, dx: number, dy: number) => {
    if (direction === 1) return -dx * 0.74 + -dy * 0.58;
    return dx * 0.74 + dy * 0.58;
  };

  const resetPointer = () => {
    pointerId = null;
    pointerMoved = false;
    isDragging = false;
  };

  const completeTurn = (direction: TurnDirection, commit: boolean) => {
    if (commit) currentIndex = clampIndex(currentIndex + direction);
    turnDirection = null;
    turnProgress = 0;
    isDragging = false;
    isAnimating = false;
    animationFrame = 0;
  };

  const clampIndex = (value: number) => Math.min(pageCount - 1, Math.max(0, value));

  const settleTurn = (direction: TurnDirection, commit: boolean) => {
    clearAnimation();
    isAnimating = true;
    isDragging = false;

    const start = clamp01(turnProgress);
    const target = commit ? 1 : 0;
    const distance = Math.abs(target - start);

    if (prefersReducedMotion || distance < 0.001) {
      turnProgress = target;
      completeTurn(direction, commit);
      return;
    }

    const duration = Math.max(240, (commit ? 720 : 420) * distance);
    const startedAt = performance.now();

    const tick = (now: number) => {
      const elapsed = clamp01((now - startedAt) / duration);
      turnProgress = start + (target - start) * smootherstep(elapsed);

      if (elapsed < 1) {
        animationFrame = requestAnimationFrame(tick);
        return;
      }

      turnProgress = target;
      animationFrame = requestAnimationFrame(() => completeTurn(direction, commit));
    };

    animationFrame = requestAnimationFrame(tick);
  };

  const startClickTurn = (direction: TurnDirection) => {
    if (isAnimating || isDragging || turnDirection || pageCount <= 1) return;
    if (direction === 1 && !canGoNext()) return;
    if (direction === -1 && !canGoPrev()) return;

    turnDirection = direction;
    turnProgress = 0;
    settleTurn(direction, true);
  };

  const hitIsStapleRegion = (clientX: number, clientY: number) => {
    const rect = stackElement.getBoundingClientRect();
    const x = clientX - rect.left;
    const y = clientY - rect.top;
    return x <= rect.width * 0.34 && y <= rect.height * 0.28;
  };

  const chooseClickDirection = (clientX: number, clientY: number): TurnDirection | null => {
    const inStapleRegion = hitIsStapleRegion(clientX, clientY);
    if (inStapleRegion && canGoPrev()) return -1;
    if (canGoNext()) return 1;
    if (!inStapleRegion && canGoPrev()) return -1;
    return null;
  };

  const handlePointerDown = (event: PointerEvent) => {
    if (isAnimating || turnDirection || pointerId !== null) return;
    if (event.pointerType === 'mouse' && event.button !== 0) return;
    if (event.cancelable) event.preventDefault();
    pointerId = event.pointerId;
    pointerStartX = event.clientX;
    pointerStartY = event.clientY;
    pointerStartedAt = performance.now();
    pointerMoved = false;
    const rect = stackElement.getBoundingClientRect();
    pointerThreshold = Math.max(1, Math.min(rect.width * 0.72, rect.height * 0.68));
  };

  const handlePointerMove = (event: PointerEvent) => {
    if (pointerId !== event.pointerId || isAnimating) return;
    const dx = event.clientX - pointerStartX;
    const dy = event.clientY - pointerStartY;
    const distance = Math.hypot(dx, dy);
    if (!pointerMoved && distance < 7) return;

    if (!turnDirection) {
      const nextTravel = canGoNext() ? dragAmountFor(1, dx, dy) : -Infinity;
      const prevTravel = canGoPrev() ? dragAmountFor(-1, dx, dy) : -Infinity;
      const best = Math.max(nextTravel, prevTravel);
      if (best <= 6) return;
      turnDirection = nextTravel >= prevTravel ? 1 : -1;
      turnProgress = 0;
      pointerMoved = true;
      isDragging = true;
    }

    const travel = dragAmountFor(turnDirection, dx, dy);
    if (travel <= 0) return;
    if (event.cancelable) event.preventDefault();
    pointerMoved = true;
    isDragging = true;
    turnProgress = Math.min(0.995, travel / pointerThreshold);
  };

  const finishPointer = (event: PointerEvent, cancelled = false) => {
    if (pointerId !== event.pointerId) return;
    const dx = event.clientX - pointerStartX;
    const elapsed = Math.max(1, performance.now() - pointerStartedAt);
    const velocity = Math.abs(dx) / elapsed;
    const moved = pointerMoved;
    const direction = turnDirection;
    resetPointer();

    if (!moved || !direction) {
      if (Math.hypot(dx, event.clientY - pointerStartY) > 6) {
        ignoreClicksUntil = performance.now() + 260;
      }
      return;
    }

    ignoreClicksUntil = performance.now() + 420;
    settleTurn(direction, !cancelled && (turnProgress >= 0.28 || velocity >= 0.34));
  };

  const handlePointerCancel = (event: PointerEvent) => finishPointer(event, true);

  const handleClick = (event: MouseEvent) => {
    if (performance.now() < ignoreClicksUntil) return;
    if (isAnimating || isDragging || turnDirection) return;
    const direction = chooseClickDirection(event.clientX, event.clientY);
    if (direction) startClickTurn(direction);
  };

  const handleKeyDown = (event: KeyboardEvent) => {
    if (isAnimating || isDragging || turnDirection) return;
    if (event.key === 'ArrowRight' || event.key === 'ArrowDown' || event.key === 'PageDown') {
      event.preventDefault();
      startClickTurn(1);
    } else if (event.key === 'ArrowLeft' || event.key === 'ArrowUp' || event.key === 'PageUp') {
      event.preventDefault();
      startClickTurn(-1);
    }
  };

  const handleStackKeyDown = (event: KeyboardEvent) => {
    if (event.key !== 'Enter' && event.key !== ' ') return;
    event.preventDefault();
    if (canGoNext()) startClickTurn(1);
    else if (canGoPrev()) startClickTurn(-1);
  };

  const sheetTransform = (direction: TurnDirection | null, progress: number) => {
    if (!direction) return 'translate3d(0, 0, 0) rotate(0deg) skew(0deg, 0deg)';

    const p = direction === 1 ? progress : 1 - progress;
    const translateX = -24 * p;
    const translateY = -19 * p;
    const rotate = -17 * p;
    const skewX = -1.4 * p;
    const skewY = -0.8 * p;
    const scale = 1 - 0.018 * p;

    return `translate3d(${translateX}%, ${translateY}%, 0) rotate(${rotate}deg) skew(${skewX}deg, ${skewY}deg) scale(${scale})`;
  };

  const sheetShadow = (direction: TurnDirection | null, progress: number) => {
    if (!direction) return '0 1.1rem 2rem rgb(18 6 2 / 18%), 0 0.22rem 0.5rem rgb(18 6 2 / 10%)';
    const p = direction === 1 ? progress : 1 - progress;
    const blur = 2 + p * 2.4;
    const lift = 1 + p * 1.3;
    const alpha = 0.18 + p * 0.08;
    return `0 ${lift.toFixed(2)}rem ${blur.toFixed(2)}rem rgb(18 6 2 / ${alpha.toFixed(2)}), 0 0.25rem 0.6rem rgb(18 6 2 / 0.10)`;
  };

  onMount(() => {
    const motionQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    const updateMotion = () => (prefersReducedMotion = motionQuery.matches);
    updateMotion();
    motionQuery.addEventListener('change', updateMotion);
    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('pointermove', handlePointerMove, { passive: false });
    window.addEventListener('pointerup', finishPointer);
    window.addEventListener('pointercancel', handlePointerCancel);

    return () => {
      clearAnimation();
      motionQuery.removeEventListener('change', updateMotion);
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('pointermove', handlePointerMove);
      window.removeEventListener('pointerup', finishPointer);
      window.removeEventListener('pointercancel', handlePointerCancel);
    };
  });
</script>

<div class="paper-stack" class:is-animating={isAnimating} class:is-dragging={isDragging}>
  <div
    class="paper-stack__stack"
    bind:this={stackElement}
    on:pointerdown={handlePointerDown}
    on:click={handleClick}
    on:keydown={handleStackKeyDown}
    role="button"
    tabindex="0"
    aria-label="About papers"
  >
    <div class="paper-stack__shadow paper-stack__shadow--far" aria-hidden="true"></div>
    <div class="paper-stack__shadow paper-stack__shadow--near" aria-hidden="true"></div>

    <div class="paper-stack__sheet paper-stack__sheet--under paper-stack__sheet--offset-2" aria-hidden="true">
      <div class="paper-stack__surface"></div>
    </div>
    <div class="paper-stack__sheet paper-stack__sheet--under paper-stack__sheet--offset-1" aria-hidden="true">
      <div class="paper-stack__surface"></div>
    </div>

    {#if turnDirection}
      <article class="paper-stack__sheet paper-stack__sheet--base" aria-hidden="true">
        <div class="paper-stack__surface">
          <div class="paper-stack__staple"></div>
          <div class="paper-stack__content">
            <div class="paper-stack__eyebrow">{targetPage?.eyebrow}</div>
            <h1 class="paper-stack__title">{targetPage?.title}</h1>
            {#if targetPage?.subtitle}
              <p class="paper-stack__subtitle">{targetPage.subtitle}</p>
            {/if}
            {#if targetPage?.visual}
              <figure class="paper-stack__portrait-block">
                <img src={targetPage.visual.src} alt={targetPage.visual.alt} class="paper-stack__portrait" />
                {#if targetPage.visual.caption}
                  <figcaption class="paper-stack__caption">{targetPage.visual.caption}</figcaption>
                {/if}
              </figure>
            {/if}
            {#each targetPage?.paragraphs ?? [] as paragraph}
              <p class="paper-stack__paragraph">{paragraph}</p>
            {/each}
          </div>
          <div class="paper-stack__page-number">{pageNumberFor(targetPage)} / {String(pageCount).padStart(2, '0')}</div>
        </div>
      </article>
    {/if}

    <article
      class="paper-stack__sheet paper-stack__sheet--current"
      style={`transform: ${sheetTransform(turnDirection, turnProgress)}; box-shadow: ${sheetShadow(turnDirection, turnProgress)};`}
    >
      <div class="paper-stack__surface">
        <div class="paper-stack__staple"></div>
        <div class="paper-stack__content">
          <div class="paper-stack__eyebrow">{turningPage?.eyebrow}</div>
          <h1 class="paper-stack__title">{turningPage?.title}</h1>
          {#if turningPage?.subtitle}
            <p class="paper-stack__subtitle">{turningPage.subtitle}</p>
          {/if}
          {#if turningPage?.visual}
            <figure class="paper-stack__portrait-block">
              <img src={turningPage.visual.src} alt={turningPage.visual.alt} class="paper-stack__portrait" />
              {#if turningPage.visual.caption}
                <figcaption class="paper-stack__caption">{turningPage.visual.caption}</figcaption>
              {/if}
            </figure>
          {/if}
          {#each turningPage?.paragraphs ?? [] as paragraph}
            <p class="paper-stack__paragraph">{paragraph}</p>
          {/each}
        </div>
        <div class="paper-stack__page-number">{pageNumberFor(turningPage)} / {String(pageCount).padStart(2, '0')}</div>
      </div>
    </article>
  </div>

  <div class="paper-stack__accessible" aria-live="polite">
    <h2>{currentPage?.title}</h2>
    {#each currentPage?.paragraphs ?? [] as paragraph}
      <p>{paragraph}</p>
    {/each}
  </div>
</div>
