import { withBase } from '@/lib/paths';

export const roomSlugs = ['red', 'green', 'orange', 'blue', 'purple'] as const;
export const hallSlugs = ['ballroom', 'museum'] as const;

export type RoomSlug = (typeof roomSlugs)[number];
export type HallSlug = (typeof hallSlugs)[number];
export type ImmersiveSlug = RoomSlug | HallSlug;
export type ImmersiveKind = 'room' | 'hall';
export type ImmersiveModelRole = 'shell' | 'objects';
export type Vector3Tuple = [number, number, number];

export type ImmersivePanoramaView = {
  id: string;
  label: string;
  panoramaUrl: string;
  panoramaYaw: number;
  cameraYaw: number;
  cameraPitch: number;
  cameraFov: number;
};

export type ImmersiveModelLayer = {
  id: string;
  role: ImmersiveModelRole;
  url: string;
  position?: Vector3Tuple;
  rotation?: Vector3Tuple;
  scale?: Vector3Tuple;
};

export type ImmersiveSpace = {
  kind: ImmersiveKind;
  slug: ImmersiveSlug;
  label: string;
  title: string;
  description: string;
  accent: string;
  panoramaUrl?: string;
  panoramaUnderwaterOverlayUrl?: string;
  panoramaCausticsOverlayUrl?: string;
  panoramaCausticsOverlayVideoUrl?: string;
  panoramaOverlayUrl?: string;
  panoramaOverlayVideoUrl?: string;
  panoramaViews?: ImmersivePanoramaView[];
  cyclesOnly?: boolean;
  renderedViewId?: string;
  modelLayers: ImmersiveModelLayer[];
  implemented: boolean;
  cameraPosition: Vector3Tuple;
  cameraYaw: number;
  panoramaYaw: number;
  windowIndex?: number;
};

// Must mirror the shared Blender room dimensions used by room_builder.py.
// The camera is centered near the entry wall; the seam is rotated to the
// entry-right corner, which is the stable winner after rotation/distance ties.
const ROOM_WIDTH = 3.99;
const ROOM_DEPTH = 5.70;
const ROOM_ENTRY_CLEARANCE = 1.95;
const ROOM_CAMERA_Z = ROOM_DEPTH / 2 - ROOM_ENTRY_CLEARANCE;
const ROOM_PANORAMA_YAW = -Math.atan2(ROOM_ENTRY_CLEARANCE, ROOM_WIDTH / 2);

const objectsLayer = (id: string, url: string): ImmersiveModelLayer => ({
  id,
  role: 'objects',
  url: withBase(url),
});

const room = (
  slug: RoomSlug,
  label: string,
  title: string,
  description: string,
  accent: string,
  windowIndex: number,
  additionalViews: ImmersivePanoramaView[] = [],
  cyclesOnly = false,
): ImmersiveSpace => {
  const panoramaUrl = withBase(`/scenes/rooms/${slug}/panorama.png?v=room-v49`);
  const defaultView: ImmersivePanoramaView = {
    id: 'default',
    label: 'Room view',
    panoramaUrl,
    panoramaYaw: ROOM_PANORAMA_YAW,
    cameraYaw: 0,
    cameraPitch: 0,
    cameraFov: 96,
  };

  return {
    kind: 'room',
    slug,
    label,
    title,
    description,
    accent,
    panoramaUrl,
    panoramaViews: [defaultView, ...additionalViews],
    cyclesOnly,
    modelLayers: [
      objectsLayer(
        `${slug}-objects`,
        `/scenes/rooms/${slug}/interactive.glb?v=room-v49`,
      ),
    ],
    implemented: true,
    cameraPosition: [0, 1.65, ROOM_CAMERA_Z],
    cameraYaw: 0,
    panoramaYaw: ROOM_PANORAMA_YAW,
    windowIndex,
  };
};

const SHARED_HALL_SHELL_URL = withBase('/scenes/halls/shared/shell.glb');

const hall = (
  slug: HallSlug,
  label: string,
  title: string,
  description: string,
  accent: string,
  mirrorShell: boolean,
): ImmersiveSpace => ({
  kind: 'hall',
  slug,
  label,
  title,
  description,
  accent,
  modelLayers: [
    {
      id: 'shared-hall-shell',
      role: 'shell',
      url: SHARED_HALL_SHELL_URL,
      scale: mirrorShell ? [-1, 1, 1] : [1, 1, 1],
    },
    objectsLayer(`${slug}-objects`, `/scenes/halls/${slug}/objects.glb`),
  ],
  implemented: true,
  cameraPosition: [0, 1.68, 0],
  cameraYaw: 0,
  panoramaYaw: 0,
});

export const rooms = {
  red: room('red', 'Room 001', 'The Red Room', 'An immersive fixed-viewpoint red tiled room.', '#4a1f24', 0),
  green: room(
    'green',
    'Room 002',
    'The Green Room',
    'A Cycles-rendered green tiled room with clickable camera views.',
    '#1c3a2f',
    1,
    [
      {
        id: 'board',
        label: 'Chessboard view',
        panoramaUrl: withBase(
          '/scenes/rooms/green/views/board.png?v=room-v49',
        ),
        panoramaYaw: -Math.PI / 2,
        cameraYaw: 0,
        cameraPitch: 0,
        cameraFov: 68,
      },
    ],
    true,
  ),
  orange: room('orange', 'Room 003', 'The Orange Room', 'An immersive fixed-viewpoint orange tiled room.', '#5a2f18', 2),
  blue: {
    ...room(
      'blue',
      'Room 004',
      'The Blue Room',
      'An immersive fixed-viewpoint blue tiled room with layered realistic pool-water overlays rendered in Blender.',
      '#18344c',
      3,
    ),
    panoramaUnderwaterOverlayUrl: withBase(
      '/scenes/rooms/blue/underwater-grade.png?v=room-v61-water-multipass',
    ),
    panoramaCausticsOverlayUrl: withBase(
      '/scenes/rooms/blue/water-caustics.png?v=room-v61-water-multipass',
    ),
    panoramaCausticsOverlayVideoUrl: withBase(
      '/scenes/rooms/blue/water-caustics.webm?v=room-v61-water-multipass',
    ),
    panoramaOverlayUrl: withBase(
      '/scenes/rooms/blue/water-surface.png?v=room-v61-water-multipass',
    ),
    panoramaOverlayVideoUrl: withBase(
      '/scenes/rooms/blue/water-surface.webm?v=room-v61-water-multipass',
    ),
  },
  purple: room('purple', 'Room 005', 'The Purple Room', 'An immersive fixed-viewpoint purple tiled room.', '#35213f', 4),
} as const satisfies Record<RoomSlug, ImmersiveSpace>;

export const halls = {
  ballroom: {
    ...hall(
      'ballroom',
      'Hall 001',
      'The Ballroom',
      'A sparse, Cycles-rendered 2.5D Neoclassical ballroom with authored camera views.',
      '#7d6848',
      false,
    ),
    cyclesOnly: true,
    renderedViewId: 'ballroom',
  },
  museum: hall(
    'museum',
    'Hall 002',
    'The Museum',
    'The canonical shared neoclassical hall with museum-specific objects.',
    '#59606d',
    false,
  ),
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
