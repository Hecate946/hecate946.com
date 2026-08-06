<script lang="ts">
  import PixiWebsiteGraph from '@/components/graphs/PixiWebsiteGraph.svelte';
  import type { NetworkLink, NetworkNode } from '@/components/graphs/types';

  export let nodes: NetworkNode[] = [];
  export let links: NetworkLink[] = [];
  let graph: { resetView: () => void } | null = null;

  const graphLinks = links.map((link) => ({
    ...link,
    distance: link.kind === 'secondary' ? 138 : 176,
    strength: link.kind === 'secondary' ? 0.17 : 0.12,
    curve: 0,
  }));
</script>

<section class="website-graph" aria-label="Website Graph" data-site-sound-silent>
  <div class="website-graph__stage">
    <PixiWebsiteGraph
      bind:this={graph}
      nodes={nodes}
      links={graphLinks}
      ariaLabel="Zoomable force graph of every destination on the site"
    />
  </div>

  <button
    class="website-graph__center"
    type="button"
    aria-label="Center graph view"
    title="Center graph"
    on:click={() => graph?.resetView()}
  >
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M8 3H3v5M16 3h5v5M21 16v5h-5M3 16v5h5"></path>
      <circle cx="12" cy="12" r="2.25"></circle>
    </svg>
  </button>

  <p class="website-graph__instructions">
    Scroll or pinch to zoom. Drag empty space to pan. Drag nodes to rearrange
    them. Use Center graph to restore the fitted view.
  </p>
</section>

<style>
  .website-graph {
    --website-graph-font: system-ui, -apple-system, BlinkMacSystemFont,
      "Segoe UI", Ubuntu, Roboto, "Noto Sans", "Helvetica Neue", Arial,
      sans-serif;

    position: relative;
    width: 100%;
    height: 100%;
    min-width: 0;
    min-height: 0;
    overflow: hidden;
    background: var(--bg);
    color: var(--text);
    font-family: var(--website-graph-font);
    overscroll-behavior: none;
  }

  .website-graph__stage {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    min-width: 0;
    min-height: 0;
    overflow: hidden;
    background: var(--bg);
    overscroll-behavior: none;
  }

  .website-graph__stage :global(.pixi-website-graph) {
    width: 100%;
    height: 100%;
    min-height: 0;
  }

  .website-graph__center {
    position: absolute;
    top: 0.75rem;
    right: 0.75rem;
    z-index: 4;
    display: grid;
    width: 3rem;
    height: 3rem;
    place-items: center;
    padding: 0;
    border: 1px solid color-mix(in srgb, var(--text) 28%, transparent);
    border-radius: 0.52rem;
    outline: 2px solid transparent;
    outline-offset: 1px;
    background: color-mix(in srgb, var(--bg) 92%, transparent);
    color: var(--muted);
    cursor: pointer;
    transition:
      border-color 220ms ease,
      outline-color 220ms ease,
      background-color 220ms ease,
      color 220ms ease,
      transform 220ms ease;
  }

  .website-graph__center:hover,
  .website-graph__center:focus-visible {
    border-color: color-mix(in srgb, var(--text) 48%, transparent);
    outline-color: color-mix(in srgb, var(--text) 18%, transparent);
    background: color-mix(in srgb, var(--text) 8%, var(--bg));
    color: var(--text);
    transform: translateY(-1px);
  }

  .website-graph__center svg {
    width: 1.62rem;
    height: 1.62rem;
    overflow: visible;
    fill: none;
    stroke: currentColor;
    stroke-linecap: round;
    stroke-linejoin: round;
    stroke-width: 1.72;
  }

  .website-graph__instructions {
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip: rect(0 0 0 0);
    white-space: nowrap;
    border: 0;
  }

  @media (max-width: 44rem) {
    .website-graph__center {
      top: 0.55rem;
      right: 0.55rem;
      width: 2.8rem;
      height: 2.8rem;
    }

    .website-graph__center svg {
      width: 1.5rem;
      height: 1.5rem;
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .website-graph__center {
      transition: none;
    }
  }
</style>
