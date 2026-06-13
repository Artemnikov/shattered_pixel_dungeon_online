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

from app.engine.dungeon.generator import TileType
from app.engine.dungeon.spd_levelgen.level import _CIRCLE8_OFFSETS
from app.engine.entities.base import Position
from app.engine.entities.buffs import add_buff
from app.engine.entities.mobs import (
    BrightFist, BurningFist, DarkFist, RottingFist, RustedFist,
    SoiledFist, YogDzewa, YogRipper,
)
from app.engine.game.floor_state import FloorState


def _yog_phase_view_distance(phase: int) -> int:
    """SPD: level.viewDistance during the Yog fight, shrinking each phase
    (phase 1->4, 2->3, 3->2, 4->1, 5->1)."""
    if phase <= 1:
        return 4
    return max(4 - (phase - 1), 1)


class YogDzewaAIMixin:
    def _update_yog_dzewa(self, yog: YogDzewa, floor: FloorState, floor_id: int):
        if not yog.fight_started:
            target = self._find_nearest_player(yog.pos, floor_id)
            if target is not None and self._get_distance(yog.pos, target.pos) <= 12:
                yog.fight_started = True
                yog.phase = 1
                pair_a = random.choice(["BurningFist", "SoiledFist"])
                pair_b = random.choice(["RottingFist", "RustedFist"])
                pair_c = random.choice(["BrightFist", "DarkFist"])
                fist_order = [pair_a, pair_b, pair_c]
                random.shuffle(fist_order)
                yog.fist_order = fist_order
                floor.view_distance = _yog_phase_view_distance(yog.phase)
                self.add_event("YOG_FIGHT_STARTED", {"mob": yog.id}, floor_id=floor_id)
            return

        alive_fists = [m for m in floor.mobs.values()
                       if m.id in yog.fist_ids and m.is_alive]

        HP_FLOORS = {1: 700, 2: 400, 3: 100, 4: 100}

        if yog.phase in (1, 2, 3) and yog.hp <= HP_FLOORS[yog.phase]:
            yog.hp = HP_FLOORS[yog.phase]
            if yog.fist_order:
                next_cls_name = yog.fist_order[0]
                yog.fist_order = yog.fist_order[1:]
                _FIST_CLASSES = {
                    "BurningFist": BurningFist,
                    "SoiledFist": SoiledFist,
                    "RottingFist": RottingFist,
                    "RustedFist": RustedFist,
                    "BrightFist": BrightFist,
                    "DarkFist": DarkFist,
                }
                fist_cls = _FIST_CLASSES.get(next_cls_name, BurningFist)
                new_fist = self._spawn_mob_at(fist_cls, yog.pos.x, yog.pos.y)
                new_fist.yog_id = yog.id
                floor.mobs[new_fist.id] = new_fist
                yog.fist_ids.append(new_fist.id)
                alive_fists.append(new_fist)
                self.add_event("YOG_FIST_SPAWN",
                               {"mob": yog.id, "fist": new_fist.id, "cls": next_cls_name},
                               floor_id=floor_id)
            yog.phase += 1
            floor.view_distance = _yog_phase_view_distance(yog.phase)
            self.add_event("YOG_PHASE_CHANGE", {"mob": yog.id, "phase": yog.phase},
                           floor_id=floor_id)

        if yog.phase == 4 and len(alive_fists) == 0:
            yog.phase = 5
            floor.view_distance = _yog_phase_view_distance(yog.phase)
            self.add_event("YOG_FINAL_PHASE", {"mob": yog.id}, floor_id=floor_id)

        if yog.phase < 5 and yog.hp < HP_FLOORS[yog.phase]:
            yog.hp = HP_FLOORS[yog.phase]

        target = self._find_nearest_player(yog.pos, floor_id)
        if target is None:
            return

        if yog.ability_cooldown > 0:
            yog.ability_cooldown -= 1
        else:
            beams = max(1, 1 + (yog.max_hp - yog.hp) // 400)
            for _ in range(beams):
                acu = random.random() * 999
                df = random.random() * target.get_effective_defense_skill()
                if acu > df:
                    dmg = random.randint(20, 30)
                    taken = target.take_damage(dmg)
                    self.add_event("ATTACK", {"source": yog.id, "target": target.id,
                                              "damage": taken, "surprise": False},
                                   floor_id=floor_id)
            self.add_event("YOG_DEATH_RAY",
                           {"mob": yog.id, "target": target.id, "beams": beams},
                           floor_id=floor_id)
            cooldown = random.randint(10, 15) - (yog.phase - 1)
            yog.ability_cooldown = max(2, cooldown)
            if yog.phase == 5:
                yog.ability_cooldown = min(yog.ability_cooldown, 2)

        if yog.summon_cooldown > 0:
            yog.summon_cooldown -= 1
        else:
            neighbors = [
                (yog.pos.x + dx, yog.pos.y + dy)
                for dx, dy in [(-1, -1), (0, -1), (1, -1), (-1, 0),
                                (1, 0), (-1, 1), (0, 1), (1, 1)]
            ]
            neighbors.sort(key=lambda p: abs(p[0] - target.pos.x) + abs(p[1] - target.pos.y))
            for sx, sy in neighbors:
                if not (0 <= sx < floor.width and 0 <= sy < floor.height):
                    continue
                occupied = any(
                    m.is_alive and m.pos.x == sx and m.pos.y == sy
                    for m in floor.mobs.values()
                )
                if not occupied:
                    minion = self._spawn_mob_at(YogRipper, sx, sy)
                    floor.mobs[minion.id] = minion
                    break

            cooldown = random.randint(10, 15) - (yog.phase - 1)
            if alive_fists:
                cooldown += 10
            yog.summon_cooldown = max(1, cooldown)
            if yog.phase == 5:
                yog.summon_cooldown = min(yog.summon_cooldown, 3)

    def _update_yog_fist(self, fist, floor: FloorState, floor_id: int) -> bool:
        if fist.ranged_cooldown > 0:
            fist.ranged_cooldown -= 1

        if isinstance(fist, RustedFist) and fist.viscosity_stacks > 0:
            released = max(1, fist.viscosity_stacks // 10)
            released = min(released, fist.viscosity_stacks)
            fist.hp = max(0, fist.hp - released)
            fist.viscosity_stacks -= released
            if fist.hp <= 0:
                fist.is_alive = False
                fist.die(floor_mobs=floor.mobs, tile_x=fist.pos.x, tile_y=fist.pos.y,
                         players=self._players_on_floor(floor_id))

        if isinstance(fist, RottingFist) and fist.is_alive:
            if floor.grid[fist.pos.y][fist.pos.x] == TileType.FLOOR_WATER and fist.hp < fist.max_hp:
                fist.hp = min(fist.max_hp, fist.hp + fist.max_hp // 50)

        if isinstance(fist, (BrightFist, DarkFist)) and getattr(fist, "pending_teleport", False):
            self._yog_fist_teleport(fist, floor, floor_id)

        if not fist.is_alive:
            return True

        target = self._find_nearest_player(fist.pos, floor_id)
        if target is None:
            return False

        dist = self._get_distance(fist.pos, target.pos)

        if isinstance(fist, (BrightFist, DarkFist)):
            if self._is_in_los(fist.pos, target.pos, floor_id=floor_id):
                if isinstance(fist, BrightFist):
                    self._fist_zap_bright(fist, target, floor_id)
                else:
                    self._fist_zap_dark(fist, target, floor_id)
                return True
            return False

        if dist > 1 and fist.ranged_cooldown <= 0 and self._is_in_los(fist.pos, target.pos, floor_id=floor_id):
            if isinstance(fist, BurningFist):
                self._fist_zap_burning(fist, target, floor_id)
            elif isinstance(fist, SoiledFist):
                self._fist_zap_soiled(fist, target, floor_id)
            elif isinstance(fist, RottingFist):
                self._fist_zap_rotting(fist, target, floor_id)
            elif isinstance(fist, RustedFist):
                self._fist_zap_rusted(fist, target, floor_id)
            fist.ranged_cooldown = random.uniform(8, 12)
            return True

        return False

    def _yog_fist_teleport(self, fist, floor: FloorState, floor_id: int):
        floor_tiles = [
            (x, y) for y in range(floor.height) for x in range(floor.width)
            if floor.grid[y][x] in [TileType.FLOOR, TileType.FLOOR_WOOD, TileType.FLOOR_WATER,
                                     TileType.FLOOR_COBBLE, TileType.FLOOR_GRASS]
            and not any(m.is_alive and m.pos.x == x and m.pos.y == y for m in floor.mobs.values())
            and not any(p.is_alive and p.pos.x == x and p.pos.y == y for p in self._players_on_floor(floor_id))
        ]
        if floor_tiles:
            x, y = random.choice(floor_tiles)
            fist.pos = Position(x=x, y=y)
            fist.ai_state = "wandering"

            target = self._find_nearest_player(fist.pos, floor_id)
            if target is not None:
                add_buff(target.buffs, "blindness", duration=15.0, level=2, stack_mode="extend")

            self.add_event("FIST_TELEPORT", {"mob": fist.id, "x": x, "y": y}, floor_id=floor_id)

        fist.pending_teleport = False

    def _fist_zap_burning(self, fist, target, floor_id: int):
        acu = random.random() * fist.attack_skill
        df = random.random() * target.get_effective_defense_skill()
        if acu < df:
            self.add_event("ATTACK", {"source": fist.id, "target": target.id,
                                      "damage": 0, "surprise": False, "fire": True}, floor_id=floor_id)
            self.add_event("MISS", {"source": fist.id, "target": target.id,
                                    "defense_verb": target.defense_verb}, floor_id=floor_id)
            return
        dmg = target.take_damage(random.randint(8, 16))
        add_buff(target.buffs, "burning", duration=3.0, level=1, stack_mode="extend")
        self.add_event("ATTACK", {"source": fist.id, "target": target.id,
                                  "damage": dmg, "surprise": False, "fire": True}, floor_id=floor_id)
        if dmg > 0:
            self.add_event("DAMAGE", {"target": target.id, "amount": dmg}, floor_id=floor_id)

    def _fist_zap_soiled(self, fist, target, floor_id: int):
        acu = random.random() * fist.attack_skill
        df = random.random() * target.get_effective_defense_skill()
        if acu < df:
            self.add_event("ATTACK", {"source": fist.id, "target": target.id,
                                      "damage": 0, "surprise": False}, floor_id=floor_id)
            self.add_event("MISS", {"source": fist.id, "target": target.id,
                                    "defense_verb": target.defense_verb}, floor_id=floor_id)
            return
        add_buff(target.buffs, "rooted", duration=3.0, level=1)
        self.add_event("ATTACK", {"source": fist.id, "target": target.id,
                                  "damage": 0, "surprise": False, "root": True}, floor_id=floor_id)

    def _fist_zap_rotting(self, fist, target, floor_id: int):
        acu = random.random() * fist.attack_skill
        df = random.random() * target.get_effective_defense_skill()
        if acu < df:
            self.add_event("ATTACK", {"source": fist.id, "target": target.id,
                                      "damage": 0, "surprise": False, "gas": True}, floor_id=floor_id)
            self.add_event("MISS", {"source": fist.id, "target": target.id,
                                    "defense_verb": target.defense_verb}, floor_id=floor_id)
            return
        dmg = target.take_damage(random.randint(10, 20))
        if random.random() < 0.5:
            add_buff(target.buffs, "ooze", duration=5.0, level=1)
        self.add_event("ATTACK", {"source": fist.id, "target": target.id,
                                  "damage": dmg, "surprise": False, "gas": True}, floor_id=floor_id)
        if dmg > 0:
            self.add_event("DAMAGE", {"target": target.id, "amount": dmg}, floor_id=floor_id)

    def _fist_zap_rusted(self, fist, target, floor_id: int):
        acu = random.random() * fist.attack_skill
        df = random.random() * target.get_effective_defense_skill()
        if acu < df:
            self.add_event("ATTACK", {"source": fist.id, "target": target.id,
                                      "damage": 0, "surprise": False}, floor_id=floor_id)
            self.add_event("MISS", {"source": fist.id, "target": target.id,
                                    "defense_verb": target.defense_verb}, floor_id=floor_id)
            return
        add_buff(target.buffs, "cripple", duration=4.0, level=1)
        self.add_event("ATTACK", {"source": fist.id, "target": target.id,
                                  "damage": 0, "surprise": False, "cripple": True}, floor_id=floor_id)

    def _fist_zap_bright(self, fist, target, floor_id: int):
        acu = random.random() * fist.attack_skill
        df = random.random() * target.get_effective_defense_skill()
        if acu < df:
            self.add_event("ATTACK", {"source": fist.id, "target": target.id,
                                      "damage": 0, "surprise": False, "light_beam": True}, floor_id=floor_id)
            self.add_event("MISS", {"source": fist.id, "target": target.id,
                                    "defense_verb": target.defense_verb}, floor_id=floor_id)
            return
        dmg = target.take_damage(random.randint(10, 20))
        add_buff(target.buffs, "blindness", duration=10.0, level=1, stack_mode="extend")
        self.add_event("ATTACK", {"source": fist.id, "target": target.id,
                                  "damage": dmg, "surprise": False, "light_beam": True}, floor_id=floor_id)
        if dmg > 0:
            self.add_event("DAMAGE", {"target": target.id, "amount": dmg}, floor_id=floor_id)

    def _fist_zap_dark(self, fist, target, floor_id: int):
        acu = random.random() * fist.attack_skill
        df = random.random() * target.get_effective_defense_skill()
        if acu < df:
            self.add_event("ATTACK", {"source": fist.id, "target": target.id,
                                      "damage": 0, "surprise": False, "dark_bolt": True}, floor_id=floor_id)
            self.add_event("MISS", {"source": fist.id, "target": target.id,
                                    "defense_verb": target.defense_verb}, floor_id=floor_id)
            return
        dmg = target.take_damage(random.randint(10, 20))
        add_buff(target.buffs, "blindness", duration=10.0, level=1, stack_mode="extend")
        self.add_event("ATTACK", {"source": fist.id, "target": target.id,
                                  "damage": dmg, "surprise": False, "dark_bolt": True}, floor_id=floor_id)
        if dmg > 0:
            self.add_event("DAMAGE", {"target": target.id, "amount": dmg}, floor_id=floor_id)
