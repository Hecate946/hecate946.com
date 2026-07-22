<script lang="ts">
  import { onMount } from 'svelte';
  import type { Season } from '@/config/seasons';
  import { trackEvent } from '@/lib/analytics';

  let picker: HTMLDivElement;

  function updateThemeColor() {
    requestAnimationFrame(() => {
      const themeColor = getComputedStyle(document.documentElement)
        .getPropertyValue('--header-bg')
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
      // The selected season still applies for this page if storage is blocked.
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
  <button
    type="button"
    class="season-button spring"
    data-season="spring"
    aria-pressed="false"
    aria-label="Use spring theme"
    title="Spring"
    onclick={() => applySeason('spring')}
  >
    <svg viewBox="0 0 32 32" aria-hidden="true">
      <path d="M16 18v10M16 23c-4-1-6 0-8 3M16 24c4-2 6-1 8 1"></path>
      <circle cx="16" cy="14" r="2.4"></circle>
      <path
        d="M16 11C12 7 12 3 16 3s4 4 0 8ZM19 14c4-4 8-4 8 0s-4 4-8 0ZM16 17c4 4 4 8 0 8s-4-4 0-8ZM13 14c-4 4-8 4-8 0s4-4 8 0Z"
      ></path>
    </svg>
  </button>

  <button
    type="button"
    class="season-button summer"
    data-season="summer"
    aria-pressed="false"
    aria-label="Use summer theme"
    title="Summer"
    onclick={() => applySeason('summer')}
  >
    <svg viewBox="0 0 32 32" aria-hidden="true">
      <circle cx="16" cy="16" r="6"></circle>
      <path
        d="M16 2v5M16 25v5M2 16h5M25 16h5M6.1 6.1l3.5 3.5M22.4 22.4l3.5 3.5M25.9 6.1l-3.5 3.5M9.6 22.4l-3.5 3.5"
      ></path>
    </svg>
  </button>

  <button
    type="button"
    class="season-button autumn"
    data-season="autumn"
    aria-pressed="false"
    aria-label="Use autumn theme"
    title="Autumn"
    onclick={() => applySeason('autumn')}
  >
    <svg viewBox="0 0 32 32" aria-hidden="true">
      <path d="M26 5C15 5 7 10 6 21c6 2 13 0 17-5 3-4 3-8 3-11Z"></path>
      <path d="M7 26c4-7 9-11 17-16M14 18l-1-6M18 14l5 1"></path>
    </svg>
  </button>

  <button
    type="button"
    class="season-button winter"
    data-season="winter"
    aria-pressed="false"
    aria-label="Use winter theme"
    title="Winter"
    onclick={() => applySeason('winter')}
  >
    <svg viewBox="0 0 32 32" aria-hidden="true">
      <path
        d="M16 2v28M4 9l24 14M4 23 28 9M12 5l4 4 4-4M12 27l4-4 4 4M5 13l6 1-2-6M27 19l-6-1 2 6M9 24l2-6-6 1M23 8l-2 6 6-1"
      ></path>
    </svg>
  </button>
</div>

<style>
  .season-picker {
    --season-button-size: 2.25rem;

    display: grid;
    width: 100%;
    height: 100%;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    align-items: center;
    justify-items: center;
    gap: 0;
    padding: 0.18rem 0.25rem;
  }

  .season-button {
    display: grid;
    width: var(--season-button-size);
    aspect-ratio: 1;
    place-items: center;
    padding: 0.08rem;
    border: 1px solid color-mix(in srgb, currentColor 34%, transparent);
    border-radius: 0.58rem;
    outline: 2px solid transparent;
    outline-offset: 1px;
    background: var(--season-preview-bg);
    box-shadow: inset 0 0 0 1px rgb(255 255 255 / 0.22);
    color: var(--season-preview-ink);
    cursor: pointer;
    transition:
      border-color 140ms ease,
      outline-color 140ms ease,
      box-shadow 140ms ease,
      transform 140ms ease;
  }

  .season-button:hover,
  .season-button:focus-visible {
    border-color: color-mix(in srgb, var(--header-accent) 80%, currentColor);
    outline-color: color-mix(
      in srgb,
      var(--header-accent) 62%,
      transparent
    );
    transform: translateY(-1px);
  }

  :global(html[data-season='spring']) .spring,
  :global(html[data-season='summer']) .summer,
  :global(html[data-season='autumn']) .autumn,
  :global(html[data-season='winter']) .winter {
    border-color: color-mix(in srgb, var(--header-accent) 82%, currentColor);
    outline-color: color-mix(
      in srgb,
      var(--header-accent) 90%,
      white 10%
    );
    box-shadow:
      inset 0 0 0 1px rgb(255 255 255 / 0.34),
      0 0 0 2px color-mix(in srgb, var(--header-accent) 26%, transparent);
  }

  :global(html[data-theme='dark'][data-season='spring']) .spring,
  :global(html[data-theme='dark'][data-season='summer']) .summer,
  :global(html[data-theme='dark'][data-season='autumn']) .autumn,
  :global(html[data-theme='dark'][data-season='winter']) .winter {
    outline-color: color-mix(
      in srgb,
      var(--header-accent) 68%,
      white 32%
    );
    box-shadow:
      inset 0 0 0 1px rgb(255 255 255 / 0.38),
      0 0 0 2px color-mix(in srgb, white 20%, transparent),
      0 0 0 4px color-mix(in srgb, var(--header-accent) 24%, transparent);
  }

  .spring {
    --season-preview-bg: #f3a8bc;
    --season-preview-ink: #355f43;
  }

  .summer {
    --season-preview-bg: #ffd064;
    --season-preview-ink: #176f72;
  }

  .autumn {
    --season-preview-bg: #e77b4d;
    --season-preview-ink: #562d26;
  }

  .winter {
    --season-preview-bg: #c7e4f1;
    --season-preview-ink: #486783;
  }

  svg {
    width: 100%;
    height: 100%;
    fill: none;
    stroke: currentColor;
    stroke-linecap: round;
    stroke-linejoin: round;
    stroke-width: 1.75;
  }

  /* This breakpoint must match Header.astro. */
  @media (max-width: 58rem) {
    .season-picker {
      --season-button-size: 1.92rem;

      grid-template-columns: repeat(2, minmax(0, 1fr));
      grid-template-rows: repeat(2, minmax(0, 1fr));
      padding: 0.14rem;
    }

    .season-button {
      padding: 0.06rem;
      border-radius: 0.46rem;
    }
  }

  @media (max-width: 24rem) {
    .season-picker {
      --season-button-size: 1.78rem;
    }
  }
</style>
