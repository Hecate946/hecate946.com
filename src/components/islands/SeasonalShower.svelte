<script lang="ts">
  import { onMount } from 'svelte';

  type Season = 'spring' | 'summer' | 'autumn' | 'winter';

  interface Particle {
    season: Season;
    startX: number;
    y: number;
    size: number;
    speed: number;
    drift: number;
    sway: number;
    swayRate: number;
    phase: number;
    rotation: number;
    spin: number;
    flutterRate: number;
    delay: number;
    age: number;
    opacity: number;
    sprite: HTMLCanvasElement;
  }

  const SHOWER_INTERVAL_MS = 60_000;
  const MAX_PIXEL_RATIO = 2;
  const SPRITE_SIZE = 180;
  const VALID_SEASONS: Season[] = ['spring', 'summer', 'autumn', 'winter'];

  let canvas!: HTMLCanvasElement;
  let active = false;
  const spriteCache = new Map<Season, HTMLCanvasElement[]>();

  function currentSeason(): Season {
    const season = document.documentElement.dataset.season;
    return VALID_SEASONS.includes(season as Season) ? (season as Season) : 'summer';
  }


  interface ShowerClock {
    listeners: Set<() => void>;
    intervalId: number;
  }

  function getShowerClock(): ShowerClock {
    const showerWindow = window as typeof window & {
      __hecateSeasonalShowerClock?: ShowerClock;
    };

    if (!showerWindow.__hecateSeasonalShowerClock) {
      const listeners = new Set<() => void>();
      const intervalId = window.setInterval(() => {
        for (const listener of listeners) listener();
      }, SHOWER_INTERVAL_MS);

      showerWindow.__hecateSeasonalShowerClock = {
        listeners,
        intervalId,
      };
    }

    return showerWindow.__hecateSeasonalShowerClock;
  }

  function randomBetween(minimum: number, maximum: number) {
    return minimum + Math.random() * (maximum - minimum);
  }

  function createSprite(season: Season, variant: number) {
    const sprite = document.createElement('canvas');
    sprite.width = SPRITE_SIZE;
    sprite.height = SPRITE_SIZE;

    const context = sprite.getContext('2d');
    if (!context) return sprite;

    context.translate(SPRITE_SIZE / 2, SPRITE_SIZE / 2);
    context.lineCap = 'round';
    context.lineJoin = 'round';

    if (season === 'spring') drawSpringFlower(context, variant);
    if (season === 'summer') drawBeachBall(context, variant);
    if (season === 'autumn') drawAutumnLeaf(context, variant);
    if (season === 'winter') drawSnowflake(context, variant);

    return sprite;
  }

  function spritesFor(season: Season) {
    const cached = spriteCache.get(season);
    if (cached) return cached;

    const variantCount = season === 'autumn' ? 12 : 8;
    const sprites = Array.from({ length: variantCount }, (_, index) => createSprite(season, index));
    spriteCache.set(season, sprites);
    return sprites;
  }

  function drawSpringFlower(
    context: CanvasRenderingContext2D,
    variant: number,
  ) {
    const petalCount = 5;
    const rotation = (variant * Math.PI) / 20;
    const petalFill = ['#ec9eb1', '#ed9fb3', '#eba0b4', '#eea4b8'][variant % 4]!;
    const petalHighlight = ['#f3bccb', '#f2b7c8', '#f4bfcd', '#f1b8c8'][variant % 4]!;
    const stamenPink = '#f989a7';
    const innerFill = '#f2d8e1';

    context.save();
    context.rotate(rotation);
    context.shadowColor = 'rgba(124, 67, 90, 0.12)';
    context.shadowBlur = 6;
    context.shadowOffsetY = 3;

    for (let index = 0; index < petalCount; index += 1) {
      context.save();
      context.rotate((index / petalCount) * Math.PI * 2);
      context.fillStyle = petalFill;
      context.beginPath();
      context.moveTo(0, -10);
      context.bezierCurveTo(-13, -15, -35, -31, -36, -45);
      context.bezierCurveTo(-37, -57, -23, -64, -9, -57);
      context.bezierCurveTo(-2, -53, -0.5, -44, 0, -39);
      context.bezierCurveTo(0.5, -44, 2, -53, 9, -57);
      context.bezierCurveTo(23, -64, 37, -57, 36, -45);
      context.bezierCurveTo(35, -31, 13, -15, 0, -10);
      context.closePath();
      context.fill();

      context.fillStyle = petalHighlight;
      context.beginPath();
      context.moveTo(-2, -18);
      context.bezierCurveTo(-14, -23, -24, -31, -24, -42);
      context.bezierCurveTo(-24, -49, -15, -52, -9, -47);
      context.bezierCurveTo(-4, -43, -2, -30, -2, -18);
      context.closePath();
      context.fill();
      context.restore();
    }

    context.strokeStyle = stamenPink;
    context.lineWidth = 5;

    for (let index = 0; index < petalCount; index += 1) {
      const angle = -Math.PI / 2 + (index / petalCount) * Math.PI * 2;
      context.beginPath();
      context.moveTo(0, 2);
      context.lineTo(Math.cos(angle) * 24, Math.sin(angle) * 24 + 2);
      context.stroke();
    }

    for (let index = 0; index < petalCount; index += 1) {
      context.save();
      context.rotate((index / petalCount) * Math.PI * 2 + Math.PI / 10);
      context.fillStyle = innerFill;
      context.beginPath();
      context.moveTo(0, -1);
      context.bezierCurveTo(-6, -5, -13, -13, -10, -21);
      context.bezierCurveTo(-8, -26, -1.5, -24, 1, -18);
      context.bezierCurveTo(3.5, -24, 10, -26, 12, -21);
      context.bezierCurveTo(15, -13, 8, -5, 2, -1);
      context.bezierCurveTo(3, 7, -3, 7, 0, -1);
      context.closePath();
      context.fill();
      context.restore();
    }

    context.restore();
  }

  function drawBeachBall(context: CanvasRenderingContext2D, variant: number) {
    const panels = ['#ef476f', '#ffd166', '#06d6a0', '#118ab2', '#ffffff'] as const;
    const radius = 61;
    const hubX = -7;
    const hubY = -8;

    context.save();
    context.rotate((variant * Math.PI) / 16);
    context.shadowColor = 'rgba(12, 35, 58, 0.24)';
    context.shadowBlur = 8;
    context.shadowOffsetY = 5;
    context.beginPath();
    context.arc(0, 0, radius, 0, Math.PI * 2);
    context.clip();

    for (let index = 0; index < panels.length; index += 1) {
      const startAngle = -Math.PI / 2 + (index / panels.length) * Math.PI * 2;
      const endAngle = -Math.PI / 2 + ((index + 1) / panels.length) * Math.PI * 2;
      context.fillStyle = panels[index]!;
      context.beginPath();
      context.moveTo(hubX, hubY);
      context.bezierCurveTo(
        Math.cos(startAngle) * radius * 0.28 + hubX * 0.7,
        Math.sin(startAngle) * radius * 0.28 + hubY * 0.7,
        Math.cos(startAngle) * radius * 0.68,
        Math.sin(startAngle) * radius * 0.68,
        Math.cos(startAngle) * radius,
        Math.sin(startAngle) * radius,
      );
      context.arc(0, 0, radius, startAngle, endAngle);
      context.bezierCurveTo(
        Math.cos(endAngle) * radius * 0.68,
        Math.sin(endAngle) * radius * 0.68,
        Math.cos(endAngle) * radius * 0.28 + hubX * 0.7,
        Math.sin(endAngle) * radius * 0.28 + hubY * 0.7,
        hubX,
        hubY,
      );
      context.closePath();
      context.fill();
    }

    const shine = context.createRadialGradient(-31, -34, 0, -28, -30, 48);
    shine.addColorStop(0, 'rgba(255,255,255,0.92)');
    shine.addColorStop(0.24, 'rgba(255,255,255,0.58)');
    shine.addColorStop(1, 'rgba(255,255,255,0)');
    context.fillStyle = shine;
    context.beginPath();
    context.arc(0, 0, radius, 0, Math.PI * 2);
    context.fill();

    context.fillStyle = '#ffffff';
    context.beginPath();
    context.arc(hubX, hubY, 9, 0, Math.PI * 2);
    context.fill();
    context.restore();
  }

  function traceMapleLeaf(context: CanvasRenderingContext2D, variant: number) {
    const asymmetry = ((variant % 5) - 2) * 0.9;
    const narrow = variant % 3 === 0 ? 0.94 : variant % 3 === 1 ? 1 : 1.04;

    context.save();
    context.scale(narrow, 1);
    context.beginPath();
    context.moveTo(-2, 47);

    // Left lower lobe and serrated shoulder.
    context.lineTo(-18, 39);
    context.lineTo(-34, 55);
    context.lineTo(-31, 31);
    context.lineTo(-57, 37);
    context.lineTo(-46, 18);
    context.lineTo(-70, 8 + asymmetry);
    context.lineTo(-50, -4);
    context.lineTo(-66, -29 + asymmetry);
    context.lineTo(-38, -23);
    context.lineTo(-43, -51);
    context.lineTo(-20, -36);
    context.lineTo(-11, -69);
    context.lineTo(1, -45);

    // Tall center lobe and right side, deliberately a little asymmetric.
    context.lineTo(14, -66);
    context.lineTo(18, -36);
    context.lineTo(45, -50 - asymmetry);
    context.lineTo(38, -22);
    context.lineTo(67, -17);
    context.lineTo(49, 0);
    context.lineTo(71, 11 - asymmetry);
    context.lineTo(48, 21);
    context.lineTo(63, 36);
    context.lineTo(36, 38);
    context.lineTo(41, 61);
    context.lineTo(17, 49);
    context.lineTo(7, 69);
    context.lineTo(0, 47);
    context.closePath();
    context.restore();
  }

  function drawAutumnLeaf(context: CanvasRenderingContext2D, variant: number) {
    const palettes = [
      ['#ffb347', '#f06a32', '#a72835'],
      ['#ff9d3f', '#e95731', '#86243a'],
      ['#ffc05a', '#ed7230', '#b12d2e'],
      ['#f8923e', '#d94b33', '#72233b'],
      ['#ffad45', '#ef5a2d', '#93262f'],
      ['#ffbd55', '#df6330', '#7e2937'],
    ] as const;
    const [light, middle, dark] = palettes[variant % palettes.length]!;
    const tilt = ((variant % 7) - 3) * 0.025;

    context.save();
    context.rotate(tilt);
    context.shadowColor = 'rgba(74, 24, 27, 0.3)';
    context.shadowBlur = 9;
    context.shadowOffsetX = 1;
    context.shadowOffsetY = 5;

    traceMapleLeaf(context, variant);
    const baseGradient = context.createLinearGradient(-58, -65, 57, 64);
    baseGradient.addColorStop(0, light);
    baseGradient.addColorStop(0.43, middle);
    baseGradient.addColorStop(1, dark);
    context.fillStyle = baseGradient;
    context.fill();

    context.shadowColor = 'transparent';
    traceMapleLeaf(context, variant);
    context.clip();

    // A warm translucent wash makes the leaf feel less like flat vector art.
    const sunWash = context.createRadialGradient(-30, -34, 2, -22, -25, 74);
    sunWash.addColorStop(0, 'rgba(255, 238, 154, 0.42)');
    sunWash.addColorStop(0.45, 'rgba(255, 164, 69, 0.12)');
    sunWash.addColorStop(1, 'rgba(255, 255, 255, 0)');
    context.fillStyle = sunWash;
    context.fillRect(-80, -80, 160, 160);

    const lowerShade = context.createLinearGradient(-5, 6, 18, 72);
    lowerShade.addColorStop(0, 'rgba(101, 27, 35, 0)');
    lowerShade.addColorStop(1, 'rgba(82, 20, 34, 0.28)');
    context.fillStyle = lowerShade;
    context.fillRect(-80, -10, 160, 100);

    // Small deterministic blemishes add organic variation without animating noise.
    for (let index = 0; index < 9; index += 1) {
      const angle = variant * 1.81 + index * 2.37;
      const radius = 9 + ((index * 13 + variant * 7) % 43);
      const x = Math.cos(angle) * radius * 0.86;
      const y = Math.sin(angle * 0.91) * radius * 0.72;
      context.fillStyle = index % 3 === 0 ? 'rgba(91, 24, 32, 0.10)' : 'rgba(255, 203, 91, 0.10)';
      context.beginPath();
      context.ellipse(x, y, 1.6 + (index % 3) * 0.8, 0.8 + (index % 2) * 0.55, angle, 0, Math.PI * 2);
      context.fill();
    }

    context.restore();

    // Crisp but subdued silhouette.
    context.save();
    context.rotate(tilt);
    traceMapleLeaf(context, variant);
    context.strokeStyle = 'rgba(98, 30, 35, 0.42)';
    context.lineWidth = 1.35;
    context.stroke();

    const veinColor = 'rgba(113, 42, 34, 0.58)';
    const fineVein = 'rgba(124, 50, 37, 0.38)';
    context.strokeStyle = veinColor;
    context.lineWidth = 3.2;
    context.beginPath();
    context.moveTo(-2, 51);
    context.quadraticCurveTo(-1, 8, 1, -56);
    context.stroke();

    const primaryVeins: Array<[number, number, number, number, number, number]> = [
      [-1, 10, -16, -10, -55, -27],
      [-1, 17, -21, 20, -55, 33],
      [0, 2, 18, -13, 51, -42],
      [0, 15, 22, 19, 57, 33],
      [0, -7, -7, -29, -11, -61],
      [1, -8, 8, -29, 14, -59],
    ];

    for (const [sx, sy, cx, cy, ex, ey] of primaryVeins) {
      context.beginPath();
      context.moveTo(sx, sy);
      context.quadraticCurveTo(cx, cy, ex, ey);
      context.stroke();
    }

    context.strokeStyle = fineVein;
    context.lineWidth = 1.35;
    const secondaryVeins: Array<[number, number, number, number]> = [
      [-13, -5, -33, -12],
      [-22, -15, -42, -20],
      [-16, 20, -37, 25],
      [-27, 27, -47, 32],
      [14, -7, 34, -18],
      [25, -22, 44, -32],
      [17, 20, 38, 25],
      [28, 27, 49, 32],
      [-4, -27, -22, -37],
      [6, -28, 25, -39],
    ];
    for (const [sx, sy, ex, ey] of secondaryVeins) {
      context.beginPath();
      context.moveTo(sx, sy);
      context.lineTo(ex, ey);
      context.stroke();
    }

    const stemGradient = context.createLinearGradient(-2, 43, -19, 79);
    stemGradient.addColorStop(0, 'rgba(132, 48, 31, 0.86)');
    stemGradient.addColorStop(1, 'rgba(82, 29, 29, 0.98)');
    context.strokeStyle = stemGradient;
    context.lineWidth = 5;
    context.beginPath();
    context.moveTo(-2, 43);
    context.quadraticCurveTo(-7, 60, -21, 77);
    context.stroke();

    context.strokeStyle = 'rgba(255, 170, 78, 0.18)';
    context.lineWidth = 1.2;
    context.beginPath();
    context.moveTo(-3, 45);
    context.quadraticCurveTo(-8, 61, -20, 75);
    context.stroke();
    context.restore();
  }

  function drawSnowflake(
    context: CanvasRenderingContext2D,
    variant: number,
  ) {
    const branches = 6;
    const length = 62;
    const branchCount = 2 + (variant % 3);

    context.save();
    context.rotate((variant * Math.PI) / 24);
    context.shadowColor = 'rgba(90, 165, 220, 0.6)';
    context.shadowBlur = 7;
    context.strokeStyle = 'rgba(165, 215, 245, 0.95)';
    context.lineWidth = 3.2;

    for (let index = 0; index < branches; index += 1) {
      context.save();
      context.rotate((index / branches) * Math.PI * 2);
      context.beginPath();
      context.moveTo(0, 0);
      context.lineTo(0, -length);
      context.stroke();

      for (let branch = 1; branch <= branchCount; branch += 1) {
        const y = -length * (0.28 + branch * 0.19);
        const branchLength = 12 + branch * 3 + (variant % 2) * 2;

        context.beginPath();
        context.moveTo(0, y);
        context.lineTo(-branchLength, y - branchLength * 0.72);
        context.moveTo(0, y);
        context.lineTo(branchLength, y - branchLength * 0.72);
        context.stroke();
      }

      context.restore();
    }

    context.fillStyle = 'rgba(238, 250, 255, 0.98)';
    context.beginPath();
    context.arc(0, 0, 5.5, 0, Math.PI * 2);
    context.fill();
    context.restore();
  }

  function particleCount(season: Season, width: number) {
    const compact = width < 620;
    if (season === 'summer') return compact ? 14 : 22;
    if (season === 'winter') return compact ? 22 : 34;
    return compact ? 18 : 28;
  }

  function makeParticles(season: Season, width: number, height: number): Particle[] {
    const sprites = spritesFor(season);
    const count = particleCount(season, width);

    return Array.from({ length: count }, (_, index) => {
      const seasonalScale = season === 'summer' ? 0.82 : season === 'spring' ? 0.72 : 1;
      const baseSize = season === 'winter' ? randomBetween(22, 43) : randomBetween(29, 52) * seasonalScale;

      return {
        season,
        startX: randomBetween(-width * 0.05, width * 1.05),
        y: -baseSize * randomBetween(1.2, 4.8),
        size: baseSize,
        speed:
          season === 'summer'
            ? randomBetween(58, 92)
            : season === 'autumn'
              ? randomBetween(34, 66)
              : randomBetween(42, 82),
        drift: season === 'autumn' ? randomBetween(-14, 14) : randomBetween(-8, 8),
        sway:
          season === 'summer'
            ? randomBetween(20, 48)
            : season === 'autumn'
              ? randomBetween(28, 72)
              : randomBetween(15, 58),
        swayRate: season === 'autumn' ? randomBetween(0.52, 1.08) : randomBetween(0.65, 1.35),
        phase: randomBetween(0, Math.PI * 2),
        rotation: randomBetween(0, Math.PI * 2),
        spin:
          season === 'summer'
            ? randomBetween(-1.1, 1.1)
            : season === 'autumn'
              ? randomBetween(-0.82, 0.82)
              : randomBetween(-0.72, 0.72),
        flutterRate: season === 'autumn' ? randomBetween(1.45, 3.2) : randomBetween(1.2, 2.5),
        delay: index * randomBetween(0.045, 0.13) + randomBetween(0, 1.1),
        age: 0,
        opacity: season === 'summer' ? randomBetween(0.985, 1) : randomBetween(0.84, 1),
        sprite: sprites[index % sprites.length]!,
      };
    });
  }

  onMount(() => {
    const canvasContext = canvas.getContext('2d');
    if (!canvasContext) return;

    const context: CanvasRenderingContext2D = canvasContext;
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
    let width = window.innerWidth;
    let height = window.innerHeight;
    let pixelRatio = 1;
    let particles: Particle[] = [];
    let animationFrame = 0;
    let lastTime = performance.now();
    let showerSeason = currentSeason();

    function resize() {
      width = window.innerWidth;
      height = window.innerHeight;
      pixelRatio = Math.min(MAX_PIXEL_RATIO, Math.max(1, window.devicePixelRatio || 1));
      canvas.width = Math.max(1, Math.round(width * pixelRatio));
      canvas.height = Math.max(1, Math.round(height * pixelRatio));
      canvas.style.width = `${width}px`;
      canvas.style.height = `${height}px`;
      context.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
    }

    function stopAnimation() {
      window.cancelAnimationFrame(animationFrame);
      animationFrame = 0;
      active = false;
      context.clearRect(0, 0, width, height);
    }

    function frame(now: number) {
      const delta = Math.min(50, now - lastTime) / 1000;
      lastTime = now;
      context.clearRect(0, 0, width, height);
      let hasVisibleParticle = false;

      for (const particle of particles) {
        particle.age += delta;
        if (particle.age < particle.delay) {
          hasVisibleParticle = true;
          continue;
        }

        const travelAge = particle.age - particle.delay;
        particle.y += particle.speed * delta;
        particle.rotation += particle.spin * delta;
        const x =
          particle.startX +
          particle.drift * travelAge +
          Math.sin(travelAge * particle.swayRate + particle.phase) * particle.sway;
        const flutter =
          0.76 + Math.abs(Math.cos(travelAge * particle.flutterRate + particle.phase)) * 0.24;

        if (particle.y < height + particle.size * 2.2) hasVisibleParticle = true;

        context.save();
        context.globalAlpha = particle.opacity;
        context.translate(x, particle.y);
        context.rotate(particle.rotation);
        if (particle.season !== 'summer') context.scale(flutter, 1);
        context.drawImage(
          particle.sprite,
          -particle.size,
          -particle.size,
          particle.size * 2,
          particle.size * 2,
        );
        context.restore();
      }

      if (hasVisibleParticle && document.visibilityState === 'visible') {
        animationFrame = window.requestAnimationFrame(frame);
      } else {
        stopAnimation();
      }
    }

    function startShower(season = currentSeason()) {
      if (reducedMotion.matches || document.visibilityState !== 'visible') {
        stopAnimation();
        return;
      }

      showerSeason = season;
      particles = makeParticles(showerSeason, width, height);
      active = true;
      lastTime = performance.now();
      window.cancelAnimationFrame(animationFrame);
      animationFrame = window.requestAnimationFrame(frame);
    }

    function handleVisibility() {
      if (document.visibilityState !== 'visible') stopAnimation();
    }

    function handleReducedMotion() {
      if (reducedMotion.matches) stopAnimation();
    }

    const showerClock = getShowerClock();
    const runScheduledShower = () => startShower(currentSeason());

    resize();
    showerClock.listeners.add(runScheduledShower);
    window.addEventListener('resize', resize, { passive: true });
    document.addEventListener('visibilitychange', handleVisibility);
    reducedMotion.addEventListener('change', handleReducedMotion);

    return () => {
      stopAnimation();
      showerClock.listeners.delete(runScheduledShower);
      window.removeEventListener('resize', resize);
      document.removeEventListener('visibilitychange', handleVisibility);
      reducedMotion.removeEventListener('change', handleReducedMotion);
    };
  });
</script>

<canvas bind:this={canvas} class:active class="seasonal-shower" aria-hidden="true"></canvas>

<style>
  .seasonal-shower {
    position: fixed;
    z-index: 45;
    inset: 0;
    width: 100vw;
    height: 100vh;
    opacity: 0;
    pointer-events: none;
    transition: opacity 220ms ease;
  }

  .seasonal-shower.active {
    opacity: 1;
  }

  @media (prefers-reduced-motion: reduce) {
    .seasonal-shower {
      display: none;
    }
  }
</style>
