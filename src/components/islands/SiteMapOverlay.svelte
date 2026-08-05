<script lang="ts">
  import { onMount, tick } from 'svelte';
  import ForceNetwork from '@/components/graphs/ForceNetwork.svelte';
  import type { NetworkLink, NetworkNode } from '@/components/graphs/types';
  import { trackEvent } from '@/lib/analytics';

  export let nodes: NetworkNode[] = [];
  export let links: NetworkLink[] = [];

  let dialog!: HTMLDialogElement;
  let searchInput!: HTMLInputElement;
  let query = '';
  let searchTerm = '';
  let directMatches = new Set<string>();
  let visibleIds = new Set<string>();
  let visibleNodes: NetworkNode[] = [];
  let visibleLinks: NetworkLink[] = [];
  let resultCount = 0;

  type SiteMapWindow = typeof window & {
    __hecateSiteMapPending?: boolean;
  };

  const normalize = (value: string) => value.trim().toLowerCase();

  $: searchTerm = normalize(query);
  $: directMatches = new Set(
    nodes
      .filter((node) => {
        if (!searchTerm) return true;
        return [node.label, node.description, node.href]
          .filter(Boolean)
          .some((value) => String(value).toLowerCase().includes(searchTerm));
      })
      .map((node) => node.id),
  );

  // Keep the home node and each direct parent visible while searching so a
  // result still reads as part of the site rather than as an isolated dot.
  $: visibleIds = (() => {
    if (!searchTerm) return new Set(nodes.map((node) => node.id));
    const ids = new Set(directMatches);
    ids.add('/');

    for (const link of links) {
      if (directMatches.has(link.target)) ids.add(link.source);
      if (directMatches.has(link.source)) ids.add(link.target);
    }

    return ids;
  })();

  $: visibleNodes = nodes.filter((node) => visibleIds.has(node.id));
  $: visibleLinks = links.filter(
    (link) => visibleIds.has(link.source) && visibleIds.has(link.target),
  );
  $: resultCount = searchTerm ? directMatches.size : nodes.length;

  async function openSiteMap() {
    if (!dialog || dialog.open) return;
    query = '';
    dialog.showModal();
    (window as SiteMapWindow).__hecateSiteMapPending = false;
    document.documentElement.dataset.siteMapOpen = 'true';
    window.dispatchEvent(
      new CustomEvent('site-map:state', { detail: { open: true } }),
    );
    await tick();
    searchInput?.focus({ preventScroll: true });
    trackEvent('site_map_opened', { destination_count: nodes.length });
  }

  function closeSiteMap() {
    if (!dialog?.open) return;
    dialog.close();
  }

  function handleClose() {
    delete document.documentElement.dataset.siteMapOpen;
    window.dispatchEvent(
      new CustomEvent('site-map:state', { detail: { open: false } }),
    );
  }

  function handleDialogClick(event: MouseEvent) {
    if (event.target === dialog) closeSiteMap();
  }

  function handleOpenRequest() {
    void openSiteMap();
  }

  function handleKeydown(event: KeyboardEvent) {
    if (!dialog?.open) return;

    if (event.key === 'Escape') {
      event.preventDefault();
      closeSiteMap();
    }
  }

  onMount(() => {
    window.addEventListener('site-map:open', handleOpenRequest);
    window.addEventListener('keydown', handleKeydown);

    if ((window as SiteMapWindow).__hecateSiteMapPending) {
      void openSiteMap();
    }

    return () => {
      window.removeEventListener('site-map:open', handleOpenRequest);
      window.removeEventListener('keydown', handleKeydown);
      delete document.documentElement.dataset.siteMapOpen;
    };
  });
</script>

<dialog
  id="site-map-dialog"
  class="site-map-dialog"
  bind:this={dialog}
  aria-labelledby="site-map-title"
  on:click={handleDialogClick}
  on:close={handleClose}
