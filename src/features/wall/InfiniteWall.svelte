<script lang="ts">
  import ProjectWall from './ProjectWall.svelte';
  import { WALL_LOOP_WIDTH, WALL_START_X, wallDestinations } from './wall-config';
</script>

<!--
  Home uses the exact same conveyor engine as Projects and Resumes. Keeping one
  implementation avoids shipping/maintaining two near-identical animation
  loops and guarantees performance fixes apply to every moving wall.
-->
<ProjectWall
  destinations={wallDestinations}
  loopWidth={WALL_LOOP_WIDTH}
  startX={WALL_START_X}
  heading="Cyrus Asasi"
  stageLabel="Infinite navigation wall. Drag or scroll horizontally, then select a lit window to enter a page."
  trackLabel="Website destinations"
/>
