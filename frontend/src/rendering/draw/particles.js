// Blood-burst particle system, mirroring CharSprite.bloodBurstA / Splash from
// the original Shattered Pixel Dungeon: a short spray of particles thrown away
// from the attacker, with gravity and a fade-out.
//
// Coordinates are in world pixels (tile * TILE_SIZE). Particles are advanced and
// drawn inside the render loop's camera transform.

const GRAVITY = 320;        // px/s^2
const SPREAD = Math.PI / 2; // total cone width (matches bloodBurstA)
const MIN_SPEED = 24;       // px/s
const MAX_SPEED = 96;       // px/s
const MIN_LIFE = 0.35;      // s
const MAX_LIFE = 0.6;       // s

let lastNow = null;

// count is precomputed by the caller (damage-scaled). awayAngle points away
// from the attacker, in radians.
export function spawnBlood(particlesRef, cx, cy, awayAngle, count, color = '#bb0000') {
  for (let i = 0; i < count; i++) {
    const angle = awayAngle + (Math.random() - 0.5) * SPREAD;
    const speed = MIN_SPEED + Math.random() * (MAX_SPEED - MIN_SPEED);
    const life = MIN_LIFE + Math.random() * (MAX_LIFE - MIN_LIFE);
    particlesRef.current.push({
      x: cx,
      y: cy,
      vx: Math.cos(angle) * speed,
      vy: Math.sin(angle) * speed,
      life,
      maxLife: life,
      size: 1 + Math.floor(Math.random() * 2), // 1-2 px squares
      color,
      gravity: true,
    });
  }
}

// Healing sparkles, mirroring Speck.HEALING: green specks drifting straight up
// (~20 px/s) over ~1s, no gravity. Spawned spread across the sprite's width.
export function spawnHeal(particlesRef, cx, cy, count, color = '#2ecc71') {
  for (let i = 0; i < count; i++) {
    const life = 0.8 + Math.random() * 0.4;
    particlesRef.current.push({
      x: cx + (Math.random() - 0.5) * 14,
      y: cy + (Math.random() - 0.5) * 6,
      vx: (Math.random() - 0.5) * 6,
      vy: -20,
      life,
      maxLife: life,
      size: 1 + Math.floor(Math.random() * 2),
      color,
      gravity: false,
    });
  }
}

export function advanceAndDrawParticles(ctx, { particlesRef }) {
  const now = performance.now();
  if (lastNow == null) lastNow = now;
  const dt = Math.min((now - lastNow) / 1000, 0.05); // clamp to avoid jumps
  lastNow = now;

  const particles = particlesRef.current;
  for (let i = particles.length - 1; i >= 0; i--) {
    const p = particles[i];
    p.life -= dt;
    if (p.life <= 0) {
      particles.splice(i, 1);
      continue;
    }
    if (p.gravity !== false) p.vy += GRAVITY * dt;
    p.x += p.vx * dt;
    p.y += p.vy * dt;

    ctx.save();
    ctx.globalAlpha = Math.max(0, Math.min(1, p.life / p.maxLife));
    ctx.fillStyle = p.color;
    ctx.fillRect(Math.round(p.x), Math.round(p.y), p.size, p.size);
    ctx.restore();
  }
}
