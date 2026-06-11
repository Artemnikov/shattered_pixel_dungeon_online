import test from 'node:test';
import assert from 'node:assert/strict';

import {
  getInternalWallTop,
  getRaisedWallFace,
  getSewerCap,
  getSewerDoorCap,
  getSewerWallInstructions,
  getWallOverhang,
} from './wallMapper.js';
import { BACKEND_TILE, WALL_INDEX } from './constants.js';

const W = BACKEND_TILE.WALL.id;
const F = BACKEND_TILE.FLOOR.id;
const D = BACKEND_TILE.DOOR.id;
const LD = BACKEND_TILE.LOCKED_DOOR.id;
const WD = BACKEND_TILE.WALL_DECO.id;

// Compact grid helper: rows top→bottom, cols left→right.
const g = (...rows) => rows;

test('getRaisedWallFace — wall with floor below + walls on both sides = solid face', () => {
  const grid = g(
    [W, W, W],
    [W, W, W],
    [F, F, F],
  );
  // Cell (1, 1): wall; below (1, 2) = floor; left (0, 1) and right (2, 1) = walls.
  // Mask: right is wallStitcheable (no +1), left is wallStitcheable (no +2) → mask=0 (solid).
  const got = getRaisedWallFace(grid, 1, 1, W);
  // Must be one of the two alts (base or alt row) at mask=0.
  assert.ok(got === WALL_INDEX.RAISED_WALL || got === WALL_INDEX.RAISED_WALL_ALT,
    `expected RAISED_WALL or _ALT (solid, mask=0), got ${got}`);
});

test('getRaisedWallFace — wall with floor below + open to the right only = mask+1', () => {
  const grid = g(
    [W, W, F],
    [W, W, F],
    [F, F, F],
  );
  // Cell (1, 1): wall. Right (2, 1) = floor (open right). Left (0, 1) = wall.
  // Mask: +1 (right open), +0 (left closed) → mask = 1.
  const got = getRaisedWallFace(grid, 1, 1, W);
  assert.ok(
    got === WALL_INDEX.RAISED_WALL + 1 || got === WALL_INDEX.RAISED_WALL_ALT + 1,
    `expected RAISED_WALL+1 or _ALT+1 (open-right), got ${got}`,
  );
});

test('getRaisedWallFace — wall with wall below returns null (cap comes from below-pass)', () => {
  const grid = g(
    [W, W, W],
    [W, W, W],
    [W, W, W],
  );
  // Cell (1, 1) has a wall below at (1, 2) → no face should be drawn here.
  assert.equal(getRaisedWallFace(grid, 1, 1, W), null);
});

test('getRaisedWallFace — wall above a door gets the RAISED_WALL_DOOR sprite', () => {
  const grid = g(
    [W, W, W],
    [W, W, W],
    [F, D, F],
  );
  // Cell (1, 1) has a DOOR directly below at (1, 2).
  assert.equal(getRaisedWallFace(grid, 1, 1, W), WALL_INDEX.RAISED_WALL_DOOR);
});

test('getInternalWallTop — fully surrounded wall returns mask=0', () => {
  const grid = g(
    [W, W, W],
    [W, W, W],
    [W, W, W],
  );
  // Cell (1, 1): every 4-neighbour (right, rightBelow, leftBelow, left) is a wall.
  assert.equal(getInternalWallTop(grid, 1, 1, W), WALL_INDEX.WALL_INTERNAL);
});

test('getInternalWallTop — isolated wall with all four corners open = mask 1|2|4|8 = 15', () => {
  const grid = g(
    [W, W, W],
    [F, W, F],
    [F, F, F],
  );
  // Cell (1, 1): right (2,1)=F(+1), rightBelow (2,2)=F(+2), leftBelow (0,2)=F(+4), left (0,1)=F(+8).
  assert.equal(getInternalWallTop(grid, 1, 1, W), WALL_INDEX.WALL_INTERNAL + 15);
});

