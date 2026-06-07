import { TILE_SIZE } from '../../constants';
import {
  FRAME_W,
  FRAME_H,
  SCORPIO_FW,
  GNOLL_FW,
  GNOLL_FH,
  SNAKE_FW,
  SNAKE_FH,
  SNAKE_DEST,
  SKELETON_FW,
  SKELETON_FH,
  SKELETON_DEST,
  THIEF_FW,
  THIEF_FH,
  THIEF_DEST,
  DM100_FW,
  DM100_FH,
  DM100_DEST,
  GUARD_FW,
  GUARD_FH,
  GUARD_DEST,
  GOO_FW,
  GOO_FH,
  GOO_DEST,
  SLIME_FW,
  SLIME_FH,
  SLIME_DEST,
  drawMobSprite,
  getCrabFrame,
  getHermitCrabFrame,
  getGnollFrame,
  getGooFrame,
  getSlimeFrame,
  getRatFrame,
  getSnakeFrame,
  getScorpioFrame,
  getSkeletonFrame,
  getThiefFrame,
  getDM100Frame,
  getGuardFrame,
  getNecromancerFrame,
} from '../mobs';

// Gnoll's 12x15 frame, centered/bottom-aligned in the 32px tile per SPD placement
// (x=(col+0.5)*16-w/2, y=(row+1)*16-h), scaled 2x -> 24x30 at offset (+4,+2).
const GNOLL_DEST = { dx: 4, dy: 2, dw: 24, dh: 30 };

// Track previous ai_state per mob to detect sleeping→hunting transitions.
const prevAiState = {};

