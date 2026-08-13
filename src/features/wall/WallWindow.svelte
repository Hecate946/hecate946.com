<script lang="ts">
  import type { WallDestination } from './wall-config';
  import { withBase } from '@/lib/paths';

  export let destination: WallDestination;
  export let primary = true;
  export let eager = false;
  export let indexLabel: string;
  export let onFocus: () => void;
  export let onEnter: (event: MouseEvent) => void;

  const paintingSrcset = destination.painting.sources
    .map((source) => `${withBase(source.src)} ${source.width}w`)
    .join(', ');
</script>

<a
  class="wall-window"
  href={withBase(destination.href)}
  aria-label={primary ? `Enter ${destination.label}` : undefined}
  aria-hidden={primary ? undefined : 'true'}
  data-wall-window={destination.id}
  data-astro-prefetch={primary ? true : undefined}
  draggable="false"
  tabindex={primary ? undefined : -1}
  onfocus={() => primary && onFocus()}
  style={`left: ${destination.x}px;`}
  onclick={onEnter}
>
  <span class="wall-window__recess" aria-hidden="true">
    <span class="wall-window__glass">
      <img
        class="wall-window__painting"
        src={withBase(destination.painting.src)}
        srcset={paintingSrcset}
        sizes="(max-width: 40rem) 248px, (max-height: 42rem) 266px, (min-height: 50rem) 340px, 306px"
        alt=""
        width={destination.painting.width}
        height={destination.painting.height}
        draggable="false"
        decoding="async"
        loading={eager ? 'eager' : 'lazy'}
        fetchpriority={eager ? 'high' : 'low'}
      />
    </span>
    <span class="wall-window__reflection"></span>
  </span>

  <span class="wall-window__sill" aria-hidden="true"></span>
  <span class:wall-window__label--clone={!primary} class="wall-window__label">
    {#if primary}
      <span class="wall-window__index">{indexLabel}</span>
      <span class="wall-window__name">{destination.label}</span>
    {:else}
      <span class="wall-window__index" data-display-text={indexLabel}></span>
      <span class="wall-window__name" data-display-text={destination.label}></span>
    {/if}
    <span class="wall-window__arrow" aria-hidden="true">
      <svg viewBox="0 0 16 16" width="16" height="16" aria-hidden="true" focusable="false">
        <path d="M4 12 12 4M6.25 4H12v5.75" />
      </svg>
    </span>
  </span>
</a>


