<script lang="ts">
  import { onMount } from 'svelte';
  import ForceNetwork from '@/components/graphs/ForceNetwork.svelte';
  import VisitorGlobeClearV2 from '@/components/islands/VisitorGlobeClearV2.svelte';
  import VisitorMap from '@/components/islands/VisitorMap.svelte';
  import YourPathGraph from '@/components/islands/YourPathTree.svelte';
  import {
    navigationNetworkLinks,
    navigationNetworkNodes,
  } from '@/data/navigation-network';
  import { resolveStatsApiBase } from '@/lib/stats-api';

  export let apiBase = '';

  interface VisitorLocation {
    city: string | null;
    region: string | null;
    country: string | null;
    countryCode: string | null;
    latitude: number;
    longitude: number;
    pageViews: number;
    estimatedVisitors: number;
    pointIndex?: number;
    pointCount?: number;
  }

  interface DailyStat {
    day: string;
    pageViews: number;
    estimatedVisitors: number;
    events: number;
  }

  interface RankedStat {
    label: string;
    value: number;
  }

  interface HourStat {
    hour: number;
    value: number;
  }

  interface LiveStats {
    summary: {
      pageViews: number;
      estimatedVisitors: number;
      sessions: number;
      trackedRequests: number;
      countries: number;
      visibleLocations: number;
      activeVisitors: number;
      firstEventAt: string | null;
      updatedAt: string | null;
    };
    daily: DailyStat[];
    pages: RankedStat[];
    interactions: RankedStat[];
    locations: VisitorLocation[];
    hours?: HourStat[];
  }

  type EarthView = '2d' | '3d';

  const numberFormatter = new Intl.NumberFormat('en-US');
  let liveStats: LiveStats | null = null;
  let liveError = '';
  let earthView: EarthView = '2d';
  let selectedHour = 12;
  let hoveredHour: number | null = null;
  let hourInitialized = false;
  let refreshing = false;
  let utcOffsetMinutes = 0;

  $: hourly = normalizedHours(liveStats?.hours);
  $: peakHour = hourly.reduce(
    (best, item) => (item.value > best.value ? item : best),
    { hour: 0, value: 0 },
  );
  $: histogramStep = niceHistogramStep(peakHour.value);
  $: histogramMaximum = histogramStep * 4;
  $: histogramTicks = [4, 3, 2, 1, 0].map((multiple) => multiple * histogramStep);
  $: displayedHour = hoveredHour ?? selectedHour;
  $: if (!hourInitialized && peakHour.value > 0) {
    selectedHour = peakHour.hour;
    hourInitialized = true;
  }
  $: maxPageViews = Math.max(
    1,
    ...navigationNetworkNodes.map((node) => valueForPath(pathFromHref(node.href ?? '/'))),
  );
  $: trafficGraphNodes = navigationNetworkNodes.map((node) => {
    const pageViews = valueForPath(pathFromHref(node.href ?? '/'));
    const relative = Math.sqrt(pageViews / maxPageViews);
    return {
      ...node,
      radius: node.id === 'home' ? 58 : 31 + relative * 10,
      description: `${formatNumber(pageViews)} ${pageViews === 1 ? 'visit' : 'visits'}`,
      descriptionAlwaysVisible: true,
    };
  });

  function formatNumber(value: number | null | undefined) {
    if (value === null || value === undefined) return '—';
    return numberFormatter.format(value);
  }

  function localHourDate(hour: number) {
    const date = new Date();
    date.setHours(((hour % 24) + 24) % 24, 0, 0, 0);
    return date;
  }

  function formatLocalHour(hour: number, includeZone = false) {
    return new Intl.DateTimeFormat(undefined, {
      hour: 'numeric',
      minute: '2-digit',
      ...(includeZone ? { timeZoneName: 'short' as const } : {}),
    }).format(localHourDate(hour));
  }

  function formatHourTick(hour: number) {
    return new Intl.DateTimeFormat(undefined, {
      hour: 'numeric',
      hour12: true,
    })
      .format(localHourDate(hour))
      .replace(/\s/g, '')
      .toLowerCase();
  }

  function normalizedHours(hours: HourStat[] | undefined) {
    const values = Array.from({ length: 24 }, (_, hour) => ({ hour, value: 0 }));
    for (const item of hours ?? []) {
      const hour = Math.trunc(Number(item.hour));
      if (hour >= 0 && hour < 24) values[hour].value = Math.max(0, Number(item.value) || 0);
    }
    return values;
  }

  function niceHistogramStep(maximum: number) {
    if (!Number.isFinite(maximum) || maximum <= 4) return 1;
    const raw = maximum / 4;
    const exponent = 10 ** Math.floor(Math.log10(raw));
    const fraction = raw / exponent;
    const niceFraction = fraction <= 1 ? 1 : fraction <= 2 ? 2 : fraction <= 5 ? 5 : 10;
    return niceFraction * exponent;
  }

  function histogramHeight(value: number) {
    if (value <= 0 || histogramMaximum <= 0) return 0;
    return Math.max(2.5, Math.min(100, (value / histogramMaximum) * 100));
  }

  function pathFromHref(href: string) {
    try {
      return new URL(href, 'https://hecate.local').pathname;
    } catch {
      return href.startsWith('/') ? href : '/';
    }
  }

  function valueForPath(path: string) {
    const normalized = path === '/' ? '/' : `${path.replace(/\/+$/, '')}/`;
    const exact = liveStats?.pages.find((item) => {
      const itemPath = item.label === '/' ? '/' : `${item.label.replace(/\/+$/, '')}/`;
      return itemPath === normalized;
    })?.value;
    return exact ?? 0;
  }

  function prewarmGlobePreview() {
    const base = String(import.meta.env.BASE_URL ?? '/').replace(/\/?$/, '/');
    const image = new Image();
    image.decoding = 'async';
    image.src = `${base}generated/globe-world-mask-4096.png`;
  }

  async function readJson<T>(url: string): Promise<T> {
    const response = await fetch(url, {
      headers: { Accept: 'application/json' },
      cache: 'no-store',
      credentials: 'omit',
      referrerPolicy: 'no-referrer',
    });
    if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
    return response.json() as Promise<T>;
  }

  function liveStatsUrl() {
    const query = new URLSearchParams({
      days: '30',
      utcOffsetMinutes: String(utcOffsetMinutes),
    });

    // Development reads production analytics through the local proxy without
    // writing local test pageviews into the public dataset.
    if (import.meta.env.DEV) return `/__local-stats/api/public-stats?${query}`;

    const base = resolveStatsApiBase(apiBase);
    return base ? `${base}/api/stats?${query}` : '';
  }

  async function loadLiveStats() {
    utcOffsetMinutes = -new Date().getTimezoneOffset();
    const url = liveStatsUrl();
    if (!url) return;
    try {
      liveStats = await readJson<LiveStats>(url);
      liveError = '';
    } catch (error) {
      liveError = error instanceof Error ? error.message : 'Stats unavailable';
    }
  }

  async function refresh() {
    if (refreshing) return;
    refreshing = true;
    await loadLiveStats();
    refreshing = false;
  }

  onMount(() => {
    utcOffsetMinutes = -new Date().getTimezoneOffset();
    void refresh();

    const prewarmTimer = window.setTimeout(prewarmGlobePreview, 300);
    const interval = window.setInterval(() => {
      if (document.visibilityState === 'visible') void loadLiveStats();
    }, 20_000);

    return () => {
      window.clearTimeout(prewarmTimer);
      window.clearInterval(interval);
    };
  });
