import { TILE_SIZE, TILE_SCALE } from '../constants';
import { drawWhiteSilhouette } from './draw/flash';

export const FRAME_W = TILE_SIZE / TILE_SCALE;
export const FRAME_H = TILE_SIZE / TILE_SCALE;
export const SCORPIO_FW = 17;
// Gnoll uses 12x15 frames in the original SPD sheet (TextureFilm(texture, 12, 15)),
// not the generic 16x16. See draw/mobs.js for the in-tile placement (24x30 @ +4,+2).
export const GNOLL_FW = 12;
export const GNOLL_FH = 15;

// Snake uses 12x11 frames. In-tile placement: 24x22 @ +4,+5 (centered in 32x32).
export const SNAKE_FW = 12;
export const SNAKE_FH = 11;
export const SNAKE_DEST = { dx: 4, dy: 5, dw: 24, dh: 22 };

// Prison mob frame sizes (from SPD sprite classes)
export const SKELETON_FW = 12;
export const SKELETON_FH = 15;
export const SKELETON_DEST = { dx: 4, dy: 1, dw: 24, dh: 30 };

export const THIEF_FW = 12;
export const THIEF_FH = 13;
export const THIEF_DEST = { dx: 4, dy: 3, dw: 24, dh: 26 };

export const DM100_FW = 16;
export const DM100_FH = 14;
export const DM100_DEST = { dx: 0, dy: 2, dw: 32, dh: 28 };

export const GUARD_FW = 12;
export const GUARD_FH = 16;
export const GUARD_DEST = { dx: 4, dy: 0, dw: 24, dh: 32 };

// Goo uses 20x14 frames in the original SPD sheet (TextureFilm(texture, 20, 14)), NOT the
// generic 16x16 — slicing at 16 grabs a sliver straddling two real frames and garbles the
// animation. Native 20x14 scaled 2x -> 40x28, centered in the 32px tile so Goo overhangs the
// tile edges (it is bigger than one tile in the original): @ (-4, +2).
export const GOO_FW = 20;
export const GOO_FH = 14;
export const GOO_DEST = { dx: -4, dy: 2, dw: 40, dh: 28 };

const isEntityMoving = (mob) =>
  mob.targetPos &&
  (Math.abs(mob.targetPos.x - mob.renderPos.x) > 0.05 ||
   Math.abs(mob.targetPos.y - mob.renderPos.y) > 0.05);

