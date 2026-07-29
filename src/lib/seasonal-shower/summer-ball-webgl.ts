export interface SummerBallQuaternion {
  x: number;
  y: number;
  z: number;
  w: number;
}

export interface SummerBallWebGlRenderer {
  resize(width: number, height: number, pixelRatio: number): void;
  draw(
    instanceData: Float32Array,
    instanceCount: number,
    width: number,
    height: number,
  ): void;
  clear(): void;
  dispose(): void;
}

const FLOATS_PER_INSTANCE = 8;
const QUAD_EXTENT = 1.22;

function seededUnit(value: number) {
  const sine = Math.sin(value * 12.9898 + 78.233) * 43758.5453;
  return sine - Math.floor(sine);
}

function normalizeQuaternion(
  quaternion: SummerBallQuaternion,
): SummerBallQuaternion {
  const length = Math.max(
    0.000001,
    Math.hypot(quaternion.x, quaternion.y, quaternion.z, quaternion.w),
  );

  return {
    x: quaternion.x / length,
    y: quaternion.y / length,
    z: quaternion.z / length,
    w: quaternion.w / length,
  };
}

function multiplyQuaternion(
  left: SummerBallQuaternion,
  right: SummerBallQuaternion,
): SummerBallQuaternion {
  return {
    x:
      left.w * right.x +
      left.x * right.w +
      left.y * right.z -
      left.z * right.y,
    y:
      left.w * right.y -
      left.x * right.z +
      left.y * right.w +
      left.z * right.x,
    z:
      left.w * right.z +
      left.x * right.y -
      left.y * right.x +
      left.z * right.w,
    w:
      left.w * right.w -
      left.x * right.x -
      left.y * right.y -
      left.z * right.z,
  };
}

function axisAngleQuaternion(
  x: number,
  y: number,
  z: number,
  angle: number,
): SummerBallQuaternion {
  const axisLength = Math.max(0.000001, Math.hypot(x, y, z));
  const halfAngle = angle / 2;
  const scale = Math.sin(halfAngle) / axisLength;

  return {
    x: x * scale,
    y: y * scale,
    z: z * scale,
    w: Math.cos(halfAngle),
  };
}

export function createInitialSummerBallQuaternion(
  variant: number,
): SummerBallQuaternion {
  const tiltX = (seededUnit(variant + 2) - 0.5) * 1.45;
  const tiltY = (seededUnit(variant + 7) - 0.5) * 1.15;
  const turn = seededUnit(variant + 13) * Math.PI * 2;
  const axisAngle = seededUnit(variant + 19) * Math.PI * 2;
  const axisZ = (seededUnit(variant + 29) - 0.5) * 0.42;
  const phase = seededUnit(variant + 37) * Math.PI * 2;

  const qx = axisAngleQuaternion(1, 0, 0, tiltX);
  const qy = axisAngleQuaternion(0, 1, 0, tiltY);
  const qz = axisAngleQuaternion(0, 0, 1, turn);
  const phaseRotation = axisAngleQuaternion(
    Math.cos(axisAngle),
    Math.sin(axisAngle),
    axisZ,
    phase,
  );

  return normalizeQuaternion(
    multiplyQuaternion(
      phaseRotation,
      multiplyQuaternion(qz, multiplyQuaternion(qx, qy)),
    ),
  );
}

function createShader(
  gl: WebGL2RenderingContext,
  type: number,
  source: string,
) {
  const shader = gl.createShader(type);
  if (!shader) throw new Error('Unable to create WebGL shader.');

  gl.shaderSource(shader, source);
  gl.compileShader(shader);

  if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
    const message = gl.getShaderInfoLog(shader) ?? 'Unknown shader compilation error.';
    gl.deleteShader(shader);
    throw new Error(message);
  }

  return shader;
}

function createProgram(
  gl: WebGL2RenderingContext,
  vertexSource: string,
  fragmentSource: string,
) {
  const vertexShader = createShader(gl, gl.VERTEX_SHADER, vertexSource);
  const fragmentShader = createShader(gl, gl.FRAGMENT_SHADER, fragmentSource);
  const program = gl.createProgram();
  if (!program) throw new Error('Unable to create WebGL program.');

  gl.attachShader(program, vertexShader);
  gl.attachShader(program, fragmentShader);
  gl.linkProgram(program);
  gl.deleteShader(vertexShader);
  gl.deleteShader(fragmentShader);

  if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
    const message = gl.getProgramInfoLog(program) ?? 'Unknown WebGL link error.';
    gl.deleteProgram(program);
    throw new Error(message);
  }

  return program;
}

