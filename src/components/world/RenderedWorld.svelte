<script lang="ts">
  import { onDestroy, onMount } from 'svelte';
  import { withBase } from '@/lib/paths';

  type Bounds = { x: number; y: number; width: number; height: number };
  type Hotspot = {
    id: string;
    label: string;
    href?: string;
    targetView?: string;
    bounds: Bounds;
  };
  type WorldView = {
    id: string;
    label: string;
    description?: string;
    image: string;
    fallbackImage?: string;
    width: number;
    height: number;
    hotspots: Hotspot[];
  };
  type Manifest = {
    version: number;
    startView: string;
    views: WorldView[];
  };

  export let manifestUrl: string;
  export let startViewId: string | undefined = undefined;

  let manifest: Manifest | null = null;
  let activeView: WorldView | null = null;
  let previousImage = '';
  let currentImage = '';
  let imageFailed = false;
  let loading = true;
  let error = '';
  let hoveredId: string | null = null;
  let transitionTimer: number | null = null;

  const resolveAsset = (value?: string) => (value ? withBase(value) : '');

  function findView(id: string) {
    return manifest?.views.find((view) => view.id === id) ?? null;
  }

  function preload(src: string) {
    if (!src || typeof Image === 'undefined') return;
    const image = new Image();
    image.decoding = 'async';
    image.src = src;
  }

  function preloadNeighbors(view: WorldView) {
    for (const hotspot of view.hotspots) {
      if (!hotspot.targetView) continue;
      const target = findView(hotspot.targetView);
      if (!target) continue;
      preload(resolveAsset(target.image || target.fallbackImage));
    }
  }

  function showView(view: WorldView, animate = true) {
    const nextImage = resolveAsset(view.image || view.fallbackImage);
    if (animate && currentImage && currentImage !== nextImage) {
      previousImage = currentImage;
      if (transitionTimer !== null) window.clearTimeout(transitionTimer);
      transitionTimer = window.setTimeout(() => {
        previousImage = '';
        transitionTimer = null;
      }, 760);
    } else {
      previousImage = '';
    }
    activeView = view;
    currentImage = nextImage;
    imageFailed = false;
    hoveredId = null;
    preloadNeighbors(view);
  }

  function handleImageError() {
    if (!activeView || imageFailed || !activeView.fallbackImage) return;
    imageFailed = true;
    currentImage = resolveAsset(activeView.fallbackImage);
  }

  function activate(hotspot: Hotspot) {
    if (hotspot.targetView) {
      const target = findView(hotspot.targetView);
      if (target) {
        showView(target, true);
        return;
      }
    }
    if (hotspot.href && typeof window !== 'undefined') {
      window.location.assign(resolveAsset(hotspot.href));
    }
  }

  onMount(async () => {
    try {
      const response = await fetch(manifestUrl, { cache: 'no-cache' });
      if (!response.ok) throw new Error(`World manifest returned ${response.status}`);
      manifest = (await response.json()) as Manifest;
      const initial = findView(startViewId ?? manifest.startView) ?? manifest.views[0] ?? null;
      if (!initial) throw new Error('World manifest contains no views');
      showView(initial, false);
    } catch (reason) {
      error = reason instanceof Error ? reason.message : 'Unable to load the rendered world';
    } finally {
      loading = false;
    }
  });

  onDestroy(() => {
    if (transitionTimer !== null && typeof window !== 'undefined') {
      window.clearTimeout(transitionTimer);
    }
  });
</script>

<div
  class="rendered-world"
  class:is-loading={loading}
  class:has-error={Boolean(error)}
  style:--world-aspect={activeView ? `${activeView.width} / ${activeView.height}` : '3 / 2'}
  aria-label={activeView?.description ?? 'Explore the house'}
