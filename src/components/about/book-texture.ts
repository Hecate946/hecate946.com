import type { PageFace, PageHitRegion, RenderedBookFace } from './book-types';

export const PAGE_ASPECT = 1.36;
const DESIGN_WIDTH = 1200;
const DESIGN_HEIGHT = Math.round(DESIGN_WIDTH * PAGE_ASPECT);
const FONT_SERIF = 'Newsreader, Georgia, "Times New Roman", serif';
const imageCache = new Map<string, HTMLImageElement>();


/**
 * Page typography/layout lives here. These values are in the 1200px design
 * coordinate system and are scaled automatically for the final WebGL texture.
 */
export const PAGE_STYLE = {
  titleStart: 78,
  titleMinimum: 58,
  bodySize: 36,
  bodyLineHeight: 49,
  bodyParagraphGap: 34,
  pageNumberSize: 23,
} as const;

type Palette = {
  paper: string;
  paperBright: string;
  paperWarm: string;
  paperEdge: string;
  ink: string;
  muted: string;
  accent: string;
  metal: string;
  leather: string;
  leatherLight: string;
};

const getPalette = (host: HTMLElement): Palette => {
  const style = getComputedStyle(host);
  const read = (name: string, fallback: string) => style.getPropertyValue(name).trim() || fallback;

  return {
    paper: read('--paper', '#ead8b7'),
    paperBright: read('--paper-bright', '#f1e3c6'),
    paperWarm: read('--paper-warm', '#e3cfaa'),
    paperEdge: read('--paper-edge', '#ad916d'),
    ink: read('--paper-ink', '#24170f'),
    muted: read('--paper-muted', '#695442'),
    accent: read('--paper-accent', '#653128'),
    metal: read('--book-metal', '#7b6040'),
    leather: read('--book-leather', '#180b08'),
    leatherLight: read('--book-leather-light', '#2d1710'),
  };
};

const loadImage = (src: string) => {
  const cached = imageCache.get(src);
  if (cached?.complete && cached.naturalWidth > 0) return Promise.resolve(cached);

  return new Promise<HTMLImageElement>((resolve) => {
    const image = cached ?? new Image();
    image.decoding = 'async';
    image.draggable = false;
    image.onload = () => {
      imageCache.set(src, image);
      resolve(image);
    };
    image.onerror = () => resolve(image);
    image.src = src;
    imageCache.set(src, image);
  });
};

export const preloadBookImages = (sources: string[]) => {
  for (const src of sources) void loadImage(src);
};

const wrapText = (context: CanvasRenderingContext2D, text: string, maxWidth: number) => {
  const words = text.trim().split(/\s+/);
  const lines: string[] = [];
  let line = '';

  for (const word of words) {
    const candidate = line ? `${line} ${word}` : word;
    if (line && context.measureText(candidate).width > maxWidth) {
      lines.push(line);
      line = word;
    } else {
      line = candidate;
    }
  }

  if (line) lines.push(line);
  return lines;
};

const drawTrackedText = (
  context: CanvasRenderingContext2D,
  text: string,
  x: number,
  y: number,
  tracking: number,
) => {
  let cursor = x;
  for (const char of text) {
    context.fillText(char, cursor, y);
    cursor += context.measureText(char).width + tracking;
  }
  return cursor;
};

const fitFontSize = (
  context: CanvasRenderingContext2D,
  text: string,
  width: number,
  start: number,
  minimum: number,
  weight = 500,
) => {
  let size = start;
  while (size > minimum) {
    context.font = `${weight} ${size}px ${FONT_SERIF}`;
    if (context.measureText(text).width <= width) return size;
    size -= 2;
  }
  return minimum;
};

const drawPaper = (context: CanvasRenderingContext2D, palette: Palette) => {
  const gradient = context.createLinearGradient(0, 0, DESIGN_WIDTH, DESIGN_HEIGHT);
  gradient.addColorStop(0, palette.paperBright);
  gradient.addColorStop(0.52, palette.paper);
  gradient.addColorStop(1, palette.paperWarm);
  context.fillStyle = gradient;
  context.fillRect(0, 0, DESIGN_WIDTH, DESIGN_HEIGHT);

  // Deterministic, extremely restrained fibre speckle. It survives downsampling
  // as paper texture without creating vertical bands during deformation.
  context.save();
  context.globalAlpha = 0.055;
  context.fillStyle = palette.muted;
  let seed = 946;
  const random = () => {
    seed = (seed * 1664525 + 1013904223) >>> 0;
    return seed / 4294967296;
  };
  for (let i = 0; i < 1050; i += 1) {
    const x = random() * DESIGN_WIDTH;
    const y = random() * DESIGN_HEIGHT;
    const size = random() > 0.92 ? 1.7 : 0.9;
    context.fillRect(x, y, size, size);
  }
  context.restore();

  // A faint perimeter makes the paper feel finite without darkening the gutter.
  context.save();
  context.strokeStyle = palette.paperEdge;
  context.globalAlpha = 0.26;
  context.lineWidth = 2;
  context.strokeRect(11, 11, DESIGN_WIDTH - 22, DESIGN_HEIGHT - 22);
  context.restore();
};

