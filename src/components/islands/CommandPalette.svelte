<script lang="ts">
  import { onMount, tick } from 'svelte';

  import { trackEvent } from '@/lib/analytics';

  export let items: ReadonlyArray<{ label: string; href: string }> = [];

  let dialog: HTMLDialogElement;
  let input: HTMLInputElement;
  let query = '';
  let selectedIndex = 0;

  $: filtered = items.filter((item) =>
    item.label.toLowerCase().includes(query.trim().toLowerCase()),
  );

  function resetSelection() {
    selectedIndex = 0;
  }

  async function open() {
    if (!dialog || dialog.open) return;

    query = '';
    resetSelection();
    dialog.showModal();
    await tick();
    input?.focus();
    trackEvent('command_palette_opened');
  }

  function close() {
    if (dialog?.open) dialog.close();
  }

  function navigateToSelected() {
    const selected = filtered[selectedIndex];
    if (!selected) return;

    window.location.assign(selected.href);
  }

  async function moveSelection(direction: 1 | -1) {
    if (filtered.length === 0) return;

    selectedIndex =
      (selectedIndex + direction + filtered.length) % filtered.length;

    await tick();
    document
      .getElementById(`command-result-${selectedIndex}`)
      ?.scrollIntoView({ block: 'nearest' });
  }

  function handlePaletteKeydown(event: KeyboardEvent) {
    if (!dialog?.open) return;

    if (event.key === 'ArrowDown') {
      event.preventDefault();
      void moveSelection(1);
      return;
    }

    if (event.key === 'ArrowUp') {
      event.preventDefault();
      void moveSelection(-1);
      return;
    }

    if (event.key === 'Enter') {
      event.preventDefault();
      navigateToSelected();
    }
  }

  function handleGlobalKeydown(event: KeyboardEvent) {
    const target = event.target as HTMLElement;
    const isTyping =
      ['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName) ||
      target.isContentEditable;

    if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
      event.preventDefault();
      void open();
    } else if (!isTyping && event.key === '/') {
      event.preventDefault();
      void open();
    }
  }

  function handleOpenRequest() {
    void open();
  }

  onMount(() => {
    window.addEventListener('keydown', handleGlobalKeydown);
    window.addEventListener('command-palette:open', handleOpenRequest);

    return () => {
      window.removeEventListener('keydown', handleGlobalKeydown);
      window.removeEventListener('command-palette:open', handleOpenRequest);
    };
  });
</script>

<dialog
  bind:this={dialog}
  on:click={(event) => event.target === dialog && close()}
  on:keydown={handlePaletteKeydown}
>
  <section aria-label="Site search">
    <div class="search-row">
      <svg class="search-symbol" viewBox="0 0 24 24" aria-hidden="true">
        <circle cx="11" cy="11" r="6.5"></circle>
        <path d="m16 16 4 4"></path>
      </svg>

      <input
        bind:this={input}
        bind:value={query}
        on:input={resetSelection}
        type="search"
        placeholder="Search pages and commands…"
        aria-label="Search pages and commands"
        aria-controls="command-results"
        aria-activedescendant={filtered.length > 0
          ? `command-result-${selectedIndex}`
          : undefined}
      />

      <button type="button" on:click={close} aria-label="Close site search">
        Esc
      </button>
    </div>

    <p class="shortcut-hint">
      First match selected — press <kbd>Enter</kbd> to open. Use
      <kbd>↑</kbd><kbd>↓</kbd> to move. Open anytime with <kbd>⌘ K</kbd> or
      <kbd>Ctrl K</kbd>.
    </p>

    <ul id="command-results" role="listbox" aria-label="Search results">
      {#each filtered as item, index}
        <li>
          <a
            id={`command-result-${index}`}
            href={item.href}
            role="option"
            aria-selected={index === selectedIndex}
            class:selected={index === selectedIndex}
            tabindex="-1"
            on:mouseenter={() => (selectedIndex = index)}
          >
            {item.label}<span aria-hidden="true">↗</span>
          </a>
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
    background: rgb(0 0 0 / 44%);
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

  .search-symbol {
    width: 1.2rem;
    height: 1.2rem;
    fill: none;
    stroke: currentColor;
    stroke-linecap: round;
    stroke-linejoin: round;
    stroke-width: 1.7;
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

  .shortcut-hint {
    padding: 0.62rem 0.85rem;
    margin: 0;
    border-bottom: 1px solid var(--line);
    color: var(--muted);
    font-size: 0.78rem;
    line-height: 1.55;
  }

  kbd {
    display: inline-flex;
    min-width: 1.65rem;
    align-items: center;
    justify-content: center;
    padding: 0.12rem 0.32rem;
    margin-inline: 0.08rem;
    border: 1px solid var(--line);
    border-radius: 0.3rem;
    background: var(--accent-soft);
    color: var(--text);
    font: inherit;
    font-size: 0.72rem;
  }

  ul {
    max-height: 22rem;
    overflow-y: auto;
    padding: 0.55rem;
    margin: 0;
    list-style: none;
  }

  li {
    border-radius: var(--radius-sm);
  }

  a {
    display: flex;
    justify-content: space-between;
    padding: 0.7rem 0.8rem;
    border-radius: inherit;
    text-decoration: none;
  }

  a.selected,
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
