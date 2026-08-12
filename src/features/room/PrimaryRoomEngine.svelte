<script lang="ts">
  import { onMount } from 'svelte';
  import AboutTV from '@/components/about/AboutTV.svelte';
  import ProjectWall from '@/features/wall/ProjectWall.svelte';
  import { WALL_LOOP_WIDTH, WALL_START_X, wallDestinations } from '@/features/wall/wall-config';
  import {
    PROJECT_LOOP_WIDTH,
    PROJECT_START_X,
    projectDestinations,
  } from '@/features/wall/project-wall-config';
  import {
    RESUME_LOOP_WIDTH,
    RESUME_START_X,
    resumeDestinations,
  } from '@/features/wall/resume-wall-config';

  export let initialPath = '/';
  export let portraitUrl: string;
  export let softwareResumeUrl: string;
  export let projectsUrl: string;
  export let musicResumeUrl: string;
  export let musicVideoUrl: string;
  export let pickleballArticleUrl: string;
  export let chessProfileUrl: string;

  type PrimaryRoom = 'home' | 'about' | 'projects' | 'resumes' | 'contact' | 'other';

  const normalizePath = (pathname: string) => {
    if (pathname === '/') return '/';
    return pathname.replace(/\/+$/, '');
  };

  const roomForPath = (pathname: string): PrimaryRoom => {
    const path = normalizePath(pathname);
    if (path === '/') return 'home';
    if (path === '/about') return 'about';
    if (path === '/projects') return 'projects';
    if (path === '/resumes') return 'resumes';
    if (path === '/contact') return 'contact';
    return 'other';
  };

  const wallConfigs = {
    home: {
      destinations: wallDestinations,
      loopWidth: WALL_LOOP_WIDTH,
      startX: WALL_START_X,
      heading: 'Cyrus Asasi',
      stageLabel:
        'Infinite navigation wall. Drag or scroll horizontally, then select a lit window to enter a page.',
      trackLabel: 'Website destinations',
    },
    projects: {
      destinations: projectDestinations,
      loopWidth: PROJECT_LOOP_WIDTH,
      startX: PROJECT_START_X,
      heading: 'Projects',
      stageLabel:
        'Infinite project conveyor. Drag, swipe, or scroll horizontally, then select a framed project.',
      trackLabel: 'Selected projects',
    },
    resumes: {
      destinations: resumeDestinations,
      loopWidth: RESUME_LOOP_WIDTH,
      startX: RESUME_START_X,
      heading: 'Resumes',
      stageLabel:
        'Infinite resume conveyor. Drag, swipe, or scroll horizontally, then select a framed resume.',
      trackLabel: 'Resumes',
    },
  } as const;

  let currentRoom: PrimaryRoom = roomForPath(initialPath);
  let aboutMounted = currentRoom === 'about';
  let wallMounted =
    currentRoom === 'home' || currentRoom === 'projects' || currentRoom === 'resumes';
  let wallRoom: keyof typeof wallConfigs =
    currentRoom === 'projects' || currentRoom === 'resumes' ? currentRoom : 'home';

  $: if (currentRoom === 'home' || currentRoom === 'projects' || currentRoom === 'resumes') {
    wallRoom = currentRoom;
  }
  $: wallConfig = wallConfigs[wallRoom];
  $: wallActive = currentRoom === 'home' || currentRoom === 'projects' || currentRoom === 'resumes';
  $: if (wallActive) wallMounted = true;
  $: if (currentRoom === 'about') aboutMounted = true;

  function syncRoute() {
    currentRoom = roomForPath(window.location.pathname);
  }

  onMount(() => {
    syncRoute();
    document.addEventListener('astro:after-swap', syncRoute);
    document.addEventListener('astro:page-load', syncRoute);
    window.addEventListener('popstate', syncRoute);

    return () => {
      document.removeEventListener('astro:after-swap', syncRoute);
      document.removeEventListener('astro:page-load', syncRoute);
      window.removeEventListener('popstate', syncRoute);
    };
  });
</script>

<div class="primary-room-engine" data-primary-room={currentRoom}>
  {#if wallMounted}
    <div class="primary-room-engine__wall" hidden={!wallActive}>
      <ProjectWall
        destinations={wallConfig.destinations}
        loopWidth={wallConfig.loopWidth}
        startX={wallConfig.startX}
        heading={wallConfig.heading}
        stageLabel={wallConfig.stageLabel}
        trackLabel={wallConfig.trackLabel}
        roomKey={wallRoom}
        active={wallActive}
      />
    </div>
  {/if}

  {#if aboutMounted}
    <div class="primary-room-engine__about" hidden={currentRoom !== 'about'}>
      <div class="about-room wall-room-host">
        <AboutTV
          {portraitUrl}
          {softwareResumeUrl}
          {projectsUrl}
          {musicResumeUrl}
          {musicVideoUrl}
          {pickleballArticleUrl}
          {chessProfileUrl}
        />
      </div>
    </div>
  {/if}
</div>
