import { createInitialSummerBallQuaternion } from './summer-ball-webgl';

export interface Vector2 {
  x: number;
  y: number;
}

export interface SummerBallVisualState {
  summerVisualX: number;
  summerVisualY: number;
  summerQx: number;
  summerQy: number;
  summerQz: number;
  summerQw: number;
  summerAngularX: number;
  summerAngularY: number;
  summerAngularZ: number;
  summerTargetAngularX: number;
  summerTargetAngularY: number;
  summerTargetAngularZ: number;
  rotationSleeping: boolean;
  rotationRestSeconds: number;
}

export const SUMMER_BALL_FIXED_TIMESTEP = 1 / 60;
export const SUMMER_BALL_MAX_FRAME_DELTA = 0.05;
export const SUMMER_BALL_MAX_STEPS_PER_FRAME = 2;

// The beach-ball drawing is rendered at 1.46x the base physics radius. A
// 1.72x collider therefore leaves a clear but still natural gap between the
// visible balls instead of allowing their artwork to overlap.
export const SUMMER_BALL_COLLIDER_SPACING = 1.72;

const D3_ALPHA_TARGET = 0.3;
const D3_ALPHA_DECAY = 1 - Math.pow(0.001, 1 / 300);
const D3_VELOCITY_RETAINED = 0.9;
const D3_CENTER_STRENGTH = 0.01;
const D3_POINTER_STRENGTH_RATIO = 2 / 3;
const D3_TICKS_PER_SECOND = 60;
const POINTER_MIN_DISTANCE_RATIO = 0.045;
const MAX_SPEED_PER_TICK = 9;

const ROTATION_SLEEP_LINEAR_SPEED = 42;
const ROTATION_WAKE_LINEAR_SPEED = 74;
const ROTATION_SLEEP_ANGULAR_SPEED = 0.85;
const ROTATION_WAKE_ANGULAR_SPEED = 1.8;
const ROTATION_REST_SECONDS = 0.22;
const VISUAL_RESPONSE_SECONDS = 0.14;
const POSITION_RESPONSE_SECONDS = 0.045;
const POSITION_REST_DEAD_ZONE = 0.8;
const ROLLING_RESPONSE = 0.22;
const COLLISION_SPIN_RESPONSE = 0.58;
const MAX_VISUAL_ANGULAR_SPEED = 7.5;

function clamp(value: number, minimum: number, maximum: number) {
  return Math.min(maximum, Math.max(minimum, value));
}

function smoothstep(minimum: number, maximum: number, value: number) {
  if (maximum <= minimum) return value >= maximum ? 1 : 0;
  const normalized = clamp((value - minimum) / (maximum - minimum), 0, 1);
  return normalized * normalized * (3 - 2 * normalized);
}

export function advanceSummerBallD3Alpha(alpha: number) {
  return alpha + (D3_ALPHA_TARGET - alpha) * D3_ALPHA_DECAY;
}

export function summerBallD3Velocity(
  currentX: number,
  currentY: number,
  physicalVelocity: Vector2,
  pointerTarget: Vector2,
  pointerActive: boolean,
  width: number,
  alpha: number,
): Vector2 {
  let velocityX = physicalVelocity.x / D3_TICKS_PER_SECOND;
  let velocityY = physicalVelocity.y / D3_TICKS_PER_SECOND;

  velocityX += -currentX * D3_CENTER_STRENGTH * alpha;
  velocityY += -currentY * D3_CENTER_STRENGTH * alpha;

  if (pointerActive) {
    const offsetX = currentX - pointerTarget.x;
    const offsetY = currentY - pointerTarget.y;
    const distance = Math.hypot(offsetX, offsetY);

    if (distance > 0.001) {
      const pointerStrength = width * D3_POINTER_STRENGTH_RATIO;
      const pointerMinimumDistance = Math.max(
        24,
        width * POINTER_MIN_DISTANCE_RATIO,
      );
      const softenedDistance = Math.max(distance, pointerMinimumDistance);
      const repulsion = (pointerStrength * alpha) / softenedDistance;
      velocityX += (offsetX / distance) * repulsion;
      velocityY += (offsetY / distance) * repulsion;
    }
  }

  velocityX *= D3_VELOCITY_RETAINED;
  velocityY *= D3_VELOCITY_RETAINED;

  const speed = Math.hypot(velocityX, velocityY);
  if (speed > MAX_SPEED_PER_TICK) {
    const scale = MAX_SPEED_PER_TICK / speed;
    velocityX *= scale;
    velocityY *= scale;
  }

  return {
    x: velocityX * D3_TICKS_PER_SECOND,
    y: velocityY * D3_TICKS_PER_SECOND,
  };
}

export function createSummerBallVisualState(
  x: number,
  y: number,
  orientationSeed: number,
): SummerBallVisualState {
  const quaternion = createInitialSummerBallQuaternion(orientationSeed);

  return {
    summerVisualX: x,
    summerVisualY: y,
    summerQx: quaternion.x,
    summerQy: quaternion.y,
    summerQz: quaternion.z,
    summerQw: quaternion.w,
    summerAngularX: 0,
    summerAngularY: 0,
    summerAngularZ: 0,
    summerTargetAngularX: 0,
    summerTargetAngularY: 0,
    summerTargetAngularZ: 0,
    rotationSleeping: false,
    rotationRestSeconds: 0,
  };
}

export function resetSummerBallVisualState(
  state: SummerBallVisualState,
  x: number,
  y: number,
  orientationSeed: number,
) {
  Object.assign(state, createSummerBallVisualState(x, y, orientationSeed));
}

