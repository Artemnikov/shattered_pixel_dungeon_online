import test from 'node:test';
import assert from 'node:assert/strict';

import {
  VIS_DISCOVERED,
  VIS_UNSEEN,
  VIS_VISIBLE,
  cellVisState,
  tileAt,
  wallEdgeDarkness,
} from './wallFog.js';

const W = 1; // BACKEND_TILE.WALL.id
const F = 6; // some floor tile id

// Compact grid helper: rows top→bottom, cols left→right.
const g = (...rows) => rows;

const vision = (visible, discovered) => ({
  visible: new Set(visible),
  discovered: new Set(discovered ?? visible),
});

test('cellVisState — visible / discovered / unseen', () => {
  const v = vision(['1,1'], ['1,1', '2,2']);
  assert.equal(cellVisState(v, 1, 1), VIS_VISIBLE);
  assert.equal(cellVisState(v, 2, 2), VIS_DISCOVERED);
  assert.equal(cellVisState(v, 9, 9), VIS_UNSEEN);
});

test('tileAt — out of bounds returns -1', () => {
  const grid = g([F, F], [F, F]);
  assert.equal(tileAt(grid, -1, 0), -1);
  assert.equal(tileAt(grid, 2, 0), -1);
  assert.equal(tileAt(grid, 0, -1), -1);
  assert.equal(tileAt(grid, 0, 2), -1);
  assert.equal(tileAt(grid, 0, 0), F);
});

test('internal wall, both sides floor, all visible -> no dimming', () => {
  const grid = g(
    [W, W, W],
    [F, W, F],
    [F, W, F],
  );
  const v = vision(['1,1', '0,1', '2,1']);
  assert.deepEqual(wallEdgeDarkness(grid, v, 1, 1), {
    left: VIS_VISIBLE,
    right: VIS_VISIBLE,
  });
});

test('internal wall, left floor neighbor undiscovered -> left half fully dark', () => {
  const grid = g(
    [W, W, W],
    [F, W, F],
    [F, W, F],
  );
  // (0,1) not in either set -> unseen
  const v = vision(['1,1', '2,1']);
  assert.deepEqual(wallEdgeDarkness(grid, v, 1, 1), {
    left: VIS_UNSEEN,
    right: VIS_VISIBLE,
  });
});

test('internal wall, diagonal neighbor is wall and below-diagonal is floor -> darkest of three', () => {
  const grid = g(
    [W, W, W, W],
    [W, W, F, F],
    [F, W, F, F],
  );
  // cell (1,1): below (1,2)=W -> internal. left neighbor (0,1)=W (wall),
  // below-left (0,2)=F (not wall) -> left = max(self, (0,2), (0,1))
  const v = vision(['1,1', '0,2', '2,1'], ['1,1', '0,2', '0,1', '2,1']);
  assert.deepEqual(wallEdgeDarkness(grid, v, 1, 1), {
    left: VIS_DISCOVERED, // (0,1) only discovered, not visible
    right: VIS_VISIBLE,
  });
});

test('internal wall, diagonal neighbor is wall and below-diagonal is also wall -> fully dark', () => {
  const grid = g(
    [W, W, W, W],
    [W, W, F, F],
    [W, W, F, F],
  );
  const v = vision(['1,1', '0,2', '0,1', '2,1']);
  assert.deepEqual(wallEdgeDarkness(grid, v, 1, 1), {
    left: VIS_UNSEEN,
    right: VIS_VISIBLE,
  });
});

test('camera-facing wall (floor below) — both halves take darker of self/below', () => {
  const grid = g(
    [F, F, F],
    [W, W, W],
    [F, F, F],
  );
  // visible: self visible, below only discovered
  const v = vision(['1,1'], ['1,1', '1,2']);
  assert.deepEqual(wallEdgeDarkness(grid, v, 1, 1), {
    left: VIS_DISCOVERED,
    right: VIS_DISCOVERED,
  });
});

test('camera-facing wall — fully visible self and below -> no dimming', () => {
  const grid = g(
    [F, F, F],
    [W, W, W],
    [F, F, F],
  );
  const v = vision(['1,1', '1,2']);
  assert.deepEqual(wallEdgeDarkness(grid, v, 1, 1), {
    left: VIS_VISIBLE,
    right: VIS_VISIBLE,
  });
});

test('map-edge wall (x=0) — left half always fully dark, right half from neighbor', () => {
  const grid = g(
    [W, F],
    [W, F],
  );
  const v = vision(['0,0', '1,0']);
  assert.deepEqual(wallEdgeDarkness(grid, v, 0, 0), {
    left: VIS_UNSEEN,
    right: VIS_VISIBLE,
  });
});

test('last-row wall (nothing below the map) -> fully dark', () => {
  const grid = g([W, F]);
  const v = vision(['0,0', '1,0']);
  assert.deepEqual(wallEdgeDarkness(grid, v, 0, 0), {
    left: VIS_UNSEEN,
    right: VIS_UNSEEN,
  });
});
