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
/*
 * SPD-style wall rendering.
 *
 * SPD uses TWO layers to draw walls with a 3D look:
 *
 *   1. Terrain layer — at the wall's own grid cell:
 *      - If the cell BELOW is non-wall: draw the RAISED_WALL front face
 *        (the vertical brick panel you see from in front of the wall).
 *      - If the cell below is also a wall: draw NOTHING here; the wall top
 *        will be drawn in the cell above via the overhang rule.
 *
 *   2. Walls layer — caps drawn on top of the terrain layer:
 *      - A wall cell whose below is also a wall gets a WALL_INTERNAL top
 *        (a top-down wall-surface tile stitched with 4-neighbour masks).
 *      - A FLOOR cell whose below is a wall gets a WALL_OVERHANG cap
 *        (top half: wall-top surface; bottom half: shadow bleeding into
 *        the floor — that's how SPD gets the visual depth).
 *      - Door cases are special-cased (sideways door on a vertical wall
 *        gets DOOR_SIDEWAYS_OVERHANG; a door on a horizontal wall gets
 *        DOOR_OVERHANG drawn in the floor cell above).
 *
 * The two passes are emitted by separate functions: drawSewerTileBase
 * (terrain + wall fronts/internals + ALL door caps, drawn before entities)
 * and drawSewerTileCap (wall overhangs only, drawn after entities so chars
 * are obscured by wall tops). Door overhangs deliberately live in the base
 * pass so doors never obscure characters — a deviation from SPD, which
 * draws door overhangs in the walls layer.
 */

import {
  BACKEND_TILE,
  QUADRANT,
  WALL_INDEX,
  hashCell,
  isDoorTile,
  isSidewaysDoor,
  isWallStitcheable,
  isWallTile,
} from './constants.js';

const getTile = (grid, x, y) => {
  if (y < 0 || y >= grid.length) return -1;
  if (x < 0 || x >= grid[y].length) return -1;
  return grid[y][x];
};

const pickAlt = (base, altBase, x, y) =>
  (hashCell(x, y) & 1) ? altBase : base;

/**
 * Returns the RAISED_WALL front-face sprite for a wall cell whose below is
 * non-wall. Returns null if this wall cell should NOT render a front face
 * (because below is also a wall — the cap will come from elsewhere).
 *
 * Mirrors SPD DungeonTileSheet.getRaisedWallTile.
 */
export const getRaisedWallFace = (grid, x, y, tile) => {
  const below = getTile(grid, x, y + 1);
  if (isWallStitcheable(below)) return null;

  // Wall directly above a door → special wall-with-doorway-inside sprite.
  if (isDoorTile(below)) return WALL_INDEX.RAISED_WALL_DOOR;

  const right = getTile(grid, x + 1, y);
  const left = getTile(grid, x - 1, y);

  const base = tile === BACKEND_TILE.WALL_DECO.id
    ? pickAlt(WALL_INDEX.RAISED_WALL_DECO, WALL_INDEX.RAISED_WALL_DECO_ALT, x, y)
    : pickAlt(WALL_INDEX.RAISED_WALL, WALL_INDEX.RAISED_WALL_ALT, x, y);

  let mask = 0;
  if (!isWallStitcheable(right)) mask += 1;  // open to the right
  if (!isWallStitcheable(left)) mask += 2;   // open to the left
  return base + mask;
};

/**
 * Returns the internal wall-top sprite for a wall cell whose below is
 * also a wall. 4-bit mask based on right / right-below / left-below / left
 * neighbours being non-wall.
 *
 * Mirrors SPD DungeonTileSheet.stitchInternalWallTile.
 */
export const getInternalWallTop = (grid, x, y, tile) => {
  const right = getTile(grid, x + 1, y);
  const rightBelow = getTile(grid, x + 1, y + 1);
  const leftBelow = getTile(grid, x - 1, y + 1);
  const left = getTile(grid, x - 1, y);

  const base = tile === BACKEND_TILE.WALL_DECO.id
    ? WALL_INDEX.WALL_INTERNAL_DECO
    : WALL_INDEX.WALL_INTERNAL;

  let mask = 0;
  if (!isWallStitcheable(right))      mask += 1;
  if (!isWallStitcheable(rightBelow)) mask += 2;
  if (!isWallStitcheable(leftBelow))  mask += 4;
  if (!isWallStitcheable(left))       mask += 8;
  return base + mask;
};

/**
 * Returns the wall-overhang cap for a non-wall cell whose below IS a wall.
 * The sprite art has the wall-top surface on the upper half and a shadow
 * fading into alpha on the lower half — together with the floor drawn
 * underneath this instruction, it gives the 3D depth effect.
 *
 * Mirrors SPD DungeonTileSheet.stitchWallOverhangTile for the plain-wall
 * path. 2-bit mask based on rightBelow / leftBelow being non-wall.
 */
