<script lang="ts">
  import { onMount } from 'svelte';

  export let musicVideoUrl: string;
  export let pickleballArticleUrl: string;
  export let chessProfileUrl: string;
  export let resumesUrl: string;
  export let portraitUrl: string;
  export let softwareImageUrl: string;
  export let musicImageUrl: string;
  export let pickleballImageUrl: string;

  type Direction = -1 | 1;
  type VisualMode = 'portrait' | 'screen' | 'document' | 'photo';

  type Spread = {
    id: 'about' | 'software' | 'music' | 'interests';
    label: string;
    eyebrow: string;
    title: string;
    paragraphs?: string[];
    visual: {
      src: string;
      alt: string;
      caption: string;
      mode: VisualMode;
    };
    link?: {
      href: string;
      label: string;
      external?: boolean;
    };
  };

  const spreads: Spread[] = [
    {
      id: 'about',
      label: 'About',
      eyebrow: 'ABOUT',
      title: 'Cyrus Asasi.',
      paragraphs: [
        "I'm a software engineer and classical musician who enjoys mastering difficult skills. Whether it's reverse engineering complex systems, performing concertos, or building interactive web experiences, I'm happiest when I'm learning something challenging.",
        "I completed dual bachelor's degrees in Computer Science and Music Performance at UCLA and am now pursuing a Master's in Music Performance while continuing to build software projects.",
      ],
      visual: {
        src: portraitUrl,
        alt: 'Portrait of Cyrus Asasi',
        caption: 'Los Angeles, California',
        mode: 'portrait',
      },
    },
    {
      id: 'software',
      label: 'Software',
      eyebrow: 'SOFTWARE',
      title: 'I like taking things apart.',
      paragraphs: [
        "I love building software that's functional, efficient, and enjoyable to use. Much of my professional experience has been in reverse engineering: understanding complex systems, then rebuilding them in cleaner and more useful ways.",
        'Outside of work, I build web applications, developer tools, and small experiments whenever I find a problem worth solving.',
      ],
      visual: {
        src: softwareImageUrl,
        alt: 'A software project from Cyrus Asasi',
        caption: 'Selected software work',
        mode: 'screen',
      },
      link: {
        href: resumesUrl,
        label: 'View resumes',
      },
    },
    {
      id: 'music',
      label: 'Music',
      eyebrow: 'MUSIC',
      title: 'A lifelong obsession.',
      paragraphs: [
        "I'm a clarinetist and pianist currently pursuing a Master's in Music Performance at UCLA. In 2026, I won UCLA's All-Stars Competition and performed as a concerto soloist with the UCLA Philharmonia.",
        'I almost exclusively listen to classical music. Brahms, Ravel, and Kapustin are current favorites.',
      ],
      visual: {
        src: musicImageUrl,
        alt: 'Clarinet performance résumé for Cyrus Asasi',
        caption: 'Clarinet performance — selected experience',
        mode: 'document',
      },
      link: {
        href: musicVideoUrl,
        label: 'Watch a performance',
        external: true,
      },
    },
    {
      id: 'interests',
      label: 'Elsewhere',
      eyebrow: 'ELSEWHERE',
      title: 'Off the clock.',
      visual: {
        src: pickleballImageUrl,
        alt: 'UCLA Pickleball at the California Collegiate Super Regional',
        caption: 'California Collegiate Super Regional',
        mode: 'photo',
      },
    },
  ];

  let currentSpread = 0;
  let turnDirection: Direction | 0 = 0;
  let turnProgress = 0;
  let isAnimating = false;
  let prefersReducedMotion = false;
  let bookElement: HTMLElement | null = null;

  let activePointerId: number | null = null;
  let pointerStartX = 0;
  let pointerStartY = 0;
  let pointerStartedAt = 0;
  let pointerWidth = 1;
  let pointerMoved = false;
  let ignoreClicksUntil = 0;
  let animationTimer = 0;

  const canTurn = (direction: Direction) =>
    direction === 1 ? currentSpread < spreads.length - 1 : currentSpread > 0;

  const getLeftSpreadIndex = (active: number, direction: Direction | 0) => {
    if (direction === -1) return Math.max(0, active - 1);
    return active;
  };

  const getRightSpreadIndex = (active: number, direction: Direction | 0) => {
    if (direction === 1) return Math.min(spreads.length - 1, active + 1);
    return active;
  };

  const getLeafFrontIndex = (active: number, direction: Direction | 0) => {
    if (direction === -1) return Math.max(0, active - 1);
    return active;
  };

  const getLeafBackIndex = (active: number, direction: Direction | 0) => {
    if (direction === 1) return Math.min(spreads.length - 1, active + 1);
    return active;
  };

  const leafStyle = (direction: Direction | 0, progress: number) => {
    const clamped = Math.min(1, Math.max(0, progress));
    const angle = direction === -1 ? -180 * (1 - clamped) : -180 * clamped;
    const arc = Math.sin(Math.PI * clamped);
    const lift = arc * 0.28;
    const skew = direction === -1 ? -0.35 * arc : 0.35 * arc;

    return [
      `--leaf-angle:${angle.toFixed(3)}deg`,
      `--leaf-lift:${lift.toFixed(3)}rem`,
      `--leaf-skew:${skew.toFixed(3)}deg`,
      `--leaf-shadow-opacity:${(0.08 + arc * 0.28).toFixed(3)}`,
      `--leaf-edge-opacity:${(0.18 + arc * 0.5).toFixed(3)}`,
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

    const duration = prefersReducedMotion ? 0 : 620;
    animationTimer = window.setTimeout(() => {
      if (complete) currentSpread += direction;
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
    pointerWidth = Math.max(1, (bookElement?.getBoundingClientRect().width ?? 2) / 2);
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
    turnProgress = Math.min(0.985, (Math.abs(dx) / pointerWidth) * 1.08);
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

    const shouldComplete = turnProgress >= 0.3 || velocity >= 0.42;
    settleTurn(direction, shouldComplete);
  };

  const handleBookClick = (event: MouseEvent) => {
    if (isInteractiveTarget(event.target)) return;
    if (performance.now() < ignoreClicksUntil) return;
    if (isAnimating || activePointerId !== null) return;

    const bounds = bookElement?.getBoundingClientRect();
    if (!bounds) return;

    const relativeX = (event.clientX - bounds.left) / bounds.width;

    if (currentSpread === 0) {
      turnPage(1);
      return;
    }

    if (currentSpread === spreads.length - 1) {
      turnPage(-1);
      return;
    }

    turnPage(relativeX < 0.5 ? -1 : 1);
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

    const book = bookElement;
    if (!book) return;

    const handlePointerCancel = (event: PointerEvent) => releasePointer(event, true);

    book.addEventListener('pointerdown', handlePointerDown);
    book.addEventListener('click', handleBookClick);
    window.addEventListener('pointermove', handlePointerMove, { passive: false });
    window.addEventListener('pointerup', releasePointer);
    window.addEventListener('pointercancel', handlePointerCancel);
    window.addEventListener('keydown', handleWindowKeyDown);
    media.addEventListener('change', updateMotionPreference);

    return () => {
      clearAnimationTimer();
      book.removeEventListener('pointerdown', handlePointerDown);
      book.removeEventListener('click', handleBookClick);
      window.removeEventListener('pointermove', handlePointerMove);
      window.removeEventListener('pointerup', releasePointer);
      window.removeEventListener('pointercancel', handlePointerCancel);
      window.removeEventListener('keydown', handleWindowKeyDown);
      media.removeEventListener('change', updateMotionPreference);
    };
  });
</script>

{#snippet visualPage(spread: Spread)}
  <div class={`book-visual book-visual--${spread.visual.mode}`}>
    <div class="book-visual__frame">
      <img src={spread.visual.src} alt={spread.visual.alt} draggable="false" />
    </div>
    <div class="book-visual__caption-row">
      <span>{spread.visual.caption}</span>
    </div>
  </div>
{/snippet}

{#snippet contentPage(spread: Spread, spreadIndex: number, interactive: boolean)}
  <div class="book-copy-page">
    <p class="sheet-eyebrow">{spread.eyebrow}</p>
    <h1 class:is-section-title={spreadIndex > 0}>{spread.title}</h1>

    {#if spread.id === 'interests'}
      <div class="interest-list">
        <div class="interest-note">
          <span class="interest-note__number">01</span>
          <div>
            <h2>Pickleball</h2>
            <p>
              I compete at the 5.0 level and captain the UCLA Pickleball Team. A favorite result was winning the
              California Collegiate Super Regional Championship.
            </p>
            {#if interactive}
              <a href={pickleballArticleUrl} target="_blank" rel="noopener noreferrer">
                Tournament recap <span aria-hidden="true">↗</span>
              </a>
            {:else}
              <span class="interest-note__ghost-link">Tournament recap ↗</span>
            {/if}
          </div>
        </div>

        <div class="interest-note">
          <span class="interest-note__number">02</span>
          <div>
            <h2>Chess</h2>
            <p>
              I've played since middle school and reached a peak online rating of 2450. I still love the game for
              the same pattern recognition and analytical thinking that drew me to computer science.
            </p>
            {#if interactive}
              <a href={chessProfileUrl} target="_blank" rel="noopener noreferrer">
                Chess.com profile <span aria-hidden="true">↗</span>
              </a>
            {:else}
              <span class="interest-note__ghost-link">Chess.com profile ↗</span>
            {/if}
          </div>
        </div>
      </div>
    {:else}
      <div class="sheet-copy">
        {#each spread.paragraphs ?? [] as paragraph}
          <p>{paragraph}</p>
        {/each}
      </div>

      {#if spread.link}
        {#if interactive}
          <a
            class="sheet-link"
            href={spread.link.href}
            target={spread.link.external ? '_blank' : undefined}
            rel={spread.link.external ? 'noopener noreferrer' : undefined}
          >
            {spread.link.label} <span aria-hidden="true">↗</span>
          </a>
        {:else}
          <span class="sheet-link sheet-link--ghost">{spread.link.label} ↗</span>
        {/if}
      {/if}
    {/if}

    <span class="book-page-number book-page-number--right" aria-hidden="true">
      {String(spreadIndex * 2 + 2).padStart(2, '0')}
    </span>
  </div>
{/snippet}

<section class="about-page-turner" aria-label="About Cyrus Asasi">
  <div
    class="about-book"
    class:is-dragging={activePointerId !== null}
    bind:this={bookElement}
    role="group"
    aria-label={`About spread ${currentSpread + 1} of ${spreads.length}: ${spreads[currentSpread].label}`}
  >
    <div class="about-book__board" aria-hidden="true"></div>

    <article class="book-page book-page--left" aria-hidden="true">
      {@render visualPage(spreads[getLeftSpreadIndex(currentSpread, turnDirection)])}
      <span class="book-page-number book-page-number--left">
        {String(getLeftSpreadIndex(currentSpread, turnDirection) * 2 + 1).padStart(2, '0')}
      </span>
    </article>

    <article class="book-page book-page--right">
      {@render contentPage(spreads[getRightSpreadIndex(currentSpread, turnDirection)], getRightSpreadIndex(currentSpread, turnDirection), true)}
    </article>

    <span class="book-gutter" aria-hidden="true"></span>

    {#if turnDirection !== 0}
      <article
        class="book-leaf"
        class:is-turning-forward={turnDirection === 1}
        class:is-turning-backward={turnDirection === -1}
        style={leafStyle(turnDirection, turnProgress)}
        aria-hidden="true"
      >
        <div class="book-leaf__face book-leaf__front">
          {@render contentPage(spreads[getLeafFrontIndex(currentSpread, turnDirection)], getLeafFrontIndex(currentSpread, turnDirection), false)}
        </div>
        <div class="book-leaf__face book-leaf__back">
          {@render visualPage(spreads[getLeafBackIndex(currentSpread, turnDirection)])}
          <span class="book-page-number book-page-number--left">
            {String(getLeafBackIndex(currentSpread, turnDirection) * 2 + 1).padStart(2, '0')}
          </span>
        </div>
        <span class="book-leaf__edge" aria-hidden="true"></span>
      </article>
    {/if}
  </div>

  <p class="page-turn-hint" aria-hidden="true">
    <span class="page-turn-hint__desktop">click a page · drag or swipe to turn</span>
    <span class="page-turn-hint__mobile">tap a page · swipe to turn</span>
  </p>
</section>
