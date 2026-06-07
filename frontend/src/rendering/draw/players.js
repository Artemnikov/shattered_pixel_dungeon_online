import { TILE_SIZE, TILE_SCALE, PLAYER_ATTACK_DURATION, PLAYER_OPERATE_DURATION } from '../../constants';
import { drawWhiteSilhouette } from './flash';

export function drawPlayers(ctx, { entitiesRef, visionRef, assetImages, playerAnimRef, myPlayerId }) {
  Object.values(entitiesRef.current.players).forEach(player => {
    const isPlayerVisible = visionRef.current.visible.has(`${Math.round(player.renderPos.x)},${Math.round(player.renderPos.y)}`) || player.id === myPlayerId;
    if (!isPlayerVisible) return;

    const x = player.renderPos.x * TILE_SIZE;
    const y = player.renderPos.y * TILE_SIZE;

    // Map class -> sheet key directly. assetImages[key] is null until that sheet
    // loads, and the `if (playerSprite)` guard below skips drawing until then, so
    // a known class never flashes as the warrior fallback during load.
    const CLASS_KEYS = { warrior: 'warrior', mage: 'mage', rogue: 'rogue', huntress: 'huntress' };
    const playerSprite = assetImages[CLASS_KEYS[player.class_type] || 'warrior'];

    if (playerSprite) {
      ctx.save();

      // Rogue stealth: render an invisible hero translucently (fully see-through
      // for others, ghosted for yourself so you can still track your position).
      if (player.invisible > 0) {
        ctx.globalAlpha = player.id === myPlayerId ? 0.45 : 0.0;
      }

      const RUN_FRAMES    = [2, 3, 4, 5, 6, 7];
      const IDLE_FRAMES   = [0, 0, 0, 1, 0, 0, 1, 1];
      const ATTACK_FRAMES = [13, 14, 15, 0]; // ~15fps swing (frames 13,14,15,idle)
      const DIE_FRAMES    = [8, 9, 10, 11, 12, 11]; // SPD HeroSprite die animation
      const OPERATE_FRAMES = [16, 17, 16, 17]; // SPD HeroSprite operate (drink) @8fps

      const now = performance.now();
      const anim = (playerAnimRef && playerAnimRef.current[player.id]) || {};
      const isAttacking = !player.is_downed && anim.attackUntil && now < anim.attackUntil;
      const isOperating = !player.is_downed && !isAttacking && anim.operateUntil && now < anim.operateUntil;
      const isFlashing = anim.flashUntil && now < anim.flashUntil;

      const isMoving = !player.is_downed && !isAttacking && !isOperating && player.targetPos && (
        Math.abs(player.targetPos.x - player.renderPos.x) > 0.05 ||
        Math.abs(player.targetPos.y - player.renderPos.y) > 0.05
      );

      let frameIndex;
      if (player.is_downed) {
        // Play the death animation once @20fps, then hold the final corpse frame.
        const elapsed = now - (player.deathStart || now);
        const fi = Math.min(Math.floor(elapsed / 50), DIE_FRAMES.length - 1);
        frameIndex = DIE_FRAMES[fi];
      } else if (isAttacking) {
        const elapsed = now - (anim.attackUntil - PLAYER_ATTACK_DURATION);
        const fi = Math.min(Math.floor(elapsed / (PLAYER_ATTACK_DURATION / ATTACK_FRAMES.length)), ATTACK_FRAMES.length - 1);
        frameIndex = ATTACK_FRAMES[fi];
      } else if (isOperating) {
        const elapsed = now - (anim.operateUntil - PLAYER_OPERATE_DURATION);
        const fi = Math.min(Math.floor(elapsed / (PLAYER_OPERATE_DURATION / OPERATE_FRAMES.length)), OPERATE_FRAMES.length - 1);
        frameIndex = OPERATE_FRAMES[fi];
      } else if (isMoving) {
        frameIndex = RUN_FRAMES[Math.floor(now / 50) % RUN_FRAMES.length];
      } else {
        frameIndex = IDLE_FRAMES[Math.floor(now / 1000) % IDLE_FRAMES.length];
      }

      const sx = frameIndex * 12;
      const sWidth = 12;
      const dWidth = sWidth * TILE_SCALE;
      const xOffset = (TILE_SIZE - dWidth) / 2;
      const FRAME_H = TILE_SIZE / TILE_SCALE;

      if (player.flipX) {
        ctx.translate(x + TILE_SIZE - xOffset, y);
        ctx.scale(-1, 1);
        ctx.drawImage(playerSprite, sx, 0, sWidth, FRAME_H, 0, 0, dWidth, TILE_SIZE);
        if (isFlashing) drawWhiteSilhouette(ctx, playerSprite, sx, 0, sWidth, FRAME_H, 0, 0, dWidth, TILE_SIZE);
      } else {
        ctx.drawImage(playerSprite, sx, 0, sWidth, FRAME_H, x + xOffset, y, dWidth, TILE_SIZE);
        if (isFlashing) drawWhiteSilhouette(ctx, playerSprite, sx, 0, sWidth, FRAME_H, x + xOffset, y, dWidth, TILE_SIZE);
      }
      ctx.restore();
    }

    if (player.id !== myPlayerId && !player.is_downed) {
      const hpBarWidth = TILE_SIZE - 4;
      const playerHpPercent = player.hp / player.max_hp;
      ctx.fillStyle = '#111';
      ctx.fillRect(x + 2, y - 12, hpBarWidth, 4);
      ctx.fillStyle = player.heal_left > 0 ? '#f1c40f' : '#2ecc71';
      ctx.fillRect(x + 2, y - 12, hpBarWidth * playerHpPercent, 4);
    }

    if (player.id !== myPlayerId) {
      ctx.fillStyle = 'white';
      ctx.font = '10px Arial';
      ctx.textAlign = 'center';
      ctx.fillText(player.name, x + TILE_SIZE / 2, y - 15);
    }
  });
}
