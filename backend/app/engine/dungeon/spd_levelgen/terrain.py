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
"""Port of com.shatteredpixel.shatteredpixeldungeon.levels.Terrain (tile id constants).

Only the constants needed by the level-gen port are listed here; flags/behaviour
tables are not needed for layout/paint transliteration (the remake's renderer
uses its own tile id space -- conversion happens at the integration boundary).
"""

CHASM = 0
EMPTY = 1
GRASS = 2
EMPTY_WELL = 3
WALL = 4
DOOR = 5
OPEN_DOOR = 6
ENTRANCE = 7
ENTRANCE_SP = 37
EXIT = 8
EMBERS = 9
LOCKED_DOOR = 10
HERO_LKD_DR = 38
CRYSTAL_DOOR = 31
PEDESTAL = 11
WALL_DECO = 12
BARRICADE = 13
EMPTY_SP = 14
HIGH_GRASS = 15
FURROWED_GRASS = 30

SECRET_DOOR = 16
SECRET_TRAP = 17
TRAP = 18
INACTIVE_TRAP = 19

EMPTY_DECO = 20
LOCKED_EXIT = 21
UNLOCKED_EXIT = 22
WELL = 24
BOOKSHELF = 27
ALCHEMY = 28

CUSTOM_DECO_EMPTY = 32
CUSTOM_DECO = 23
STATUE = 25
STATUE_SP = 26
REGION_DECO = 33
REGION_DECO_ALT = 34
MINE_CRYSTAL = 35
MINE_BOULDER = 36

WATER = 29

# Terrain.flags[...] & Terrain.PASSABLE != 0 -- ids reachable at paint-time on
# a regular (sewers) level whose flags carry the PASSABLE (0x01) bit.
PASSABLE: frozenset = frozenset({
    EMPTY, GRASS, EMPTY_WELL, WATER, DOOR, OPEN_DOOR, ENTRANCE, ENTRANCE_SP,
    EXIT, EMBERS, PEDESTAL, EMPTY_SP, HIGH_GRASS, FURROWED_GRASS, SECRET_TRAP,
    INACTIVE_TRAP, EMPTY_DECO, UNLOCKED_EXIT, CUSTOM_DECO_EMPTY,
})

# Terrain.flags[...] & Terrain.SOLID != 0
SOLID: frozenset = frozenset({
    WALL, DOOR, LOCKED_DOOR, HERO_LKD_DR, CRYSTAL_DOOR, WALL_DECO, BARRICADE,
    LOCKED_EXIT, BOOKSHELF, ALCHEMY, CUSTOM_DECO, STATUE, STATUE_SP,
    REGION_DECO, REGION_DECO_ALT, MINE_CRYSTAL, MINE_BOULDER,
})

# Terrain.flags[...] & Terrain.LOS_BLOCKING != 0
LOS_BLOCKING: frozenset = frozenset({
    WALL, DOOR, LOCKED_DOOR, HERO_LKD_DR, BARRICADE, WALL_DECO,
    HIGH_GRASS, FURROWED_GRASS, SECRET_DOOR,
})
