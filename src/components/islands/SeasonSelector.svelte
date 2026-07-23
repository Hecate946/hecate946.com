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

  let picker: HTMLDivElement;

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
          <path d="M16 18v10M16 23c-4-1-6 0-8 3M16 24c4-2 6-1 8 1"></path>
          <circle cx="16" cy="14" r="2.4"></circle>
          <path
            d="M16 11C12 7 12 3 16 3s4 4 0 8ZM19 14c4-4 8-4 8 0s-4 4-8 0ZM16 17c4 4 4 8 0 8s-4-4 0-8ZM13 14c-4 4-8 4-8 0s4-4 8 0Z"
          ></path>
        </svg>
      {:else if season.id === 'summer'}
        <svg viewBox="0 0 32 32" aria-hidden="true">
          <circle cx="16" cy="16" r="6"></circle>
          <path
            d="M16 2v5M16 25v5M2 16h5M25 16h5M6.1 6.1l3.5 3.5M22.4 22.4l3.5 3.5M25.9 6.1l-3.5 3.5M9.6 22.4l-3.5 3.5"
          ></path>
        </svg>
      {:else if season.id === 'autumn'}
        <svg viewBox="0 0 32 32" aria-hidden="true">
          <path d="M26 5C15 5 7 10 6 21c6 2 13 0 17-5 3-4 3-8 3-11Z"></path>
          <path d="M7 26c4-7 9-11 17-16M14 18l-1-6M18 14l5 1"></path>
        </svg>
      {:else}
        <svg viewBox="0 0 32 32" aria-hidden="true">
          <path
            d="M16 2v28M4 9l24 14M4 23 28 9M12 5l4 4 4-4M12 27l4-4 4 4M5 13l6 1-2-6M27 19l-6-1 2 6M9 24l2-6-6 1M23 8l-2 6 6-1"
          ></path>
        </svg>
      {/if}
    </button>
  {/each}
</div>