>
  <section class="site-map-shell">
    <header class="site-map-header">
      <div class="site-map-title-group">
        <p class="site-map-kicker">Dynamic route graph</p>
        <h2 id="site-map-title">Site map</h2>
      </div>

      <label class="site-map-search">
        <span class="sr-only">Filter destinations</span>
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <circle cx="10.5" cy="10.5" r="5.75"></circle>
          <path d="m15 15 4.5 4.5"></path>
        </svg>
        <input
          bind:this={searchInput}
          bind:value={query}
          type="search"
          placeholder="Filter pages…"
          aria-label="Filter site-map destinations"
        />
      </label>

      <button
        class="site-map-close"
        type="button"
        aria-label="Close site map"
        on:click={closeSiteMap}
      >
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path d="m6.5 6.5 11 11m0-11-11 11"></path>
        </svg>
      </button>
    </header>

    <div class="site-map-meta" aria-live="polite">
      <span>{resultCount} {resultCount === 1 ? 'destination' : 'destinations'}</span>
      <span aria-hidden="true">·</span>
      <span>Generated from the current route catalog</span>
    </div>

    <div class="site-map-stage">
      {#if !searchTerm || resultCount > 0}
        <ForceNetwork
          nodes={visibleNodes}
          links={visibleLinks}
          centerNodeId="/"
          idPrefix="global-site-map"
          ariaLabel="Interactive force graph of every destination on the site"
          height="100%"
          showHint={false}
          settings={{
            layout: 'anchored',
            entranceRadius: 78,
            chargeStrength: -118,
            centerChargeMultiplier: 1.8,
            anchorStrength: 0.055,
            centerAnchorStrength: 0.32,
            collisionPadding: 10,
            linkDistance: 128,
            linkStrength: 0.15,
            velocityDecay: 0.31,
            alphaDecay: 0.035,
            dragAlphaTarget: 0.28,
          }}
        />
      {:else}
        <p class="site-map-empty">No destination matches “{query}”.</p>
      {/if}
    </div>

    <footer class="site-map-footer">
      <p>Drag nodes to reshape the map. Select a node to visit its page.</p>
      <div class="site-map-legend" aria-label="Site-map categories">
        <span><i class="legend-dot legend-dot--profile"></i>Profile</span>
        <span><i class="legend-dot legend-dot--projects"></i>Projects</span>
        <span><i class="legend-dot legend-dot--spaces"></i>Spaces</span>
        <span><i class="legend-dot legend-dot--experiments"></i>Experiments</span>
      </div>
    </footer>
  </section>
</dialog>

<style>
  .site-map-dialog {
    width: min(calc(100% - 1.5rem), 78rem);
    height: min(calc(100svh - 1.5rem), 52rem);
    max-width: none;
    max-height: none;
    padding: 0;
    border: 0;
    background: transparent;
    color: var(--text);
  }

  .site-map-dialog::backdrop {
    background: color-mix(in srgb, #000 52%, transparent);
    backdrop-filter: blur(0.45rem);
  }

  .site-map-shell {
    display: grid;
    grid-template-rows: auto auto minmax(0, 1fr) auto;
    width: 100%;
    height: 100%;
    overflow: hidden;
    border: 1px solid color-mix(in srgb, var(--line) 82%, var(--text));
    border-radius: 0.72rem;
    background: var(--bg);
    box-shadow: 0 1.4rem 4rem rgb(0 0 0 / 0.28);
  }

  .site-map-header {
    display: grid;
    grid-template-columns: minmax(10rem, 1fr) minmax(12rem, 24rem) auto;
    gap: clamp(0.65rem, 1.5vw, 1rem);
    min-width: 0;
    align-items: center;
    padding: clamp(0.75rem, 1.5vw, 1rem);
    border-bottom: 1px solid var(--line);
  }

  .site-map-title-group {
    min-width: 0;
  }

  .site-map-kicker,
  .site-map-title-group h2,
  .site-map-meta,
  .site-map-footer p {
    margin: 0;
  }

  .site-map-kicker {
    color: var(--muted);
    font-family: var(--font-mono);
    font-size: 0.66rem;
    letter-spacing: 0.1em;
    line-height: 1;
    text-transform: uppercase;
  }

  .site-map-title-group h2 {
    margin-top: 0.2rem;
    font-family: var(--font-display);
    font-size: clamp(1.55rem, 3vw, 2.15rem);
    font-weight: 400;
    letter-spacing: -0.035em;
    line-height: 1;
  }

  .site-map-search {
    display: grid;
    grid-template-columns: auto minmax(0, 1fr);
    min-width: 0;
    align-items: center;
    gap: 0.55rem;
    padding: 0.55rem 0.7rem;
    border: 1px solid var(--line);
    border-radius: 0.52rem;
    background: color-mix(in srgb, var(--surface-strong) 78%, transparent);
  }

  .site-map-search:focus-within {
    border-color: var(--accent);
    outline: 0.13rem solid color-mix(in srgb, var(--accent) 32%, transparent);
  }

  .site-map-search svg {
    width: 1rem;
    height: 1rem;
    fill: none;
    stroke: var(--muted);
    stroke-linecap: round;
    stroke-linejoin: round;
    stroke-width: 1.7;
  }

  .site-map-search input {
    width: 100%;
    min-width: 0;
    padding: 0;
    border: 0;
    outline: 0;
    background: transparent;
    color: var(--text);
    font: inherit;
  }

  .site-map-search input::placeholder {
    color: var(--muted);
  }

  .site-map-close {
    display: grid;
    width: 2.35rem;
    height: 2.35rem;
    place-items: center;
    padding: 0;
    border: 1px solid var(--line);
    border-radius: 0.52rem;
    background: transparent;
    color: var(--text);
    cursor: pointer;
  }

  .site-map-close:hover,
  .site-map-close:focus-visible {
    border-color: var(--accent);
    color: var(--accent-strong);
  }

  .site-map-close svg {
    width: 1.15rem;
    height: 1.15rem;
    fill: none;
    stroke: currentColor;
    stroke-linecap: round;
    stroke-width: 1.7;
  }

  .site-map-meta {
    display: flex;
    gap: 0.45rem;
    align-items: center;
    padding: 0.48rem 1rem;
    border-bottom: 1px solid var(--line);
    color: var(--muted);
    font-family: var(--font-mono);
    font-size: 0.65rem;
  }

  .site-map-stage {
    min-width: 0;
    min-height: 0;
    padding: clamp(0.5rem, 1.4vw, 0.85rem);
  }

  .site-map-stage :global(.force-network) {
    min-height: 0;
    border-radius: 0.5rem;
  }

  .site-map-stage :global(.force-network__label) {
    font-size: 0.7rem;
    font-weight: 550;
  }

  .site-map-stage :global(.force-network__description) {
    font-size: 0.58rem;
  }

  .site-map-empty {
    display: grid;
    height: 100%;
    place-items: center;
    margin: 0;
    color: var(--muted);
    text-align: center;
  }

  .site-map-footer {
    display: flex;
    min-width: 0;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    padding: 0.62rem 1rem;
    border-top: 1px solid var(--line);
    color: var(--muted);
    font-size: 0.68rem;
  }

  .site-map-legend {
    display: flex;
    flex-wrap: wrap;
    justify-content: flex-end;
    gap: 0.45rem 0.8rem;
  }

  .site-map-legend span {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    white-space: nowrap;
  }

  .legend-dot {
    width: 0.48rem;
    height: 0.48rem;
    border-radius: 999px;
    background: var(--accent);
  }

  .legend-dot--profile {
    background: var(--season-1);
  }

  .legend-dot--projects {
    background: var(--season-2);
  }

  .legend-dot--spaces {
    background: var(--season-3);
  }

  .legend-dot--experiments {
    background: var(--accent-strong);
  }

  .sr-only {
    position: absolute;
    width: 1px;
    height: 1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    white-space: nowrap;
    clip-path: inset(50%);
  }

  @media (max-width: 44rem) {
    .site-map-dialog {
      width: calc(100% - 0.75rem);
      height: calc(100svh - 0.75rem);
    }

    .site-map-header {
      grid-template-columns: minmax(0, 1fr) auto;
    }

    .site-map-search {
      grid-column: 1 / -1;
      grid-row: 2;
    }

    .site-map-close {
      grid-column: 2;
      grid-row: 1;
    }

    .site-map-meta span:last-child,
    .site-map-meta span[aria-hidden='true'] {
      display: none;
    }

    .site-map-stage {
      padding: 0.38rem;
    }

    .site-map-stage :global(.force-network__label) {
      font-size: 0.62rem;
    }

    .site-map-footer {
      display: grid;
      gap: 0.5rem;
    }

    .site-map-legend {
      justify-content: flex-start;
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .site-map-dialog::backdrop {
      backdrop-filter: none;
    }
  }
</style>
