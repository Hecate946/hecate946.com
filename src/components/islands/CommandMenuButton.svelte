<script lang="ts">
  function openCommandPalette() {
    window.dispatchEvent(new CustomEvent('command-palette:open'));
  }
</script>

<div class="command-control">
  <button
    type="button"
    class="header-action command-action"
    aria-label="Open site search"
    aria-keyshortcuts="Meta+K Control+K"
    title="Open search — Ctrl/⌘ K"
    onclick={openCommandPalette}
  >
    <span class="header-action-icon search-icon" aria-hidden="true">
      <svg viewBox="0 0 24 24">
        <circle cx="11" cy="11" r="6.5"></circle>
        <path d="m16 16 4 4"></path>
      </svg>
    </span>
  </button>

  <span class="command-label">Search</span>
</div>
