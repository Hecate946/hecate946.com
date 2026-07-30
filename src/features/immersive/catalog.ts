import { withBase } from '@/lib/paths';

export const roomSlugs = ['red', 'green', 'orange', 'blue', 'purple'] as const;
export const hallSlugs = ['ballroom', 'museum'] as const;

export type RoomSlug = (typeof roomSlugs)[number];
export type HallSlug = (typeof hallSlugs)[number];
export type ImmersiveSlug = RoomSlug | HallSlug;
export type ImmersiveKind = 'room' | 'hall';

export type ImmersiveSpace = {
  kind: ImmersiveKind;
  slug: ImmersiveSlug;
  label: string;
  title: string;
  description: string;
  accent: string;
  panoramaUrl?: string;
  interactiveUrl?: string;
  implemented: boolean;
  cameraPosition: [number, number, number];
  panoramaYaw: number;
  windowIndex?: number;
};

const room = (
  slug: RoomSlug,
  label: string,
  title: string,
  description: string,
  accent: string,
  windowIndex: number,
): ImmersiveSpace => ({
  kind: 'room',
  slug,
  label,
  title,
  description,
  accent,
  panoramaUrl: withBase(`/scenes/rooms/${slug}/panorama.webp`),
  interactiveUrl: withBase(`/scenes/rooms/${slug}/interactive.glb`),
  implemented: true,
  cameraPosition: [0, 1.65, 3.8],
  panoramaYaw: -Math.PI / 2,
  windowIndex,
});

export const rooms = {
  red: room('red', 'Room 001', 'The Red Room', 'An immersive fixed-viewpoint red tiled room.', '#4a1f24', 0),
  green: room('green', 'Room 002', 'The Green Room', 'An immersive fixed-viewpoint green tiled room.', '#1c3a2f', 1),
  orange: room('orange', 'Room 003', 'The Orange Room', 'An immersive fixed-viewpoint orange tiled room.', '#5a2f18', 2),
  blue: room('blue', 'Room 004', 'The Blue Room', 'An immersive fixed-viewpoint blue tiled room.', '#18344c', 3),
  purple: room('purple', 'Room 005', 'The Purple Room', 'An immersive fixed-viewpoint purple tiled room.', '#35213f', 4),
} as const satisfies Record<RoomSlug, ImmersiveSpace>;

export const halls = {
  ballroom: {
    kind: 'hall',
    slug: 'ballroom',
    label: 'Hall 001',
    title: 'The Ballroom',
    description: 'A panoramic neoclassical ballroom with polished marble flooring.',
    accent: '#7d6848',
    panoramaUrl: withBase('/scenes/halls/ballroom/panorama.webp'),
    implemented: true,
    cameraPosition: [0, 1.68, 0],
    panoramaYaw: -Math.PI / 2,
  },
  museum: {
    kind: 'hall',
    slug: 'museum',
    label: 'Hall 002',
    title: 'The Museum',
    description: 'A future immersive museum hall.',
    accent: '#59606d',
    implemented: false,
    cameraPosition: [0, 1.68, 0],
    panoramaYaw: -Math.PI / 2,
  },
} as const satisfies Record<HallSlug, ImmersiveSpace>;

export const secondStoryRooms = roomSlugs.map((slug) => rooms[slug]);
export const hallCatalog = hallSlugs.map((slug) => halls[slug]);
export const implementedHalls = hallCatalog.filter((hall) => hall.implemented);

export function getRoom(slug: string): ImmersiveSpace | undefined {
  return rooms[slug as RoomSlug];
}

export function getHall(slug: string): ImmersiveSpace | undefined {
  return halls[slug as HallSlug];
}
