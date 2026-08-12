<script lang="ts">
  import { onMount } from 'svelte';
  import { withBase } from '../../lib/paths';

  type MagnetLink = {
    id: 'email' | 'github' | 'linkedin' | 'coffee' | 'chess' | 'spotify';
    label: string;
    href: string;
    imageSrc: string;
    target?: '_blank';
    rel?: string;
  };

  type MagnetState = MagnetLink & {
    x: number;
    y: number;
    dragging: boolean;
    pressed: boolean;
  };

  type DragState = {
    magnetId: MagnetState['id'];
    pointerId: number;
    offsetX: number;
    offsetY: number;
    startX: number;
    startY: number;
    moved: boolean;
  };

  const magnetLinks: MagnetLink[] = [
    {
      id: 'email',
      label: 'Email',
      href: 'mailto:cyrusasasi@gmail.com',
      imageSrc: '/images/contact/buttons/email.png',
    },
    {
      id: 'github',
      label: 'GitHub',
      href: 'https://github.com/Hecate946/',
      imageSrc: '/images/contact/buttons/github.png',
      target: '_blank',
      rel: 'me noopener noreferrer',
    },
    {
      id: 'linkedin',
      label: 'LinkedIn',
      href: 'https://www.linkedin.com/in/cyrus-asasi/',
      imageSrc: '/images/contact/buttons/linkedin.png',
      target: '_blank',
      rel: 'me noopener noreferrer',
    },
    {
      id: 'coffee',
      label: 'Buy Me a Coffee',
      href: 'https://buymeacoffee.com/hecate946',
      imageSrc: '/images/contact/buttons/coffee.png',
      target: '_blank',
      rel: 'noopener noreferrer',
    },
    {
      id: 'chess',
      label: 'Chess.com',
      href: 'https://www.chess.com/member/Cyrus2020SD/stats?time=0',
      imageSrc: '/images/contact/buttons/chess.png',
      target: '_blank',
      rel: 'noopener noreferrer',
    },
    {
      id: 'spotify',
      label: 'Spotify',
      href: 'https://open.spotify.com/user/hecate946',
      imageSrc: '/images/contact/buttons/spotify.png',
      target: '_blank',
      rel: 'noopener noreferrer',
    },
  ];

  let fridgeSurfaceEl: HTMLDivElement | null = null;
  let resizeObserver: ResizeObserver | null = null;
  let magnets: MagnetState[] = [];
  let magnetSize = 68;
  let activeDrag: DragState | null = null;

  // Magnets should feel stuck to a metal surface, not like loose pucks.
  // Lower values make the pointer feel more resisted/sticky while dragging.
  const dragResponse = 0.58;

  const clamp = (value: number, min: number, max: number) => Math.min(max, Math.max(min, value));
  const randomInRange = (min: number, max: number) => min + Math.random() * (max - min);

  function getSurfaceBounds() {
    if (!fridgeSurfaceEl) return { width: 0, height: 0 };
    const rect = fridgeSurfaceEl.getBoundingClientRect();
    return { width: rect.width, height: rect.height };
  }

  function updateMagnetSize() {
    const { width, height } = getSurfaceBounds();
    if (!width || !height) return;
    magnetSize = clamp(Math.min(width, height) * 0.16, 54, 72);
  }

  function createInitialMagnets() {
    updateMagnetSize();
    const { width, height } = getSurfaceBounds();
    if (!width || !height) return;

    const next: MagnetState[] = [];
    const gap = magnetSize * 0.12;

    for (const link of magnetLinks) {
      let x = 0;
      let y = 0;
      let placed = false;

      for (let attempt = 0; attempt < 1200; attempt += 1) {
        const candidateX = randomInRange(0, Math.max(0, width - magnetSize));
        const candidateY = randomInRange(0, Math.max(0, height - magnetSize));
        const separated = next.every((other) => !(
          candidateX < other.x + magnetSize + gap &&
          candidateX + magnetSize + gap > other.x &&
          candidateY < other.y + magnetSize + gap &&
          candidateY + magnetSize + gap > other.y
        ));

        if (separated) {
          x = candidateX;
          y = candidateY;
          placed = true;
          break;
        }
      }

      if (!placed) {
        const index = next.length;
        const cols = 2;
        x = (index % cols) * (magnetSize + gap);
        y = Math.floor(index / cols) * (magnetSize + gap);
      }

      next.push({ ...link, x, y, dragging: false, pressed: false });
    }

    magnets = next;
    resolveCollisions();
    magnets = [...magnets];
  }

  function openMagnet(magnet: MagnetState) {
    if (typeof window === 'undefined') return;
    if (magnet.target === '_blank') {
      window.open(magnet.href, '_blank', 'noopener,noreferrer');
      return;
    }
    window.location.href = magnet.href;
  }

  function keepInsideBounds(magnet: MagnetState) {
    const { width, height } = getSurfaceBounds();
    magnet.x = clamp(magnet.x, 0, Math.max(0, width - magnetSize));
    magnet.y = clamp(magnet.y, 0, Math.max(0, height - magnetSize));
  }

  function resolveCollisions() {
    const minDistance = magnetSize * 0.96;

    // A few deterministic relaxation passes are enough for six magnets and
    // avoid any post-release motion/inertia.
    for (let pass = 0; pass < 5; pass += 1) {
      for (let i = 0; i < magnets.length; i += 1) {
        const a = magnets[i];
        for (let j = i + 1; j < magnets.length; j += 1) {
          const b = magnets[j];

          const ax = a.x + magnetSize / 2;
          const ay = a.y + magnetSize / 2;
          const bx = b.x + magnetSize / 2;
          const by = b.y + magnetSize / 2;
          let dx = bx - ax;
          let dy = by - ay;
          let distance = Math.hypot(dx, dy);

          if (distance === 0) {
            dx = 0.001;
            dy = 0.001;
            distance = Math.hypot(dx, dy);
          }
          if (distance >= minDistance) continue;

          const nx = dx / distance;
          const ny = dy / distance;
          const overlap = minDistance - distance;

          if (a.dragging && !b.dragging) {
            b.x += nx * overlap;
            b.y += ny * overlap;
          } else if (!a.dragging && b.dragging) {
            a.x -= nx * overlap;
            a.y -= ny * overlap;
          } else if (!a.dragging && !b.dragging) {
            a.x -= nx * overlap * 0.5;
            a.y -= ny * overlap * 0.5;
            b.x += nx * overlap * 0.5;
            b.y += ny * overlap * 0.5;
          }

          keepInsideBounds(a);
          keepInsideBounds(b);
        }
      }
    }
  }

  function handlePointerDown(event: PointerEvent, magnet: MagnetState) {
    if (!fridgeSurfaceEl) return;
    event.preventDefault();

    const surfaceRect = fridgeSurfaceEl.getBoundingClientRect();
    activeDrag = {
      magnetId: magnet.id,
      pointerId: event.pointerId,
      offsetX: event.clientX - surfaceRect.left - magnet.x,
      offsetY: event.clientY - surfaceRect.top - magnet.y,
      startX: event.clientX,
      startY: event.clientY,
      moved: false,
    };

    magnet.dragging = true;
    magnet.pressed = true;
    magnets = [...magnets];
    (event.currentTarget as HTMLElement | null)?.setPointerCapture?.(event.pointerId);
  }

  function handlePointerMove(event: PointerEvent) {
    if (!activeDrag || !fridgeSurfaceEl) return;
    const magnet = magnets.find((item) => item.id === activeDrag?.magnetId);
    if (!magnet) return;

    const surfaceRect = fridgeSurfaceEl.getBoundingClientRect();
    const targetX = clamp(
      event.clientX - surfaceRect.left - activeDrag.offsetX,
      0,
      Math.max(0, surfaceRect.width - magnetSize),
    );
    const targetY = clamp(
      event.clientY - surfaceRect.top - activeDrag.offsetY,
      0,
      Math.max(0, surfaceRect.height - magnetSize),
    );

    if (!activeDrag.moved && Math.hypot(event.clientX - activeDrag.startX, event.clientY - activeDrag.startY) > 4) {
      activeDrag.moved = true;
      magnet.pressed = false;
    }

    // Resist the cursor slightly to mimic the friction of sliding a magnet
    // across painted metal. There is intentionally no stored velocity.
    magnet.x += (targetX - magnet.x) * dragResponse;
    magnet.y += (targetY - magnet.y) * dragResponse;

    resolveCollisions();
    magnets = [...magnets];
  }

  function finishActiveDrag(shouldOpen = false) {
    if (!activeDrag) return;
    const magnet = magnets.find((item) => item.id === activeDrag?.magnetId);
    if (!magnet) {
      activeDrag = null;
      return;
    }

    const dragged = activeDrag.moved;
    magnet.dragging = false;
    magnet.pressed = false;
    keepInsideBounds(magnet);
    resolveCollisions();
    magnets = [...magnets];

    if (shouldOpen && !dragged) openMagnet(magnet);
    activeDrag = null;
  }

  function handlePointerUp(event: PointerEvent) {
    if (!activeDrag || activeDrag.pointerId !== event.pointerId) return;
    finishActiveDrag(true);
  }

  function handlePointerCancel(event: PointerEvent) {
    if (!activeDrag || activeDrag.pointerId !== event.pointerId) return;
    finishActiveDrag(false);
  }

  function handleKeyActivate(event: KeyboardEvent, magnet: MagnetState) {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      openMagnet(magnet);
    }
  }

  onMount(() => {
    createInitialMagnets();

    const onMove = (event: PointerEvent) => handlePointerMove(event);
    const onUp = (event: PointerEvent) => handlePointerUp(event);
    const onCancel = (event: PointerEvent) => handlePointerCancel(event);

    window.addEventListener('pointermove', onMove, { passive: true });
    window.addEventListener('pointerup', onUp);
    window.addEventListener('pointercancel', onCancel);

    if (fridgeSurfaceEl) {
      resizeObserver = new ResizeObserver(() => createInitialMagnets());
      resizeObserver.observe(fridgeSurfaceEl);
    }

    return () => {
      resizeObserver?.disconnect();
      window.removeEventListener('pointermove', onMove);
      window.removeEventListener('pointerup', onUp);
      window.removeEventListener('pointercancel', onCancel);
    };
  });
