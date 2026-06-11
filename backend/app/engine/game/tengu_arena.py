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
"""Floor 10 (PrisonBossLevel / Tengu) state machine -- port of
PrisonBossLevel.java's `progress()`/`occupyCell()` transitions:
START -> FIGHT_START -> FIGHT_PAUSE -> FIGHT_ARENA -> WON.

Each transition rebuilds `floor.grid` from the hardcoded
`prison_boss_layout` variants and bumps `floor.map_version` so clients
re-fetch a fresh INIT for the floor (see `main.py`)."""

from __future__ import annotations

import uuid
from typing import List, Optional, Tuple

from app.engine.dungeon.constants import TrapType
from app.engine.dungeon.generator import TileType, TrapInfo
from app.engine.dungeon.spd_levelgen import patch
from app.engine.dungeon.spd_levelgen import prison_boss_layout as layout
from app.engine.dungeon.spd_levelgen.geom import Point
from app.engine.dungeon.spd_random import SPDRandom
from app.engine.entities.base import Faction, Position
from app.engine.entities.mobs import Tengu
from app.engine.game.floor_state import FloorState
from app.engine.game.spd_adapter import _convert_tile

PRISON_BOSS_FLOOR = 10

_NEIGHBOURS8 = (
    (-1, -1), (0, -1), (1, -1),
    (-1, 0), (1, 0),
    (-1, 1), (0, 1), (1, 1),
)


def _grid_from_level(level) -> List[List[int]]:
    w, h = level.width(), level.height()
    return [[_convert_tile(level.map[y * w + x]) for x in range(w)] for y in range(h)]


