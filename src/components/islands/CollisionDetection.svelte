<script lang="ts">
  import { onMount } from 'svelte';
  import SeasonSelector from '@/components/islands/SeasonSelector.svelte';
  import { preloadAutumnLeafAssets } from '@/lib/seasonal-shower/autumn';
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
    Collider as RapierCollider,
    RigidBody as RapierRigidBody,
    World as RapierWorld,
  } from '@dimforge/rapier2d-compat';

  type RapierApi = typeof import('@dimforge/rapier2d-compat')['default'];

  interface CollisionObject extends SummerBallVisualState {
    r: number;
    body: RapierRigidBody;
    collider: RapierCollider;
    sprite: HTMLCanvasElement;
    spriteVariant: number;
    previousX: number;
    previousY: number;
    currentX: number;
    currentY: number;
    previousRotation: number;
    currentRotation: number;
  }

  const MAX_NODE_COUNT = 100;
  const SEASON_NODE_COUNT: Record<Season, number> = {
    spring: 100,
    summer: 100,
    autumn: 100,
    winter: 100,
  };
  const MAX_PIXEL_RATIO = 2;
  const WALL_THICKNESS = 42;

  // The seasonal drawings occupy slightly different amounts of their shared
  // sprite canvas. These display scales make the visible artwork approximately
  // match each body's circular collider.
  const SPRITE_DISPLAY_SCALE: Record<Season, number> = {
    spring: 1.6,
    summer: 1.76,
    autumn: 2.92,
    winter: 1.64,
  };


  // Summer uses a larger invisible collider than its visible artwork so the
  // balls maintain a clean gap instead of visually overlapping in the cluster.
  const COLLIDER_SPACING: Record<Season, number> = {
    spring: SUMMER_BALL_COLLIDER_SPACING,
    summer: 2.06,
    autumn: SUMMER_BALL_COLLIDER_SPACING,
    winter: SUMMER_BALL_COLLIDER_SPACING,
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
  let summerRendererWarmed = false;
  let activeObjectCount = SEASON_NODE_COUNT.summer;
  let seasonChangeId = 0;
  let transparentSprite: HTMLCanvasElement | null = null;
  const summerInstanceData = new Float32Array(MAX_NODE_COUNT * 8);
  const summerWarmupData = new Float32Array([0, 0, 1, 0, 0, 0, 1, 0]);

  function readSeason(): Season {
    const season = document.documentElement.dataset.season;
    return VALID_SEASONS.includes(season as Season) ? (season as Season) : 'summer';
  }

  function randomBetween(minimum: number, maximum: number) {
    return minimum + Math.random() * (maximum - minimum);
  }

  function getSeasonNodeCount(season: Season) {
    return SEASON_NODE_COUNT[season];
  }

  function shortestAngleDelta(from: number, to: number) {
    return Math.atan2(Math.sin(to - from), Math.cos(to - from));
  }

  function getTransparentSprite() {
    if (transparentSprite) return transparentSprite;
    transparentSprite = document.createElement('canvas');
    transparentSprite.width = 1;
    transparentSprite.height = 1;
    return transparentSprite;
  }

  function spritesForSeason(season: Season) {
    if (season === 'summer' && summerRenderer) return [getTransparentSprite()];
    return seasonSprites(season);
  }

  async function prepareSeasonAssets(season: Season) {
    // Summer is procedural WebGL. Pre-generating 8 × 64 Canvas sphere frames
    // was the largest source of the season-switch delay and served no purpose
    // while the WebGL renderer was available.
    if (season === 'summer') {
      if (!summerRenderer) seasonSprites('summer');
      return;
    }

    if (season === 'autumn') await preloadAutumnLeafAssets();
    if ((SEASONAL_SHOWERS[season].animationFrames ?? 1) > 1) {
      await prewarmSeasonSpriteFrames(season, 5);
    }
  }

  function initialPosition(index: number, season: Season) {
    const goldenAngle = Math.PI * (3 - Math.sqrt(5));
    const spacing =
      (season === 'autumn' ? 9.4 : season === 'summer' ? 11.6 : 11.4) *
      (width / 800);
    const distance = spacing * Math.sqrt(index + 0.5);
    const angle = index * goldenAngle;
    return {
      x: Math.cos(angle) * distance,
      y: Math.sin(angle) * distance,
    };
  }

  function commitSeason(nextSeason: Season) {
    const previousObjectCount = activeObjectCount;
    activeSeason = nextSeason;
    activeObjectCount = getSeasonNodeCount(nextSeason);
    const sprites = spritesForSeason(nextSeason);
    const colliderSpacing = COLLIDER_SPACING[nextSeason];

    for (let index = 0; index < objects.length; index += 1) {
      const object = objects[index]!;
      const enabled = index < activeObjectCount;
      const wasEnabled = index < previousObjectCount;

      object.body.setEnabled(enabled);
      if (!enabled) continue;

      object.collider.setRadius(object.r * colliderSpacing);
      object.spriteVariant = index % sprites.length;
      object.sprite = sprites[object.spriteVariant]!;

      if (!wasEnabled) {
        const position = initialPosition(index, nextSeason);
        object.body.setTranslation(position, true);
        object.body.setLinvel(
          { x: randomBetween(-4, 4), y: randomBetween(-4, 4) },
          true,
        );
        object.body.setAngvel(randomBetween(-0.08, 0.08), true);
        object.previousX = position.x;
        object.previousY = position.y;
        object.currentX = position.x;
        object.currentY = position.y;
      }

      if (nextSeason === 'summer') {
        resetSummerBallVisualState(
          object,
          object.currentX,
          object.currentY,
          index,
        );
      }
    }

    d3Alpha = Math.max(d3Alpha, 0.82);
    accumulator = 0;
    lastFrameTime = performance.now();
    if (nextSeason !== 'summer') summerRenderer?.clear();
    draw();
  }

  async function applySeason(nextSeason: Season) {
    const changeId = ++seasonChangeId;
    await prepareSeasonAssets(nextSeason);
    if (changeId !== seasonChangeId) return;
    commitSeason(nextSeason);
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

      for (let index = 0; index < activeObjectCount; index += 1) {
        const object = objects[index]!;
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

      summerRenderer.draw(summerInstanceData, activeObjectCount, width, width);
      return;
    }

    summerRenderer?.clear();
    context.save();
    context.translate(width / 2, width / 2);

    for (let index = 0; index < activeObjectCount; index += 1) {
      const object = objects[index]!;
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

  function warmSummerRenderer() {
    if (!summerRenderer || summerRendererWarmed || width <= 0) return;
    summerRenderer.draw(summerWarmupData, 1, width, width);
    summerRenderer.clear();
    summerRendererWarmed = true;
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
    warmSummerRenderer();

    const nextWorld = new rapier.World({ x: 0, y: 0 });
    nextWorld.timestep = SUMMER_BALL_FIXED_TIMESTEP;
    nextWorld.numSolverIterations = 4;
    world = nextWorld;

    addBoundaryColliders(width);

    const radiusScale = width / 175;
    const minimumRadius = radiusScale * 1.42;
    const maximumRadius = radiusScale * 4.45;
    const randomRadius = () =>
      minimumRadius + Math.random() * (maximumRadius - minimumRadius);
    const sprites = spritesForSeason(activeSeason);
    const goldenAngle = Math.PI * (3 - Math.sqrt(5));
    const d3Spacing =
      (activeSeason === 'autumn' ? 9.4 : activeSeason === 'summer' ? 11.6 : 11.4) *
      (width / 800);

    activeObjectCount = getSeasonNodeCount(activeSeason);

    objects = Array.from({ length: MAX_NODE_COUNT }, (_, index) => {
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

      const collider = world!.createCollider(
        rapier!
          .ColliderDesc.ball(radius * COLLIDER_SPACING[activeSeason])
          .setDensity(0.012)
          .setFriction(0.32)
          .setRestitution(0.04),
        body,
      );

      const enabled = index < activeObjectCount;
      body.setEnabled(enabled);
      const initialRotation = body.rotation();

      return {
        r: radius,
        body,
        collider,
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

    for (let index = 0; index < activeObjectCount; index += 1) {
      const object = objects[index]!;
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
    for (let index = 0; index < activeObjectCount; index += 1) {
      const object = objects[index]!;
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

    for (let index = 0; index < activeObjectCount; index += 1) {
      const object = objects[index]!;
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
      await prepareSeasonAssets(activeSeason);

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
        if (nextSeason !== activeSeason) void applySeason(nextSeason);
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
      aria-label="Seasonal objects move with D3-style force motion and Rapier collision physics. An extremely large invisible pointer charge pushes much of the field away."
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
