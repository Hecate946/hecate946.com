<script lang="ts">
  import PixiWebsiteGraph from '@/components/graphs/PixiWebsiteGraph.svelte';
  import type { NetworkLink, NetworkNode } from '@/components/graphs/types';

  export let nodes: NetworkNode[] = [];
  export let links: NetworkLink[] = [];
  let graph: { resetView: () => void } | null = null;

  const graphLinks = links.map((link) => ({
    ...link,
    distance: link.kind === 'secondary' ? 78 : 108,
    strength: link.kind === 'secondary' ? 0.19 : 0.16,
    curve: 0,
  }));
</script>

<section class="website-graph" aria-labelledby="website-graph-title" data-site-sound-silent>
  <header class="website-graph__toolbar">
    <span class="website-graph__toolbar-spacer" aria-hidden="true"></span>

    <h1 id="website-graph-title">Website Graph</h1>

    <button
      class="website-graph__toolbar-button website-graph__center"
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
  </header>

  <p class="website-graph__instructions">
    Scroll or pinch to zoom. Drag empty space to pan. Drag nodes to rearrange
    them. Use Center graph to restore the fitted view.
  </p>

  <div class="website-graph__stage">
    <PixiWebsiteGraph
      bind:this={graph}
      nodes={nodes}
      links={graphLinks}
      ariaLabel="Zoomable force graph of every destination on the site"
    />
  </div>
</section>

<style>
  .website-graph {
    --website-graph-toolbar-height: 3.55rem;
    --website-graph-font: system-ui, -apple-system, BlinkMacSystemFont,
      "Segoe UI", Ubuntu, Roboto, "Noto Sans", "Helvetica Neue", Arial,
      sans-serif;

    display: grid;
    width: 100%;
    height: 100%;
    min-width: 0;
    min-height: 0;
    grid-template-rows: var(--website-graph-toolbar-height) minmax(0, 1fr);
    overflow: hidden;
    background-color: var(--bg);
    color: var(--text);
    font-family: var(--website-graph-font);
    overscroll-behavior: none;
  }

  .website-graph__toolbar {
    position: relative;
    z-index: 4;
    display: grid;
    width: 100%;
    height: var(--website-graph-toolbar-height);
    min-width: 0;
    grid-template-columns: 3.65rem minmax(0, 1fr) 3.65rem;
    align-items: center;
    padding: 0 0.5rem;
    border-bottom: 1px solid var(--line);
    background: var(--bg);
  }

  .website-graph__toolbar h1 {
    grid-column: 2;
    margin: 0;
    overflow: hidden;
    color: var(--text);
    font-family: var(--website-graph-font);
    font-size: 0.9rem;
    font-weight: 500;
    letter-spacing: 0.006em;
    line-height: 1;
    text-align: center;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .website-graph__toolbar-button {
    display: grid;
    width: 3rem;
    height: 3rem;
    place-items: center;
    padding: 0;
    border: 0;
    border-radius: 0.42rem;
    background: transparent;
    color: var(--muted);
    cursor: pointer;
    text-decoration: none;
    transition:
      color 420ms cubic-bezier(0.22, 1, 0.36, 1),
      background-color 420ms cubic-bezier(0.22, 1, 0.36, 1),
      opacity 420ms cubic-bezier(0.22, 1, 0.36, 1);
  }

  .website-graph__toolbar-spacer {
    grid-column: 1;
  }

  .website-graph__center {
    grid-column: 3;
    justify-self: end;
  }

  .website-graph__toolbar-button:hover,
  .website-graph__toolbar-button:focus-visible {
    background: color-mix(in srgb, var(--text) 9%, transparent);
    color: var(--accent);
  }

  .website-graph__toolbar-button svg {
    width: 1.62rem;
    height: 1.62rem;
    overflow: visible;
    fill: none;
    stroke: currentColor;
    stroke-linecap: round;
    stroke-linejoin: round;
    stroke-width: 1.72;
  }

  .website-graph__stage {
    width: 100%;
    height: 100%;
    min-width: 0;
    min-height: 0;
    overflow: hidden;
    background-color: var(--bg);
    overscroll-behavior: none;
  }

  .website-graph__stage :global(.pixi-website-graph) {
    width: 100%;
    height: 100%;
    min-height: 0;
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
    .website-graph {
      --website-graph-toolbar-height: 3.35rem;
    }

    .website-graph__toolbar {
      grid-template-columns: 3.35rem minmax(0, 1fr) 3.35rem;
      padding: 0 0.3rem;
    }

    .website-graph__toolbar h1 {
      font-size: 0.84rem;
    }

    .website-graph__toolbar-button {
      width: 2.8rem;
      height: 2.8rem;
    }

    .website-graph__toolbar-button svg {
      width: 1.5rem;
      height: 1.5rem;
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .website-graph__toolbar-button {
      transition: none;
    }
  }
</style>
