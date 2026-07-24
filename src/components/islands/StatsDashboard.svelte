<script lang="ts">
  import { onMount } from 'svelte';
  import VisitorMap from '@/components/islands/VisitorMap.svelte';

  export let apiBase = '';
  export let codeStatsUrl = '/generated/code-stats.json';

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
  }

  interface CodeStats {
    generatedAt: string;
    commit: {
      count: number;
      latestSha: string | null;
      latestDate: string | null;
      latestMessage: string | null;
      firstDate: string | null;
    };
    repository: {
      files: number;
      countedFiles?: number;
      directories: number;
      totalLines: number;
      sourceLines: number;
    };
    site: {
      pages: number;
      components: number;
      layouts: number;
      assets: number;
    };
    languages: Array<{
      name: string;
      files: number;
      lines: number;
      percentage: number;
    }>;
  }

  let liveStats: LiveStats | null = null;
  let codeStats: CodeStats | null = null;
  let liveError = '';
  let codeError = '';
  type StatsTab = 'website' | 'code' | 'you';

  interface YourStats {
    firstVisitAt: string;
    lastVisitAt: string;
    visits: number;
    pageViews: number;
    activeSeconds: number;
    interactions: number;
    pages: Record<string, number>;
    events: Record<string, number>;
    colorTheme: string;
    season: string;
  }

  const LOCAL_STATS_KEY = 'hecate946:your-stats';
  let activeTab: StatsTab = 'website';
  let yourStats: YourStats | null = null;
  let refreshing = false;

  const numberFormatter = new Intl.NumberFormat('en-US');
  const compactFormatter = new Intl.NumberFormat('en-US', {
    notation: 'compact',
    maximumFractionDigits: 1,
  });
  const dateFormatter = new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
  const dateTimeFormatter = new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  });

  function formatNumber(value: number, compact = false) {
    return (compact ? compactFormatter : numberFormatter).format(value ?? 0);
  }

  function formatDate(value: string | null | undefined) {
    if (!value) return 'Not yet';
    const date = new Date(value);
    return Number.isNaN(date.valueOf()) ? 'Unknown' : dateFormatter.format(date);
  }

  function formatDateTime(value: string | null | undefined) {
    if (!value) return 'not yet';
    const date = new Date(value);
    return Number.isNaN(date.valueOf())
      ? 'at an unknown time'
      : dateTimeFormatter.format(date);
  }

  function formatDuration(totalSeconds: number) {
    const minutes = Math.floor(totalSeconds / 60);
    const hours = Math.floor(minutes / 60);
    if (hours) return `${hours}h ${minutes % 60}m`;
    if (minutes) return `${minutes}m`;
    return `${Math.max(0, totalSeconds)}s`;
  }

  function rankedEntries(values: Record<string, number> = {}) {
    return Object.entries(values)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 8);
  }

  function loadYourStats() {
    try {
      const saved = window.localStorage.getItem(LOCAL_STATS_KEY);
      yourStats = saved ? JSON.parse(saved) as YourStats : null;
    } catch {
      yourStats = null;
    }
  }

  function selectTab(tab: StatsTab, updateUrl = true) {
    activeTab = tab;
    if (!updateUrl) return;
    const url = new URL(window.location.href);
    url.searchParams.set('tab', tab);
    window.history.replaceState({}, '', url);
  }

  function clearYourStats() {
    window.localStorage.removeItem(LOCAL_STATS_KEY);
    yourStats = null;
  }

  function humanizeEvent(value: string) {
    return value
      .replaceAll('_', ' ')
      .replace(/\b\w/g, (letter) => letter.toUpperCase());
  }

  async function readJson<T>(url: string): Promise<T> {
    const response = await fetch(url, {
      headers: { Accept: 'application/json' },
      cache: 'no-store',
    });

    if (!response.ok) {
      throw new Error(`${response.status} ${response.statusText}`);
    }

    return response.json() as Promise<T>;
  }

  async function loadLiveStats() {
    const base = apiBase.trim().replace(/\/$/, '');

    if (!base) {
      liveError = 'Live analytics are not configured yet.';
      return;
    }

    try {
      liveStats = await readJson<LiveStats>(`${base}/api/stats?days=30`);
      liveError = '';
    } catch (error) {
      liveError = `Live analytics are temporarily unavailable${
        error instanceof Error ? `: ${error.message}` : '.'
      }`;
    }
  }

  async function loadCodeStats() {
    try {
      codeStats = await readJson<CodeStats>(codeStatsUrl);
      codeError = '';
    } catch (error) {
      codeError = `Code statistics are unavailable${
        error instanceof Error ? `: ${error.message}` : '.'
      }`;
    }
  }

  async function refresh() {
    refreshing = true;
    await Promise.all([loadLiveStats(), loadCodeStats()]);
    refreshing = false;
  }

  function chartPath(values: number[], width = 720, height = 190) {
    if (values.length === 0) return '';

    const horizontalPadding = 24;
    const verticalPadding = 22;
    const maximum = Math.max(1, ...values);
    const drawableWidth = width - horizontalPadding * 2;
    const drawableHeight = height - verticalPadding * 2;

    return values
      .map((value, index) => {
        const x =
          horizontalPadding +
          (values.length === 1
            ? drawableWidth / 2
            : (index / (values.length - 1)) * drawableWidth);
        const y =
          height -
          verticalPadding -
          (Math.max(0, value) / maximum) * drawableHeight;

        return `${index === 0 ? 'M' : 'L'}${x.toFixed(2)},${y.toFixed(2)}`;
      })
      .join(' ');
  }

  onMount(() => {
    const requestedTab = new URL(window.location.href).searchParams.get('tab');
    if (requestedTab === 'code' || requestedTab === 'you') activeTab = requestedTab;
    loadYourStats();
    window.addEventListener('hecate:local-stats-updated', loadYourStats);
    void refresh();
    const interval = window.setInterval(() => void loadLiveStats(), 15_000);
    return () => {
      window.clearInterval(interval);
      window.removeEventListener('hecate:local-stats-updated', loadYourStats);
    };
  });
