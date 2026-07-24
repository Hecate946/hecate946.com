<script lang="ts">
  import { onMount } from 'svelte';
  import { SEASONAL_SHOWERS, VALID_SEASONS } from '../../lib/seasonal-shower/seasons';
  import type { Particle, Range, Season } from '../../lib/seasonal-shower/types';

  const SHOWER_INTERVAL_MS = 60_000;
  const MAX_PIXEL_RATIO = 2;
  const SPRITE_SIZE = 180;
  const OLD_SEASON_FADE_MS = 900;

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
    reset: () => void;
  }

  function getShowerClock(): ShowerClock {
    const showerWindow = window as typeof window & {
      __hecateSeasonalShowerClock?: ShowerClock;
    };

    if (!showerWindow.__hecateSeasonalShowerClock) {
      const listeners = new Set<() => void>();
      const clock: ShowerClock = {
        listeners,
        intervalId: 0,
        reset() {
          window.clearInterval(clock.intervalId);
          clock.intervalId = window.setInterval(() => {
            for (const listener of listeners) listener();
          }, SHOWER_INTERVAL_MS);
        },
      };
      clock.reset();
      showerWindow.__hecateSeasonalShowerClock = clock;
    }

    return showerWindow.__hecateSeasonalShowerClock;
  }

  function randomBetween(minimum: number, maximum: number) {
    return minimum + Math.random() * (maximum - minimum);
  }

  function randomFrom(range: Range) {
    return randomBetween(range.minimum, range.maximum);
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
    SEASONAL_SHOWERS[season].drawSprite(context, variant);

    return sprite;
  }

  function spritesFor(season: Season) {
    const cached = spriteCache.get(season);
    if (cached) return cached;

    const definition = SEASONAL_SHOWERS[season];
    const sprites = Array.from({ length: definition.variantCount }, (_, index) =>
      createSprite(season, index),
    );
    spriteCache.set(season, sprites);
    return sprites;
  }

  function makeParticles(season: Season, width: number): Particle[] {
    const definition = SEASONAL_SHOWERS[season];
    const sprites = spritesFor(season);
    const compact = width < 620;
    const count = compact
      ? definition.particleCount.compact
      : definition.particleCount.desktop;

    return Array.from({ length: count }, (_, index) => {
      const baseSize = randomFrom(definition.size) * definition.scale;
      const startX = randomBetween(baseSize, Math.max(baseSize, width - baseSize));
      const speed = randomFrom(definition.speed);

      return {
        season,
        startX,
        x: startX,
        y: -baseSize * randomBetween(1.2, 4.8),
        size: baseSize,
        speed,
        drift: randomFrom(definition.drift),
        sway: randomFrom(definition.sway),
        swayRate: randomFrom(definition.swayRate),
        phase: randomBetween(0, Math.PI * 2),
        rotation: randomBetween(0, Math.PI * 2),
        spin: randomFrom(definition.spin),
        flutterRate: randomFrom(definition.flutterRate),
        delay: index * randomBetween(0.035, 0.095) + randomBetween(0, 0.55),
        age: 0,
        opacity: randomFrom(definition.opacity),
        sprite: sprites[index % sprites.length]!,
        velocityX: season === 'summer' ? randomFrom(definition.drift) : 0,
        velocityY: season === 'summer' ? speed : 0,
        gravity: definition.gravity ? randomFrom(definition.gravity) : 0,
        bounceCount: 0,
        maxBounces: season === 'summer' ? Math.floor(randomBetween(4, 7)) : 0,
        fadeStartedAt: null,
        fadeDuration: OLD_SEASON_FADE_MS / 1000,
        expired: false,
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
    let observedSeason = currentSeason();

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

    function stopAnimation(clear = true) {
      window.cancelAnimationFrame(animationFrame);
      animationFrame = 0;
      active = false;
      if (clear) context.clearRect(0, 0, width, height);
    }

    function beginFade(particle: Particle, nowSeconds: number) {
      if (particle.fadeStartedAt === null) particle.fadeStartedAt = nowSeconds;
    }

    function updateSummerParticle(particle: Particle, delta: number, nowSeconds: number) {
      particle.velocityY += particle.gravity * delta;
      particle.x += particle.velocityX * delta;
      particle.y += particle.velocityY * delta;
      particle.rotation += particle.spin * delta;

      const radius = particle.size * 0.78;
      let hitSurface = false;
      let hitFloor = false;

      if (particle.x - radius <= 0 && particle.velocityX < 0) {
        particle.x = radius;
        particle.velocityX = Math.abs(particle.velocityX) * randomBetween(0.78, 0.9);
        hitSurface = true;
      } else if (particle.x + radius >= width && particle.velocityX > 0) {
        particle.x = width - radius;
        particle.velocityX = -Math.abs(particle.velocityX) * randomBetween(0.78, 0.9);
        hitSurface = true;
      }

      if (particle.y + radius >= height && particle.velocityY > 0) {
        particle.y = height - radius;
        const rebound = Math.max(72, Math.abs(particle.velocityY) * randomBetween(0.58, 0.72));
        particle.velocityY = -rebound;
        particle.velocityX = particle.velocityX * randomBetween(0.86, 0.95) + randomBetween(-24, 24);
        hitSurface = true;
        hitFloor = true;
      }

      if (hitSurface) {
        particle.spin += particle.velocityX * 0.0045 + randomBetween(-0.28, 0.28);
        particle.spin = Math.max(-3.6, Math.min(3.6, particle.spin));
      }

      if (hitFloor) {
        particle.bounceCount += 1;
        if (particle.bounceCount >= particle.maxBounces) beginFade(particle, nowSeconds);
      }

      if (particle.y - radius > height + particle.size * 2) beginFade(particle, nowSeconds);
    }

    function frame(now: number) {
      const delta = Math.min(50, now - lastTime) / 1000;
      const nowSeconds = now / 1000;
      lastTime = now;
      context.clearRect(0, 0, width, height);
      let hasVisibleParticle = false;

      for (const particle of particles) {
        if (particle.expired) continue;

        particle.age += delta;
        if (particle.age < particle.delay) {
          hasVisibleParticle = true;
          continue;
        }

        const travelAge = particle.age - particle.delay;
        let x = particle.x;
        let flutter = 1;

        if (particle.season === 'summer') {
          updateSummerParticle(particle, delta, nowSeconds);
          x = particle.x;
        } else {
          particle.y += particle.speed * delta;
          particle.rotation += particle.spin * delta;
          x =
            particle.startX +
            particle.drift * travelAge +
            Math.sin(travelAge * particle.swayRate + particle.phase) * particle.sway;
          flutter =
            0.76 + Math.abs(Math.cos(travelAge * particle.flutterRate + particle.phase)) * 0.24;

          if (particle.y >= height + particle.size * 2.2) {
            particle.expired = true;
            continue;
          }
        }

        let fadeMultiplier = 1;
        if (particle.fadeStartedAt !== null) {
          fadeMultiplier = 1 - (nowSeconds - particle.fadeStartedAt) / particle.fadeDuration;
          if (fadeMultiplier <= 0) {
            particle.expired = true;
            continue;
          }
        }

        hasVisibleParticle = true;
        context.save();
        context.globalAlpha = particle.opacity * fadeMultiplier;
        context.translate(x, particle.y);
        context.rotate(particle.rotation);
        if (SEASONAL_SHOWERS[particle.season].flutter) context.scale(flutter, 1);
        context.drawImage(
          particle.sprite,
          -particle.size,
          -particle.size,
          particle.size * 2,
          particle.size * 2,
        );
        context.restore();
      }

      particles = particles.filter((particle) => !particle.expired);

      if (hasVisibleParticle && document.visibilityState === 'visible') {
        animationFrame = window.requestAnimationFrame(frame);
      } else {
        stopAnimation();
      }
    }

    function ensureAnimation() {
      if (animationFrame || reducedMotion.matches || document.visibilityState !== 'visible') return;
      active = true;
      lastTime = performance.now();
      animationFrame = window.requestAnimationFrame(frame);
    }

    function startShower(season = currentSeason(), fadeExisting = false) {
      if (reducedMotion.matches || document.visibilityState !== 'visible') {
        stopAnimation();
        return;
      }

      const nowSeconds = performance.now() / 1000;
      if (fadeExisting) {
        for (const particle of particles) beginFade(particle, nowSeconds);
      } else {
        particles = [];
      }

      particles.push(...makeParticles(season, width));
      active = true;
      lastTime = performance.now();
      window.cancelAnimationFrame(animationFrame);
      animationFrame = window.requestAnimationFrame(frame);
    }

    function handleVisibility() {
      if (document.visibilityState !== 'visible') {
        stopAnimation();
      } else if (particles.length > 0) {
        ensureAnimation();
      }
    }

    function handleReducedMotion() {
      if (reducedMotion.matches) stopAnimation();
    }

    const showerClock = getShowerClock();
    const runScheduledShower = () => startShower(currentSeason());
    const seasonObserver = new MutationObserver(() => {
      const nextSeason = currentSeason();
      if (nextSeason === observedSeason) return;

      observedSeason = nextSeason;
      showerClock.reset();
      startShower(nextSeason, true);
    });

    resize();
    showerClock.listeners.add(runScheduledShower);
    seasonObserver.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['data-season'],
    });
    window.addEventListener('resize', resize, { passive: true });
    document.addEventListener('visibilitychange', handleVisibility);
    reducedMotion.addEventListener('change', handleReducedMotion);

    return () => {
      stopAnimation();
      showerClock.listeners.delete(runScheduledShower);
      seasonObserver.disconnect();
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
