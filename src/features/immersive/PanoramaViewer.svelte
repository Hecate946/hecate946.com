<script lang="ts">
  import { Canvas } from '@threlte/core';
  import { AgXToneMapping, PCFSoftShadowMap, SRGBColorSpace } from 'three';
  import type { ImmersiveSpace } from './catalog';
  import { withBase } from '@/lib/paths';
  import PanoramaScene from './PanoramaScene.svelte';

  export let space: ImmersiveSpace;

  let shell: HTMLDivElement;
  let ready = false;
  let fullscreen = false;
  let resetSignal = 0;
  let indexHref = withBase('/');
  $: indexHref = withBase(space.kind === 'room' ? '/rooms/' : '/halls/');

  function markReady() {
    ready = true;
  }

  function resetView() {
    resetSignal += 1;
  }

  async function toggleFullscreen() {
    try {
      if (document.fullscreenElement) {
        await document.exitFullscreen();
      } else {
        await shell.requestFullscreen();
      }
    } catch {
      // Fullscreen is optional; the scene remains usable without it.
    }
  }

  function updateFullscreenState() {
    fullscreen = document.fullscreenElement === shell;
  }
</script>

<svelte:window onfullscreenchange={updateFullscreenState} />

<div
  class:ready
  class="immersive-shell"
  bind:this={shell}
  aria-label={`Interactive Cycles-rendered ${space.title}`}
  style={`--space-accent: ${space.accent}`}
>
  <div class="immersive-canvas" aria-hidden={!ready}>
    <Canvas
      shadows={PCFSoftShadowMap}
      toneMapping={AgXToneMapping}
      colorSpace={SRGBColorSpace}
      dpr={[1, 1.5]}
    >
      <PanoramaScene {space} onReady={markReady} {resetSignal} />
    </Canvas>
  </div>

  <div class="immersive-topbar">
    <a class="immersive-exit" href={indexHref}>← Back to {space.kind === 'room' ? 'rooms' : 'halls'}</a>

    <div class="immersive-actions">
      <button class="immersive-control" type="button" onclick={resetView}>
        Reset view
      </button>
      <button class="immersive-control" type="button" onclick={toggleFullscreen}>
        {fullscreen ? 'Exit fullscreen' : 'Fullscreen'}
      </button>
    </div>
  </div>

  <div class="immersive-caption">
    <p class="immersive-kicker">{space.label}</p>
    <h1>{space.title}</h1>
    <p>
      Drag to look around. Scroll or pinch to zoom.{space.interactiveUrl
        ? ' Grab interactive objects.'
        : ''}
    </p>
  </div>

  <div
    class="immersive-loader"
    role="status"
    aria-live="polite"
    aria-hidden={ready}
  >
    <span class="immersive-loader-mark" aria-hidden="true"></span>
    <span>{ready ? 'Scene ready' : `Loading ${space.title.toLowerCase()}…`}</span>
  </div>

  <noscript>
    <p class="immersive-noscript">JavaScript is required to enter this scene.</p>
  </noscript>
</div>

