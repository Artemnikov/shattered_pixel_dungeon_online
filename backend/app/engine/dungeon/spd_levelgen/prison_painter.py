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
"""Port of com.shatteredpixel.shatteredpixeldungeon.levels.painters.PrisonPainter."""

from __future__ import annotations

from typing import List

from app.engine.dungeon.spd_levelgen import terrain
from app.engine.dungeon.spd_levelgen.level import GenLevel
from app.engine.dungeon.spd_levelgen.regular_painter import RegularPainter
from app.engine.dungeon.spd_levelgen.room import Room
from app.engine.dungeon.spd_levelgen.room_types import SpecialRoom
from app.engine.dungeon.spd_levelgen.standard_rooms import ChasmBridgeRoom, FissureRoom
from app.engine.dungeon.spd_random import SPDRandom


class PrisonPainter(RegularPainter):

    def decorate(self, rng: SPDRandom, level: GenLevel, rooms: List[Room]) -> None:
        m = level.map
        w = level.width()
        l = level.length()

        # Pass 1: EMPTY -> EMPTY_DECO near wall corners
        for i in range(w + 1, l - w - 1):
            if m[i] == terrain.EMPTY:
                c = 0.05
                if m[i + 1] == terrain.WALL and m[i + w] == terrain.WALL:
                    c += 0.2
                if m[i - 1] == terrain.WALL and m[i + w] == terrain.WALL:
                    c += 0.2
                if m[i + 1] == terrain.WALL and m[i - w] == terrain.WALL:
                    c += 0.2
                if m[i - 1] == terrain.WALL and m[i - w] == terrain.WALL:
                    c += 0.2
                if rng.Float() < c:
                    m[i] = terrain.EMPTY_DECO

        # Pass 2: CHASM -> REGION_DECO_ALT below another CHASM (stalactite visual)
        for r in rooms:
            if isinstance(r, SpecialRoom):
                continue
            chance = 3 if isinstance(r, FissureRoom) else (5 if isinstance(r, ChasmBridgeRoom) else 15)
            for y in range(r.bottom - 1, r.top, -1):
                cell = r.left + 1 + w * y
                for x in range(r.left + 1, r.right):
                    if m[cell] == terrain.CHASM and m[cell - w] == terrain.CHASM:
                        if rng.IntMax(chance) == 0:
                            m[cell] = terrain.REGION_DECO_ALT
                    cell += 1

        # Pass 3: top-row WALL -> WALL_DECO (torches) above EMPTY / EMPTY_SP
        for i in range(w):
            if (m[i] == terrain.WALL
                    and (m[i + w] == terrain.EMPTY or m[i + w] == terrain.EMPTY_SP)
                    and rng.IntMax(6) == 0):
                m[i] = terrain.WALL_DECO

        # Pass 4: interior WALL -> WALL_DECO sandwiched (wall above, floor below)
        for i in range(w, l - w):
            if (m[i] == terrain.WALL
                    and m[i - w] == terrain.WALL
                    and (m[i + w] == terrain.EMPTY or m[i + w] == terrain.EMPTY_SP)
                    and rng.IntMax(3) == 0):
                m[i] = terrain.WALL_DECO
