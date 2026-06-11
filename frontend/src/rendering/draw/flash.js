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
// White hit-flash overlay.
//
// Canvas2D can't additively tint a drawImage call, so we build a solid-white
// silhouette of the current sprite frame on a cached offscreen canvas and draw
// that over the sprite. This mirrors the 50ms full-sprite white blink from the
// original Shattered Pixel Dungeon (CharSprite.flash()).
//
// The caller is responsible for any flip/transform on `ctx` before calling this
// (we draw into the same transformed space, so flips are respected).

let offCanvas = null;
let offCtx = null;

function ensureOffscreen(w, h) {
  if (!offCanvas) {
    offCanvas = document.createElement('canvas');
    offCtx = offCanvas.getContext('2d');
  }
  if (offCanvas.width < w || offCanvas.height < h) {
    offCanvas.width = Math.max(offCanvas.width, w);
    offCanvas.height = Math.max(offCanvas.height, h);
  }
  return offCtx;
}

export function drawWhiteSilhouette(ctx, sprite, sx, sy, fw, fh, dx, dy, dw, dh) {
  if (!sprite) return;
  const octx = ensureOffscreen(fw, fh);
  octx.save();
  octx.clearRect(0, 0, fw, fh);
  octx.globalCompositeOperation = 'source-over';
  octx.imageSmoothingEnabled = false;
  octx.drawImage(sprite, sx, sy, fw, fh, 0, 0, fw, fh);
  // Keep only the sprite's opaque pixels, recolored solid white.
  octx.globalCompositeOperation = 'source-in';
  octx.fillStyle = '#ffffff';
  octx.fillRect(0, 0, fw, fh);
  octx.restore();

  ctx.drawImage(offCanvas, 0, 0, fw, fh, dx, dy, dw, dh);
}
