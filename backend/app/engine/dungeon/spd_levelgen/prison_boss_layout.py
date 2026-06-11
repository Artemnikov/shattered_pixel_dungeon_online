# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 ArtemNikov
#
# Adapted from Shattered Pixel Dungeon (C) 2014-2024 Evan Debenham
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
"""Direct port of the hardcoded 32x32 layout from
levels/PrisonBossLevel.java -- the START/FIGHT_START/FIGHT_PAUSE/FIGHT_ARENA/WON
map variants and the helpers that build/patch them."""

from __future__ import annotations

from app.engine.dungeon.spd_levelgen import terrain
from app.engine.dungeon.spd_levelgen.geom import Point, Rect
from app.engine.dungeon.spd_levelgen.level import Feeling, GenLevel
from app.engine.dungeon.spd_levelgen.painter import Painter
from app.engine.dungeon.spd_random import SPDRandom

SIZE = 32

ENTRANCE_POS = 10 + 4 * SIZE
ENTRANCE_ROOM = Rect(8, 2, 13, 8)
START_HALLWAY = Rect(9, 7, 12, 24)
START_CELLS = [
    Rect(5, 9, 10, 16),
    Rect(11, 9, 16, 16),
    Rect(5, 15, 10, 22),
    Rect(11, 15, 16, 22),
]
TENGU_CELL = Rect(6, 23, 15, 32)
TENGU_CELL_CENTER = Point(10, 27)
TENGU_CELL_DOOR = Point(10, 23)
START_TORCHES = [
    Point(10, 2),
    Point(7, 9), Point(13, 9),
    Point(7, 15), Point(13, 15),
    Point(8, 23), Point(12, 23),
]

PAUSE_SAFE_AREA = Rect(9, 2, 12, 12)

ARENA = Rect(3, 1, 18, 16)

END_START = Point(START_HALLWAY.left + 2, START_HALLWAY.top + 2)
LEVEL_EXIT = Point(END_START.x + 11, END_START.y + 6)

_W = terrain.WALL
_D = terrain.WALL_DECO
_e = terrain.EMPTY
_E = terrain.EXIT
_C = terrain.CHASM

END_MAP = [
    _W, _W, _D, _W, _W, _W, _W, _W, _W, _W, _W, _W, _W, _W,
    _W, _e, _e, _e, _W, _W, _W, _W, _W, _W, _W, _W, _W, _W,
    _W, _e, _e, _e, _e, _e, _e, _e, _e, _W, _W, _W, _W, _W,
    _e, _e, _e, _e, _e, _e, _e, _e, _e, _e, _e, _e, _W, _W,
    _e, _e, _e, _e, _e, _e, _e, _e, _e, _e, _e, _e, _e, _W,
    _e, _e, _e, _C, _C, _C, _C, _C, _C, _C, _C, _e, _e, _W,
    _e, _W, _C, _C, _C, _C, _C, _C, _C, _C, _C, _E, _E, _W,
    _e, _e, _e, _C, _C, _C, _C, _C, _C, _C, _C, _E, _E, _W,
    _e, _e, _e, _e, _e, _C, _C, _C, _C, _C, _C, _E, _E, _W,
    _e, _e, _e, _e, _e, _e, _e, _W, _W, _W, _C, _C, _C, _W,
    _W, _e, _e, _e, _e, _e, _W, _W, _W, _W, _C, _C, _C, _W,
    _W, _e, _e, _e, _e, _W, _W, _W, _W, _W, _W, _C, _C, _W,
    _W, _W, _W, _W, _W, _W, _W, _W, _W, _W, _W, _C, _C, _W,
    _W, _W, _W, _W, _W, _W, _W, _W, _W, _W, _W, _C, _C, _W,
    _W, _D, _W, _W, _W, _W, _W, _W, _W, _W, _W, _C, _C, _W,
    _e, _e, _e, _W, _W, _W, _W, _W, _W, _W, _W, _C, _C, _W,
    _e, _e, _e, _W, _W, _W, _W, _W, _W, _W, _W, _C, _C, _W,
    _e, _e, _e, _W, _W, _W, _W, _W, _W, _W, _W, _C, _C, _W,
    _e, _e, _e, _W, _W, _W, _W, _W, _W, _W, _W, _C, _C, _W,
    _e, _e, _e, _W, _W, _W, _W, _W, _W, _W, _W, _C, _C, _W,
    _e, _e, _e, _W, _W, _W, _W, _W, _W, _W, _W, _C, _C, _W,
    _e, _e, _e, _W, _W, _W, _W, _W, _W, _W, _W, _C, _C, _W,
    _W, _W, _W, _W, _W, _W, _W, _W, _W, _W, _W, _C, _C, _W,
]

_NEIGHBOURS4 = (-SIZE, -1, 1, SIZE)


def _new_level(depth: int) -> GenLevel:
    level = GenLevel(depth, Feeling.NONE)
    level.set_size(SIZE, SIZE)
    return level


