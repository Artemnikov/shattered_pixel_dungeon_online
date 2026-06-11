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

import random

from app.engine.dungeon.spd_levelgen.level import _CIRCLE8_OFFSETS
from app.engine.entities.mobs import DemonSpawner, RipperDemon
from app.engine.game.floor_state import FloorState


class DemonSpawnerAIMixin:
    def _update_demon_spawner(self, spawner: DemonSpawner, floor: FloorState, floor_id: int):
        spawner.spawn_cooldown -= 1
        if spawner.spawn_cooldown > 0:
            return

        if spawner.spawn_cooldown < -20:
            spawner.spawn_cooldown = -20

        candidates = []
        for dx, dy in _CIRCLE8_OFFSETS:
            nx, ny = spawner.pos.x + dx, spawner.pos.y + dy
            if not (0 <= nx < floor.width and 0 <= ny < floor.height):
                continue
            if not floor.flags or not floor.flags.passable[ny][nx]:
                continue
            occupied = any(m.is_alive and m.pos.x == nx and m.pos.y == ny for m in floor.mobs.values())
            occupied = occupied or any(p.is_alive and p.pos.x == nx and p.pos.y == ny for p in self._players_on_floor(floor_id))
            if not occupied:
                candidates.append((nx, ny))

        if candidates:
            sx, sy = random.choice(candidates)
            new_mob = self._spawn_mob_at(RipperDemon, sx, sy)
            new_mob.ai_state = "hunting"
            floor.mobs[new_mob.id] = new_mob
            self.add_event("MOB_SPAWN", {"mob": new_mob.id, "cls": "RipperDemon"}, floor_id=floor_id)

            spawner.spawn_cooldown += 60
            if floor.floor_id > 21:
                spawner.spawn_cooldown -= min(20, int((floor.floor_id - 21) * 6.67))
