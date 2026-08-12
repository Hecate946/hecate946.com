<script lang="ts">
  import type { WallDestination } from './wall-config';
  import { withBase } from '@/lib/paths';

  export let destination: WallDestination;
  export let entering = false;
  export let keyboardAccessible = true;
  export let semantic = true;
  export let eager = false;
  export let indexLabel: string | undefined = undefined;
  export let onFocus: (destination: WallDestination) => void;
  export let onEnter: (event: MouseEvent, destination: WallDestination) => void;

  const displayIndex = indexLabel ?? wallIndex(destination.id);
  const paintingSrcset = destination.painting.sources
    ?.map((source) => `${withBase(source.src)} ${source.width}w`)
    .join(', ');

  function wallIndex(id: string) {
    const order = ['about', 'projects', 'resume', 'contact'];
    const index = order.indexOf(id);
    return String(index + 1).padStart(2, '0');
  }
</script>

<a
  class:wall-window--entering={entering}
  class="wall-window"
  href={withBase(destination.href)}
  aria-label={semantic ? `Enter ${destination.label}` : undefined}
  aria-hidden={semantic ? undefined : 'true'}
  data-wall-window={destination.id}
  data-astro-prefetch={semantic ? true : undefined}
  draggable="false"
  tabindex={keyboardAccessible ? undefined : -1}
  onfocus={() => keyboardAccessible && onFocus(destination)}
  style={`left: ${destination.x}px; --painting-position: ${destination.painting.objectPosition ?? '50% 50%'}; --painting-fit: ${destination.painting.objectFit ?? 'cover'};`}
  onclick={(event) => onEnter(event, destination)}
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
  <span class:wall-window__label--clone={!semantic} class="wall-window__label">
    {#if semantic}
      <span class="wall-window__index">{displayIndex}</span>
      <span class="wall-window__name">{destination.label}</span>
    {:else}
      <span class="wall-window__index" data-display-text={displayIndex}></span>
      <span class="wall-window__name" data-display-text={destination.label}></span>
    {/if}
    <span class="wall-window__arrow" aria-hidden="true">
      <svg viewBox="0 0 16 16" width="16" height="16" aria-hidden="true" focusable="false">
        <path d="M4 12 12 4M6.25 4H12v5.75" />
      </svg>
    </span>
  </span>
</a>


