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
"""Port of com.shatteredpixel.shatteredpixeldungeon.levels.painters.CavesPainter."""

from __future__ import annotations

from typing import List

from app.engine.dungeon.spd_levelgen import terrain
from app.engine.dungeon.spd_levelgen.level import GenLevel
from app.engine.dungeon.spd_levelgen.regular_painter import RegularPainter
from app.engine.dungeon.spd_levelgen.room import Room
from app.engine.dungeon.spd_levelgen.room_types import StandardRoom
from app.engine.dungeon.spd_random import SPDRandom


class CavesPainter(RegularPainter):

    def decorate(self, rng: SPDRandom, level: GenLevel, rooms: List[Room]) -> None:
        m = level.map
        w = level.width()
        l = level.length()

        # Pass 1: merge non-connected neighbour pairs (RNG order critical)
        for r in rooms:
            for n in r.neighbours:
                if n not in r.connected:
                    merge_tile = terrain.REGION_DECO if rng.IntMax(3) == 0 else terrain.CHASM
                    self._merge_rooms(rng, level, r, n, None, merge_tile)

        # Pass 2: corner-fill large rooms (square > 8, random per corner)
        for room in rooms:
            if not isinstance(room, StandardRoom):
                continue
            if room.width() <= 4 or room.height() <= 4:
                continue
            s = room.square()

            # top-left
            if rng.IntMax(s) > 8:
                corner = (room.left + 1) + (room.top + 1) * w
                if (m[corner] not in terrain.SOLID
                        and m[corner - 1] == terrain.WALL
                        and level.cell_to_point(corner - 1) not in room.connected.values()
                        and m[corner - w] == terrain.WALL
                        and level.cell_to_point(corner - w) not in room.connected.values()
                        and m[corner + 1] != terrain.TRAP
                        and m[corner + w] != terrain.TRAP):
                    m[corner] = terrain.WALL
                    level.traps.pop(corner, None)

            # top-right
            if rng.IntMax(s) > 8:
                corner = (room.right - 1) + (room.top + 1) * w
                if (m[corner] not in terrain.SOLID
                        and m[corner + 1] == terrain.WALL
                        and level.cell_to_point(corner + 1) not in room.connected.values()
                        and m[corner - w] == terrain.WALL
                        and level.cell_to_point(corner - w) not in room.connected.values()
                        and m[corner - 1] != terrain.TRAP
                        and m[corner + w] != terrain.TRAP):
                    m[corner] = terrain.WALL
                    level.traps.pop(corner, None)

            # bottom-left
            if rng.IntMax(s) > 8:
                corner = (room.left + 1) + (room.bottom - 1) * w
                if (m[corner] not in terrain.SOLID
                        and m[corner - 1] == terrain.WALL
                        and level.cell_to_point(corner - 1) not in room.connected.values()
                        and m[corner + w] == terrain.WALL
                        and level.cell_to_point(corner + w) not in room.connected.values()
                        and m[corner + 1] != terrain.TRAP
                        and m[corner - w] != terrain.TRAP):
                    m[corner] = terrain.WALL
                    level.traps.pop(corner, None)

            # bottom-right
            if rng.IntMax(s) > 8:
                corner = (room.right - 1) + (room.bottom - 1) * w
                if (m[corner] not in terrain.SOLID
                        and m[corner + 1] == terrain.WALL
                        and level.cell_to_point(corner + 1) not in room.connected.values()
                        and m[corner + w] == terrain.WALL
                        and level.cell_to_point(corner + w) not in room.connected.values()
                        and m[corner - 1] != terrain.TRAP
                        and m[corner - w] != terrain.TRAP):
                    m[corner] = terrain.WALL
                    level.traps.pop(corner, None)

        # Pass 3: EMPTY -> EMPTY_DECO based on orthogonal WALL neighbour count
        for i in range(w + 1, l - w):
            if m[i] == terrain.EMPTY:
                n = (
                    (1 if m[i + 1] == terrain.WALL else 0)
                    + (1 if m[i - 1] == terrain.WALL else 0)
                    + (1 if m[i + w] == terrain.WALL else 0)
                    + (1 if m[i - w] == terrain.WALL else 0)
                )
                if rng.IntMax(6) <= n:
                    m[i] = terrain.EMPTY_DECO

        # Pass 4: generateGold -- WALL above passable tile -> WALL_DECO (1/4)
        self._generate_gold(rng, level)

    def _generate_gold(self, rng: SPDRandom, level: GenLevel) -> None:
        m = level.map
        w = level.width()
        l = level.length()
        for i in range(l - w):
            if m[i] == terrain.WALL and m[i + w] in terrain.PASSABLE and rng.IntMax(4) == 0:
                m[i] = terrain.WALL_DECO