<style>
  .immersive-shell {
    position: relative;
    isolation: isolate;
    width: 100%;
    min-height: clamp(38rem, calc(100svh - var(--header-height)), 68rem);
    overflow: hidden;
    background: #020202;
    color: #eef7ef;
  }

  .immersive-shell:fullscreen {
    width: 100vw;
    height: 100vh;
    min-height: 100vh;
  }

  .immersive-canvas,
  .immersive-canvas :global(canvas) {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
  }

  .immersive-canvas {
    opacity: 0;
    transition: opacity 700ms ease;
  }

  .ready .immersive-canvas {
    opacity: 1;
  }

  .immersive-canvas :global(canvas) {
    display: block;
    cursor: grab;
    outline: none;
    touch-action: none;
  }

  .immersive-canvas :global(canvas.is-looking),
  .immersive-canvas :global(canvas.is-grabbing-object) {
    cursor: grabbing;
  }

  .immersive-canvas :global(canvas:focus-visible) {
    box-shadow: inset 0 0 0 2px rgb(255 255 255 / 64%);
  }

  .immersive-topbar {
    position: absolute;
    z-index: 4;
    top: clamp(0.85rem, 2vw, 1.4rem);
    right: clamp(0.85rem, 2vw, 1.4rem);
    left: clamp(0.85rem, 2vw, 1.4rem);
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    pointer-events: none;
  }

  .immersive-actions {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    pointer-events: auto;
  }

  .immersive-exit,
  .immersive-control {
    display: inline-flex;
    min-height: 2.55rem;
    align-items: center;
    justify-content: center;
    padding: 0.55rem 0.9rem;
    background: rgb(0 0 0 / 68%);
    border: 1px solid color-mix(in srgb, var(--space-accent), white 34%);
    border-radius: 999px;
    box-shadow: 0 0.75rem 2.2rem rgb(0 0 0 / 24%);
    color: #f5f5f5;
    font: inherit;
    font-size: 0.78rem;
    letter-spacing: 0.035em;
    text-decoration: none;
    backdrop-filter: blur(0.8rem);
    pointer-events: auto;
  }

  .immersive-exit:hover,
  .immersive-control:hover {
    background: rgb(24 24 24 / 84%);
    border-color: color-mix(in srgb, var(--space-accent), white 62%);
    color: #fff;
  }

  .immersive-control {
    cursor: pointer;
  }

  .immersive-caption {
    position: absolute;
    z-index: 3;
    right: clamp(1rem, 4vw, 3rem);
    bottom: clamp(1.2rem, 4vw, 3rem);
    left: clamp(1rem, 4vw, 3rem);
    max-width: 36rem;
    pointer-events: none;
    text-shadow: 0 0.18rem 1.1rem rgb(0 0 0 / 88%);
  }

  .immersive-caption h1,
  .immersive-caption p {
    margin: 0;
  }

  .immersive-caption h1 {
    margin-block: 0.2rem 0.45rem;
    font-family: var(--font-display);
    font-size: clamp(2.2rem, 6vw, 5.4rem);
    font-weight: 400;
    letter-spacing: -0.045em;
    line-height: 0.94;
    text-wrap: balance;
  }

  .immersive-caption > p:last-child {
    color: rgb(255 255 255 / 76%);
    font-size: clamp(0.82rem, 1.6vw, 1rem);
  }

  .immersive-kicker {
    color: color-mix(in srgb, var(--space-accent), white 68%);
    font-family: var(--font-mono);
    font-size: 0.7rem;
    letter-spacing: 0.16em;
    text-transform: uppercase;
  }

  .immersive-loader {
    position: absolute;
    z-index: 5;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.75rem;
    background: #020202;
    color: rgb(255 255 255 / 72%);
    font-family: var(--font-mono);
    font-size: 0.75rem;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    transition:
      opacity 420ms ease,
      visibility 420ms ease;
  }

  .ready .immersive-loader {
    visibility: hidden;
    opacity: 0;
  }

  .immersive-loader-mark {
    width: 0.7rem;
    aspect-ratio: 1;
    border: 1px solid color-mix(in srgb, var(--space-accent), white 72%);
    transform: rotate(45deg);
    animation: immersive-pulse 1.1s ease-in-out infinite alternate;
  }

  .immersive-noscript {
    position: absolute;
    z-index: 10;
    inset: auto 1rem 1rem;
    margin: 0;
    padding: 0.8rem 1rem;
    background: #111;
    border: 1px solid rgb(255 255 255 / 18%);
  }

  @keyframes immersive-pulse {
    to {
      background: color-mix(in srgb, var(--space-accent), white 72%);
      box-shadow: 0 0 1.25rem color-mix(in srgb, var(--space-accent), transparent 56%);
      transform: rotate(135deg) scale(1.16);
    }
  }

  @media (max-width: 620px) {
    .immersive-topbar {
      align-items: flex-start;
    }

    .immersive-actions {
      flex-direction: column;
      align-items: stretch;
    }

    .immersive-exit,
    .immersive-control {
      min-height: 2.35rem;
      padding-inline: 0.75rem;
      font-size: 0.7rem;
    }

    .immersive-caption {
      bottom: 1.25rem;
      max-width: calc(100% - 2rem);
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .immersive-canvas,
    .immersive-loader {
      transition: none;
    }

    .immersive-loader-mark {
      animation: none;
    }
  }
</style>
