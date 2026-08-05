<script lang="ts">
  import { onMount } from 'svelte';
  import { preloadAutumnLeafAssets } from '../../lib/seasonal-shower/autumn';
  import { SEASONAL_SHOWERS, VALID_SEASONS } from '../../lib/seasonal-shower/seasons';
  import {
    prewarmSeasonSpriteFrames,
    seasonSpriteAtPhase,
    seasonSprites,
  } from '../../lib/seasonal-shower/sprites';
  import {
    createSummerBallWebGlRenderer,
    type SummerBallWebGlRenderer,
  } from '../../lib/seasonal-shower/summer-ball-webgl';
  import {
    createSummerBallVisualState,
    resetSummerBallVisualState,
    SUMMER_BALL_FIXED_TIMESTEP,
    SUMMER_BALL_MAX_FRAME_DELTA,
    SUMMER_BALL_MAX_STEPS_PER_FRAME,
    type SummerBallVisualState,
    updateSummerBallPhysicsTargets,
    updateSummerBallPresentation,
  } from '../../lib/seasonal-shower/summer-ball-motion';
  import type { Particle, Range, Season } from '../../lib/seasonal-shower/types';
  import type {
    Collider as RapierCollider,
    RigidBody as RapierRigidBody,
    World as RapierWorld,
  } from '@dimforge/rapier2d-compat';

  type RapierApi = typeof import('@dimforge/rapier2d-compat')['default'];

  interface ShowerParticle extends Particle, SummerBallVisualState {
    body: RapierRigidBody;
    collider: RapierCollider;
    enabled: boolean;
    previousX: number;
    previousY: number;
    currentX: number;
    currentY: number;
    previousRotation: number;
    currentRotation: number;
    previousVelocityY: number;
    lastBounceAt: number;
  }

  interface PointerState {
    active: boolean;
    x: number;
    y: number;
    velocityX: number;
    velocityY: number;
    lastX: number;
    lastY: number;
    lastMoveAt: number;
  }

  interface PointerPulse {
    x: number;
    y: number;
    startedAt: number;
  }

  const SHOWER_INTERVAL_MS = 60_000;
  const MAX_PIXEL_RATIO = 2;
  const OLD_SEASON_FADE_MS = 900;
  const SUMMER_DISPLAY_SCALE = 1.46;
  const MAX_SUMMER_PARTICLES = 32;
  const WORLD_GRAVITY = 96;
  const WALL_THICKNESS = 64;
  const POINTER_IDLE_MS = 150;
  const POINTER_FORCE_RADIUS_MIN = 118;
  const POINTER_FORCE_RADIUS_RATIO = 0.18;
  const POINTER_BASE_ACCELERATION = 760;
  const POINTER_SPEED_ACCELERATION = 1.55;
  const POINTER_WAKE_ACCELERATION = 0.52;
  const POINTER_MAX_SPEED = 2_400;
  const CLICK_PULSE_RADIUS = 210;
  const CLICK_PULSE_DURATION = 0.32;
  const CLICK_PULSE_ACCELERATION = 1_180;
  const CLICK_PULSE_COOLDOWN_MS = 220;
  const PARTICLE_DENSITY = 0.0012;

  const COLLIDER_SCALE: Record<Season, number> = {
    spring: 0.56,
    summer: 0.78,
    autumn: 0.48,
    winter: 0.54,
  };

  const RESTITUTION: Record<Season, number> = {
    spring: 0.08,
    summer: 0.58,
    autumn: 0.04,
    winter: 0.06,
  };

  const FRICTION: Record<Season, number> = {
    spring: 0.18,
    summer: 0.42,
    autumn: 0.14,
    winter: 0.12,
  };

  const LINEAR_DAMPING: Record<Season, number> = {
    spring: 0.18,
    summer: 0.06,
    autumn: 0.12,
    winter: 0.16,
  };

  const ANGULAR_DAMPING: Record<Season, number> = {
    spring: 0.34,
    summer: 0.18,
    autumn: 0.24,
    winter: 0.32,
  };

  let canvas!: HTMLCanvasElement;
  let summerCanvas!: HTMLCanvasElement;
  let active = false;

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

  function clamp(value: number, minimum: number, maximum: number) {
    return Math.min(maximum, Math.max(minimum, value));
  }

  function smoothstep(minimum: number, maximum: number, value: number) {
    if (maximum <= minimum) return value >= maximum ? 1 : 0;
    const normalized = clamp((value - minimum) / (maximum - minimum), 0, 1);
    return normalized * normalized * (3 - 2 * normalized);
  }

  function shortestAngleDelta(from: number, to: number) {
    return Math.atan2(Math.sin(to - from), Math.cos(to - from));
  }

  function gravityScaleForParticle(season: Season, gravity: number) {
    if (season === 'summer') {
      return clamp(gravity / WORLD_GRAVITY, 0.32, 0.72);
    }

    return season === 'autumn' ? 0.13 : 0.09;
  }

  onMount(() => {
    const canvasContext = canvas.getContext('2d');
    if (!canvasContext) return;

    const context: CanvasRenderingContext2D = canvasContext;
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
    let width = window.innerWidth;
    let height = window.innerHeight;
    let pixelRatio = 1;
    let rapier: RapierApi | null = null;
    let world: RapierWorld | null = null;
    let particles: ShowerParticle[] = [];
    let poolSeason: Season | null = null;
    let animationFrame = 0;
    let lastTime = performance.now();
    let accumulator = 0;
    let observedSeason = currentSeason();
    let summerRenderer: SummerBallWebGlRenderer | null =
      createSummerBallWebGlRenderer(summerCanvas);
    const summerInstanceData = new Float32Array(MAX_SUMMER_PARTICLES * 8);
    let showerRequestId = 0;
    let disposed = false;
    let physicsReady: Promise<void> | null = null;
    let lastClickPulseAt = -Infinity;
    const pointer: PointerState = {
      active: false,
      x: 0,
      y: 0,
      velocityX: 0,
      velocityY: 0,
      lastX: 0,
      lastY: 0,
      lastMoveAt: -Infinity,
    };
    const pointerPulses: PointerPulse[] = [];

    function resizeCanvases() {
      width = window.innerWidth;
      height = window.innerHeight;
      pixelRatio = Math.min(MAX_PIXEL_RATIO, Math.max(1, window.devicePixelRatio || 1));
      canvas.width = Math.max(1, Math.round(width * pixelRatio));
      canvas.height = Math.max(1, Math.round(height * pixelRatio));
      canvas.style.width = `${width}px`;
      canvas.style.height = `${height}px`;
      context.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
      context.imageSmoothingEnabled = true;
      context.imageSmoothingQuality = 'medium';
      summerRenderer?.resize(width, height, pixelRatio);
    }

    function stopAnimation(clear = true) {
      window.cancelAnimationFrame(animationFrame);
      animationFrame = 0;
      active = false;
      accumulator = 0;
      if (clear) {
        context.clearRect(0, 0, width, height);
        summerRenderer?.clear();
      }
    }

    function beginFade(particle: ShowerParticle, nowSeconds: number) {
      if (particle.fadeStartedAt === null) particle.fadeStartedAt = nowSeconds;
    }

    function disposeWorld() {
      world?.free();
      world = null;
      particles = [];
      poolSeason = null;
    }

    function addSummerBoundaries() {
      if (!rapier || !world) return;

      const createWall = (
        halfWidth: number,
        halfHeight: number,
        x: number,
        y: number,
      ) => {
        world!.createCollider(
          rapier!
            .ColliderDesc.cuboid(halfWidth, halfHeight)
            .setTranslation(x, y)
            .setFriction(0.44)
            .setRestitution(0.54),
        );
      };

      createWall(WALL_THICKNESS, height + WALL_THICKNESS, -WALL_THICKNESS, height / 2);
      createWall(
        WALL_THICKNESS,
        height + WALL_THICKNESS,
        width + WALL_THICKNESS,
        height / 2,
      );
      createWall(width + WALL_THICKNESS, WALL_THICKNESS, width / 2, height + WALL_THICKNESS);
    }

    function makeParticle(
      season: Season,
      index: number,
      sprite: HTMLCanvasElement,
    ): ShowerParticle {
      if (!rapier || !world) throw new Error('Rapier world is not ready.');

      const definition = SEASONAL_SHOWERS[season];
      const baseSize = randomFrom(definition.size) * definition.scale;
      const startX = randomBetween(baseSize, Math.max(baseSize, width - baseSize));
      const speed = randomFrom(definition.speed);
      const startY =
        season === 'autumn'
          ? -baseSize * randomBetween(0.35, 1.6)
          : -baseSize * randomBetween(1.2, 4.8);
      const gravity = definition.gravity ? randomFrom(definition.gravity) : 0;
      const body = world.createRigidBody(
        rapier.RigidBodyDesc.dynamic()
          .setTranslation(startX, startY)
          .setRotation(randomBetween(-Math.PI, Math.PI))
          .setLinvel(season === 'summer' ? randomFrom(definition.drift) : 0, speed)
          .setAngvel(randomFrom(definition.spin))
          .setLinearDamping(LINEAR_DAMPING[season])
          .setAngularDamping(ANGULAR_DAMPING[season])
          .setGravityScale(gravityScaleForParticle(season, gravity))
          .setCanSleep(false),
      );
      const collider = world.createCollider(
        rapier.ColliderDesc.ball(baseSize * COLLIDER_SCALE[season])
          .setDensity(PARTICLE_DENSITY)
          .setFriction(FRICTION[season])
          .setRestitution(RESTITUTION[season]),
        body,
      );
      body.setEnabled(false);

      return {
        season,
        startX,
        x: startX,
        y: startY,
        size: baseSize,
        speed,
        drift: randomFrom(definition.drift),
        sway: randomFrom(definition.sway),
        swayRate: randomFrom(definition.swayRate),
        phase: randomBetween(0, Math.PI * 2),
        rotation: body.rotation(),
        spin: body.angvel(),
        flutterRate: randomFrom(definition.flutterRate),
        delay: 0,
        age: 0,
        opacity: randomFrom(definition.opacity),
        sprite,
        spriteVariant: index % definition.variantCount,
        velocityX: body.linvel().x,
        velocityY: body.linvel().y,
        gravity,
        bounceCount: 0,
        maxBounces: season === 'summer' ? Math.floor(randomBetween(1, 4)) : 0,
        fadeStartedAt: null,
        fadeDuration: OLD_SEASON_FADE_MS / 1000,
        expired: false,
        body,
        collider,
        enabled: false,
        previousX: startX,
        previousY: startY,
        currentX: startX,
        currentY: startY,
        previousRotation: body.rotation(),
        currentRotation: body.rotation(),
        previousVelocityY: body.linvel().y,
        lastBounceAt: -Infinity,
        ...createSummerBallVisualState(startX, startY, index),
      };
    }

    function resetParticle(particle: ShowerParticle, index: number) {
      const definition = SEASONAL_SHOWERS[particle.season];
      const baseSize = randomFrom(definition.size) * definition.scale;
      const startX = randomBetween(baseSize, Math.max(baseSize, width - baseSize));
      const startY =
        particle.season === 'autumn'
          ? -baseSize * randomBetween(0.35, 1.6)
          : -baseSize * randomBetween(1.2, 4.8);
      const speed = randomFrom(definition.speed);
      const gravity = definition.gravity ? randomFrom(definition.gravity) : 0;
      const delay =
        particle.season === 'autumn'
          ? index * randomBetween(0.01, 0.026) + randomBetween(0, 0.34)
          : index * randomBetween(0.035, 0.095) + randomBetween(0, 0.55);
      const velocityX =
        particle.season === 'summer'
          ? randomFrom(definition.drift)
          : randomFrom(definition.drift) * 0.22;
      const rotation = randomBetween(-Math.PI, Math.PI);
      const spin = randomFrom(definition.spin);

      particle.startX = startX;
      particle.x = startX;
      particle.y = startY;
      particle.size = baseSize;
      particle.speed = speed;
      particle.drift = randomFrom(definition.drift);
      particle.sway = randomFrom(definition.sway);
      particle.swayRate = randomFrom(definition.swayRate);
      particle.phase = randomBetween(0, Math.PI * 2);
      particle.rotation = rotation;
      particle.spin = spin;
      particle.flutterRate = randomFrom(definition.flutterRate);
      particle.delay = delay;
      particle.age = 0;
      particle.opacity = randomFrom(definition.opacity);
      particle.velocityX = velocityX;
      particle.velocityY = speed;
      particle.gravity = gravity;
      particle.bounceCount = 0;
      particle.maxBounces =
        particle.season === 'summer' ? Math.floor(randomBetween(1, 4)) : 0;
      particle.fadeStartedAt = null;
      particle.expired = false;
      particle.enabled = false;
      particle.previousX = startX;
      particle.previousY = startY;
      particle.currentX = startX;
      particle.currentY = startY;
      particle.previousRotation = rotation;
      particle.currentRotation = rotation;
      particle.previousVelocityY = speed;
      particle.lastBounceAt = -Infinity;

      particle.collider.setEnabled(true);
      particle.collider.setRadius(baseSize * COLLIDER_SCALE[particle.season]);
      particle.body.setEnabled(false);
      particle.body.setTranslation({ x: startX, y: startY }, false);
      particle.body.setRotation(rotation, false);
      particle.body.setLinvel({ x: velocityX, y: speed }, false);
      particle.body.setAngvel(spin, false);
      particle.body.setGravityScale(gravityScaleForParticle(particle.season, gravity), false);
      resetSummerBallVisualState(particle, startX, startY, index);
    }

    function createParticlePool(season: Season) {
      if (!rapier) return;

      disposeWorld();
      poolSeason = season;
      world = new rapier.World({ x: 0, y: WORLD_GRAVITY });
      world.timestep = SUMMER_BALL_FIXED_TIMESTEP;
      world.numSolverIterations = 4;
      if (season === 'summer') addSummerBoundaries();

      const definition = SEASONAL_SHOWERS[season];
      const compact = width < 620;
      const count = compact
        ? definition.particleCount.compact
        : definition.particleCount.desktop;
      const sprites = seasonSprites(season);

      particles = Array.from({ length: count }, (_, index) =>
        makeParticle(season, index, sprites[index % sprites.length]!),
      );
    }

    function enableReadyParticles() {
      for (const particle of particles) {
        if (particle.expired || particle.enabled || particle.age < particle.delay) continue;
        particle.enabled = true;
        particle.body.setEnabled(true);
        particle.previousX = particle.currentX;
        particle.previousY = particle.currentY;
        particle.previousRotation = particle.currentRotation;
      }
    }

    function particleMassScale(particle: ShowerParticle) {
      const colliderRadius = particle.size * COLLIDER_SCALE[particle.season];
      return Math.max(0.8, colliderRadius * colliderRadius * PARTICLE_DENSITY * Math.PI);
    }

    function applyPointerForces(particle: ShowerParticle, nowSeconds: number) {
      const position = particle.body.translation();
      const mass = particleMassScale(particle);

      if (pointer.active) {
        const offsetX = position.x - pointer.x;
        const offsetY = position.y - pointer.y;
        const distance = Math.hypot(offsetX, offsetY);
        const influenceRadius = Math.max(
          POINTER_FORCE_RADIUS_MIN,
          Math.min(width, height) * POINTER_FORCE_RADIUS_RATIO,
        );

        if (distance > 0.001 && distance < influenceRadius) {
          const normalizedDistance = distance / influenceRadius;
          const influence = 1 - smoothstep(0.12, 1, normalizedDistance);
          const pointerSpeed = Math.min(
            POINTER_MAX_SPEED,
            Math.hypot(pointer.velocityX, pointer.velocityY),
          );
          const inverseDistance = 1 / distance;
          const outwardAcceleration =
            (POINTER_BASE_ACCELERATION + pointerSpeed * POINTER_SPEED_ACCELERATION) *
            influence *
            influence;
          const wakeAcceleration = pointerSpeed * POINTER_WAKE_ACCELERATION * influence;
          const pointerDirectionScale = pointerSpeed > 0.001 ? 1 / pointerSpeed : 0;
          const accelerationX =
            offsetX * inverseDistance * outwardAcceleration +
            pointer.velocityX * pointerDirectionScale * wakeAcceleration;
          const accelerationY =
            offsetY * inverseDistance * outwardAcceleration +
            pointer.velocityY * pointerDirectionScale * wakeAcceleration;

          particle.body.applyImpulse(
            {
              x: accelerationX * mass * SUMMER_BALL_FIXED_TIMESTEP,
              y: accelerationY * mass * SUMMER_BALL_FIXED_TIMESTEP,
            },
            true,
          );

          if (particle.season !== 'summer') {
            const torqueDirection =
              pointer.velocityX * offsetY - pointer.velocityY * offsetX >= 0 ? 1 : -1;
            particle.body.applyTorqueImpulse(
              torqueDirection * influence * Math.min(0.16, pointerSpeed / 8_000),
              true,
            );
          }
        }
      }

      for (const pulse of pointerPulses) {
        const pulseAge = nowSeconds - pulse.startedAt;
        if (pulseAge < 0 || pulseAge > CLICK_PULSE_DURATION) continue;
        const pulseOffsetX = position.x - pulse.x;
        const pulseOffsetY = position.y - pulse.y;
        const pulseDistance = Math.hypot(pulseOffsetX, pulseOffsetY);
        if (pulseDistance <= 0.001 || pulseDistance >= CLICK_PULSE_RADIUS) continue;

        const pulseLife = 1 - pulseAge / CLICK_PULSE_DURATION;
        const pulseInfluence =
          (1 - smoothstep(0.08, 1, pulseDistance / CLICK_PULSE_RADIUS)) * pulseLife;
        const pulseImpulse =
          CLICK_PULSE_ACCELERATION * pulseInfluence * mass * SUMMER_BALL_FIXED_TIMESTEP;

        particle.body.applyImpulse(
          {
            x: (pulseOffsetX / pulseDistance) * pulseImpulse,
            y: (pulseOffsetY / pulseDistance) * pulseImpulse,
          },
          true,
        );
      }
    }

    function applySeasonForces(particle: ShowerParticle) {
      if (particle.season === 'summer') return;

      const velocity = particle.body.linvel();
      const travelAge = Math.max(0, particle.age - particle.delay);
      const swayWave = Math.sin(travelAge * particle.swayRate + particle.phase);
      const targetVelocityX = particle.drift + swayWave * particle.sway * 0.48;
      const targetVelocityY = particle.speed;
      const mass = particleMassScale(particle);
      const accelerationX = (targetVelocityX - velocity.x) * 1.25;
      const accelerationY = (targetVelocityY - velocity.y) * 0.72;

      particle.body.applyImpulse(
        {
          x: accelerationX * mass * SUMMER_BALL_FIXED_TIMESTEP,
          y: accelerationY * mass * SUMMER_BALL_FIXED_TIMESTEP,
        },
        true,
      );
    }

    function capturePhysicsState(nowSeconds: number) {
      for (const particle of particles) {
        if (!particle.enabled || particle.expired) continue;

        particle.previousX = particle.currentX;
        particle.previousY = particle.currentY;
        particle.previousRotation = particle.currentRotation;
        const position = particle.body.translation();
        const velocity = particle.body.linvel();
        particle.currentX = position.x;
        particle.currentY = position.y;
        particle.x = position.x;
        particle.y = position.y;
        particle.velocityX = velocity.x;
        particle.velocityY = velocity.y;
        particle.currentRotation += shortestAngleDelta(
          particle.currentRotation,
          particle.body.rotation(),
        );
        particle.rotation = particle.currentRotation;
        particle.spin = particle.body.angvel();

        if (particle.season === 'summer') {
          const radius = particle.size * COLLIDER_SCALE.summer;
          const touchedFloor = position.y + radius >= height - 5;
          const bouncedUpward =
            particle.previousVelocityY > 18 && velocity.y < -5;

          if (
            touchedFloor &&
            bouncedUpward &&
            nowSeconds - particle.lastBounceAt > 0.12
          ) {
            particle.bounceCount += 1;
            particle.lastBounceAt = nowSeconds;

            if (particle.bounceCount >= particle.maxBounces) {
              beginFade(particle, nowSeconds);
              // Rapier still owns the final trajectory. Disabling only this
              // collider lets the ball fall through the floor after its last
              // real collision instead of bouncing forever at the footer.
              particle.collider.setEnabled(false);
            }
          }

          updateSummerBallPhysicsTargets(
            particle,
            velocity,
            particle.body.angvel(),
            particle.size / SUMMER_DISPLAY_SCALE,
            width,
            (angularVelocity) => particle.body.setAngvel(angularVelocity, false),
          );
        }

        particle.previousVelocityY = velocity.y;
      }
    }

    function expireFinishedParticles(nowSeconds: number) {
      for (const particle of particles) {
        if (particle.expired) continue;

        if (particle.fadeStartedAt !== null) {
          const fadeMultiplier =
            1 - (nowSeconds - particle.fadeStartedAt) / particle.fadeDuration;
          if (fadeMultiplier <= 0) {
            particle.expired = true;
            particle.enabled = false;
            particle.body.setEnabled(false);
            continue;
          }
        }

        if (!particle.enabled) continue;
        const margin = particle.size * 2.2;
        if (particle.currentY - margin > height) {
          particle.expired = true;
          particle.enabled = false;
          particle.body.setEnabled(false);
        }
      }
    }

    function stepPhysics(nowSeconds: number) {
      if (!world) return;

      for (const particle of particles) {
        if (particle.expired) continue;
        particle.age += SUMMER_BALL_FIXED_TIMESTEP;
      }

      enableReadyParticles();

      if (performance.now() - pointer.lastMoveAt > POINTER_IDLE_MS) {
        pointer.active = false;
      }
      pointer.velocityX *= 0.82;
      pointer.velocityY *= 0.82;

      for (const particle of particles) {
        if (!particle.enabled || particle.expired) continue;
        applySeasonForces(particle);
        applyPointerForces(particle, nowSeconds);
      }

      world.step();
      capturePhysicsState(nowSeconds);
      expireFinishedParticles(nowSeconds);

      for (let index = pointerPulses.length - 1; index >= 0; index -= 1) {
        if (nowSeconds - pointerPulses[index]!.startedAt > CLICK_PULSE_DURATION) {
          pointerPulses.splice(index, 1);
        }
      }
    }

    function draw(nowSeconds: number, frameDelta: number) {
      context.clearRect(0, 0, width, height);
      const interpolation = Math.min(1, accumulator / SUMMER_BALL_FIXED_TIMESTEP);
      let hasPendingParticle = false;
      let summerCount = 0;

      for (const particle of particles) {
        if (particle.expired) continue;
        hasPendingParticle = true;
        if (!particle.enabled || particle.age < particle.delay) continue;

        const x =
          particle.previousX +
          (particle.currentX - particle.previousX) * interpolation;
        const y =
          particle.previousY +
          (particle.currentY - particle.previousY) * interpolation;
        const rotation =
          particle.previousRotation +
          (particle.currentRotation - particle.previousRotation) * interpolation;
        const travelAge = Math.max(0, particle.age - particle.delay);
        let fadeMultiplier = 1;

        if (particle.fadeStartedAt !== null) {
          fadeMultiplier = clamp(
            1 - (nowSeconds - particle.fadeStartedAt) / particle.fadeDuration,
            0,
            1,
          );
        }

        if (particle.season === 'summer') {
          updateSummerBallPresentation(particle, x, y, frameDelta);

          if (summerRenderer) {
            const dataOffset = summerCount * 8;
            summerInstanceData[dataOffset] = particle.summerVisualX;
            summerInstanceData[dataOffset + 1] = particle.summerVisualY;
            summerInstanceData[dataOffset + 2] = particle.size;
            summerInstanceData[dataOffset + 3] = particle.summerQx;
            summerInstanceData[dataOffset + 4] = particle.summerQy;
            summerInstanceData[dataOffset + 5] = particle.summerQz;
            summerInstanceData[dataOffset + 6] = particle.summerQw;
            summerInstanceData[dataOffset + 7] = particle.opacity * fadeMultiplier;
            summerCount += 1;
            continue;
          }
        }

        let sprite = particle.sprite;
        let flutter = 1;
        if ((SEASONAL_SHOWERS[particle.season].animationFrames ?? 1) > 1) {
          sprite = seasonSpriteAtPhase(
            particle.season,
            particle.spriteVariant,
            travelAge * particle.flutterRate + particle.phase + rotation * 0.24,
          );
        }
        if (SEASONAL_SHOWERS[particle.season].flutter) {
          flutter =
            0.76 +
            Math.abs(Math.cos(travelAge * particle.flutterRate + particle.phase)) * 0.24;
        }

        context.save();
        context.globalAlpha = particle.opacity * fadeMultiplier;
        context.translate(x, y);
        context.rotate(particle.season === 'autumn' ? rotation * 0.52 : rotation);
        if (SEASONAL_SHOWERS[particle.season].flutter) context.scale(flutter, 1);
        context.drawImage(
          sprite,
          -particle.size,
          -particle.size,
          particle.size * 2,
          particle.size * 2,
        );
        context.restore();
      }

      if (summerRenderer) {
        if (summerCount > 0) {
          summerRenderer.draw(summerInstanceData, summerCount, width, height);
        } else {
          summerRenderer.clear();
        }
      }

      return hasPendingParticle;
    }

    function frame(now: number) {
      const frameDelta = Math.min(
        SUMMER_BALL_MAX_FRAME_DELTA,
        Math.max(0, (now - lastTime) / 1000),
      );
      const nowSeconds = now / 1000;
      lastTime = now;
      accumulator += frameDelta;

      let stepCount = 0;
      while (
        accumulator >= SUMMER_BALL_FIXED_TIMESTEP &&
        stepCount < SUMMER_BALL_MAX_STEPS_PER_FRAME
      ) {
        stepPhysics(nowSeconds);
        accumulator -= SUMMER_BALL_FIXED_TIMESTEP;
        stepCount += 1;
      }
      if (stepCount === SUMMER_BALL_MAX_STEPS_PER_FRAME) accumulator = 0;

      const hasPendingParticle = draw(nowSeconds, frameDelta);
      if (hasPendingParticle && document.visibilityState === 'visible') {
        animationFrame = window.requestAnimationFrame(frame);
      } else {
        stopAnimation();
      }
    }

    function ensureAnimation() {
      if (
        animationFrame ||
        reducedMotion.matches ||
        document.visibilityState !== 'visible' ||
        !world
      ) {
        return;
      }
      active = true;
      lastTime = performance.now();
      accumulator = 0;
      animationFrame = window.requestAnimationFrame(frame);
    }

    async function ensurePhysics() {
      if (rapier) return;
      if (!physicsReady) {
        physicsReady = (async () => {
          const importedRapier = (await import('@dimforge/rapier2d-compat')).default;
          await importedRapier.init();
          if (disposed) return;
          rapier = importedRapier;
        })();
      }
      await physicsReady;
    }

    async function prepareSeasonAssets(season: Season, requestId: number) {
      if (season === 'autumn') {
        await preloadAutumnLeafAssets();
        if (requestId !== showerRequestId) return false;
      }

      // Summer remains procedural WebGL. Its Canvas frames are only needed as
      // a fallback when WebGL2 is unavailable.
      if (season !== 'summer' || !summerRenderer) {
        if ((SEASONAL_SHOWERS[season].animationFrames ?? 1) > 1) {
          await prewarmSeasonSpriteFrames(season, 5);
          if (requestId !== showerRequestId) return false;
        }
      }

      return true;
    }

    async function startShower(season = currentSeason()) {
      const requestId = ++showerRequestId;

      if (reducedMotion.matches || document.visibilityState !== 'visible') {
        stopAnimation();
        return;
      }

      const assetsReady = await prepareSeasonAssets(season, requestId);
      if (!assetsReady || requestId !== showerRequestId) return;
      await ensurePhysics();
      if (!rapier || requestId !== showerRequestId) return;

      if (poolSeason !== season || particles.length === 0) {
        createParticlePool(season);
      }

      particles.forEach(resetParticle);
      context.clearRect(0, 0, width, height);
      summerRenderer?.clear();
      active = true;
      lastTime = performance.now();
      accumulator = 0;
      window.cancelAnimationFrame(animationFrame);
      animationFrame = window.requestAnimationFrame(frame);
    }

    function handleVisibility() {
      if (document.visibilityState !== 'visible') {
        stopAnimation(false);
      } else if (particles.some((particle) => !particle.expired)) {
        ensureAnimation();
      }
    }

    function handleReducedMotion() {
      if (reducedMotion.matches) stopAnimation();
    }

    function handlePointerMove(event: PointerEvent) {
      if (reducedMotion.matches) return;
      const now = performance.now();
      const elapsedSeconds = Math.max(1 / 240, (now - pointer.lastMoveAt) / 1000);
      const hasPreviousPosition = Number.isFinite(pointer.lastMoveAt);
      const rawVelocityX = hasPreviousPosition
        ? (event.clientX - pointer.lastX) / elapsedSeconds
        : 0;
      const rawVelocityY = hasPreviousPosition
        ? (event.clientY - pointer.lastY) / elapsedSeconds
        : 0;

      pointer.x = event.clientX;
      pointer.y = event.clientY;
      pointer.velocityX = clamp(rawVelocityX, -POINTER_MAX_SPEED, POINTER_MAX_SPEED);
      pointer.velocityY = clamp(rawVelocityY, -POINTER_MAX_SPEED, POINTER_MAX_SPEED);
      pointer.lastX = event.clientX;
      pointer.lastY = event.clientY;
      pointer.lastMoveAt = now;
      pointer.active = true;
    }

    function handlePointerDown(event: PointerEvent) {
      if (
        reducedMotion.matches ||
        event.pointerType === 'touch' ||
        performance.now() - lastClickPulseAt < CLICK_PULSE_COOLDOWN_MS
      ) {
        return;
      }

      lastClickPulseAt = performance.now();
      pointerPulses.push({
        x: event.clientX,
        y: event.clientY,
        startedAt: performance.now() / 1000,
      });
    }

    let resizeTimer = 0;
    function handleResize() {
      window.clearTimeout(resizeTimer);
      resizeTimer = window.setTimeout(() => {
        const previousWidth = width;
        const previousHeight = height;
        resizeCanvases();

        if (
          rapier &&
          poolSeason &&
          (Math.abs(previousWidth - width) > 8 || Math.abs(previousHeight - height) > 8)
        ) {
          const hadActiveWave = particles.some((particle) => !particle.expired);
          createParticlePool(poolSeason);
          if (hadActiveWave) {
            particles.forEach(resetParticle);
            ensureAnimation();
          }
        }
      }, 120);
    }

    const showerClock = getShowerClock();
    const runScheduledShower = () => {
      void startShower(currentSeason());
    };
    const seasonObserver = new MutationObserver(() => {
      const nextSeason = currentSeason();
      if (nextSeason === observedSeason) return;

      observedSeason = nextSeason;
      showerClock.reset();
      void startShower(nextSeason);
    });

    resizeCanvases();
    showerClock.listeners.add(runScheduledShower);
    seasonObserver.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['data-season'],
    });
    window.addEventListener('resize', handleResize, { passive: true });
    window.addEventListener('pointermove', handlePointerMove, { passive: true });
    window.addEventListener('pointerdown', handlePointerDown, { passive: true });
    document.addEventListener('visibilitychange', handleVisibility);
    reducedMotion.addEventListener('change', handleReducedMotion);

    return () => {
      disposed = true;
      window.clearTimeout(resizeTimer);
      stopAnimation();
      summerRenderer?.dispose();
      summerRenderer = null;
      disposeWorld();
      showerClock.listeners.delete(runScheduledShower);
      seasonObserver.disconnect();
      window.removeEventListener('resize', handleResize);
      window.removeEventListener('pointermove', handlePointerMove);
      window.removeEventListener('pointerdown', handlePointerDown);
      document.removeEventListener('visibilitychange', handleVisibility);
      reducedMotion.removeEventListener('change', handleReducedMotion);
    };
  });
</script>

<canvas bind:this={canvas} class:active class="seasonal-shower" aria-hidden="true"></canvas>
<canvas
  bind:this={summerCanvas}
  class:active
  class="seasonal-shower seasonal-shower-summer"
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

  .seasonal-shower-summer {
    z-index: 46;
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
