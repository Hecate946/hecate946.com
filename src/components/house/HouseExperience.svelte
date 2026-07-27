<script lang="ts">
  import type { HouseDestination } from '@/config/house-scene';
  import HouseIllustration from './HouseIllustration.svelte';

  export let destinations: readonly HouseDestination[] = [];
  export let navigationEnabled = true;
</script>

<div class="house-experience">
  <div class="house-experience__viewport">
    <HouseIllustration {destinations} {navigationEnabled} />
  </div>
</div>
