import { TILE_SIZE, TILE_SCALE } from '../constants';

// Item Sprite Mapping (Simplified based on ItemSpriteSheet.java)
// Format: { name_keyword: [col, row] }
export const ITEM_SPRITES = {
  // Weapon Tier 1
  "Shortsword": [13, 13],
  "Mage's Staff": [15, 16],
  "Dagger": [12, 13],
  "Spirit Bow": [0, 10],

  // Weapon Tier 2
  "Wooden Club": [15, 15],
  "Spear": [0, 7],

  // Wearable
  "Cloth Armor": [15, 12],
  "Leather Vest": [14, 13],
  "Rogue's Cloak": [9, 15],
  "Broken Shield": [12, 16],

  // Potions
  "Potion": [12, 14],

  // Default
  "default": [8, 13],

  // Throwables (Approximated)
  "Stone": [10, 10],
  "Boomerang": [11, 10],
  "Throwable Dagger": [12, 13]
};

export const getItemSpriteCoords = (itemName, itemType) => {
  for (const key in ITEM_SPRITES) {
    if (itemName && itemName.includes(key)) {
      return ITEM_SPRITES[key];
    }
  }
  if (itemType === 'grave') return [3, 2]; // GRAVE cell in items.png (SPD ItemSpriteSheet)
  if (itemType === 'potion') return [12, 14];
  if (itemType === 'weapon') return [14, 14];
  if (itemType === 'wearable') return [14, 12];
  if (itemType === 'throwable') return [11, 10];
  return ITEM_SPRITES["default"];
};

export const fallbackTileMap = {
  1: { x: 0, y: 3 }, // Wall
  2: { x: 0, y: 0 }, // Floor
};

export const drawSpriteTile = (ctx, image, coords, x, y, flipX = false) => {
  if (!image || !coords) return;
  const sx = coords.x * (TILE_SIZE / TILE_SCALE);
  const sy = coords.y * (TILE_SIZE / TILE_SCALE);
  const dx = x * TILE_SIZE;
  const dy = y * TILE_SIZE;

  if (flipX) {
    ctx.save();
    ctx.translate(dx + TILE_SIZE, dy);
    ctx.scale(-1, 1);
    ctx.drawImage(
      image,
      sx,
      sy,
      TILE_SIZE / TILE_SCALE,
      TILE_SIZE / TILE_SCALE,
      0,
      0,
      TILE_SIZE,
      TILE_SIZE
    );
    ctx.restore();
    return;
  }

  ctx.drawImage(
    image,
    sx,
    sy,
    TILE_SIZE / TILE_SCALE,
    TILE_SIZE / TILE_SCALE,
    dx,
    dy,
    TILE_SIZE,
    TILE_SIZE
  );
};
