<script lang="ts">
  import { onMount } from 'svelte';
  import VoronoiWebsiteGraph from '@/components/graphs/VoronoiWebsiteGraph.svelte';
  import type { NetworkLink, NetworkNode } from '@/components/graphs/types';
  import { WEBSITE_GRAPH_GROUPS } from '@/config/graph';

  export let nodes: NetworkNode[] = [];
  export let links: NetworkLink[] = [];
  export let closeHref = '/';

  type GraphTheme = 'light' | 'dark';

  const GRAPH_THEME_STORAGE_KEY = 'hecate946:graph-theme';

  let graph: { resetView: () => void } | null = null;
  let graphTheme: GraphTheme | null = null;

  function currentSiteTheme(): GraphTheme {
    return document.documentElement.dataset.theme === 'dark' ? 'dark' : 'light';
  }

  function toggleGraphTheme() {
    const current = graphTheme ?? currentSiteTheme();
    graphTheme = current === 'dark' ? 'light' : 'dark';
    try {
      localStorage.setItem(GRAPH_THEME_STORAGE_KEY, graphTheme);
    } catch {
      // The graph still toggles normally when storage is unavailable.
    }
  }

  onMount(() => {
    let storedTheme: string | null = null;
    try {
      storedTheme = localStorage.getItem(GRAPH_THEME_STORAGE_KEY);
    } catch {
      storedTheme = null;
    }

    graphTheme = storedTheme === 'light' || storedTheme === 'dark'
      ? storedTheme
      : currentSiteTheme();
  });
</script>

<section
  class="website-graph"
  data-graph-theme={graphTheme ?? undefined}
  aria-label="Website graph"
  data-site-sound-silent
>
  <VoronoiWebsiteGraph
    bind:this={graph}
    {nodes}
    {links}
    ariaLabel="Force-directed graph of every destination on the website"
    theme={graphTheme}
  />

  <a class="website-graph__control website-graph__close" href={closeHref} aria-label="Close graph" title="Close graph">
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M6 6l12 12M18 6L6 18"></path>
    </svg>
  </a>

  <div class="website-graph__controls-right">
    <button
      class="website-graph__control website-graph__mode"
      type="button"
      aria-label={graphTheme === 'dark' ? 'Switch graph to light mode' : 'Switch graph to dark mode'}
      title={graphTheme === 'dark' ? 'Switch graph to light mode' : 'Switch graph to dark mode'}
      on:click={toggleGraphTheme}
    >
      {graphTheme === 'dark' ? 'Light' : 'Dark'}
    </button>

    <button
      class="website-graph__control website-graph__center"
      type="button"
      aria-label="Center graph"
      title="Center graph"
      on:click={() => graph?.resetView()}
    >
      Center
    </button>
  </div>

  <aside class="website-graph__legend" aria-label="Graph groups">
    {#each WEBSITE_GRAPH_GROUPS as item}
      <div class="website-graph__legend-item">
        <span class="website-graph__legend-dot" style={`--legend-color: ${item.color}`}></span>
        <span>{item.label}</span>
      </div>
    {/each}
  </aside>
</section>

<style>
  .website-graph {
    position: relative;
    width: 100%;
    height: 100%;
    min-width: 0;
    min-height: 0;
    overflow: hidden;
    background: #fff;
    color: #000;
  }

  .website-graph[data-graph-theme='dark'] {
    background: #000;
    color: #fff;
  }

  :global(html[data-theme='dark']) .website-graph:not([data-graph-theme]) {
    background: #000;
    color: #fff;
  }

  .website-graph :global(.voronoi-website-graph) {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
  }

  .website-graph__control {
    position: absolute;
    top: 14px;
    z-index: 5;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    box-sizing: border-box;
    height: 30px;
    border: 1px solid #d5d5d5;
    border-radius: 3px;
    background: rgba(255, 255, 255, 0.94);
    color: #222;
    font-family: Arial, Helvetica, sans-serif;
    font-size: 11px;
    line-height: 1;
    text-decoration: none;
    cursor: pointer;
  }

  .website-graph[data-graph-theme='dark'] .website-graph__control {
    border-color: #333;
    background: rgba(0, 0, 0, 0.94);
    color: #eee;
  }

  :global(html[data-theme='dark']) .website-graph:not([data-graph-theme]) .website-graph__control {
    border-color: #333;
    background: rgba(0, 0, 0, 0.94);
    color: #eee;
  }

  .website-graph__control:hover,
  .website-graph__control:focus-visible {
    border-color: #999;
  }

  .website-graph__control:focus-visible {
    outline: 1px solid currentColor;
    outline-offset: 2px;
  }

  .website-graph__close {
    left: 14px;
    width: 30px;
    padding: 0;
  }

  .website-graph__close svg {
    width: 14px;
    height: 14px;
    fill: none;
    stroke: currentColor;
    stroke-width: 1.5;
    stroke-linecap: round;
  }

  .website-graph__controls-right {
    position: absolute;
    top: 14px;
    right: 14px;
    z-index: 5;
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .website-graph__controls-right .website-graph__control {
    position: static;
  }

  .website-graph__mode,
  .website-graph__center {
    padding: 0 10px;
  }

  .website-graph__legend {
    position: absolute;
    left: 14px;
    bottom: 14px;
    z-index: 4;
    display: grid;
    gap: 4px;
    padding: 7px 9px;
    border: 1px solid #e2e2e2;
    border-radius: 3px;
    background: rgba(255, 255, 255, 0.9);
    color: #222;
    font-family: Arial, Helvetica, sans-serif;
    font-size: 10px;
    line-height: 1.15;
  }

  .website-graph[data-graph-theme='dark'] .website-graph__legend {
    border-color: #282828;
    background: rgba(0, 0, 0, 0.88);
    color: #ddd;
  }

  :global(html[data-theme='dark']) .website-graph:not([data-graph-theme]) .website-graph__legend {
    border-color: #282828;
    background: rgba(0, 0, 0, 0.88);
    color: #ddd;
  }

  .website-graph__legend-item {
    display: flex;
    align-items: center;
    gap: 6px;
    white-space: nowrap;
  }

  .website-graph__legend-dot {
    width: 8px;
    height: 8px;
    flex: 0 0 8px;
    border-radius: 50%;
    background: var(--legend-color);
  }

  @media (max-width: 40rem) {
    .website-graph__control {
      top: 10px;
    }

    .website-graph__close {
      left: 10px;
    }

    .website-graph__controls-right {
      top: 10px;
      right: 10px;
    }

    .website-graph__legend {
      left: 10px;
      bottom: 10px;
    }
  }
</style>
