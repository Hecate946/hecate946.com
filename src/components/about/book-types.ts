export type Direction = -1 | 1;
export type PageSide = 'left' | 'right';
export type BookClosedSide = 'front' | 'back' | null;

export type BookMotion =
  | {
      kind: 'page';
      direction: Direction;
    }
  | {
      kind: 'cover';
      side: Exclude<BookClosedSide, null>;
      opening: boolean;
    };

export type BookLink = {
  href: string;
  label: string;
  external?: boolean;
};

export type BookInterest = {
  title: string;
  body: string;
  link: BookLink;
};

export type BookVisual = {
  src: string;
  alt: string;
  caption: string;
};

export type BookSpread = {
  id: 'about' | 'software' | 'music' | 'interests';
  label: string;
  eyebrow: string;
  title: string;
  paragraphs?: string[];
  visual?: BookVisual;
  link?: BookLink;
  interests?: BookInterest[];
};

export type PageFace =
  | {
      kind: 'visual';
      spread: BookSpread;
      pageNumber: number;
    }
  | {
      kind: 'content';
      spread: BookSpread;
      pageNumber: number;
    }
  | {
      kind: 'cover';
      side: 'front' | 'back';
      eyebrow?: string;
      title?: string;
    };

export type PageHitRegion = {
  x: number;
  y: number;
  width: number;
  height: number;
  link: BookLink;
};

export type RenderedBookFace = {
  canvas: HTMLCanvasElement;
  hitRegions: PageHitRegion[];
};
