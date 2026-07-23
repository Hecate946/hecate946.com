<script lang="ts">
  import { onMount } from 'svelte';
  import type { Season } from '@/config/seasons';
  import { trackEvent } from '@/lib/analytics';

  const seasons = [
    { id: 'spring', label: 'Spring' },
    { id: 'summer', label: 'Summer' },
    { id: 'autumn', label: 'Autumn' },
    { id: 'winter', label: 'Winter' },
  ] as const satisfies readonly { id: Season; label: string }[];

  let picker!: HTMLDivElement;

  function updateThemeColor() {
    requestAnimationFrame(() => {
      const themeColor = getComputedStyle(document.documentElement)
        .getPropertyValue('--bg')
        .trim();

      if (themeColor) {
        document
          .querySelector<HTMLMetaElement>('meta[name="theme-color"]')
          ?.setAttribute('content', themeColor);
      }
    });
  }

  function syncPressedState() {
    const activeSeason = document.documentElement.dataset.season;

    picker
      ?.querySelectorAll<HTMLButtonElement>('[data-season]')
      .forEach((button) => {
        button.setAttribute(
          'aria-pressed',
          String(button.dataset.season === activeSeason),
        );
      });
  }

  function applySeason(next: Season) {
    document.documentElement.dataset.seasonPreference = next;
    document.documentElement.dataset.season = next;

    try {
      localStorage.setItem('season-preference', next);
    } catch {
      // The season still applies if storage is unavailable.
    }

    syncPressedState();
    updateThemeColor();
    trackEvent('season_changed', { preference: next, resolved: next });
  }

  onMount(() => {
    syncPressedState();
    const resync = () => syncPressedState();
    document.addEventListener('astro:after-swap', resync);

    return () => document.removeEventListener('astro:after-swap', resync);
  });
</script>

<div
  class="season-picker"
  role="group"
  aria-label="Choose a seasonal theme"
  bind:this={picker}
>
  {#each seasons as season}
    <button
      type="button"
      class={`season-button ${season.id}`}
      data-season={season.id}
      aria-pressed="false"
      aria-label={`Use ${season.label.toLowerCase()} theme`}
      title={season.label}
      onclick={() => applySeason(season.id)}
    >
      {#if season.id === 'spring'}
        <svg viewBox="0 0 32 32" aria-hidden="true">
          <g
            fill="none"
            stroke="currentColor"
            stroke-width="1.55"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <ellipse cx="16" cy="8.9" rx="3.85" ry="6.15"></ellipse>
            <ellipse cx="16" cy="8.9" rx="3.85" ry="6.15" transform="rotate(72 16 16)"></ellipse>
            <ellipse cx="16" cy="8.9" rx="3.85" ry="6.15" transform="rotate(144 16 16)"></ellipse>
            <ellipse cx="16" cy="8.9" rx="3.85" ry="6.15" transform="rotate(216 16 16)"></ellipse>
            <ellipse cx="16" cy="8.9" rx="3.85" ry="6.15" transform="rotate(288 16 16)"></ellipse>
            <circle cx="16" cy="16" r="2.65"></circle>
          </g>
        </svg>
      {:else if season.id === 'summer'}
        <svg viewBox="0 0 32 32" aria-hidden="true">
          <circle cx="16" cy="16" r="11.5"></circle>
          <circle cx="18.1" cy="12.7" r="2.15"></circle>
          <path d="M18.1 10.55C15.2 7.7 13.25 6.45 10.1 5.7"></path>
          <path d="M20.25 12.7c3.15.15 5.2 1.05 7.1 2.65"></path>
          <path d="M18.35 14.8c1.05 3.2.95 6.25-.25 10.7"></path>
          <path d="M16.15 14.05c-3.25 1.05-6 3.2-8.55 6.55"></path>
          <path d="M16.55 10.95c-2.25-.15-4.85.15-7.65 1.25"></path>
          <path d="M6.3 17.9c4.2.8 7.75 3.05 10.4 7.45"></path>
          <path d="M22.3 6.55c-.45 3.2.15 6.2 2.95 8.85"></path>
        </svg>
      {:else if season.id === 'autumn'}
        <svg viewBox="0 0 32 32" aria-hidden="true">
          <path d="M26 5C15 5 7 10 6 21c6 2 13 0 17-5 3-4 3-8 3-11Z"></path>
          <path d="M7 26c4-7 9-11 17-16M14 18l-1-6M18 14l5 1"></path>
        </svg>
      {:else}
        <svg viewBox="0 0 32 32" aria-hidden="true">
          <path d="M16 2v28M4 9l24 14M4 23 28 9M12 5l4 4 4-4M12 27l4-4 4 4M5 13l6 1-2-6M27 19l-6-1 2 6M9 24l2-6-6 1M23 8l-2 6 6-1"></path>
        </svg>
      {/if}
    </button>
  {/each}
</div>
