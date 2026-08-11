<script lang="ts">
  import type { WallDestination } from './wall-config';
  import { withBase } from '@/lib/paths';

  export let destination: WallDestination;
  export let entering = false;
  export let keyboardAccessible = true;
  export let onFocus: (destination: WallDestination) => void;
  export let onEnter: (event: MouseEvent, destination: WallDestination) => void;

  const indexLabel = wallIndex(destination.id);
  const paintingSrcset = destination.painting.sources
    ?.map((source) => `${withBase(source.src)} ${source.width}w`)
    .join(', ');

  function wallIndex(id: string) {
    const order = ['about', 'projects', 'contact', 'stats'];
    const index = order.indexOf(id);
    return String(index + 1).padStart(2, '0');
  }
</script>

<a
  class:wall-window--entering={entering}
  class="wall-window"
  href={withBase(destination.href)}
  aria-label={`Enter ${destination.label}`}
  data-wall-window={destination.id}
  data-site-sound-silent
  data-astro-prefetch
  draggable="false"
  tabindex={keyboardAccessible ? undefined : -1}
  onfocus={() => keyboardAccessible && onFocus(destination)}
  style={`left: ${destination.x}px; --painting-position: ${destination.painting.objectPosition ?? '50% 50%'};`}
  onclick={(event) => onEnter(event, destination)}
>
  <span class="wall-window__recess" aria-hidden="true">
    <span class="wall-window__glass">
      <img
        class="wall-window__painting"
        src={withBase(destination.painting.src)}
        srcset={paintingSrcset}
        sizes="340px"
        alt=""
        width={destination.width}
        height={destination.height}
        draggable="false"
        decoding="async"
        loading="eager"
      />
    </span>
    <span class="wall-window__reflection"></span>
  </span>

  <span class="wall-window__sill" aria-hidden="true"></span>
  <span class="wall-window__label">
    <span class="wall-window__index">{indexLabel}</span>
    <span class="wall-window__name">{destination.label}</span>
    <span class="wall-window__arrow" aria-hidden="true">
      <svg viewBox="0 0 16 16" focusable="false">
        <path d="M4 12 12 4M6.25 4H12v5.75" />
      </svg>
    </span>
  </span>
</a>

