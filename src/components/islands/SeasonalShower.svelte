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
  const SPRITE_SIZE = 160;
  const VALID_SEASONS: Season[] = [
    'spring',
    'summer',
    'autumn',
    'winter',
  ];

  let canvas!: HTMLCanvasElement;
  let active = false;

  const spriteCache = new Map<Season, HTMLCanvasElement[]>();

  function currentSeason(): Season {
    const season = document.documentElement.dataset.season;
    return VALID_SEASONS.includes(season as Season)
      ? (season as Season)
      : 'summer';
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

    const sprites = Array.from({ length: 8 }, (_, variant) =>
      createSprite(season, variant),
    );
    spriteCache.set(season, sprites);
    return sprites;
  }

  function drawSpringFlower(
    context: CanvasRenderingContext2D,
    variant: number,
  ) {
    const petalCount = 5;
    const rotation = (variant * Math.PI) / 20;
    const petalFill = ['#ec9eb1', '#ed9fb3', '#eba0b4', '#eea4b8'][variant % 4];
    const petalHighlight = ['#f3bccb', '#f2b7c8', '#f4bfcd', '#f1b8c8'][variant % 4];
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

  function drawBeachBall(
    context: CanvasRenderingContext2D,
    variant: number,
  ) {
    const radius = 58;
    const rotation = (variant * Math.PI) / 22;
    const hubX = 7.5;
    const hubY = 7.5;
    const whitePanel = '#fbfbfb';
    const panelColors = [whitePanel, '#ef4a47', whitePanel, '#f4d438', whitePanel, '#7fb7e7'];
    const seamColor = 'rgba(235, 237, 240, 0.92)';

    context.save();
    context.rotate(rotation);
    context.shadowColor = 'rgba(14, 34, 56, 0.18)';
    context.shadowBlur = 7;
    context.shadowOffsetY = 4;

    context.beginPath();
    context.arc(0, 0, radius, 0, Math.PI * 2);
    context.clip();

    const base = context.createRadialGradient(-16, -22, 0, 8, 10, radius * 1.08);
    base.addColorStop(0, '#ffffff');
    base.addColorStop(0.78, '#fbfbfb');
    base.addColorStop(1, '#ececec');
    context.fillStyle = base;
    context.fillRect(-radius - 8, -radius - 8, radius * 2 + 16, radius * 2 + 16);

    for (let index = 0; index < panelColors.length; index += 1) {
      const startAngle = -Math.PI / 2 + (index / panelColors.length) * Math.PI * 2;
      const endAngle = -Math.PI / 2 + ((index + 1) / panelColors.length) * Math.PI * 2;
      const color = panelColors[index];

      context.fillStyle = color;
      context.beginPath();
      context.moveTo(hubX, hubY);
      context.bezierCurveTo(
        Math.cos(startAngle) * radius * 0.26 + hubX * 0.72,
        Math.sin(startAngle) * radius * 0.26 + hubY * 0.72,
        Math.cos(startAngle) * radius * 0.68,
        Math.sin(startAngle) * radius * 0.68,
        Math.cos(startAngle) * radius * 1.01,
        Math.sin(startAngle) * radius * 1.01,
      );
      context.arc(0, 0, radius, startAngle, endAngle);
      context.bezierCurveTo(
        Math.cos(endAngle) * radius * 0.68,
        Math.sin(endAngle) * radius * 0.68,
        Math.cos(endAngle) * radius * 0.26 + hubX * 0.72,
        Math.sin(endAngle) * radius * 0.26 + hubY * 0.72,
        hubX,
        hubY,
      );
      context.closePath();
      context.fill();
    }

    context.lineWidth = 1.5;
    context.strokeStyle = seamColor;
    for (let index = 0; index < panelColors.length; index += 1) {
      const angle = -Math.PI / 2 + (index / panelColors.length) * Math.PI * 2;
      context.beginPath();
      context.moveTo(hubX, hubY);
      context.bezierCurveTo(
        Math.cos(angle) * radius * 0.30 + hubX * 0.66,
        Math.sin(angle) * radius * 0.30 + hubY * 0.66,
        Math.cos(angle) * radius * 0.72,
        Math.sin(angle) * radius * 0.72,
        Math.cos(angle) * radius * 0.99,
        Math.sin(angle) * radius * 0.99,
      );
      context.stroke();
    }

    const shadow = context.createRadialGradient(18, 20, 10, 18, 20, radius * 1.02);
    shadow.addColorStop(0, 'rgba(0,0,0,0)');
    shadow.addColorStop(0.72, 'rgba(0,0,0,0.02)');
    shadow.addColorStop(1, 'rgba(0,0,0,0.10)');
    context.fillStyle = shadow;
    context.beginPath();
    context.arc(0, 0, radius, 0, Math.PI * 2);
    context.fill();

    const wideShine = context.createRadialGradient(-23, -22, 0, -24, -23, 45);
    wideShine.addColorStop(0, 'rgba(255,255,255,0.94)');
    wideShine.addColorStop(0.18, 'rgba(255,255,255,0.76)');
    wideShine.addColorStop(0.48, 'rgba(255,255,255,0.24)');
    wideShine.addColorStop(1, 'rgba(255,255,255,0)');
    context.fillStyle = wideShine;
    context.beginPath();
    context.ellipse(-22, -20, 34, 27, -0.62, 0, Math.PI * 2);
    context.fill();

    const spotShine = context.createRadialGradient(-34, -35, 0, -34, -35, 13);
    spotShine.addColorStop(0, 'rgba(255,255,255,0.96)');
    spotShine.addColorStop(0.42, 'rgba(255,255,255,0.65)');
    spotShine.addColorStop(1, 'rgba(255,255,255,0)');
    context.fillStyle = spotShine;
    context.beginPath();
    context.ellipse(-33, -34, 13, 9, -0.55, 0, Math.PI * 2);
    context.fill();

    context.fillStyle = '#ffffff';
    context.beginPath();
    context.arc(hubX, hubY, 9.6, 0, Math.PI * 2);
    context.fill();
    context.fillStyle = 'rgba(187, 199, 212, 0.92)';
    context.beginPath();
    context.arc(hubX, hubY, 5.8, 0, Math.PI * 2);
    context.fill();

    context.restore();
  }

  function drawAutumnLeaf(
    context: CanvasRenderingContext2D,
    variant: number,
  ) {
    const palettes = [
      ['#f6b53d', '#d95f2f', '#8d2f24'],
      ['#ffd166', '#e76f51', '#9b3f2f'],
      ['#f4a261', '#d8572a', '#7f2f21'],
      ['#e9c46a', '#c65d35', '#7d3628'],
    ];
    const [light, middle, dark] = palettes[variant % palettes.length];

    context.save();
    context.rotate((variant * Math.PI) / 18);
    context.shadowColor = 'rgba(91, 45, 21, 0.3)';
    context.shadowBlur = 8;
    context.shadowOffsetY = 5;

    const gradient = context.createLinearGradient(-42, -55, 38, 53);
    gradient.addColorStop(0, light);
    gradient.addColorStop(0.53, middle);
    gradient.addColorStop(1, dark);
    context.fillStyle = gradient;

    context.beginPath();
    context.moveTo(0, -66);
    context.lineTo(12, -43);
    context.lineTo(31, -53);
    context.lineTo(28, -31);
    context.lineTo(53, -29);
    context.lineTo(37, -10);
    context.lineTo(61, 2);
    context.lineTo(34, 12);
    context.lineTo(41, 37);
    context.lineTo(14, 27);
    context.lineTo(5, 61);
    context.lineTo(-5, 61);
    context.lineTo(-14, 27);
    context.lineTo(-41, 37);
    context.lineTo(-34, 12);
    context.lineTo(-61, 2);
    context.lineTo(-37, -10);
    context.lineTo(-53, -29);
    context.lineTo(-28, -31);
    context.lineTo(-31, -53);
    context.lineTo(-12, -43);
    context.closePath();
    context.fill();

    context.strokeStyle = 'rgba(91, 45, 21, 0.58)';
    context.lineWidth = 3;
    context.beginPath();
    context.moveTo(0, -57);
    context.lineTo(0, 66);
    context.stroke();

    context.lineWidth = 1.55;
    const veins = [
      [-4, -35, -28, -48],
      [4, -35, 28, -48],
      [-3, -17, -41, -25],
      [3, -17, 41, -25],
      [-2, 2, -43, 2],
      [2, 2, 43, 2],
      [-2, 20, -29, 33],
      [2, 20, 29, 33],
    ];

    for (const [x1, y1, x2, y2] of veins) {
      context.beginPath();
      context.moveTo(x1, y1);
      context.lineTo(x2, y2);
      context.stroke();
    }

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

  function makeParticles(
    season: Season,
    width: number,
    height: number,
  ): Particle[] {
    const sprites = spritesFor(season);
    const count = particleCount(season, width);

    return Array.from({ length: count }, (_, index) => {
      const seasonalScale =
        season === 'summer' ? 0.82 : season === 'spring' ? 0.72 : 1;
      const baseSize =
        season === 'winter'
          ? randomBetween(22, 43)
          : randomBetween(29, 52) * seasonalScale;

      return {
        season,
        startX: randomBetween(-width * 0.05, width * 1.05),
        y: -baseSize * randomBetween(1.2, 4.8),
        size: baseSize,
        speed:
          season === 'summer'
            ? randomBetween(58, 92)
            : randomBetween(42, 82),
        drift: randomBetween(-8, 8),
        sway:
          season === 'summer'
            ? randomBetween(20, 48)
            : randomBetween(15, 58),
        swayRate: randomBetween(0.65, 1.35),
        phase: randomBetween(0, Math.PI * 2),
        rotation: randomBetween(0, Math.PI * 2),
        spin:
          season === 'summer'
            ? randomBetween(-1.1, 1.1)
            : randomBetween(-0.72, 0.72),
        flutterRate: randomBetween(1.2, 2.5),
        delay: index * randomBetween(0.045, 0.13) + randomBetween(0, 1.1),
        age: 0,
        opacity: season === 'summer' ? randomBetween(0.985, 1) : randomBetween(0.82, 1),
        sprite: sprites[index % sprites.length],
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
    let interval = 0;
    let initialTimer = 0;
    let lastTime = performance.now();
    let showerSeason = currentSeason();

    function resize() {
      width = window.innerWidth;
      height = window.innerHeight;
      pixelRatio = Math.min(
        MAX_PIXEL_RATIO,
        Math.max(1, window.devicePixelRatio || 1),
      );

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
          Math.sin(travelAge * particle.swayRate + particle.phase) *
            particle.sway;
        const flutter =
          0.78 +
          Math.abs(
            Math.cos(
              travelAge * particle.flutterRate + particle.phase,
            ),
          ) *
            0.22;

        if (particle.y < height + particle.size * 2.2) {
          hasVisibleParticle = true;
        }

        context.save();
        context.globalAlpha = particle.opacity;
        context.translate(x, particle.y);
        context.rotate(particle.rotation);
        if (particle.season !== 'summer') {
          context.scale(flutter, 1);
        }
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
      if (
        reducedMotion.matches ||
        document.visibilityState !== 'visible'
      ) {
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

    function restartInterval() {
      window.clearInterval(interval);
      interval = window.setInterval(
        () => startShower(currentSeason()),
        SHOWER_INTERVAL_MS,
      );
    }

    function handleVisibility() {
      if (document.visibilityState !== 'visible') {
        stopAnimation();
        return;
      }

      restartInterval();
    }

    function handleReducedMotion() {
      if (reducedMotion.matches) {
        stopAnimation();
      } else {
        startShower(currentSeason());
      }
    }

    const seasonObserver = new MutationObserver((records) => {
      const changed = records.some(
        (record) =>
          record.type === 'attributes' &&
          record.attributeName === 'data-season',
      );

      if (!changed) return;
      const nextSeason = currentSeason();
      if (nextSeason !== showerSeason || !active) {
        startShower(nextSeason);
      }
      restartInterval();
    });

    resize();
    restartInterval();
    initialTimer = window.setTimeout(
      () => startShower(currentSeason()),
      650,
    );

    seasonObserver.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['data-season'],
    });
    window.addEventListener('resize', resize, { passive: true });
    document.addEventListener('visibilitychange', handleVisibility);
    reducedMotion.addEventListener('change', handleReducedMotion);

    return () => {
      stopAnimation();
      window.clearInterval(interval);
      window.clearTimeout(initialTimer);
      seasonObserver.disconnect();
      window.removeEventListener('resize', resize);
      document.removeEventListener(
        'visibilitychange',
        handleVisibility,
      );
      reducedMotion.removeEventListener('change', handleReducedMotion);
    };
  });
</script>

<canvas
  bind:this={canvas}
  class:active
  class="seasonal-shower"
  aria-hidden="true"
></canvas>

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