export function updateSummerBallPhysicsTargets(
  state: SummerBallVisualState,
  linearVelocity: Vector2,
  physicalAngularVelocity: number,
  radius: number,
  width: number,
  setPhysicalAngularVelocity: (velocity: number) => void,
) {
  const responsiveMotionScale = Math.max(0.55, width / 800);
  const sleepLinearSpeed = ROTATION_SLEEP_LINEAR_SPEED * responsiveMotionScale;
  const wakeLinearSpeed = ROTATION_WAKE_LINEAR_SPEED * responsiveMotionScale;
  const linearSpeed = Math.hypot(linearVelocity.x, linearVelocity.y);
  const angularSpeed = Math.abs(physicalAngularVelocity);
  const shouldWake =
    linearSpeed > wakeLinearSpeed || angularSpeed > ROTATION_WAKE_ANGULAR_SPEED;

  if (state.rotationSleeping && !shouldWake) {
    state.summerTargetAngularX = 0;
    state.summerTargetAngularY = 0;
    state.summerTargetAngularZ = 0;
    setPhysicalAngularVelocity(0);
    return;
  }

  if (state.rotationSleeping) {
    state.rotationSleeping = false;
    state.rotationRestSeconds = 0;
  }

  const quietEnoughToRest =
    linearSpeed < sleepLinearSpeed &&
    angularSpeed < ROTATION_SLEEP_ANGULAR_SPEED;

  state.rotationRestSeconds = quietEnoughToRest
    ? state.rotationRestSeconds + SUMMER_BALL_FIXED_TIMESTEP
    : 0;

  if (state.rotationRestSeconds >= ROTATION_REST_SECONDS) {
    state.rotationSleeping = true;
    state.rotationRestSeconds = 0;
    state.summerAngularX = 0;
    state.summerAngularY = 0;
    state.summerAngularZ = 0;
    state.summerTargetAngularX = 0;
    state.summerTargetAngularY = 0;
    state.summerTargetAngularZ = 0;
    setPhysicalAngularVelocity(0);
    return;
  }

  const rollingAmount = smoothstep(
    sleepLinearSpeed,
    wakeLinearSpeed,
    linearSpeed,
  );
  const inverseRadius = 1 / Math.max(4, radius);
  const rollingScale = ROLLING_RESPONSE * rollingAmount * inverseRadius;
  const collisionSpin =
    angularSpeed < ROTATION_SLEEP_ANGULAR_SPEED
      ? 0
      : physicalAngularVelocity * COLLISION_SPIN_RESPONSE;

  state.summerTargetAngularX = clamp(
    linearVelocity.y * rollingScale,
    -MAX_VISUAL_ANGULAR_SPEED,
    MAX_VISUAL_ANGULAR_SPEED,
  );
  state.summerTargetAngularY = clamp(
    -linearVelocity.x * rollingScale,
    -MAX_VISUAL_ANGULAR_SPEED,
    MAX_VISUAL_ANGULAR_SPEED,
  );
  state.summerTargetAngularZ = clamp(
    collisionSpin,
    -MAX_VISUAL_ANGULAR_SPEED,
    MAX_VISUAL_ANGULAR_SPEED,
  );
}

export function updateSummerBallPresentation(
  state: SummerBallVisualState,
  desiredX: number,
  desiredY: number,
  frameDelta: number,
) {
  const response = 1 - Math.exp(-frameDelta / VISUAL_RESPONSE_SECONDS);
  const positionResponse =
    1 - Math.exp(-frameDelta / POSITION_RESPONSE_SECONDS);
  const positionDeltaX = desiredX - state.summerVisualX;
  const positionDeltaY = desiredY - state.summerVisualY;
  const positionDelta = Math.hypot(positionDeltaX, positionDeltaY);

  if (!state.rotationSleeping || positionDelta > POSITION_REST_DEAD_ZONE) {
    state.summerVisualX += positionDeltaX * positionResponse;
    state.summerVisualY += positionDeltaY * positionResponse;
  }

  if (state.rotationSleeping) return;

  state.summerAngularX +=
    (state.summerTargetAngularX - state.summerAngularX) * response;
  state.summerAngularY +=
    (state.summerTargetAngularY - state.summerAngularY) * response;
  state.summerAngularZ +=
    (state.summerTargetAngularZ - state.summerAngularZ) * response;

  const angularMagnitude = Math.hypot(
    state.summerAngularX,
    state.summerAngularY,
    state.summerAngularZ,
  );

  if (angularMagnitude < 0.008) {
    state.summerAngularX = 0;
    state.summerAngularY = 0;
    state.summerAngularZ = 0;
    return;
  }

  const halfAngle = (angularMagnitude * frameDelta) / 2;
  const deltaScale = Math.sin(halfAngle) / angularMagnitude;
  const deltaX = state.summerAngularX * deltaScale;
  const deltaY = state.summerAngularY * deltaScale;
  const deltaZ = state.summerAngularZ * deltaScale;
  const deltaW = Math.cos(halfAngle);

  const nextX =
    deltaW * state.summerQx +
    deltaX * state.summerQw +
    deltaY * state.summerQz -
    deltaZ * state.summerQy;
  const nextY =
    deltaW * state.summerQy -
    deltaX * state.summerQz +
    deltaY * state.summerQw +
    deltaZ * state.summerQx;
  const nextZ =
    deltaW * state.summerQz +
    deltaX * state.summerQy -
    deltaY * state.summerQx +
    deltaZ * state.summerQw;
  const nextW =
    deltaW * state.summerQw -
    deltaX * state.summerQx -
    deltaY * state.summerQy -
    deltaZ * state.summerQz;
  const inverseLength =
    1 / Math.max(0.000001, Math.hypot(nextX, nextY, nextZ, nextW));

  state.summerQx = nextX * inverseLength;
  state.summerQy = nextY * inverseLength;
  state.summerQz = nextZ * inverseLength;
  state.summerQw = nextW * inverseLength;
}
