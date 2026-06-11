import { SOURCE_TILE_SIZE, DEST_TILE_SIZE } from '../sewers/constants';

const ATLAS_COLS = 16;

// Decorative custom tilemaps (e.g. GooNest) -- cosmetic floor texture overlay
// drawn on top of the base grid, gated by the same discovered/visible state.
export function drawCustomTiles(ctx, { customTiles, assetImages, visionRef }) {
  if (!customTiles || !customTiles.length) return;

  for (const layer of customTiles) {
    const atlas = assetImages.customTiles?.[layer.texture];
    if (!atlas) continue;

    for (let row = 0; row < layer.h; row++) {
      const tileRow = layer.tiles[row];
      for (let col = 0; col < layer.w; col++) {
        const idx = tileRow[col];
        if (idx < 0) continue;

        const x = layer.x + col;
        const y = layer.y + row;
        const key = `${x},${y}`;
        if (!visionRef.current.discovered.has(key)) continue;

        const sx = (idx % ATLAS_COLS) * SOURCE_TILE_SIZE;
        const sy = Math.floor(idx / ATLAS_COLS) * SOURCE_TILE_SIZE;
        ctx.drawImage(
          atlas,
          sx, sy, SOURCE_TILE_SIZE, SOURCE_TILE_SIZE,
          x * DEST_TILE_SIZE, y * DEST_TILE_SIZE, DEST_TILE_SIZE, DEST_TILE_SIZE
        );
      }
    }
  }
}