const drawPageNumber = (
  context: CanvasRenderingContext2D,
  pageNumber: number,
  align: 'left' | 'right',
  palette: Palette,
) => {
  context.save();
  context.fillStyle = palette.muted;
  context.globalAlpha = 0.88;
  context.font = `400 ${PAGE_STYLE.pageNumberSize}px ${FONT_SERIF}`;
  context.textBaseline = 'middle';
  context.textAlign = align;
  context.fillText(
    String(pageNumber).padStart(2, '0'),
    align === 'left' ? 78 : DESIGN_WIDTH - 78,
    DESIGN_HEIGHT - 66,
  );
  context.restore();
};

const drawImageCover = (
  context: CanvasRenderingContext2D,
  image: HTMLImageElement,
  x: number,
  y: number,
  width: number,
  height: number,
  contain = false,
) => {
  if (!image.naturalWidth || !image.naturalHeight) return;

  if (contain) {
    const scale = Math.min(width / image.naturalWidth, height / image.naturalHeight);
    const drawWidth = image.naturalWidth * scale;
    const drawHeight = image.naturalHeight * scale;
    context.drawImage(
      image,
      x + (width - drawWidth) / 2,
      y + (height - drawHeight) / 2,
      drawWidth,
      drawHeight,
    );
    return;
  }

  const imageRatio = image.naturalWidth / image.naturalHeight;
  const targetRatio = width / height;
  let sx = 0;
  let sy = 0;
  let sw = image.naturalWidth;
  let sh = image.naturalHeight;

  if (imageRatio > targetRatio) {
    sw = image.naturalHeight * targetRatio;
    sx = (image.naturalWidth - sw) / 2;
  } else {
    sh = image.naturalWidth / targetRatio;
    sy = (image.naturalHeight - sh) / 2;
  }

  context.drawImage(image, sx, sy, sw, sh, x, y, width, height);
};

const gothicFramePath = (context: CanvasRenderingContext2D, x: number, y: number, w: number, h: number) => {
  const shoulder = 74;
  context.beginPath();
  context.moveTo(x + w / 2, y);
  context.lineTo(x + w - 18, y + shoulder);
  context.quadraticCurveTo(x + w, y + shoulder + 20, x + w, y + shoulder + 54);
  context.lineTo(x + w, y + h);
  context.lineTo(x, y + h);
  context.lineTo(x, y + shoulder + 54);
  context.quadraticCurveTo(x, y + shoulder + 20, x + 18, y + shoulder);
  context.closePath();
};



const drawCoverFace = (
  context: CanvasRenderingContext2D,
  face: Extract<PageFace, { kind: 'cover' }>,
  palette: Palette,
) => {
  const gradient = context.createLinearGradient(0, 0, DESIGN_WIDTH, DESIGN_HEIGHT);
  gradient.addColorStop(0, palette.leatherLight);
  gradient.addColorStop(0.48, palette.leather);
  gradient.addColorStop(1, '#090403');
  context.fillStyle = gradient;
  context.fillRect(0, 0, DESIGN_WIDTH, DESIGN_HEIGHT);

  // Restrained deterministic grain: enough to read as leather at high DPI,
  // but not so much that it shimmers when the cover rotates.
  context.save();
  context.globalAlpha = 0.14;
  let seed = face.side === 'front' ? 946 : 1946;
  for (let index = 0; index < 1800; index += 1) {
    seed = (seed * 1664525 + 1013904223) >>> 0;
    const x = (seed / 4294967296) * DESIGN_WIDTH;
    seed = (seed * 1664525 + 1013904223) >>> 0;
    const y = (seed / 4294967296) * DESIGN_HEIGHT;
    context.fillStyle = index % 3 === 0 ? palette.leatherLight : '#050201';
    context.fillRect(x, y, 1.2, 1.2);
  }
  context.restore();

  context.save();
  context.strokeStyle = palette.metal;
  context.globalAlpha = 0.46;
  context.lineWidth = 3;
  context.strokeRect(56, 56, DESIGN_WIDTH - 112, DESIGN_HEIGHT - 112);
  context.globalAlpha = 0.22;
  context.lineWidth = 1.5;
  context.strokeRect(78, 78, DESIGN_WIDTH - 156, DESIGN_HEIGHT - 156);
  context.restore();

  if (face.side === 'front') {
    context.save();
    context.textAlign = 'center';
    context.textBaseline = 'middle';
    context.fillStyle = palette.metal;
    context.globalAlpha = 0.82;
    context.font = `500 27px ${FONT_SERIF}`;
    context.fillText(
      (face.eyebrow ?? 'ABOUT').toUpperCase().split('').join(' '),
      DESIGN_WIDTH / 2,
      DESIGN_HEIGHT * 0.43,
    );
    context.globalAlpha = 0.62;
    context.font = `400 62px ${FONT_SERIF}`;
    context.fillText(face.title ?? 'About', DESIGN_WIDTH / 2, DESIGN_HEIGHT * 0.52);
    context.restore();
  } else {
    context.save();
    context.textAlign = 'center';
    context.textBaseline = 'middle';
    context.fillStyle = palette.metal;
    context.globalAlpha = 0.42;
    context.font = `400 32px ${FONT_SERIF}`;
    context.fillText('✦', DESIGN_WIDTH / 2, DESIGN_HEIGHT / 2);
    context.restore();
  }
};

