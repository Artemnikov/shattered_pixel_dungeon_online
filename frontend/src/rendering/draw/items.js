import { TILE_SIZE, TILE_SCALE } from '../../constants';
import { coordsForItem } from '../sprites';

export function drawItems(ctx, { entitiesRef, visionRef, assetImages }) {
  if (!entitiesRef.current.items) return;
  entitiesRef.current.items.forEach(item => {
    if (!visionRef.current.visible.has(`${item.pos.x},${item.pos.y}`)) return;

    if (assetImages.items) {
      const coords = coordsForItem(item);
      if (!coords) return;
      ctx.drawImage(
        assetImages.items,
        coords[0] * (TILE_SIZE / TILE_SCALE),
        coords[1] * (TILE_SIZE / TILE_SCALE),
        TILE_SIZE / TILE_SCALE,
        TILE_SIZE / TILE_SCALE,
        item.pos.x * TILE_SIZE,
        item.pos.y * TILE_SIZE,
        TILE_SIZE,
        TILE_SIZE
      );
    } else {
      ctx.fillStyle = item.type === 'weapon' ? '#f1c40f' : '#9b59b6';
      ctx.beginPath();
      ctx.arc(item.pos.x * TILE_SIZE + TILE_SIZE / 2, item.pos.y * TILE_SIZE + TILE_SIZE / 2, 6, 0, Math.PI * 2);
      ctx.fill();
    }
  });
}
