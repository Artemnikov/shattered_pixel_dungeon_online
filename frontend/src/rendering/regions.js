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
 * Depth -> region mapping. Mirrors the SPD pattern of 5-floor regions
 * with a boss on the 5th floor of each region:
 *   1-5    sewers
 *   6-10   prison
 *   11-15  caves
 *   16-20  city
 *   21+    halls
 *
 * The atlas layout is identical across regions in SPD's tile sheets, so
 * the same wallMapper / terrainMapper logic works as long as we feed in
 * the right region's PNG.
 */
export const regionForDepth = (depth) => {
  if (depth <= 5) return 'sewers';
  if (depth <= 10) return 'prison';
  if (depth <= 15) return 'caves';
  if (depth <= 20) return 'city';
  return 'halls';
};

export const tilesForDepth = (assetImages, depth) => {
  const region = regionForDepth(depth);
  const fromRegion = assetImages.tilesByRegion?.[region];
  // Fall back to the sewers atlas (or `tiles` for back-compat) if the
  // region's PNG hasn't loaded yet — better than rendering nothing.
  return fromRegion || assetImages.tilesByRegion?.sewers || assetImages.tiles;
};
