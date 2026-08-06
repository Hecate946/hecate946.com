<script lang="ts">
  import { onMount, tick } from 'svelte';
  import ForceNetwork from '@/components/graphs/ForceNetwork.svelte';
  import type { NetworkLink, NetworkNode } from '@/components/graphs/types';
  import { trackEvent } from '@/lib/analytics';

  export let nodes: NetworkNode[] = [];
  export let links: NetworkLink[] = [];

  let dialog!: HTMLDialogElement;
  let graphVersion = 0;

  type SiteMapWindow = typeof window & {
    __hecateSiteMapPending?: boolean;
  };

  const graphLinks = links.map((link) => ({
    ...link,
    distance: link.kind === 'secondary' ? 78 : 108,
    strength: link.kind === 'secondary' ? 0.19 : 0.16,
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
      <h2 id="site-map-title">Site map</h2>

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

    <p class="sr-only">
      Scroll or pinch to zoom. Drag empty space to pan. Drag nodes to rearrange
      them. Double-click empty space to reset the view.
    </p>

    <div class="site-map-stage">
      {#key graphVersion}
        <ForceNetwork
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
          settings={{
            layout: 'anchored',
            entranceRadius: 24,
            chargeStrength: -92,
            centerChargeMultiplier: 1.08,
            anchorStrength: 0.018,
            centerAnchorStrength: 0.018,
            collisionPadding: 5,
            linkDistance: 102,
            linkStrength: 0.17,
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
  .site-map-dialog {
    --site-map-background: #fff;
    --site-map-text: #111;
    --site-map-muted: #686868;
    --site-map-line: rgb(0 0 0 / 0.16);
    --site-map-font: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI",
      Ubuntu, Roboto, "Noto Sans", "Helvetica Neue", Arial, sans-serif;

    width: min(calc(100% - 1.5rem), 80rem);
    height: min(calc(100svh - 1.5rem), 54rem);
    max-width: none;
    max-height: none;
    padding: 0;
    border: 0;
    background: transparent;
    color: var(--site-map-text);
    font-family: var(--site-map-font);
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
    grid-template-rows: auto minmax(0, 1fr);
    width: 100%;
    height: 100%;
    overflow: hidden;
    border: 1px solid var(--site-map-line);
    border-radius: 0.55rem;
    background: var(--site-map-background);
  }

  .site-map-toolbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    min-height: 2.95rem;
    padding: 0.5rem 0.58rem 0.5rem 0.72rem;
    border-bottom: 1px solid var(--site-map-line);
    background: var(--site-map-background);
  }

  .site-map-toolbar h2 {
    margin: 0;
    color: var(--site-map-text);
    font-family: var(--site-map-font);
    font-size: 0.76rem;
    font-weight: 560;
    letter-spacing: 0.01em;
  }

  .site-map-close {
    display: grid;
    width: 1.9rem;
    height: 1.9rem;
    place-items: center;
    padding: 0;
    border: 0;
    border-radius: 0.3rem;
    background: transparent;
    color: var(--site-map-muted);
    cursor: pointer;
  }

  .site-map-close:hover,
  .site-map-close:focus-visible {
    background: color-mix(in srgb, var(--site-map-text) 9%, transparent);
    color: var(--site-map-text);
  }

  .site-map-close svg {
    width: 1rem;
    height: 1rem;
    fill: none;
    stroke: currentColor;
    stroke-linecap: round;
    stroke-width: 1.6;
  }

  .site-map-stage {
    min-width: 0;
    min-height: 0;
    overflow: hidden;
    background: var(--site-map-background);
  }

  .site-map-stage :global(.force-network) {
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
      width: calc(100% - 0.75rem);
      height: calc(100svh - 0.75rem);
    }

    .site-map-toolbar {
      min-height: 2.7rem;
      padding: 0.4rem 0.42rem 0.4rem 0.58rem;
    }

    .site-map-toolbar h2 {
      font-size: 0.68rem;
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .site-map-dialog::backdrop {
      backdrop-filter: none;
    }
  }
</style>