>
  {#if activeView}
    <div class="rendered-world__frame">
      {#if previousImage}
        <img class="rendered-world__image rendered-world__image--previous" src={previousImage} alt="" aria-hidden="true" />
      {/if}
      <img
        class="rendered-world__image rendered-world__image--current"
        src={currentImage}
        alt=""
        aria-hidden="true"
        draggable="false"
        on:error={handleImageError}
      />

      <div class="rendered-world__hotspots" aria-label={`${activeView.label} destinations`}>
        {#each activeView.hotspots as hotspot (hotspot.id)}
          <button
            type="button"
            class="rendered-world__hotspot"
            class:is-hovered={hoveredId === hotspot.id}
            style:left={`${hotspot.bounds.x * 100}%`}
            style:top={`${hotspot.bounds.y * 100}%`}
            style:width={`${hotspot.bounds.width * 100}%`}
            style:height={`${hotspot.bounds.height * 100}%`}
            aria-label={hotspot.label}
            on:mouseenter={() => (hoveredId = hotspot.id)}
            on:mouseleave={() => (hoveredId = null)}
            on:focus={() => (hoveredId = hotspot.id)}
            on:blur={() => (hoveredId = null)}
            on:click={() => activate(hotspot)}
          >
            <span class="rendered-world__label">{hotspot.label}</span>
          </button>
        {/each}
      </div>
    </div>
  {:else if loading}
    <div class="rendered-world__status" aria-live="polite">Loading house…</div>
  {:else if error}
    <div class="rendered-world__status" aria-live="polite">{error}</div>
  {/if}
</div>

<style>
  .rendered-world {
    position: relative;
    width: 100%;
    aspect-ratio: var(--world-aspect, 3 / 2);
    contain: layout paint;
  }

  .rendered-world__frame,
  .rendered-world__image,
  .rendered-world__hotspots {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
  }

  .rendered-world__frame {
    isolation: isolate;
  }

  .rendered-world__image {
    display: block;
    object-fit: contain;
    user-select: none;
    pointer-events: none;
  }

  .rendered-world__image--previous {
    z-index: 0;
    animation: world-image-out 720ms cubic-bezier(0.22, 1, 0.36, 1) forwards;
  }

  .rendered-world__image--current {
    z-index: 1;
    animation: world-image-in 720ms cubic-bezier(0.22, 1, 0.36, 1) both;
  }

  .rendered-world__hotspots {
    z-index: 2;
    pointer-events: none;
  }

  .rendered-world__hotspot {
    position: absolute;
    display: grid;
    place-items: end center;
    margin: 0;
    padding: 0;
    appearance: none;
    border: 0;
    background: transparent;
    color: inherit;
    cursor: pointer;
    pointer-events: auto;
  }

  .rendered-world__hotspot:focus-visible {
    outline: 1px solid color-mix(in srgb, var(--accent) 62%, transparent);
    outline-offset: 2px;
  }

  .rendered-world__label {
    position: absolute;
    left: 50%;
    top: calc(100% + 0.45rem);
    translate: -50% 0.2rem;
    padding: 0.18rem 0.36rem;
    border-radius: 0.2rem;
    background: color-mix(in srgb, var(--bg) 88%, transparent);
    color: var(--text);
    font-family: var(--font-mono);
    font-size: clamp(0.56rem, 0.72vw, 0.66rem);
    font-weight: 500;
    letter-spacing: 0.015em;
    line-height: 1.15;
    opacity: 0;
    white-space: nowrap;
    pointer-events: none;
    transition: opacity 360ms ease, translate 360ms cubic-bezier(0.22, 1, 0.36, 1);
  }

  .rendered-world__hotspot:is(:hover, :focus-visible) .rendered-world__label {
    translate: -50% 0;
    opacity: 1;
  }

  .rendered-world__status {
    position: absolute;
    inset: 0;
    display: grid;
    place-items: center;
    color: var(--muted);
    font-family: var(--font-mono);
    font-size: 0.72rem;
  }

  @keyframes world-image-in {
    from { opacity: 0; }
    to { opacity: 1; }
  }

  @keyframes world-image-out {
    from { opacity: 1; }
    to { opacity: 0; }
  }

  @media (prefers-reduced-motion: reduce) {
    .rendered-world__image,
    .rendered-world__label {
      animation: none !important;
      transition: none !important;
    }
  }
</style>
