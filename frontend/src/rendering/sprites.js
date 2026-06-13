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
import { TILE_SIZE, TILE_SCALE } from '../constants';

// Item Sprite Mapping
// Format: { name_keyword: [col, row] } — 0-indexed column/row in items.png (16x16 cells).
//
// Coordinates are ported from the original ItemSpriteSheet.java. That file's xy(x,y)
// helper is 1-based: idx = (x-1) + 16*(y-1); an item's index is its section base xy(...)
// plus its offset, and the grid cell is [idx % 16, idx // 16]. (items.png is the same
// 256x512 / 16x32 atlas as the original game.) NOTE: the numbers in the source's
// assignItemRect(NAME, w, h) calls are the sprite's pixel width/height, NOT the cell.
//
// Matching below is substring-based (itemName.includes(key)), so more-specific keys must
// be listed before the generic ones they contain (e.g. "Scroll Holder" before "Scroll").
export const ITEM_SPRITES = {
  // Weapons (WEP_TIER1 = xy(1,7) = idx 96 -> row 6; WEP_TIER2 = xy(9,7) = idx 104)
  "Throwable Dagger": [2, 9],   // THROWING_KNIFE (MISSILE_WEP+2)
  "Throwing":         [2, 9],
  "Worn Key":         [10, 3],  // WORN_KEY (MISC_CONSUMABLE+10 = idx 58) — before "Worn"
  "Worn":             [0, 6],   // WORN_SHORTSWORD
  "Rusty Sword":      [1, 6],   // SHORT_SWORD (WEP_TIER1+1)
  "Shortsword":       [8, 6],   // SHORTSWORD (WEP_TIER2+0)
  "Dagger":           [4, 6],   // DAGGER (WEP_TIER1+4)
  "Wooden Club":      [2, 6],   // GLOVES/club-ish (WEP_TIER1+2)
  "Club":             [2, 6],
  "Mace":             [10, 6],  // MACE (WEP_TIER3+0)
  "Sword":            [9, 6],   // SWORD (WEP_TIER2+1)
  "Mage's Staff":     [5, 6],   // MAGES_STAFF (WEP_TIER1+5)
  "Magic Staff":      [5, 6],
  "Staff":            [5, 6],

  // Bows / ranged (MISSILE_WEP = xy(1,10) = idx 144 -> row 9)
  "Spirit Bow":       [0, 9],   // SPIRIT_BOW
  "Old Bow":          [0, 9],
  "Bow":              [0, 9],
  "Boomerang":        [12, 9],  // BOOMERANG (MISSILE_WEP+12)
  "Stone":            [3, 9],   // THROWING_STONE (MISSILE_WEP+3)

  // Armor (ARMOR = xy(1,12) = idx 176 -> row 11)
  "Cloth Armor":      [0, 11],  // ARMOR_CLOTH
  "Leather Vest":     [1, 11],  // ARMOR_LEATHER (ARMOR+1)
  "Leather":          [1, 11],
  "Broken Shield":    [2, 11],  // ARMOR_MAIL (ARMOR+2) — closest stand-in
  "Mail Armor":       [2, 11],
  "Rogue's Cloak":    [7, 11],  // ARMOR_ROGUE (ARMOR+7)

  // Wands / rings / artifacts (section bases, generic first entry)
  "Wand":             [0, 13],  // WANDS = xy(1,14) = idx 208
  "Ring":             [0, 14],  // RINGS = xy(1,15) = idx 224
  "Artifact":         [0, 15],  // ARTIFACTS = xy(1,16) = idx 240

  // Bags (BAGS = xy(1,31) = idx 480 -> row 30). Listed before Scroll/Potion so the
  // specialised holder/bandolier names win over the generic consumable keys.
  "Backpack":         [1, 30],  // BACKPACK
  "Velvet Pouch":     [2, 30],  // POUCH
  "Scroll Holder":    [3, 30],  // HOLDER
  "Potion Bandolier": [4, 30],  // BANDOLIER
  "Magical Holster":  [5, 30],  // HOLSTER

  // Consumables (generic first entry of each section)
  "Metamorphosis":    [5, 19],  // SCROLL_METAMORPH (SCROLLS+5 = idx 309)
  "Scroll":           [0, 19],  // SCROLLS = xy(1,20) = idx 304
  "Health Potion":    [0, 22],  // POTIONS = xy(1,23) = idx 352
  "Reviving Potion":  [0, 22],
  "Elixir of Aquatic Rejuvenation": [9, 25],  // ELIXIR_AQUA (ELIXIRS+1, ELIXIRS=xy(9,26))
  "Potion":           [0, 22],
  "Food":             [0, 27],  // FOOD = xy(1,28) = idx 432

  // Seeds (SEEDS = xy(1,25) = idx 384 -> col0,row24; per-kind names like "Sungrass Seed")
  "Sungrass Seed":    [3, 24],  // SEED_SUNGRASS (SEEDS+3)
  "Earthroot Seed":   [8, 24],  // SEED_EARTHROOT (SEEDS+8)
  "Firebloom Seed":   [1, 24],  // SEED_FIREBLOOM (SEEDS+1)
  "Icecap Seed":      [4, 24],  // SEED_ICECAP (SEEDS+4)
  "Sorrowmoss Seed":  [6, 24],  // SEED_SORROWMOSS (SEEDS+6)
  "Dreamfoil Seed":   [7, 24],  // SEED_MAGEROYAL slot (SEEDS+7) — no SPD dreamfoil seed sprite
  "Fadeleaf Seed":    [10, 24], // SEED_FADELEAF (SEEDS+10)
  "Rotberry Seed":    [0, 24],  // SEED_ROTBERRY (SEEDS+0)
  "Starflower Seed":  [9, 24],  // SEED_STARFLOWER (SEEDS+9)
  "Stormvine Seed":   [5, 24],  // SEED_STORMVINE (SEEDS+5)
  "Blindweed Seed":   [11, 24], // SEED_BLINDWEED (SEEDS+11)
  "Swiftthistle Seed":[2, 24],  // SEED_SWIFTTHISTLE (SEEDS+2)
  "Seed":             [3, 24],  // generic Seed / "Seed of Sunlight" -> SEED_SUNGRASS

  // Misc
  "Tengu's Mask":     [0, 6],   // MASK (WEP_TIER1+0 = idx 96 = col 0, row 6 in items.png)
  "Goo Blob":         [7, 29],  // BLOB (QUEST+7, QUEST = xy(1,30) = idx 464)
  "Gold":             [2, 1],   // GOLD (UNCOLLECTIBLE+0 = xy(3,2) = idx 18)
  "Dewdrop":          [5, 1],   // DEWDROP (UNCOLLECTIBLE+3 = idx 21)
  "Waterskin":        [0, 30],  // WATERSKIN = BAGS+0 = xy(1,31) -> idx 480 -> col0,row30
  "Golden Key":       [8, 3],   // GOLDEN_KEY (MISC_CONSUMABLE+8 = idx 56)
  "Crystal Key":      [9, 3],   // CRYSTAL_KEY (MISC_CONSUMABLE+9 = idx 57)
  "Rusty Key":        [7, 3],   // IRON_KEY (MISC_CONSUMABLE+7 = idx 55)
  "Key":              [7, 3],

  // Default fallback (SOMETHING "?" placeholder, idx 0)
  "default":          [0, 0],
};