<style>
  .wall-window {
    --room-light-hot: var(--wall-light, #f4f1e9);

    position: absolute;
    z-index: 3;
    top: calc((100% - var(--floor-height)) / 2 + 1.125rem);
    bottom: auto;
    display: block;
    box-sizing: border-box;
    width: var(--window-width);
    height: var(--window-height);
    margin-top: var(--window-offset-y);
    margin-left: var(--window-offset-x);
    color: color-mix(in srgb, var(--wall-light, #f4f1e9) 72%, transparent);
    outline: none;
    text-decoration: none;
    user-select: none;
    -webkit-user-drag: none;
  }

  .wall-window__recess {
    position: absolute;
    top: 0;
    left: 0;
    box-sizing: border-box;
    width: 100%;
    height: calc(100% - 2.25rem);
    overflow: hidden;
    contain: paint;
    border: 0.7rem solid #050505;
    background: #020202;
    box-shadow:
      0 0 0 1px color-mix(in srgb, var(--wall-light, #f4f1e9) 7%, transparent),
      0 0 0 0.32rem #0b0b0b,
      0.65rem 0.85rem 1.15rem rgb(0 0 0 / 66%),
      0 0 2.6rem color-mix(in srgb, var(--room-light-hot) 8%, transparent),
      inset 0 0 2.2rem rgb(0 0 0 / 88%);
    transition:
      box-shadow 320ms cubic-bezier(0.2, 0.75, 0.25, 1),
      border-color 320ms ease;
  }

  .wall-window__glass {
    position: absolute;
    inset: 0.3rem;
    box-sizing: border-box;
    overflow: hidden;
    contain: paint;
    background: #0b0b0a;
    box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--wall-light, #f4f1e9) 8%, transparent);
  }

  .wall-window__painting {
    position: relative;
    z-index: 1;
    display: block;
    width: 100%;
    height: 100%;
    max-width: 100%;
    max-height: 100%;
    object-fit: cover;
    object-position: var(--painting-position);
    transform: none;
    pointer-events: none;
    user-select: none;
    -webkit-user-drag: none;
  }

  .wall-window__glass::after {
    position: absolute;
    z-index: 2;
    inset: 0;
    background: rgb(0 0 0 / 14%);
    content: '';
    opacity: 1;
    pointer-events: none;
    transition: opacity 320ms cubic-bezier(0.2, 0.75, 0.25, 1);
  }

  .wall-window__reflection {
    position: absolute;
    z-index: 3;
    inset: 0.45rem;
    background:
      linear-gradient(112deg, transparent 12%, color-mix(in srgb, var(--wall-light, #f4f1e9) 6%, transparent) 27%, transparent 42%),
      linear-gradient(180deg, color-mix(in srgb, var(--wall-light, #f4f1e9) 2%, transparent), transparent 38%);
    pointer-events: none;
  }

  .wall-window__sill {
    position: absolute;
    right: -0.65rem;
    bottom: 2rem;
    left: -0.65rem;
    height: 0.55rem;
    background: #050505;
    border-top: 1px solid color-mix(in srgb, var(--wall-light, #f4f1e9) 7%, transparent);
    box-shadow: 0 0.5rem 0.65rem rgb(0 0 0 / 58%);
  }

  .wall-window__label {
    position: absolute;
    right: 0;
    bottom: 0;
    left: 0;
    display: grid;
    grid-template-columns: auto 1fr auto;
    align-items: center;
    gap: 0.7rem;
    color: color-mix(in srgb, var(--wall-light, #f4f1e9) 58%, transparent);
    font-family: var(--font-sans, system-ui, sans-serif);
    font-size: 0.7rem;
    font-weight: 400;
    letter-spacing: 0.16em;
    line-height: 1;
    text-transform: uppercase;
    transition: color 260ms ease;
  }

  .wall-window__index {
    color: color-mix(in srgb, var(--wall-light, #f4f1e9) 30%, transparent);
    font-variant-numeric: tabular-nums;
  }

  .wall-window__arrow {
    display: grid;
    width: 0.9rem;
    height: 0.9rem;
    place-items: center;
    opacity: 0;
    transform: translate(-0.2rem, 0.2rem);
    transition:
      opacity 260ms ease,
      transform 260ms ease;
  }

  .wall-window__arrow svg {
    display: block;
    width: 100%;
    height: 100%;
    overflow: visible;
    fill: none;
    stroke: currentColor;
    stroke-width: 1.35;
    stroke-linecap: round;
    stroke-linejoin: round;
  }

  .wall-window--entering {
    color: var(--wall-light, #f4f1e9);
  }

  .wall-window--entering .wall-window__recess {
    border-color: #080808;
    box-shadow:
      0 0 0 1px color-mix(in srgb, var(--wall-light, #f4f1e9) 11%, transparent),
      0 0 0 0.32rem #0d0d0d,
      0.65rem 0.85rem 1.15rem rgb(0 0 0 / 68%),
      0 0 2.8rem color-mix(in srgb, var(--room-light-hot) 32%, transparent),
      inset 0 0 1.5rem rgb(0 0 0 / 58%);
  }

  .wall-window--entering .wall-window__glass::after {
    opacity: 0;
  }

  .wall-window--entering .wall-window__label {
    color: color-mix(in srgb, var(--wall-light, #f4f1e9) 92%, transparent);
  }

  .wall-window--entering .wall-window__arrow {
    opacity: 1;
    transform: translate(0, 0);
  }

  @media (hover: hover) and (pointer: fine) {
    .wall-window:hover {
      color: var(--wall-light, #f4f1e9);
    }

    .wall-window:hover .wall-window__recess {
      border-color: #080808;
      box-shadow:
        0 0 0 1px color-mix(in srgb, var(--wall-light, #f4f1e9) 11%, transparent),
        0 0 0 0.32rem #0d0d0d,
        0.65rem 0.85rem 1.15rem rgb(0 0 0 / 68%),
        0 0 2.8rem color-mix(in srgb, var(--room-light-hot) 32%, transparent),
        inset 0 0 1.5rem rgb(0 0 0 / 58%);
    }

    .wall-window:hover .wall-window__glass::after {
      opacity: 0;
    }

    .wall-window:hover .wall-window__label {
      color: color-mix(in srgb, var(--wall-light, #f4f1e9) 92%, transparent);
    }

    .wall-window:hover .wall-window__arrow {
      opacity: 1;
      transform: translate(0, 0);
    }
  }

  .wall-window:focus-visible .wall-window__recess {
    outline: 2px solid color-mix(in srgb, var(--wall-light, #f4f1e9) 82%, transparent);
    outline-offset: 0.5rem;
  }

  @media (max-width: 40rem) {
    .wall-window__label {
      font-size: 0.76rem;
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .wall-window__recess,
    .wall-window__glass::after,
    .wall-window__label,
    .wall-window__arrow {
      transition: none;
    }
  }
</style>
