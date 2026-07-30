<script lang="ts">
  import type { Object3D } from 'three';
  import type { ImmersiveSpace } from './catalog';
  import RedRoomExtras from './extras/rooms/RedRoomExtras.svelte';
  import GreenRoomExtras from './extras/rooms/GreenRoomExtras.svelte';
  import OrangeRoomExtras from './extras/rooms/OrangeRoomExtras.svelte';
  import BlueRoomExtras from './extras/rooms/BlueRoomExtras.svelte';
  import PurpleRoomExtras from './extras/rooms/PurpleRoomExtras.svelte';
  import BallroomExtras from './extras/halls/BallroomExtras.svelte';
  import MuseumExtras from './extras/halls/MuseumExtras.svelte';

  export let space: ImmersiveSpace;
  export let interactiveScene: Object3D | null = null;
</script>

{#if space.kind === 'room' && space.slug === 'red'}
  <RedRoomExtras {space} {interactiveScene} />
{:else if space.kind === 'room' && space.slug === 'green'}
  <GreenRoomExtras {space} {interactiveScene} />
{:else if space.kind === 'room' && space.slug === 'orange'}
  <OrangeRoomExtras {space} {interactiveScene} />
{:else if space.kind === 'room' && space.slug === 'blue'}
  <BlueRoomExtras {space} {interactiveScene} />
{:else if space.kind === 'room' && space.slug === 'purple'}
  <PurpleRoomExtras {space} {interactiveScene} />
{:else if space.kind === 'hall' && space.slug === 'ballroom'}
  <BallroomExtras {space} {interactiveScene} />
{:else if space.kind === 'hall' && space.slug === 'museum'}
  <MuseumExtras {space} {interactiveScene} />
{/if}