</script>

<div class="fridge-scene">
  <div class="fridge-stage">
    <div class="fridge-cast-shadow" aria-hidden="true"></div>
    <div class="fridge-body" aria-label="Off-white refrigerator with draggable contact magnets">
      <div class="fridge-side" aria-hidden="true"></div>
      <div class="fridge-door fridge-door--top" aria-hidden="true"></div>
      <div class="fridge-door fridge-door--bottom" aria-hidden="true"></div>
      <div class="fridge-seam" aria-hidden="true"></div>
      <div class="fridge-handle fridge-handle--top" aria-hidden="true"></div>
      <div class="fridge-handle fridge-handle--bottom" aria-hidden="true"></div>
      <div class="fridge-feet" aria-hidden="true">
        <div class="fridge-foot fridge-foot--left"></div>
        <div class="fridge-foot fridge-foot--right"></div>
      </div>
      <div bind:this={fridgeSurfaceEl} class="fridge-surface">
        {#each magnets as magnet (magnet.id)}
          <button
            type="button"
            class:magnet--dragging={magnet.dragging}
            class:magnet--pressed={magnet.pressed && !magnet.dragging}
            class="magnet"
            style={`left:${magnet.x}px; top:${magnet.y}px; width:${magnetSize}px; height:${magnetSize}px;`}
            aria-label={magnet.label}
            on:pointerdown={(event) => handlePointerDown(event, magnet)}
            on:dragstart|preventDefault
            on:keydown={(event) => handleKeyActivate(event, magnet)}
          >
            <span class="magnet__ambient" aria-hidden="true"></span>
            <span class="magnet__keycap">
              <img class="magnet__image" src={withBase(magnet.imageSrc)} alt="" width="240" height="240" draggable="false" />
            </span>
            <span class="magnet__tooltip">{magnet.label}</span>
          </button>
        {/each}
      </div>
    </div>
  </div>
</div>

<style>
  .fridge-scene {
    width: 100%;
    height: 100%;
    display: grid;
    align-items: end;
    justify-items: center;
    perspective: 1400px;
  }

  .fridge-stage {
    position: relative;
    width: clamp(16.5rem, 24vw, 21rem);
    height: clamp(30rem, 78vh, 37rem);
  }

  .fridge-cast-shadow {
    position: absolute;
    left: 14%;
    right: 10%;
    bottom: 0.05rem;
    height: 1.65rem;
    border-radius: 50%;
    background: rgb(0 0 0 / 0.2);
    filter: blur(0.95rem);
    transform: scaleX(1.02);
  }

  .fridge-body {
    position: absolute;
    left: 50%;
    bottom: 0.65rem;
    width: 100%;
    height: calc(100% - 1rem);
    transform: translateX(-50%);
    border-radius: 1.35rem 1.35rem 1rem 1rem;
    transform-style: preserve-3d;
  }

  .fridge-side {
    position: absolute;
    top: 0.55rem;
    right: -0.7rem;
    bottom: 0.7rem;
    width: 0.85rem;
    border-radius: 0 0.85rem 0.8rem 0;
    background: linear-gradient(180deg, #d5d9d7 0%, #c3c8c5 100%);
    box-shadow:
      inset 1px 0 0 rgb(255 255 255 / 0.52),
      inset -1px 0 0 rgb(0 0 0 / 0.05);
  }

  .fridge-door {
    position: absolute;
    left: 0;
    right: 0;
    border: 1px solid rgb(148 152 150 / 0.2);
    background:
      radial-gradient(circle at 18% 10%, rgb(255 255 255 / 0.72), transparent 28%),
      linear-gradient(180deg, #f2f3f1 0%, #e8ebe8 40%, #dde1de 100%);
    box-shadow:
      inset 0 1px 0 rgb(255 255 255 / 0.82),
      inset 0 -1px 0 rgb(145 150 148 / 0.16),
      0 0.8rem 1.6rem rgb(0 0 0 / 0.11);
  }

  .fridge-door--top {
    top: 0;
    height: 36.5%;
    border-radius: 1.35rem 1.35rem 0.5rem 0.5rem;
  }

  .fridge-door--bottom {
    bottom: 0;
    height: calc(63.5% - 0.42rem);
    border-radius: 0.5rem 0.5rem 1rem 1rem;
  }

  .fridge-seam {
    position: absolute;
    left: 0.42rem;
    right: 0.42rem;
    top: calc(36.5% - 0.08rem);
    height: 0.32rem;
    border-radius: 999px;
    background: linear-gradient(180deg, #8a918f 0%, #bfc4c1 100%);
    box-shadow:
      0 1px 0 rgb(255 255 255 / 0.56),
      0 -1px 0 rgb(0 0 0 / 0.07);
  }

  .fridge-handle {
    position: absolute;
    left: 0.95rem;
    width: 0.52rem;
    border-radius: 999px;
    background: linear-gradient(180deg, #d6dbd8 0%, #c2c7c4 50%, #b3b9b6 100%);
    box-shadow:
      inset 1px 0 0 rgb(255 255 255 / 0.6),
      inset -1px 0 0 rgb(0 0 0 / 0.12),
      0 0.18rem 0.55rem rgb(0 0 0 / 0.06);
  }

  .fridge-handle--top {
    top: 10.5%;
    height: 21%;
  }

  .fridge-handle--bottom {
    top: 44.5%;
    height: 26%;
  }

  .fridge-feet {
    position: absolute;
    left: 0;
    right: 0;
    bottom: -0.45rem;
    height: 0.8rem;
    pointer-events: none;
  }

  .fridge-foot {
    position: absolute;
    bottom: 0;
    width: 0.5rem;
    height: 0.55rem;
    border-radius: 0.08rem 0.08rem 0.18rem 0.18rem;
    background: linear-gradient(180deg, #d7d9d7 0%, #afb4b2 100%);
    box-shadow:
      inset 1px 0 0 rgb(255 255 255 / 0.6),
      inset -1px 0 0 rgb(0 0 0 / 0.1);
  }

  .fridge-foot--left { left: 0.85rem; }
  .fridge-foot--right { right: 0.85rem; }

  .fridge-surface {
    position: absolute;
    inset: 1.1rem 0.95rem 1.2rem 2rem;
    z-index: 5;
    overflow: hidden;
  }

  .magnet {
    --magnet-radius: 0.72rem;

    position: absolute;
    display: block;
    padding: 0;
    border: 0;
    background: transparent;
    cursor: grab;
    transform: translate3d(0, 0, 0);
    transform-origin: 50% 50%;
    backface-visibility: hidden;
    touch-action: none;
    user-select: none;
    -webkit-tap-highlight-color: transparent;
    -webkit-user-drag: none;
  }

  .magnet:focus { outline: none; }

  .magnet--dragging {
    cursor: grabbing;
    z-index: 12;
  }

  .magnet__ambient {
    position: absolute;
    left: 0.3rem;
    right: 0.3rem;
    bottom: -0.22rem;
    height: 0.46rem;
    border-radius: 999px;
    background: rgb(0 0 0 / 0.14);
    filter: blur(0.42rem);
    opacity: 0.38;
    pointer-events: none;
    transition: opacity 120ms ease, filter 120ms ease, transform 120ms ease;
    backface-visibility: hidden;
  }

  .magnet__keycap {
    position: absolute;
    inset: 0;
    overflow: hidden;
    border-radius: var(--magnet-radius);
    transform: translate3d(0, 0, 0) scale(1);
    background: linear-gradient(180deg, rgb(255 255 255 / 0.08), rgb(0 0 0 / 0.02));
    box-shadow:
      0 0.14rem 0 #202020,
      0 0.22rem 0.42rem rgb(0 0 0 / 0.17),
      inset 0 1px 0 rgb(255 255 255 / 0.2),
      inset 0 -1px 0 rgb(0 0 0 / 0.08);
    transition:
      transform 100ms cubic-bezier(0.16, 0.84, 0.24, 1),
      box-shadow 100ms cubic-bezier(0.16, 0.84, 0.24, 1),
      filter 140ms ease;
    backface-visibility: hidden;
    will-change: transform;
  }

  .magnet__keycap::before {
    position: absolute;
    inset: 0;
    border-radius: inherit;
    background: linear-gradient(180deg, rgb(255 255 255 / 0.08), transparent 24%, transparent 76%, rgb(0 0 0 / 0.06));
    content: '';
    pointer-events: none;
    z-index: 1;
  }

  .magnet__image {
    position: relative;
    z-index: 0;
    display: block;
    width: 100%;
    height: 100%;
    object-fit: cover;
    border-radius: inherit;
    pointer-events: none;
    user-select: none;
    -webkit-user-drag: none;
    transform: translate3d(0, 0, 0);
    backface-visibility: hidden;
  }

  .magnet:hover .magnet__keycap {
    filter: brightness(0.93) saturate(0.98);
  }

  .magnet:hover .magnet__ambient {
    opacity: 0.5;
    filter: blur(0.5rem);
    transform: translate3d(0, 0.04rem, 0) scaleX(1.02);
  }

  .magnet--pressed .magnet__keycap {
    transform: translate3d(0, 0.16rem, 0) scale(0.988);
    filter: brightness(0.84);
    box-shadow:
      0 0.04rem 0 #202020,
      0 0.1rem 0.22rem rgb(0 0 0 / 0.16),
      inset 0 0.16rem 0.26rem rgb(0 0 0 / 0.2),
      inset 0 -1px 0 rgb(255 255 255 / 0.05);
  }

  .magnet--pressed .magnet__ambient {
    opacity: 0.3;
    filter: blur(0.3rem);
    transform: translate3d(0, 0.08rem, 0) scaleX(0.98);
  }

  .magnet--dragging .magnet__keycap {
    filter: brightness(0.95);
  }

  .magnet__tooltip {
    position: absolute;
    left: 50%;
    top: calc(100% + 0.42rem);
    min-width: max-content;
    padding: 0.16rem 0.36rem;
    border-radius: 0.36rem;
    background: rgb(255 255 255 / 0.96);
    color: #121212;
    font-family: var(--font-mono);
    font-size: clamp(0.54rem, 0.68vw, 0.7rem);
    font-weight: 600;
    letter-spacing: 0.04em;
    line-height: 1;
    opacity: 0;
    pointer-events: none;
    text-transform: uppercase;
    white-space: nowrap;
    box-shadow: 0 0.2rem 0.65rem rgb(0 0 0 / 0.13);
    transform: translateX(-50%) translateY(0.2rem);
    transition: opacity 120ms ease, transform 120ms ease;
  }

  .magnet:hover .magnet__tooltip {
    opacity: 1;
    transform: translateX(-50%) translateY(0);
  }

  .magnet--dragging .magnet__tooltip { opacity: 0; }

  @media (max-width: 52rem) {
    .fridge-stage {
      width: clamp(14.5rem, 45vw, 18rem);
      height: clamp(27rem, 72vh, 33rem);
    }

    .fridge-handle { left: 0.8rem; }
    .fridge-surface { inset: 0.95rem 0.8rem 1.05rem 1.75rem; }
  }
</style>
