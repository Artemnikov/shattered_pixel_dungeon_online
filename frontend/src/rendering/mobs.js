// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 ArtemNikov
//
// Adapted from Shattered Pixel Dungeon (C) 2014-2024 Evan Debenham
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
// See the GNU General Public License for more details.
//
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

// Slime's 14x12 frame, bottom-aligned in the 32px tile per SPD placement
// (x=(col+0.5)*16-w/2, y=(row+1)*16-h), scaled 2x -> 28x24 at offset (+2,+8).
export const SLIME_FW = 14;
export const SLIME_FH = 12;
export const SLIME_DEST = { dx: 2, dy: 8, dw: 28, dh: 24 };

// --- New mobs (Wraith, Piranha, Mimics, Statues, Bee, DwarfKing arena, Yog-Dzewa arena) ---
// All dest values follow the SPD centering formula: x=(col+0.5)*16-w/2, y=(row+1)*16-h, scaled 2x.

export const WRAITH_FW = 14;
export const WRAITH_FH = 15;
export const WRAITH_DEST = { dx: 2, dy: 2, dw: 28, dh: 30 };

export const PIRANHA_FW = 12;
export const PIRANHA_FH = 16;
export const PIRANHA_DEST = { dx: 4, dy: 0, dw: 24, dh: 32 };

export const STATUE_FW = 12;
export const STATUE_FH = 15;
export const STATUE_DEST = { dx: 4, dy: 2, dw: 24, dh: 30 };

export const GHOUL_FW = 12;
export const GHOUL_FH = 14;
export const GHOUL_DEST = { dx: 4, dy: 4, dw: 24, dh: 28 };

export const MONK_FW = 15;
export const MONK_FH = 14;
export const MONK_DEST = { dx: 1, dy: 4, dw: 30, dh: 28 };

export const WARLOCK_FW = 12;
export const WARLOCK_FH = 15;
export const WARLOCK_DEST = { dx: 4, dy: 2, dw: 24, dh: 30 };

export const GOLEM_FW = 17;
export const GOLEM_FH = 19;
export const GOLEM_DEST = { dx: -1, dy: -6, dw: 34, dh: 38 };

export const YOG_FW = 20;
export const YOG_FH = 19;
export const YOG_DEST = { dx: -4, dy: -6, dw: 40, dh: 38 };

export const FIST_FW = 24;
export const FIST_FH = 17;
export const FIST_DEST = { dx: -8, dy: -2, dw: 48, dh: 34 };

export const EYE_FW = 16;
export const EYE_FH = 18;
export const EYE_DEST = { dx: 0, dy: -4, dw: 32, dh: 36 };

export const RIPPER_FW = 15;
export const RIPPER_FH = 14;
export const RIPPER_DEST = { dx: 1, dy: 4, dw: 30, dh: 28 };

export const PYLON_FW = 10;
export const PYLON_FH = 20;
export const PYLON_DEST = { dx: 6, dy: -8, dw: 20, dh: 40 };

// Tengu (floor 10 boss): 14x16 frames (TenguSprite TextureFilm(texture, 14, 16)), tengu.png
// is a single row (256x16 -> 18 frames). 16x16 cell, 2x scale -> dx=2, dy=0, dw=28, dh=32.
export const TENGU_FW = 14;
export const TENGU_FH = 16;
export const TENGU_DEST = { dx: 2, dy: 0, dw: 28, dh: 32 };

// DM-300 (floor 15 boss): 25x22 frames (DM300Sprite TextureFilm(texture, 25, 22)), dm300.png
// is 256x64 = 2 rows of 10 columns (row 0 = normal, row 1 = supercharged/enraged).
export const DM300_FW = 25;
export const DM300_FH = 22;
export const DM300_DEST = { dx: -9, dy: -6, dw: 50, dh: 44 };

