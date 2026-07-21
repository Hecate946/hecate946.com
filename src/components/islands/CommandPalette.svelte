<script lang="ts">
  import { onMount } from 'svelte';
  import { trackEvent } from '@/lib/analytics';

  export let items: ReadonlyArray<{ label: string; href: string }> = [];

  let dialog: HTMLDialogElement;
  let query = '';
  let input: HTMLInputElement;

  $: filtered = items.filter((item) =>
    item.label.toLowerCase().includes(query.toLowerCase()),
  );

  function open() {
    query = '';
    dialog.showModal();
    requestAnimationFrame(() => input?.focus());
    trackEvent('command_palette_opened');
  }

  function close() {
    dialog.close();
  }

  function handleKeydown(event: KeyboardEvent) {
    const target = event.target as HTMLElement;
    const isTyping =
      ['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName) ||
      target.isContentEditable;

    if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
      event.preventDefault();
      open();
    } else if (!isTyping && event.key === '/') {
      event.preventDefault();
      open();
    }
  }

  onMount(() => {
    window.addEventListener('keydown', handleKeydown);
    return () => window.removeEventListener('keydown', handleKeydown);
  });
</script>

<dialog
  bind:this={dialog}
  on:click={(event) => event.target === dialog && close()}
>
  <section aria-label="Command palette">
    <div class="search-row">
      <span aria-hidden="true">⌘</span>
      <input
        bind:this={input}
        bind:value={query}
        type="search"
        placeholder="Go anywhere…"
        aria-label="Filter destinations"
      />
      <button type="button" on:click={close} aria-label="Close command palette"
        >Esc</button
      >
    </div>

    <ul>
      {#each filtered as item}
        <li>
          <a href={item.href}>{item.label}<span aria-hidden="true">↗</span></a>
        </li>
      {:else}
        <li class="empty">No destination found.</li>
      {/each}
    </ul>
  </section>
</dialog>

<style>
  dialog {
    width: min(calc(100% - 2rem), 36rem);
    padding: 0;
    background: transparent;
    border: 0;
    color: var(--text);
  }

  dialog::backdrop {
    background: rgba(0, 0, 0, 0.44);
    backdrop-filter: blur(0.35rem);
  }

  section {
    overflow: hidden;
    background: var(--surface-strong);
    border: 1px solid var(--line);
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow);
  }

  .search-row {
    display: grid;
    grid-template-columns: auto 1fr auto;
    gap: 0.7rem;
    align-items: center;
    padding: 0.85rem;
    border-bottom: 1px solid var(--line);
  }

  input {
    width: 100%;
    min-width: 0;
    padding: 0.45rem 0;
    background: transparent;
    border: 0;
    color: var(--text);
    font-size: 1rem;
    outline: 0;
  }

  button {
    padding: 0.3rem 0.45rem;
    background: var(--accent-soft);
    border: 1px solid var(--line);
    border-radius: 0.35rem;
    color: var(--muted);
    cursor: pointer;
    font-size: 0.72rem;
  }

  ul {
    max-height: 22rem;
    overflow-y: auto;
    padding: 0.55rem;
    margin: 0;
    list-style: none;
  }

  a {
    display: flex;
    justify-content: space-between;
    padding: 0.7rem 0.8rem;
    border-radius: var(--radius-sm);
    text-decoration: none;
  }

  a:hover,
  a:focus-visible {
    background: var(--accent-soft);
  }

  .empty {
    padding: 1rem;
    color: var(--muted);
    text-align: center;
  }
</style>