export function drawMobs(ctx, { entitiesRef, visionRef, assetImages, mobAnimRef, dyingMobsRef }) {
  const now = performance.now();

  Object.values(entitiesRef.current.mobs).forEach(mob => {
    if (!visionRef.current.visible.has(`${Math.round(mob.renderPos.x)},${Math.round(mob.renderPos.y)}`)) return;

    // Rogue's Shadow Clone: a translucent dark copy of the rogue hero sprite.
    if (mob.type === 'shadow_clone' && assetImages.rogue) {
      const cx = mob.renderPos.x * TILE_SIZE;
      const cy = mob.renderPos.y * TILE_SIZE;
      const fw = 12;
      const dw = fw * (TILE_SIZE / 16);
      const off = (TILE_SIZE - dw) / 2;
      ctx.save();
      ctx.globalAlpha = 0.7;
      ctx.drawImage(assetImages.rogue, 0, 0, fw, 16, cx + off, cy, dw, TILE_SIZE);
      // Darken toward shadow.
      ctx.globalCompositeOperation = 'source-atop';
      ctx.globalAlpha = 0.5;
      ctx.fillStyle = '#000';
      ctx.fillRect(cx + off, cy, dw, TILE_SIZE);
      ctx.restore();
      const w = TILE_SIZE - 8;
      const pct = (mob.hp || 0) / (mob.max_hp || 1);
      ctx.fillStyle = '#111';
      ctx.fillRect(cx + 4, cy - 4, w, 3);
      ctx.fillStyle = '#9b59b6';
      ctx.fillRect(cx + 4, cy - 4, w * pct, 3);
      return;
    }

    let mobSprite = assetImages.rat;
    let sx = 0;
    if (mob.name === 'Rat') {
      mobSprite = assetImages.rat;
      sx = getRatFrame(mob, mobAnimRef.current, now);
    } else if (mob.name === 'Crab') {
      mobSprite = assetImages.crab;
      sx = getCrabFrame(mob, mobAnimRef.current, now);
    } else if (mob.name === 'Hermit Crab') {
      mobSprite = assetImages.crab;
      sx = getHermitCrabFrame(mob, mobAnimRef.current, now);
    } else if (mob.name === 'Slime' || mob.name === 'Caustic Slime') {
      mobSprite = assetImages.slime;
      sx = getSlimeFrame(mob, mobAnimRef.current, now);
    } else if (mob.name === 'Snake') {
      mobSprite = assetImages.snake;
      sx = getSnakeFrame(mob, mobAnimRef.current, now);
    } else if (mob.name === 'Bat') {
      mobSprite = assetImages.bat;
    } else if (mob.name === 'Gnoll') {
      mobSprite = assetImages.gnoll;
      sx = getGnollFrame(mob, mobAnimRef.current, now);
    } else if (mob.name === 'Goo') {
      mobSprite = assetImages.goo;
      sx = getGooFrame(mob, mobAnimRef.current, now);
    } else if (mob.name === 'Scorpio') {
      mobSprite = assetImages.scorpio;
      sx = getScorpioFrame(mob, mobAnimRef.current, now);
    } else if (mob.name === 'Skeleton') {
      mobSprite = assetImages.skeleton;
      sx = getSkeletonFrame(mob, mobAnimRef.current, now);
    } else if (mob.name === 'Thief') {
      mobSprite = assetImages.thief;
      sx = getThiefFrame(mob, mobAnimRef.current, now);
    } else if (mob.name === 'DM-100') {
      mobSprite = assetImages.dm100;
      sx = getDM100Frame(mob, mobAnimRef.current, now);
    } else if (mob.name === 'Guard') {
      mobSprite = assetImages.guard;
      sx = getGuardFrame(mob, mobAnimRef.current, now);
    } else if (mob.name === 'Necromancer') {
      mobSprite = assetImages.necromancer;
      sx = getNecromancerFrame(mob, mobAnimRef.current, now);
    }

    const isScorpio = mob.name === 'Scorpio';
    const isCrab = mob.name === 'Crab';
    const isHermitCrab = mob.name === 'Hermit Crab';
    const isSlime = mob.name === 'Slime';
    const isCausticSlime = mob.name === 'Caustic Slime';
    const isGnoll = mob.name === 'Gnoll';
    const isSnake = mob.name === 'Snake';
    const isSkeleton = mob.name === 'Skeleton';
    const isThief = mob.name === 'Thief';
    const isDM100 = mob.name === 'DM-100';
    const isGuard = mob.name === 'Guard';
    const isGoo = mob.name === 'Goo';
    const flash = !!(mobAnimRef.current[mob.id]?.flashUntil && now < mobAnimRef.current[mob.id].flashUntil);
    if (isGnoll) {
      drawMobSprite(ctx, mob, mobSprite, sx, GNOLL_FW, GNOLL_FH, flash, GNOLL_DEST);
    } else if (isSnake) {
      drawMobSprite(ctx, mob, mobSprite, sx, SNAKE_FW, SNAKE_FH, flash, SNAKE_DEST);
    } else if (isSkeleton) {
      drawMobSprite(ctx, mob, mobSprite, sx, SKELETON_FW, SKELETON_FH, flash, SKELETON_DEST);
    } else if (isThief) {
      drawMobSprite(ctx, mob, mobSprite, sx, THIEF_FW, THIEF_FH, flash, THIEF_DEST);
    } else if (isDM100) {
      drawMobSprite(ctx, mob, mobSprite, sx, DM100_FW, DM100_FH, flash, DM100_DEST);
    } else if (isGuard) {
      drawMobSprite(ctx, mob, mobSprite, sx, GUARD_FW, GUARD_FH, flash, GUARD_DEST);
    } else if (isGoo) {
      drawMobSprite(ctx, mob, mobSprite, sx, GOO_FW, GOO_FH, flash, GOO_DEST);
    } else if (isCrab || isHermitCrab) {
      // crab.png stacks variants in 16px rows: Crab = row 0, Hermit Crab = row 1.
      drawMobSprite(ctx, mob, mobSprite, sx, FRAME_W, FRAME_H, flash, null, 1, isHermitCrab ? FRAME_H : 0);
    } else if (isSlime || isCausticSlime) {
      // slime.png stacks variants in 12px rows: Slime = row 0, Caustic Slime = row 1.
      drawMobSprite(ctx, mob, mobSprite, sx, SLIME_FW, SLIME_FH, flash, SLIME_DEST, 1, isCausticSlime ? SLIME_FH : 0);
    } else {
      drawMobSprite(ctx, mob, mobSprite, sx,
        isScorpio ? SCORPIO_FW : FRAME_W,
        isScorpio ? SCORPIO_FW : FRAME_W,
        flash);
    }

    const x = mob.renderPos.x * TILE_SIZE;
    const y = mob.renderPos.y * TILE_SIZE;
    const mobHpBarWidth = TILE_SIZE - 8;
    const mobHpPercent = (mob.hp || 0) / (mob.max_hp || 1);
    ctx.fillStyle = '#111';
    ctx.fillRect(x + 4, y - 4, mobHpBarWidth, 3);
    ctx.fillStyle = '#e74c3c';
    ctx.fillRect(x + 4, y - 4, mobHpBarWidth * mobHpPercent, 3);

    // Sleeping indicator: "Zzz" float above sleeping mobs
    if (mob.ai_state === 'sleeping') {
      ctx.font = `${TILE_SIZE * 0.4}px sans-serif`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'bottom';
      ctx.strokeStyle = 'rgba(0,0,0,0.6)';
      ctx.lineWidth = 2;
      const zzz = '💤 Zzz';
      ctx.strokeText(zzz, x + TILE_SIZE / 2, y - 6);
      ctx.fillStyle = '#aac';
      ctx.fillText(zzz, x + TILE_SIZE / 2, y - 6);
    }

    // Alert indicator: "!" when mob transitions to hunting
    const prev = prevAiState[mob.id];
    if (prev && prev !== 'hunting' && mob.ai_state === 'hunting') {
      const cx = x + TILE_SIZE / 2;
      const cy = y - 8;
      ctx.font = `bold ${TILE_SIZE * 0.6}px sans-serif`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'bottom';
      ctx.strokeStyle = '#000';
      ctx.lineWidth = 3;
      ctx.strokeText('!', cx, cy + 4);
      ctx.fillStyle = '#ff0';
      ctx.fillText('!', cx, cy + 4);
    }
    prevAiState[mob.id] = mob.ai_state;
  });

  Object.entries(dyingMobsRef.current).forEach(([id, mob]) => {
    const elapsed = now - mob.deathStart;
    const isScorpioDeath = mob.name === 'Scorpio';
    const isGooDeath = mob.name === 'Goo';
    const isRatDeath = mob.name === 'Rat';
    const isCrabDeath = mob.name === 'Crab';
    const isHermitCrabDeath = mob.name === 'Hermit Crab';
    const isSlimeDeath = mob.name === 'Slime';
    const isCausticSlimeDeath = mob.name === 'Caustic Slime';
    const isSnakeDeath = mob.name === 'Snake';
    const isSkeletonDeath = mob.name === 'Skeleton';
    const isThiefDeath = mob.name === 'Thief';
    const isDM100Death = mob.name === 'DM-100';
    const isGuardDeath = mob.name === 'Guard';
    const isNecromancerDeath = mob.name === 'Necromancer';
    // Gnoll: die frames [8,9,10] over 250ms, then a 3s alpha fade (SPD AlphaTweener).
    // Snake: die frames [11,12,13] over 300ms, then a 3s alpha fade.
    const deathDuration = isScorpioDeath ? 417 : isGooDeath ? 300 : isRatDeath ? 400 : (isCrabDeath || isHermitCrabDeath) ? 333 : (isSlimeDeath || isCausticSlimeDeath) ? 400 : isSnakeDeath ? 3300 : isSkeletonDeath ? 332 : isThiefDeath ? 500 : isDM100Death ? 498 : isGuardDeath ? 500 : isNecromancerDeath ? 400 : 3250;
    if (elapsed > deathDuration) { delete dyingMobsRef.current[id]; return; }
    if (!visionRef.current.visible.has(`${Math.round(mob.renderPos.x)},${Math.round(mob.renderPos.y)}`)) return;
    if (isScorpioDeath) {
      const fi = Math.min(Math.floor(elapsed / 83), 4);
      drawMobSprite(ctx, mob, assetImages.scorpio, [0, 7, 8, 9, 10][fi] * SCORPIO_FW, SCORPIO_FW, SCORPIO_FW);
    } else if (isGooDeath) {
      const fi = Math.min(Math.floor(elapsed / 100), 2);
      drawMobSprite(ctx, mob, assetImages.goo, [5, 6, 7][fi] * GOO_FW, GOO_FW, GOO_FH, false, GOO_DEST);
    } else if (isRatDeath) {
      const fi = Math.min(Math.floor(elapsed / 100), 3);
      drawMobSprite(ctx, mob, assetImages.rat, [11, 12, 13, 14][fi] * FRAME_W);
    } else if (isCrabDeath || isHermitCrabDeath) {
      const fi = Math.min(Math.floor(elapsed / 83), 3);
      const sy = isHermitCrabDeath ? FRAME_H : 0;
      drawMobSprite(ctx, mob, assetImages.crab, [10, 11, 12, 13][fi] * FRAME_W, FRAME_W, FRAME_H, false, null, 1, sy);
    } else if (isSlimeDeath || isCausticSlimeDeath) {
      const fi = Math.min(Math.floor(elapsed / 100), 3);
      const sy = isCausticSlimeDeath ? SLIME_FH : 0;
      drawMobSprite(ctx, mob, assetImages.slime, [0, 5, 6, 7][fi] * SLIME_FW, SLIME_FW, SLIME_FH, false, SLIME_DEST, 1, sy);
    } else if (isSkeletonDeath) {
      const fi = Math.min(Math.floor(elapsed / 83), 3);
      drawMobSprite(ctx, mob, assetImages.skeleton, [10, 11, 12, 13][fi] * SKELETON_FW, SKELETON_FW, SKELETON_FH, false, SKELETON_DEST);
    } else if (isThiefDeath) {
      const fi = Math.min(Math.floor(elapsed / 100), 4);
      drawMobSprite(ctx, mob, assetImages.thief, [5, 6, 7, 8, 9][fi] * THIEF_FW, THIEF_FW, THIEF_FH, false, THIEF_DEST);
    } else if (isDM100Death) {
      const fi = Math.min(Math.floor(elapsed / 83), 5);
      drawMobSprite(ctx, mob, assetImages.dm100, [10, 11, 12, 13, 14, 15][fi] * DM100_FW, DM100_FW, DM100_FH, false, DM100_DEST);
    } else if (isGuardDeath) {
      const fi = Math.min(Math.floor(elapsed / 125), 3);
      drawMobSprite(ctx, mob, assetImages.guard, [11, 12, 13, 14][fi] * GUARD_FW, GUARD_FW, GUARD_FH, false, GUARD_DEST);
    } else if (isNecromancerDeath) {
      const fi = Math.min(Math.floor(elapsed / 100), 3);
      drawMobSprite(ctx, mob, assetImages.necromancer, [9, 10, 11, 12][fi] * FRAME_W, FRAME_W, FRAME_W);
    } else if (isSnakeDeath) {
      const fi = Math.min(Math.floor(elapsed / 100), 2);
      const sx = [11, 12, 13][fi] * SNAKE_FW;
      const alpha = elapsed <= 300 ? 1 : Math.max(0, 1 - (elapsed - 300) / 3000);
      drawMobSprite(ctx, mob, assetImages.snake, sx, SNAKE_FW, SNAKE_FH, false, SNAKE_DEST, alpha);
    } else {
      // Gnoll death: [8,9,10] @ 83ms, then hold frame 10 and fade alpha 1->0 over 3s.
      const fi = Math.min(Math.floor(elapsed / 83), 2);
      const sx = [8, 9, 10][fi] * GNOLL_FW;
      const alpha = elapsed <= 250 ? 1 : Math.max(0, 1 - (elapsed - 250) / 3000);
      drawMobSprite(ctx, mob, assetImages.gnoll, sx, GNOLL_FW, GNOLL_FH, false, GNOLL_DEST, alpha);
    }
  });
}
