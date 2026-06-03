import { useEffect, useState } from 'react';
import itemsSrc from '../assets/pixel-dungeon/sprites/items.png';
import iconsSrc from '../assets/pixel-dungeon/sprites/item_icons.png';

// Per-cell alpha bounding boxes for a sprite atlas.
//
// SPD anchors each item's art to the TOP-LEFT of its grid cell and only spans a
// smaller rect (ItemSpriteSheet.assignItemRect), leaving transparent padding to
// the bottom-right. SPD's ItemSlot then centres that *cropped* art rect in the
// slot. We reproduce that here without porting ~200 hand-authored rects: decode
// the atlas once and measure the real alpha bounds of every cell.
//
// Each entry is the art's offset + size *within* its cell: { rx, ry, w, h }.
function createRectMap(src, cell) {
  const map = new Map();
  const subs = new Set();
  let isReady = false;

  const img = new Image();
  img.onload = () => {
    const W = img.width;
    const H = img.height;
    const cols = Math.floor(W / cell);
    const rows = Math.floor(H / cell);
    const canvas = document.createElement('canvas');
    canvas.width = W;
    canvas.height = H;
    const ctx = canvas.getContext('2d', { willReadFrequently: true });
    ctx.drawImage(img, 0, 0);
    let data;
    try {
      data = ctx.getImageData(0, 0, W, H).data;
    } catch {
      return; // tainted canvas — leave map empty, callers fall back to full cell
    }
    for (let row = 0; row < rows; row++) {
      for (let col = 0; col < cols; col++) {
        const x0 = col * cell;
        const y0 = row * cell;
        let minX = cell, minY = cell, maxX = -1, maxY = -1;
        for (let y = 0; y < cell; y++) {
          for (let x = 0; x < cell; x++) {
            if (data[((y0 + y) * W + (x0 + x)) * 4 + 3] > 0) {
              if (x < minX) minX = x;
              if (x > maxX) maxX = x;
              if (y < minY) minY = y;
              if (y > maxY) maxY = y;
            }
          }
        }
        if (maxX >= 0) {
          map.set(`${col},${row}`, { rx: minX, ry: minY, w: maxX - minX + 1, h: maxY - minY + 1 });
        }
      }
    }
    isReady = true;
    subs.forEach((fn) => fn());
  };
  img.src = src;

  return {
    cell,
    get(col, row) {
      return map.get(`${col},${row}`) || null;
    },
    get ready() {
      return isReady;
    },
    subscribe(fn) {
      subs.add(fn);
      return () => subs.delete(fn);
    },
  };
}

// items.png — 16x16 cells. item_icons.png — 8x8 cells.
export const itemRects = createRectMap(itemsSrc, 16);
export const iconRects = createRectMap(iconsSrc, 8);

// Re-render when an atlas finishes measuring, so the initial (rect-less) paint
// upgrades to the cropped/centred one.
export function useRectsReady(rectMap) {
  const [, bump] = useState(0);
  useEffect(() => {
    if (rectMap.ready) return undefined;
    return rectMap.subscribe(() => bump((n) => n + 1));
  }, [rectMap]);
  return rectMap.ready;
}
