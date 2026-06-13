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
// Ports the wall-corner softening from SPD's FogOfWar.updateTexture
// (tiles/FogOfWar.java ~210-267): wall cells are split into left/right
// halves, each taking the darkest visibility state among the wall cell
// itself, its horizontal neighbor, and (if that neighbor is also a wall)
// the diagonal cell below the neighbor.

import { isWallStitcheable } from '../sewers/constants.js';

// Visibility states, darkest wins via Math.max.
export const VIS_VISIBLE = 0;
export const VIS_DISCOVERED = 1;
export const VIS_UNSEEN = 2;

export const cellVisState = (vision, x, y) => {
  const key = `${x},${y}`;
  if (vision.visible.has(key)) return VIS_VISIBLE;
  if (vision.discovered.has(key)) return VIS_DISCOVERED;
  return VIS_UNSEEN;
};

export const tileAt = (grid, x, y) => {
  if (y < 0 || y >= grid.length) return -1;
  const row = grid[y];
  if (x < 0 || x >= row.length) return -1;
  return row[x];
};

const sideDarkness = (grid, vision, x, y, selfState, neighborX) => {
  const neighborIsWall = isWallStitcheable(tileAt(grid, neighborX, y));
  if (neighborIsWall) {
    if (isWallStitcheable(tileAt(grid, neighborX, y + 1))) {
      return VIS_UNSEEN;
    }
    return Math.max(
      selfState,
      cellVisState(vision, neighborX, y + 1),
      cellVisState(vision, neighborX, y)
    );
  }
  return Math.max(selfState, cellVisState(vision, neighborX, y));
};

export const wallEdgeDarkness = (grid, vision, x, y) => {
  const below = tileAt(grid, x, y + 1);

  // Last row / off the bottom of the map: always fully dark.
  if (below === -1) {
    return { left: VIS_UNSEEN, right: VIS_UNSEEN };
  }

  const selfState = cellVisState(vision, x, y);

  // Camera-facing wall (floor below): whole cell takes the darker of
  // itself and the cell below.
  if (!isWallStitcheable(below)) {
    const darkness = Math.max(selfState, cellVisState(vision, x, y + 1));
    return { left: darkness, right: darkness };
  }

  // Internal wall (below is also a wall): split into halves.
  return {
    left: sideDarkness(grid, vision, x, y, selfState, x - 1),
    right: sideDarkness(grid, vision, x, y, selfState, x + 1),
  };
};
