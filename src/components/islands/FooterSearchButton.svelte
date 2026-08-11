<script lang="ts">
  function openCommandPalette() {
    window.dispatchEvent(new CustomEvent('command-palette:open'));
  }
</script>

<button
  class="footer-icon-link footer-search-toggle"
  type="button"
  aria-label="Open site search"
  aria-keyshortcuts="Meta+K Control+K"
  data-label="Search"
  onclick={openCommandPalette}
>
  <svg class="footer-search-icon footer-ui-icon" viewBox="0 0 24 24" aria-hidden="true" width="24" height="24" focusable="false">
    <circle cx="11" cy="11" r="6.5"></circle>
    <path d="m16 16 4 4"></path>
  </svg>
</button>
