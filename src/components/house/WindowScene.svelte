<script lang="ts">
  import type { HouseWindowSceneId } from '@/config/house-scene';
  import AboutWindowScene from './scenes/AboutWindowScene.svelte';
  import ChessRookWindowScene from './scenes/ChessRookWindowScene.svelte';
  import CollisionWindowScene from './scenes/CollisionWindowScene.svelte';
  import ConcertHallWindowScene from './scenes/ConcertHallWindowScene.svelte';
  import ContactWindowScene from './scenes/ContactWindowScene.svelte';
  import PickleballWindowScene from './scenes/PickleballWindowScene.svelte';
  import PortfolioWindowScene from './scenes/PortfolioWindowScene.svelte';
  import ProjectsWindowScene from './scenes/ProjectsWindowScene.svelte';
  import ResumeWindowScene from './scenes/ResumeWindowScene.svelte';

  export let scene: HouseWindowSceneId;
</script>

{#if scene === 'collision'}
  <CollisionWindowScene />
{:else if scene === 'chess-rook'}
  <ChessRookWindowScene />
{:else if scene === 'concert-hall'}
  <ConcertHallWindowScene />
{:else if scene === 'pickleball'}
  <PickleballWindowScene />
{:else if scene === 'portfolio'}
  <PortfolioWindowScene />
{:else if scene === 'about'}
  <AboutWindowScene />
{:else if scene === 'resume'}
  <ResumeWindowScene />
{:else if scene === 'projects'}
  <ProjectsWindowScene />
{:else}
  <ContactWindowScene />
{/if}
