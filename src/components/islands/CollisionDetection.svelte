<script lang="ts">
  import { onMount } from 'svelte';
  import SeasonSelector from '@/components/islands/SeasonSelector.svelte';
  import { SEASONAL_SHOWERS, VALID_SEASONS } from '@/lib/seasonal-shower/seasons';
  import {
    prewarmSeasonSpriteFrames,
    seasonSpriteAtPhase,
    seasonSprites,
  } from '@/lib/seasonal-shower/sprites';
  import {
    createSummerBallWebGlRenderer,
    type SummerBallWebGlRenderer,
  } from '@/lib/seasonal-shower/summer-ball-webgl';
  import {
    advanceSummerBallD3Alpha,
    createSummerBallVisualState,
    resetSummerBallVisualState,
    SUMMER_BALL_COLLIDER_SPACING,
    SUMMER_BALL_FIXED_TIMESTEP,
    SUMMER_BALL_MAX_FRAME_DELTA,
    SUMMER_BALL_MAX_STEPS_PER_FRAME,
    summerBallD3Velocity,
    type SummerBallVisualState,
    updateSummerBallPhysicsTargets,
    updateSummerBallPresentation,
  } from '@/lib/seasonal-shower/summer-ball-motion';
  import type { Season } from '@/lib/seasonal-shower/types';
  import type {
    RigidBody as RapierRigidBody,
    World as RapierWorld,
  } from '@dimforge/rapier2d-compat';

  type RapierApi = typeof import('@dimforge/rapier2d-compat')['default'];

  interface CollisionObject extends SummerBallVisualState {
    r: number;
    body: RapierRigidBody;
    sprite: HTMLCanvasElement;
    spriteVariant: number;
    previousX: number;
    previousY: number;
    currentX: number;
    currentY: number;
    previousRotation: number;
    currentRotation: number;
  }

  const NODE_COUNT = 200;
  const MAX_PIXEL_RATIO = 2;
  const WALL_THICKNESS = 42;

  // The seasonal drawings occupy slightly different amounts of their shared
  // sprite canvas. These display scales make the visible artwork approximately
  // match each body's circular collider.
  const SPRITE_DISPLAY_SCALE: Record<Season, number> = {
    spring: 1.38,
    summer: 1.46,
    autumn: 1.2,
    winter: 1.42,
  };

  let activeSeason: Season = 'summer';
  let stage!: HTMLDivElement;
  let canvas!: HTMLCanvasElement;
  let summerCanvas!: HTMLCanvasElement;

  let width = 0;
  let context: CanvasRenderingContext2D | null = null;
  let rapier: RapierApi | null = null;
  let world: RapierWorld | null = null;
  let objects: CollisionObject[] = [];
  let pointerActive = true;
  let pointerTarget = { x: 0, y: 0 };
  let d3Alpha = 1;
  let animationFrame = 0;
  let lastFrameTime = 0;
  let accumulator = 0;
  let simulationVisible = true;
  let animationPrepared = false;
  let summerRenderer: SummerBallWebGlRenderer | null = null;
  const summerInstanceData = new Float32Array(NODE_COUNT * 8);

  function readSeason(): Season {
    const season = document.documentElement.dataset.season;
    return VALID_SEASONS.includes(season as Season) ? (season as Season) : 'summer';
  }

  function randomBetween(minimum: number, maximum: number) {
    return minimum + Math.random() * (maximum - minimum);
  }

  function shortestAngleDelta(from: number, to: number) {
    return Math.atan2(Math.sin(to - from), Math.cos(to - from));
  }

  function applySeason(nextSeason: Season) {
    activeSeason = nextSeason;
    if ((SEASONAL_SHOWERS[nextSeason].animationFrames ?? 1) > 1) {
      void prewarmSeasonSpriteFrames(nextSeason, 5);
    }
    const sprites = seasonSprites(nextSeason);

    objects.forEach((object, index) => {
      object.spriteVariant = index % sprites.length;
      object.sprite = sprites[object.spriteVariant]!;

      if (nextSeason === 'summer') {
        resetSummerBallVisualState(
          object,
          object.currentX,
          object.currentY,
          index,
        );
      }
    });

    if (nextSeason !== 'summer') summerRenderer?.clear();
    draw();
  }

  function drawSprite(
    sprite: HTMLCanvasElement,
    x: number,
    y: number,
    halfSize: number,
  ) {
    if (!context) return;

    context.drawImage(
      sprite,
      x - halfSize,
      y - halfSize,
      halfSize * 2,
      halfSize * 2,
    );
  }

  function draw() {
    if (!context) return;

    context.clearRect(0, 0, width, width);
    const displayScale = SPRITE_DISPLAY_SCALE[activeSeason];
    const interpolation = Math.min(1, accumulator / SUMMER_BALL_FIXED_TIMESTEP);

    if (activeSeason === 'summer' && summerRenderer) {
      let dataOffset = 0;

      for (const object of objects) {
        summerInstanceData[dataOffset] = object.summerVisualX + width / 2;
        summerInstanceData[dataOffset + 1] = object.summerVisualY + width / 2;
        summerInstanceData[dataOffset + 2] = object.r * displayScale;
        summerInstanceData[dataOffset + 3] = object.summerQx;
        summerInstanceData[dataOffset + 4] = object.summerQy;
        summerInstanceData[dataOffset + 5] = object.summerQz;
        summerInstanceData[dataOffset + 6] = object.summerQw;
        summerInstanceData[dataOffset + 7] = 1;
        dataOffset += 8;
      }

      summerRenderer.draw(summerInstanceData, objects.length, width, width);
      return;
    }

    summerRenderer?.clear();
    context.save();
    context.translate(width / 2, width / 2);

    for (const object of objects) {
      const x =
        object.previousX + (object.currentX - object.previousX) * interpolation;
      const y =
        object.previousY + (object.currentY - object.previousY) * interpolation;
      const rotation =
        object.previousRotation +
        (object.currentRotation - object.previousRotation) * interpolation;
      const halfSize = object.r * displayScale;

      if (activeSeason === 'summer') {
        // WebGL2 is unavailable: keep a stable static summer sprite rather
        // than falling back to quantized animation frames.
        drawSprite(object.sprite, x, y, halfSize);
        continue;
      }

      const animatedSprite =
        (SEASONAL_SHOWERS[activeSeason].animationFrames ?? 1) > 1
          ? seasonSpriteAtPhase(
              activeSeason,
              object.spriteVariant,
              rotation * 1.4 + object.r * 0.17,
            )
          : object.sprite;
      const displayRotation = activeSeason === 'autumn' ? rotation * 0.42 : rotation;

      context.save();
      context.translate(x, y);
      context.rotate(displayRotation);
      context.drawImage(
        animatedSprite,
        -halfSize,
        -halfSize,
        halfSize * 2,
        halfSize * 2,
      );
      context.restore();
    }

    context.restore();
  }

  function addBoundaryColliders(nextWidth: number) {
    if (!rapier || !world) return;

    const half = nextWidth / 2;
    const thickness = WALL_THICKNESS;
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
          .setFriction(0.2)
          .setRestitution(0.02),
      );
    };

    createWall(half + thickness, thickness, 0, -half - thickness);
    createWall(half + thickness, thickness, 0, half + thickness);
    createWall(thickness, half + thickness, -half - thickness, 0);
    createWall(thickness, half + thickness, half + thickness, 0);
  }

  function createWorld(nextWidth: number) {
    if (!context || !rapier) return;

    world?.free();
    world = null;
    objects = [];
    pointerActive = true;
    pointerTarget = { x: 0, y: 0 };
    d3Alpha = 1;
    accumulator = 0;
    lastFrameTime = performance.now();
    width = nextWidth;

    const pixelRatio = Math.min(
      MAX_PIXEL_RATIO,
      Math.max(1, window.devicePixelRatio || 1),
    );
    canvas.width = Math.round(width * pixelRatio);
    canvas.height = Math.round(width * pixelRatio);
    canvas.style.width = `${width}px`;
    canvas.style.height = `${width}px`;
    context.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
    context.imageSmoothingEnabled = true;
    context.imageSmoothingQuality = 'medium';
    summerRenderer?.resize(width, width, pixelRatio);

    const nextWorld = new rapier.World({ x: 0, y: 0 });
    nextWorld.timestep = SUMMER_BALL_FIXED_TIMESTEP;
    nextWorld.numSolverIterations = 4;
    world = nextWorld;

    addBoundaryColliders(width);

    const radiusScale = width / 200;
    const randomRadius = () =>
      radiusScale + Math.random() * (radiusScale * 4 - radiusScale);
    const sprites = seasonSprites(activeSeason);
    const goldenAngle = Math.PI * (3 - Math.sqrt(5));
    const d3Spacing = 10 * (width / 800);

    objects = Array.from({ length: NODE_COUNT }, (_, index) => {
      const radius = randomRadius();
      const distance = d3Spacing * Math.sqrt(index + 0.5);
      const angle = index * goldenAngle;
      const x = Math.cos(angle) * distance;
      const y = Math.sin(angle) * distance;
      const spriteVariant = index % sprites.length;

      const body = world!.createRigidBody(
        rapier!
          .RigidBodyDesc.dynamic()
          .setTranslation(x, y)
          .setRotation(randomBetween(-Math.PI, Math.PI))
          .setLinvel(randomBetween(-6, 6), randomBetween(-6, 6))
          .setAngvel(randomBetween(-0.12, 0.12))
          .setLinearDamping(0)
          .setAngularDamping(1.8)
          .setCanSleep(false),
      );

      world!.createCollider(
        rapier!
          .ColliderDesc.ball(radius * SUMMER_BALL_COLLIDER_SPACING)
          .setDensity(0.012)
          .setFriction(0.32)
          .setRestitution(0.04),
        body,
      );

      const initialRotation = body.rotation();

      return {
        r: radius,
        body,
        sprite: sprites[spriteVariant]!,
        spriteVariant,
        previousX: x,
        previousY: y,
        currentX: x,
        currentY: y,
        previousRotation: initialRotation,
        currentRotation: initialRotation,
        ...createSummerBallVisualState(x, y, index),
      };
    });
  }

  function updateD3Motion() {
    if (!world) return;

    d3Alpha = advanceSummerBallD3Alpha(d3Alpha);

    for (const object of objects) {
      const body = object.body;
      const velocity = summerBallD3Velocity(
        object.currentX,
        object.currentY,
        body.linvel(),
        pointerTarget,
        pointerActive,
        width,
        d3Alpha,
      );
      body.setLinvel(velocity, true);
    }
  }

  function capturePhysicsState() {
    for (const object of objects) {
      object.previousX = object.currentX;
      object.previousY = object.currentY;
      object.previousRotation = object.currentRotation;

      const body = object.body;
      const position = body.translation();
      object.currentX = position.x;
      object.currentY = position.y;

      if (activeSeason !== 'summer') {
        object.rotationSleeping = false;
        object.rotationRestSeconds = 0;
        object.currentRotation += shortestAngleDelta(
          object.currentRotation,
          body.rotation(),
        );
        continue;
      }

      updateSummerBallPhysicsTargets(
        object,
        body.linvel(),
        body.angvel(),
        object.r,
        width,
        (velocity) => body.setAngvel(velocity, false),
      );
    }
  }

  function updateSummerVisualState(frameDelta: number) {
    if (activeSeason !== 'summer') return;

    const interpolation = Math.min(
      1,
      accumulator / SUMMER_BALL_FIXED_TIMESTEP,
    );

    for (const object of objects) {
      const desiredX =
        object.previousX + (object.currentX - object.previousX) * interpolation;
      const desiredY =
        object.previousY + (object.currentY - object.previousY) * interpolation;

      updateSummerBallPresentation(object, desiredX, desiredY, frameDelta);
    }
  }

  function stepPhysics() {
    if (!world) return;

    updateD3Motion();
    world.step();
    capturePhysicsState();
  }

  function frame(now: number) {
    if (!simulationVisible) {
      animationFrame = 0;
      return;
    }

    const frameDelta = Math.min(
      SUMMER_BALL_MAX_FRAME_DELTA,
      Math.max(0, (now - lastFrameTime) / 1000),
    );
    lastFrameTime = now;
    accumulator += frameDelta;

    let stepCount = 0;
    while (accumulator >= SUMMER_BALL_FIXED_TIMESTEP && stepCount < SUMMER_BALL_MAX_STEPS_PER_FRAME) {
      stepPhysics();
      accumulator -= SUMMER_BALL_FIXED_TIMESTEP;
      stepCount += 1;
    }

    if (stepCount === SUMMER_BALL_MAX_STEPS_PER_FRAME) accumulator = 0;

    updateSummerVisualState(frameDelta);
    draw();
    animationFrame = window.requestAnimationFrame(frame);
  }

  function startAnimation() {
    if (animationFrame || !simulationVisible || !animationPrepared) return;
    lastFrameTime = performance.now();
    accumulator = 0;
    animationFrame = window.requestAnimationFrame(frame);
  }

  onMount(() => {
    context = canvas.getContext('2d', {
      alpha: true,
    });
    if (!context) return;

    summerRenderer = createSummerBallWebGlRenderer(summerCanvas);

    let disposed = false;
    let resizeObserver: ResizeObserver | null = null;
    let seasonObserver: MutationObserver | null = null;
    let intersectionObserver: IntersectionObserver | null = null;

    const updatePointer = (event: PointerEvent) => {
      if (!world) return;

      // offsetX/offsetY are already CSS-pixel coordinates relative to the
      // canvas, avoiding a forced layout read on every pointer event.
      pointerTarget = {
        x: event.offsetX - width / 2,
        y: event.offsetY - width / 2,
      };
      pointerActive = true;
    };

    const preventTouchScroll = (event: TouchEvent) => {
      event.preventDefault();
    };

    const handleVisibility = () => {
      if (document.visibilityState === 'visible') startAnimation();
    };

    void (async () => {
      const importedRapier = (await import('@dimforge/rapier2d-compat')).default;
      await importedRapier.init();
      if (disposed) return;

      rapier = importedRapier;
      activeSeason = readSeason();

      const initialWidth = Math.max(1, Math.floor(stage.getBoundingClientRect().width));
      createWorld(initialWidth);

      resizeObserver = new ResizeObserver(([entry]) => {
        const nextWidth = Math.max(1, Math.floor(entry.contentRect.width));
        if (Math.abs(nextWidth - width) > 1) {
          createWorld(nextWidth);
          draw();
        }
      });

      seasonObserver = new MutationObserver(() => {
        const nextSeason = readSeason();
        if (nextSeason !== activeSeason) applySeason(nextSeason);
      });

      intersectionObserver = new IntersectionObserver(
        ([entry]) => {
          simulationVisible = entry?.isIntersecting ?? true;

          if (simulationVisible) {
            startAnimation();
          } else {
            window.cancelAnimationFrame(animationFrame);
            animationFrame = 0;
          }
        },
        { rootMargin: '120px' },
      );

      resizeObserver.observe(stage);
      seasonObserver.observe(document.documentElement, {
        attributes: true,
        attributeFilter: ['data-season'],
      });
      intersectionObserver.observe(stage);

      canvas.addEventListener('pointermove', updatePointer);
      canvas.addEventListener('touchmove', preventTouchScroll, { passive: false });
      document.addEventListener('visibilitychange', handleVisibility);

      // The summer layer is procedural WebGL, so there is no animated sprite
      // warm-up or per-frame texture generation before motion can begin.
      draw();
      animationPrepared = true;
      startAnimation();
    })();

    return () => {
      disposed = true;
      window.cancelAnimationFrame(animationFrame);
      canvas.removeEventListener('pointermove', updatePointer);
      canvas.removeEventListener('touchmove', preventTouchScroll);
      document.removeEventListener('visibilitychange', handleVisibility);
      resizeObserver?.disconnect();
      seasonObserver?.disconnect();
      intersectionObserver?.disconnect();
      summerRenderer?.dispose();
      summerRenderer = null;
      world?.free();
      world = null;
      objects = [];
    };
  });
</script>

<div class="collision-lab">
  <div class="collision-season-selector">
    <SeasonSelector />
  </div>

  <div class="collision-stage" bind:this={stage}>
    <canvas
      class="collision-interaction-layer"
      bind:this={canvas}
      aria-label="Two hundred seasonal objects move with D3-style force motion and Rapier collision physics. An extremely large invisible pointer charge pushes much of the field away."
      role="img"
    >
      An interactive Rapier rigid-body collision simulation.
    </canvas>
    <canvas
      class="collision-summer-layer"
      bind:this={summerCanvas}
      aria-hidden="true"
    ></canvas>
  </div>
</div>
