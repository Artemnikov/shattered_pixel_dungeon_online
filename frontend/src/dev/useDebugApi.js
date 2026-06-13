import { useEffect } from 'react';
import { BACKEND_TILE } from '../rendering/sewers/constants';

const TILE_NAMES = Object.fromEntries(
  Object.entries(BACKEND_TILE).map(([k, v]) => [v.id, k])
);

const ASCII = {
  0: ' ', 2: '.', 3: '+', 4: '<', 5: '>',
  6: '.', 7: '~', 8: '.', 9: '"', 10: 'L',
  11: '#', 12: '#', 13: '#', 14: '#', 15: '#',
  16: '#', 17: '#', 18: '.', 19: '"', 20: '#',
};

export default function useDebugApi({
  gridRef, entitiesRef, visionRef, openDoorsRef,
  myPlayerIdRef, panOffsetRef, cameraLerpRef, zoomRef,
  depthRef,
}) {
  useEffect(() => {
    if (!import.meta.env.DEV) return;

    const roundPos = (e) => ({ x: Math.round(e.renderPos.x), y: Math.round(e.renderPos.y) });

    const api = {
      tiles: () => gridRef.current,

      ascii: ({ entities = true } = {}) => {
        const g = gridRef.current;
        if (!g?.length) return '';
        const rows = g.map(row => row.map(t => ASCII[t] ?? '?'));
        if (entities) {
          Object.values(entitiesRef.current.mobs).forEach(m => {
            const { x, y } = roundPos(m);
            if (rows[y]?.[x] !== undefined) rows[y][x] = 'm';
          });
          Object.values(entitiesRef.current.players).forEach(p => {
            const { x, y } = roundPos(p);
            if (rows[y]?.[x] !== undefined) {
              rows[y][x] = p.id === myPlayerIdRef.current ? '@' : 'P';
            }
          });
        }
        return rows.map(r => r.join('')).join('\n');
      },

      entities: () => ({
        players: { ...entitiesRef.current.players },
        mobs: { ...entitiesRef.current.mobs },
      }),

      at: (x, y) => {
        const g = gridRef.current;
        const tileId = g?.[y]?.[x];
        const here = [];
        Object.values(entitiesRef.current.players).forEach(p => {
          const r = roundPos(p);
          if (r.x === x && r.y === y) here.push({ kind: 'player', ...p });
        });
        Object.values(entitiesRef.current.mobs).forEach(m => {
          const r = roundPos(m);
          if (r.x === x && r.y === y) here.push({ kind: 'mob', ...m });
        });
        return {
          tileId,
          tileName: TILE_NAMES[tileId] ?? 'UNKNOWN',
          visible: visionRef.current.visible.has(`${x},${y}`),
          discovered: visionRef.current.discovered.has(`${x},${y}`),
          doorOpen: openDoorsRef.current.has(`${x},${y}`),
          entities: here,
        };
      },

      vision: () => ({
        visibleCount: visionRef.current.visible.size,
        discoveredCount: visionRef.current.discovered.size,
        openDoorsCount: openDoorsRef.current.size,
      }),

      camera: () => ({
        x: cameraLerpRef.current.x,
        y: cameraLerpRef.current.y,
        zoom: zoomRef.current,
        pan: { ...panOffsetRef.current },
      }),

      me: () => {
        const id = myPlayerIdRef.current;
        return { id, player: entitiesRef.current.players[id] ?? null };
      },

      depth: () => depthRef.current,

      bounds: () => {
        const g = gridRef.current;
        return { rows: g?.length ?? 0, cols: g?.[0]?.length ?? 0 };
      },

      help: () => [
        'tiles()    2D array of tile ids',
        'ascii()    ASCII map with entities (# wall, . floor, ~ water, " grass, + door, < > stairs, @ me, P player, m mob)',
        'entities() { players, mobs }',
        'at(x,y)    tile + entities at cell',
        'vision()   visible/discovered counts',
        'camera()   { x, y, zoom, pan }',
        'me()       { id, player }',
        'depth()    current floor',
        'bounds()   { rows, cols }',
      ].join('\n'),
    };

    window.__debug = api;
    console.info('[debug] window.__debug ready — __debug.help()');

    return () => {
      if (window.__debug === api) delete window.__debug;
    };
  }, [gridRef, entitiesRef, visionRef, openDoorsRef, myPlayerIdRef, panOffsetRef, cameraLerpRef, zoomRef, depthRef]);
}
