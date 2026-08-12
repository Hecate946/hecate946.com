import * as THREE from 'three';
import { PAGE_ASPECT, preloadBookImages, renderBookFace } from './book-texture';
import type {
  BookClosedSide,
  BookLink,
  BookMotion,
  BookSpread,
  Direction,
  PageFace,
  PageHitRegion,
  PageSide,
} from './book-types';

const PAGE_WIDTH = 1;
const PAGE_HEIGHT = PAGE_ASPECT;
const COVER_Z = -0.055;
const BASE_PAGE_Z = 0.004;
const BINDING_Z = BASE_PAGE_Z + 0.025;
const LEAF_THICKNESS = 0.0065;
const PAGE_WIDTH_SEGMENTS = 72;
const PAGE_HEIGHT_SEGMENTS = 18;
const CAMERA_FOV = 19.5;
// Keep the volume intentionally compact inside the actual wall area. The lower
// fill also leaves generous room for the free edge to rise during a turn.
const BOOK_FRAME_FILL_Y = 0.60;
const BOOK_FRAME_FILL_X = 0.76;
const BOOK_FRAME_HEIGHT = PAGE_HEIGHT * 1.035;
const BOOK_FRAME_WIDTH = PAGE_WIDTH * 2.08;

type CachedFace = {
  texture: THREE.CanvasTexture;
  hitRegions: PageHitRegion[];
};

export type BookSurfaceHit =
  | {
      target: 'page';
      side: PageSide;
      uv: { x: number; y: number };
    }
  | {
      target: 'cover';
      side: 'front' | 'back';
      uv: { x: number; y: number };
    };

const clamp01 = (value: number) => Math.min(1, Math.max(0, value));
const smootherstep = (value: number) => {
  const x = clamp01(value);
  return x * x * x * (x * (x * 6 - 15) + 10);
};
const smoothstep = (edge0: number, edge1: number, value: number) => {
  const x = clamp01((value - edge0) / Math.max(0.0001, edge1 - edge0));
  return x * x * (3 - 2 * x);
};

export class BookScene {
  private renderer: THREE.WebGLRenderer;
  private scene = new THREE.Scene();
  private camera = new THREE.PerspectiveCamera(CAMERA_FOV, 1.55, 0.1, 30);
  private group = new THREE.Group();
  private raycaster = new THREE.Raycaster();
  private pointerNdc = new THREE.Vector2();

  private currentSpread = 0;
  private closedSide: BookClosedSide = null;
  private motion: BookMotion | null = null;
  private turnProgress = 0;
  private textureWidth = 0;
  private textureGeneration = 0;
  private disposed = false;

  private faceCache = new Map<string, CachedFace>();
  private resizeObserver: ResizeObserver | null = null;
  private themeObserver: MutationObserver | null = null;

  private leftPageGeometry = new THREE.PlaneGeometry(
    PAGE_WIDTH,
    PAGE_HEIGHT,
    PAGE_WIDTH_SEGMENTS,
    PAGE_HEIGHT_SEGMENTS,
  );
  private rightPageGeometry = new THREE.PlaneGeometry(
    PAGE_WIDTH,
    PAGE_HEIGHT,
    PAGE_WIDTH_SEGMENTS,
    PAGE_HEIGHT_SEGMENTS,
  );
  private turnFrontGeometry = new THREE.PlaneGeometry(
    PAGE_WIDTH,
    PAGE_HEIGHT,
    PAGE_WIDTH_SEGMENTS,
    PAGE_HEIGHT_SEGMENTS,
  );
  private turnBackGeometry = new THREE.PlaneGeometry(
    PAGE_WIDTH,
    PAGE_HEIGHT,
    PAGE_WIDTH_SEGMENTS,
    PAGE_HEIGHT_SEGMENTS,
  );
  private turnEdgeGeometry = new THREE.BufferGeometry();

  private leftPageMaterial = new THREE.MeshBasicMaterial({
    color: 0xffffff,
    side: THREE.DoubleSide,
    vertexColors: true,
    toneMapped: false,
  });
  private rightPageMaterial = this.leftPageMaterial.clone();
  private turnFrontMaterial = new THREE.MeshBasicMaterial({
    color: 0xffffff,
    side: THREE.FrontSide,
    vertexColors: true,
    toneMapped: false,
    polygonOffset: true,
    polygonOffsetFactor: -1,
    polygonOffsetUnits: -1,
  });
  private turnBackMaterial = new THREE.MeshBasicMaterial({
    color: 0xffffff,
    side: THREE.BackSide,
    vertexColors: true,
    toneMapped: false,
    polygonOffset: true,
    polygonOffsetFactor: -1,
    polygonOffsetUnits: -1,
  });
  private coverMaterial = new THREE.MeshStandardMaterial({
    color: 0x24120e,
    roughness: 0.94,
    metalness: 0.01,
  });
  private coverHitMaterial = new THREE.MeshBasicMaterial({
    transparent: true,
    opacity: 0,
    side: THREE.DoubleSide,
    depthTest: false,
    depthWrite: false,
    colorWrite: false,
  });
  private pageBlockMaterial = new THREE.MeshStandardMaterial({
    color: 0xffffff,
    roughness: 0.96,
    metalness: 0,
  });
  private spineMaterial = new THREE.MeshStandardMaterial({
    color: 0x180b08,
    roughness: 0.96,
    metalness: 0,
  });
  private turnEdgeMaterial = new THREE.LineBasicMaterial({
    color: 0xad916d,
    transparent: true,
    opacity: 0.72,
    toneMapped: false,
  });

