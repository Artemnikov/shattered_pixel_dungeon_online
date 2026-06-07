import { useEffect, useRef } from 'react';
import AudioManager from '../audio/AudioManager';

import statusPaneImg from '../assets/pixel-dungeon/interfaces/status_pane.png';
import buffsImg from '../assets/pixel-dungeon/interfaces/buffs.png';
import warriorSheet from '../assets/pixel-dungeon/sprites/warrior.png';
import mageSheet from '../assets/pixel-dungeon/sprites/mage.png';
import rogueSheet from '../assets/pixel-dungeon/sprites/rogue.png';
import huntressSheet from '../assets/pixel-dungeon/sprites/huntress.png';

// Pixel-faithful reproduction of SPD's StatusPane (small / mobile layout).
// Native coordinates are taken straight from StatusPane.java and scaled up by
// SCALE. All sprites are drawn with smoothing off so they stay crisp pixels.
const SCALE = 3;
const PANE_W = 90;   // a touch wider than the 82px bg so the buff row fits
const PANE_H = 38;

// status_pane.png source regions (small UI), from StatusPane.java
const BG = { x: 0, y: 0, w: 82, h: 38 };
const HP_FILL = { x: 0, y: 40, w: 50, h: 4 };
const EXP_FILL = { x: 0, y: 48, w: 17, h: 4 };

// Avatar = 12x15 crop of the class sprite sheet at frame index 1 (x=12), row =
// armour tier (0 when unarmoured). Mirrors HeroSprite.avatar().
const FRAME_W = 12;
const FRAME_H = 15;

// The HUD portrait uses the distinctive class bust (SPD HeroSelectScene art,
// also used in CharacterSelection) so each class is unmistakable, rather than
// the near-identical bare-chested tier-0 walking frame.
const BUST = { x: 0, y: 90 };

// buffs.png is sliced into 7x7 cells; 128/7 = 18 columns. icon idx -> (col,row).
const BUFF_SIZE = 7;
const BUFF_COLS = 18;

// 1.5 blinks/sec, like StatusPane.FLASH_RATE.
const FLASH_RATE = Math.PI * 1.5;
const WARNING_COLORS = ['#660000', '#cc0000', '#660000'];

const CLASS_SHEETS = {
  warrior: warriorSheet,
  mage: mageSheet,
  rogue: rogueSheet,
  huntress: huntressSheet,
};

function lerpColor(t, colors) {
  // t in [0,1] across the colors array (matches ColorMath.interpolate).
  if (!Number.isFinite(t)) t = 0;
  t = Math.max(0, Math.min(1, t));
  const seg = Math.min(Math.floor(t * (colors.length - 1)), colors.length - 2);
  const local = t * (colors.length - 1) - seg;
  const a = parseInt(colors[seg].slice(1), 16);
  const b = parseInt(colors[seg + 1].slice(1), 16);
  const ar = (a >> 16) & 0xff, ag = (a >> 8) & 0xff, ab = a & 0xff;
  const br = (b >> 16) & 0xff, bg = (b >> 8) & 0xff, bb = b & 0xff;
  const r = Math.round(ar + (br - ar) * local);
  const g = Math.round(ag + (bg - ag) * local);
  const bl = Math.round(ab + (bb - ab) * local);
  return `rgb(${r},${g},${bl})`;
}