const VERTEX_SHADER = `#version 300 es
precision highp float;

layout(location = 0) in vec2 aCorner;
layout(location = 1) in vec3 aCenterRadius;
layout(location = 2) in vec4 aQuaternion;
layout(location = 3) in float aOpacity;

uniform vec2 uResolution;

out vec2 vLocal;
flat out vec4 vQuaternion;
flat out float vOpacity;

void main() {
  vec2 position = aCenterRadius.xy + aCorner * aCenterRadius.z;
  vec2 clip = position / uResolution * 2.0 - 1.0;
  clip.y = -clip.y;

  gl_Position = vec4(clip, 0.0, 1.0);
  vLocal = aCorner;
  vQuaternion = aQuaternion;
  vOpacity = aOpacity;
}
`;

const FRAGMENT_SHADER = `#version 300 es
precision highp float;

in vec2 vLocal;
flat in vec4 vQuaternion;
flat in float vOpacity;

out vec4 outputColor;

const float PI = 3.141592653589793;
const float TAU = 6.283185307179586;

vec3 rotateByInverseQuaternion(vec3 vector, vec4 quaternion) {
  vec3 inverseVector = -quaternion.xyz;
  return vector +
    2.0 * cross(inverseVector, cross(inverseVector, vector) + quaternion.w * vector);
}

vec3 panelColor(float index) {
  if (index < 0.5) return vec3(0.9373, 0.2784, 0.4353);
  if (index < 1.5) return vec3(1.0, 0.8196, 0.4);
  if (index < 2.5) return vec3(0.0235, 0.8392, 0.6275);
  if (index < 3.5) return vec3(0.0706, 0.5412, 0.6980);
  return vec3(1.0);
}

void main() {
  float radiusSquared = dot(vLocal, vLocal);

  if (radiusSquared > 1.0) {
    vec2 shadowPoint = vec2(vLocal.x / 1.04, (vLocal.y - 0.20) / 0.43);
    float shadowDistance = length(shadowPoint);
    float shadowAlpha = (1.0 - smoothstep(0.28, 1.0, shadowDistance)) * 0.17;

    if (shadowAlpha < 0.002) discard;
    outputColor = vec4(0.0196, 0.0784, 0.1412, shadowAlpha * vOpacity);
    return;
  }

  float screenZ = sqrt(max(0.0, 1.0 - radiusSquared));
  vec3 visibleNormal = vec3(vLocal.x, vLocal.y, screenZ);
  vec3 objectNormal = rotateByInverseQuaternion(visibleNormal, normalize(vQuaternion));

  float longitude = atan(objectNormal.z, objectNormal.x);
  float panelPosition = (longitude + PI) / TAU * 5.0;
  float panelIndex = mod(floor(panelPosition), 5.0);
  float panelFraction = fract(panelPosition);
  float seamDistance = min(panelFraction, 1.0 - panelFraction);

  vec3 lightDirection = normalize(vec3(-0.48, -0.55, 0.78));
  vec3 halfVector = normalize(lightDirection + vec3(0.0, 0.0, 1.0));
  float diffuse = max(0.0, dot(visibleNormal, lightDirection));
  float specular = pow(max(0.0, dot(visibleNormal, halfVector)), 34.0);
  float sphericalEdge = pow(screenZ, 0.42);
  float shade = 0.56 + diffuse * 0.30 + sphericalEdge * 0.14;
  float seam = smoothstep(0.0, 0.022, seamDistance);
  shade *= mix(0.76, 1.0, seam);

  vec3 color = panelColor(panelIndex) * shade + vec3(specular * 0.44);

  float rim = smoothstep(0.82, 1.0, sqrt(radiusSquared));
  color = mix(color, vec3(0.0196, 0.0902, 0.1569), rim * 0.23);

  float highlightArc =
    smoothstep(0.24, 0.0, length(vLocal - vec2(-0.30, -0.34))) *
    smoothstep(0.96, 0.54, sqrt(radiusSquared));
  color += vec3(highlightArc * 0.10);

  float antialiasWidth = max(fwidth(radiusSquared) * 1.3, 0.002);
  float alpha = 1.0 - smoothstep(1.0 - antialiasWidth, 1.0, radiusSquared);
  outputColor = vec4(clamp(color, 0.0, 1.0), alpha * vOpacity);
}
`;