  private leftPageMesh = new THREE.Mesh(this.leftPageGeometry, this.leftPageMaterial);
  private rightPageMesh = new THREE.Mesh(this.rightPageGeometry, this.rightPageMaterial);
  private turnFrontMesh = new THREE.Mesh(this.turnFrontGeometry, this.turnFrontMaterial);
  private turnBackMesh = new THREE.Mesh(this.turnBackGeometry, this.turnBackMaterial);
  private turnEdgeLine = new THREE.Line(this.turnEdgeGeometry, this.turnEdgeMaterial);

  private leftBlockMesh = new THREE.Mesh(new THREE.BoxGeometry(1, 1, 1), this.pageBlockMaterial);
  private rightBlockMesh = new THREE.Mesh(new THREE.BoxGeometry(1, 1, 1), this.pageBlockMaterial);
  private leftCoverMesh = new THREE.Mesh(
    new THREE.BoxGeometry(PAGE_WIDTH * 1.018, PAGE_HEIGHT * 1.024, 0.044),
    this.coverMaterial,
  );
  private rightCoverMesh = new THREE.Mesh(
    new THREE.BoxGeometry(PAGE_WIDTH * 1.018, PAGE_HEIGHT * 1.024, 0.044),
    this.coverMaterial,
  );
  private spineMesh = new THREE.Mesh(
    new THREE.BoxGeometry(0.054, PAGE_HEIGHT * 1.018, 0.050),
    this.spineMaterial,
  );
  // A transparent, double-sided copy of the active cover geometry is used only
  // for hit testing when the book is closed. This makes the entire visible
  // cover reliably clickable/draggable regardless of face orientation.
  private coverHitMesh = new THREE.Mesh(this.turnFrontGeometry, this.coverHitMaterial);

  private edgeTexture: THREE.CanvasTexture | null = null;
  private leatherTexture: THREE.CanvasTexture | null = null;

  constructor(
    private readonly host: HTMLElement,
    private readonly canvas: HTMLCanvasElement,
    private readonly spreads: BookSpread[],
  ) {
    this.renderer = new THREE.WebGLRenderer({
      canvas,
      alpha: true,
      antialias: true,
      powerPreference: 'high-performance',
      preserveDrawingBuffer: false,
    });
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 1.02;
    this.renderer.setClearColor(0x000000, 0);

    this.leftPageGeometry.translate(PAGE_WIDTH / 2, 0, 0);
    this.rightPageGeometry.translate(PAGE_WIDTH / 2, 0, 0);
    this.turnFrontGeometry.translate(PAGE_WIDTH / 2, 0, 0);
    this.turnBackGeometry.translate(PAGE_WIDTH / 2, 0, 0);
    const backUv = this.turnBackGeometry.attributes.uv as THREE.BufferAttribute;
    for (let index = 0; index < backUv.count; index += 1) backUv.setX(index, 1 - backUv.getX(index));
    backUv.needsUpdate = true;

    this.turnEdgeGeometry.setAttribute(
      'position',
      new THREE.BufferAttribute(new Float32Array((PAGE_HEIGHT_SEGMENTS + 1) * 3), 3),
    );

    this.configureScene();
  }

