// Boss ability telegraphs (e.g. Goo's pumped-up charge): tints the threatened
// tiles so players can see where the incoming hit will land and step away.
// Mirrors the original SPD's CellEmitter "!!!" warning over Goo's charge target.

import { TILE_SIZE } from '../../constants';

const FILL = 'rgba(200, 40, 30, 0.30)';
const STROKE = 'rgba(255, 90, 70, 0.65)';

export function drawWarnedTiles(ctx, { ref }) {
  const warn = ref?.current;
  if (!warn || !warn.tiles?.length) return;

  if (performance.now() >= warn.untilMs) {
    ref.current = null;
    return;
  }

  ctx.save();
  warn.tiles.forEach(([tx, ty]) => {
    const x = tx * TILE_SIZE;
    const y = ty * TILE_SIZE;
    ctx.fillStyle = FILL;
    ctx.fillRect(x, y, TILE_SIZE, TILE_SIZE);
    ctx.strokeStyle = STROKE;
    ctx.lineWidth = 1.5;
    ctx.strokeRect(x + 0.75, y + 0.75, TILE_SIZE - 1.5, TILE_SIZE - 1.5);
  });
  ctx.restore();
}
