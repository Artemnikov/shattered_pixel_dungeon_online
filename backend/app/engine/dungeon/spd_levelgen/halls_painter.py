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
"""Port of com.shatteredpixel.shatteredpixeldungeon.levels.painters.HallsPainter."""

from __future__ import annotations

from typing import List

from app.engine.dungeon.spd_levelgen import terrain
from app.engine.dungeon.spd_levelgen.level import GenLevel
from app.engine.dungeon.spd_levelgen.regular_painter import RegularPainter
from app.engine.dungeon.spd_levelgen.room import Room
from app.engine.dungeon.spd_random import SPDRandom

# PathFinder.NEIGHBOURS8 offsets (filled in relative to map width at paint time)
def _nb8(w: int) -> tuple:
    return (-w - 1, -w, -w + 1, -1, 1, w - 1, w, w + 1)


class HallsPainter(RegularPainter):

    def decorate(self, rng: SPDRandom, level: GenLevel, rooms: List[Room]) -> None:
        m = level.map
        w = level.width()
        l = level.length()
        nb8 = _nb8(w)

        # Pass 1: single sweep over interior cells (RNG order critical — before merge)
        for i in range(w + 1, l - w - 1):
            if m[i] == terrain.EMPTY:
                count = sum(1 for off in nb8 if m[i + off] in terrain.PASSABLE)
                if rng.IntMax(80) < count:
                    m[i] = terrain.EMPTY_DECO

            elif (m[i] == terrain.WALL
                    and m[i - 1] != terrain.WALL_DECO
                    and m[i - w] != terrain.WALL_DECO
                    and rng.IntMax(20) == 0):
                m[i] = terrain.WALL_DECO

            elif m[i] == terrain.REGION_DECO and rng.IntMax(2) == 0:
                m[i] = terrain.REGION_DECO_ALT

        # Pass 2: merge non-connected neighbour pairs
        for r in rooms:
            for n in r.neighbours:
                if n not in r.connected:
                    merge_tile = terrain.REGION_DECO if rng.IntMax(3) == 0 else terrain.CHASM
                    self._merge_rooms(rng, level, r, n, None, merge_tile)