// Placeholder sprites shown in empty equip slots (ItemSpriteSheet PLACEHOLDERS row,
// base idx 0 -> row 0). Keyed by InventoryPane equip-slot key.
export const HOLDER_SPRITES = {
  weapon:   [1, 0],  // WEAPON_HOLDER
  armor:    [2, 0],  // ARMOR_HOLDER
  artifact: [6, 0],  // ARTIFACT_HOLDER
  misc:     [7, 0],  // TRINKET_HOLDER
  ring:     [5, 0],  // RING_HOLDER
};

export const getItemSpriteCoords = (itemName, itemType) => {
  for (const key in ITEM_SPRITES) {
    if (itemName && itemName.includes(key)) {
      return ITEM_SPRITES[key];
    }
  }
  // Type fallbacks — also cover unidentified potions/scrolls (masked name, kept type).
  if (itemType === 'weapon')    return [8, 6];
  if (itemType === 'wearable')  return [0, 11];
  if (itemType === 'potion')    return [0, 22];
  if (itemType === 'scroll')    return [0, 19];
  if (itemType === 'wand')      return [0, 13];
  if (itemType === 'ring')      return [0, 14];
  if (itemType === 'artifact')  return [0, 15];
  if (itemType === 'throwable') return [3, 9];
  if (itemType === 'food')      return [0, 27];
  if (itemType === 'key')       return [7, 3];
  if (itemType === 'gold')      return [2, 1];
  if (itemType === 'seed')      return [3, 24];  // SEED_SUNGRASS
  if (itemType === 'dewdrop')   return [5, 1];   // DEWDROP
  return ITEM_SPRITES["default"];
};

// Quickslot placeholders (depleted stackables) only carry a `kind`, not a
// `name`/`type`/`appearance`. Map kind prefixes to a generic item-type sprite
// so the slot shows a recognizable (dimmed) icon instead of going blank.
const PLACEHOLDER_TYPE_BY_KIND_PREFIX = [
  ['potion', 'potion'],
  ['scroll', 'scroll'],
  ['stone', 'throwable'],
  ['boomerang', 'throwable'],
  ['throwable_dagger', 'throwable'],
  ['seed', 'seed'],
  ['mystery_meat', 'food'],
  ['berry', 'food'],
  ['small_ration', 'food'],
  ['ration', 'food'],
  ['pasty', 'food'],
  ['chargrilled_meat', 'food'],
  ['dewdrop', 'dewdrop'],
  ['gold', 'gold'],
];

// Resolve a serialized item to its sprite cell: server-sent per-run appearance
// (potion colour / scroll rune) first, then the name/type lookup table.
export const coordsForItem = (item) => {
  if (!item) return null;
  if (item.appearance) return [item.appearance.col, item.appearance.row];
  if (item.is_placeholder && item.kind) {
    const match = PLACEHOLDER_TYPE_BY_KIND_PREFIX.find(([prefix]) => item.kind.startsWith(prefix));
    if (match) return getItemSpriteCoords(null, match[1]);
  }
  return getItemSpriteCoords(item.name, item.type);
};

// Type-glyph overlay sprites — the small 8x8 icons SPD draws on an *identified*
// ring/scroll/potion/wand slot (ItemSpriteSheet.Icons). [col, row] in the 16x8
// grid of item_icons.png. Sections: RINGS row 0, SCROLLS row 2, POTIONS row 5.
// Matched by name substring like ITEM_SPRITES. The remake's consumable taxonomy
// is currently thin, so only the items that have a concrete identity map here;
// add entries as more real subtypes land.
export const ITEM_GLYPHS = {
  "Health Potion": [1, 5],  // POTION_HEALING
};

// Glyph cell for an item, or null when it has no type-glyph or isn't identified.
// SPD only shows the glyph once the item's type is known; the backend masks the
// real name of unidentified potions/scrolls, so a name match here implies known.
export const getItemGlyphCoords = (item) => {
  if (!item || !item.name) return null;
  if (!item.level_known) return null;
  for (const key in ITEM_GLYPHS) {
    if (item.name.includes(key)) return ITEM_GLYPHS[key];
  }
  return null;
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