</script>

<div class="stats-dashboard" aria-busy={refreshing}>
  <nav class="stats-tabs" aria-label="Stats sections">
    <button class:active={activeTab === 'website'} aria-selected={activeTab === 'website'} on:click={() => selectTab('website')}>Website stats</button>
    <button class:active={activeTab === 'code'} aria-selected={activeTab === 'code'} on:click={() => selectTab('code')}>Code stats</button>
    <button class:active={activeTab === 'you'} aria-selected={activeTab === 'you'} on:click={() => selectTab('you')}>Your stats</button>
  </nav>

  {#if activeTab === 'website'}
  <section class="stats-section" aria-labelledby="website-stats-title">
    <div class="stats-section-heading">
      <h2 id="website-stats-title">Website</h2>
      <p
        class="stats-status"
        data-state={liveStats && !liveError ? 'live' : 'offline'}
      >
        {#if liveStats && !liveError}
          Live · updated {formatDateTime(liveStats.summary.updatedAt)}
        {:else}
          {liveError || 'Connecting…'}
        {/if}
      </p>
    </div>

    <div class="stats-metrics">
      <div class="stats-metric">
        <strong>{formatNumber(liveStats?.summary.estimatedVisitors ?? 0)}</strong>
        <span>Estimated visitors</span>
      </div>
      <div class="stats-metric">
        <strong>{formatNumber(liveStats?.summary.pageViews ?? 0)}</strong>
        <span>Page views</span>
      </div>
      <div class="stats-metric">
        <strong>{formatNumber(liveStats?.summary.sessions ?? 0)}</strong>
        <span>Sessions</span>
      </div>
      <div class="stats-metric">
        <strong>{formatNumber(liveStats?.summary.trackedRequests ?? 0)}</strong>
        <span>Tracked requests</span>
      </div>
      <div class="stats-metric">
        <strong>{formatNumber(liveStats?.summary.countries ?? 0)}</strong>
        <span>Countries</span>
      </div>
      <div class="stats-metric">
        <strong>{formatNumber(liveStats?.summary.activeVisitors ?? 0)}</strong>
        <span>Active now</span>
      </div>
    </div>

    <div class="stats-grid">
      <article class="stats-panel stats-panel-map">
        <div class="stats-panel-heading">
          <h3>Where people visit from</h3>
          <p>One anonymous dot per visitor; nearby dots remain separate.</p>
        </div>

        {#if liveStats?.locations?.length}
          <VisitorMap
            locations={liveStats.locations}
            totalVisitors={liveStats.summary.estimatedVisitors}
          />
        {:else if liveError}
          <div class="stats-error">{liveError}</div>
        {:else}
          <div class="stats-empty">
            No visitor location data has been recorded yet.
          </div>
        {/if}
      </article>

      <article class="stats-panel stats-panel-wide">
        <div class="stats-panel-heading">
          <h3>Last 30 days</h3>
          <p>Daily page views</p>
        </div>

        {#if liveStats?.daily?.length}
          <div class="activity-chart">
            <svg viewBox="0 0 720 190" role="img" aria-label="Daily page views over the last 30 days">
              <line class="chart-guide" x1="24" x2="696" y1="22" y2="22" />
              <line class="chart-baseline" x1="24" x2="696" y1="168" y2="168" />
              <path
                class="chart-line"
                d={chartPath(liveStats.daily.map((item) => item.pageViews))}
              />
              <text x="24" y="184">{liveStats.daily[0]?.day ?? ''}</text>
              <text x="696" y="184" text-anchor="end">
                {liveStats.daily[liveStats.daily.length - 1]?.day ?? ''}
              </text>
              <text x="696" y="17" text-anchor="end">
                {formatNumber(Math.max(...liveStats.daily.map((item) => item.pageViews)))} max
              </text>
            </svg>
          </div>
        {:else}
          <div class="stats-empty">No daily activity recorded yet.</div>
        {/if}
      </article>

      <article class="stats-panel stats-panel-half">
        <div class="stats-panel-heading">
          <h3>Most visited</h3>
          <p>Page views</p>
        </div>

        {#if liveStats?.pages?.length}
          <ol class="stats-list">
            {#each liveStats.pages as item}
              <li>
                <span class="stats-list-label">{item.label}</span>
                <span class="stats-list-value">{formatNumber(item.value)}</span>
              </li>
            {/each}
          </ol>
        {:else}
          <div class="stats-empty">No page ranking yet.</div>
        {/if}
      </article>

      <article class="stats-panel stats-panel-half">
        <div class="stats-panel-heading">
          <h3>Interactions</h3>
          <p>Accepted analytics events</p>
        </div>

        {#if liveStats?.interactions?.length}
          <ol class="stats-list">
            {#each liveStats.interactions as item}
              <li>
                <span class="stats-list-label">{humanizeEvent(item.label)}</span>
                <span class="stats-list-value">{formatNumber(item.value)}</span>
              </li>
            {/each}
          </ol>
        {:else}
          <div class="stats-empty">No interactions recorded yet.</div>
        {/if}
      </article>
    </div>

    <p class="stats-footnote">
      “Tracked requests” means requests accepted by this site's analytics API,
      not every image, font, or asset request served by GitHub Pages. Visitor
      totals are estimates because browsers can clear storage or visit from
      multiple devices.
    </p>
  </section>
  {:else if activeTab === 'code'}
  <section class="stats-section" aria-labelledby="code-stats-title">
    <div class="stats-section-heading">
      <h2 id="code-stats-title">Code</h2>
      <p>
        {#if codeStats}
          Generated from commit {codeStats.commit.latestSha?.slice(0, 7) ?? 'unknown'} on {formatDate(codeStats.generatedAt)}
        {:else}
          {codeError || 'Reading the repository…'}
        {/if}
      </p>
    </div>

    {#if codeStats}
      <div class="stats-grid">
        <article class="stats-panel stats-panel-wide">
          <div class="code-summary">
            <div>
              <strong>{formatNumber(codeStats.repository.sourceLines, true)}</strong>
              <span>Non-empty source lines</span>
            </div>
            <div>
              <strong>{formatNumber(codeStats.repository.files)}</strong>
              <span>Tracked files</span>
            </div>
            <div>
              <strong>{formatNumber(codeStats.commit.count)}</strong>
              <span>Commits</span>
            </div>
          </div>
        </article>

        <article class="stats-panel stats-panel-half">
          <div class="stats-panel-heading">
            <h3>Languages</h3>
            <p>By non-empty lines</p>
          </div>

          <ol class="language-list">
            {#each codeStats.languages.slice(0, 10) as language}
              <li>
                <div class="language-row">
                  <span>{language.name}</span>
                  <span>{formatNumber(language.lines)} · {language.percentage.toFixed(1)}%</span>
                </div>
                <div class="language-track" aria-hidden="true">
                  <span style={`--share: ${language.percentage}%`}></span>
                </div>
              </li>
            {/each}
          </ol>
        </article>

        <article class="stats-panel stats-panel-half">
          <div class="stats-panel-heading">
            <h3>Site structure</h3>
            <p>Current build source</p>
          </div>

          <ul class="stats-list">
            <li>
              <span class="stats-list-label">Pages</span>
              <span class="stats-list-value">{formatNumber(codeStats.site.pages)}</span>
            </li>
            <li>
              <span class="stats-list-label">Components</span>
              <span class="stats-list-value">{formatNumber(codeStats.site.components)}</span>
            </li>
            <li>
              <span class="stats-list-label">Layouts</span>
              <span class="stats-list-value">{formatNumber(codeStats.site.layouts)}</span>
            </li>
            <li>
              <span class="stats-list-label">Public assets</span>
              <span class="stats-list-value">{formatNumber(codeStats.site.assets)}</span>
            </li>
            <li>
              <span class="stats-list-label">Directories</span>
              <span class="stats-list-value">{formatNumber(codeStats.repository.directories)}</span>
            </li>
            <li>
              <span class="stats-list-label">First commit</span>
              <span class="stats-list-value">{formatDate(codeStats.commit.firstDate)}</span>
            </li>
          </ul>
        </article>
      </div>

      <p class="stats-footnote">
        Code statistics are regenerated during every GitHub Pages deployment.
        Build output, dependencies, lockfiles, binaries, and generated analytics
        files are excluded from line counts.
      </p>
    {:else}
      <div class={codeError ? 'stats-error' : 'stats-empty'}>
        {codeError || 'Generating code statistics…'}
      </div>
    {/if}
  </section>
  {:else}
  <section class="stats-section" aria-labelledby="your-stats-title">
    <div class="stats-section-heading">
      <div>
        <h2 id="your-stats-title">Your stats</h2>
        <p>Stored only in this browser. Nothing here identifies you personally.</p>
      </div>
      {#if yourStats}
        <button class="stats-reset" type="button" on:click={clearYourStats}>Clear my stats</button>
      {/if}
    </div>

    {#if yourStats}
      <div class="stats-metrics">
        <div class="stats-metric"><strong>{formatNumber(yourStats.visits)}</strong><span>Visits</span></div>
        <div class="stats-metric"><strong>{formatNumber(yourStats.pageViews)}</strong><span>Page views</span></div>
        <div class="stats-metric"><strong>{formatDuration(yourStats.activeSeconds)}</strong><span>Active time</span></div>
        <div class="stats-metric"><strong>{formatNumber(yourStats.interactions)}</strong><span>Interactions</span></div>
        <div class="stats-metric"><strong>{humanizeEvent(yourStats.season)}</strong><span>Favorite season setting</span></div>
        <div class="stats-metric"><strong>{humanizeEvent(yourStats.colorTheme)}</strong><span>Color mode</span></div>
      </div>

      <div class="stats-grid">
        <article class="stats-panel stats-panel-half">
          <div class="stats-panel-heading"><h3>Your most visited pages</h3><p>On this browser</p></div>
          {#if rankedEntries(yourStats.pages).length}
            <ol class="stats-list">
              {#each rankedEntries(yourStats.pages) as [label, value]}
                <li><span class="stats-list-label">{label}</span><span class="stats-list-value">{formatNumber(value)}</span></li>
              {/each}
            </ol>
          {:else}<div class="stats-empty">Explore a few pages to build your history.</div>{/if}
        </article>

        <article class="stats-panel stats-panel-half">
          <div class="stats-panel-heading"><h3>Your interactions</h3><p>Buttons, themes, searches, and links</p></div>
          {#if rankedEntries(yourStats.events).length}
            <ol class="stats-list">
              {#each rankedEntries(yourStats.events) as [label, value]}
                <li><span class="stats-list-label">{humanizeEvent(label)}</span><span class="stats-list-value">{formatNumber(value)}</span></li>
              {/each}
            </ol>
          {:else}<div class="stats-empty">Your interactions will appear here.</div>{/if}
        </article>
      </div>

      <p class="stats-footnote">First seen {formatDate(yourStats.firstVisitAt)} · Most recently active {formatDateTime(yourStats.lastVisitAt)}. Clearing browser storage or using another device starts a separate history.</p>
    {:else}
      <div class="stats-empty stats-empty-personal">Your personal history starts as you browse this site. Reload once after this update is deployed to begin tracking it.</div>
    {/if}
  </section>
  {/if}
</div>
