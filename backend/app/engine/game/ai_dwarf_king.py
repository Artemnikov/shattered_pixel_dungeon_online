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

from app.engine.entities.mobs import DKGhoul, DKMonk, DKWarlock, DwarfKing
from app.engine.game.floor_state import FloorState


class DwarfKingAIMixin:
    def _update_dwarf_king(self, dk: DwarfKing, floor: FloorState, floor_id: int):
        if not dk.fight_started:
            target = self._find_nearest_player(dk.pos, floor_id)
            if target is not None:
                dk.fight_started = True
                self.add_event("DWARF_KING_FIGHT_STARTED", {"mob": dk.id}, floor_id=floor_id)
            return

        if dk.phase == 1 and dk.hp <= 200:
            dk.phase = 2
            if "IMMOVABLE" not in dk.properties:
                dk.properties.append("IMMOVABLE")
            self.add_event("DWARF_KING_PHASE2", {"mob": dk.id}, floor_id=floor_id)

        if dk.phase == 2 and dk.hp <= 100:
            dk.phase = 3
            self.add_event("DWARF_KING_PHASE3", {"mob": dk.id}, floor_id=floor_id)

        if dk.summon_cooldown > 0:
            dk.summon_cooldown -= 1
            return

        if dk.summons_made % 4 == 3:
            cls = DKMonk if random.randint(0, 1) == 0 else DKWarlock
        else:
            cls = DKGhoul

        summon_spots = floor.dk_summon_spots
        first_mob = None
        for spot in summon_spots:
            sx, sy = spot
            occupied = any(m.is_alive and m.pos.x == sx and m.pos.y == sy
                           for m in floor.mobs.values())
            if not occupied:
                new_mob = self._spawn_mob_at(cls, sx, sy)
                floor.mobs[new_mob.id] = new_mob
                dk.summons_made += 1
                first_mob = new_mob
                break

        if first_mob is None:
            return

        if cls == DKGhoul:
            for spot in summon_spots:
                sx, sy = spot
                occupied = any(m.is_alive and m.pos.x == sx and m.pos.y == sy
                               for m in floor.mobs.values())
                if not occupied:
                    second_mob = self._spawn_mob_at(DKGhoul, sx, sy)
                    floor.mobs[second_mob.id] = second_mob
                    first_mob.linked_ghoul_id = second_mob.id
                    second_mob.linked_ghoul_id = first_mob.id
                    break

        if dk.phase == 3:
            dk.summon_cooldown = random.randint(3, 5)
        else:
            dk.summon_cooldown = random.randint(10, 14)
