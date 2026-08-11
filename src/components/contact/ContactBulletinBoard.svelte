<script lang="ts">
  import { onMount } from 'svelte';

  type LinkItem = {
    id: string;
    label: string;
    href: string;
    rel?: string;
    target?: string;
    variant: string;
  };

  type Placement = {
    x: number;
    y: number;
    rotate: number;
    z: number;
  };

  const links: LinkItem[] = [
    { id: 'gmail', label: 'Email', href: 'mailto:cyrusasasi@gmail.com', variant: 'gmail' },
    { id: 'github', label: 'GitHub', href: 'https://github.com/Hecate946/', variant: 'github', target: '_blank', rel: 'me noopener noreferrer' },
    { id: 'linkedin', label: 'LinkedIn', href: 'https://www.linkedin.com/in/cyrus-asasi/', variant: 'linkedin', target: '_blank', rel: 'me noopener noreferrer' },
    { id: 'coffee', label: 'Buy Me a Coffee', href: 'https://buymeacoffee.com/hecate946', variant: 'coffee', target: '_blank', rel: 'noopener noreferrer' },
    { id: 'chess', label: 'Chess.com', href: 'https://www.chess.com/member/Cyrus2020SD/stats?time=0', variant: 'chess', target: '_blank', rel: 'noopener noreferrer' },
    { id: 'spotify', label: 'Spotify', href: 'https://open.spotify.com/user/hecate946', variant: 'spotify', target: '_blank', rel: 'noopener noreferrer' },
  ];

  let placements: Record<string, Placement> = {};
  let boardElement: HTMLDivElement | null = null;
  let resizeObserver: ResizeObserver | null = null;

  function clamp(value: number, min: number, max: number) {
    return Math.min(max, Math.max(min, value));
  }

  function randomInRange(min: number, max: number) {
    return min + Math.random() * (max - min);
  }

  function randomize() {
    if (!boardElement) return;

    const rect = boardElement.getBoundingClientRect();
    const boardSize = Math.min(rect.width, rect.height);
    const tileSize = clamp(boardSize * 0.115, 54, 74);
    const half = tileSize / 2;
    const padX = clamp(rect.width * 0.085, 52, 88) + half;
    const padY = clamp(rect.height * 0.11, 46, 92) + half;
    const minDistance = tileSize * 1.75;

    const placed: Placement[] = [];
    const next: Record<string, Placement> = {};

    links.forEach((link, index) => {
      let x = rect.width / 2;
      let y = rect.height / 2;
      let success = false;

      for (let attempt = 0; attempt < 500; attempt += 1) {
        const candidateX = randomInRange(padX, rect.width - padX);
        const candidateY = randomInRange(padY, rect.height - padY);
        const separated = placed.every((other) => {
          const dx = candidateX - other.x;
          const dy = candidateY - other.y;
          return Math.hypot(dx, dy) >= minDistance;
        });

        if (separated) {
          x = candidateX;
          y = candidateY;
          success = true;
          break;
        }
      }

      if (!success) {
        x = randomInRange(padX, rect.width - padX);
        y = randomInRange(padY, rect.height - padY);
      }

      const placement: Placement = {
        x,
        y,
        rotate: randomInRange(-10, 10),
        z: 2 + index,
      };

      placed.push(placement);
      next[link.id] = placement;
    });

    placements = next;
  }

  onMount(() => {
    randomize();
    if (boardElement) {
      resizeObserver = new ResizeObserver(() => randomize());
      resizeObserver.observe(boardElement);
    }

    return () => {
      resizeObserver?.disconnect();
    };
  });
</script>

