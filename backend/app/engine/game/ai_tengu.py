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
from app.engine.dungeon.spd_levelgen import prison_boss_layout as layout
from app.engine.dungeon.spd_levelgen.level import _CIRCLE8_OFFSETS
from app.engine.entities.base import Position
from app.engine.entities.buffs import add_buff
from app.engine.entities.mobs import Tengu
from app.engine.game.floor_state import FloorState
from app.engine.systems.loot import roll_drops


class TenguAIMixin:
    def _tick_tengu_blobs(self, floor: FloorState, floor_id: int) -> None:
        if floor.floor_id != 10:
            return

        for blob_id, blob in list(floor.blob_areas.items()):
            if blob.get("type") == "tengu_fire":
                self._tick_tengu_fire_blob(blob, floor, floor_id)
            elif blob.get("type") == "tengu_shocker":
                self._tick_tengu_shocker_blob(blob, floor, floor_id)

    def _tick_tengu_fire_blob(self, blob: dict, floor: FloorState, floor_id: int) -> None:
        cells: set = blob.get("cells", set())
        volume: dict = blob.get("volume", {})
        new_cells = set()
        burned = False
        observe = False

        for (cx, cy) in list(cells):
            vol = volume.get((cx, cy), 1) - 1
            if vol <= 0:
                for p in self._players_on_floor(floor_id):
                    if p.is_alive and p.pos.x == cx and p.pos.y == cy:
                        add_buff(p.buffs, "burning", duration=4.0, level=1, stack_mode="extend")
                        burned = True
                        self.boss_scores[1] -= 100
                        self.qualified_for_boss_challenge = False
                for m in list(floor.mobs.values()):
                    if m.is_alive and m.pos.x == cx and m.pos.y == cy and not isinstance(m, Tengu):
                        add_buff(m.buffs, "burning", duration=4.0, level=1, stack_mode="extend")
                        burned = True
                for item_id, item in list(floor.items.items()):
                    if item.pos and item.pos.x == cx and item.pos.y == cy:
                        del floor.items[item_id]
                if (cx, cy) in floor.plants:
                    del floor.plants[(cx, cy)]
                if floor.grid[cy][cx] in (TileType.FLOOR_GRASS, TileType.HIGH_GRASS, TileType.FURROWED_GRASS):
                    floor.grid[cy][cx] = TileType.FLOOR
                    observe = True
                cells.discard((cx, cy))
                del volume[(cx, cy)]
            else:
                volume[(cx, cy)] = vol
                new_cells.add((cx, cy))

        if new_cells:
            blob["cells"] = new_cells
            blob["volume"] = volume
        else:
            del floor.blob_areas[id(blob)]

        if observe:
            floor.rebuild_flags()
        if burned:
            self.add_event("PLAY_SOUND", {"sound": "BURNING"}, floor_id=floor_id)

    def _tick_tengu_shocker_blob(self, blob: dict, floor: FloorState, floor_id: int) -> None:
        cells: set = blob.get("cells", set())
        volume: dict = blob.get("volume", {})
        new_cells = set()
        depth = floor.floor_id
        shocked = False

        for (cx, cy) in list(cells):
            vol = volume.get((cx, cy), 1) - 1
            if vol <= 0:
                for p in self._players_on_floor(floor_id):
                    if p.is_alive and p.pos.x == cx and p.pos.y == cy:
                        taken = p.take_damage(2 + depth)
                        self.add_event("ATTACK", {"source": "tengu_blob", "target": p.id,
                                                  "damage": taken, "surprise": False, "shock": True}, floor_id=floor_id)
                        if taken > 0:
                            self.add_event("DAMAGE", {"target": p.id, "amount": taken}, floor_id=floor_id)
                            self.boss_scores[1] -= 100
                            self.qualified_for_boss_challenge = False
                        shocked = True
                for m in list(floor.mobs.values()):
                    if m.is_alive and m.pos.x == cx and m.pos.y == cy and not isinstance(m, Tengu):
                        taken = m.take_damage(2 + depth)
                        shocked = True
                        if not m.is_alive:
                            m.die(floor_mobs=floor.mobs, tile_x=m.pos.x, tile_y=m.pos.y,
                                  players=list(self._players_on_floor(floor_id)))
                            self.add_event("DEATH", {"target": m.id}, floor_id=floor_id)
                            self.handle_mob_death(m, floor, floor_id)
                cells.discard((cx, cy))
                del volume[(cx, cy)]
            else:
                volume[(cx, cy)] = vol
                new_cells.add((cx, cy))

        if new_cells:
            blob["cells"] = new_cells
            blob["volume"] = volume
        else:
            del floor.blob_areas[id(blob)]

        if shocked:
            self.add_event("PLAY_SOUND", {"sound": "LIGHTNING"}, floor_id=floor_id)

    def _update_tengu(self, tengu: Tengu, floor: FloorState, floor_id: int) -> bool:
        if tengu.is_alive:
            tengu.clamp_bracket()

        if tengu.bomb_timer > 0:
            tengu.bomb_timer -= 1
            if tengu.bomb_timer == 0:
                self._tengu_detonate_bomb(tengu, floor, floor_id)
                return True
            if tengu.bomb_timer % 20 == 0 and tengu.bomb_timer < 60:
                countdown = tengu.bomb_timer // 20
                self.add_event("TENGU_BOMB_COUNTDOWN", {
                    "mob": tengu.id, "x": tengu.bomb_x, "y": tengu.bomb_y, "count": countdown,
                }, floor_id=floor_id)

        if not tengu.is_alive:
            return False

        bracket = (tengu.hp * 8 - 1) // tengu.max_hp
        if bracket < tengu.hp_bracket:
            tengu.hp_bracket = bracket

            if floor.tengu_state == "FIGHT_START" and tengu.is_enraged():
                pass
            else:
                self._tengu_jump(tengu, floor, floor_id)
            return True

        if not tengu.is_enraged():
            return False

        if not self._can_tengu_use_ability(tengu):
            return False

        target = self._find_nearest_player(tengu.pos, floor_id)
        if target is None:
            return False

        if not self._is_in_los(tengu.pos, target.pos, floor_id=floor_id,
                                distance=self._view_distance(tengu)):
            return False

        self._tengu_use_ability(tengu, target, floor, floor_id)
        return True

    def _tengu_jump(self, tengu: Tengu, floor: FloorState, floor_id: int) -> None:
        target = self._find_nearest_player(tengu.pos, floor_id)
        if target is None:
            return

        confine_to_tengu_cell = (floor.floor_id == 10 and floor.tengu_state == "FIGHT_START")

        new_pos = None
        for _ in range(100):
            if confine_to_tengu_cell:
                x = random.randint(layout.TENGU_CELL.left + 1, layout.TENGU_CELL.right - 2)
                y = random.randint(layout.TENGU_CELL.top + 1, layout.TENGU_CELL.bottom - 2)
            else:
                x = random.randint(0, floor.width - 1)
                y = random.randint(0, floor.height - 1)

            if not floor.flags or not floor.flags.passable[y][x]:
                continue
            if x == tengu.pos.x and y == tengu.pos.y:
                continue
            if any(m.is_alive and m.pos.x == x and m.pos.y == y
                   for m in floor.mobs.values() if m.id != tengu.id):
                continue
            if any(p.is_alive and p.pos.x == x and p.pos.y == y
                   for p in self._players_on_floor(floor_id)):
                continue

            d = self._get_distance(Position(x=x, y=y), target.pos)
            if confine_to_tengu_cell:
                if d < 3.5:
                    continue
            else:
                if d < 5 or d > 7:
                    continue
                hero_d = self._get_distance(Position(x=x, y=y),
                                            self._find_nearest_player(tengu.pos, floor_id).pos)
                if hero_d < 5 or hero_d > 7:
                    continue
                from_current = self._get_distance(Position(x=x, y=y), tengu.pos)
                if from_current < 5:
                    continue
                has_heap = any(item.pos and item.pos.x == x and item.pos.y == y
                               for item in floor.items.values())
                if has_heap:
                    continue

            new_pos = (x, y)
            break

        if new_pos is None:
            return

        x, y = new_pos
        tengu.pos.x, tengu.pos.y = x, y
        self.add_event("TENGU_JUMP", {"mob": tengu.id, "x": x, "y": y}, floor_id=floor_id)
        self.add_event("PLAY_SOUND", {"sound": "PUFF"}, floor_id=floor_id)

        if confine_to_tengu_cell:
            fill = 0.9 - 0.5 * ((tengu.hp - tengu.max_hp / 2) / (tengu.max_hp / 2))
            self._place_traps_in_tengu_cell(floor, floor_id, tengu, max(0.0, min(1.0, fill)))
        else:
            if tengu.arena_jumps < 4:
                tengu.arena_jumps += 1

    def _can_tengu_use_ability(self, tengu: Tengu) -> bool:
        if not tengu.is_enraged():
            return False
        if tengu.abilities_used >= tengu.target_ability_uses():
            return False
        if tengu.ability_cooldown_until > 0:
            tengu.ability_cooldown_until -= 1
        behind = tengu.target_ability_uses() - tengu.abilities_used
        if behind >= 4:
            tengu.ability_cooldown_until = 0
        elif behind >= 3:
            if tengu.ability_cooldown_until == -1 or tengu.ability_cooldown_until > 1:
                tengu.ability_cooldown_until = 1
        else:
            if tengu.ability_cooldown_until == -1:
                tengu.ability_cooldown_until = random.randint(1, 4)
        return tengu.ability_cooldown_until == 0

    def _tengu_use_ability(self, tengu: Tengu, target, floor: FloorState, floor_id: int) -> None:
        ability_used = False
        ability_to_use = -1
        while not ability_used:
            if tengu.abilities_used == 0:
                ability_to_use = 0
            elif tengu.abilities_used == 1:
                ability_to_use = 2
            else:
                ability_to_use = random.randint(0, 2)

            if ability_to_use == tengu.last_ability and random.randint(0, 9) != 0:
                continue

            if ability_to_use == 0:
                ability_used = self._tengu_throw_bomb(tengu, target, floor, floor_id)
                if not ability_used and tengu.abilities_used == 0:
                    ability_to_use = 1
                    ability_used = self._tengu_throw_fire(tengu, target, floor, floor_id)
            elif ability_to_use == 1:
                ability_used = self._tengu_throw_fire(tengu, target, floor, floor_id)
            else:
                ability_used = self._tengu_throw_shocker(tengu, target, floor, floor_id)
                if not ability_used and tengu.abilities_used == 1:
                    ability_to_use = 1
                    ability_used = self._tengu_throw_fire(tengu, target, floor, floor_id)

        tengu.last_ability = ability_to_use
        tengu.abilities_used += 1

        behind = tengu.target_ability_uses() - tengu.abilities_used
        if behind >= 4:
            tengu.ability_cooldown_until = 0
        else:
            tengu.ability_cooldown_until = random.randint(1, 4)

    def _tengu_throw_bomb(self, tengu: Tengu, target, floor: FloorState, floor_id: int) -> bool:
        target_cell = None
        for dx, dy in _CIRCLE8_OFFSETS:
            nx, ny = target.pos.x + dx, target.pos.y + dy
            if not (0 <= nx < floor.width and 0 <= ny < floor.height):
                continue
            if floor.flags and floor.flags.solid[ny][nx]:
                continue
            if tengu.bomb_x == nx and tengu.bomb_y == ny:
                continue
            occupied = False
            if any(m.is_alive and m.pos.x == nx and m.pos.y == ny for m in floor.mobs.values()):
                occupied = True
            if not occupied:
                for p in self._players_on_floor(floor_id):
                    if p.is_alive and p.pos.x == nx and p.pos.y == ny:
                        occupied = True
                        break
            if occupied:
                continue
            if target_cell is None:
                target_cell = (nx, ny)
            else:
                cur_d = (nx - tengu.pos.x) ** 2 + (ny - tengu.pos.y) ** 2
                best_d = (target_cell[0] - tengu.pos.x) ** 2 + (target_cell[1] - tengu.pos.y) ** 2
                if cur_d < best_d:
                    target_cell = (nx, ny)

        if target_cell is None:
            return False

        x, y = target_cell
        tengu.bomb_x, tengu.bomb_y = x, y
        tengu.bomb_timer = 60

        self.add_event("RANGED_ATTACK", {"source": tengu.id, "x": tengu.pos.x, "y": tengu.pos.y,
                                          "target_x": x, "target_y": y, "projectile": "shuriken",
                                          "crit": False, "grim_proc": False}, floor_id=floor_id)
        self.add_event("TENGU_BOMB", {"mob": tengu.id, "x": x, "y": y, "timer": tengu.bomb_timer}, floor_id=floor_id)
        self.add_event("PLAY_SOUND", {"sound": "PUFF"}, floor_id=floor_id)
        return True

    def _tengu_detonate_bomb(self, tengu: Tengu, floor: FloorState, floor_id: int) -> None:
        x, y = tengu.bomb_x, tengu.bomb_y
        tengu.bomb_x = -1
        tengu.bomb_y = -1
        depth = floor.floor_id
        center = Position(x=x, y=y)

        for p in self._players_on_floor(floor_id):
            if p.is_alive and self._get_distance(p.pos, center) <= 2:
                raw = random.randint(5 + depth, 10 + 2 * depth)
                taken = p.take_damage(max(0, raw - random.randint(p.get_dr_min(), p.get_dr_max())))
                self.add_event("ATTACK", {"source": tengu.id, "target": p.id,
                                          "damage": taken, "surprise": False}, floor_id=floor_id)
                if taken > 0:
                    self.add_event("DAMAGE", {"target": p.id, "amount": taken}, floor_id=floor_id)
                    self.boss_scores[1] -= 100
                    self.qualified_for_boss_challenge = False

        for m in list(floor.mobs.values()):
            if m.is_alive and m.id != tengu.id and self._get_distance(m.pos, center) <= 2:
                raw = random.randint(5 + depth, 10 + 2 * depth)
                taken = m.take_damage(max(0, raw - random.randint(m.get_dr_min(), m.get_dr_max())))
                self.add_event("ATTACK", {"source": tengu.id, "target": m.id,
                                          "damage": taken, "surprise": False}, floor_id=floor_id)
                if taken > 0:
                    self.add_event("DAMAGE", {"target": m.id, "amount": taken}, floor_id=floor_id)
                if not m.is_alive:
                    m.die(floor_mobs=floor.mobs, tile_x=m.pos.x, tile_y=m.pos.y,
                          players=list(self._players_on_floor(floor_id)))
                    self.add_event("DEATH", {"target": m.id}, floor_id=floor_id)
                    self.handle_mob_death(m, floor, floor_id)
                    for item in roll_drops(m, self.drop_counters, m.pos.x, m.pos.y):
                        floor.items[item.id] = item

        self.add_event("TENGU_BLAST", {"mob": tengu.id, "x": x, "y": y}, floor_id=floor_id)
        self.add_event("PLAY_SOUND", {"sound": "BLAST"}, floor_id=floor_id)

    def _tengu_throw_fire(self, tengu: Tengu, target, floor: FloorState, floor_id: int) -> bool:
        dx = target.pos.x - tengu.pos.x
        dy = target.pos.y - tengu.pos.y
        step_x = (dx > 0) - (dx < 0)
        step_y = (dy > 0) - (dy < 0)
        if step_x == 0 and step_y == 0:
            return False

        direction = -1
        for i, (cdx, cdy) in enumerate(_CIRCLE8_OFFSETS):
            if cdx == step_x and cdy == step_y:
                direction = i
                break
        if direction == -1:
            return False

        blob = {
            "type": "tengu_fire",
            "direction": direction,
            "cells": {(tengu.pos.x, tengu.pos.y)},
            "volume": {(tengu.pos.x, tengu.pos.y): 4},
            "cur_cells": [(tengu.pos.x, tengu.pos.y)],
        }
        floor.blob_areas[id(blob)] = blob

        self._spread_tengu_fire(blob, floor, floor_id)

        self.add_event("TENGU_FIRE", {"mob": tengu.id, "cells": [(tengu.pos.x, tengu.pos.y)]}, floor_id=floor_id)
        self.add_event("PLAY_SOUND", {"sound": "BURNING"}, floor_id=floor_id)
        return True

    def _spread_tengu_fire(self, blob: dict, floor: FloorState, floor_id: int) -> None:
        direction = blob.get("direction", 0)
        cur_cells = blob.get("cur_cells", [])
        cells: set = blob.get("cells", set())
        volume: dict = blob.get("volume", {})

        def _left(d):
            return 7 if d == 0 else d - 1
        def _right(d):
            return 0 if d == 7 else d + 1

        new_cur = []
        for (cx, cy) in cur_cells:
            for di in (_left(direction), direction, _right(direction)):
                cdx, cdy = _CIRCLE8_OFFSETS[di]
                nx, ny = cx + cdx, cy + cdy
                if not (0 <= nx < floor.width and 0 <= ny < floor.height):
                    continue
                if floor.flags and floor.flags.solid[ny][nx]:
                    continue
                if (nx, ny) not in cells:
                    cells.add((nx, ny))
                    volume[(nx, ny)] = 2
                    new_cur.append((nx, ny))

        blob["cur_cells"] = new_cur if new_cur else cur_cells

    def _tengu_throw_shocker(self, tengu: Tengu, target, floor: FloorState, floor_id: int) -> bool:
        target_cell = None
        for dx, dy in _CIRCLE8_OFFSETS:
            nx, ny = target.pos.x + dx, target.pos.y + dy
            if not (0 <= nx < floor.width and 0 <= ny < floor.height):
                continue
            if floor.flags and floor.flags.solid[ny][nx]:
                continue
            if abs(nx - tengu.pos.x) + abs(ny - tengu.pos.y) < 2:
                continue
            too_close = False
            for blob_id, blob in list(floor.blob_areas.items()):
                if blob.get("type") == "tengu_shocker":
                    sx, sy = blob.get("origin", (-1, -1))
                    if abs(nx - sx) + abs(ny - sy) < 2:
                        too_close = True
                        break
            if too_close:
                continue
            if target_cell is None:
                target_cell = (nx, ny)
            else:
                cur_d = (nx - tengu.pos.x) ** 2 + (ny - tengu.pos.y) ** 2
                best_d = (target_cell[0] - tengu.pos.x) ** 2 + (target_cell[1] - tengu.pos.y) ** 2
                if cur_d < best_d:
                    target_cell = (nx, ny)

        if target_cell is None:
            return False

        x, y = target_cell

        blob = {
            "type": "tengu_shocker",
            "origin": (x, y),
            "cells": {(x, y)},
            "volume": {(x, y): 1},
            "shocking_ordinals": None,
        }
        floor.blob_areas[id(blob)] = blob

        self.add_event("TENGU_SHOCKER", {"mob": tengu.id, "cells": [(x, y)]}, floor_id=floor_id)
        self.add_event("PLAY_SOUND", {"sound": "LIGHTNING"}, floor_id=floor_id)
        return True
