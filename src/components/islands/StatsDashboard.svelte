<script lang="ts">
  import type { StatsSnapshot, StatsWindowKey } from '@/types/stats';

  export let stats: StatsSnapshot;
  let windowKey: StatsWindowKey = '30';
  $: current = stats.windows[windowKey];
  $: maxViews = Math.max(
    ...current.topSections.map((section) => section.views),
    1,
  );

  function formatDuration(seconds: number) {
    return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
  }
</script>

<div class="dashboard">
  <div class="toolbar">
    <div>
      <span class="eyebrow">Public observatory</span>
      <p>Generated {new Date(stats.generatedAt).toLocaleString()}</p>
    </div>
    <label>
      <span>Window</span>
      <select bind:value={windowKey}>
        <option value="7">7 days</option>
        <option value="30">30 days</option>
        <option value="90">90 days</option>
      </select>
    </label>
  </div>

  {#if stats.isSample}
    <div class="sample-note">
      Sample data is active. Replace it through the stats generation script.
    </div>
  {/if}

  <section class="metrics" aria-label="Traffic summary">
    <article>
      <span>Visitors</span><strong>{current.visitors.toLocaleString()}</strong>
    </article>
    <article>
      <span>Page views</span><strong
        >{current.pageviews.toLocaleString()}</strong
      >
    </article>
    <article>
      <span>Average visit</span><strong
        >{formatDuration(current.averageSessionSeconds)}</strong
      >
    </article>
    <article>
      <span>Returning</span><strong>{current.returningPercent}%</strong>
    </article>
  </section>

  <div class="detail-grid">
    <section class="panel" aria-labelledby="attention-title">
      <h2 id="attention-title">Attention by world</h2>
      <div class="bars">
        {#each current.topSections as section}
          <div class="bar-row">
            <div>
              <span>{section.name}</span><strong>{section.views}</strong>
            </div>
            <div
              class="track"
              aria-label={`${section.name}: ${section.views} views`}
            >
              <span style={`width: ${(section.views / maxViews) * 100}%`}
              ></span>
            </div>
          </div>
        {/each}
      </div>
    </section>

    <section class="panel" aria-labelledby="health-title">
      <h2 id="health-title">Site health</h2>
      <dl>
        <div>
          <dt>Performance</dt>
          <dd>{stats.performance.lighthousePerformance}</dd>
        </div>
        <div>
          <dt>Accessibility</dt>
          <dd>{stats.performance.lighthouseAccessibility}</dd>
        </div>
        <div>
          <dt>JavaScript</dt>
          <dd>{stats.performance.javascriptKb} KB</dd>
        </div>
        <div>
          <dt>Images</dt>
          <dd>{stats.performance.imageKb} KB</dd>
        </div>
      </dl>
    </section>
  </div>

  <section class="panel" aria-labelledby="events-title">
    <h2 id="events-title">Meaningful interactions</h2>
    <div class="event-grid">
      {#each stats.events as event}
        <article>
          <strong>{event.count}</strong><span>{event.name}</span>
        </article>
      {/each}
    </div>
  </section>
</div>

<style>
  .dashboard {
    display: grid;
    gap: 1.25rem;
  }

  .toolbar,
  .metrics,
  .detail-grid,
  .event-grid,
  dl div {
    display: grid;
  }

  .toolbar {
    grid-template-columns: 1fr auto;
    gap: 1rem;
    align-items: end;
  }

  .toolbar p {
    margin: 0.2rem 0 0;
    color: var(--muted);
    font-size: 0.86rem;
  }

  label {
    display: grid;
    gap: 0.3rem;
    color: var(--muted);
    font-size: 0.82rem;
  }

  select {
    padding: 0.55rem 2rem 0.55rem 0.7rem;
    background: var(--surface-strong);
    border: 1px solid var(--line);
    border-radius: var(--radius-sm);
    color: var(--text);
  }

  .sample-note {
    padding: 0.75rem 1rem;
    background: var(--accent-soft);
    border: 1px solid color-mix(in srgb, var(--accent) 30%, var(--line));
    border-radius: var(--radius-md);
    color: var(--accent-strong);
  }

  .metrics {
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 0.75rem;
  }

  .metrics article,
  .panel {
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: var(--radius-lg);
  }

  .metrics article {
    padding: 1rem;
  }

  .metrics span,
  .event-grid span {
    color: var(--muted);
    font-size: 0.82rem;
  }

  .metrics strong {
    display: block;
    margin-top: 0.2rem;
    font-family: var(--font-display);
    font-size: clamp(1.8rem, 5vw, 3rem);
    font-weight: 500;
    line-height: 1;
  }

  .detail-grid {
    grid-template-columns: 1.5fr 1fr;
    gap: 1.25rem;
  }

  .panel {
    padding: clamp(1rem, 3vw, 1.5rem);
  }

  h2 {
    margin: 0 0 1.2rem;
    font-family: var(--font-display);
    font-size: 1.5rem;
    font-weight: 500;
  }

  .bars {
    display: grid;
    gap: 1rem;
  }

  .bar-row > div:first-child {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    margin-bottom: 0.35rem;
  }

  .track {
    height: 0.65rem;
    overflow: hidden;
    background: var(--accent-soft);
    border-radius: var(--radius-pill);
  }

  .track span {
    display: block;
    height: 100%;
    background: var(--accent);
    border-radius: inherit;
  }

  dl {
    display: grid;
    gap: 0.7rem;
    margin: 0;
  }

  dl div {
    grid-template-columns: 1fr auto;
    gap: 1rem;
    padding-bottom: 0.65rem;
    border-bottom: 1px solid var(--line);
  }

  dt {
    color: var(--muted);
  }

  dd {
    margin: 0;
    font-weight: 750;
  }

  .event-grid {
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 1rem;
  }

  .event-grid article {
    display: grid;
    gap: 0.2rem;
  }

  .event-grid strong {
    font-family: var(--font-display);
    font-size: 2rem;
    font-weight: 500;
  }

  @media (max-width: 48rem) {
    .metrics,
    .event-grid {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .detail-grid {
      grid-template-columns: 1fr;
    }
  }

  @media (max-width: 32rem) {
    .toolbar {
      grid-template-columns: 1fr;
      align-items: start;
    }
  }
</style>