export default function StatusPane({ myStats, depth, onSearch }) {
  const canvasRef = useRef(null);
  const imagesRef = useRef({});
  const imgsLoadedRef = useRef(false);
  const statsRef = useRef(myStats);
  const starsRef = useRef([]);
  const prevLevelRef = useRef(myStats.level || 1);
  const warningRef = useRef(0);

  useEffect(() => { statsRef.current = myStats; }, [myStats]);

  useEffect(() => {
    const sources = { status: statusPaneImg, buffs: buffsImg, ...CLASS_SHEETS };
    const entries = Object.entries(sources);
    let loaded = 0;
    let errored = 0;
    const total = entries.length;
    const checkDone = () => {
      if (loaded + errored === total) imgsLoadedRef.current = true;
    };
    entries.forEach(([key, src]) => {
      const img = new Image();
      img.onload = () => { loaded++; checkDone(); };
      img.onerror = () => {
        errored++;
        console.error(`[StatusPane] failed to load image: ${key} (${src})`);
        checkDone();
      };
      img.src = src;
      if (img.complete && img.naturalWidth > 0) {
        img.onload = null;
        loaded++;
        checkDone();
      } else if (img.complete && img.naturalWidth === 0) {
        img.onerror = null;
        errored++;
        console.error(`[StatusPane] broken image: ${key} (${src})`);
        checkDone();
      }
      imagesRef.current[key] = img;
    });
  }, []);

  useEffect(() => {
    let raf;
    let last = performance.now();
    const avatarCanvas = document.createElement('canvas');
    avatarCanvas.width = FRAME_W;
    avatarCanvas.height = FRAME_H;

    const draw = (now) => {
      try {
        const dt = (now - last) / 1000;
        last = now;
        const canvas = canvasRef.current;
        const ctx = canvas?.getContext('2d');
        const imgs = imagesRef.current;
        if (!ctx) { raf = requestAnimationFrame(draw); return; }

        const s = statsRef.current || {};
        const hp = Math.max(0, Math.ceil(s.hp ?? 0));
        const maxHp = Math.max(1, s.maxHp ?? 1);
        const hpPct = Math.min(1, hp / maxHp);
        const exp = s.exp ?? 0;
        const maxExp = Math.max(1, s.maxExp ?? 10);
        const expPct = Math.min(1, exp / maxExp);
        const level = s.level ?? 1;
        const effects = s.effects ?? [];
        const sheet = imgs[s.classType] || imgs.warrior;

        if (level > prevLevelRef.current) {
          const cx = (9 + FRAME_W / 2) * SCALE;
          const cy = (8 + FRAME_H / 2) * SCALE;
          for (let i = 0; i < 12; i++) {
            const ang = (Math.PI * 2 * i) / 12 + Math.random() * 0.4;
            const spd = (20 + Math.random() * 30) * SCALE;
            starsRef.current.push({ x: cx, y: cy, vx: Math.cos(ang) * spd, vy: Math.sin(ang) * spd, life: 1 });
          }
          AudioManager.play('LEVELUP');
        }
        prevLevelRef.current = level;

        ctx.imageSmoothingEnabled = false;
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        // Fallback background: always visible even before pixel-art images load.
        ctx.fillStyle = '#161616';
        ctx.fillRect(0, 0, BG.w * SCALE, BG.h * SCALE);

        // Draw a subtle placeholder grid so the HUD area is never empty.
        ctx.strokeStyle = '#2a2a2a';
        ctx.lineWidth = 1;
        ctx.strokeRect(0, 0, BG.w * SCALE, BG.h * SCALE);

        const statusImg = imgs.status;
        if (statusImg?.complete && statusImg?.naturalWidth > 0) {
          ctx.drawImage(statusImg, BG.x, BG.y, BG.w, BG.h, 0, 0, BG.w * SCALE, BG.h * SCALE);
        }

        // --- Avatar ---
        if (sheet?.complete && sheet?.naturalWidth > 0) {
          const ac = avatarCanvas.getContext('2d');
          ac.imageSmoothingEnabled = false;
          ac.clearRect(0, 0, FRAME_W, FRAME_H);
          ac.drawImage(sheet, BUST.x, BUST.y, FRAME_W, FRAME_H, 0, 0, FRAME_W, FRAME_H);

          if (s.isDowned) {
            ac.globalCompositeOperation = 'source-atop';
            ac.fillStyle = 'rgba(0,0,0,0.5)';
            ac.fillRect(0, 0, FRAME_W, FRAME_H);
            ac.globalCompositeOperation = 'source-over';
          } else if (hpPct < 0.334) {
            warningRef.current = (warningRef.current + dt * 5 * (0.4 - hpPct)) % 1;
            ac.globalCompositeOperation = 'source-atop';
            ac.fillStyle = lerpColor(warningRef.current, WARNING_COLORS);
            ac.globalAlpha = 0.5;
            ac.fillRect(0, 0, FRAME_W, FRAME_H);
            ac.globalAlpha = 1;
            ac.globalCompositeOperation = 'source-over';
          }
          ctx.drawImage(avatarCanvas, 9 * SCALE, 8 * SCALE, FRAME_W * SCALE, FRAME_H * SCALE);

          // Armor-tier marker: small badge in the bottom-right of the portrait so
          // worn gear is still legible now that the bust no longer reflects armor.
          const tier = s.armorTier ?? 0;
          if (tier > 0) {
            const bx = (9 + FRAME_W) * SCALE;
            const by = (8 + FRAME_H) * SCALE;
            const r = 3.5 * SCALE;
            ctx.fillStyle = 'rgba(0,0,0,0.7)';
            ctx.beginPath();
            ctx.arc(bx - r, by - r, r, 0, Math.PI * 2);
            ctx.fill();
            ctx.fillStyle = '#ffe9a8';
            ctx.font = `${4 * SCALE}px monospace`;
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillText(`${tier}`, bx - r, by - r + 0.5 * SCALE);
          }
        }

        // --- HP bar + text ---
        if (statusImg?.complete && statusImg?.naturalWidth > 0 && hpPct > 0) {
          ctx.drawImage(statusImg, HP_FILL.x, HP_FILL.y, HP_FILL.w, HP_FILL.h,
            30 * SCALE, 2 * SCALE, HP_FILL.w * hpPct * SCALE, HP_FILL.h * SCALE);
        }
        ctx.font = `${4 * SCALE}px monospace`;
        ctx.textBaseline = 'middle';
        ctx.textAlign = 'center';
        ctx.fillStyle = 'rgba(255,255,255,0.85)';
        ctx.fillText(`${hp}/${maxHp}`, (30 + HP_FILL.w / 2) * SCALE, 4.5 * SCALE);

        // --- EXP bar + level ---
        if (statusImg?.complete && statusImg?.naturalWidth > 0 && expPct > 0) {
          ctx.drawImage(statusImg, EXP_FILL.x, EXP_FILL.y, EXP_FILL.w, EXP_FILL.h,
            2 * SCALE, 30 * SCALE, EXP_FILL.w * expPct * SCALE, EXP_FILL.h * SCALE);
        }
        ctx.fillStyle = '#ffffaa';
        ctx.fillText(`${level}`, 25.5 * SCALE, 31.5 * SCALE);

        // --- Buff indicators ---
        const buffsSheet = imgs.buffs;
        if (buffsSheet?.complete && buffsSheet?.naturalWidth > 0) {
          effects.forEach((eff, i) => {
            const idx = eff.icon ?? 0;
            const col = idx % BUFF_COLS;
            const row = Math.floor(idx / BUFF_COLS);
            ctx.globalAlpha = 0.85;
            ctx.drawImage(buffsSheet,
              col * BUFF_SIZE, row * BUFF_SIZE, BUFF_SIZE, BUFF_SIZE,
              (31 + i * (BUFF_SIZE + 1)) * SCALE, 9 * SCALE, BUFF_SIZE * SCALE, BUFF_SIZE * SCALE);
            ctx.globalAlpha = 1;
          });
        }

        // --- Level-up star particles ---
        const stars = starsRef.current;
        for (let i = stars.length - 1; i >= 0; i--) {
          const st = stars[i];
          st.x += st.vx * dt;
          st.y += st.vy * dt;
          st.vy += 40 * SCALE * dt;
          st.life -= dt * 1.4;
          if (st.life <= 0) { stars.splice(i, 1); continue; }
          ctx.globalAlpha = Math.max(0, st.life);
          ctx.fillStyle = '#ffff88';
          ctx.fillRect(st.x, st.y, 2 * SCALE, 2 * SCALE);
          ctx.globalAlpha = 1;
        }
      } catch (err) {
        console.error('[StatusPane] render error:', err);
      }
      raf = requestAnimationFrame(draw);
    };

    raf = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(raf);
  }, []);

  return (
    <div className="top-left-hud">
      <canvas
        ref={canvasRef}
        width={PANE_W * SCALE}
        height={PANE_H * SCALE}
        className="status-pane-canvas"
      />
      <div className="status-pane-footer">
        <span className="status-floor-label">floor: {depth}</span>
        <button
          type="button"
          className="search-btn"
          onClick={() => { AudioManager.play('CLICK'); onSearch(); }}
        >
          Search (E)
        </button>
      </div>
    </div>
  );
}
