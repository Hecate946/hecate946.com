<script lang="ts">
  import { onMount } from 'svelte';
  import {
    getSiteAudioState,
    setMusicVolume,
    setSfxVolume,
    subscribeSiteAudio,
    type SiteAudioState,
  } from '@/lib/site-audio';

  type Channel = 'music' | 'sfx';

  let root!: HTMLDivElement;
  let open = false;
  let music = 0;
  let sfx = 0;
  let musicAvailable: boolean | null = null;
  let editing: Channel | null = null;
  let draft: number | undefined = 0;
  let musicEditInput: HTMLInputElement | null = null;
  let sfxEditInput: HTMLInputElement | null = null;

  const clampPercent = (value: number) => {
    if (!Number.isFinite(value)) return 0;
    return Math.min(100, Math.max(0, Math.round(value)));
  };

  const applyState = (state: SiteAudioState) => {
    music = state.music;
    sfx = state.sfx;
    musicAvailable = state.musicAvailable;
  };

  onMount(() => {
    applyState(getSiteAudioState());
    const unsubscribe = subscribeSiteAudio(applyState);

    const handleOutside = (event: PointerEvent) => {
      if (!open || !(event.target instanceof Node) || root.contains(event.target)) return;
      closePanel();
    };

    const handleKey = (event: KeyboardEvent) => {
      if (event.key !== 'Escape') return;
      if (editing) {
        cancelEditing();
        return;
      }
      if (open) closePanel();
    };

    document.addEventListener('pointerdown', handleOutside, true);
    document.addEventListener('keydown', handleKey, true);

    return () => {
      unsubscribe();
      document.removeEventListener('pointerdown', handleOutside, true);
      document.removeEventListener('keydown', handleKey, true);
    };
  });

  function togglePanel() {
    if (open) closePanel();
    else open = true;
  }

  function closePanel() {
    if (editing) commitEditing();
    open = false;
  }

  function setChannel(channel: Channel, value: number, persist = true) {
    const next = clampPercent(value);
    if (channel === 'music') setMusicVolume(next, persist);
    else setSfxVolume(next, persist);
  }

  function handleRangeInput(channel: Channel, event: Event) {
    const input = event.currentTarget as HTMLInputElement;
    setChannel(channel, Number(input.value), false);
  }

  function handleRangeCommit(channel: Channel, event: Event) {
    const input = event.currentTarget as HTMLInputElement;
    setChannel(channel, Number(input.value), true);
  }

  function startEditing(channel: Channel) {
    draft = channel === 'music' ? music : sfx;
    editing = channel;

    // Both editors stay mounted (but visually clipped while inactive). Focusing
    // synchronously inside the tap/click gesture is important on iOS/Android:
    // deferring focus until the next frame can prevent the virtual keyboard
    // from opening even though the field becomes visible.
    const input = channel === 'music' ? musicEditInput : sfxEditInput;
    input?.focus({ preventScroll: true });
    input?.select();
  }

  function commitEditing() {
    if (!editing) return;
    const parsed = Number(draft);
    const value = Number.isFinite(parsed)
      ? clampPercent(parsed)
      : editing === 'music'
        ? music
        : sfx;
    setChannel(editing, value, true);
    editing = null;
    draft = 0;
  }

  function cancelEditing() {
    editing = null;
    draft = 0;
  }

  function handleNumberKey(event: KeyboardEvent) {
    if (event.key === 'Enter') {
      event.preventDefault();
      commitEditing();
    }
  }
</script>