  async initialise() {
    if (!this.spreads.length) return;
    this.resize();
    preloadBookImages(this.spreads.flatMap((spread) => (spread.visual ? [spread.visual.src] : [])));
    await this.renderAllFaces(true);
    if (this.disposed) return;
    this.applyState();

    this.resizeObserver = new ResizeObserver(() => this.resize());
    this.resizeObserver.observe(this.host);
    window.addEventListener('resize', this.resize);

    this.themeObserver = new MutationObserver(() => {
      this.updateBookMaterials();
      void this.renderAllFaces(true);
    });
    this.themeObserver.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['data-theme'],
    });
  }

  setState(
    currentSpread: number,
    closedSide: BookClosedSide,
    motion: BookMotion | null,
    turnProgress: number,
  ) {
    this.currentSpread = currentSpread;
    this.closedSide = closedSide;
    this.motion = motion;
    this.turnProgress = clamp01(turnProgress);
    this.applyState();
  }

  pickSurface(clientX: number, clientY: number): BookSurfaceHit | null {
    const bounds = this.canvas.getBoundingClientRect();
    if (!bounds.width || !bounds.height) return null;

    this.pointerNdc.set(
      ((clientX - bounds.left) / bounds.width) * 2 - 1,
      -((clientY - bounds.top) / bounds.height) * 2 + 1,
    );
    this.raycaster.setFromCamera(this.pointerNdc, this.camera);

    if (this.closedSide && !this.motion) {
      const hit = this.raycaster.intersectObject(this.coverHitMesh, false)[0];
      if (!hit?.uv) return null;
      return {
        target: 'cover',
        side: this.closedSide,
        uv: { x: hit.uv.x, y: 1 - hit.uv.y },
      };
    }

    const hit = this.raycaster.intersectObjects([this.leftPageMesh, this.rightPageMesh], false)[0];
    if (!hit?.uv) return null;

    return {
      target: 'page',
      side: hit.object === this.rightPageMesh ? 'right' : 'left',
      uv: { x: hit.uv.x, y: 1 - hit.uv.y },
    };
  }

  linkAtCurrentRight(uv: { x: number; y: number }): BookLink | null {
    const face = this.contentFace(this.currentSpread);
    const entry = this.faceCache.get(this.faceKey(face));
    if (!entry) return null;

    return (
      entry.hitRegions.find(
        (region) =>
          uv.x >= region.x &&
          uv.x <= region.x + region.width &&
          uv.y >= region.y &&
          uv.y <= region.y + region.height,
      )?.link ?? null
    );
  }

  dispose() {
    this.disposed = true;
    this.textureGeneration += 1;
    this.resizeObserver?.disconnect();
    this.themeObserver?.disconnect();
    window.removeEventListener('resize', this.resize);
    this.disposeFaceCache();

    this.leatherTexture?.dispose();
    this.edgeTexture?.dispose();
    this.leftPageGeometry.dispose();
    this.rightPageGeometry.dispose();
    this.turnFrontGeometry.dispose();
    this.turnBackGeometry.dispose();
    this.turnEdgeGeometry.dispose();
    this.leftPageMaterial.dispose();
    this.rightPageMaterial.dispose();
    this.turnFrontMaterial.dispose();
    this.turnBackMaterial.dispose();
    this.turnEdgeMaterial.dispose();
    this.coverMaterial.dispose();
    this.coverHitMaterial.dispose();
    this.pageBlockMaterial.dispose();
    this.spineMaterial.dispose();

    for (const mesh of [
      this.leftBlockMesh,
      this.rightBlockMesh,
      this.leftCoverMesh,
      this.rightCoverMesh,
      this.spineMesh,
    ]) {
      mesh.geometry.dispose();
    }
    this.renderer.dispose();
  }

  private configureScene() {
    this.camera.position.set(0, 0, 5.5);
    this.camera.lookAt(0, 0, 0);
    this.scene.add(this.group);

    const hemisphere = new THREE.HemisphereLight(0xfff4dc, 0x26110a, 1.45);
    const key = new THREE.DirectionalLight(0xfff0d5, 1.05);
    key.position.set(-2.8, 3.4, 4.2);
    const fill = new THREE.DirectionalLight(0xd8c4a3, 0.28);
    fill.position.set(2.6, -1.2, 3.4);
    this.scene.add(hemisphere, key, fill);

    this.leftCoverMesh.position.set(-PAGE_WIDTH / 2 - 0.007, -0.003, COVER_Z - 0.020);
    this.rightCoverMesh.position.set(PAGE_WIDTH / 2 + 0.007, -0.003, COVER_Z - 0.020);
    this.spineMesh.position.set(0, -0.002, COVER_Z - 0.010);

    this.leftPageMesh.renderOrder = 8;
    this.rightPageMesh.renderOrder = 8;
    this.turnFrontMesh.renderOrder = 16;
    this.turnBackMesh.renderOrder = 16;
    this.turnEdgeLine.renderOrder = 17;
    this.turnFrontMesh.visible = false;
    this.turnBackMesh.visible = false;
    this.turnEdgeLine.visible = false;
    this.coverHitMesh.visible = false;
    this.coverHitMesh.scale.set(1.035, 1.035, 1);

    this.group.add(
      this.leftCoverMesh,
      this.rightCoverMesh,
      this.spineMesh,
      this.leftBlockMesh,
      this.rightBlockMesh,
      this.leftPageMesh,
      this.rightPageMesh,
      this.turnFrontMesh,
      this.turnBackMesh,
      this.turnEdgeLine,
      this.coverHitMesh,
    );

    this.updateBookMaterials();
  }

  private visualFace(index: number): PageFace {
    return { kind: 'visual', spread: this.spreads[index], pageNumber: index * 2 + 1 };
  }

  private contentFace(index: number): PageFace {
    return { kind: 'content', spread: this.spreads[index], pageNumber: index * 2 + 2 };
  }

  private coverFace(side: 'front' | 'back'): PageFace {
    return side === 'front'
      ? {
          kind: 'cover',
          side,
          eyebrow: this.spreads[0]?.eyebrow ?? 'ABOUT',
          title: this.spreads[0]?.title ?? 'About',
        }
      : { kind: 'cover', side };
  }

  private faceKey(face: PageFace) {
    return face.kind === 'cover'
      ? `cover:${face.side}`
      : `${face.kind}:${face.spread.id}:${face.pageNumber}`;
  }

  private leftTopZ(spreadIndex: number) {
    return BASE_PAGE_Z + spreadIndex * LEAF_THICKNESS;
  }

  private rightTopZ(spreadIndex: number) {
    return BASE_PAGE_Z + (this.spreads.length - 1 - spreadIndex) * LEAF_THICKNESS;
  }

  private getCssColor(name: string, fallback: string) {
    return getComputedStyle(this.host).getPropertyValue(name).trim() || fallback;
  }

  private createNoiseTexture(
    width: number,
    height: number,
    base: string,
    line: string,
    lineAlpha: number,
  ) {
    const canvas = document.createElement('canvas');
    canvas.width = width;
    canvas.height = height;
    const context = canvas.getContext('2d');
    if (!context) return null;

    context.fillStyle = base;
    context.fillRect(0, 0, width, height);
    context.strokeStyle = line;
    context.globalAlpha = lineAlpha;
    context.lineWidth = 1;
    for (let y = 4; y < height; y += 5) {
      context.beginPath();
      context.moveTo(0, y + ((y * 17) % 3) * 0.18);
      context.lineTo(width, y);
      context.stroke();
    }

    context.globalAlpha = 0.065;
    let seed = 946;
    for (let index = 0; index < Math.floor(width * height * 0.018); index += 1) {
      seed = (seed * 1664525 + 1013904223) >>> 0;
      const x = (seed / 4294967296) * width;
      seed = (seed * 1664525 + 1013904223) >>> 0;
      const y = (seed / 4294967296) * height;
      context.fillStyle = line;
      context.fillRect(x, y, 1, 1);
    }

    const texture = new THREE.CanvasTexture(canvas);
    texture.colorSpace = THREE.SRGBColorSpace;
    texture.wrapS = THREE.RepeatWrapping;
    texture.wrapT = THREE.RepeatWrapping;
    texture.needsUpdate = true;
    return texture;
  }

  private updateBookMaterials() {
    const leather = this.getCssColor('--book-leather', '#180b08');
    const leatherLight = this.getCssColor('--book-leather-light', '#2d1710');
    const paper = this.getCssColor('--paper-warm', '#e3cfaa');
    const paperEdge = this.getCssColor('--paper-edge', '#ad916d');

    this.leatherTexture?.dispose();
    this.edgeTexture?.dispose();
    this.leatherTexture = this.createNoiseTexture(96, 96, leatherLight, '#120806', 0.18);
    this.edgeTexture = this.createNoiseTexture(96, 160, paper, paperEdge, 0.24);

    this.coverMaterial.color.setStyle(leather);
    this.coverMaterial.map = this.leatherTexture;
    this.coverMaterial.needsUpdate = true;
    this.pageBlockMaterial.color.setStyle('#ffffff');
    this.pageBlockMaterial.map = this.edgeTexture;
    this.pageBlockMaterial.needsUpdate = true;
    this.spineMaterial.color.setStyle(leather);
    this.spineMaterial.map = this.leatherTexture;
    this.spineMaterial.needsUpdate = true;
    this.turnEdgeMaterial.color.setStyle(paperEdge);
  }

  private chooseTextureWidth() {
    const bounds = this.host.getBoundingClientRect();
    const dpr = Math.min(window.devicePixelRatio || 1, 2.5);
    const desired = bounds.width * 0.5 * dpr * 1.45;
    const tiers = [1024, 1280, 1536, 1792, 2048];
    const maxTextureSize = this.renderer.capabilities.maxTextureSize || 2048;
    return Math.min(tiers.find((tier) => tier >= desired) ?? 2048, maxTextureSize);
  }

  private async buildTexture(face: PageFace, width: number): Promise<CachedFace> {
    const rendered = await renderBookFace(face, this.host, width);
    const texture = new THREE.CanvasTexture(rendered.canvas);
    texture.colorSpace = THREE.SRGBColorSpace;
    texture.anisotropy = Math.min(16, this.renderer.capabilities.getMaxAnisotropy());
    texture.minFilter = THREE.LinearMipmapLinearFilter;
    texture.magFilter = THREE.LinearFilter;
    texture.generateMipmaps = true;
    texture.needsUpdate = true;
    return { texture, hitRegions: rendered.hitRegions };
  }

  private async renderAllFaces(force = false) {
    const width = this.chooseTextureWidth();
    if (!force && width === this.textureWidth && this.faceCache.size === this.spreads.length * 2 + 2) return;

    const generation = ++this.textureGeneration;
    this.textureWidth = width;
    preloadBookImages(this.spreads.flatMap((spread) => (spread.visual ? [spread.visual.src] : [])));
    await document.fonts?.ready;

    const faces: PageFace[] = [
      this.coverFace('front'),
      this.coverFace('back'),
      ...this.spreads.flatMap((_, index) => [this.visualFace(index), this.contentFace(index)]),
    ];
    const built = await Promise.all(
      faces.map(async (face) => [this.faceKey(face), await this.buildTexture(face, width)] as const),
    );

    if (this.disposed || generation !== this.textureGeneration) {
      for (const [, entry] of built) entry.texture.dispose();
      return;
    }

    this.disposeFaceCache();
    for (const [key, entry] of built) this.faceCache.set(key, entry);
    this.applyState();
  }

  private disposeFaceCache() {
    for (const { texture } of this.faceCache.values()) texture.dispose();
    this.faceCache.clear();
  }

  private setMaterialFace(material: THREE.MeshBasicMaterial, face: PageFace) {
    material.map = this.faceCache.get(this.faceKey(face))?.texture ?? null;
    material.needsUpdate = true;
  }

  private restingSurfaceZ(distanceFromSpine: number, vertical: number, stackTopZ: number) {
    // Every leaf meets at one stable binding height. The outer half then relaxes
    // onto whichever page stack is currently thicker, so the center of the book
    // never jumps up and down as pages migrate from right to left.
    const stackBlend = smoothstep(0.02, 0.72, distanceFromSpine);
    const stackSurface = stackTopZ + 0.0010;
    const base = BINDING_Z + (stackSurface - BINDING_Z) * stackBlend;
    const crown =
      0.0065 *
      Math.sin(Math.PI * distanceFromSpine) *
      (0.76 + 0.24 * (1 - vertical * vertical));
    return base + crown;
  }

  private setStaticPageGeometry(geometry: THREE.PlaneGeometry, side: PageSide, topZ: number) {
    const position = geometry.attributes.position as THREE.BufferAttribute;
    const uv = geometry.attributes.uv as THREE.BufferAttribute;
    let color = geometry.getAttribute('color') as THREE.BufferAttribute | undefined;
    if (!color) {
      color = new THREE.BufferAttribute(new Float32Array(position.count * 3), 3);
      geometry.setAttribute('color', color);
    }

    for (let index = 0; index < position.count; index += 1) {
      const u = uv.getX(index);
      const v = uv.getY(index);
      const vertical = (v - 0.5) * 2;
      const distance = side === 'right' ? u : 1 - u;
      const x = side === 'right' ? distance * PAGE_WIDTH : -distance * PAGE_WIDTH;
      const y = (v - 0.5) * PAGE_HEIGHT * (1 - 0.004 * distance);
      const z = this.restingSurfaceZ(distance, vertical, topZ);
      position.setXYZ(index, x, y, z);

      const factor = 0.995 + 0.010 * (1 - distance) + 0.004 * Math.sin(Math.PI * distance);
      color.setXYZ(index, factor, factor, factor);
    }

    position.needsUpdate = true;
    color.needsUpdate = true;
    geometry.computeBoundingSphere();
  }

  private deformTurningLeaf(
    amount: number,
    direction: Direction,
    startZ: number,
    endZ: number,
  ) {
    const frontPosition = this.turnFrontGeometry.attributes.position as THREE.BufferAttribute;
    const backPosition = this.turnBackGeometry.attributes.position as THREE.BufferAttribute;
    const uv = this.turnFrontGeometry.attributes.uv as THREE.BufferAttribute;
    let frontColor = this.turnFrontGeometry.getAttribute('color') as THREE.BufferAttribute | undefined;
    let backColor = this.turnBackGeometry.getAttribute('color') as THREE.BufferAttribute | undefined;

    if (!frontColor) {
      frontColor = new THREE.BufferAttribute(new Float32Array(frontPosition.count * 3), 3);
      this.turnFrontGeometry.setAttribute('color', frontColor);
    }
    if (!backColor) {
      backColor = new THREE.BufferAttribute(new Float32Array(backPosition.count * 3), 3);
      this.turnBackGeometry.setAttribute('color', backColor);
    }

    const actual = clamp01(amount);
    const canonical = direction === 1 ? actual : 1 - actual;
    const turnAngle = Math.PI * canonical;
    const curlWindow = Math.sin(Math.PI * canonical);
    const curlEnvelope = Math.pow(Math.max(0, curlWindow), 0.82);
    const stackTopZ = startZ + (endZ - startZ) * smootherstep(actual);
    const curlAmplitude = 1.04 * curlEnvelope;

    for (let index = 0; index < frontPosition.count; index += 1) {
      const u = uv.getX(index);
      const v = uv.getY(index);
      const vertical = (v - 0.5) * 2;
      const baseY = (v - 0.5) * PAGE_HEIGHT;
      const steps = 48;
      const ds = (u * PAGE_WIDTH) / steps;
      let x = 0;
      let z = 0;

      for (let step = 0; step < steps; step += 1) {
        const local = ((step + 0.5) / steps) * u;
        const roll = smoothstep(0.02, 0.98, local);
        const hingeLag = -0.30 * curlAmplitude * Math.pow(1 - roll, 1.3);
        const rollingCurl = 0.58 * curlAmplitude * (roll - 0.44);
        const freeEdgeLead = 0.26 * curlAmplitude * Math.pow(roll, 2.4);
        const cornerTwist = 0.040 * curlEnvelope * vertical * Math.pow(roll, 2.2);
        const tangent = turnAngle + hingeLag + rollingCurl + freeEdgeLead + cornerTwist;
        x += Math.cos(tangent) * ds;
        z += Math.sin(tangent) * ds;
      }

      const edge = Math.pow(u, 1.7);
      const belly = Math.sin(Math.PI * u);
      const verticalPinch = 1 - 0.042 * curlEnvelope * edge;
      const topBottomCurl = -vertical * 0.014 * curlEnvelope * edge;
      const centerCrown = 0.016 * curlEnvelope * belly * (1 - vertical * vertical);
      const y = baseY * verticalPinch + topBottomCurl + centerCrown;

      z += this.restingSurfaceZ(u, vertical, stackTopZ);
      z += 0.018 * curlEnvelope * belly + 0.020 * curlEnvelope * edge;

      frontPosition.setXYZ(index, x, y, z);
      backPosition.setXYZ(index, x, y, z);
    }

    frontPosition.needsUpdate = true;
    backPosition.needsUpdate = true;
    this.turnFrontGeometry.computeVertexNormals();
    this.turnBackGeometry.computeVertexNormals();

    const frontNormal = this.turnFrontGeometry.attributes.normal as THREE.BufferAttribute;
    for (let index = 0; index < frontPosition.count; index += 1) {
      const u = uv.getX(index);
      const facing = Math.abs(frontNormal.getZ(index));
      const belly = Math.sin(Math.PI * u);
      const restingFactor = 0.995 + 0.010 * (1 - u) + 0.004 * belly;
      const curvatureTint =
        1 + curlEnvelope * (0.014 * (facing - 0.72) + 0.008 * belly);
      const factor = restingFactor * curvatureTint;
      frontColor.setXYZ(index, factor, factor, factor);
      backColor.setXYZ(index, factor * 0.998, factor * 0.998, factor * 0.998);
    }
    frontColor.needsUpdate = true;
    backColor.needsUpdate = true;

    const edgePositions = this.turnEdgeGeometry.attributes.position as THREE.BufferAttribute;
    for (let row = 0; row <= PAGE_HEIGHT_SEGMENTS; row += 1) {
      const vertexIndex = row * (PAGE_WIDTH_SEGMENTS + 1) + PAGE_WIDTH_SEGMENTS;
      edgePositions.setXYZ(
        row,
        frontPosition.getX(vertexIndex),
        frontPosition.getY(vertexIndex),
        frontPosition.getZ(vertexIndex) + 0.0006,
      );
    }
    edgePositions.needsUpdate = true;
    this.turnEdgeGeometry.computeBoundingSphere();
  }

  private updateBlockMesh(mesh: THREE.Mesh, side: PageSide, topZ: number) {
    const depth = Math.max(0.024, topZ - COVER_Z);
    mesh.scale.set(PAGE_WIDTH * 1.002, PAGE_HEIGHT * 1.006, depth);
    mesh.position.set(side === 'left' ? -PAGE_WIDTH / 2 : PAGE_WIDTH / 2, 0, COVER_Z + depth / 2);
  }

  private sceneFaces(direction: Direction | 0) {
    if (!direction) {
      return {
        left: this.visualFace(this.currentSpread),
        right: this.contentFace(this.currentSpread),
        leftZ: this.leftTopZ(this.currentSpread),
        rightZ: this.rightTopZ(this.currentSpread),
      };
    }

    if (direction === 1) {
      return {
        left: this.visualFace(this.currentSpread),
        right: this.contentFace(Math.min(this.spreads.length - 1, this.currentSpread + 1)),
        leftZ: this.leftTopZ(this.currentSpread),
        rightZ: this.rightTopZ(this.currentSpread) - LEAF_THICKNESS,
      };
    }

    return {
      left: this.visualFace(Math.max(0, this.currentSpread - 1)),
      right: this.contentFace(this.currentSpread),
      leftZ: this.leftTopZ(this.currentSpread) - LEAF_THICKNESS,
      rightZ: this.rightTopZ(this.currentSpread),
    };
  }

  private setOpenVisibility() {
    this.coverHitMesh.visible = false;
    this.leftPageMesh.visible = true;
    this.rightPageMesh.visible = true;
    this.leftBlockMesh.visible = true;
    this.rightBlockMesh.visible = true;
    this.leftCoverMesh.visible = true;
    this.rightCoverMesh.visible = true;
    this.spineMesh.visible = true;
  }

  private deformCoverLeaf(
    closureAmount: number,
    side: 'front' | 'back',
    startZ: number,
    endZ: number,
  ) {
    const direction: Direction = side === 'front' ? -1 : 1;
    const actual = clamp01(closureAmount);
    const canonical = direction === 1 ? actual : 1 - actual;
    const angle = Math.PI * canonical;
    const lift = Math.sin(Math.PI * actual);
    const stackZ = startZ + (endZ - startZ) * smootherstep(actual);
    const frontPosition = this.turnFrontGeometry.attributes.position as THREE.BufferAttribute;
    const backPosition = this.turnBackGeometry.attributes.position as THREE.BufferAttribute;
    const uv = this.turnFrontGeometry.attributes.uv as THREE.BufferAttribute;
    let frontColor = this.turnFrontGeometry.getAttribute('color') as THREE.BufferAttribute | undefined;
    let backColor = this.turnBackGeometry.getAttribute('color') as THREE.BufferAttribute | undefined;

    if (!frontColor) {
      frontColor = new THREE.BufferAttribute(new Float32Array(frontPosition.count * 3), 3);
      this.turnFrontGeometry.setAttribute('color', frontColor);
    }
    if (!backColor) {
      backColor = new THREE.BufferAttribute(new Float32Array(backPosition.count * 3), 3);
      this.turnBackGeometry.setAttribute('color', backColor);
    }

    for (let index = 0; index < frontPosition.count; index += 1) {
      const u = uv.getX(index);
      const v = uv.getY(index);
      const vertical = (v - 0.5) * 2;
      const distance = u * PAGE_WIDTH;
      // A hardcover is mostly rigid, but a tiny shoulder flex keeps the hinge from
      // reading like a mechanical door when it takes off from the page block.
      const shoulder = 0.035 * lift * Math.sin(Math.PI * u);
      const localAngle = angle + (direction === 1 ? shoulder : -shoulder);
      const x = Math.cos(localAngle) * distance;
      const y = (v - 0.5) * PAGE_HEIGHT * (1 - 0.003 * lift * u);
      const z = Math.sin(localAngle) * distance + this.restingSurfaceZ(u, vertical, stackZ);

      frontPosition.setXYZ(index, x, y, z);
      backPosition.setXYZ(index, x, y, z);
      const factor = 0.992 + 0.008 * Math.abs(Math.cos(localAngle));
      frontColor.setXYZ(index, factor, factor, factor);
      backColor.setXYZ(index, factor, factor, factor);
    }

    frontPosition.needsUpdate = true;
    backPosition.needsUpdate = true;
    frontColor.needsUpdate = true;
    backColor.needsUpdate = true;
    this.turnFrontGeometry.computeVertexNormals();
    this.turnBackGeometry.computeVertexNormals();

    const edgePositions = this.turnEdgeGeometry.attributes.position as THREE.BufferAttribute;
    for (let row = 0; row <= PAGE_HEIGHT_SEGMENTS; row += 1) {
      const vertexIndex = row * (PAGE_WIDTH_SEGMENTS + 1) + PAGE_WIDTH_SEGMENTS;
      edgePositions.setXYZ(
        row,
        frontPosition.getX(vertexIndex),
        frontPosition.getY(vertexIndex),
        frontPosition.getZ(vertexIndex) + 0.001,
      );
    }
    edgePositions.needsUpdate = true;
    this.turnEdgeGeometry.computeBoundingSphere();
  }

  private applyPageState(direction: Direction | 0, progress: number) {
    this.group.position.x = 0;
    this.setOpenVisibility();
    const state = this.sceneFaces(direction);
    this.setMaterialFace(this.leftPageMaterial, state.left);
    this.setMaterialFace(this.rightPageMaterial, state.right);
    this.setStaticPageGeometry(this.leftPageGeometry, 'left', state.leftZ);
    this.setStaticPageGeometry(this.rightPageGeometry, 'right', state.rightZ);
    this.updateBlockMesh(this.leftBlockMesh, 'left', state.leftZ);
    this.updateBlockMesh(this.rightBlockMesh, 'right', state.rightZ);

    const active = Boolean(direction);
    this.turnFrontMesh.visible = active;
    this.turnBackMesh.visible = active;
    this.turnEdgeLine.visible = active;
    this.turnEdgeMaterial.color.setStyle(this.getCssColor('--paper-edge', '#ad916d'));
    this.turnEdgeMaterial.opacity = 0.72;

    if (!direction) return;

    const front =
      direction === 1
        ? this.contentFace(this.currentSpread)
        : this.contentFace(Math.max(0, this.currentSpread - 1));
    const back =
      direction === 1
        ? this.visualFace(Math.min(this.spreads.length - 1, this.currentSpread + 1))
        : this.visualFace(this.currentSpread);
    this.setMaterialFace(this.turnFrontMaterial, front);
    this.setMaterialFace(this.turnBackMaterial, back);

    const startZ = direction === 1 ? this.rightTopZ(this.currentSpread) : this.leftTopZ(this.currentSpread);
    const endZ =
      direction === 1
        ? this.leftTopZ(this.currentSpread) + LEAF_THICKNESS
        : this.rightTopZ(this.currentSpread) + LEAF_THICKNESS;
    this.deformTurningLeaf(progress, direction, startZ, endZ);
  }

  private applyCoverState(side: 'front' | 'back', closureAmount: number) {
    const amount = clamp01(closureAmount);
    const isFront = side === 'front';
    const index = isFront ? 0 : this.spreads.length - 1;
    this.setOpenVisibility();
    this.group.position.x = (isFront ? -0.5 : 0.5) * amount * PAGE_WIDTH;

    if (isFront) {
      this.leftPageMesh.visible = false;
      this.leftBlockMesh.visible = false;
      this.leftCoverMesh.visible = false;
      this.setMaterialFace(this.rightPageMaterial, this.contentFace(0));
      this.setStaticPageGeometry(this.rightPageGeometry, 'right', this.rightTopZ(0));
      this.updateBlockMesh(this.rightBlockMesh, 'right', this.rightTopZ(0));
      this.setMaterialFace(this.turnFrontMaterial, this.coverFace('front'));
      this.setMaterialFace(this.turnBackMaterial, this.visualFace(0));
    } else {
      this.rightPageMesh.visible = false;
      this.rightBlockMesh.visible = false;
      this.rightCoverMesh.visible = false;
      this.setMaterialFace(this.leftPageMaterial, this.visualFace(index));
      this.setStaticPageGeometry(this.leftPageGeometry, 'left', this.leftTopZ(index));
      this.updateBlockMesh(this.leftBlockMesh, 'left', this.leftTopZ(index));
      this.setMaterialFace(this.turnFrontMaterial, this.contentFace(index));
      this.setMaterialFace(this.turnBackMaterial, this.coverFace('back'));
    }

    this.turnFrontMesh.visible = true;
    this.turnBackMesh.visible = true;
    this.turnEdgeLine.visible = true;
    this.turnEdgeMaterial.color.setStyle(this.getCssColor('--book-leather-light', '#2d1710'));
    this.turnEdgeMaterial.opacity = 0.9;

    const startZ = isFront ? this.leftTopZ(0) : this.rightTopZ(index);
    const endZ = isFront
      ? this.rightTopZ(0) + LEAF_THICKNESS + 0.004
      : this.leftTopZ(index) + LEAF_THICKNESS + 0.004;
    this.deformCoverLeaf(amount, side, startZ, endZ);
    this.coverHitMesh.visible = Boolean(this.closedSide && !this.motion && amount >= 0.999);
  }

  private applyState() {
    if (!this.spreads.length) return;

    if (this.motion?.kind === 'cover') {
      const closureAmount = this.motion.opening ? 1 - this.turnProgress : this.turnProgress;
      this.applyCoverState(this.motion.side, closureAmount);
    } else if (this.closedSide) {
      this.applyCoverState(this.closedSide, 1);
    } else {
      const direction = this.motion?.kind === 'page' ? this.motion.direction : 0;
      this.applyPageState(direction, this.motion?.kind === 'page' ? this.turnProgress : 0);
    }

    this.render();
  }

  private render() {
    this.renderer.render(this.scene, this.camera);
  }

  private resize = () => {
    if (this.disposed) return;
    const bounds = this.host.getBoundingClientRect();
    if (!bounds.width || !bounds.height) return;

    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2.5));
    this.renderer.setSize(Math.round(bounds.width), Math.round(bounds.height), false);
    this.camera.aspect = bounds.width / bounds.height;

    // Frame the book against the actual wall portion rather than the viewport.
    // The compact fill leaves enough headroom for the free edge to rise during a
    // turn without clipping while keeping both open and closed states centered.
    const verticalDistance =
      (BOOK_FRAME_HEIGHT / 2) /
      Math.tan((this.camera.fov * Math.PI) / 360) /
      BOOK_FRAME_FILL_Y;
    const horizontalFov =
      2 * Math.atan(Math.tan((this.camera.fov * Math.PI) / 360) * this.camera.aspect);
    const horizontalDistance =
      (BOOK_FRAME_WIDTH / 2) / Math.tan(horizontalFov / 2) / BOOK_FRAME_FILL_X;
    this.camera.position.z = Math.max(verticalDistance, horizontalDistance);
    this.camera.updateProjectionMatrix();
    this.render();

    if (this.chooseTextureWidth() !== this.textureWidth) void this.renderAllFaces();
  };
}