test('getInternalWallTop — WALL_DECO uses the DECO variant row', () => {
  const grid = g(
    [WD, WD, WD],
    [WD, WD, WD],
    [WD, WD, WD],
  );
  assert.equal(getInternalWallTop(grid, 1, 1, WD), WALL_INDEX.WALL_INTERNAL_DECO);
});

test('getWallOverhang — floor above wall, both below-diagonals are wall = mask 0', () => {
  const grid = g(
    [F, F, F],
    [F, F, F],
    [W, W, W],
  );
  // Cell (1, 1): below (1,2)=W, rightBelow (2,2)=W(no+1), leftBelow (0,2)=W(no+2) → mask=0.
  assert.equal(getWallOverhang(grid, 1, 1), WALL_INDEX.WALL_OVERHANG);
});

test('getWallOverhang — floor above wall, both below-diagonals non-wall = mask 3', () => {
  const grid = g(
    [F, F, F],
    [F, F, F],
    [F, W, F],
  );
  // Below (1,2)=W. rightBelow (2,2)=F (+1). leftBelow (0,2)=F (+2). Mask = 3.
  assert.equal(getWallOverhang(grid, 1, 1), WALL_INDEX.WALL_OVERHANG + 3);
});

test('getSewerCap — wall with wall below returns WALL_INTERNAL', () => {
  const grid = g(
    [W, W, W],
    [W, W, W],
    [W, W, W],
  );
  assert.equal(getSewerCap(grid, 1, 1, W), WALL_INDEX.WALL_INTERNAL);
});

test('getSewerCap — floor with wall below returns WALL_OVERHANG', () => {
  const grid = g(
    [F, F, F],
    [F, F, F],
    [W, W, W],
  );
  assert.equal(getSewerCap(grid, 1, 1, F), WALL_INDEX.WALL_OVERHANG);
});

test('getSewerCap — floor with floor below returns null', () => {
  const grid = g(
    [F, F, F],
    [F, F, F],
    [F, F, F],
  );
  assert.equal(getSewerCap(grid, 1, 1, F), null);
});

test('getSewerCap — floor with door below returns null (door caps live in base pass)', () => {
  const grid = g(
    [F, F, F],
    [F, F, F],
    [F, D, F],
  );
  assert.equal(getSewerCap(grid, 1, 1, F), null);
});

test('getSewerCap — side-door cell with wall below returns null (door caps live in base pass)', () => {
  const grid = g(
    [W, W, W],
    [F, D, F],
    [W, W, W],
  );
  assert.equal(getSewerCap(grid, 1, 1, D), null);
});

test('getSewerCap — wall above a door returns null (door caps live in base pass)', () => {
  const grid = g(
    [W, W, W],
    [W, W, W],
    [W, LD, W],
  );
  assert.equal(getSewerCap(grid, 1, 1, W), null);
});

test('getSewerDoorCap — floor with closed door below returns DOOR_OVERHANG', () => {
  const grid = g(
    [F, F, F],
    [F, F, F],
    [F, D, F],
  );
  assert.equal(
    getSewerDoorCap(grid, 1, 1, F, new Set()),
    WALL_INDEX.DOOR_OVERHANG,
  );
});

test('getSewerDoorCap — floor with an OPEN door below returns DOOR_OVERHANG_OPEN', () => {
  const grid = g(
    [F, F, F],
    [F, F, F],
    [F, D, F],
  );
  const openDoors = new Set(['1,2']);
  assert.equal(
    getSewerDoorCap(grid, 1, 1, F, openDoors),
    WALL_INDEX.DOOR_OVERHANG_OPEN,
  );
});

test('getSewerDoorCap — closed side-door cell with wall below returns DOOR_SIDEWAYS_OVERHANG_CLOSED', () => {
  const grid = g(
    [W, W, W],
    [F, D, F],
    [W, W, W],
  );
  // Below (1,2)=W. rightBelow (2,2)=W (no +1). leftBelow (0,2)=W (no +2). Mask=0.
  assert.equal(
    getSewerDoorCap(grid, 1, 1, D, new Set()),
    WALL_INDEX.DOOR_SIDEWAYS_OVERHANG_CLOSED,
  );
});

