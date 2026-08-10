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
  let editInput: HTMLInputElement | null = null;

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
    editing = channel;
    draft = channel === 'music' ? music : sfx;
    requestAnimationFrame(() => {
      editInput?.focus();
      editInput?.select();
    });
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
      <svg viewBox="0 0 24 24">
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
      >×</button>
    </div>

    <div class="audio-channel" data-channel="music">
      <div class="audio-channel-heading">
        <label for="site-music-volume" class="ui-text">Music</label>
        {#if editing === 'music'}
          <span class="audio-percent-editor">
            <input
              bind:this={editInput}
              type="number"
              min="0"
              max="100"
              step="1"
              inputmode="numeric"
              aria-label="Music volume percentage"
              bind:value={draft}
              onkeydown={handleNumberKey}
              onblur={commitEditing}
            />
            <span aria-hidden="true">%</span>
          </span>
        {:else}
          <button
            class="audio-percent"
            type="button"
            aria-label={`Set music volume. Current volume ${music}%`}
            onclick={() => startEditing('music')}
          >{music}%</button>
        {/if}
      </div>
      <input
        id="site-music-volume"
        class="audio-slider"
        type="range"
        min="0"
        max="100"
        step="1"
        value={music}
        style={`--audio-level: ${music}%`}
        aria-valuetext={`${music}%`}
        oninput={(event) => handleRangeInput('music', event)}
        onchange={(event) => handleRangeCommit('music', event)}
      />
      {#if musicAvailable === false}
        <p class="audio-channel-note">Music file unavailable</p>
      {/if}
    </div>

    <div class="audio-channel" data-channel="sfx">
      <div class="audio-channel-heading">
        <label for="site-sfx-volume" class="ui-text">SFX</label>
        {#if editing === 'sfx'}
          <span class="audio-percent-editor">
            <input
              bind:this={editInput}
              type="number"
              min="0"
              max="100"
              step="1"
              inputmode="numeric"
              aria-label="Sound effects volume percentage"
              bind:value={draft}
              onkeydown={handleNumberKey}
              onblur={commitEditing}
            />
            <span aria-hidden="true">%</span>
          </span>
        {:else}
          <button
            class="audio-percent"
            type="button"
            aria-label={`Set sound effects volume. Current volume ${sfx}%`}
            onclick={() => startEditing('sfx')}
          >{sfx}%</button>
        {/if}
      </div>
      <input
        id="site-sfx-volume"
        class="audio-slider"
        type="range"
        min="0"
        max="100"
        step="1"
        value={sfx}
        style={`--audio-level: ${sfx}%`}
        aria-valuetext={`${sfx}%`}
        oninput={(event) => handleRangeInput('sfx', event)}
        onchange={(event) => handleRangeCommit('sfx', event)}
      />
    </div>
  </div>
</div>