export function createSummerBallWebGlRenderer(
  canvas: HTMLCanvasElement,
): SummerBallWebGlRenderer | null {
  const gl = canvas.getContext('webgl2', {
    alpha: true,
    antialias: true,
    depth: false,
    premultipliedAlpha: false,
    powerPreference: 'high-performance',
  });

  if (!gl) return null;

  let program: WebGLProgram;

  try {
    program = createProgram(gl, VERTEX_SHADER, FRAGMENT_SHADER);
  } catch (error) {
    console.warn('Summer ball WebGL renderer could not initialize.', error);
    return null;
  }

  const vertexArray = gl.createVertexArray();
  const cornerBuffer = gl.createBuffer();
  const instanceBuffer = gl.createBuffer();
  const resolutionLocation = gl.getUniformLocation(program, 'uResolution');

  if (!vertexArray || !cornerBuffer || !instanceBuffer || !resolutionLocation) {
    gl.deleteProgram(program);
    gl.deleteVertexArray(vertexArray);
    gl.deleteBuffer(cornerBuffer);
    gl.deleteBuffer(instanceBuffer);
    return null;
  }

  const corners = new Float32Array([
    -QUAD_EXTENT,
    -QUAD_EXTENT,
    QUAD_EXTENT,
    -QUAD_EXTENT,
    -QUAD_EXTENT,
    QUAD_EXTENT,
    -QUAD_EXTENT,
    QUAD_EXTENT,
    QUAD_EXTENT,
    -QUAD_EXTENT,
    QUAD_EXTENT,
    QUAD_EXTENT,
  ]);

  gl.bindVertexArray(vertexArray);

  gl.bindBuffer(gl.ARRAY_BUFFER, cornerBuffer);
  gl.bufferData(gl.ARRAY_BUFFER, corners, gl.STATIC_DRAW);
  gl.enableVertexAttribArray(0);
  gl.vertexAttribPointer(0, 2, gl.FLOAT, false, 0, 0);

  gl.bindBuffer(gl.ARRAY_BUFFER, instanceBuffer);
  gl.enableVertexAttribArray(1);
  gl.vertexAttribPointer(
    1,
    3,
    gl.FLOAT,
    false,
    FLOATS_PER_INSTANCE * Float32Array.BYTES_PER_ELEMENT,
    0,
  );
  gl.vertexAttribDivisor(1, 1);

  gl.enableVertexAttribArray(2);
  gl.vertexAttribPointer(
    2,
    4,
    gl.FLOAT,
    false,
    FLOATS_PER_INSTANCE * Float32Array.BYTES_PER_ELEMENT,
    3 * Float32Array.BYTES_PER_ELEMENT,
  );
  gl.vertexAttribDivisor(2, 1);

  gl.enableVertexAttribArray(3);
  gl.vertexAttribPointer(
    3,
    1,
    gl.FLOAT,
    false,
    FLOATS_PER_INSTANCE * Float32Array.BYTES_PER_ELEMENT,
    7 * Float32Array.BYTES_PER_ELEMENT,
  );
  gl.vertexAttribDivisor(3, 1);

  gl.bindVertexArray(null);
  gl.bindBuffer(gl.ARRAY_BUFFER, null);

  gl.disable(gl.DEPTH_TEST);
  gl.enable(gl.BLEND);
  gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);

  let allocatedInstances = 0;

  const ensureCapacity = (instanceCount: number) => {
    if (instanceCount <= allocatedInstances) return;

    allocatedInstances = Math.max(instanceCount, allocatedInstances * 2, 256);
    gl.bindBuffer(gl.ARRAY_BUFFER, instanceBuffer);
    gl.bufferData(
      gl.ARRAY_BUFFER,
      allocatedInstances * FLOATS_PER_INSTANCE * Float32Array.BYTES_PER_ELEMENT,
      gl.DYNAMIC_DRAW,
    );
  };

  return {
    resize(width, height, pixelRatio) {
      const physicalWidth = Math.max(1, Math.round(width * pixelRatio));
      const physicalHeight = Math.max(1, Math.round(height * pixelRatio));
      if (canvas.width !== physicalWidth) canvas.width = physicalWidth;
      if (canvas.height !== physicalHeight) canvas.height = physicalHeight;
      canvas.style.width = `${width}px`;
      canvas.style.height = `${height}px`;
      gl.viewport(0, 0, physicalWidth, physicalHeight);
    },

    draw(instanceData, instanceCount, width, height) {
      ensureCapacity(instanceCount);
      gl.clearColor(0, 0, 0, 0);
      gl.clear(gl.COLOR_BUFFER_BIT);

      if (instanceCount <= 0) return;

      gl.useProgram(program);
      gl.uniform2f(resolutionLocation, width, height);
      gl.bindVertexArray(vertexArray);
      gl.bindBuffer(gl.ARRAY_BUFFER, instanceBuffer);
      gl.bufferSubData(
        gl.ARRAY_BUFFER,
        0,
        instanceData.subarray(0, instanceCount * FLOATS_PER_INSTANCE),
      );
      gl.drawArraysInstanced(gl.TRIANGLES, 0, 6, instanceCount);
      gl.bindVertexArray(null);
    },

    clear() {
      gl.clearColor(0, 0, 0, 0);
      gl.clear(gl.COLOR_BUFFER_BIT);
    },

    dispose() {
      gl.deleteProgram(program);
      gl.deleteVertexArray(vertexArray);
      gl.deleteBuffer(cornerBuffer);
      gl.deleteBuffer(instanceBuffer);
    },
  };
}
