export function resolveTapAction({ tileX, tileY, playerTile, mobs }) {
  if (!playerTile) {
    return { type: 'MOVE_TO', x: tileX, y: tileY };
  }

  const px = Math.round(playerTile.x);
  const py = Math.round(playerTile.y);
  const dx = tileX - px;
  const dy = tileY - py;
  const chebyshev = Math.max(Math.abs(dx), Math.abs(dy));

  if (chebyshev === 0) {
    return { type: 'WAIT' };
  }

  if (chebyshev <= 1) {
    const npc = mobs && Object.values(mobs).find(
      m => m.type === 'npc' && Math.round(m.pos.x) === tileX && Math.round(m.pos.y) === tileY
    );
    if (npc) {
      return { type: 'NPC_INTERACT', npc_id: npc.id };
    }
  }

  if (chebyshev === 1) {
    let direction = null;
    if (dx === 0 && dy === -1) direction = 'UP';
    else if (dx === 0 && dy === 1) direction = 'DOWN';
    else if (dx === -1 && dy === 0) direction = 'LEFT';
    else if (dx === 1 && dy === 0) direction = 'RIGHT';
    else if (dx === -1 && dy === -1) direction = 'UP_LEFT';
    else if (dx === 1 && dy === -1) direction = 'UP_RIGHT';
    else if (dx === -1 && dy === 1) direction = 'DOWN_LEFT';
    else if (dx === 1 && dy === 1) direction = 'DOWN_RIGHT';
    return { type: 'MOVE', direction };
  }

  return { type: 'MOVE_TO', x: tileX, y: tileY };
}
