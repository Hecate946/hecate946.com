<script lang="ts">
  import { onMount } from 'svelte';
  import { getSeasonForMonth, type SeasonPreference } from '@/config/seasons';
  import { trackEvent } from '@/lib/analytics';

  let preference: SeasonPreference = 'auto';

  function applyPreference(next: SeasonPreference, shouldTrack = true) {
    preference = next;
    const resolved =
      next === 'auto' ? getSeasonForMonth(new Date().getMonth()) : next;
    document.documentElement.dataset.seasonPreference = next;
    document.documentElement.dataset.season = resolved;
    localStorage.setItem('season-preference', next);

    if (shouldTrack)
      trackEvent('season_changed', { preference: next, resolved });
  }

  function handleChange(event: Event) {
    applyPreference(
      (event.currentTarget as HTMLSelectElement).value as SeasonPreference,
    );
  }

  onMount(() => {
    const saved = document.documentElement.dataset.seasonPreference as
      SeasonPreference | undefined;
    applyPreference(saved ?? 'auto', false);
  });
</script>

<label>
  <span class="visually-hidden">Season theme</span>
  <select value={preference} on:change={handleChange} aria-label="Season theme">
    <option value="auto">Auto season</option>
    <option value="spring">Spring</option>
    <option value="summer">Summer</option>
    <option value="autumn">Autumn</option>
    <option value="winter">Winter</option>
  </select>
</label>

<style>
  select {
    max-width: 8.5rem;
    padding: 0.42rem 1.7rem 0.42rem 0.65rem;
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: var(--radius-pill);
    color: var(--text);
    font-size: 0.78rem;
  }
</style>
