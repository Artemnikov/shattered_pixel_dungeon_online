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
"""Port of com.shatteredpixel.shatteredpixeldungeon.levels.painters.SewerPainter
-- the `decorate()` override that stamps WALL_DECO near water and EMPTY_DECO
near walls."""

from __future__ import annotations

from typing import List

from app.engine.dungeon.spd_levelgen import terrain
from app.engine.dungeon.spd_levelgen.level import GenLevel
from app.engine.dungeon.spd_levelgen.regular_painter import RegularPainter
from app.engine.dungeon.spd_levelgen.room import Room
from app.engine.dungeon.spd_random import SPDRandom


class SewerPainter(RegularPainter):

    def decorate(self, rng: SPDRandom, level: GenLevel, rooms: List[Room]) -> None:
        m = level.map
        w = level.width()
        length = level.length()

        for i in range(w):
            if (m[i] == terrain.WALL
                    and m[i + w] == terrain.WATER
                    and rng.IntMax(4) == 0):
                m[i] = terrain.WALL_DECO

        for i in range(w, length - w):
            if (m[i] == terrain.WALL
                    and m[i - w] == terrain.WALL
                    and m[i + w] == terrain.WATER
                    and rng.IntMax(2) == 0):
                m[i] = terrain.WALL_DECO

        for i in range(w + 1, length - w - 1):
            if m[i] == terrain.EMPTY:
                count = (
                    (1 if m[i + 1] == terrain.WALL else 0)
                    + (1 if m[i - 1] == terrain.WALL else 0)
                    + (1 if m[i + w] == terrain.WALL else 0)
                    + (1 if m[i - w] == terrain.WALL else 0)
                )
                if rng.IntMax(16) < count * count:
                    m[i] = terrain.EMPTY_DECO