test('getSewerDoorCap — open side-door cell with wall below returns DOOR_SIDEWAYS_OVERHANG', () => {
  const grid = g(
    [W, W, W],
    [F, D, F],
    [W, W, W],
  );
  assert.equal(
    getSewerDoorCap(grid, 1, 1, D, new Set(['1,1'])),
    WALL_INDEX.DOOR_SIDEWAYS_OVERHANG,
  );
});

test('getSewerDoorCap — locked side-door cell with wall below returns DOOR_SIDEWAYS_OVERHANG_LOCKED', () => {
  const grid = g(
    [W, W, W],
    [F, LD, F],
    [W, W, W],
  );
  assert.equal(
    getSewerDoorCap(grid, 1, 1, LD, new Set()),
    WALL_INDEX.DOOR_SIDEWAYS_OVERHANG_LOCKED,
  );
});

test('getSewerDoorCap — wall above a locked side-door (floor on both sides) returns DOOR_SIDEWAYS_LOCKED', () => {
  const grid = g(
    [W, W, W],
    [F, LD, F],
    [W, W, W],
  );
  assert.equal(
    getSewerDoorCap(grid, 1, 0, W, new Set()),
    WALL_INDEX.DOOR_SIDEWAYS_LOCKED,
  );
});

test('getSewerDoorCap — wall above a closed side-door (floor on both sides) returns DOOR_SIDEWAYS', () => {
  const grid = g(
    [W, W, W],
    [F, D, F],
    [W, W, W],
  );
  assert.equal(
    getSewerDoorCap(grid, 1, 0, W, new Set()),
    WALL_INDEX.DOOR_SIDEWAYS,
  );
});

test('getSewerDoorCap — wall above a locked door walled in on both sides (alcove) returns DOOR_OVERHANG', () => {
  // Mirrors the Goo boss arena's locked-exit pedestal: walls on both sides
  // and above the door, so the door renders front-facing (RAISED_DOOR_LOCKED)
  // rather than as a side-door body — the cell above gets the regular
  // door-overhang cap, not a sideways one.
  const grid = g(
    [W, W, W],
    [W, W, W],
    [W, LD, W],
  );
  assert.equal(
    getSewerDoorCap(grid, 1, 1, W, new Set()),
    WALL_INDEX.DOOR_OVERHANG,
  );
});

test('getSewerDoorCap — floor with floor below returns null', () => {
  const grid = g(
    [F, F, F],
    [F, F, F],
    [F, F, F],
  );
  assert.equal(getSewerDoorCap(grid, 1, 1, F, new Set()), null);
});

test('getSewerWallInstructions — wall above floor returns a raised-face instruction', () => {
  const grid = g(
    [W, W, W],
    [W, W, W],
    [F, F, F],
  );
  const out = getSewerWallInstructions(grid, 1, 1);
  assert.equal(out.length, 1);
  // At mask=0 the returned index is RAISED_WALL or its alt row.
  assert.ok(
    out[0].srcIndex === WALL_INDEX.RAISED_WALL
      || out[0].srcIndex === WALL_INDEX.RAISED_WALL_ALT,
  );
});

test('getSewerWallInstructions — wall above wall returns an internal-top instruction', () => {
  const grid = g(
    [W, W, W],
    [W, W, W],
    [W, W, W],
  );
  const out = getSewerWallInstructions(grid, 1, 1);
  assert.equal(out.length, 1);
  assert.equal(out[0].srcIndex, WALL_INDEX.WALL_INTERNAL);
});

test('getSewerWallInstructions — non-wall tile returns empty list', () => {
  const grid = g(
    [F, F, F],
    [F, F, F],
    [F, F, F],
  );
  assert.deepEqual(getSewerWallInstructions(grid, 1, 1), []);
});
