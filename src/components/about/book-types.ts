export type Direction = -1 | 1;
export type PageSide = 'left' | 'right';
export type VisualMode = 'portrait' | 'screen' | 'document' | 'photo';

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

export type BookSpread = {
  id: 'about' | 'software' | 'music' | 'interests';
  label: string;
  eyebrow: string;
  title: string;
  paragraphs?: string[];
  visual: {
    src: string;
    alt: string;
    caption: string;
    mode: VisualMode;
  };
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