// Brute / Armored Brute: 12x16 frames (BruteSprite TextureFilm(texture, 12, 16)), brute.png
// is 256x32 = 2 rows (Brute = row 0, Armored Brute = row 1).
export const BRUTE_FW = 12;
export const BRUTE_FH = 16;
export const BRUTE_DEST = { dx: 4, dy: 0, dw: 24, dh: 32 };

// Swarm: 16x16 frames (SwarmSprite TextureFilm(texture, 16, 16)), swarm.png.
// 16px sprite at 2x scale = full 32x32 tile, no offset needed.
export const SWARM_FW = 16;
export const SWARM_FH = 16;
export const SWARM_DEST = { dx: 0, dy: 0, dw: 32, dh: 32 };

// Shopkeeper: 14x14 frames (ShopkeeperSprite TextureFilm(texture, 14, 14)),
// shopkeeper.png. Centered/bottom-aligned in the 32px tile, scaled 2x -> 28x28 @ +2,+2.
export const KEEPER_FW = 14;
export const KEEPER_FH = 14;
export const KEEPER_DEST = { dx: 2, dy: 2, dw: 28, dh: 28 };

// Imp: 12x14 frames (ImpSprite TextureFilm(texture, 12, 14)), demon.png.
// Centered/bottom-aligned in the 32px tile, scaled 2x -> 24x28 @ +4,+4.
export const IMP_FW = 12;
export const IMP_FH = 14;
export const IMP_DEST = { dx: 4, dy: 4, dw: 24, dh: 28 };

// Rat King: 16x17 frames (RatKingSprite TextureFilm(texture, 16, 17)), ratking.png.
// Centered/bottom-aligned in the 32px tile, scaled 2x -> 32x34 @ 0,-2.
export const RATKING_FW = 16;
export const RATKING_FH = 17;
export const RATKING_DEST = { dx: 0, dy: -2, dw: 32, dh: 34 };

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

