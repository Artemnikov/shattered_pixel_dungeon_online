// Floating combat text, mirroring FloatingText from the original Shattered Pixel
// Dungeon: a short-lived label that rises ~1 tile and fades out in its second half.
// Currently used for healing numbers, but kept generic (text + color) for reuse.
//
// Coordinates are in world pixels (tile * TILE_SIZE). Entries are advanced and drawn
// inside the render loop's camera transform.

import { TILE_SIZE } from '../../constants';

const LIFESPAN = 1.0;          // s, matches FloatingText.LIFESPAN
const RISE = TILE_SIZE;        // px risen over the full lifespan (FloatingText.DISTANCE)

let lastNow = null;

export function spawnFloatingText(floatingTextRef, cx, cy, text, color = '#ffffff') {
  floatingTextRef.current.push({
    x: cx,
    y: cy,
    text,
    color,
    life: LIFESPAN,
    maxLife: LIFESPAN,
  });
}

export function advanceAndDrawFloatingText(ctx, { floatingTextRef }) {
  const now = performance.now();
  if (lastNow == null) lastNow = now;
  const dt = Math.min((now - lastNow) / 1000, 0.05); // clamp to avoid jumps
  lastNow = now;

  const items = floatingTextRef.current;
  for (let i = items.length - 1; i >= 0; i--) {
    const t = items[i];
    t.life -= dt;
    if (t.life <= 0) {
      items.splice(i, 1);
      continue;
    }
    t.y -= (RISE / t.maxLife) * dt;

    // Fade out over the last half of the lifespan (mirrors FloatingText).
    const alpha = t.life > t.maxLife / 2 ? 1 : Math.max(0, t.life / (t.maxLife / 2));

    ctx.save();
    ctx.globalAlpha = alpha;
    ctx.font = '9px Arial';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    // Outline for legibility over any background.
    ctx.lineWidth = 2;
    ctx.strokeStyle = 'rgba(0, 0, 0, 0.6)';
    ctx.strokeText(t.text, Math.round(t.x), Math.round(t.y));
    ctx.fillStyle = t.color;
    ctx.fillText(t.text, Math.round(t.x), Math.round(t.y));
    ctx.restore();
  }
}
