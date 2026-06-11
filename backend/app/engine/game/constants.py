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
"""Module-level gameplay constants for the game engine.

Extracted from manager.py so the per-concern mixin modules can import them
without pulling in the whole GameInstance. manager.py re-exports these for
backward-compatible imports.
"""

MAX_FLOOR_ID = 50
SEWERS_MAX_FLOOR = 4
PRISON_MAX_FLOOR = 9

AUTO_MOVE_INTERVAL = 0.15

HEAL_TICK_INTERVAL = 20
ROOM_HEAL_AMOUNT = 10
PASSIVE_REGEN_INTERVAL = 10

# Caustic ooze (SPD Ooze): DURATION=20 turns, ~1 dmg/turn vs the depth-5 Goo,
# washed off by stepping into water. Ticks are throttled so the real-time loop
# applies roughly one point of damage per in-game "turn".
OOZE_DURATION = 20
OOZE_TICK_INTERVAL = 20  # ticks (~1s at 20Hz) between ooze damage applications

# Goo water-heal cadence: ticks between each +heal_inc while standing in water.
GOO_WATER_HEAL_INTERVAL = 20

# Respawn timer: 50 turns (ticks) base
RESPAWN_TURNS = 50
# No respawns on floor 1
NO_RESPAWN_FLOORS = {1}

# Canvas seed size handed to the generator. The v2 generator resizes its canvas
# to fit the room layout, so each floor ends up a different size; these are only
# the starting bounds. Per-floor dimensions live on FloorState.width/height.
MAP_WIDTH = 60
MAP_HEIGHT = 40