<div class="audio-settings" bind:this={root} data-open={open}>
  <button
    type="button"
    class="header-action audio-action"
    aria-label="Audio settings"
    aria-expanded={open}
    aria-controls="site-audio-panel"
    title="Audio settings"
    onclick={togglePanel}
  >
    <span class="header-action-icon audio-icon" aria-hidden="true">
      <svg viewBox="0 0 24 24" width="24" height="24" aria-hidden="true" focusable="false">
        <path class="audio-speaker" d="M4 9.5v5h3.5L12 18V6L7.5 9.5H4Z" />
        <path class="audio-wave" d="M15.25 9.1a4 4 0 0 1 0 5.8" />
        <path class="audio-wave" d="M17.75 6.75a7.25 7.25 0 0 1 0 10.5" />
        <path class="audio-muted" d="m15.2 9.2 5.6 5.6m0-5.6-5.6 5.6" />
      </svg>
    </span>
  </button>

  <div
    id="site-audio-panel"
    class="audio-panel"
    role="dialog"
    aria-label="Audio settings"
    aria-hidden={!open}
  >
    <div class="audio-panel-heading">
      <span class="ui-text">Audio</span>
      <button
        class="audio-panel-close"
        type="button"
        aria-label="Close audio settings"
        onclick={closePanel}
      >
        <svg viewBox="0 0 10 10" aria-hidden="true" focusable="false" width="10" height="10">
          <path d="M1.5 1.5 8.5 8.5M8.5 1.5 1.5 8.5" />
        </svg>
      </button>
    </div>

    <div class="audio-channels">
      <div class="audio-channel" data-channel="music">
        <div class="audio-channel-heading">
          <label for="site-music-volume" class="ui-text">Music</label>
          <div class="audio-percent-control">
            <button
              class="audio-percent"
              class:audio-percent-hidden={editing === 'music'}
              type="button"
              aria-label={`Set music volume. Current volume ${music}%`}
              aria-hidden={editing === 'music'}
              tabindex={editing === 'music' ? -1 : 0}
              onclick={() => startEditing('music')}
            >{music}%</button>
            <span
              class="audio-percent-editor"
              class:audio-percent-editor-active={editing === 'music'}
              aria-hidden={editing !== 'music'}
            >
              <input
                bind:this={musicEditInput}
                type="number"
                min="0"
                max="100"
                step="1"
                inputmode="numeric"
                pattern="[0-9]*"
                enterkeyhint="done"
                aria-label="Music volume percentage"
                tabindex={editing === 'music' ? 0 : -1}
                bind:value={draft}
                onkeydown={handleNumberKey}
                onblur={() => editing === 'music' && commitEditing()}
              />
              <span aria-hidden="true">%</span>
            </span>
          </div>
        </div>

        <div class="audio-slider-well">
          <input
            id="site-music-volume"
            class="audio-slider"
            type="range"
            min="0"
            max="100"
            step="1"
            value={music}
            style={`--audio-level: ${music}%`}
            aria-label="Music volume"
            aria-valuetext={`${music}%`}
            oninput={(event) => handleRangeInput('music', event)}
            onchange={(event) => handleRangeCommit('music', event)}
          />
        </div>

        {#if musicAvailable === false}
          <p class="audio-channel-note">Unavailable</p>
        {/if}
      </div>

      <div class="audio-channel" data-channel="sfx">
        <div class="audio-channel-heading">
          <label for="site-sfx-volume" class="ui-text">SFX</label>
          <div class="audio-percent-control">
            <button
              class="audio-percent"
              class:audio-percent-hidden={editing === 'sfx'}
              type="button"
              aria-label={`Set sound effects volume. Current volume ${sfx}%`}
              aria-hidden={editing === 'sfx'}
              tabindex={editing === 'sfx' ? -1 : 0}
              onclick={() => startEditing('sfx')}
            >{sfx}%</button>
            <span
              class="audio-percent-editor"
              class:audio-percent-editor-active={editing === 'sfx'}
              aria-hidden={editing !== 'sfx'}
            >
              <input
                bind:this={sfxEditInput}
                type="number"
                min="0"
                max="100"
                step="1"
                inputmode="numeric"
                pattern="[0-9]*"
                enterkeyhint="done"
                aria-label="Sound effects volume percentage"
                tabindex={editing === 'sfx' ? 0 : -1}
                bind:value={draft}
                onkeydown={handleNumberKey}
                onblur={() => editing === 'sfx' && commitEditing()}
              />
              <span aria-hidden="true">%</span>
            </span>
          </div>
        </div>

        <div class="audio-slider-well">
          <input
            id="site-sfx-volume"
            class="audio-slider"
            type="range"
            min="0"
            max="100"
            step="1"
            value={sfx}
            style={`--audio-level: ${sfx}%`}
            aria-label="Sound effects volume"
            aria-valuetext={`${sfx}%`}
            oninput={(event) => handleRangeInput('sfx', event)}
            onchange={(event) => handleRangeCommit('sfx', event)}
          />
        </div>
      </div>
    </div>
  </div>
</div>
