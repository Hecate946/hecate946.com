<script lang="ts">
  import { Canvas } from '@threlte/core';
  import CheckerboardScene from './CheckerboardScene.svelte';

  let shell: HTMLDivElement;
  let ready = false;
  let fullscreen = false;
  let resetSignal = 0;

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
      // Fullscreen is optional; the room remains usable without it.
    }
  }

  function updateFullscreenState() {
    fullscreen = document.fullscreenElement === shell;
  }
</script>

<svelte:window onfullscreenchange={updateFullscreenState} />

<div
  class:ready
  class="room-shell"
  bind:this={shell}
  aria-label="Interactive three-dimensional checkerboard room"
>
  <div class="room-canvas" aria-hidden={!ready}>
    <Canvas shadows dpr={1.5}>
      <CheckerboardScene onReady={markReady} {resetSignal} />
    </Canvas>
  </div>

  <div class="room-vignette" aria-hidden="true"></div>

  <div class="room-topbar">
    <a class="room-exit" href="/projects/">← Back to projects</a>

    <div class="room-actions">
      <button class="room-control" type="button" onclick={resetView}>
        Reset view
      </button>
      <button class="room-control" type="button" onclick={toggleFullscreen}>
        {fullscreen ? 'Exit fullscreen' : 'Fullscreen'}
      </button>
    </div>
  </div>

  <div class="room-caption">
    <p class="room-kicker">Room 001</p>
    <h1>The Checkerboard Room</h1>
    <p>Drag to look around. Your viewpoint stays fixed inside the room.</p>
  </div>

  <div
    class="room-loader"
    role="status"
    aria-live="polite"
    aria-hidden={ready}
  >
    <span class="room-loader-mark" aria-hidden="true"></span>
    <span>{ready ? 'Room ready' : 'Loading the room…'}</span>
  </div>

  <noscript>
    <p class="room-noscript">JavaScript is required to enter this room.</p>
  </noscript>
</div>

<style>
  .room-shell {
    position: relative;
    isolation: isolate;
    width: 100%;
    min-height: clamp(38rem, calc(100svh - var(--header-height)), 68rem);
    overflow: hidden;
    background:
      radial-gradient(circle at 50% 38%, rgb(64 45 21 / 28%), transparent 28%),
      radial-gradient(circle at 50% 58%, rgb(8 46 27 / 52%), transparent 58%),
      #010503;
    color: #eef7ef;
  }

  .room-shell:fullscreen {
    width: 100vw;
    height: 100vh;
    min-height: 100vh;
  }

  .room-canvas,
  .room-canvas :global(canvas) {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
  }

  .room-canvas {
    opacity: 0;
    transition: opacity 700ms ease;
  }

  .ready .room-canvas {
    opacity: 1;
  }

  .room-canvas :global(canvas) {
    display: block;
    cursor: grab;
    outline: none;
    touch-action: none;
  }

  .room-canvas :global(canvas.is-looking) {
    cursor: grabbing;
  }

  .room-canvas :global(canvas:focus-visible) {
    box-shadow: inset 0 0 0 2px rgb(255 222 174 / 72%);
  }

  .room-vignette {
    position: absolute;
    z-index: 2;
    inset: 0;
    background:
      linear-gradient(180deg, rgb(0 0 0 / 42%), transparent 27%, transparent 68%, rgb(0 0 0 / 68%)),
      radial-gradient(circle at center, transparent 45%, rgb(0 0 0 / 62%) 118%);
    pointer-events: none;
  }

  .room-topbar {
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

  .room-actions {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    pointer-events: auto;
  }

  .room-exit,
  .room-control {
    display: inline-flex;
    min-height: 2.55rem;
    align-items: center;
    justify-content: center;
    padding: 0.55rem 0.9rem;
    background: rgb(2 10 6 / 72%);
    border: 1px solid rgb(255 225 184 / 18%);
    border-radius: 999px;
    box-shadow: 0 0.75rem 2.2rem rgb(0 0 0 / 24%);
    color: #f2f7f1;
    font: inherit;
    font-size: 0.78rem;
    letter-spacing: 0.035em;
    text-decoration: none;
    backdrop-filter: blur(0.8rem);
    pointer-events: auto;
  }

  .room-exit:hover,
  .room-control:hover {
    background: rgb(61 39 19 / 76%);
    border-color: rgb(255 220 167 / 42%);
    color: #fff;
  }

  .room-control {
    cursor: pointer;
  }

  .room-caption {
    position: absolute;
    z-index: 3;
    right: clamp(1rem, 4vw, 3rem);
    bottom: clamp(1.2rem, 4vw, 3rem);
    left: clamp(1rem, 4vw, 3rem);
    max-width: 36rem;
    pointer-events: none;
    text-shadow: 0 0.18rem 1.1rem rgb(0 0 0 / 88%);
  }

  .room-caption h1,
  .room-caption p {
    margin: 0;
  }

  .room-caption h1 {
    margin-block: 0.2rem 0.45rem;
    font-family: var(--font-display);
    font-size: clamp(2.2rem, 6vw, 5.4rem);
    font-weight: 400;
    letter-spacing: -0.045em;
    line-height: 0.94;
    text-wrap: balance;
  }

  .room-caption > p:last-child {
    color: rgb(242 239 224 / 78%);
    font-size: clamp(0.82rem, 1.6vw, 1rem);
  }

  .room-kicker {
    color: #efbd77;
    font-family: var(--font-mono);
    font-size: 0.7rem;
    letter-spacing: 0.16em;
    text-transform: uppercase;
  }

  .room-loader {
    position: absolute;
    z-index: 5;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.75rem;
    background: #010503;
    color: rgb(235 231 214 / 74%);
    font-family: var(--font-mono);
    font-size: 0.75rem;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    transition:
      opacity 420ms ease,
      visibility 420ms ease;
  }

  .ready .room-loader {
    visibility: hidden;
    opacity: 0;
  }

  .room-loader-mark {
    width: 0.7rem;
    aspect-ratio: 1;
    border: 1px solid #edb96f;
    transform: rotate(45deg);
    animation: room-pulse 1.1s ease-in-out infinite alternate;
  }

  .room-noscript {
    position: absolute;
    z-index: 10;
    inset: auto 1rem 1rem;
    margin: 0;
    padding: 0.8rem 1rem;
    background: #07150d;
    border: 1px solid rgb(255 255 255 / 18%);
  }

  @keyframes room-pulse {
    to {
      background: #edb96f;
      box-shadow: 0 0 1.25rem rgb(237 185 111 / 62%);
      transform: rotate(135deg) scale(1.16);
    }
  }

  @media (max-width: 620px) {
    .room-topbar {
      align-items: flex-start;
    }

    .room-actions {
      flex-direction: column;
      align-items: stretch;
    }

    .room-exit,
    .room-control {
      min-height: 2.35rem;
      padding-inline: 0.75rem;
      font-size: 0.7rem;
    }

    .room-caption {
      bottom: 1.25rem;
      max-width: calc(100% - 2rem);
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .room-canvas,
    .room-loader {
      transition: none;
    }

    .room-loader-mark {
      animation: none;
    }
  }
</style>
