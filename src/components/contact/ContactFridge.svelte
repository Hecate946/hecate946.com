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
  let magnetSize = 88;
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
    magnetSize = clamp(Math.min(width, height) * 0.205, 70, 96);
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
    place-items: center;
    perspective: 1400px;
  }

  .fridge-stage {
    position: relative;
    width: clamp(18rem, 28vw, 24rem);
    height: clamp(28rem, 74vh, 36rem);
  }

  .fridge-cast-shadow {
    position: absolute;
    left: 6%;
    right: -2%;
    bottom: -2.6rem;
    height: 2.4rem;
    border-radius: 50%;
    background: rgb(0 0 0 / 0.2);
    filter: blur(1.1rem);
    transform: scaleX(0.96);
  }

  .fridge-body {
    position: absolute;
    inset: 0;
    border-radius: 1.5rem 1.5rem 1.2rem 1.2rem;
    transform: rotateY(-8deg) rotateX(1.2deg);
    transform-style: preserve-3d;
  }

  .fridge-side {
    position: absolute;
    top: 0.55rem;
    right: -1.05rem;
    bottom: 0.7rem;
    width: 1.2rem;
    border-radius: 0 1rem 0.95rem 0;
    background: linear-gradient(180deg, #d5d8d6 0%, #b9bfbd 100%);
    box-shadow:
      inset 1px 0 0 rgb(255 255 255 / 0.55),
      inset -1px 0 0 rgb(0 0 0 / 0.06);
    transform: translateZ(-1px);
  }

  .fridge-door {
    position: absolute;
    left: 0;
    right: 0;
    border: 1px solid rgb(145 149 147 / 0.26);
    background:
      radial-gradient(circle at 18% 12%, rgb(255 255 255 / 0.82), transparent 34%),
      linear-gradient(180deg, #f3f5f3 0%, #ecefed 42%, #dde2df 100%);
    box-shadow:
      inset 0 1px 0 rgb(255 255 255 / 0.8),
      inset 0 -1px 0 rgb(160 166 163 / 0.22),
      0 0.75rem 1.8rem rgb(0 0 0 / 0.14);
  }

  .fridge-door--top {
    top: 0;
    height: 37%;
    border-radius: 1.5rem 1.5rem 0.55rem 0.55rem;
  }

  .fridge-door--bottom {
    bottom: 0;
    height: calc(63% - 0.45rem);
    border-radius: 0.55rem 0.55rem 1.2rem 1.2rem;
  }

  .fridge-seam {
    position: absolute;
    left: 0.45rem;
    right: 0.55rem;
    top: calc(37% - 0.06rem);
    height: 0.34rem;
    border-radius: 999px;
    background: linear-gradient(180deg, #8b9190 0%, #c4c9c7 100%);
    box-shadow:
      0 1px 0 rgb(255 255 255 / 0.55),
      0 -1px 0 rgb(0 0 0 / 0.08);
  }

  .fridge-handle {
    position: absolute;
    left: 1rem;
    width: 0.62rem;
    border-radius: 999px;
    background: linear-gradient(180deg, #d8dddb 0%, #bcc3c0 50%, #aab1ae 100%);
    box-shadow:
      inset 1px 0 0 rgb(255 255 255 / 0.65),
      inset -1px 0 0 rgb(0 0 0 / 0.14),
      0 0.3rem 0.8rem rgb(0 0 0 / 0.08);
  }

  .fridge-handle--top {
    top: 11%;
    height: 22%;
  }

  .fridge-handle--bottom {
    top: 44%;
    height: 27%;
  }

  .fridge-surface {
    position: absolute;
    inset: 1.2rem 1rem 1.3rem 2.2rem;
    z-index: 5;
    overflow: hidden;
  }

  .magnet {
    --magnet-radius: 0.95rem;

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

  .magnet:focus {
    outline: none;
  }

  .magnet--dragging {
    cursor: grabbing;
    z-index: 12;
  }

  .magnet__ambient {
    position: absolute;
    left: 0.45rem;
    right: 0.45rem;
    bottom: -0.3rem;
    height: 0.72rem;
    border-radius: 999px;
    background: rgb(0 0 0 / 0.2);
    filter: blur(0.46rem);
    opacity: 0.48;
    pointer-events: none;
    transform: translate3d(0, 0, 0);
    transition: opacity 120ms ease, filter 120ms ease, transform 120ms ease;
    backface-visibility: hidden;
  }

  .magnet__keycap {
    position: absolute;
    inset: 0;
    overflow: hidden;
    border-radius: var(--magnet-radius);
    transform: translate3d(0, 0, 0) scale(1);
    box-shadow:
      0 0.3rem 0 #151515,
      0 0.48rem 0.85rem rgb(0 0 0 / 0.2),
      inset 0 1px 0 rgb(255 255 255 / 0.1),
      inset 0 -0.12rem 0 rgb(0 0 0 / 0.12);
    transition:
      transform 100ms cubic-bezier(0.16, 0.84, 0.24, 1),
      box-shadow 100ms cubic-bezier(0.16, 0.84, 0.24, 1),
      filter 140ms ease;
    backface-visibility: hidden;
    will-change: transform;
  }

  .magnet__image {
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
    filter: brightness(0.95);
  }

  .magnet:hover .magnet__ambient {
    opacity: 0.62;
    filter: blur(0.58rem);
    transform: translate3d(0, 0.05rem, 0) scaleX(1.03);
  }

  .magnet--pressed .magnet__keycap {
    transform: translate3d(0, 0.27rem, 0) scale(0.986);
    filter: brightness(0.82);
    box-shadow:
      0 0.06rem 0 #151515,
      0 0.12rem 0.28rem rgb(0 0 0 / 0.18),
      inset 0 0.18rem 0.34rem rgb(0 0 0 / 0.25),
      inset 0 -1px 0 rgb(255 255 255 / 0.05);
  }

  .magnet--pressed .magnet__ambient {
    opacity: 0.4;
    filter: blur(0.35rem);
    transform: translate3d(0, 0.11rem, 0) scaleX(0.96);
  }

  .magnet--dragging .magnet__keycap {
    filter: brightness(0.94);
  }

  .magnet__tooltip {
    position: absolute;
    left: 50%;
    top: calc(100% + 0.54rem);
    min-width: max-content;
    padding: 0.22rem 0.42rem;
    border-radius: 0.42rem;
    background: rgb(255 255 255 / 0.96);
    color: #121212;
    font-family: var(--font-mono);
    font-size: clamp(0.6rem, 0.72vw, 0.76rem);
    font-weight: 600;
    letter-spacing: 0.04em;
    line-height: 1;
    opacity: 0;
    pointer-events: none;
    text-transform: uppercase;
    white-space: nowrap;
    box-shadow: 0 0.25rem 0.9rem rgb(0 0 0 / 0.14);
    transform: translateX(-50%) translateY(0.22rem);
    transition: opacity 120ms ease, transform 120ms ease;
  }

  .magnet:hover .magnet__tooltip {
    opacity: 1;
    transform: translateX(-50%) translateY(0);
  }

  .magnet--dragging .magnet__tooltip {
    opacity: 0;
  }

  @media (max-width: 52rem) {
    .fridge-stage {
      width: clamp(16rem, 42vw, 19rem);
      height: clamp(25rem, 68vh, 32rem);
    }

    .fridge-handle {
      left: 0.85rem;
    }
  }
</style>
