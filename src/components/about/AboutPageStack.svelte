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
  type PageSide = 'left' | 'right';
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
      title: 'Cyrus Asasi',
      paragraphs: [
        "I split most of my time between code and music. I studied Computer Science and clarinet performance at UCLA, and I'm back there now for a master's in clarinet.",
        "I tend to get obsessed with things that are hard to get exactly right: taking apart strange systems, building something for the web, learning a difficult piece, or chasing a tiny detail until it finally feels right.",
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
      title: 'I like taking things apart',
      paragraphs: [
        "I've always liked figuring out how things work. A lot of my work has involved reverse engineering: digging through a system until it makes sense, then rebuilding the useful parts more cleanly.",
        "Most of my side projects start the same way: something bothers me, I wonder if I can make it better, and I lose a few evenings to it.",
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
      title: 'Music has always been there',
      paragraphs: [
        "Clarinet has been the constant for most of my life. I'm currently doing my master's at UCLA, where I also did my undergraduate music degree alongside computer science.",
        "In 2026 I got to solo with the UCLA Philharmonia after winning the All-Stars Competition. I also play piano, mostly because I love chamber music. I listen to an unreasonable amount of Brahms, Ravel, and Kapustin.",
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
      title: 'Away from the desk',
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
  let pointerSide: PageSide | null = null;
  let ignoreClicksUntil = 0;
  let animationFrame = 0;

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

  const clamp01 = (value: number) => Math.min(1, Math.max(0, value));

  const geometryProgress = (direction: Direction | 0, progress: number) => {
    const clamped = clamp01(progress);
    return direction === -1 ? 1 - clamped : clamped;
  };

  const leafStyle = (direction: Direction | 0, progress: number) => {
    const pageProgress = geometryProgress(direction, progress);
    const arc = Math.sin(Math.PI * pageProgress);
    const angle = -180 * pageProgress;
    const lift = arc * 0.24;
    const depth = arc * 1.35;
    const skew = Math.sin(Math.PI * pageProgress) * Math.cos(Math.PI * pageProgress) * -1.25;
    const compression = 1 - arc * 0.045;
    const curlInset = arc * 2.2;
    const curlTip = arc * 1.35;
    const radius = 0.14 + arc * 0.62;
    const highlightOpacity = arc * 0.14;
    const edgeOpacity = 0.36 + arc * 0.42;

    return [
      `--leaf-angle:${angle.toFixed(3)}deg`,
      `--leaf-lift:${lift.toFixed(3)}rem`,
      `--leaf-depth:${depth.toFixed(3)}rem`,
      `--leaf-skew:${skew.toFixed(3)}deg`,
      `--leaf-compression:${compression.toFixed(4)}`,
      `--leaf-curl-inset:${curlInset.toFixed(3)}%`,
      `--leaf-curl-tip:${curlTip.toFixed(3)}%`,
      `--leaf-radius:${radius.toFixed(3)}rem`,
      `--leaf-highlight-opacity:${highlightOpacity.toFixed(3)}`,
      `--leaf-edge-opacity:${edgeOpacity.toFixed(3)}`,
    ].join(';');
  };

  const clearAnimationFrame = () => {
    if (!animationFrame) return;
    window.cancelAnimationFrame(animationFrame);
    animationFrame = 0;
  };

  const finishTurn = (direction: Direction, complete: boolean) => {
    if (complete) currentSpread += direction;
    turnDirection = 0;
    turnProgress = 0;
    isAnimating = false;
    animationFrame = 0;
  };

  const settleTurn = (direction: Direction, complete: boolean) => {
    if (!turnDirection || !canTurn(direction)) {
      turnDirection = 0;
      turnProgress = 0;
      isAnimating = false;
      return;
    }

    clearAnimationFrame();
    isAnimating = true;

    const startProgress = turnProgress;
    const targetProgress = complete ? 1 : 0;
    const distance = Math.abs(targetProgress - startProgress);

    if (prefersReducedMotion || distance < 0.001) {
      turnProgress = targetProgress;
      finishTurn(direction, complete);
      return;
    }

    const startedAt = performance.now();
    const duration = Math.max(260, 960 * distance);

    const tick = (now: number) => {
      const elapsed = Math.min(1, (now - startedAt) / duration);
      // Sine ease gives the page enough time around 90° for the bend and
      // changing underside to be visible instead of reading as a card flip.
      const eased = 0.5 - Math.cos(Math.PI * elapsed) / 2;
      turnProgress = startProgress + (targetProgress - startProgress) * eased;

      if (elapsed < 1) {
        animationFrame = window.requestAnimationFrame(tick);
      } else {
        turnProgress = targetProgress;
        finishTurn(direction, complete);
      }
    };

    animationFrame = window.requestAnimationFrame(tick);
  };

  const turnPage = (direction: Direction) => {
    if (isAnimating || activePointerId !== null || !canTurn(direction)) return;

    turnDirection = direction;
    turnProgress = 0;

    // Let Svelte mount the physical leaf before advancing its geometry.
    requestAnimationFrame(() => settleTurn(direction, true));
  };

  const isInteractiveTarget = (target: EventTarget | null) =>
    target instanceof Element && Boolean(target.closest('a, button, input, textarea, select'));

  const resetPointer = () => {
    activePointerId = null;
    pointerMoved = false;
    pointerSide = null;
  };

  const handlePointerDown = (event: PointerEvent) => {
    if (isAnimating || activePointerId !== null || isInteractiveTarget(event.target)) return;
    if (event.pointerType === 'mouse' && event.button !== 0) return;

    const bounds = bookElement?.getBoundingClientRect();
    const page = event.target instanceof Element ? event.target.closest('.book-page--left, .book-page--right') : null;
    if (!bounds || !page) return;

    const side: PageSide = page.classList.contains('book-page--right') ? 'right' : 'left';
    const direction: Direction = side === 'right' ? 1 : -1;

    // A closed end of the book is deliberately inert. The first spread cannot
    // be pulled backward and the final spread cannot be pulled forward.
    if (!canTurn(direction)) return;

    activePointerId = event.pointerId;
    pointerSide = side;
    pointerStartX = event.clientX;
    pointerStartY = event.clientY;
    pointerStartedAt = performance.now();
    pointerWidth = Math.max(1, bounds.width / 2);
    pointerMoved = false;
  };

  const handlePointerMove = (event: PointerEvent) => {
    if (activePointerId !== event.pointerId || isAnimating || !pointerSide) return;

    const dx = event.clientX - pointerStartX;
    const dy = event.clientY - pointerStartY;
    const distance = Math.hypot(dx, dy);

    if (!pointerMoved && distance < 7) return;

    if (!pointerMoved && Math.abs(dy) > Math.abs(dx) * 1.15) {
      ignoreClicksUntil = performance.now() + 250;
      resetPointer();
      turnDirection = 0;
      turnProgress = 0;
      return;
    }

    pointerMoved = true;
    if (event.cancelable) event.preventDefault();

    const direction: Direction = pointerSide === 'right' ? 1 : -1;
    const travel = direction === 1 ? -dx : dx;

    // Right pages only turn forward (drag left). Left pages only turn backward
    // (drag right). Pulling a page the wrong way leaves it attached to the book.
    if (travel <= 0 || !canTurn(direction)) {
      turnDirection = 0;
      turnProgress = 0;
      return;
    }

    turnDirection = direction;
    turnProgress = Math.min(0.985, (travel / pointerWidth) * 1.08);
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

    const page = event.target instanceof Element ? event.target.closest('.book-page--left, .book-page--right') : null;
    if (!page) return;

    const direction: Direction = page.classList.contains('book-page--right') ? 1 : -1;

    // Only the physical page itself responds. The binding, boards and page
    // edges are inert, and canTurn() keeps the closed ends of the book inert.
    turnPage(direction);
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
      clearAnimationFrame();
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
              Pickleball started as something casual and got a little out of hand. I play around the 5.0 level and
              captain UCLA's team. Winning the California Collegiate Super Regional is still one of my favorite team memories.
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
              Chess was my first serious obsession. I started in middle school and eventually hit 2450 online. I play
              less now, but I still love the calculation and pattern recognition that made me stick with it in the first place.
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
    class:can-turn-backward={currentSpread > 0}
    class:can-turn-forward={currentSpread < spreads.length - 1}
    bind:this={bookElement}
    role="group"
    aria-label={`About spread ${currentSpread + 1} of ${spreads.length}: ${spreads[currentSpread].label}`}
  >
    <div class="about-book__board" aria-hidden="true"></div>
    <span class="about-book__spine" aria-hidden="true"></span>
    <span class="book-page-block book-page-block--left" aria-hidden="true"></span>
    <span class="book-page-block book-page-block--right" aria-hidden="true"></span>

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
</section>
