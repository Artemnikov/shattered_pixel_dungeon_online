// Describe whatever occupies a cell, for the examine-mode "inspect" action.
// Mirrors the spirit of GameScene.examineCell() in the original Shattered Pixel
// Dungeon (look at a mob, item, or tile) but returns a short label that the caller
// shows as in-world floating text.
//
// Tile ids match the backend TileType enum (app/engine/dungeon/constants.py).
const TILE_NAMES = {
  0: 'Chasm',
  1: 'Wall',
  2: 'Floor',
  3: 'Open door',
  4: 'Stairs up',
  5: 'Stairs down',
  6: 'Wooden floor',
  7: 'Water',
  8: 'Cobbled floor',
  9: 'Grass',
  10: 'Locked door',
  17: 'Wall',
  18: 'Floor',
  19: 'High grass',
  20: 'Wall',
  21: 'Furrowed grass',
};

// Logical tile of an animated entity: prefer its server destination (targetPos),
// fall back to where it currently renders. The per-tick sync updates targetPos but
// not pos, so targetPos is the freshest logical cell.
function entityTile(e) {
  const p = e.targetPos || e.renderPos || e.pos;
  return p ? { x: Math.round(p.x), y: Math.round(p.y) } : null;
}

// Returns { name, sub } describing the cell, or null if there's nothing to make
// out (out of bounds). `sub` is an optional secondary line (e.g. a mob's HP).
export function describeCell({ tileX, tileY, gridRef, entitiesRef, visionRef, myPlayerId }) {
  const grid = gridRef.current;
  if (!grid || tileY < 0 || tileY >= grid.length || tileX < 0 || tileX >= (grid[0]?.length || 0)) {
    return null;
  }

  // Default anchor is the inspected world cell; mobs override it with their id so the
  // popup can follow the moving sprite (see computeInspectPos in App.jsx).
  const tileAnchor = { type: 'tile', x: tileX, y: tileY };

  const visible = visionRef.current.visible.has(`${tileX},${tileY}`);
  const discovered = visible || visionRef.current.discovered.has(`${tileX},${tileY}`);
  if (!discovered) return { name: 'Darkness', sub: null, anchor: tileAnchor };

  const ents = entitiesRef.current;

  // Mobs and players are only identifiable while currently visible.
  if (visible) {
    for (const mob of Object.values(ents.mobs || {})) {
      const t = entityTile(mob);
      if (t && t.x === tileX && t.y === tileY) {
        const hp = mob.hp != null && mob.max_hp != null ? `HP ${mob.hp}/${mob.max_hp}` : null;
        return { name: mob.name || 'Creature', sub: hp, anchor: { type: 'mob', id: mob.id } };
      }
    }
    for (const pl of Object.values(ents.players || {})) {
      const t = entityTile(pl);
      if (t && t.x === tileX && t.y === tileY) {
        return { name: pl.id === myPlayerId ? 'You' : (pl.name || 'Adventurer'), sub: null, anchor: tileAnchor };
      }
    }
    for (const item of ents.items || []) {
      if (item.pos && item.pos.x === tileX && item.pos.y === tileY) {
        return { name: item.name || 'Item', sub: null, anchor: tileAnchor };
      }
    }
  }

  return { name: TILE_NAMES[grid[tileY][tileX]] || 'Floor', sub: null, anchor: tileAnchor };
}
