<script lang="ts">
  import PixiWebsiteGraph from '@/components/graphs/PixiWebsiteGraph.svelte';
  import type { NetworkLink, NetworkNode } from '@/components/graphs/types';

  export let nodes: NetworkNode[] = [];
  export let links: NetworkLink[] = [];
  let graph: { resetView: () => void } | null = null;
</script>

<section
  class="website-graph"
  aria-label="Website graph"
  aria-describedby="website-graph-instructions"
  data-site-sound-silent
>
  <p id="website-graph-instructions" class="website-graph__instructions">
    Hover or focus a node to reveal its label. Scroll or pinch to zoom. Drag
    empty space to pan, and drag nodes to rearrange them. Use Center graph to
    restore the fitted view.
  </p>

  <div class="website-graph__stage">
    <PixiWebsiteGraph
      bind:this={graph}
      nodes={nodes}
      {links}
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
</section>

<style>
  .website-graph {
    --website-graph-font: system-ui, -apple-system, BlinkMacSystemFont,
      "Segoe UI", Ubuntu, Roboto, "Noto Sans", "Helvetica Neue", Arial,
      sans-serif;

    --graph-bg: #f4f7f6;
    --graph-panel: #eef3f1;
    --graph-text: #172522;
    --graph-muted: #667572;
    --graph-line: #d6dfdc;
    --graph-node: #6f7e7a;
    --graph-node-current: #344b47;
    --graph-node-ring: #f4f7f6;
    --graph-edge: #9ba9a5;
    --graph-label: #1c312d;
    --graph-label-active: #102925;
    --graph-hover: #0b6f69;
    --graph-hover-ring: #e4efed;
    --graph-hover-soft: color-mix(in srgb, #0b6f69 11%, transparent);

    position: relative;
    width: 100%;
    height: 100%;
    min-width: 0;
    min-height: 0;
    overflow: hidden;
    background-color: var(--graph-bg);
    color: var(--graph-text);
    font-family: var(--website-graph-font);
    overscroll-behavior: none;
  }

  :global(html[data-theme='dark']) .website-graph {
    --graph-bg: #0d1312;
    --graph-panel: #111917;
    --graph-text: #e4ebe9;
    --graph-muted: #879592;
    --graph-line: #26322f;
    --graph-node: #93a19d;
    --graph-node-current: #d2dcda;
    --graph-node-ring: #0d1312;
    --graph-edge: #45534f;
    --graph-label: #e5eeeb;
    --graph-label-active: #f2fffc;
    --graph-hover: #0b6f69;
    --graph-hover-ring: #183d38;
    --graph-hover-soft: color-mix(in srgb, #0b6f69 22%, transparent);
  }

  .website-graph__stage {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    min-width: 0;
    min-height: 0;
    overflow: hidden;
    background-color: var(--graph-bg);
    overscroll-behavior: none;
  }

  .website-graph__stage :global(.pixi-website-graph) {
    width: 100%;
    height: 100%;
    min-height: 0;
  }

  .website-graph__center {
    position: absolute;
    top: 0.72rem;
    right: 0.72rem;
    z-index: 4;
    display: grid;
    width: 2.8rem;
    height: 2.8rem;
    place-items: center;
    padding: 0;
    border: 1px solid var(--graph-line);
    border-radius: 0.5rem;
    background: color-mix(in srgb, var(--graph-panel) 92%, transparent);
    color: var(--graph-muted);
    cursor: pointer;
    box-shadow: 0 1px 5px color-mix(in srgb, #000 10%, transparent);
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
    transition:
      color 220ms cubic-bezier(0.22, 1, 0.36, 1),
      background-color 220ms cubic-bezier(0.22, 1, 0.36, 1),
      border-color 220ms cubic-bezier(0.22, 1, 0.36, 1);
  }

  .website-graph__center:hover,
  .website-graph__center:focus-visible {
    border-color: var(--graph-hover);
    background: var(--graph-hover-soft);
    color: var(--graph-hover);
  }

  .website-graph__center:focus-visible {
    outline: 2px solid var(--graph-hover);
    outline-offset: 2px;
  }

  .website-graph__center svg {
    width: 1.48rem;
    height: 1.48rem;
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
      width: 2.65rem;
      height: 2.65rem;
    }

    .website-graph__center svg {
      width: 1.42rem;
      height: 1.42rem;
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .website-graph__center {
      transition: none;
    }
  }
</style>