export const getGooFrame = (mob, mobAnim, now) => {
  const anim = mobAnim[mob.id] || {};
  // Pumped-up charge: play the pump frames [4,3,2,1,0] while the boss winds up (anim.pumpUntil
  // set from the backend telegraph events), and the pump-release frame 7 on the burst.
  const isPumping = anim.pumpUntil && now < anim.pumpUntil;
  const isAttacking = anim.attackUntil && now < anim.attackUntil;
  if (isAttacking) {
    const elapsed = now - (anim.attackUntil - 300);
    const fi = Math.min(Math.floor(elapsed / 100), 2);
    return [8, 9, 10][fi] * GOO_FW;
  }
  if (isPumping) {
    return [4, 3, 2, 1, 0][Math.floor(now / 50) % 5] * GOO_FW;
  }
  if (isEntityMoving(mob)) return [3, 2, 1, 2][Math.floor(now / 67) % 4] * GOO_FW;
  return [2, 1, 0, 0, 1][Math.floor(now / 100) % 5] * GOO_FW;
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

export const getSkeletonFrame = (mob, mobAnim, now) => {
  const anim = mobAnim[mob.id] || {};
  const isAttacking = anim.attackUntil && now < anim.attackUntil;
  if (isAttacking) {
    const elapsed = now - (anim.attackUntil - 200);
    const fi = Math.min(Math.floor(elapsed / 67), 2);
    return [14, 15, 16][fi] * SKELETON_FW;
  }
  if (isEntityMoving(mob)) {
    return [4, 5, 6, 7, 8, 9][Math.floor(now / 67) % 6] * SKELETON_FW;
  }
  return [0,0,0,0,0,0,0,0,0,0,0,0,0,1,2,3][Math.floor(now / 83) % 16] * SKELETON_FW;
};

export const getThiefFrame = (mob, mobAnim, now) => {
  const anim = mobAnim[mob.id] || {};
  const isAttacking = anim.attackUntil && now < anim.attackUntil;
  if (isAttacking) {
    const elapsed = now - (anim.attackUntil - 333);
    const fi = Math.min(Math.floor(elapsed / 83), 3);
    return [10, 11, 12, 0][fi] * THIEF_FW;
  }
  if (isEntityMoving(mob)) {
    return [0, 0, 2, 3, 3, 4][Math.floor(now / 67) % 6] * THIEF_FW;
  }
  return [0, 0, 0, 1, 0, 0, 0, 0, 1][Math.floor(now / 1000) % 9] * THIEF_FW;
};

export const getDM100Frame = (mob, mobAnim, now) => {
  const anim = mobAnim[mob.id] || {};
  const isAttacking = anim.attackUntil && now < anim.attackUntil;
  if (isAttacking) {
    const elapsed = now - (anim.attackUntil - 250);
    const fi = Math.min(Math.floor(elapsed / 63), 3);
    return [2, 3, 4, 0][fi] * DM100_FW;
  }
  if (isEntityMoving(mob)) {
    return [6, 7, 8, 9][Math.floor(now / 83) % 4] * DM100_FW;
  }
  return [0, 1][Math.floor(now / 1000) % 2] * DM100_FW;
};

export const getGuardFrame = (mob, mobAnim, now) => {
  const anim = mobAnim[mob.id] || {};
  const isAttacking = anim.attackUntil && now < anim.attackUntil;
  if (isAttacking) {
    const elapsed = now - (anim.attackUntil - 250);
    const fi = Math.min(Math.floor(elapsed / 83), 2);
    return [8, 9, 10][fi] * GUARD_FW;
  }
  if (isEntityMoving(mob)) {
    return [2, 3, 4, 5, 6, 7][Math.floor(now / 67) % 6] * GUARD_FW;
  }
  return [0, 0, 0, 1, 0, 0, 1, 1][Math.floor(now / 500) % 8] * GUARD_FW;
};

export const getNecromancerFrame = (mob, mobAnim, now) => {
  const anim = mobAnim[mob.id] || {};
  const isAttacking = anim.attackUntil && now < anim.attackUntil;
  if (isAttacking) {
    const elapsed = now - (anim.attackUntil - 400);
    const fi = Math.min(Math.floor(elapsed / 100), 3);
    return [5, 6, 7, 8][fi] * FRAME_W;
  }
  if (isEntityMoving(mob)) {
    return [0, 0, 0, 2, 3, 4][Math.floor(now / 125) % 6] * FRAME_W;
  }
  return [0, 0, 0, 1, 0, 0, 0, 0, 1][Math.floor(now / 1000) % 9] * FRAME_W;
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

// Faithful to original SPD SnakeSprite (12x11 frames, row 0):
//   idle   10fps loop  0(x15), 1(x10), 2, 3, 2, 1(x2) = 30 frames, 3s loop
//   run     8fps loop  [4,5,6,7] = 4 frames, 0.5s loop
//   attack 15fps once  [8,9,10,9,0] = 5 frames, ~333ms
//   die    10fps once  [11,12,13] = 3 frames, 300ms (death handled in draw/mobs.js)
export const getSnakeFrame = (mob, mobAnim, now) => {
  const anim = mobAnim[mob.id] || {};
  const isAttacking = anim.attackUntil && now < anim.attackUntil;
  if (isAttacking) {
    const elapsed = now - (anim.attackUntil - 333);
    const fi = Math.min(Math.floor(elapsed / 67), 4);
    return [8, 9, 10, 9, 0][fi] * SNAKE_FW;
  }
  if (isEntityMoving(mob)) {
    return [4, 5, 6, 7][Math.floor(now / 125) % 4] * SNAKE_FW;
  }
  return [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0, 1,1,1,1,1,1,1,1,1,1, 2,3,2,1,1][Math.floor(now / 100) % 30] * SNAKE_FW;
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
