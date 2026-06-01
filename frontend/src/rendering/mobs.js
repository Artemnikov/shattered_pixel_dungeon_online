import { TILE_SIZE, TILE_SCALE } from '../constants';
import { drawWhiteSilhouette } from './draw/flash';

export const FRAME_W = TILE_SIZE / TILE_SCALE;
export const FRAME_H = TILE_SIZE / TILE_SCALE;
export const SCORPIO_FW = 17;
// Gnoll uses 12x15 frames in the original SPD sheet (TextureFilm(texture, 12, 15)),
// not the generic 16x16. See draw/mobs.js for the in-tile placement (24x30 @ +4,+2).
export const GNOLL_FW = 12;
export const GNOLL_FH = 15;

const isEntityMoving = (mob) =>
  mob.targetPos &&
  (Math.abs(mob.targetPos.x - mob.renderPos.x) > 0.05 ||
   Math.abs(mob.targetPos.y - mob.renderPos.y) > 0.05);

export const getGooFrame = (mob, mobAnim, now) => {
  const anim = mobAnim[mob.id] || {};
  const isAttacking = anim.attackUntil && now < anim.attackUntil;
  if (isAttacking) {
    const elapsed = now - (anim.attackUntil - 300);
    const fi = Math.min(Math.floor(elapsed / 100), 2);
    return [8, 9, 10][fi] * FRAME_W;
  }
  if (isEntityMoving(mob)) return [3, 2, 1, 2][Math.floor(now / 67) % 4] * FRAME_W;
  return [2, 1, 0, 0, 1][Math.floor(now / 100) % 5] * FRAME_W;
};

// Faithful to original SPD GnollSprite (12x15 frames, row 0):
//   idle   2fps loop  [0,0,0,1,0,0,1,1]
//   run   12fps loop  [4,5,6,7]
//   attack 12fps once [2,3,0]
//   die   12fps once  [8,9,10]   (death handled in draw/mobs.js)
export const getGnollFrame = (mob, mobAnim, now) => {
  const anim = mobAnim[mob.id] || {};
  const isAttacking = anim.attackUntil && now < anim.attackUntil;
  if (isAttacking) {
    const elapsed = now - (anim.attackUntil - 250);
    const fi = Math.min(Math.floor(elapsed / 83), 2);
    return [2, 3, 0][fi] * GNOLL_FW;
  }
  if (isEntityMoving(mob)) {
    return [4, 5, 6, 7][Math.floor(now / 83) % 4] * GNOLL_FW;
  }
  return [0, 0, 0, 1, 0, 0, 1, 1][Math.floor(now / 500) % 8] * GNOLL_FW;
};

export const getScorpioFrame = (mob, mobAnim, now) => {
  const anim = mobAnim[mob.id] || {};
  const isAttacking = anim.attackUntil && now < anim.attackUntil;
  if (isAttacking) {
    const elapsed = now - (anim.attackUntil - 200);
    const fi = Math.min(Math.floor(elapsed / 67), 2);
    return [0, 3, 4][fi] * SCORPIO_FW;
  }
  if (isEntityMoving(mob)) return [5, 5, 6, 6][Math.floor(now / 125) % 4] * SCORPIO_FW;
  return [0,0,0,0,0,0,0,0,1,2,1,2,1,2][Math.floor(now / 83) % 14] * SCORPIO_FW;
};

export const getRatFrame = (mob, mobAnim, now) => {
  const anim = mobAnim[mob.id] || {};
  const isAttacking = anim.attackUntil && now < anim.attackUntil;
  if (isAttacking) {
    const elapsed = now - (anim.attackUntil - 333);
    const fi = Math.min(Math.floor(elapsed / 67), 4);
    return [2, 3, 4, 5, 0][fi] * FRAME_W;
  }
  if (isEntityMoving(mob)) {
    return [6, 7, 8, 9, 10][Math.floor(now / 100) % 5] * FRAME_W;
  }
  return [0, 0, 0, 1][Math.floor(now / 500) % 4] * FRAME_W;
};

// dest (optional): in-tile placement {dx,dy,dw,dh} for sprites whose native frame is not a
// full 32x32 tile (e.g. gnoll's 12x15 -> 24x30 @ +4,+2). Omitted = legacy full-tile draw.
// alpha (optional): 0..1 used for the death fade-out.
export const drawMobSprite = (ctx, mob, sprite, sx, fw = FRAME_W, fh = FRAME_H, flash = false, dest = null, alpha = 1) => {
  const x = mob.renderPos.x * TILE_SIZE;
  const y = mob.renderPos.y * TILE_SIZE;
  const dx = dest ? dest.dx : 0;
  const dy = dest ? dest.dy : 0;
  const dw = dest ? dest.dw : TILE_SIZE;
  const dh = dest ? dest.dh : TILE_SIZE;
  if (sprite) {
    ctx.save();
    if (alpha < 1) ctx.globalAlpha = alpha;
    if (mob.facing === 'LEFT') {
      // Mirror around the tile: a sub-rect at left offset dx maps to local TILE_SIZE-dx-dw.
      const lx = TILE_SIZE - dx - dw;
      ctx.translate(x + TILE_SIZE, y);
      ctx.scale(-1, 1);
      ctx.drawImage(sprite, sx, 0, fw, fh, lx, dy, dw, dh);
      if (flash) drawWhiteSilhouette(ctx, sprite, sx, 0, fw, fh, lx, dy, dw, dh);
    } else {
      ctx.drawImage(sprite, sx, 0, fw, fh, x + dx, y + dy, dw, dh);
      if (flash) drawWhiteSilhouette(ctx, sprite, sx, 0, fw, fh, x + dx, y + dy, dw, dh);
    }
    ctx.restore();
  } else {
    ctx.fillStyle = '#e74c3c';
    ctx.fillRect(x + 4, y + 4, TILE_SIZE - 8, TILE_SIZE - 8);
  }
};