const drawVisualFace = async (
  context: CanvasRenderingContext2D,
  face: Extract<PageFace, { kind: 'visual' }>,
  palette: Palette,
) => {
  const image = await loadImage(face.spread.visual.src);
  const mode = face.spread.visual.mode;
  const frameX = mode === 'portrait' ? 178 : 126;
  const frameY = mode === 'portrait' ? 144 : 150;
  const frameW = mode === 'portrait' ? 844 : 948;
  const frameH = mode === 'portrait' ? 1010 : 980;

  context.save();
  context.fillStyle = palette.ink;
  context.globalAlpha = 0.82;
  if (mode === 'portrait') {
    gothicFramePath(context, frameX - 16, frameY - 16, frameW + 32, frameH + 32);
    context.fill();
  } else {
    context.fillRect(frameX - 16, frameY - 16, frameW + 32, frameH + 32);
  }
  context.restore();

  context.save();
  context.fillStyle = palette.metal;
  context.globalAlpha = 0.92;
  if (mode === 'portrait') {
    gothicFramePath(context, frameX - 8, frameY - 8, frameW + 16, frameH + 16);
    context.fill();
  } else {
    context.fillRect(frameX - 8, frameY - 8, frameW + 16, frameH + 16);
  }
  context.restore();

  context.save();
  if (mode === 'portrait') {
    gothicFramePath(context, frameX, frameY, frameW, frameH);
    context.clip();
  } else {
    context.beginPath();
    context.rect(frameX, frameY, frameW, frameH);
    context.clip();
  }

  context.fillStyle = palette.paperBright;
  context.fillRect(frameX, frameY, frameW, frameH);
  drawImageCover(context, image, frameX, frameY, frameW, frameH, mode === 'document');
  context.restore();

  context.save();
  context.fillStyle = palette.muted;
  context.font = `400 24px ${FONT_SERIF}`;
  context.textBaseline = 'alphabetic';
  drawTrackedText(context, '✦', 126, 1265, 0);
  drawTrackedText(context, face.spread.visual.caption.toUpperCase(), 176, 1265, 4.2);
  context.restore();

  drawPageNumber(context, face.pageNumber, 'left', palette);
};

const drawParagraphs = (
  context: CanvasRenderingContext2D,
  paragraphs: string[],
  x: number,
  y: number,
  width: number,
  palette: Palette,
) => {
  const bodySize = PAGE_STYLE.bodySize;
  const lineHeight = PAGE_STYLE.bodyLineHeight;
  const paragraphGap = PAGE_STYLE.bodyParagraphGap;

  context.save();
  context.fillStyle = palette.ink;
  context.globalAlpha = 0.92;
  context.font = `400 ${bodySize}px ${FONT_SERIF}`;
  context.textBaseline = 'alphabetic';

  let cursorY = y;
  for (const paragraph of paragraphs) {
    const lines = wrapText(context, paragraph, width);
    for (const line of lines) {
      context.fillText(line, x, cursorY);
      cursorY += lineHeight;
    }
    cursorY += paragraphGap;
  }
  context.restore();
  return cursorY;
};

const drawLink = (
  context: CanvasRenderingContext2D,
  label: string,
  x: number,
  y: number,
  palette: Palette,
) => {
  context.save();
  context.fillStyle = palette.accent;
  context.font = `500 25px ${FONT_SERIF}`;
  context.textBaseline = 'alphabetic';
  const text = `${label.toUpperCase()}  ↗`;
  drawTrackedText(context, text, x, y, 2.1);
  const metrics = context.measureText(text);
  context.restore();
  return Math.max(150, metrics.width + 58);
};