</script>

<div class="stats-observatory" aria-busy={refreshing}>
  <section class="observatory-section observatory-earth" aria-labelledby="geography-title">
    <header class="observatory-section-header">
      <h2 id="geography-title">Geography</h2>
    </header>

    <div class="observatory-earth-stage" data-view={earthView}>
      <div class="earth-switcher" role="group" aria-label="Visitor geography view">
        <button
          type="button"
          class:active={earthView === '2d'}
          aria-pressed={earthView === '2d'}
          on:click={() => (earthView = '2d')}
        >2D</button>
        <button
          type="button"
          class:active={earthView === '3d'}
          aria-pressed={earthView === '3d'}
          on:click={() => (earthView = '3d')}
        >3D</button>
      </div>

      {#if liveStats?.locations?.length}
        {#key earthView}
          {#if earthView === '2d'}
            <VisitorMap
              locations={liveStats.locations}
              totalVisitors={liveStats.summary.estimatedVisitors}
            />
          {:else}
            <VisitorGlobeClearV2
              embedded={true}
              locations={liveStats.locations}
              totalVisitors={liveStats.summary.estimatedVisitors}
            />
          {/if}
        {/key}
      {:else}
        <div class="observatory-loading">
          <span class="observatory-orbit" aria-hidden="true"></span>
          <span>{liveError ? 'Unavailable' : 'Locating…'}</span>
        </div>
      {/if}
    </div>

    <div class="earth-caption" aria-label="Visitor summary">
      <strong>{formatNumber(liveStats?.summary.sessions)}</strong>
      <span>visits</span>
      <i aria-hidden="true">·</i>
      <strong>{formatNumber(liveStats?.summary.countries)}</strong>
      <span>countries</span>
    </div>
  </section>

  <section class="observatory-section observatory-traffic" aria-labelledby="page-traffic-title">
    <header class="observatory-section-header">
      <h2 id="page-traffic-title">Page traffic</h2>
    </header>

    <div class="traffic-force-stage">
      <ForceNetwork
        nodes={trafficGraphNodes}
        links={navigationNetworkLinks}
        centerNodeId="home"
        idPrefix="stats-traffic-network"
        ariaLabel="Interactive website traffic network with visit totals"
        height="min(62svh, 40rem)"
        showHint={false}
        collisionSounds={false}
        settings={{
          layout: 'radial',
          radialRadius: 0.33,
          radialStartAngle: -Math.PI / 2,
          entranceRadius: 0,
          chargeStrength: -205,
          anchorStrength: 0.19,
          centerAnchorStrength: 0.42,
          collisionPadding: 18,
          linkStrength: 0.2,
        }}
      />
    </div>
  </section>

  <section class="observatory-section observatory-histogram" aria-labelledby="visit-time-title">
    <header class="observatory-section-header">
      <h2 id="visit-time-title">Visit time</h2>
    </header>

    <div class="visit-histogram" role="group" aria-label="Visits by the viewer's local hour of day">
      <div class="histogram-y-axis" aria-hidden="true">
        <span class="histogram-y-title">Visits</span>
        <div class="histogram-y-ticks">
          {#each histogramTicks as tick}
            <span>{formatNumber(tick)}</span>
          {/each}
        </div>
      </div>

      <div class="histogram-plot">
        <div class="histogram-grid" aria-hidden="true">
          <span></span><span></span><span></span><span></span><span></span>
        </div>

        <div class="histogram-bars">
          {#each hourly as item}
            <button
              type="button"
              class:active={displayedHour === item.hour}
              aria-pressed={selectedHour === item.hour}
              aria-label={`${formatLocalHour(item.hour, true)}: ${formatNumber(item.value)} visits`}
              on:mouseenter={() => (hoveredHour = item.hour)}
              on:mouseleave={() => (hoveredHour = null)}
              on:focus={() => (hoveredHour = item.hour)}
              on:blur={() => (hoveredHour = null)}
              on:click={() => (selectedHour = item.hour)}
            >
              <span class="histogram-bar-track">
                <span
                  class="histogram-bar-fill"
                  style={`--bar-height:${histogramHeight(item.value)}%`}
                ></span>
                <span
                  class="histogram-bar-cap"
                  style={`--bar-height:${histogramHeight(item.value)}%`}
                ></span>

                {#if displayedHour === item.hour}
                  <span
                    class="histogram-bar-tooltip"
                    style={`--bar-height:${histogramHeight(item.value)}%`}
                    aria-hidden="true"
                  >
                    <strong>{formatNumber(item.value)}</strong>
                    <span>{formatLocalHour(item.hour, true)}</span>
                  </span>
                {/if}
              </span>
              <small>{item.hour % 3 === 0 ? formatHourTick(item.hour) : ''}</small>
            </button>
          {/each}
        </div>
      </div>

      <div class="histogram-x-axis" aria-hidden="true">Local hour</div>
    </div>
  </section>

  <section class="observatory-section observatory-path" aria-labelledby="your-path-title">
    <header class="observatory-section-header">
      <h2 id="your-path-title">Your path</h2>
    </header>
    <YourPathGraph />
  </section>
</div>