export const getWallOverhang = (grid, x, y) => {
  const below = getTile(grid, x, y + 1);
  const rightBelow = getTile(grid, x + 1, y + 1);
  const leftBelow = getTile(grid, x - 1, y + 1);

  const base = below === BACKEND_TILE.WALL_DECO.id
    ? WALL_INDEX.WALL_OVERHANG_DECO
    : WALL_INDEX.WALL_OVERHANG;

  let mask = 0;
  if (!isWallStitcheable(rightBelow)) mask += 1;
  if (!isWallStitcheable(leftBelow))  mask += 2;
  return base + mask;
};

/**
 * Returns the door-overhang cap for a side-door cell whose below is a wall.
 * Variant is picked from THIS cell's tile (the door itself), not from below.
 * 2-bit stitch mask for rightBelow / leftBelow non-wall, just like
 * WALL_OVERHANG.
 *
 * Mirrors the DOOR_SIDEWAYS_OVERHANG* branches in
 * SPD DungeonTileSheet.stitchWallOverhangTile.
 */
export const getDoorSidewaysOverhang = (grid, x, y, tile, openDoors) => {
  const rightBelow = getTile(grid, x + 1, y + 1);
  const leftBelow = getTile(grid, x - 1, y + 1);

  let base;
  if (tile === BACKEND_TILE.LOCKED_DOOR.id) {
    base = WALL_INDEX.DOOR_SIDEWAYS_OVERHANG_LOCKED;
  } else if (tile === BACKEND_TILE.OPEN_DOOR.id || openDoors?.has(`${x},${y}`)) {
    base = WALL_INDEX.DOOR_SIDEWAYS_OVERHANG;
  } else {
    base = WALL_INDEX.DOOR_SIDEWAYS_OVERHANG_CLOSED;
  }

  let mask = 0;
  if (!isWallStitcheable(rightBelow)) mask += 1;
  if (!isWallStitcheable(leftBelow))  mask += 2;
  return base + mask;
};

/**
 * Wall-only cap (WALL_INTERNAL / WALL_OVERHANG). Drawn AFTER entities so
 * walls partially obscure characters, mirroring the upper portion of SPD's
 * DungeonWallsTilemap. Door-related caps live in `getSewerDoorCap` and
 * render in the base pass — characters are never obscured by doors.
 */
export const getSewerCap = (grid, x, y, tile) => {
  const below = getTile(grid, x, y + 1);

  if (!isWallStitcheable(below)) return null;
  if (isWallTile(tile)) return getInternalWallTop(grid, x, y, tile);
  if (isDoorTile(tile)) return null;
  return getWallOverhang(grid, x, y);
};

/**
 * Door-only cap. Drawn in the base pass (BEFORE entities), so a character
 * standing on a door cell or in the floor cell above a door always renders
 * on top of the door art. `openDoors` is a Set of "x,y" strings of doors
 * currently in the open state.
 */
export const getSewerDoorCap = (grid, x, y, tile, openDoors) => {
  const below = getTile(grid, x, y + 1);

  // Side-door cell with a wall below — door-shaped overhang that
  // blends the door body into the lower wall.
  if (isWallStitcheable(below) && isDoorTile(tile)) {
    return getDoorSidewaysOverhang(grid, x, y, tile, openDoors);
  }

  if (isDoorTile(below)) {
    if (isWallTile(tile) && isSidewaysDoor(grid, x, y + 1, getTile)) {
      // Wall above a sideways door — vertical-wall cap with doorway.
      return below === BACKEND_TILE.LOCKED_DOOR.id
        ? WALL_INDEX.DOOR_SIDEWAYS_LOCKED
        : WALL_INDEX.DOOR_SIDEWAYS;
    }
    // Floor above a top-facing door — the door-top cap sprite.
    const isOpen = below === BACKEND_TILE.OPEN_DOOR.id || openDoors?.has(`${x},${y + 1}`);
    return isOpen ? WALL_INDEX.DOOR_OVERHANG_OPEN : WALL_INDEX.DOOR_OVERHANG;
  }

  return null;
};

/**
 * Primary entry point. Returns the base-layer instructions for a wall
 * cell: either the raised front face, the internal wall top, or empty
 * (when the cell's content will entirely come from a cap drawn here).
 */
export const getSewerWallInstructions = (grid, x, y) => {
  const tile = getTile(grid, x, y);
  if (!isWallTile(tile)) return [];

  const below = getTile(grid, x, y + 1);

  // Wall with non-wall below → raised front face.
  if (!isWallStitcheable(below)) {
    const face = getRaisedWallFace(grid, x, y, tile);
    if (face == null) return [];
    return [{ srcIndex: face, quadrant: QUADRANT.FULL }];
  }

  // Wall with wall below → internal wall-top cap goes here.
  return [{ srcIndex: getInternalWallTop(grid, x, y, tile), quadrant: QUADRANT.FULL }];
};
