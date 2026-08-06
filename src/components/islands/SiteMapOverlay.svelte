<script lang="ts">
  import { onMount, tick } from 'svelte';
  import ForceNetwork from '@/components/graphs/ForceNetwork.svelte';
  import type { NetworkLink, NetworkNode } from '@/components/graphs/types';
  import { trackEvent } from '@/lib/analytics';

  export let nodes: NetworkNode[] = [];
  export let links: NetworkLink[] = [];

  let dialog!: HTMLDialogElement;
  let graph: ForceNetwork | null = null;
  let graphVersion = 0;

  type SiteMapWindow = typeof window & {
    __hecateSiteMapPending?: boolean;
  };

  const graphLinks = links.map((link) => ({
    ...link,
    distance: link.kind === 'secondary' ? 78 : 108,
    strength: link.kind === 'secondary' ? 0.4 : 0.36,
    curve: 0,
  }));

  async function openSiteMap() {
    if (!dialog || dialog.open) return;
    graphVersion += 1;
    dialog.showModal();
    (window as SiteMapWindow).__hecateSiteMapPending = false;
    document.documentElement.dataset.siteMapOpen = 'true';
    window.dispatchEvent(
      new CustomEvent('site-map:state', { detail: { open: true } }),
    );
    await tick();
    dialog.focus({ preventScroll: true });
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
  data-site-sound-silent
  on:click={handleDialogClick}
  on:close={handleClose}
>
  <section class="site-map-shell">
    <header class="site-map-toolbar">
      <button
        class="site-map-toolbar-button site-map-close"
        type="button"
        aria-label="Close Website Graph"
        title="Close"
        on:click={closeSiteMap}
      >
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path d="m6.5 6.5 11 11m0-11-11 11"></path>
        </svg>
      </button>

      <h2 id="site-map-title">Website Graph</h2>

      <button
        class="site-map-toolbar-button site-map-reset"
        type="button"
        aria-label="Reset graph view"
        title="Reset view"
        on:click={() => graph?.resetView()}
      >
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path d="M8 3H3v5M16 3h5v5M21 16v5h-5M3 16v5h5"></path>
          <circle cx="12" cy="12" r="2.25"></circle>
        </svg>
      </button>
    </header>

    <p class="sr-only">
      Scroll or pinch to zoom. Drag empty space to pan. Drag nodes to rearrange
      them. Double-click empty space to reset the view.
    </p>

    <div class="site-map-stage">
      {#key graphVersion}
        <ForceNetwork
          bind:this={graph}
          nodes={nodes}
          links={graphLinks}
          centerNodeId="/"
          idPrefix="global-site-map"
          ariaLabel="Zoomable force graph of every destination on the site"
          height="100%"
          showHint={false}
          appearance="obsidian"
          collisionSounds={false}
          zoomable={true}
          showResetControl={false}
          settings={{
            layout: 'anchored',
            entranceRadius: 24,
            chargeStrength: -92,
            centerChargeMultiplier: 1.08,
            anchorStrength: 0.018,
            centerAnchorStrength: 0.018,
            collisionPadding: 5,
            linkDistance: 102,
            linkStrength: 0.36,
            linkCompressionRatio: 0.97,
            linkCompressionStrength: 0.94,
            linkCompressionIterations: 8,
            linkStretchRatio: 1.03,
            linkStretchStrength: 0.94,
            linkStretchIterations: 8,
            velocityDecay: 0.36,
            alphaDecay: 0.026,
            dragAlphaTarget: 0.18,
          }}
        />
      {/key}
    </div>
  </section>
</dialog>

<style>
  :global(html[data-site-map-open='true']),
  :global(html[data-site-map-open='true'] body) {
    overflow: hidden !important;
    overscroll-behavior: none;
  }

  .site-map-dialog {
    --site-map-background: #fff;
    --site-map-text: #111;
    --site-map-muted: #686868;
    --site-map-line: rgb(0 0 0 / 0.16);
    --site-map-font: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI",
      Ubuntu, Roboto, "Noto Sans", "Helvetica Neue", Arial, sans-serif;
    --site-map-toolbar-height: 3.35rem;

    position: fixed;
    inset: 0;
    box-sizing: border-box;
    width: 100vw;
    height: 100vh;
    height: 100svh;
    height: 100dvh;
    max-width: none;
    max-height: none;
    margin: 0;
    padding: 0;
    overflow: hidden;
    border: 0;
    background: transparent;
    color: var(--site-map-text);
    font-family: var(--site-map-font);
    overscroll-behavior: none;
  }

  :global(html[data-theme='dark']) .site-map-dialog {
    --site-map-background: #000;
    --site-map-text: #f5f5f5;
    --site-map-muted: #a0a0a0;
    --site-map-line: rgb(255 255 255 / 0.18);
  }

  .site-map-dialog::backdrop {
    background: rgb(0 0 0 / 0.58);
    backdrop-filter: blur(0.3rem);
  }

  .site-map-shell {
    display: grid;
    grid-template-rows: var(--site-map-toolbar-height) minmax(0, 1fr);
    width: 100%;
    height: 100%;
    min-width: 0;
    min-height: 0;
    overflow: hidden;
    border: 0;
    border-radius: 0;
    background: var(--site-map-background);
  }

  .site-map-toolbar {
    position: relative;
    z-index: 4;
    display: grid;
    grid-template-columns: 3rem minmax(0, 1fr) 3rem;
    align-items: center;
    width: 100%;
    height: var(--site-map-toolbar-height);
    min-width: 0;
    padding: 0 0.45rem;
    border-bottom: 1px solid
      color-mix(in srgb, var(--site-map-line) 72%, transparent);
    background: color-mix(in srgb, var(--site-map-background) 92%, transparent);
    backdrop-filter: blur(0.4rem);
  }

  .site-map-toolbar h2 {
    grid-column: 2;
    margin: 0;
    overflow: hidden;
    color: var(--site-map-text);
    font-family: var(--site-map-font);
    font-size: 0.82rem;
    font-weight: 540;
    letter-spacing: 0.006em;
    text-align: center;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .site-map-toolbar-button {
    display: grid;
    width: 2.55rem;
    height: 2.55rem;
    place-items: center;
    padding: 0;
    border: 0;
    border-radius: 0.34rem;
    background: transparent;
    color: var(--site-map-muted);
    cursor: pointer;
    transition:
      color 360ms cubic-bezier(0.22, 1, 0.36, 1),
      background-color 360ms cubic-bezier(0.22, 1, 0.36, 1),
      opacity 360ms cubic-bezier(0.22, 1, 0.36, 1);
  }

  .site-map-close {
    grid-column: 1;
    justify-self: start;
  }

  .site-map-reset {
    grid-column: 3;
    justify-self: end;
  }

  .site-map-toolbar-button:hover,
  .site-map-toolbar-button:focus-visible {
    background: color-mix(in srgb, var(--site-map-text) 9%, transparent);
    color: var(--site-map-text);
  }

  .site-map-toolbar-button svg {
    width: 1.38rem;
    height: 1.38rem;
    overflow: visible;
    fill: none;
    stroke: currentColor;
    stroke-linecap: round;
    stroke-linejoin: round;
    stroke-width: 1.7;
  }

  .site-map-stage {
    width: 100%;
    height: 100%;
    min-width: 0;
    min-height: 0;
    overflow: hidden;
    background: var(--site-map-background);
    overscroll-behavior: none;
  }

  .site-map-stage :global(.force-network) {
    width: 100%;
    height: 100%;
    min-height: 0;
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
      --site-map-toolbar-height: 3.15rem;
    }

    .site-map-toolbar {
      grid-template-columns: 2.85rem minmax(0, 1fr) 2.85rem;
      padding: 0 0.3rem;
    }

    .site-map-toolbar h2 {
      font-size: 0.78rem;
    }

    .site-map-toolbar-button {
      width: 2.45rem;
      height: 2.45rem;
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .site-map-dialog::backdrop {
      backdrop-filter: none;
    }

    .site-map-toolbar-button {
      transition: none;
    }
  }
</style>
