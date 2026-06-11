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
"""Port of com.shatteredpixel.shatteredpixeldungeon.levels.painters.CityPainter.

CityPainter uses Dungeon.depth in Java (global state). In Python we take depth
at construction time and store it as an instance attribute.
"""

from __future__ import annotations

from typing import List

from app.engine.dungeon.spd_levelgen import terrain
from app.engine.dungeon.spd_levelgen.level import GenLevel
from app.engine.dungeon.spd_levelgen.regular_painter import RegularPainter
from app.engine.dungeon.spd_levelgen.room import Room
from app.engine.dungeon.spd_random import SPDRandom

# Tiles that count as wall for stitching purposes (DungeonTileSheet.wallStitcheable)
_WALL_STITCHEABLE = frozenset({
    terrain.WALL, terrain.WALL_DECO, terrain.SECRET_DOOR,
    terrain.LOCKED_EXIT, terrain.UNLOCKED_EXIT, terrain.BOOKSHELF,
})


class CityPainter(RegularPainter):

    def __init__(self, depth: int) -> None:
        super().__init__()
        self.depth = depth

    def decorate(self, rng: SPDRandom, level: GenLevel, rooms: List[Room]) -> None:
        m = level.map
        w = level.width()
        l = level.length()

        for i in range(l - w):
            if m[i] == terrain.EMPTY and rng.IntMax(10) == 0:
                m[i] = terrain.EMPTY_DECO
            elif m[i] == terrain.WALL and m[i + w] not in _WALL_STITCHEABLE:
                if rng.IntMax(21 - self.depth) == 0:
                    m[i] = terrain.WALL_DECO
