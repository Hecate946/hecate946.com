<script lang="ts">
  import '@/styles/wall-room.css';

  export let showFloor = true;
</script>

<div class="wall-stage__wall-surface" aria-hidden="true">
  <div class="wall-stage__brick-pattern"></div>
</div>

<div class="wall-stage__mortar-light" aria-hidden="true"></div>

{#if showFloor}
  <div class="wall-floor" aria-hidden="true">
    <div class="wall-floor__surface"></div>
  </div>

  <div class="wall-floor__baseboard" aria-hidden="true"></div>
{/if}

<div class="wall-stage__vignette" aria-hidden="true"></div>
