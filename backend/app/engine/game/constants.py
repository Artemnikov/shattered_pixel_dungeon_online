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

# Respawn timer: 50 turns (ticks) base
RESPAWN_TURNS = 50
# No respawns on floor 1
NO_RESPAWN_FLOORS = {1}

# Canvas seed size handed to the generator. The v2 generator resizes its canvas
# to fit the room layout, so each floor ends up a different size; these are only
# the starting bounds. Per-floor dimensions live on FloorState.width/height.
MAP_WIDTH = 60
MAP_HEIGHT = 40
