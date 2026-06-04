export const SOURCE_TILE_SIZE = 16;
export const DEST_TILE_SIZE = 32;
export const ATLAS_COLUMNS = 16;

export const QUADRANT = {
  FULL: 'full',
  TL: 'tl',
  TR: 'tr',
  BL: 'bl',
  BR: 'br',
};

export const atlasIndex = (x, y) => y * ATLAS_COLUMNS + x;

export const BACKEND_TILE = {
  VOID: { id: 0, atlasIndex: null, seethrough: true },
  WALL: { id: 1, atlasIndex: atlasIndex(0, 5), seethrough: false },
  FLOOR: { id: 2, atlasIndex: null, seethrough: true },
  DOOR: { id: 3, atlasIndex: atlasIndex(8, 3), seethrough: false },
  OPEN_DOOR: { id: 3, atlasIndex: atlasIndex(9, 3), seethrough: true },
  STAIRS_UP: { id: 4, atlasIndex: atlasIndex(0, 1), seethrough: true },
  STAIRS_DOWN: { id: 5, atlasIndex: atlasIndex(1, 1), seethrough: true },
  FLOOR_WOOD: { id: 6, atlasIndex: atlasIndex(4, 0), seethrough: true },
  FLOOR_WATER: { id: 7, atlasIndex: null, seethrough: true },
  FLOOR_COBBLE: { id: 8, atlasIndex: atlasIndex(12, 0), seethrough: true },
  FLOOR_GRASS: { id: 9, atlasIndex: null, seethrough: true },
  LOCKED_DOOR: { id: 10, atlasIndex: atlasIndex(8, 3), seethrough: false },
  SECRET_TRAP: { id: 11, atlasIndex: null, seethrough: true },
  TRAP: { id: 12, atlasIndex: null, seethrough: true },
  INACTIVE_TRAP: { id: 13, atlasIndex: null, seethrough: true },
  WALL_DECO: { id: 17, atlasIndex: atlasIndex(1, 3), seethrough: false },
  EMPTY_DECO: { id: 18, atlasIndex: atlasIndex(3, 0), seethrough: true },
  HIGH_GRASS: { id: 19, atlasIndex: null, seethrough: false },
  SECRET_DOOR: { id: 20, atlasIndex: atlasIndex(0, 5), seethrough: false },
  FURROWED_GRASS: { id: 21, atlasIndex: null, seethrough: false },
};

export const toAtlasCoords = (index) => ({
  x: index % ATLAS_COLUMNS,
  y: Math.floor(index / ATLAS_COLUMNS),
});

export const hashCell = (x, y) => ((x * 73856093) ^ (y * 19349663)) >>> 0;

export const TERRAIN_INDEX = {
  FLOOR_VARIANTS: [atlasIndex(0, 0), atlasIndex(1, 0), atlasIndex(2, 0)],
  FLOOR_ALT_VARIANTS: [atlasIndex(6, 0), atlasIndex(7, 0), atlasIndex(8, 0)],

  // SPD DungeonTileSheet: FLOOR_DECO = GROUND+1, FLOOR_DECO_ALT = GROUND+7.
  // EMPTY_DECO renders as one of these full-tile decorated floor variants,
  // picked by hashCell for per-cell but stable variation.
  EMPTY_DECO_VARIANTS: [atlasIndex(1, 0), atlasIndex(7, 0)],

  GRASS_CENTER: [atlasIndex(2, 4), atlasIndex(5, 4), atlasIndex(6, 4)],
  HIGH_GRASS_CENTER: [atlasIndex(10, 7), atlasIndex(13, 7)],
  FURROWED_GRASS_CENTER: [atlasIndex(11, 7), atlasIndex(12, 7)],
  GRASS_EDGE: {
    tl: atlasIndex(1, 2),
    tr: atlasIndex(2, 2),
    bl: atlasIndex(3, 2),
    br: atlasIndex(4, 2),
  },

  WATER_CENTER: [atlasIndex(3, 7), atlasIndex(11, 3)],
  WATER_EDGE: {
    tl: atlasIndex(8, 7),
    tr: atlasIndex(9, 7),
    bl: atlasIndex(10, 7),
    br: atlasIndex(11, 7),
  },
};

