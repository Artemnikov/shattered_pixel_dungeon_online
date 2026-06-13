import { TILE_SIZE } from '../../constants';
import { drawSpriteTile, fallbackTileMap } from '../sprites';
import { drawSewerTileBase, drawSewerTileCap } from '../sewers/draw';
import { isWallTile } from '../sewers/constants';
import { tilesForDepth } from '../regions';
import { VIS_DISCOVERED, VIS_UNSEEN, wallEdgeDarkness } from './wallFog';

const dimCell = (ctx, x, y) => {
  ctx.fillStyle = 'rgba(0, 0, 0, 0.6)';
  ctx.fillRect(x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE);
};

// Soft diagonal fog edge for wall corners (mirrors SPD FogOfWar's
// left/right half-cell split for wall tiles).
const HALF_TILE = TILE_SIZE / 2;
const dimHalf = (ctx, x, y, side, darkness) => {
  if (darkness === VIS_DISCOVERED) ctx.fillStyle = 'rgba(0, 0, 0, 0.6)';
  else if (darkness === VIS_UNSEEN) ctx.fillStyle = 'rgba(0, 0, 0, 1)';
  else return;
  const dx = x * TILE_SIZE + (side === 'right' ? HALF_TILE : 0);
  ctx.fillRect(dx, y * TILE_SIZE, HALF_TILE, TILE_SIZE);
};

const dimWallCell = (ctx, grid, vision, x, y) => {
  const { left, right } = wallEdgeDarkness(grid, vision, x, y);
  dimHalf(ctx, x, y, 'left', left);
  dimHalf(ctx, x, y, 'right', right);
};

// Reused offscreen canvas: one pixel per tile, alpha = fog darkness.
// Drawing it scaled up with bilinear smoothing softens LOS edges in all
// directions (including diagonals), mirroring SPD's FogOfWar texture.
const fogCanvas = document.createElement('canvas');
const fogCtx = fogCanvas.getContext('2d');

const drawFogOverlay = (ctx, fogAlpha, cols, rows) => {
  if (fogCanvas.width !== cols || fogCanvas.height !== rows) {
    fogCanvas.width = cols;
    fogCanvas.height = rows;
  }
  fogCtx.putImageData(new ImageData(fogAlpha, cols, rows), 0, 0);

  ctx.save();
  ctx.imageSmoothingEnabled = true;
  ctx.drawImage(fogCanvas, 0, 0, cols, rows, 0, 0, cols * TILE_SIZE, rows * TILE_SIZE);
  ctx.restore();
};

export function drawGrid(ctx, { grid, depth, assetImages, visionRef, openDoorsRef }) {
  // SPD tile-sheets share the same atlas layout per region — pick the
  // right PNG for this depth, then run the same autotiler pipeline.
  const regionTiles = tilesForDepth(assetImages, depth);

  const rows = grid.length;
  const cols = rows > 0 ? grid[0].length : 0;
  const fogAlpha = new Uint8ClampedArray(cols * rows * 4);
  const wallCells = [];

  for (let y = 0; y < grid.length; y++) {
    for (let x = 0; x < grid[y].length; x++) {
      const tile = grid[y][x];
      if (tile === 0) {
        ctx.fillStyle = 'black';
        ctx.fillRect(x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE);
        continue;
      }

      const key = `${x},${y}`;
      const isVisible = visionRef.current.visible.has(key);
      const isDiscovered = visionRef.current.discovered.has(key);

      if (!isDiscovered) {
        ctx.fillStyle = 'black';
        ctx.fillRect(x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE);
        fogAlpha[(y * cols + x) * 4 + 3] = 255;
        continue;
      }

      let tileDrawn = false;

      if (regionTiles) {
        tileDrawn = drawSewerTileBase(
          ctx,
          regionTiles,
          grid,
          x,
          y,
          tile,
          openDoorsRef.current
        );
      }

      if (!tileDrawn) {
        const tileCoords = fallbackTileMap[tile];
        if (tileCoords && regionTiles) {
          drawSpriteTile(ctx, regionTiles, tileCoords, x, y);
          tileDrawn = true;
        }
      }

      if (!tileDrawn) {
        if (tile === 3) ctx.fillStyle = '#855';
        else if (tile === 4) ctx.fillStyle = '#aa4';
        else if (tile === 5) ctx.fillStyle = '#4aa';
        else if (tile === 6) ctx.fillStyle = '#6f5234';
        else if (tile === 7) ctx.fillStyle = '#2f5f7a';
        else if (tile === 8) ctx.fillStyle = '#666';
        else if (tile === 9) ctx.fillStyle = '#3f7f3f';
        else if (tile === 10) ctx.fillStyle = '#8a5d23';
        else ctx.fillStyle = '#222';
        ctx.fillRect(x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE);
      }

      fogAlpha[(y * cols + x) * 4 + 3] = isVisible ? 0 : 153;
      if (isWallTile(tile)) wallCells.push([x, y]);
    }
  }

  if (cols > 0 && rows > 0) drawFogOverlay(ctx, fogAlpha, cols, rows);

  // Crisp corner-split darkness for walls, drawn on top of the soft overlay.
  for (const [x, y] of wallCells) {
    dimWallCell(ctx, grid, visionRef.current, x, y);
  }
}

// Second pass: wall overhangs drawn AFTER items / mobs / players so chars
// are partially obscured by the wall top, mirroring the upper half of SPD's
// DungeonWallsTilemap. Door caps live in the base pass (drawSewerTileBase)
// so doors never obscure chars.
export function drawGridCaps(ctx, { grid, depth, assetImages, visionRef }) {
  const regionTiles = tilesForDepth(assetImages, depth);
  if (!regionTiles) return;

  for (let y = 0; y < grid.length; y++) {
    for (let x = 0; x < grid[y].length; x++) {
      const tile = grid[y][x];
      if (tile === 0) continue;

      const key = `${x},${y}`;
      if (!visionRef.current.discovered.has(key)) continue;

      const drew = drawSewerTileCap(ctx, regionTiles, grid, x, y, tile);
      if (!drew) continue;

      if (isWallTile(tile)) {
        dimWallCell(ctx, grid, visionRef.current, x, y);
      } else if (!visionRef.current.visible.has(key)) {
        dimCell(ctx, x, y);
      }
    }
  }
}
