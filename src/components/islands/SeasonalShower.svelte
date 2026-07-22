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

  const SHOWER_INTERVAL_MS = 60_000; // 1 minute
  const MAX_PIXEL_RATIO = 2;
  const SPRITE_SIZE = 160;
  const VALID_SEASONS: Season[] = ['spring', 'summer', 'autumn', 'winter'];

  let canvas: HTMLCanvasElement;
  let active = false;
  const spriteCache = new Map<Season, HTMLCanvasElement[]>();

  function currentSeason(): Season {
    const season = document.documentElement.dataset.season;
    return VALID_SEASONS.includes(season as Season)
      ? (season as Season)
      : 'summer';
  }

  function randomBetween(min: number, max: number) {
    return min + Math.random() * (max - min);
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
    if (season === 'summer') drawSunflower(context, variant);
    if (season === 'autumn') drawAutumnLeaf(context, variant);
    if (season === 'winter') drawSnowflake(context, variant);

    return sprite;
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
        -petalLength * 0.35,
        -petalWidth * 0.72,
        -petalLength,
        0,
        -petalLength,
      );
      context.bezierCurveTo(
        petalWidth * 0.72,
        -petalLength,
        petalWidth,
        -petalLength * 0.35,
        0,
        -4,
      );
      context.fill();

      context.strokeStyle = `hsla(${hue}, 48%, 95%, 0.45)`;
      context.lineWidth = 1.5;
      context.beginPath();
      context.moveTo(0, -8);
      context.quadraticCurveTo(-2, -petalLength * 0.55, 0, -petalLength * 0.91);
      context.stroke();
      context.restore();
    }

    const center = context.createRadialGradient(-4, -5, 2, 0, 0, 19);
    center.addColorStop(0, '#fff4a8');
    center.addColorStop(0.48, '#f5c84e');
    center.addColorStop(1, '#a76a24');
    context.fillStyle = center;
    context.beginPath();
    context.arc(0, 0, 16, 0, Math.PI * 2);
    context.fill();

    context.fillStyle = 'rgba(113, 65, 22, 0.46)';
    for (let index = 0; index < 18; index += 1) {
      const angle = index * 2.39996;
      const radius = Math.sqrt(index / 18) * 12;
      context.beginPath();
      context.arc(
        Math.cos(angle) * radius,
        Math.sin(angle) * radius,
        1.15,
        0,
        Math.PI * 2,
      );
      context.fill();
    }

    context.restore();
  }

  function drawSunflower(context: CanvasRenderingContext2D, variant: number) {
    const petals = 18 + (variant % 3) * 2;
    const outerRadius = 61 + (variant % 2) * 3;

    context.save();
    context.rotate((variant * Math.PI) / 21);
    context.shadowColor = 'rgba(75, 43, 10, 0.32)';
    context.shadowBlur = 8;
    context.shadowOffsetY = 4;

    for (let index = 0; index < petals; index += 1) {
      context.save();
      context.rotate((index / petals) * Math.PI * 2);
      const petalGradient = context.createLinearGradient(
        0,
        -15,
        0,
        -outerRadius,
      );
      petalGradient.addColorStop(0, '#f4a70c');
      petalGradient.addColorStop(0.55, '#ffd84e');
      petalGradient.addColorStop(1, '#f6b516');
      context.fillStyle = petalGradient;
      context.beginPath();
      context.moveTo(-7, -13);
      context.bezierCurveTo(-15, -30, -12, -53, 0, -outerRadius);
      context.bezierCurveTo(12, -53, 15, -30, 7, -13);
      context.closePath();
      context.fill();
      context.restore();
    }

    const center = context.createRadialGradient(-8, -9, 3, 0, 0, 34);
    center.addColorStop(0, '#9c6b24');
    center.addColorStop(0.36, '#714415');
    center.addColorStop(0.78, '#432914');
    center.addColorStop(1, '#26190f');
    context.fillStyle = center;
    context.beginPath();
    context.arc(0, 0, 31, 0, Math.PI * 2);
    context.fill();

    const seedColors = ['#d79a3d', '#a96723', '#5b3516'];
    for (let index = 0; index < 74; index += 1) {
      const angle = index * 2.39996;
      const radius = Math.sqrt(index / 74) * 27;
      context.fillStyle = seedColors[index % seedColors.length];
      context.beginPath();
      context.ellipse(
        Math.cos(angle) * radius,
        Math.sin(angle) * radius,
        1.35,
        0.85,
        angle,
        0,
        Math.PI * 2,
      );
      context.fill();
    }

    context.restore();
  }

  function drawAutumnLeaf(context: CanvasRenderingContext2D, variant: number) {
    const palettes = [
      ['#f6b53d', '#d95f2f', '#8d2f24'],
      ['#ed8c32', '#c84727', '#7e291d'],
      ['#f3c750', '#cf7228', '#8b3d20'],
      ['#d95732', '#a92f25', '#6d261d'],
      ['#e49b33', '#b94d25', '#70401f'],
      ['#f0b843', '#d4682b', '#8c3422'],
    ];
    const [light, middle, dark] = palettes[variant % palettes.length];

    context.save();
    context.rotate((variant - 2) * 0.035);
    context.shadowColor = 'rgba(61, 25, 12, 0.34)';
    context.shadowBlur = 8;
    context.shadowOffsetY = 4;

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

    context.strokeStyle = 'rgba(255, 218, 115, 0.24)';
    context.lineWidth = 1.2;
    context.beginPath();
    context.moveTo(-5, -56);
    context.lineTo(-5, 48);
    context.stroke();
    context.restore();
  }
  function drawSnowflake(context: CanvasRenderingContext2D, variant: number) {
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

    context.fillStyle = 'rgba(190, 228, 250, 0.98)';
    context.beginPath();
    context.arc(0, 0, 4.4, 0, Math.PI * 2);
    context.fill();

    context.restore();
  }
  function buildSpriteSet(season: Season) {
    const cached = spriteCache.get(season);
    if (cached) return cached;

    const sprites = Array.from({ length: 6 }, (_, index) =>
      createSprite(season, index),
    );
    spriteCache.set(season, sprites);
    return sprites;
  }

  onMount(() => {
    const context = canvas.getContext('2d');
    if (!context) return;

    const motionQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    let particles: Particle[] = [];
    let animationFrame = 0;
    let showerTimer = 0;
    let previousTime = performance.now();
    let viewportWidth = 1;
    let viewportHeight = 1;
    let pixelRatio = 1;

    const resize = () => {
      pixelRatio = Math.min(window.devicePixelRatio || 1, MAX_PIXEL_RATIO);
      viewportWidth = Math.max(1, window.innerWidth);
      viewportHeight = Math.max(1, window.innerHeight);
      canvas.width = Math.round(viewportWidth * pixelRatio);
      canvas.height = Math.round(viewportHeight * pixelRatio);
      context.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
    };

    const stopShower = () => {
      cancelAnimationFrame(animationFrame);
      particles = [];
      active = false;
      context.clearRect(0, 0, viewportWidth, viewportHeight);
      canvas.width = 1;
      canvas.height = 1;
    };

    const frame = (time: number) => {
      const delta = Math.min((time - previousTime) / 1000, 0.05);
      previousTime = time;
      context.clearRect(0, 0, viewportWidth, viewportHeight);

      let visibleParticles = 0;

      for (const particle of particles) {
        particle.age += delta;
        if (particle.age < particle.delay) {
          visibleParticles += 1;
          continue;
        }

        const liveTime = particle.age - particle.delay;
        particle.y += particle.speed * delta;
        particle.rotation += particle.spin * delta;

        const x =
          particle.startX +
          particle.drift * liveTime +
          Math.sin(liveTime * particle.swayRate + particle.phase) *
            particle.sway;

        const flutter =
          0.72 + Math.abs(Math.cos(liveTime * particle.flutterRate)) * 0.28;
        const enteringOpacity = Math.min(1, liveTime / 0.32);
        const leavingOpacity = Math.min(
          1,
          Math.max(0, (viewportHeight + particle.size - particle.y) / 90),
        );

        if (particle.y - particle.size > viewportHeight + 40) continue;

        visibleParticles += 1;
        context.save();
        context.globalAlpha =
          particle.opacity * enteringOpacity * leavingOpacity;
        context.translate(x, particle.y);
        context.rotate(particle.rotation);
        context.scale(flutter, 1);
        context.drawImage(
          particle.sprite,
          -particle.size / 2,
          -particle.size / 2,
          particle.size,
          particle.size,
        );
        context.restore();
      }

      particles = particles.filter(
        (particle) =>
          particle.age < particle.delay ||
          particle.y - particle.size <= viewportHeight + 40,
      );

      if (visibleParticles === 0 || particles.length === 0) {
        stopShower();
        return;
      }

      animationFrame = requestAnimationFrame(frame);
    };

    const startShower = () => {
      if (
        active ||
        motionQuery.matches ||
        document.visibilityState !== 'visible'
      ) {
        return;
      }

      resize();
      const season = currentSeason();
      const sprites = buildSpriteSet(season);
      const count = Math.round(Math.min(155, Math.max(72, viewportWidth / 11)));

      const seasonScale =
        season === 'winter' ? 0.86 : season === 'summer' ? 1.08 : 1;
      const baseSize =
        season === 'winter'
          ? [24, 52]
          : season === 'summer'
            ? [34, 66]
            : [28, 58];

      particles = Array.from({ length: count }, (_, index) => {
        const depth = randomBetween(0.72, 1.24);
        const size = randomBetween(baseSize[0], baseSize[1]) * depth;
        const speed = randomBetween(86, 175) * depth * seasonScale;

        return {
          startX: randomBetween(-size * 0.2, viewportWidth + size * 0.2),
          y: randomBetween(-viewportHeight * 0.28, -size),
          size,
          speed,
          drift: randomBetween(-22, 22) * depth,
          sway: randomBetween(10, 45) * depth,
          swayRate: randomBetween(0.75, 1.75),
          phase: randomBetween(0, Math.PI * 2),
          rotation: randomBetween(0, Math.PI * 2),
          spin: randomBetween(-1.65, 1.65),
          flutterRate: randomBetween(2.1, 5.4),
          delay: randomBetween(0, 2.35) + (index % 7) * 0.035,
          age: 0,
          opacity: randomBetween(0.76, 1),
          sprite: sprites[index % sprites.length],
        };
      });

      active = true;
      previousTime = performance.now();
      animationFrame = requestAnimationFrame(frame);
    };

    const scheduleNextShower = () => {
      window.clearTimeout(showerTimer);
      showerTimer = window.setTimeout(() => {
        startShower();
        scheduleNextShower();
      }, SHOWER_INTERVAL_MS);
    };

    const handleMotionChange = () => {
      if (motionQuery.matches) stopShower();
    };

    const handleManualTrigger = () => startShower();

    const handleResize = () => {
      if (active) resize();
    };

    scheduleNextShower();
    window.addEventListener('resize', handleResize, { passive: true });
    window.addEventListener('seasonal-shower:trigger', handleManualTrigger);
    motionQuery.addEventListener('change', handleMotionChange);

    return () => {
      window.clearTimeout(showerTimer);
      stopShower();
      window.removeEventListener('resize', handleResize);
      window.removeEventListener(
        'seasonal-shower:trigger',
        handleManualTrigger,
      );
      motionQuery.removeEventListener('change', handleMotionChange);
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
    inset: 0;
    z-index: 80;
    width: 100%;
    height: 100%;
    visibility: hidden;
    pointer-events: none;
    contain: strict;
  }

  .seasonal-shower.active {
    visibility: visible;
  }
</style>
