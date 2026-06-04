import {
  BACKEND_TILE,
  QUADRANT,
  QUADRANT_NEIGHBORS,
  TERRAIN_INDEX,
  WALL_INDEX,
  hashCell,
  isGrassTile,
  isWallStitcheable,
  isWaterTile,
} from './constants.js';

const getTile = (grid, x, y) => {
  if (y < 0 || y >= grid.length) return BACKEND_TILE.VOID.id;
  if (x < 0 || x >= grid[y].length) return BACKEND_TILE.VOID.id;
  return grid[y][x];
};

const pickVariant = (variants, x, y, salt = 0) => {
  const idx = (hashCell(x + salt, y - salt) + salt) % variants.length;
  return variants[idx];
};

const shouldUseCornerType = (grid, x, y, matcher, quadrant) => {
  const cells = QUADRANT_NEIGHBORS[quadrant];
  let matches = 0;
  for (const [dx, dy] of cells) {
    if (matcher(getTile(grid, x + dx, y + dy))) matches += 1;
  }
  return matches >= 3;
};

const getFloorBase = (x, y) => pickVariant(TERRAIN_INDEX.FLOOR_VARIANTS, x, y);

const tileInstr = (asset) => ({
  srcIndex: asset.atlasIndex,
  quadrant: QUADRANT.FULL,
  ...(asset.rotate    != null && { rotate:    asset.rotate }),
  ...(asset.srcOffset != null && { srcOffset: asset.srcOffset }),
  ...(asset.crop      != null && { crop:      asset.crop }),
});

const getTerrainQuadrants = (grid, x, y, matcher, centerVariants, edgeByQuadrant, salt) => {
  const center = pickVariant(centerVariants, x, y, salt);
  const out = [];
  for (const quadrant of [QUADRANT.TL, QUADRANT.TR, QUADRANT.BL, QUADRANT.BR]) {
    out.push({
      srcIndex: shouldUseCornerType(grid, x, y, matcher, quadrant) ? center : edgeByQuadrant[quadrant],
      quadrant,
    });
  }
  return out;
};

const _isTrapTile = (tile) =>
  tile === BACKEND_TILE.SECRET_TRAP.id ||
  tile === BACKEND_TILE.TRAP.id ||
  tile === BACKEND_TILE.INACTIVE_TRAP.id;

export const getSewerTerrainInstructions = (grid, x, y, tile, openDoors = new Set()) => {
  if (tile === BACKEND_TILE.VOID.id) return [];

  if (tile === BACKEND_TILE.FLOOR.id || _isTrapTile(tile)) {
    return [{ srcIndex: getFloorBase(x, y), quadrant: QUADRANT.FULL }];
  }

  if (tile === BACKEND_TILE.FLOOR_WOOD.id) {
    return [{ srcIndex: BACKEND_TILE.FLOOR_WOOD.atlasIndex, quadrant: QUADRANT.FULL }];
  }

  if (tile === BACKEND_TILE.FLOOR_COBBLE.id) {
    return [{ srcIndex: BACKEND_TILE.FLOOR_COBBLE.atlasIndex, quadrant: QUADRANT.FULL }];
  }

  if (tile === BACKEND_TILE.STAIRS_UP.id || tile === BACKEND_TILE.STAIRS_DOWN.id) {
    return [
      { srcIndex: pickVariant(TERRAIN_INDEX.FLOOR_ALT_VARIANTS, x, y), quadrant: QUADRANT.FULL },
      {
        srcIndex: tile === BACKEND_TILE.STAIRS_UP.id ? BACKEND_TILE.STAIRS_UP.atlasIndex : BACKEND_TILE.STAIRS_DOWN.atlasIndex,
        quadrant: QUADRANT.FULL,
      },
    ];
  }

  if (tile === BACKEND_TILE.DOOR.id || tile === BACKEND_TILE.LOCKED_DOOR.id) {
    // Side door: when the cell above is a wall, the door is set into a
    // vertical wall and uses the dedicated side-door body sprite. Mirrors
    // SPD DungeonTileSheet.getRaisedDoorTile.
    if (isWallStitcheable(getTile(grid, x, y - 1))) {
      return [{ srcIndex: WALL_INDEX.RAISED_DOOR_SIDEWAYS, quadrant: QUADRANT.FULL }];
    }
    // Top-facing door: regular door sprite. Adjacent-wall stitching is
    // handled by wallMapper.getSewerCap (DOOR_OVERHANG family).
    const base = tile === BACKEND_TILE.LOCKED_DOOR.id
      ? BACKEND_TILE.LOCKED_DOOR
      : (openDoors.has(`${x},${y}`) ? BACKEND_TILE.OPEN_DOOR : BACKEND_TILE.DOOR);
    return [tileInstr(base)];
  }

  if (tile === BACKEND_TILE.FLOOR_WATER.id) {
    const out = [];
    for (const q of [QUADRANT.TL, QUADRANT.TR, QUADRANT.BL, QUADRANT.BR]) {
      if (!shouldUseCornerType(grid, x, y, isWaterTile, q)) {
        out.push({ srcIndex: TERRAIN_INDEX.WATER_EDGE[q], quadrant: q });
      }
    }
    return out;
  }

  if (tile === BACKEND_TILE.FLOOR_GRASS.id) {
    const instructions = [{ srcIndex: getFloorBase(x, y), quadrant: QUADRANT.FULL }];
    instructions.push(
      ...getTerrainQuadrants(
        grid,
        x,
        y,
        isGrassTile,
        TERRAIN_INDEX.GRASS_CENTER,
        TERRAIN_INDEX.GRASS_EDGE,
        31
      )
    );
    return instructions;
  }

  if (tile === BACKEND_TILE.EMPTY_DECO.id) {
    // SPD picks one of two full-tile FLOOR_DECO variants, not an overlay on
    // a plain floor. hashCell gives stable per-cell variation.
    return [{ srcIndex: pickVariant(TERRAIN_INDEX.EMPTY_DECO_VARIANTS, x, y), quadrant: QUADRANT.FULL }];
  }

  if (tile === BACKEND_TILE.HIGH_GRASS.id) {
    const instructions = [{ srcIndex: getFloorBase(x, y), quadrant: QUADRANT.FULL }];
    instructions.push(
      ...getTerrainQuadrants(
        grid,
        x,
        y,
        isGrassTile,
        TERRAIN_INDEX.HIGH_GRASS_CENTER,
        TERRAIN_INDEX.GRASS_EDGE,
        31
      )
    );
    return instructions;
  }

  if (tile === BACKEND_TILE.FURROWED_GRASS.id) {
    const instructions = [{ srcIndex: getFloorBase(x, y), quadrant: QUADRANT.FULL }];
    instructions.push(
      ...getTerrainQuadrants(
        grid,
        x,
        y,
        isGrassTile,
        TERRAIN_INDEX.FURROWED_GRASS_CENTER,
        TERRAIN_INDEX.GRASS_EDGE,
        31
      )
    );
    return instructions;
  }

  return [];
};
