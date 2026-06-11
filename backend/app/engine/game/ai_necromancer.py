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
from app.engine.entities.base import Position
from app.engine.entities.buffs import add_buff, has_buff
from app.engine.entities.mobs import Necromancer, NecroSkeleton
from app.engine.game.floor_state import FloorState


class NecromancerAIMixin:
    def _update_necromancer(self, necro: Necromancer, floor: FloorState, floor_id: int) -> bool:
        if necro.summoning and necro.ai_state != "hunting":
            necro.summoning = False

        if necro.ai_state != "hunting":
            return False

        target = self._find_nearest_player(necro.pos, floor_id)

        if necro.summoning:
            self._necro_summon_minion(necro, floor, floor_id)
            return True

        skeleton = floor.mobs.get(necro.my_skeleton_id) if necro.my_skeleton_id else None
        if skeleton and (not skeleton.is_alive or skeleton.faction != necro.faction):
            skeleton = None
            necro.my_skeleton_id = ""

        if target is None:
            return False

        enemy_seen = self._is_in_los(necro.pos, target.pos, floor_id=floor_id,
                                       distance=self._view_distance(necro))

        if enemy_seen and self._get_distance(necro.pos, target.pos) <= 4 and skeleton is None:
            best_pos = None
            best_dist = float("inf")
            for dx, dy in _CIRCLE8_OFFSETS:
                nx, ny = target.pos.x + dx, target.pos.y + dy
                if not (0 <= nx < floor.width and 0 <= ny < floor.height):
                    continue
                if not floor.flags or not floor.flags.passable[ny][nx]:
                    continue
                if any(m.is_alive and m.pos.x == nx and m.pos.y == ny for m in floor.mobs.values()):
                    continue
                if any(p.is_alive and p.pos.x == nx and p.pos.y == ny for p in self._players_on_floor(floor_id)):
                    continue
                if not self._is_in_los(necro.pos, Position(x=nx, y=ny), floor_id=floor_id):
                    continue
                d = self._get_distance(necro.pos, Position(x=nx, y=ny))
                if d < best_dist:
                    best_dist = d
                    best_pos = (nx, ny)
            if best_pos:
                necro.summoning = True
                necro.summoning_x, necro.summoning_y = best_pos
                self.add_event("ZAP_SUMMON", {"mob": necro.id, "x": best_pos[0], "y": best_pos[1]}, floor_id=floor_id)
            return True

        if enemy_seen and skeleton is not None:
            if skeleton.hp < skeleton.max_hp:
                heal = skeleton.max_hp // 5
                skeleton.hp = min(skeleton.max_hp, skeleton.hp + heal)
                self.add_event("HEAL", {"target": skeleton.id, "amount": heal,
                                          "x": skeleton.pos.x, "y": skeleton.pos.y}, floor_id=floor_id)
                self.add_event("ZAP_SUMMON", {"mob": necro.id, "x": skeleton.pos.x, "y": skeleton.pos.y}, floor_id=floor_id)
                self.add_event("PLAY_SOUND", {"sound": "RAY"}, floor_id=floor_id)
            elif not has_buff(skeleton.buffs, "adrenaline"):
                skeleton.add_buff("adrenaline", 3.0)
                self.add_event("ZAP_SUMMON", {"mob": necro.id, "x": skeleton.pos.x, "y": skeleton.pos.y}, floor_id=floor_id)
                self.add_event("PLAY_SOUND", {"sound": "RAY"}, floor_id=floor_id)
            return True

        return False

    def _necro_summon_minion(self, necro: Necromancer, floor: FloorState, floor_id: int) -> None:
        x, y = necro.summoning_x, necro.summoning_y

        occupied_by = None
        for m in floor.mobs.values():
            if m.is_alive and m.id != necro.id and m.pos.x == x and m.pos.y == y:
                occupied_by = m
        if occupied_by is None:
            for p in self._players_on_floor(floor_id):
                if p.is_alive and p.pos.x == x and p.pos.y == y:
                    occupied_by = p

        impassable = not floor.flags or not floor.flags.passable[y][x]

        if occupied_by is not None or impassable:
            best = None
            best_dist = -1
            for dx, dy in _CIRCLE8_OFFSETS:
                nx, ny = x + dx, y + dy
                if not (0 <= nx < floor.width and 0 <= ny < floor.height):
                    continue
                if not floor.flags or not floor.flags.passable[ny][nx]:
                    continue
                if any(m.is_alive and m.pos.x == nx and m.pos.y == ny for m in floor.mobs.values()):
                    continue
                if any(p.is_alive and p.pos.x == nx and p.pos.y == ny for p in self._players_on_floor(floor_id)):
                    continue
                d = self._get_distance(necro.pos, Position(x=nx, y=ny))
                if d > best_dist:
                    best_dist = d
                    best = (nx, ny)
            if best:
                necro.summoning_x, necro.summoning_y = best
                x, y = best
            else:
                if occupied_by is not None and getattr(occupied_by, "faction", None) != necro.faction:
                    dmg = random.randint(2, 10)
                    taken = occupied_by.take_damage(dmg)
                    if taken > 0:
                        self.add_event("DAMAGE", {"target": occupied_by.id, "amount": taken}, floor_id=floor_id)
                return

        necro.summoning = False
        necro.first_summon = False

        skeleton = floor.mobs.get(necro.my_skeleton_id) if necro.my_skeleton_id else None
        if skeleton is None or not skeleton.is_alive:
            new_skel = self._spawn_mob_at(NecroSkeleton, x, y)
            new_skel.faction = necro.faction
            floor.mobs[new_skel.id] = new_skel
            necro.my_skeleton_id = new_skel.id
            self.add_event("NECRO_SUMMON", {"necromancer": necro.id, "skeleton": new_skel.id, "x": x, "y": y}, floor_id=floor_id)
        else:
            skeleton.pos = Position(x=x, y=y)
            self.add_event("NECRO_SUMMON", {"necromancer": necro.id, "skeleton": skeleton.id, "x": x, "y": y}, floor_id=floor_id)
