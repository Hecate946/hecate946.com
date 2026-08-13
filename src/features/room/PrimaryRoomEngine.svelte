<script lang="ts">
  import { onMount } from 'svelte';
  import AboutScroll from '@/components/about/AboutScroll.svelte';
  import HomeWall from '@/features/wall/HomeWall.svelte';
  import { pdfViewerHref, withBase } from '@/lib/paths';

  export let initialPath = '/';

  const portraitUrl = withBase('/images/about/cyrus-portrait-480.webp');
  const softwareResumeUrl = pdfViewerHref('/resumes/cyrus-asasi-software-engineering-resume.pdf');
  const projectsUrl = withBase('/projects/');
  const musicResumeUrl = pdfViewerHref('/resumes/cyrus-asasi-clarinet-performance-resume.pdf');
  const musicVideoUrl = 'https://www.youtube.com/watch?v=EkgH4zzXoNg';
  const pickleballArticleUrl =
    'https://www.dupr.com/post/california-super-regional-recap-ucla-rises-hawaii-makes-history-and-the-west-coast-delivers';
  const chessProfileUrl = 'https://www.chess.com/member/Cyrus2020SD/stats?time=0';

  type PrimaryRoom = 'home' | 'about' | 'other';

  const normalizePath = (pathname: string) => {
    if (pathname === '/') return '/';
    return pathname.replace(/\/+$/, '');
  };

  const roomForPath = (pathname: string): PrimaryRoom => {
    const path = normalizePath(pathname);
    if (path === '/') return 'home';
    if (path === '/about') return 'about';
    return 'other';
  };

  let currentRoom: PrimaryRoom = roomForPath(initialPath);
  let aboutMounted = currentRoom === 'about';
  let wallMounted = currentRoom === 'home';

  $: wallActive = currentRoom === 'home';
  $: if (wallActive) wallMounted = true;
  $: if (currentRoom === 'about') aboutMounted = true;

  function syncRoute() {
    currentRoom = roomForPath(window.location.pathname);
  }

  function warmAboutNow() {
    aboutMounted = true;
  }

  const warmAboutDuringIdle = () => {
    if (aboutMounted) return () => {};

    let fallbackTimer = 0;
    let idleHandle: number | null = null;
    const mountAbout = warmAboutNow;

    if ('requestIdleCallback' in window) {
      idleHandle = window.requestIdleCallback(mountAbout, { timeout: 1_500 });
    } else {
      fallbackTimer = window.setTimeout(mountAbout, 450);
    }

    return () => {
      if (idleHandle !== null && 'cancelIdleCallback' in window) {
        window.cancelIdleCallback(idleHandle);
      }
      if (fallbackTimer) window.clearTimeout(fallbackTimer);
    };
  };

  onMount(() => {
    syncRoute();
    const cancelAboutWarm = warmAboutDuringIdle();
    document.addEventListener('astro:after-swap', syncRoute);

    return () => {
      cancelAboutWarm();
      document.removeEventListener('astro:after-swap', syncRoute);
    };
  });
</script>

<div class="primary-room-engine" data-primary-room={currentRoom}>
  {#if wallMounted}
    <div class="primary-room-engine__wall" hidden={!wallActive}>
      <HomeWall active={wallActive} />
    </div>
  {/if}

  {#if aboutMounted}
    <div class="primary-room-engine__about" hidden={currentRoom !== 'about'}>
      <div class="about-room wall-room-host">
        <AboutScroll
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
