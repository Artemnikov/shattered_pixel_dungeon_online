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
