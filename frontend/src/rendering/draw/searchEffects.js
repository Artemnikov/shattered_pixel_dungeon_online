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
// Search "CheckedCell" rings, ported from effects/CheckedCell.java in the original
// Shattered Pixel Dungeon: a cyan square drawn on each searched cell that fades and
// shrinks over ~0.8s. Each cell's ring is delayed by its distance from the hero so the
// sweep emanates outward cell-by-cell.
//
// Coordinates are in world pixels (tile * TILE_SIZE), advanced and drawn inside the
// render loop's camera transform — same convention as draw/particles.js.

import { TILE_SIZE } from '../../constants';

const COLOR = '#55AAFF'; // 0xFF55AAFF in the original
const START_ALPHA = 0.8;

let lastNow = null;

// cells: [[cx, cy], ...] tile coords. (sourceX, sourceY) is the hero tile the sweep
// emanates from. Mirrors `new CheckedCell(curr, pos)` per cell.
export function spawnCheckedCells(ref, cells, sourceX, sourceY) {
  if (!cells) return;
  cells.forEach(([cx, cy]) => {
    const dist = Math.hypot(cx - sourceX, cy - sourceY);
    // delay steadily accelerates as distance increases (CheckedCell.java:49-52)
    let delay = dist - 1;
    delay = delay > 0 ? Math.pow(delay, 0.67) / 10 : 0;
    ref.current.push({
      x: (cx + 0.5) * TILE_SIZE,
      y: (cy + 0.5) * TILE_SIZE,
      delay,
      alpha: START_ALPHA,
    });
  });
}

export function advanceAndDrawCheckedCells(ctx, { ref }) {
  const now = performance.now();
  if (lastNow == null) lastNow = now;
  const dt = Math.min((now - lastNow) / 1000, 0.05); // clamp to avoid jumps
  lastNow = now;

  const effects = ref.current;
  for (let i = effects.length - 1; i >= 0; i--) {
    const c = effects[i];
    // Hold (invisible) until the per-cell delay elapses, then fade+shrink, then die.
    if ((c.delay -= dt) > 0) {
      continue;
    }
    if ((c.alpha -= dt) <= 0) {
      effects.splice(i, 1);
      continue;
    }
    const side = TILE_SIZE * c.alpha; // shrinks as it fades (CheckedCell.java:63)
    ctx.save();
    ctx.globalAlpha = c.alpha;
    ctx.fillStyle = COLOR;
    ctx.fillRect(c.x - side / 2, c.y - side / 2, side, side);
    ctx.restore();
  }
}