class PrisonBossMixin:
    def _update_prison_boss(self, floor: FloorState, floor_id: int) -> None:
        if floor_id != PRISON_BOSS_FLOOR:
            return

        state = floor.tengu_state
        if state == "START":
            self._prison_boss_start_to_fight_start(floor, floor_id)
        elif state == "FIGHT_START":
            self._prison_boss_fight_start_to_pause(floor, floor_id)
        elif state == "FIGHT_PAUSE":
            self._prison_boss_pause_to_arena(floor, floor_id)
        elif state == "FIGHT_ARENA":
            self._prison_boss_arena_to_won(floor, floor_id)

    # -- helpers ----------------------------------------------------------

    def _find_tengu(self, floor: FloorState) -> Optional[Tengu]:
        for mob in floor.mobs.values():
            if isinstance(mob, Tengu):
                return mob
        return None

    def _cell_occupied(self, floor: FloorState, floor_id: int, x: int, y: int) -> bool:
        if any(m.is_alive and m.pos.x == x and m.pos.y == y for m in floor.mobs.values()):
            return True
        if any(p.is_alive and p.pos.x == x and p.pos.y == y for p in self._players_on_floor(floor_id)):
            return True
        return False

    def _clear_entities_outside(self, floor: FloorState, floor_id: int, safe_area,
                                 keep_mob_id: Optional[str] = None) -> None:
        """Port of clearEntities(): destroys items/mobs outside `safe_area`,
        stashing dropped items in `prison_stored_items`."""
        for item_id, item in list(floor.items.items()):
            if not safe_area.inside(Point(item.pos.x, item.pos.y)):
                floor.prison_stored_items.append(item)
                del floor.items[item_id]

        for mob_id, mob in list(floor.mobs.items()):
            if mob_id == keep_mob_id:
                continue
            if not safe_area.inside(Point(mob.pos.x, mob.pos.y)):
                del floor.mobs[mob_id]

    def _place_traps_in_tengu_cell(self, floor: FloorState, floor_id: int,
                                    tengu: Tengu, fill: float = 0.65) -> None:
        """Simplified port of placeTrapsInTenguCell(): scatters hidden dart
        traps inside TENGU_CELL via a 7x7 cellular-automaton patch
        (Patch.generate). The original retries until the patch sits a
        specific pathfinder-distance band from the hero; that distance-map
        machinery isn't ported, so this just rerolls a bounded number of
        times and skips Tengu's/the target's own cell."""
        rng = SPDRandom()
        cell = layout.TENGU_CELL
        inner_left, inner_top = cell.left + 1, cell.top + 1
        target = self._find_nearest_player(tengu.pos, floor_id)

        # cleanTenguCell(): clear any traps already in the cell before
        # scattering a new patch (Tengu re-rolls traps on every jump).
        cleared = []
        for (tx, ty), trap in list(floor.traps.items()):
            if cell.left < tx < cell.right - 1 and cell.top < ty < cell.bottom - 1:
                del floor.traps[(tx, ty)]
                if floor.grid[ty][tx] in (TileType.SECRET_TRAP, TileType.TRAP):
                    floor.grid[ty][tx] = TileType.FLOOR
                    cleared.append({"x": tx, "y": ty, "tile": TileType.FLOOR})

        trap_cells: List[Tuple[int, int]] = []
        for _ in range(20):
            patch_bits = patch.generate(rng, 7, 7, fill, 0, False)
            trap_cells = []
            for i, bit in enumerate(patch_bits):
                if not bit:
                    continue
                x = inner_left + i % 7
                y = inner_top + i // 7
                if x == tengu.pos.x and y == tengu.pos.y:
                    continue
                if target is not None and x == target.pos.x and y == target.pos.y:
                    continue
                trap_cells.append((x, y))
            if trap_cells:
                break

        patches = list(cleared)
        for x, y in trap_cells:
            floor.traps[(x, y)] = TrapInfo(x=x, y=y, trap_type=TrapType.TENGU_DART, hidden=True)
            floor.grid[y][x] = TileType.SECRET_TRAP
            patches.append({"x": x, "y": y, "tile": TileType.SECRET_TRAP})

        if patches:
            floor.rebuild_flags()
            self.add_event("MAP_PATCH", {"tiles": patches}, floor_id=floor_id)

    # -- transitions --------------------------------------------------------

    def _prison_boss_start_to_fight_start(self, floor: FloorState, floor_id: int) -> None:
        if not any(p.is_alive and p.pos.y > layout.TENGU_CELL.top
                   for p in self._players_on_floor(floor_id)):
            return

        cx, cy = layout.TENGU_CELL_CENTER.x, layout.TENGU_CELL_CENTER.y
        if self._cell_occupied(floor, floor_id, cx, cy):
            candidates = []
            for dx, dy in _NEIGHBOURS8:
                nx, ny = cx + dx, cy + dy
                if not self._cell_occupied(floor, floor_id, nx, ny):
                    candidates.append((nx, ny))
            if not candidates:
                return  # mirrors Java: nothing free, wait and try again next tick
            cx, cy = candidates[0]

        # Seal the cell behind Tengu.
        dx, dy = layout.TENGU_CELL_DOOR.x, layout.TENGU_CELL_DOOR.y
        floor.grid[dy][dx] = TileType.LOCKED_DOOR
        floor.rebuild_flags()
        self.add_event("MAP_PATCH", {"tiles": [{"x": dx, "y": dy, "tile": TileType.LOCKED_DOOR}]}, floor_id=floor_id)

        tengu = Tengu(id=str(uuid.uuid4()), pos=Position(x=cx, y=cy), faction=Faction.DUNGEON)
        tengu.ai_state = "hunting"
        tengu.fight_started = True
        floor.mobs[tengu.id] = tengu

        self.add_event("TENGU_FIGHT_STARTED", {"mob": tengu.id}, floor_id=floor_id)
        self.add_event("PLAY_SOUND", {"sound": "PUFF"}, floor_id=floor_id)

        # SPD: entering boss fight resets badge eligibility
        self.qualified_for_boss_challenge = True

        self._place_traps_in_tengu_cell(floor, floor_id, tengu)

        floor.tengu_state = "FIGHT_START"

    def _prison_boss_fight_start_to_pause(self, floor: FloorState, floor_id: int) -> None:
        tengu = self._find_tengu(floor)
        if tengu is None or not tengu.is_alive or not tengu.is_enraged():
            return

        self._clear_entities_outside(floor, floor_id, layout.TENGU_CELL, keep_mob_id=tengu.id)

        rng = SPDRandom()
        level = layout._new_level(PRISON_BOSS_FLOOR)
        layout.apply_pause_patch(level, rng)
        floor.grid = _grid_from_level(level)
        floor.traps.clear()
        floor.rebuild_flags()
        floor.map_version += 1

        # Tengu leaves the world during FIGHT_PAUSE; restored in FIGHT_ARENA.
        del floor.mobs[tengu.id]
        floor.generation_meta["tengu_pending"] = tengu

        self.add_event("PLAY_SOUND", {"sound": "BLAST"}, floor_id=floor_id)
        floor.tengu_state = "FIGHT_PAUSE"

    def _prison_boss_pause_to_arena(self, floor: FloorState, floor_id: int) -> None:
        if not any(p.is_alive and p.pos.y <= layout.START_HALLWAY.top + 1
                   for p in self._players_on_floor(floor_id)):
            return

        self._clear_entities_outside(floor, floor_id, layout.PAUSE_SAFE_AREA)

        level = layout._new_level(PRISON_BOSS_FLOOR)
        layout.build_arena_grid(level)
        floor.grid = _grid_from_level(level)
        floor.rebuild_flags()
        floor.map_version += 1

        tengu = floor.generation_meta.pop("tengu_pending", None)
        if tengu is None:
            tengu = Tengu(id=str(uuid.uuid4()), faction=Faction.DUNGEON)
        tengu.pos = Position(x=layout.ARENA.left + layout.ARENA.width() // 2, y=layout.ARENA.top + 2)
        tengu.ai_state = "hunting"
        floor.mobs[tengu.id] = tengu

        self.add_event("PLAY_SOUND", {"sound": "BLAST"}, floor_id=floor_id)
        floor.tengu_state = "FIGHT_ARENA"

    def _prison_boss_arena_to_won(self, floor: FloorState, floor_id: int) -> None:
        if self._find_tengu(floor) is not None:
            return  # Tengu still alive

        for p in self._players_on_floor(floor_id):
            p.pos.x, p.pos.y = layout.TENGU_CELL.left + 4, layout.TENGU_CELL.top + 2

        rng = SPDRandom()
        level = layout._new_level(PRISON_BOSS_FLOOR)
        layout.apply_end_patch(level, rng)
        floor.grid = _grid_from_level(level)
        floor.rebuild_flags()
        floor.map_version += 1

        for item in floor.prison_stored_items:
            cell = layout.random_tengu_cell_pos(rng, level)
            item.pos.x, item.pos.y = cell % level.width(), cell // level.width()
            floor.items[item.id] = item
        floor.prison_stored_items = []

        self.add_event("PLAY_SOUND", {"sound": "BLAST"}, floor_id=floor_id)
        floor.tengu_state = "WON"
