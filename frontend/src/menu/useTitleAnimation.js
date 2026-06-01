// Drives the title-screen <canvas>: the scrolling parallax background
// (TitleParallax), the two animated Fireball torches, and the banner with its
// pulsing additive glow. Mirrors the layout math of TitleScene.java.

import { useEffect } from 'react';
import TitleParallax, { TITLE_ASSET_URLS } from './titleBackground';
import { getDisplaySettings, subscribeDisplay } from './menuSettings';

import bannersUrl from '../assets/pixel-dungeon/interfaces/banners.png';
import fireballTallUrl from '../assets/pixel-dungeon/effects/fireball-tall.png';
import fireballShortUrl from '../assets/pixel-dungeon/effects/fireball-short.png';

// banners.png (512x256) sub-rects, from BannerSprites.java
const BANNER = {
  land:      { sx: 0,   sy: 100, w: 240, h: 57 },
  landGlow:  { sx: 240, sy: 100, w: 240, h: 57 },
  port:      { sx: 0,   sy: 0,   w: 139, h: 100 },
  portGlow:  { sx: 139, sy: 0,   w: 139, h: 100 },
};
// fireball sheets: 24 frames @ 24fps
const FB_TALL = { url: fireballTallUrl, size: 61, cols: 4 };
const FB_SHORT = { url: fireballShortUrl, size: 47, cols: 5 };
const FB_FPS = 24;
const FB_COUNT = 24;

function loadImages(urls) {
  return Promise.all(urls.map(url => new Promise((resolve) => {
    const img = new Image();
    img.onload = () => resolve([url, img]);
    img.onerror = () => resolve([url, null]);
    img.src = url;
  }))).then(pairs => Object.fromEntries(pairs));
}

export default function useTitleAnimation(canvasRef) {
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    ctx.imageSmoothingEnabled = false;

    let raf = 0;
    let last = performance.now();
    let glowTime = 0;
    let fbTime = 0;
    let parallax = null;
    let images = null;
    let disposed = false;

    const allUrls = [...TITLE_ASSET_URLS, bannersUrl, fireballTallUrl, fireballShortUrl];

    const sizeCanvas = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      const w = canvas.clientWidth || window.innerWidth;
      const h = canvas.clientHeight || window.innerHeight;
      canvas.width = Math.round(w * dpr);
      canvas.height = Math.round(h * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.imageSmoothingEnabled = false;
      if (parallax) { parallax.reset(w, h); parallax.prime(); }
      return { w, h };
    };

    const drawFireball = (sheet, x, y, px, frame, flip) => {
      const img = images[sheet.url];
      if (!img) return;
      const f = ((frame % FB_COUNT) + FB_COUNT) % FB_COUNT;
      const sx = (f % sheet.cols) * sheet.size;
      const sy = Math.floor(f / sheet.cols) * sheet.size;
      const w = sheet.size * px, h = sheet.size * px;
      ctx.save();
      ctx.translate(x, y);
      if (flip) ctx.scale(-1, 1);
      ctx.drawImage(img, sx, sy, sheet.size, sheet.size, -w / 2, 0, w, h);
      ctx.restore();
    };

    const render = (now) => {
      if (disposed) return;
      const dt = Math.min((now - last) / 1000, 0.1);
      last = now;
      const motion = getDisplaySettings().bgMotion;

      const w = canvas.clientWidth || window.innerWidth;
      const h = canvas.clientHeight || window.innerHeight;
      const landscape = w > h;

      ctx.clearRect(0, 0, w, h);
      // dark base
      ctx.fillStyle = '#16151a';
      ctx.fillRect(0, 0, w, h);

      if (parallax) {
        if (motion) parallax.update(dt);
        parallax.draw(ctx);
      }

      if (images) {
        // pixel-art scale for the foreground title group (banner + torches)
        const bFrame = landscape ? BANNER.land : BANNER.port;
        const gFrame = landscape ? BANNER.landGlow : BANNER.portGlow;
        const targetW = landscape ? w * 0.55 : w * 0.7;
        const px = Math.max(2, Math.round(targetW / bFrame.w));

        const bw = bFrame.w * px, bh = bFrame.h * px;
        const topRegion = Math.max(bh - 6 * px, h * 0.45);
        const tx = Math.round((w - bw) / 2);
        const ty = Math.round(2 * px + (topRegion - bh) / 2);

        const banners = images[bannersUrl];

        // torches behind banner
        if (motion) fbTime += dt;
        const baseFrame = Math.floor(fbTime * FB_FPS);
        const fbSheet = landscape ? FB_TALL : FB_SHORT;
        const fbPx = px;
        const fbDraw = fbSheet.size * fbPx;
        let lx, rx, lyTorch;
        if (landscape) {
          lx = tx + 30 * px; rx = tx + bw - 30 * px; lyTorch = ty + 35 * px;
        } else {
          lx = tx + 16 * px; rx = tx + bw - 16 * px; lyTorch = ty + 70 * px;
        }
        // placeTorch: y is torch base; sprite top = base - height
        const torchTop = lyTorch - fbDraw;
        drawFireball(fbSheet, lx, torchTop, fbPx, baseFrame, false);
        drawFireball(fbSheet, rx, torchTop, fbPx, baseFrame + 12, true);

        // banner
        if (banners) {
          ctx.drawImage(banners, bFrame.sx, bFrame.sy, bFrame.w, bFrame.h, tx, ty, bw, bh);
          // pulsing additive glow
          if (motion) { glowTime += dt; if (glowTime >= 1.5 * Math.PI) glowTime = 0; }
          const glowA = Math.max(0, Math.sin(glowTime));
          if (glowA > 0.001) {
            const gw = gFrame.w * px, gh = gFrame.h * px;
            const gx = tx + (bw - gw) / 2;
            ctx.save();
            ctx.globalCompositeOperation = 'lighter';
            ctx.globalAlpha = glowA;
            ctx.drawImage(banners, gFrame.sx, gFrame.sy, gFrame.w, gFrame.h, gx, ty, gw, gh);
            ctx.restore();
          }

          // "online" brand label centered just below the banner
          ctx.save();
          ctx.textAlign = 'center';
          ctx.textBaseline = 'top';
          ctx.letterSpacing = `${px}px`;
          ctx.font = `bold ${Math.round(px * 7)}px monospace`;
          ctx.fillStyle = '#ffe070';
          ctx.shadowColor = '#ffe070';
          ctx.shadowBlur = px * 2;
          ctx.fillText('online', tx + bw / 2, ty + bh + 4 * px);
          ctx.restore();
        }
      }

      raf = requestAnimationFrame(render);
    };

    loadImages(allUrls).then((imgs) => {
      if (disposed) return;
      images = imgs;
      parallax = new TitleParallax(imgs);
      sizeCanvas();
      last = performance.now();
      raf = requestAnimationFrame(render);
    });

    const onResize = () => sizeCanvas();
    window.addEventListener('resize', onResize);
    const unsub = subscribeDisplay(() => {}); // keep store warm / re-render driven elsewhere

    return () => {
      disposed = true;
      cancelAnimationFrame(raf);
      window.removeEventListener('resize', onResize);
      unsub();
    };
  }, [canvasRef]);
}
