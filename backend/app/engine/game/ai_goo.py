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
import time

from app.engine.dungeon.generator import TileType
from app.engine.entities.base import Position
from app.engine.entities.mobs import Goo
from app.engine.game.constants import GOO_WATER_HEAL_INTERVAL
from app.engine.game.floor_state import FloorState


class GooAIMixin:
    def _update_goo(self, goo: Goo, floor: FloorState, floor_id: int) -> bool:
        self._goo_sync_enrage(goo, floor_id)
        self._goo_water_heal(goo, floor, floor_id)

        target = self._find_nearest_player(goo.pos, floor_id)
        if target is None:
            self._goo_cancel_charge(goo, floor_id)
            return False

        dist = self._get_distance(goo.pos, target.pos)
        charge_ok = dist <= 2 and self._is_in_los(goo.pos, target.pos, floor_id=floor_id)
        now = time.time()

        if goo.pumped_up >= 1:
            if not charge_ok:
                self._goo_cancel_charge(goo, floor_id)
                return False
            if now - goo.last_attack_time >= goo.attack_cooldown:
                goo.last_attack_time = now
                goo.pumped_up += 1
                if goo.pumped_up >= 2:
                    self._goo_release_charge(goo, target, floor_id)
                    goo.pumped_up = 0
            return True

        if charge_ok and now - goo.last_attack_time >= goo.attack_cooldown:
            odds = 2 if goo.is_enraged() else 5
            if random.randint(0, odds - 1) == 0:
                goo.last_attack_time = now
                goo.pumped_up = 2 if "stronger_bosses" in self.challenges else 1
                self._goo_begin_charge(goo, target, floor_id)
                return True
        return False

    def _goo_sync_enrage(self, goo: Goo, floor_id: int):
        enraged = goo.is_enraged()
        goo.attack_skill = 15 if enraged else 10
        if enraged and not goo.enraged_announced:
            goo.enraged_announced = True
            self.add_event("GOO_ENRAGE", {"mob": goo.id}, floor_id=floor_id)

    def _goo_water_heal(self, goo: Goo, floor: FloorState, floor_id: int):
        if goo.flying or goo.hp >= goo.max_hp:
            goo.heal_cooldown = 0
            return
        if floor.grid[goo.pos.y][goo.pos.x] != TileType.FLOOR_WATER:
            goo.heal_cooldown = 0
            return
        if goo.heal_cooldown > 0:
            goo.heal_cooldown -= 1
            return
        goo.hp = min(goo.max_hp, goo.hp + goo.heal_inc)
        goo.heal_cooldown = GOO_WATER_HEAL_INTERVAL
        self.add_event("HEAL", {"target": goo.id, "amount": goo.heal_inc,
                                "x": goo.pos.x, "y": goo.pos.y}, floor_id=floor_id)
        if "stronger_bosses" in self.challenges:
            goo.heal_inc = min(3, goo.heal_inc + 1)

    def _goo_threatened_tiles(self, goo: Goo, floor_id: int):
        tiles = []
        radius = max(1, goo.pumped_up)
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                if dx == 0 and dy == 0:
                    continue
                if abs(dx) + abs(dy) > radius:
                    continue
                x, y = goo.pos.x + dx, goo.pos.y + dy
                if self._is_in_los(goo.pos, Position(x=x, y=y), floor_id=floor_id):
                    tiles.append([x, y])
        return tiles

    def _goo_begin_charge(self, goo: Goo, target, floor_id: int):
        tiles = self._goo_threatened_tiles(goo, floor_id)
        self.add_event("GOO_CHARGE", {"mob": goo.id, "tiles": tiles,
                                      "duration_ms": int(goo.attack_cooldown * 1000)},
                       floor_id=floor_id)
        self.add_event("PLAY_SOUND", {"sound": "CHARGEUP"}, floor_id=floor_id)

    def _goo_cancel_charge(self, goo: Goo, floor_id: int):
        if goo.pumped_up > 0:
            goo.pumped_up = 0
            self.add_event("GOO_CHARGE", {"mob": goo.id, "tiles": []}, floor_id=floor_id)

    def _goo_release_charge(self, goo: Goo, target, floor_id: int):
        self.add_event("GOO_CHARGE", {"mob": goo.id, "tiles": []}, floor_id=floor_id)
        acu = random.random() * goo.attack_skill * 2
        df = random.random() * target.get_effective_defense_skill()
        if acu < df:
            self.add_event("ATTACK", {"source": goo.id, "target": target.id,
                                      "damage": 0, "surprise": False}, floor_id=floor_id)
            self.add_event("MISS", {"source": goo.id, "target": target.id,
                                    "defense_verb": target.defense_verb}, floor_id=floor_id)
            return
        dmg_roll = random.randint(goo.get_damage_min() * 3, goo.get_damage_max() * 3)
        dr = random.randint(target.get_dr_min(), target.get_dr_max())
        dmg = target.take_damage(max(0, dmg_roll - dr))
        self.add_event("ATTACK", {"source": goo.id, "target": target.id,
                                  "damage": dmg, "surprise": False, "pumped": True}, floor_id=floor_id)
        self.add_event("SCREEN_SHAKE", {"intensity": 3, "duration_ms": 200}, floor_id=floor_id)
        self.add_event("PLAY_SOUND", {"sound": "BURNING"}, floor_id=floor_id)
        if dmg > 0:
            self.add_event("DAMAGE", {"target": target.id, "amount": dmg}, floor_id=floor_id)
            self.add_event("PLAY_SOUND", {"sound": "HIT_BODY"}, floor_id=floor_id, source_player_id=target.id)
            goo.attack_proc(target)
