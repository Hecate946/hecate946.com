<script lang="ts">
  import { onMount } from 'svelte';

  type Season = 'spring' | 'summer' | 'autumn' | 'winter';

  interface Particle {
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
    const petals = 5 + (variant % 2);
    const petalLength = 47 + (variant % 3) * 3;
    const petalWidth = 23 + ((variant + 1) % 3) * 2;
    const hues = [337, 344, 329, 350, 320, 340];
    const hue = hues[variant % hues.length];

    context.save();
    context.rotate((variant * Math.PI) / 15);
    context.shadowColor = 'rgba(78, 31, 54, 0.28)';
    context.shadowBlur = 8;
    context.shadowOffsetY = 4;

    for (let index = 0; index < petals; index += 1) {
      context.save();
      context.rotate((index / petals) * Math.PI * 2);

      const gradient = context.createRadialGradient(
        0,
        -12,
        3,
        0,
        -petalLength * 0.58,
        petalLength,
      );
      gradient.addColorStop(0, `hsla(${hue}, 78%, 87%, 0.98)`);
      gradient.addColorStop(0.55, `hsla(${hue}, 74%, 72%, 0.98)`);
      gradient.addColorStop(1, `hsla(${hue - 8}, 64%, 52%, 0.88)`);

      context.fillStyle = gradient;
      context.beginPath();
      context.moveTo(0, -4);
      context.bezierCurveTo(
        -petalWidth,
        -petalLength * 0.32,
        -petalWidth * 0.72,
        -petalLength,
        0,
        -petalLength,
      );
      context.bezierCurveTo(
        petalWidth * 0.72,
        -petalLength,
        petalWidth,
        -petalLength * 0.32,
        0,
        -4,
      );
      context.fill();
      context.restore();
    }

    const center = context.createRadialGradient(-5, -6, 2, 0, 0, 22);
    center.addColorStop(0, '#fff3b6');
    center.addColorStop(0.55, '#efb74b');
    center.addColorStop(1, '#9d5a2c');
    context.fillStyle = center;
    context.beginPath();
    context.arc(0, 0, 20, 0, Math.PI * 2);
    context.fill();
    context.restore();
  }

  function drawBeachBall(
    context: CanvasRenderingContext2D,
    variant: number,
  ) {
    const radius = 58;
    const palettes = [
      ['#ef5b5b', '#f6c94c', '#50a9e8'],
      ['#ff7b54', '#ffd56b', '#5db7de'],
      ['#ee6c8a', '#f8d66d', '#5cb8a5'],
      ['#e95d78', '#f7bc4b', '#5b91e5'],
    ];
    const palette = palettes[variant % palettes.length];
    const rotation = (variant * Math.PI) / 10;

    context.save();
    context.rotate(rotation);
    context.shadowColor = 'rgba(29, 70, 93, 0.25)';
    context.shadowBlur = 9;
    context.shadowOffsetY = 5;

    context.beginPath();
    context.arc(0, 0, radius, 0, Math.PI * 2);
    context.clip();

    const base = context.createRadialGradient(-20, -25, 2, 5, 8, 78);
    base.addColorStop(0, '#ffffff');
    base.addColorStop(0.72, '#fffdf3');
    base.addColorStop(1, '#d9e3e9');
    context.fillStyle = base;
    context.fillRect(-radius, -radius, radius * 2, radius * 2);

    const capX = 14;
    const capY = -16;
    const panelColors = [
      palette[0],
      '#fffdf4',
      palette[1],
      '#fffdf4',
      palette[2],
      '#fffdf4',
    ];

    for (let index = 0; index < 6; index += 1) {
      const start = -Math.PI / 2 + (index / 6) * Math.PI * 2;
      const end = -Math.PI / 2 + ((index + 1) / 6) * Math.PI * 2;

      context.fillStyle = panelColors[index];
      context.beginPath();
      context.moveTo(capX, capY);
      context.lineTo(Math.cos(start) * radius * 1.3, Math.sin(start) * radius * 1.3);
      context.arc(0, 0, radius, start, end);
      context.closePath();
      context.fill();
    }

    context.strokeStyle = 'rgba(26, 74, 99, 0.35)';
    context.lineWidth = 2.1;
    for (let index = 0; index < 6; index += 1) {
      const angle = -Math.PI / 2 + (index / 6) * Math.PI * 2;
      context.beginPath();
      context.moveTo(capX, capY);
      context.quadraticCurveTo(
        Math.cos(angle + 0.18) * radius * 0.55,
        Math.sin(angle + 0.18) * radius * 0.55,
        Math.cos(angle) * radius,
        Math.sin(angle) * radius,
      );
      context.stroke();
    }

    context.fillStyle = palette[(variant + 1) % palette.length];
    context.beginPath();
    context.arc(capX, capY, 10.5, 0, Math.PI * 2);
    context.fill();
    context.strokeStyle = 'rgba(22, 65, 88, 0.5)';
    context.lineWidth = 2;
    context.stroke();

    const highlight = context.createRadialGradient(-27, -31, 0, -27, -31, 22);
    highlight.addColorStop(0, 'rgba(255,255,255,0.9)');
    highlight.addColorStop(1, 'rgba(255,255,255,0)');
    context.fillStyle = highlight;
    context.beginPath();
    context.ellipse(-23, -28, 21, 13, -0.55, 0, Math.PI * 2);
    context.fill();

    context.restore();

    context.save();
    context.rotate(rotation);
    context.strokeStyle = 'rgba(21, 61, 82, 0.72)';
    context.lineWidth = 3.2;
    context.beginPath();
    context.arc(0, 0, radius, 0, Math.PI * 2);
    context.stroke();
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
      const summerScale = season === 'summer' ? 1.18 : 1;
      const baseSize =
        season === 'winter'
          ? randomBetween(22, 43)
          : randomBetween(29, 52) * summerScale;

      return {
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
        opacity: randomBetween(0.82, 1),
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
        context.scale(flutter, 1);
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
