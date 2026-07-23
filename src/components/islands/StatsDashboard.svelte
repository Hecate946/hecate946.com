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
    void refresh();
    const interval = window.setInterval(() => void loadLiveStats(), 60_000);
    return () => window.clearInterval(interval);
  });
</script>

<div class="stats-dashboard" aria-busy={refreshing}>
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
          <p>Aggregated locations; the view widens as the audience grows.</p>
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
            No location has crossed the public privacy threshold yet.
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
</div>
