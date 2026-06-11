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
import itemsSrc from '../assets/pixel-dungeon/sprites/items.png';
import { coordsForItem } from '../rendering/sprites';
import { itemRects, useRectsReady } from '../rendering/spriteRects';

// Renders a single item sprite from items.png as a scaled, pixelated tile.
// Used by the SPD-style inventory window and quickslot bar. Resolution order:
// explicit `coords` (e.g. an empty-slot holder) -> server-sent per-run appearance
// (potion colour / scroll rune) -> name/type lookup table.
//
// Like SPD's ItemSlot, the art is anchored to the top-left of its 16x16 atlas
// cell and only spans a smaller rect; we crop to that measured rect and let the
// slot's flexbox centre it, so icons sit centred instead of skewed top-left.
export default function ItemIcon({ item, size = 32, coords: override }) {
  const ready = useRectsReady(itemRects);
  if (!override && !item) return null;
  const coords = override || coordsForItem(item) || [8, 13];
  const [col, row] = coords;
  const scale = size / 16;

  const rect = ready ? itemRects.get(col, row) : null;
  // Fall back to the full 16x16 cell until the atlas has been measured.
  const rx = rect ? rect.rx : 0;
  const ry = rect ? rect.ry : 0;
  const w = rect ? rect.w : 16;
  const h = rect ? rect.h : 16;

  return (
    <div
      className="item-icon"
      style={{
        width: w * scale,
        height: h * scale,
        backgroundImage: `url(${itemsSrc})`,
        backgroundPosition: `-${(col * 16 + rx) * scale}px -${(row * 16 + ry) * scale}px`,
        backgroundSize: `${256 * scale}px ${512 * scale}px`,
        imageRendering: 'pixelated',
      }}
    />
  );
}