// Faithful to original SPD BanditSprite (12x13 frames, thief.png, same sheet/size as Thief):
//   idle    1fps loop  [21,21,21,22,21,21,21,21,22]
//   run    15fps loop  [21,21,23,24,24,25]
//   attack 12fps once  [31,32,33]    (die handled in draw/mobs.js)
export const getBanditFrame = (mob, mobAnim, now) => {
  const anim = mobAnim[mob.id] || {};
  const isAttacking = anim.attackUntil && now < anim.attackUntil;
  if (isAttacking) {
    const elapsed = now - (anim.attackUntil - 250);
    const fi = Math.min(Math.floor(elapsed / 83), 2);
    return [31, 32, 33][fi] * THIEF_FW;
  }
  if (isEntityMoving(mob)) {
    return [21, 21, 23, 24, 24, 25][Math.floor(now / 67) % 6] * THIEF_FW;
  }
  return [21, 21, 21, 22, 21, 21, 21, 21, 22][Math.floor(now / 1000) % 9] * THIEF_FW;
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

// Faithful to original SPD SlimeSprite (14x12 frames, row 0 of slime.png):
//   idle    3fps loop  [0,1,1,0]
//   run    10fps loop  [0,2,3,3,2,0]
//   attack 15fps once  [2,3,4,6,5]   ~333ms
//   die    10fps once  [0,5,6,7]     (handled in draw/mobs.js)
// Caustic Slime reuses this (same column indices), drawn from row 1 (sy = SLIME_FH)
// per CausticSlimeSprite's frame offset c=9.
export const getSlimeFrame = (mob, mobAnim, now) => {
  const anim = mobAnim[mob.id] || {};
  const isAttacking = anim.attackUntil && now < anim.attackUntil;
  if (isAttacking) {
    const elapsed = now - (anim.attackUntil - 333);
    const fi = Math.min(Math.floor(elapsed / 67), 4);
    return [2, 3, 4, 6, 5][fi] * SLIME_FW;
  }
  if (isEntityMoving(mob)) {
    return [0, 2, 3, 3, 2, 0][Math.floor(now / 100) % 6] * SLIME_FW;
  }
  return [0, 1, 1, 0][Math.floor(now / 333) % 4] * SLIME_FW;
};

// Faithful to original SPD CrabSprite (16x16 frames, row 0 of crab.png):
//   idle    5fps loop  [0,1,0,2]
//   run    15fps loop  [3,4,5,6]
//   attack 12fps once  [7,8,9]        ~250ms
//   die    12fps once  [10,11,12,13]  (handled in draw/mobs.js)
export const getCrabFrame = (mob, mobAnim, now) => {
  const anim = mobAnim[mob.id] || {};
  const isAttacking = anim.attackUntil && now < anim.attackUntil;
  if (isAttacking) {
    const elapsed = now - (anim.attackUntil - 250);
    const fi = Math.min(Math.floor(elapsed / 83), 2);
    return [7, 8, 9][fi] * FRAME_W;
  }
  if (isEntityMoving(mob)) {
    return [3, 4, 5, 6][Math.floor(now / 67) % 4] * FRAME_W;
  }
  return [0, 1, 0, 2][Math.floor(now / 200) % 4] * FRAME_W;
};

// Hermit Crab: same crab.png sheet, second row (HermitCrabSprite uses frame index +16),
// with a slower 10fps run animation.
export const getHermitCrabFrame = (mob, mobAnim, now) => {
  const anim = mobAnim[mob.id] || {};
  const isAttacking = anim.attackUntil && now < anim.attackUntil;
  if (isAttacking) {
    const elapsed = now - (anim.attackUntil - 250);
    const fi = Math.min(Math.floor(elapsed / 83), 2);
    return [7, 8, 9][fi] * FRAME_W;
  }
  if (isEntityMoving(mob)) {
    return [3, 4, 5, 6][Math.floor(now / 100) % 4] * FRAME_W;
  }
  return [0, 1, 0, 2][Math.floor(now / 200) % 4] * FRAME_W;
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

// Wraith: simple 4-frame idle loop (wraith.png row 0).
export const getWraithFrame = (mob, mobAnim, now) =>
  [0, 1, 2, 1][Math.floor(now / 150) % 4] * WRAITH_FW;

// Piranha / Phantom Piranha: 2-frame idle wiggle.
export const getPiranhaFrame = (mob, mobAnim, now) =>
  [0, 1][Math.floor(now / 250) % 2] * PIRANHA_FW;

// Mimic variants: mostly static (mimics disguise as items until triggered).
export const getMimicFrame = () => 0;

// Bee: simple 2-frame wing flutter.
export const getBeeFrame = (mob, mobAnim, now) =>
  [0, 1][Math.floor(now / 100) % 2] * FRAME_W;

// DwarfKing boss: 2-frame idle loop.
export const getDwarfKingFrame = (mob, mobAnim, now) =>
  [0, 1][Math.floor(now / 400) % 2] * FRAME_W;

// DK Ghoul / Monk / Warlock minions: 2-frame idle loop.
export const getGhoulFrame = (mob, mobAnim, now) =>
  [0, 1][Math.floor(now / 300) % 2] * GHOUL_FW;

export const getMonkFrame = (mob, mobAnim, now) =>
  [0, 1][Math.floor(now / 300) % 2] * MONK_FW;

export const getWarlockFrame = (mob, mobAnim, now) =>
  [0, 1][Math.floor(now / 300) % 2] * WARLOCK_FW;

// DK Golem: heavy, slow 2-frame idle.
export const getGolemFrame = (mob, mobAnim, now) =>
  [0, 1][Math.floor(now / 500) % 2] * GOLEM_FW;

// Yog-Dzewa: slow pulsing idle loop.
export const getYogFrame = (mob, mobAnim, now) =>
  [0, 1, 2, 1][Math.floor(now / 250) % 4] * YOG_FW;

// Yog's Fists: shared 2-frame idle loop across all 6 fist variants (rows differ via sy).
export const getFistFrame = (mob, mobAnim, now) =>
  [0, 1][Math.floor(now / 250) % 2] * FIST_FW;

// Yog Eye: 2-frame idle loop.
export const getEyeFrame = (mob, mobAnim, now) =>
  [0, 1][Math.floor(now / 300) % 2] * EYE_FW;

// Yog Ripper: 2-frame idle loop.
export const getRipperFrame = (mob, mobAnim, now) =>
  [0, 1][Math.floor(now / 250) % 2] * RIPPER_FW;

// Demon Spawner: immobile, single static frame.
export const getSpawnerFrame = () => 0;

// Pylon: immobile, single static frame.
export const getPylonFrame = () => 0;

// Statue: static frame when inactive, simple idle loop once activated.
export const getStatueFrame = (mob, mobAnim, now) =>
  mob.activated ? [0, 1][Math.floor(now / 300) % 2] * STATUE_FW : 0;

// Faithful to original SPD TenguSprite (14x16 frames, single row of tengu.png):
//   idle    2fps loop  [0,0,0,1]
//   run    15fps loop  [2,3,4,5,0]
//   attack 15fps once  [6,7,7,0]    (death handled in draw/mobs.js)
export const getTenguFrame = (mob, mobAnim, now) => {
  const anim = mobAnim[mob.id] || {};
  const isAttacking = anim.attackUntil && now < anim.attackUntil;
  if (isAttacking) {
    const elapsed = now - (anim.attackUntil - 200);
    const fi = Math.min(Math.floor(elapsed / 67), 3);
    return [6, 7, 7, 0][fi] * TENGU_FW;
  }
  if (isEntityMoving(mob)) {
    return [2, 3, 4, 5, 0][Math.floor(now / 67) % 5] * TENGU_FW;
  }
  return [0, 0, 0, 1][Math.floor(now / 500) % 4] * TENGU_FW;
};

// Faithful to original SPD DM300Sprite (25x22 frames, dm300.png is 2 rows of 10 columns:
// row 0 = normal, row 1 = supercharged/enraged):
//   idle    10fps loop  [0,1]
//   run     10fps loop  [0,2]
//   attack  15fps once  [3,4,5]
//   zap     15fps loop  [6,7,7,6]    (die handled in draw/mobs.js)
export const getDM300Frame = (mob, mobAnim, now) => {
  const anim = mobAnim[mob.id] || {};
  const isAttacking = anim.attackUntil && now < anim.attackUntil;
  const isZapping = anim.zapUntil && now < anim.zapUntil;
  if (isAttacking) {
    const elapsed = now - (anim.attackUntil - 200);
    const fi = Math.min(Math.floor(elapsed / 67), 2);
    return [3, 4, 5][fi] * DM300_FW;
  }
  if (isZapping) {
    return [6, 7, 7, 6][Math.floor(now / 67) % 4] * DM300_FW;
  }
  if (isEntityMoving(mob)) {
    return [0, 2][Math.floor(now / 100) % 2] * DM300_FW;
  }
  return [0, 1][Math.floor(now / 100) % 2] * DM300_FW;
};

// Faithful to original SPD BruteSprite (12x16 frames, brute.png is 2 rows: Brute = row 0,
// Armored Brute = row 1):
//   idle    2fps loop  [0,0,0,1,0,0,1,1]
//   run    12fps loop  [4,5,6,7]
//   attack 12fps once  [2,3,0]    (die handled in draw/mobs.js)
export const getBruteFrame = (mob, mobAnim, now) => {
  const anim = mobAnim[mob.id] || {};
  const isAttacking = anim.attackUntil && now < anim.attackUntil;
  if (isAttacking) {
    const elapsed = now - (anim.attackUntil - 250);
    const fi = Math.min(Math.floor(elapsed / 83), 2);
    return [2, 3, 0][fi] * BRUTE_FW;
  }
  if (isEntityMoving(mob)) {
    return [4, 5, 6, 7][Math.floor(now / 83) % 4] * BRUTE_FW;
  }
  return [0, 0, 0, 1, 0, 0, 1, 1][Math.floor(now / 500) % 8] * BRUTE_FW;
};

// Faithful to original SPD SwarmSprite (16x16 frames, swarm.png):
//   idle   15fps loop  [0,1,2,3,4,5] (same as run)
//   run    15fps loop  [0,1,2,3,4,5]
//   attack 20fps once  [6,7,8,9]    (die handled in draw/mobs.js)
export const getSwarmFrame = (mob, mobAnim, now) => {
  const anim = mobAnim[mob.id] || {};
  const isAttacking = anim.attackUntil && now < anim.attackUntil;
  if (isAttacking) {
    const elapsed = now - (anim.attackUntil - 200);
    const fi = Math.min(Math.floor(elapsed / 50), 3);
    return [6, 7, 8, 9][fi] * SWARM_FW;
  }
  return [0, 1, 2, 3, 4, 5][Math.floor(now / 67) % 6] * SWARM_FW;
};

// Faithful to original SPD ShopkeeperSprite (14x14 frames, shopkeeper.png):
//   idle 10fps loop [1,1,1,1,1,0,0,0,0]
export const getKeeperFrame = (mob, mobAnim, now) =>
  [1, 1, 1, 1, 1, 0, 0, 0, 0][Math.floor(now / 100) % 9] * KEEPER_FW;

// Imp: simplified idle wobble loop (full ImpSprite idle is a long mostly-static
// cycle of frames 0/4 with occasional 1-3), demon.png, 12x14 frames.
export const getImpFrame = (mob, mobAnim, now) =>
  [0, 0, 0, 1, 2, 3, 0, 0, 0, 4, 4, 4, 4, 4, 4][Math.floor(now / 100) % 15] * IMP_FW;

// Faithful to original SPD RatKingSprite (16x17 frames, ratking.png):
//   idle 2fps loop [0,0,0,1]
export const getRatKingFrame = (mob, mobAnim, now) =>
  [0, 0, 0, 1][Math.floor(now / 500) % 4] * RATKING_FW;

// dest (optional): in-tile placement {dx,dy,dw,dh} for sprites whose native frame is not a
// full 32x32 tile (e.g. gnoll's 12x15 -> 24x30 @ +4,+2). Omitted = legacy full-tile draw.
// alpha (optional): 0..1 used for the death fade-out.
export const drawMobSprite = (ctx, mob, sprite, sx, fw = FRAME_W, fh = FRAME_H, flash = false, dest = null, alpha = 1, sy = 0, brightness = 1) => {
  const x = mob.renderPos.x * TILE_SIZE;
  const y = mob.renderPos.y * TILE_SIZE;
  const dx = dest ? dest.dx : 0;
  const dy = dest ? dest.dy : 0;
  const dw = dest ? dest.dw : TILE_SIZE;
  const dh = dest ? dest.dh : TILE_SIZE;
  if (sprite) {
    ctx.save();
    if (alpha < 1) ctx.globalAlpha = alpha;
    // NecroSkeleton: 0.75 brightness tint (mirrors NecroSkeletonSprite.resetColor()).
    if (brightness < 1) ctx.filter = `brightness(${brightness * 100}%)`;
    if (mob.facing === 'LEFT') {
      // Mirror around the tile: a sub-rect at left offset dx maps to local TILE_SIZE-dx-dw.
      const lx = TILE_SIZE - dx - dw;
      ctx.translate(x + TILE_SIZE, y);
      ctx.scale(-1, 1);
      ctx.drawImage(sprite, sx, sy, fw, fh, lx, dy, dw, dh);
      if (flash) drawWhiteSilhouette(ctx, sprite, sx, sy, fw, fh, lx, dy, dw, dh);
    } else {
      ctx.drawImage(sprite, sx, sy, fw, fh, x + dx, y + dy, dw, dh);
      if (flash) drawWhiteSilhouette(ctx, sprite, sx, sy, fw, fh, x + dx, y + dy, dw, dh);
    }
    ctx.restore();
  } else {
    ctx.fillStyle = '#e74c3c';
    ctx.fillRect(x + 4, y + 4, TILE_SIZE - 8, TILE_SIZE - 8);
  }
};
