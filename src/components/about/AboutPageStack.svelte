<script lang="ts">
  import { onMount } from 'svelte';

  export let musicVideoUrl: string;
  export let pickleballArticleUrl: string;
  export let chessProfileUrl: string;
  export let resumesUrl: string;

  const pages = [
    { id: 'cover', label: 'Cover' },
    { id: 'bio', label: 'About' },
    { id: 'software', label: 'Software' },
    { id: 'music', label: 'Music' },
    { id: 'interests', label: 'Interests' },
  ] as const;

  type Direction = -1 | 1;

  let currentPage = 0;
  let turnDirection: Direction | 0 = 0;
  let turnProgress = 0;
  let isAnimating = false;
  let prefersReducedMotion = false;
  let stackElement: HTMLElement | null = null;

  let activePointerId: number | null = null;
  let pointerStartX = 0;
  let pointerStartY = 0;
  let pointerStartedAt = 0;
  let pointerWidth = 1;
  let pointerMoved = false;
  let ignoreClicksUntil = 0;
  let animationTimer = 0;

  const canTurn = (direction: Direction) =>
    direction === 1 ? currentPage < pages.length - 1 : currentPage > 0;

  // Reactive state must be visible to Svelte at the markup expression level.
  // The page transform helper receives every changing value as an argument for
  // the same reason; otherwise an event can update JS state without repainting.
  const pageStyle = (index: number, activePage: number, progress: number) => {
    const depth = Math.min(Math.max(0, index - activePage), 3);
    const forward = progress;
    const backward = 1 - progress;

    return [
      `--stack-depth:${depth}`,
      `--stack-x:${(depth * 0.11).toFixed(3)}rem`,
      `--stack-y:${(depth * 0.13).toFixed(3)}rem`,
      `--stack-z:${-depth}px`,
      `--stack-scale:${(1 - depth * 0.0028).toFixed(4)}`,
      `--forward-x:${(-4 * forward).toFixed(3)}%`,
      `--forward-y:${(0.2 * forward).toFixed(3)}%`,
      `--forward-angle:${(-179 * forward).toFixed(3)}deg`,
      `--forward-tilt:${(-1.15 * forward).toFixed(3)}deg`,
      `--forward-shadow-x:${(-1.35 * forward).toFixed(3)}rem`,
      `--backward-x:${(-4 * backward).toFixed(3)}%`,
      `--backward-y:${(0.2 * backward).toFixed(3)}%`,
      `--backward-angle:${(-179 * backward).toFixed(3)}deg`,
      `--backward-tilt:${(-1.15 * backward).toFixed(3)}deg`,
      `--backward-shadow-x:${(-1.35 * backward).toFixed(3)}rem`,
      `--turn-shade-opacity:${(forward * 0.72).toFixed(3)}`,
    ].join(';');
  };

  const clearAnimationTimer = () => {
    if (!animationTimer) return;
    window.clearTimeout(animationTimer);
    animationTimer = 0;
  };

  const settleTurn = (direction: Direction, complete: boolean) => {
    if (!turnDirection || !canTurn(direction)) {
      turnDirection = 0;
      turnProgress = 0;
      isAnimating = false;
      return;
    }

    clearAnimationTimer();
    isAnimating = true;
    turnProgress = complete ? 1 : 0;

    const duration = prefersReducedMotion ? 0 : 560;
    animationTimer = window.setTimeout(() => {
      if (complete) currentPage += direction;
      turnDirection = 0;
      turnProgress = 0;
      isAnimating = false;
      animationTimer = 0;
    }, duration);
  };

  const turnPage = (direction: Direction) => {
    if (isAnimating || activePointerId !== null || !canTurn(direction)) return;

    turnDirection = direction;
    turnProgress = direction === -1 ? 0.001 : 0;

    requestAnimationFrame(() => {
      requestAnimationFrame(() => settleTurn(direction, true));
    });
  };

  const isInteractiveTarget = (target: EventTarget | null) =>
    target instanceof Element && Boolean(target.closest('a, button, input, textarea, select'));

  const resetPointer = () => {
    activePointerId = null;
    pointerMoved = false;
  };

  const handlePointerDown = (event: PointerEvent) => {
    if (isAnimating || activePointerId !== null || isInteractiveTarget(event.target)) return;
    if (event.pointerType === 'mouse' && event.button !== 0) return;

    activePointerId = event.pointerId;
    pointerStartX = event.clientX;
    pointerStartY = event.clientY;
    pointerStartedAt = performance.now();
    pointerWidth = Math.max(1, stackElement?.getBoundingClientRect().width ?? 1);
    pointerMoved = false;
  };

  const handlePointerMove = (event: PointerEvent) => {
    if (activePointerId !== event.pointerId || isAnimating) return;

    const dx = event.clientX - pointerStartX;
    const dy = event.clientY - pointerStartY;
    const distance = Math.hypot(dx, dy);

    if (!pointerMoved && distance < 7) return;

    if (!pointerMoved && Math.abs(dy) > Math.abs(dx) * 1.15) {
      resetPointer();
      turnDirection = 0;
      turnProgress = 0;
      return;
    }

    pointerMoved = true;
    if (event.cancelable) event.preventDefault();

    const direction: Direction = dx < 0 ? 1 : -1;

    if (!canTurn(direction)) {
      turnDirection = 0;
      turnProgress = 0;
      return;
    }

    turnDirection = direction;
    turnProgress = Math.min(0.96, (Math.abs(dx) / pointerWidth) * 1.45);
  };

  const releasePointer = (event: PointerEvent, cancelled = false) => {
    if (activePointerId !== event.pointerId) return;

    const dx = event.clientX - pointerStartX;
    const elapsed = Math.max(1, performance.now() - pointerStartedAt);
    const velocity = Math.abs(dx) / elapsed;
    const didMove = pointerMoved;
    const direction = turnDirection;

    resetPointer();

    if (!didMove) return;

    ignoreClicksUntil = performance.now() + 450;

    if (!direction) {
      turnProgress = 0;
      return;
    }

    if (cancelled) {
      settleTurn(direction, false);
      return;
    }

    const shouldComplete = turnProgress >= 0.24 || velocity >= 0.38;
    settleTurn(direction, shouldComplete);
  };

  const handleStackClick = (event: MouseEvent) => {
    if (isInteractiveTarget(event.target)) return;

    if (performance.now() < ignoreClicksUntil) return;

    if (isAnimating || activePointerId !== null) return;

    const bounds = stackElement?.getBoundingClientRect();
    if (!bounds) return;

    const relativeX = (event.clientX - bounds.left) / bounds.width;

    if (currentPage === 0) {
      turnPage(1);
    } else if (relativeX < 0.32 && canTurn(-1)) {
      turnPage(-1);
    } else if (canTurn(1)) {
      turnPage(1);
    } else {
      turnPage(-1);
    }
  };

  const handleWindowKeyDown = (event: KeyboardEvent) => {
    if (isInteractiveTarget(event.target)) return;

    if (event.key === 'ArrowRight' || event.key === 'PageDown') {
      event.preventDefault();
      turnPage(1);
    }

    if (event.key === 'ArrowLeft' || event.key === 'PageUp') {
      event.preventDefault();
      turnPage(-1);
    }
  };

  onMount(() => {
    const media = window.matchMedia('(prefers-reduced-motion: reduce)');
    const updateMotionPreference = () => (prefersReducedMotion = media.matches);
    updateMotionPreference();

    const stack = stackElement;
    if (!stack) return;

    const handlePointerCancel = (event: PointerEvent) => releasePointer(event, true);

    stack.addEventListener('pointerdown', handlePointerDown);
    stack.addEventListener('click', handleStackClick);
    window.addEventListener('pointermove', handlePointerMove, { passive: false });
    window.addEventListener('pointerup', releasePointer);
    window.addEventListener('pointercancel', handlePointerCancel);
    window.addEventListener('keydown', handleWindowKeyDown);
    media.addEventListener('change', updateMotionPreference);

    return () => {
      clearAnimationTimer();
      stack.removeEventListener('pointerdown', handlePointerDown);
      stack.removeEventListener('click', handleStackClick);
      window.removeEventListener('pointermove', handlePointerMove);
      window.removeEventListener('pointerup', releasePointer);
      window.removeEventListener('pointercancel', handlePointerCancel);
      window.removeEventListener('keydown', handleWindowKeyDown);
      media.removeEventListener('change', updateMotionPreference);
    };
  });
