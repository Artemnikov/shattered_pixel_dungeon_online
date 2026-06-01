import { TILE_SIZE } from '../../constants';
import {
  FRAME_W,
  SCORPIO_FW,
  GNOLL_FW,
  GNOLL_FH,
  drawMobSprite,
  getGnollFrame,
  getGooFrame,
  getRatFrame,
  getScorpioFrame,
} from '../mobs';

// Gnoll's 12x15 frame, centered/bottom-aligned in the 32px tile per SPD placement
// (x=(col+0.5)*16-w/2, y=(row+1)*16-h), scaled 2x -> 24x30 at offset (+4,+2).
const GNOLL_DEST = { dx: 4, dy: 2, dw: 24, dh: 30 };

export function drawMobs(ctx, { entitiesRef, visionRef, assetImages, mobAnimRef, dyingMobsRef }) {
  const now = performance.now();

  Object.values(entitiesRef.current.mobs).forEach(mob => {
    if (!visionRef.current.visible.has(`${Math.round(mob.renderPos.x)},${Math.round(mob.renderPos.y)}`)) return;

    let mobSprite = assetImages.rat;
    let sx = 0;
    if (mob.name === 'Rat') {
      mobSprite = assetImages.rat;
      sx = getRatFrame(mob, mobAnimRef.current, now);
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
    }

    const isScorpio = mob.name === 'Scorpio';
    const isGnoll = mob.name === 'Gnoll';
    const flash = !!(mobAnimRef.current[mob.id]?.flashUntil && now < mobAnimRef.current[mob.id].flashUntil);
    if (isGnoll) {
      drawMobSprite(ctx, mob, mobSprite, sx, GNOLL_FW, GNOLL_FH, flash, GNOLL_DEST);
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
  });

  Object.entries(dyingMobsRef.current).forEach(([id, mob]) => {
    const elapsed = now - mob.deathStart;
    const isScorpioDeath = mob.name === 'Scorpio';
    const isGooDeath = mob.name === 'Goo';
    const isRatDeath = mob.name === 'Rat';
    // Gnoll: die frames [8,9,10] over 250ms, then a 3s alpha fade (SPD AlphaTweener).
    const deathDuration = isScorpioDeath ? 417 : isGooDeath ? 300 : isRatDeath ? 400 : 3250;
    if (elapsed > deathDuration) { delete dyingMobsRef.current[id]; return; }
    if (!visionRef.current.visible.has(`${Math.round(mob.renderPos.x)},${Math.round(mob.renderPos.y)}`)) return;
    if (isScorpioDeath) {
      const fi = Math.min(Math.floor(elapsed / 83), 4);
      drawMobSprite(ctx, mob, assetImages.scorpio, [0, 7, 8, 9, 10][fi] * SCORPIO_FW, SCORPIO_FW, SCORPIO_FW);
    } else if (isGooDeath) {
      const fi = Math.min(Math.floor(elapsed / 100), 2);
      drawMobSprite(ctx, mob, assetImages.goo, [5, 6, 7][fi] * FRAME_W);
    } else if (isRatDeath) {
      const fi = Math.min(Math.floor(elapsed / 100), 3);
      drawMobSprite(ctx, mob, assetImages.rat, [11, 12, 13, 14][fi] * FRAME_W);
    } else {
      // Gnoll death: [8,9,10] @ 83ms, then hold frame 10 and fade alpha 1->0 over 3s.
      const fi = Math.min(Math.floor(elapsed / 83), 2);
      const sx = [8, 9, 10][fi] * GNOLL_FW;
      const alpha = elapsed <= 250 ? 1 : Math.max(0, 1 - (elapsed - 250) / 3000);
      drawMobSprite(ctx, mob, assetImages.gnoll, sx, GNOLL_FW, GNOLL_FH, false, GNOLL_DEST, alpha);
    }
  });
}
