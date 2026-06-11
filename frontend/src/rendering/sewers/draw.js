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
import {
  ATLAS_COLUMNS,
  BACKEND_TILE,
  DEST_TILE_SIZE,
  QUADRANT,
  SOURCE_TILE_SIZE,
  WATER_SCROLL_PX_PER_SEC,
} from './constants.js';
import { getSewerTerrainInstructions } from './terrainMapper.js';
import { getSewerCap, getSewerDoorCap, getSewerWallInstructions } from './wallMapper.js';

const HALF_SOURCE = SOURCE_TILE_SIZE / 2;
const HALF_DEST = DEST_TILE_SIZE / 2;

const QUADRANT_RECTS = {
  [QUADRANT.TL]: {
    sxOffset: 0,
    syOffset: 0,
    sw: HALF_SOURCE,
    sh: HALF_SOURCE,
    dxOffset: 0,
    dyOffset: 0,
    dw: HALF_DEST,
    dh: HALF_DEST,
  },
  [QUADRANT.TR]: {
    sxOffset: HALF_SOURCE,
    syOffset: 0,
    sw: HALF_SOURCE,
    sh: HALF_SOURCE,
    dxOffset: HALF_DEST,
    dyOffset: 0,
    dw: HALF_DEST,
    dh: HALF_DEST,
  },
  [QUADRANT.BL]: {
    sxOffset: 0,
    syOffset: HALF_SOURCE,
    sw: HALF_SOURCE,
    sh: HALF_SOURCE,
    dxOffset: 0,
    dyOffset: HALF_DEST,
    dw: HALF_DEST,
    dh: HALF_DEST,
  },
  [QUADRANT.BR]: {
    sxOffset: HALF_SOURCE,
    syOffset: HALF_SOURCE,
    sw: HALF_SOURCE,
    sh: HALF_SOURCE,
    dxOffset: HALF_DEST,
    dyOffset: HALF_DEST,
    dw: HALF_DEST,
    dh: HALF_DEST,
  },
};

const getSourceXY = (srcIndex) => ({
  sx: (srcIndex % ATLAS_COLUMNS) * SOURCE_TILE_SIZE,
  sy: Math.floor(srcIndex / ATLAS_COLUMNS) * SOURCE_TILE_SIZE,
});

const applyCrop = (crop, sx, sy, sw, sh, dx, dy, dw, dh) => {
  if (!crop) return [sx, sy, sw, sh, dx, dy, dw, dh];
  let [nsx, nsy, nsw, nsh, ndx, ndy, ndw, ndh] = [sx, sy, sw, sh, dx, dy, dw, dh];
  if (crop.top    != null) { nsh = sh * crop.top; ndh = dh * crop.top; }
  if (crop.bottom != null) { nsy += sh * (1 - crop.bottom); nsh = sh * crop.bottom; ndy += dh * (1 - crop.bottom); ndh = dh * crop.bottom; }
  if (crop.left   != null) { nsw = sw * crop.left; ndw = dw * crop.left; }
  if (crop.right  != null) { nsx += sw * (1 - crop.right); nsw = sw * crop.right; ndx += dw * (1 - crop.right); ndw = dw * crop.right; }
  return [nsx, nsy, nsw, nsh, ndx, ndy, ndw, ndh];
};

export const drawInstructions = (ctx, atlasImage, instructions, x, y) => {
  if (!atlasImage || !instructions || instructions.length === 0) return;

  const dx = x * DEST_TILE_SIZE;
  const dy = y * DEST_TILE_SIZE;

  for (const instruction of instructions) {
    const { srcIndex, quadrant = QUADRANT.FULL, alpha, rotate, srcOffset, crop, flipX } = instruction;
    if (typeof srcIndex !== 'number') continue;

    const raw = getSourceXY(srcIndex);
    const sx = raw.sx + (srcOffset?.x ?? 0);
    const sy = raw.sy + (srcOffset?.y ?? 0);
    const needsRotation = rotate != null && rotate !== 0;
    const needsTransform = needsRotation || flipX;
    const prevAlpha = ctx.globalAlpha;

    if (typeof alpha === 'number') ctx.globalAlpha = alpha;

    if (needsTransform) ctx.save();

    if (quadrant === QUADRANT.FULL) {
      if (needsTransform) {
        ctx.translate(dx + HALF_DEST, dy + HALF_DEST);
        if (flipX) ctx.scale(-1, 1);
        if (needsRotation) ctx.rotate(rotate * Math.PI / 180);
        ctx.drawImage(atlasImage, sx, sy, SOURCE_TILE_SIZE, SOURCE_TILE_SIZE, -HALF_DEST, -HALF_DEST, DEST_TILE_SIZE, DEST_TILE_SIZE);
      } else {
        const [csx, csy, csw, csh, cdx, cdy, cdw, cdh] =
          applyCrop(crop, sx, sy, SOURCE_TILE_SIZE, SOURCE_TILE_SIZE, dx, dy, DEST_TILE_SIZE, DEST_TILE_SIZE);
        ctx.drawImage(atlasImage, csx, csy, csw, csh, cdx, cdy, cdw, cdh);
      }
    } else {
      const rect = QUADRANT_RECTS[quadrant];
      if (rect) {
        if (needsTransform) {
          const cx = dx + rect.dxOffset + rect.dw / 2;
          const cy = dy + rect.dyOffset + rect.dh / 2;
          ctx.translate(cx, cy);
          if (flipX) ctx.scale(-1, 1);
          if (needsRotation) ctx.rotate(rotate * Math.PI / 180);
          ctx.drawImage(atlasImage, sx + rect.sxOffset, sy + rect.syOffset, rect.sw, rect.sh, -rect.dw / 2, -rect.dh / 2, rect.dw, rect.dh);
        } else {
          ctx.drawImage(atlasImage, sx + rect.sxOffset, sy + rect.syOffset, rect.sw, rect.sh, dx + rect.dxOffset, dy + rect.dyOffset, rect.dw, rect.dh);
        }
      }
    }

    if (needsTransform) ctx.restore();
    if (typeof alpha === 'number') ctx.globalAlpha = prevAlpha;
  }
};

