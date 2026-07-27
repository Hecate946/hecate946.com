<script lang="ts">
  import type { HouseDestination } from '@/config/house-scene';

  export let destination: HouseDestination;
  export let navigationEnabled = true;

  $: geometry = destination.geometry;
  $: isRound = geometry.kind === 'round';
  $: isHalfdome = geometry.kind === 'halfdome';
  $: inset = isRound ? 14 : isHalfdome ? 16 : 13;
  $: outerHalfdomePath = `M0 ${geometry.height}A${geometry.width / 2} ${geometry.height} 0 0 1 ${geometry.width} ${geometry.height}L0 ${geometry.height}Z`;
  $: innerHalfdomePath = `M${inset} ${geometry.height - inset}A${(geometry.width - inset * 2) / 2} ${geometry.height - inset * 1.5} 0 0 1 ${geometry.width - inset} ${geometry.height - inset}L${inset} ${geometry.height - inset}Z`;
  $: halfdomeMullions = [0.2, 0.4, 0.6, 0.8].map(
    (ratio) =>
      `M${geometry.width * ratio} ${geometry.height - inset}V${
        geometry.height -
        Math.sqrt(
          Math.max(
            0,
            (1 - Math.pow((geometry.width * ratio - geometry.width / 2) / (geometry.width / 2 - inset), 2)) *
              Math.pow(geometry.height - inset * 1.5, 2),
          ),
        )
      }`,
  );

  function handleClick(event: MouseEvent) {
    if (!navigationEnabled) event.preventDefault();
  }
</script>

<a
  class:house-window--round={isRound}
  class:house-window--halfdome={isHalfdome}
  class="house-window"
  href={destination.href}
  aria-label={`Open ${destination.label}: ${destination.description}`}
  aria-disabled={!navigationEnabled}
  data-house-window={destination.id}
  onclick={handleClick}
>
  <g transform={`translate(${geometry.x} ${geometry.y})`}>
    <defs>
      {#if isRound}
        <clipPath id={`house-window-clip-${destination.id}`}>
          <circle cx={geometry.width / 2} cy={geometry.height / 2} r={geometry.width / 2 - inset} />
        </clipPath>
      {:else if isHalfdome}
        <clipPath id={`house-window-clip-${destination.id}`}>
          <path d={innerHalfdomePath} />
        </clipPath>
      {:else}
        <clipPath id={`house-window-clip-${destination.id}`}>
          <rect x={inset} y={inset} width={geometry.width - inset * 2} height={geometry.height - inset * 2} />
        </clipPath>
      {/if}
    </defs>

    {#if isRound}
      <circle class="house-window__shadow" cx={geometry.width / 2 + 4} cy={geometry.height / 2 + 7} r={geometry.width / 2 + 10} />
      <circle class="house-window__frame" cx={geometry.width / 2} cy={geometry.height / 2} r={geometry.width / 2 + 10} />
      <circle class="house-window__inner-frame" cx={geometry.width / 2} cy={geometry.height / 2} r={geometry.width / 2 - 2} />
      <circle class="house-window__glass" cx={geometry.width / 2} cy={geometry.height / 2} r={geometry.width / 2 - inset} />
      <path class="house-window__mullion" d={`M${geometry.width / 2} ${inset}V${geometry.height - inset}M${inset} ${geometry.height / 2}H${geometry.width - inset}`} />
      <path class="house-window__shine" d={`M${geometry.width * 0.28} ${geometry.height * 0.31}l${geometry.width * 0.2} -${geometry.height * 0.08}`} />
      <circle class="house-window__hit" cx={geometry.width / 2} cy={geometry.height / 2} r={geometry.width / 2 + 14} />
    {:else if isHalfdome}
      <path class="house-window__shadow" d={outerHalfdomePath} transform="translate(4 7)" />
      <path class="house-window__frame" d={outerHalfdomePath} />
      <path class="house-window__inner-frame" d={`M8 ${geometry.height - 8}A${geometry.width / 2 - 8} ${geometry.height - 8} 0 0 1 ${geometry.width - 8} ${geometry.height - 8}L8 ${geometry.height - 8}Z`} />
      <path class="house-window__glass" d={innerHalfdomePath} />
      <g class="house-window__mullions" clip-path={`url(#house-window-clip-${destination.id})`}>
        {#each halfdomeMullions as mullion}
          <path class="house-window__mullion" d={mullion} />
        {/each}
        <path class="house-window__mullion" d={`M${inset} ${geometry.height * 0.67}H${geometry.width - inset}`} />
      </g>
      <path class="house-window__shine" d={`M${geometry.width * 0.18} ${geometry.height * 0.53}l${geometry.width * 0.18} -${geometry.height * 0.13}`} />
      <path class="house-window__sill" d={`M-10 ${geometry.height - 3}h${geometry.width + 20}v14H-10z`} />
      <path class="house-window__hit" d={outerHalfdomePath} />
    {:else}
      <rect class="house-window__shadow" x="4" y="7" width={geometry.width + 18} height={geometry.height + 18} rx="2" />
      <rect class="house-window__frame" x="-9" y="-9" width={geometry.width + 18} height={geometry.height + 18} rx="2" />
      <rect class="house-window__inner-frame" width={geometry.width} height={geometry.height} rx="1" />
      <rect class="house-window__glass" x={inset} y={inset} width={geometry.width - inset * 2} height={geometry.height - inset * 2} />
      <path class="house-window__mullion" d={`M${geometry.width / 2} ${inset}V${geometry.height - inset}M${inset} ${geometry.height / 2}H${geometry.width - inset}`} />
      <path class="house-window__shine" d={`M${geometry.width * 0.2} ${geometry.height * 0.24}l${geometry.width * 0.25} -${geometry.height * 0.08}`} />
      <path class="house-window__sill" d={`M-15 ${geometry.height + 6}h${geometry.width + 30}v12H-15z`} />
      <rect class="house-window__hit" x="-13" y="-13" width={geometry.width + 26} height={geometry.height + 34} />
    {/if}

    <g class="house-window__label" transform={`translate(${geometry.width / 2} ${geometry.height + (isHalfdome ? 36 : 43)})`}>
      <rect x="-76" y="-17" width="152" height="34" rx="17" />
      <text text-anchor="middle" dominant-baseline="central">{destination.label}</text>
    </g>
  </g>
</a>
