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
          <g transform="translate(16 16) scale(1.5) translate(-16 -16)">
            <path d="M16 15c-3.4-1.5-4.5-4.5-2.5-6.3 1.8-1.6 4.5-.2 4.5 3.1 0 1.4-.7 2.5-2 3.2Z"></path>
            <path d="M16 15c-3.4-1.5-4.5-4.5-2.5-6.3 1.8-1.6 4.5-.2 4.5 3.1 0 1.4-.7 2.5-2 3.2Z" transform="rotate(72 16 16)"></path>
            <path d="M16 15c-3.4-1.5-4.5-4.5-2.5-6.3 1.8-1.6 4.5-.2 4.5 3.1 0 1.4-.7 2.5-2 3.2Z" transform="rotate(144 16 16)"></path>
            <path d="M16 15c-3.4-1.5-4.5-4.5-2.5-6.3 1.8-1.6 4.5-.2 4.5 3.1 0 1.4-.7 2.5-2 3.2Z" transform="rotate(216 16 16)"></path>
            <path d="M16 15c-3.4-1.5-4.5-4.5-2.5-6.3 1.8-1.6 4.5-.2 4.5 3.1 0 1.4-.7 2.5-2 3.2Z" transform="rotate(288 16 16)"></path>
            <circle cx="16" cy="16" r="2.1"></circle>
            <path d="m14.8 15.2-1.2-1.1M17.2 15.2l1.2-1.1M16 17.2v1.7"></path>
          </g>
        </svg>
      {:else if season.id === 'summer'}
        <svg viewBox="0 0 32 32" aria-hidden="true">
          <g>
            <path d="M16 10.7c-2.1-2.1-2.1-5.1 0-7 2.1 1.9 2.1 4.9 0 7Z"></path>
            <path d="M16 10.7c-2.1-2.1-2.1-5.1 0-7 2.1 1.9 2.1 4.9 0 7Z" transform="rotate(45 16 16)"></path>
            <path d="M16 10.7c-2.1-2.1-2.1-5.1 0-7 2.1 1.9 2.1 4.9 0 7Z" transform="rotate(90 16 16)"></path>
            <path d="M16 10.7c-2.1-2.1-2.1-5.1 0-7 2.1 1.9 2.1 4.9 0 7Z" transform="rotate(135 16 16)"></path>
            <path d="M16 10.7c-2.1-2.1-2.1-5.1 0-7 2.1 1.9 2.1 4.9 0 7Z" transform="rotate(180 16 16)"></path>
            <path d="M16 10.7c-2.1-2.1-2.1-5.1 0-7 2.1 1.9 2.1 4.9 0 7Z" transform="rotate(225 16 16)"></path>
            <path d="M16 10.7c-2.1-2.1-2.1-5.1 0-7 2.1 1.9 2.1 4.9 0 7Z" transform="rotate(270 16 16)"></path>
            <path d="M16 10.7c-2.1-2.1-2.1-5.1 0-7 2.1 1.9 2.1 4.9 0 7Z" transform="rotate(315 16 16)"></path>
          </g>
          <circle cx="16" cy="16" r="4.7"></circle>
          <path d="M14.2 14.3h.1M17.7 14.3h.1M14.2 17.7h.1M17.7 17.7h.1M16 16h.1"></path>
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
