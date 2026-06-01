// Decides what a tap/click on a tile means. A tap on a cardinally-adjacent tile
// is a single-step MOVE (which also melee-attacks when the tile holds an enemy),
// matching original SPD's tap-to-move/attack. This keeps mobile players able to
// step away or hit back even while a mob is adjacent — MOVE_TO pathfinding gets
// cancelled by the server the moment an enemy is next to you.
//
// playerTile is the player's logical tile { x, y } (entity.targetPos ?? renderPos).
// Returns the WebSocket message object to send, or null if there's no player yet.
export function resolveTapAction({ tileX, tileY, playerTile }) {
  if (!playerTile) {
    return { type: 'MOVE_TO', x: tileX, y: tileY };
  }

  const px = Math.round(playerTile.x);
  const py = Math.round(playerTile.y);
  const dx = tileX - px;
  const dy = tileY - py;
  const manhattan = Math.abs(dx) + Math.abs(dy);

  if (manhattan === 0) {
    // Tapped own tile: wait a turn (skip / wait out an attack cooldown).
    return { type: 'WAIT' };
  }

  if (manhattan === 1) {
    let direction = null;
    if (dy === -1) direction = 'UP';
    else if (dy === 1) direction = 'DOWN';
    else if (dx === -1) direction = 'LEFT';
    else if (dx === 1) direction = 'RIGHT';
    return { type: 'MOVE', direction };
  }

  // Game movement is cardinal-only; diagonal/distant taps path-find.
  return { type: 'MOVE_TO', x: tileX, y: tileY };
}
