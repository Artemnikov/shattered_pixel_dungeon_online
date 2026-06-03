import {
  ATLAS_COLUMNS,
  BACKEND_TILE,
  DEST_TILE_SIZE,
  SOURCE_TILE_SIZE,
  trapDisarmedIndex,
  trapSpriteIndex,
} from '../sewers/constants.js';

const getSourceXY = (srcIndex) => ({
  sx: (srcIndex % ATLAS_COLUMNS) * SOURCE_TILE_SIZE,
  sy: Math.floor(srcIndex / ATLAS_COLUMNS) * SOURCE_TILE_SIZE,
});

export function drawTerrainFeatures(ctx, terrainFeaturesImg, traps, grid, visionRef) {
  if (!terrainFeaturesImg || !traps || traps.length === 0) return;

  const discovered = visionRef.current.discovered;

  for (const trap of traps) {
    const { x, y, trap_type } = trap;
    const key = `${x},${y}`;
    if (!discovered.has(key)) continue;

    const tile = grid[y]?.[x];
    if (tile === undefined) continue;

    if (tile === BACKEND_TILE.SECRET_TRAP.id) continue;

    let srcIndex;
    if (tile === BACKEND_TILE.INACTIVE_TRAP.id) {
      srcIndex = trapDisarmedIndex(trap_type);
    } else {
      srcIndex = trapSpriteIndex(trap_type);
    }

    if (srcIndex == null) continue;

    const { sx, sy } = getSourceXY(srcIndex);
    const dx = x * DEST_TILE_SIZE;
    const dy = y * DEST_TILE_SIZE;

    ctx.drawImage(
      terrainFeaturesImg,
      sx, sy, SOURCE_TILE_SIZE, SOURCE_TILE_SIZE,
      dx, dy, DEST_TILE_SIZE, DEST_TILE_SIZE
    );
  }
}