export const getWaterTextureForDepth = (depth, waterFrames) => {
  if (!waterFrames || waterFrames.length === 0) return null;
  const region = Math.min(
    waterFrames.length - 1,
    Math.max(0, Math.floor(((depth ?? 1) - 1) / 5))
  );
  return waterFrames[region] ?? waterFrames[0];
};

export const buildWaterClipPath = (grid) => {
  if (!grid || grid.length === 0) return null;
  const path = new Path2D();
  let hasAny = false;
  for (let y = 0; y < grid.length; y++) {
    const row = grid[y];
    if (!row) continue;
    for (let x = 0; x < row.length; x++) {
      if (row[x] !== BACKEND_TILE.FLOOR_WATER.id) continue;
      path.rect(x * DEST_TILE_SIZE, y * DEST_TILE_SIZE, DEST_TILE_SIZE, DEST_TILE_SIZE);
      hasAny = true;
    }
  }
  return hasAny ? path : null;
};

export const drawWaterBackground = (ctx, waterTex, clipPath, bounds, nowMs) => {
  if (!waterTex || !clipPath || !bounds) return;
  const pattern = ctx.createPattern(waterTex, 'repeat');
  if (!pattern) return;

  const scale = DEST_TILE_SIZE / waterTex.width;
  const scrollPx = -(nowMs / 1000) * WATER_SCROLL_PX_PER_SEC;
  pattern.setTransform(
    new DOMMatrix().scaleSelf(scale).translateSelf(0, scrollPx / scale)
  );

  ctx.save();
  ctx.clip(clipPath);
  ctx.fillStyle = pattern;
  ctx.fillRect(bounds.x, bounds.y, bounds.w, bounds.h);
  ctx.restore();
};

// Two-pass render adapted from SPD's terrain + walls tilemaps:
//   base = RAISED_WALL face (wall above floor) or WALL_INTERNAL (wall surrounded
//          by walls), OR the normal terrain (floor/grass/water/door) for
//          non-wall cells, PLUS all door caps (DOOR_OVERHANG, DOOR_SIDEWAYS,
//          DOOR_SIDEWAYS_OVERHANG*). Drawn before entities — chars never
//          obscured by doors.
//   cap  = WALL_OVERHANG / WALL_INTERNAL drawn AFTER entities so chars are
//          partially obscured by the wall top, same z-order as SPD's
//          DungeonWallsTilemap which is added after the mobs group in
//          GameScene. Door caps deliberately live in the base pass.

export const drawSewerTileBase = (ctx, atlasImage, grid, x, y, tile, openDoors = new Set()) => {
  const isWall = tile === BACKEND_TILE.WALL.id
    || tile === BACKEND_TILE.WALL_DECO.id
    || tile === BACKEND_TILE.SECRET_DOOR.id;

  const instructions = isWall
    ? getSewerWallInstructions(grid, x, y)
    : getSewerTerrainInstructions(grid, x, y, tile, openDoors);

  const doorCap = getSewerDoorCap(grid, x, y, tile, openDoors);
  if (doorCap != null) {
    instructions.push({ srcIndex: doorCap, quadrant: QUADRANT.FULL });
  }

  const isWater = tile === BACKEND_TILE.FLOOR_WATER.id;
  if (instructions.length === 0 && !isWater) return false;

  drawInstructions(ctx, atlasImage, instructions, x, y);

  if (typeof window !== 'undefined' && window.__debugTileIds) {
    const dx = x * DEST_TILE_SIZE;
    const dy = y * DEST_TILE_SIZE;
    ctx.save();
    ctx.font = 'bold 8px monospace';
    ctx.fillStyle = 'black';
    ctx.fillText(String(tile), dx + 2, dy + 8);
    ctx.fillStyle = 'white';
    ctx.fillText(String(tile), dx + 1, dy + 7);
    ctx.restore();
  }

  return true;
};

export const drawSewerTileCap = (ctx, atlasImage, grid, x, y, tile) => {
  const cap = getSewerCap(grid, x, y, tile);
  if (cap == null) return false;
  drawInstructions(ctx, atlasImage, [{ srcIndex: cap, quadrant: QUADRANT.FULL }], x, y);
  return true;
};