<div class="contact-board-wrap">
  <div class="contact-board-shadow" aria-hidden="true"></div>
  <div class="contact-board-frame">
    <div bind:this={boardElement} class="contact-board" aria-label="Contact links blackboard">
      <div class="contact-board__surface" aria-hidden="true"></div>
      <div class="contact-board__chalk-tray" aria-hidden="true">
        <span class="chalk chalk--white"></span>
        <span class="chalk chalk--green"></span>
        <span class="chalk chalk--blue"></span>
      </div>

      {#each links as link}
        {@const p = placements[link.id]}
        <a
          class={`board-link board-link--${link.variant}`}
          href={link.href}
          target={link.target}
          rel={link.rel}
          aria-label={link.label}
          style={p ? `left:${p.x}px; top:${p.y}px; --board-rotate:${p.rotate}deg; z-index:${p.z};` : ''}
        >
          <span class="board-link__icon" aria-hidden="true">
            {#if link.variant === 'gmail'}
              <svg viewBox="0 0 64 64" width="40" height="40" fill="none">
                <rect x="10" y="16" width="44" height="32" rx="5" stroke="currentColor" stroke-width="3.5"/>
                <path d="M12 19l20 16 20-16" stroke="currentColor" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"/>
                <path d="M12 45l14-14" stroke="currentColor" stroke-width="3" stroke-linecap="round"/>
                <path d="M52 45L38 31" stroke="currentColor" stroke-width="3" stroke-linecap="round"/>
              </svg>
            {:else if link.variant === 'github'}
              <svg viewBox="0 0 24 24" width="40" height="40"><path fill="currentColor" d="M12 2.8a9.4 9.4 0 0 0-2.97 18.32c.47.09.64-.2.64-.45v-1.66c-2.62.57-3.17-1.11-3.17-1.11-.43-1.09-1.05-1.38-1.05-1.38-.86-.59.06-.58.06-.58.95.07 1.45.98 1.45.98.84 1.44 2.21 1.02 2.75.78.09-.61.33-1.03.6-1.27-2.09-.24-4.29-1.05-4.29-4.66 0-1.03.37-1.87.97-2.53-.1-.24-.42-1.2.09-2.5 0 0 .79-.25 2.58.97A8.95 8.95 0 0 1 12 7.4c.8 0 1.6.11 2.35.32 1.79-1.22 2.57-.97 2.57-.97.52 1.3.2 2.26.1 2.5.6.66.97 1.5.97 2.53 0 3.62-2.21 4.42-4.31 4.66.34.29.64.87.64 1.75v2.59c0 .25.17.55.65.45A9.4 9.4 0 0 0 12 2.8Z"/></svg>
            {:else if link.variant === 'linkedin'}
              <svg viewBox="0 0 24 24" width="40" height="40"><path fill="currentColor" d="M6.3 8.1A1.8 1.8 0 1 1 6.3 4.5a1.8 1.8 0 0 1 0 3.6ZM4.75 9.55h3.1V19.5h-3.1V9.55Zm4.95 0h2.97v1.36h.04c.41-.78 1.43-1.61 2.94-1.61 3.14 0 3.72 2.07 3.72 4.76v5.44h-3.1v-4.82c0-1.15-.02-2.63-1.61-2.63-1.61 0-1.86 1.26-1.86 2.55v4.9H9.7V9.55Z"/></svg>
            {:else if link.variant === 'coffee'}
              <svg viewBox="0 0 64 64" width="40" height="40" fill="none">
                <path d="M20 22h18c6 0 10 4 10 10 0 6-4 10-10 10h-2" stroke="currentColor" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>
                <path d="M16 18h18c3.5 0 6 2.6 6 6v18c0 6.5-5.5 12-12 12h-6c-6.5 0-12-5.5-12-12V24c0-3.4 2.6-6 6-6Z" stroke="currentColor" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>
                <path d="M16 18c0-5 5-8 16-8s16 3 16 8" stroke="currentColor" stroke-width="4" stroke-linecap="round"/>
              </svg>
            {:else if link.variant === 'chess'}
              <svg viewBox="0 0 64 64" width="40" height="40" fill="none">
                <path d="M24 18a8 8 0 1 1 16 0c0 3.2-1.8 5.7-4.5 7 3.8 1.8 6.5 5.3 6.5 10v2H22v-2c0-4.7 2.7-8.2 6.5-10C25.8 23.7 24 21.2 24 18Z" stroke="currentColor" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"/>
                <path d="M20 46h24" stroke="currentColor" stroke-width="4" stroke-linecap="round"/>
                <path d="M16 53h32" stroke="currentColor" stroke-width="4" stroke-linecap="round"/>
              </svg>
            {:else if link.variant === 'spotify'}
              <svg viewBox="0 0 64 64" width="40" height="40" fill="none">
                <circle cx="32" cy="32" r="23" stroke="currentColor" stroke-width="3.5"/>
                <path d="M22 27.5c8-2.3 17-1.6 24.4 2.1" stroke="currentColor" stroke-width="3.8" stroke-linecap="round"/>
                <path d="M24.6 35c6.3-1.6 13.1-1.1 19 1.8" stroke="currentColor" stroke-width="3.4" stroke-linecap="round"/>
                <path d="M27.2 41.9c4.8-1 9.5-.5 13.8 1.4" stroke="currentColor" stroke-width="3" stroke-linecap="round"/>
              </svg>
            {/if}
          </span>
          <span class="board-link__label">{link.label}</span>
        </a>
      {/each}
    </div>
  </div>
</div>