/*
 * WALL_INDEX — atlas base indices for SPD's two-layer wall architecture.
 *
 * Layout (mirrors SPD DungeonTileSheet constants, translated from 1-indexed
 * xy(col, row) to 0-indexed atlasIndex(x, y)):
 *
 *   RAISED_WALL         y=5, cols 0-3   (front-face: +1 open right, +2 open left)
 *   RAISED_WALL_DECO    y=5, cols 4-7
 *   RAISED_WALL_DOOR    y=5, col 8      (wall cell directly above a door)
 *   RAISED_WALL_ALT     y=6, cols 0-3   (alt visual row — hash picks between)
 *   RAISED_WALL_DECO_ALT y=6, cols 4-7
 *
 *   WALL_INTERNAL       y=9, cols 0-15  (wall top when surrounded by walls —
 *                                        4-bit mask: +1 right, +2 rightBelow,
 *                                        +4 leftBelow, +8 left)
 *   WALL_INTERNAL_DECO  y=10, cols 0-15
 *
 *   WALL_OVERHANG       y=12, cols 0-3  (wall top bleeding into the floor cell
 *                                        above it — 2-bit mask: +1 rightBelow
 *                                        non-wall, +2 leftBelow non-wall)
 *   WALL_OVERHANG_DECO  y=12, cols 4-7
 *
 *   DOOR_SIDEWAYS_OVERHANG          y=13, cols 0-3   (door on a vertical wall,
 *                                                     seen from the floor above)
 *   DOOR_SIDEWAYS_OVERHANG_CLOSED   y=13, cols 4-7
 *   DOOR_SIDEWAYS_OVERHANG_LOCKED   y=13, cols 8-11
 *
 *   DOOR_OVERHANG               y=14, col 0   (top cap of a horizontal door)
 *   DOOR_OVERHANG_OPEN          y=14, col 1
 *   DOOR_SIDEWAYS               y=14, col 3   (wall cell directly above a
 *                                              vertical door — no stitching)
 *   DOOR_SIDEWAYS_LOCKED        y=14, col 4
 *
 *   RAISED_DOOR_SIDEWAYS        y=7, col 4    (the side-door body itself,
 *                                              drawn at the door cell when
 *                                              it sits between two walls)
 *
 * The "raised" naming comes from SPD's 3D look: the wall cell at (x, y) draws
 * only its FRONT FACE (lower half of the sprite hangs below the top-of-wall
 * line). The wall's top-of-wall surface is drawn ONE CELL UP from its grid
 * row — in what is, logically, the floor cell above it — as WALL_OVERHANG.
 * That's how walls visually obscure characters standing behind them.
 */
export const WALL_INDEX = {
  RAISED_WALL: atlasIndex(0, 5),
  RAISED_WALL_DECO: atlasIndex(4, 5),
  RAISED_WALL_DOOR: atlasIndex(8, 5),
  RAISED_WALL_ALT: atlasIndex(0, 6),
  RAISED_WALL_DECO_ALT: atlasIndex(4, 6),

  WALL_INTERNAL: atlasIndex(0, 9),
  WALL_INTERNAL_DECO: atlasIndex(0, 10),

  WALL_OVERHANG: atlasIndex(0, 12),
  WALL_OVERHANG_DECO: atlasIndex(4, 12),

  DOOR_SIDEWAYS_OVERHANG: atlasIndex(0, 13),
  DOOR_SIDEWAYS_OVERHANG_CLOSED: atlasIndex(4, 13),
  DOOR_SIDEWAYS_OVERHANG_LOCKED: atlasIndex(8, 13),

  DOOR_OVERHANG: atlasIndex(0, 14),
  DOOR_OVERHANG_OPEN: atlasIndex(1, 14),
  DOOR_SIDEWAYS: atlasIndex(3, 14),
  DOOR_SIDEWAYS_LOCKED: atlasIndex(4, 14),

  RAISED_DOOR_SIDEWAYS: atlasIndex(4, 7),
};

export const WATER_SCROLL_PX_PER_SEC = 10;

export const QUADRANT_NEIGHBORS = {
  tl: [
    [0, 0],
    [-1, 0],
    [0, -1],
    [-1, -1],
  ],
  tr: [
    [0, 0],
    [1, 0],
    [0, -1],
    [1, -1],
  ],
  bl: [
    [0, 0],
    [-1, 0],
    [0, 1],
    [-1, 1],
  ],
  br: [
    [0, 0],
    [1, 0],
    [0, 1],
    [1, 1],
  ],
};

// Used by rendering + game logic: WALL, WALL_DECO, and SECRET_DOOR all
// render as walls (SECRET_DOOR is indistinguishable from WALL to the player
// until revealed).
export const isWallTile = (tile) =>
  tile === BACKEND_TILE.WALL.id ||
  tile === BACKEND_TILE.WALL_DECO.id ||
  tile === BACKEND_TILE.SECRET_DOOR.id;

// Used ONLY by wall-autotile stitching: any tile that should visually
// continue a wall surface. Out-of-bounds (-1) and unpainted VOID cells
// count as walls so the outer frame of the map stitches cleanly instead
// of showing jagged edges. Mirrors SPD's DungeonTileSheet.wallStitcheable.
export const isWallStitcheable = (tile) =>
  tile === -1 ||
  tile === BACKEND_TILE.VOID.id ||
  tile === BACKEND_TILE.WALL.id ||
  tile === BACKEND_TILE.WALL_DECO.id ||
  tile === BACKEND_TILE.SECRET_DOOR.id;

export const isDoorTile = (tile) =>
  tile === BACKEND_TILE.DOOR.id || tile === BACKEND_TILE.LOCKED_DOOR.id;

export const isWaterTile = (tile) => tile === BACKEND_TILE.FLOOR_WATER.id;
export const isGrassTile = (tile) =>
  tile === BACKEND_TILE.FLOOR_GRASS.id ||
  tile === BACKEND_TILE.HIGH_GRASS.id ||
  tile === BACKEND_TILE.FURROWED_GRASS.id;

export const TRAP_VISUAL = {
  worn_dart: { color: 7, shape: 5 },
};

export const trapSpriteIndex = (trapType) => {
  const v = TRAP_VISUAL[trapType];
  if (!v) return null;
  return v.color + v.shape * 16;
};

export const trapDisarmedIndex = (trapType) => {
  const v = TRAP_VISUAL[trapType];
  if (!v) return null;
  return 8 + v.shape * 16;
};