</script>

<section class="about-page-turner" aria-label="About Cyrus Asasi">
  <div
    class="about-stack"
    class:is-dragging={activePointerId !== null}
    bind:this={stackElement}
    role="group"
    aria-label={`About page ${currentPage + 1} of ${pages.length}: ${pages[currentPage].label}`}
  >
    {#each pages as page, index}
      <article
        class="about-sheet"
        class:is-current={index === currentPage}
        class:is-future={index > currentPage}
        class:is-past={index < currentPage}
        class:is-turning={
          (turnDirection === 1 && index === currentPage) ||
          (turnDirection === -1 && index === currentPage - 1)
        }
        class:is-turning-forward={turnDirection === 1 && index === currentPage}
        class:is-turning-backward={turnDirection === -1 && index === currentPage - 1}
        style={pageStyle(index, currentPage, turnProgress)}
        aria-hidden={index !== currentPage && !(turnDirection === -1 && index === currentPage - 1)}
        inert={index !== currentPage && !(turnDirection === -1 && index === currentPage - 1)}
      >
        <div class="about-sheet__front">
          {#if page.id === 'cover'}
            <div class="sheet-cover">
              <p class="sheet-eyebrow">ABOUT</p>
              <h1>CYRUS ASASI</h1>
              <p class="sheet-subtitle">clarinetist + software engineer</p>
              <p class="sheet-location">Los Angeles, CA</p>
            </div>
          {:else if page.id === 'bio'}
            <div class="sheet-content sheet-content--reading">
              <p class="sheet-eyebrow">ABOUT</p>
              <h2>A little about me.</h2>
              <div class="sheet-copy">
                <p>
                  I'm a software engineer and classical musician who enjoys mastering difficult skills. Whether
                  it's reverse engineering complex systems, performing concertos, or building interactive web
                  experiences, I'm happiest when I'm learning something challenging.
                </p>
                <p>
                  I completed dual bachelor's degrees in Computer Science and Music Performance at UCLA and am now
                  pursuing a Master's in Music Performance while continuing to build software projects.
                </p>
              </div>
            </div>
          {:else if page.id === 'software'}
            <div class="sheet-content sheet-content--reading">
              <p class="sheet-eyebrow">SOFTWARE</p>
              <h2>I like taking things apart.</h2>
              <div class="sheet-copy">
                <p>
                  I love building software that's functional, efficient, and enjoyable to use. Much of my
                  professional experience has been in reverse engineering: understanding complex systems, then
                  rebuilding them in cleaner and more useful ways.
                </p>
                <p>
                  Outside of work, I build web applications, developer tools, and small experiments whenever I find
                  a problem worth solving.
                </p>
              </div>
              <a class="sheet-link" href={resumesUrl}>View resumes <span aria-hidden="true">↗</span></a>
            </div>
          {:else if page.id === 'music'}
            <div class="sheet-content sheet-content--reading">
              <p class="sheet-eyebrow">MUSIC</p>
              <h2>A lifelong obsession.</h2>
              <div class="sheet-copy">
                <p>
                  I'm a clarinetist and pianist currently pursuing a Master's in Music Performance at UCLA. In 2026,
                  I won UCLA's All-Stars Competition and performed as a concerto soloist with the UCLA Philharmonia.
                </p>
                <p>
                  I almost exclusively listen to classical music. Brahms, Ravel, and Kapustin are current favorites.
                </p>
              </div>
              <a class="sheet-link" href={musicVideoUrl} target="_blank" rel="noopener noreferrer">
                Watch a performance <span aria-hidden="true">↗</span>
              </a>
            </div>
          {:else}
            <div class="sheet-content sheet-content--interests">
              <p class="sheet-eyebrow">ELSEWHERE</p>
              <h2>Off the clock.</h2>

              <div class="interest-note">
                <span class="interest-note__number">01</span>
                <div>
                  <h3>Pickleball</h3>
                  <p>
                    I compete at the 5.0 level and captain the UCLA Pickleball Team. A favorite result was winning
                    the California Collegiate Super Regional Championship.
                  </p>
                  <a href={pickleballArticleUrl} target="_blank" rel="noopener noreferrer">
                    Tournament recap <span aria-hidden="true">↗</span>
                  </a>
                </div>
              </div>

              <div class="interest-note">
                <span class="interest-note__number">02</span>
                <div>
                  <h3>Chess</h3>
                  <p>
                    I've played since middle school and reached a peak online rating of 2450. I still love the game
                    for the same pattern recognition and analytical thinking that drew me to computer science.
                  </p>
                  <a href={chessProfileUrl} target="_blank" rel="noopener noreferrer">
                    Chess.com profile <span aria-hidden="true">↗</span>
                  </a>
                </div>
              </div>
            </div>
          {/if}

          <span class="sheet-number" aria-hidden="true">
            {String(index + 1).padStart(2, '0')} / {String(pages.length).padStart(2, '0')}
          </span>

          {#if index < pages.length - 1}
            <span class="sheet-corner" aria-hidden="true">
              <span class="sheet-corner__paper"></span>
            </span>
          {/if}

          <span class="sheet-turn-shade" aria-hidden="true"></span>
        </div>

        <div class="about-sheet__back" aria-hidden="true">
          <span class="sheet-back-shadow"></span>
        </div>
      </article>
    {/each}
  </div>

  <p class="page-turn-hint" aria-hidden="true">
    <span class="page-turn-hint__desktop">click the page · swipe to turn</span>
    <span class="page-turn-hint__mobile">tap · swipe to turn</span>
  </p>
</section>