def _paint_start(level: GenLevel, rng: SPDRandom) -> None:
    """Port of setMapStart()."""
    Painter.fill(level, 0, 0, SIZE, SIZE, terrain.WALL)

    Painter.fill(level, ENTRANCE_ROOM, terrain.WALL)
    Painter.fill(level, ENTRANCE_ROOM, 1, terrain.EMPTY)
    Painter.set(level, ENTRANCE_POS, terrain.ENTRANCE)

    Painter.fill(level, START_HALLWAY, terrain.WALL)
    Painter.fill(level, START_HALLWAY, 1, terrain.EMPTY)

    Painter.set(level, START_HALLWAY.left + 1, START_HALLWAY.top, terrain.DOOR)

    for r in START_CELLS:
        Painter.fill(level, r, terrain.WALL)
        Painter.fill(level, r, 1, terrain.EMPTY)

    Painter.set(level, START_HALLWAY.left, START_HALLWAY.top + 5, terrain.DOOR)
    Painter.set(level, START_HALLWAY.right - 1, START_HALLWAY.top + 5, terrain.DOOR)
    Painter.set(level, START_HALLWAY.left, START_HALLWAY.top + 11, terrain.DOOR)
    Painter.set(level, START_HALLWAY.right - 1, START_HALLWAY.top + 11, terrain.DOOR)

    Painter.fill(level, TENGU_CELL, terrain.WALL)
    Painter.fill(level, TENGU_CELL, 1, terrain.EMPTY)

    Painter.set(level, TENGU_CELL.left + 4, TENGU_CELL.top, terrain.LOCKED_DOOR)

    for p in START_TORCHES:
        Painter.set(level, p, terrain.WALL_DECO)

    add_cages_to_cells(rng, level)


def build_start_grid(rng: SPDRandom, depth: int = 10) -> GenLevel:
    """Port of the START-state map (setMapStart())."""
    level = _new_level(depth)
    _paint_start(level, rng)
    return level


def apply_pause_patch(level: GenLevel, rng: SPDRandom) -> None:
    """Port of setMapPause(): rebuild the start layout, then patch it for the
    FIGHT_PAUSE phase (tengu door unlocked, startCells[1] passage opened,
    entrance sealed, hallway door rerouted)."""
    _paint_start(level, rng)

    Painter.set(level, TENGU_CELL.left + 4, TENGU_CELL.top, terrain.DOOR)

    Painter.fill(level, START_CELLS[1].left, START_CELLS[1].top + 3, 1, 7, terrain.EMPTY)
    Painter.fill(level, START_CELLS[1].left + 2, START_CELLS[1].top + 2, 3, 10, terrain.EMPTY)

    Painter.fill(level, ENTRANCE_ROOM, terrain.WALL)
    Painter.set(level, START_HALLWAY.left + 1, START_HALLWAY.top, terrain.EMPTY)
    Painter.set(level, START_HALLWAY.left + 1, START_HALLWAY.top + 1, terrain.DOOR)

    add_cages_to_cells(rng, level)


def build_arena_grid(level: GenLevel) -> None:
    """Port of setMapArena(): the open arena, in place on `level`."""
    Painter.fill(level, 0, 0, SIZE, SIZE, terrain.WALL)
    Painter.fill(level, ARENA, terrain.WALL)
    Painter.fill_ellipse(level, ARENA, 1, terrain.EMPTY)


def apply_end_patch(level: GenLevel, rng: SPDRandom) -> None:
    """Port of setMapEnd(): rebuild the start layout, unlock the tengu door,
    then stamp the chasm/exit endMap over the south half of the floor."""
    Painter.fill(level, 0, 0, SIZE, SIZE, terrain.WALL)
    _paint_start(level, rng)

    Painter.set(level, TENGU_CELL.left + 4, TENGU_CELL.top, terrain.DOOR)

    cell = level.point_to_cell(END_START)
    i = 0
    while cell < level.length():
        level.map[cell:cell + 14] = END_MAP[i:i + 14]
        i += 14
        cell += level.width()

    add_cages_to_cells(rng, level)


def add_cages_to_cells(rng: SPDRandom, level: GenLevel) -> None:
    """Port of addCagesToCells(): up to 5 REGION_DECO cages on cells adjacent
    to a wall, drawn from a separate RNG sequence."""
    rng.push_generator(rng.Long())
    try:
        for _ in range(5):
            cell = random_prison_cell_pos(rng, level)
            valid = False
            for j in _NEIGHBOURS4:
                if level.map[cell + j] == terrain.WALL:
                    valid = True
            if valid:
                Painter.set(level, cell, terrain.REGION_DECO)
    finally:
        rng.pop_generator()


def random_prison_cell_pos(rng: SPDRandom, level: GenLevel) -> int:
    """Port of randomPrisonCellPos()."""
    room = START_CELLS[rng.IntMax(len(START_CELLS))]
    return (rng.IntRange(room.left + 1, room.right - 2)
            + level.width() * rng.IntRange(room.top + 1, room.bottom - 2))


def random_tengu_cell_pos(rng: SPDRandom, level: GenLevel) -> int:
    """Port of randomTenguCellPos()."""
    return (rng.IntRange(TENGU_CELL.left + 1, TENGU_CELL.right - 2)
            + level.width() * rng.IntRange(TENGU_CELL.top + 1, TENGU_CELL.bottom - 2))
