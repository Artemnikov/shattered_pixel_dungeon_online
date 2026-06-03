import { PROJECTILE_SPEED, TILE_SIZE, TILE_SCALE } from '../../constants';

const PROJECTILE_ROTATION_SPEED = 0.15;

const PROJECTILE_SPRITE_MAP = {
  arrow: [0, 9],
  magic_bolt: [0, 13],
  users_projectile: [3, 9],
  stone: [3, 9],
  boomerang: [12, 9],
  dagger: [2, 9],
};

export function advanceAndDrawProjectiles(ctx, { projectilesRef, assetImages }) {
  const finishedIndices = [];
  const itemsImg = assetImages?.items;
  projectilesRef.current.forEach((proj, index) => {
    const dx = proj.targetX - proj.startX;
    const dy = proj.targetY - proj.startY;
    const dist = Math.sqrt(dx * dx + dy * dy);

    proj.progress += PROJECTILE_SPEED * 15;

    const ratio = dist > 0 ? Math.min(1, proj.progress / dist) : 1;
    proj.x = proj.startX + dx * ratio;
    proj.y = proj.startY + dy * ratio;

    if (ratio >= 1) {
      proj.finished = true;
      finishedIndices.push(index);
    }

    proj.rotation += PROJECTILE_ROTATION_SPEED;

    if (itemsImg) {
      const spriteSize = TILE_SIZE / TILE_SCALE;
      const coords = proj.spriteCoords || PROJECTILE_SPRITE_MAP[proj.type] || [3, 9];
      const sx = coords[0] * spriteSize;
      const sy = coords[1] * spriteSize;

      ctx.save();
      ctx.translate(proj.x, proj.y);
      ctx.rotate(proj.rotation);
      ctx.drawImage(
        itemsImg,
        sx, sy,
        spriteSize, spriteSize,
        -TILE_SIZE / 2, -TILE_SIZE / 2,
        TILE_SIZE, TILE_SIZE
      );
      ctx.restore();
    } else {
      ctx.fillStyle = proj.type === 'magic_bolt' ? '#3498db' : '#ecf0f1';
      ctx.beginPath();
      ctx.arc(proj.x, proj.y, 4, 0, Math.PI * 2);
      ctx.fill();
    }
  });

  for (let i = finishedIndices.length - 1; i >= 0; i--) {
    projectilesRef.current.splice(finishedIndices[i], 1);
  }
}
