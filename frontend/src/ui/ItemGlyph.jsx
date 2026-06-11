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
import iconsSrc from '../assets/pixel-dungeon/sprites/item_icons.png';
import { getItemGlyphCoords } from '../rendering/sprites';
import { iconRects, useRectsReady } from '../rendering/spriteRects';

// SPD's ItemSlot type-glyph: a small icon (from item_icons.png, 8x8 cells)
// overlaid on an identified ring/scroll/potion/wand slot. Cropped to the art's
// measured rect so it sits tight, like the main item sprite. Returns null when
// the item has no glyph (or isn't identified). `scale` is px per source pixel.
export default function ItemGlyph({ item, scale = 2 }) {
  const ready = useRectsReady(iconRects);
  const coords = getItemGlyphCoords(item);
  if (!coords) return null;
  const [col, row] = coords;

  const rect = ready ? iconRects.get(col, row) : null;
  const rx = rect ? rect.rx : 0;
  const ry = rect ? rect.ry : 0;
  const w = rect ? rect.w : 8;
  const h = rect ? rect.h : 8;

  return (
    <span
      className="inv-glyph"
      style={{
        width: w * scale,
        height: h * scale,
        backgroundImage: `url(${iconsSrc})`,
        backgroundPosition: `-${(col * 8 + rx) * scale}px -${(row * 8 + ry) * scale}px`,
        backgroundSize: `${128 * scale}px ${64 * scale}px`,
        imageRendering: 'pixelated',
      }}
    />
  );
}