const drawContentFace = (
  context: CanvasRenderingContext2D,
  face: Extract<PageFace, { kind: 'content' }>,
  palette: Palette,
): PageHitRegion[] => {
  const { spread } = face;
  const hitRegions: PageHitRegion[] = [];
  const x = 116;
  const width = 956;

  context.save();
  context.fillStyle = palette.muted;
  context.font = `500 23px ${FONT_SERIF}`;
  context.textBaseline = 'alphabetic';
  drawTrackedText(context, spread.eyebrow.toUpperCase(), x, 152, 5.4);
  context.restore();

  context.save();
  context.fillStyle = palette.ink;
  const titleSize = fitFontSize(
    context,
    spread.title,
    width,
    PAGE_STYLE.titleStart,
    PAGE_STYLE.titleMinimum,
  );
  context.font = `500 ${titleSize}px ${FONT_SERIF}`;
  context.textBaseline = 'alphabetic';
  context.fillText(spread.title, x, 262);
  context.restore();

  context.save();
  context.strokeStyle = palette.accent;
  context.globalAlpha = 0.58;
  context.lineWidth = 2;
  context.beginPath();
  context.moveTo(x, 316);
  context.lineTo(x + 560, 316);
  context.stroke();
  context.fillStyle = palette.accent;
  context.globalAlpha = 0.76;
  context.translate(x + 589, 316);
  context.rotate(Math.PI / 4);
  context.fillRect(-5, -5, 10, 10);
  context.restore();

  if (spread.interests?.length) {
    let y = 390;
    const columnWidth = width;

    for (let index = 0; index < spread.interests.length; index += 1) {
      const interest = spread.interests[index];
      context.save();
      context.fillStyle = palette.muted;
      context.font = `400 22px ${FONT_SERIF}`;
      context.fillText(String(index + 1).padStart(2, '0'), x, y + 10);
      context.restore();

      const textX = x + 72;
      context.save();
      context.fillStyle = palette.ink;
      context.font = `500 43px ${FONT_SERIF}`;
      context.fillText(interest.title, textX, y + 10);
      context.restore();

      context.save();
      context.fillStyle = palette.ink;
      context.globalAlpha = 0.92;
      context.font = `400 32px ${FONT_SERIF}`;
      const lines = wrapText(context, interest.body, columnWidth - 72);
      let lineY = y + 68;
      for (const line of lines) {
        context.fillText(line, textX, lineY);
        lineY += 43;
      }
      context.restore();

      const linkY = lineY + 10;
      const linkWidth = drawLink(context, interest.link.label, textX, linkY, palette);
      hitRegions.push({
        x: textX / DESIGN_WIDTH,
        y: (linkY - 35) / DESIGN_HEIGHT,
        width: linkWidth / DESIGN_WIDTH,
        height: 60 / DESIGN_HEIGHT,
        link: interest.link,
      });

      y = linkY + 104;
      if (index < spread.interests.length - 1) {
        context.save();
        context.strokeStyle = palette.paperEdge;
        context.globalAlpha = 0.55;
        context.lineWidth = 1.5;
        context.beginPath();
        context.moveTo(textX, y - 50);
        context.lineTo(x + width, y - 50);
        context.stroke();
        context.restore();
      }
    }
  } else {
    drawParagraphs(context, spread.paragraphs ?? [], x, 408, width, palette);

    if (spread.link) {
      const linkY = 1380;
      const linkWidth = drawLink(context, spread.link.label, x, linkY, palette);
      hitRegions.push({
        x: x / DESIGN_WIDTH,
        y: (linkY - 38) / DESIGN_HEIGHT,
        width: linkWidth / DESIGN_WIDTH,
        height: 64 / DESIGN_HEIGHT,
        link: spread.link,
      });
    }
  }

  drawPageNumber(context, face.pageNumber, 'right', palette);
  return hitRegions;
};

export const renderBookFace = async (
  face: PageFace,
  host: HTMLElement,
  textureWidth: number,
): Promise<RenderedBookFace> => {
  const width = Math.max(768, Math.round(textureWidth));
  const height = Math.round(width * PAGE_ASPECT);
  const canvas = document.createElement('canvas');
  canvas.width = width;
  canvas.height = height;
  const context = canvas.getContext('2d', { alpha: false });
  if (!context) return { canvas, hitRegions: [] };

  context.imageSmoothingEnabled = true;
  context.imageSmoothingQuality = 'high';
  const scale = width / DESIGN_WIDTH;
  context.scale(scale, scale);

  const palette = getPalette(host);
  if (face.kind === 'cover') {
    drawCoverFace(context, face, palette);
    return { canvas, hitRegions: [] };
  }

  drawPaper(context, palette);

  if (face.kind === 'visual') {
    await drawVisualFace(context, face, palette);
    return { canvas, hitRegions: [] };
  }

  return {
    canvas,
    hitRegions: drawContentFace(context, face, palette),
  };
};
