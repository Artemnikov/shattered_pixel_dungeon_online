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
from typing import Optional

from app.engine.dungeon.spd_levelgen.level import _CIRCLE8_OFFSETS
from app.engine.entities.base import Position
from app.engine.entities.mobs import Pylon
from app.engine.game.floor_state import FloorState


class PylonAIMixin:
    def _update_pylon(self, pylon: Pylon, floor: FloorState, floor_id: int):
        if not pylon.activated:
            return

        pylon.bolt_cooldown -= 1
        if pylon.bolt_cooldown > 0:
            return

        idx_a = pylon.fire_target_idx
        idx_b = (pylon.fire_target_idx + 4) % 8
        shock_cells = []
        for idx in (idx_a, idx_b):
            ox, oy = _CIRCLE8_OFFSETS[idx]
            shock_cells.append((pylon.pos.x + ox, pylon.pos.y + oy))

        for cx, cy in shock_cells:
            for p in self._players_on_floor(floor_id):
                if p.is_alive and p.pos.x == cx and p.pos.y == cy:
                    dmg = random.randint(10, 20)
                    taken = p.take_damage(dmg)
                    self.add_event("ATTACK", {"source": pylon.id, "target": p.id,
                                              "damage": taken, "surprise": False},
                                   floor_id=floor_id)
                    if taken > 0:
                        self.add_event("DAMAGE", {"target": p.id, "amount": taken}, floor_id=floor_id)
            for m in floor.mobs.values():
                if m.is_alive and m.id != pylon.id and m.pos.x == cx and m.pos.y == cy:
                    dmg = random.randint(10, 20)
                    taken = m.take_damage(dmg)
                    self.add_event("ATTACK", {"source": pylon.id, "target": m.id,
                                              "damage": taken, "surprise": False},
                                   floor_id=floor_id)
                    if taken > 0:
                        self.add_event("DAMAGE", {"target": m.id, "amount": taken}, floor_id=floor_id)

        pylon.fire_target_idx = (pylon.fire_target_idx + 1) % 8
        pylon.bolt_cooldown = 1

    def _activate_pylon(self, floor: FloorState, floor_id: int, near_pos: Optional[Position] = None):
        candidates = [m for m in floor.mobs.values() if isinstance(m, Pylon) and not m.activated]
        if not candidates:
            return

        if len(candidates) > 1 and near_pos is not None:
            closest = min(candidates, key=lambda p: self._get_distance(p.pos, near_pos))
            pool = [p for p in candidates if p.id != closest.id]
        else:
            pool = candidates

        chosen = random.choice(pool) if pool else candidates[0]
        chosen.activated = True
        self.add_event("PYLON_ACTIVATED", {"mob": chosen.id}, floor_id=floor_id)
