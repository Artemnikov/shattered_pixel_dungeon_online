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
"""The per-tick game loop for GameInstance.

Advances death processing, buff sync, player auto-movement, healing/regen,
status effects (bleed/ooze), mob respawns, and delegates boss AI to sub-mixins.
"""

import math
import random
import time
from typing import List, Optional, Type

from app.engine.dungeon.generator import TileType
from app.engine.entities.base import Difficulty, Effect, Faction, Player, Position
from app.engine.entities.buffs import process_buffs
from app.engine.game.blobs import tick_foliage_blobs
from app.engine.entities.mobs import (
    Rat, Goo, DwarfKing,
    YogDzewa, BurningFist, SoiledFist, RottingFist, RustedFist, BrightFist, DarkFist,
    DemonSpawner, Pylon, DM300,
    Wraith, TormentedSpirit, Bee, EbonyMimic, MobEntity,
    Necromancer, Tengu,
)
from app.engine.game.constants import (
    AUTO_MOVE_INTERVAL,
    HEAL_TICK_INTERVAL,
    NO_RESPAWN_FLOORS,
    OOZE_TICK_INTERVAL,
    PASSIVE_REGEN_INTERVAL,
    RESPAWN_TURNS,
    ROOM_HEAL_AMOUNT,
    SEWERS_MAX_FLOOR,
    PRISON_MAX_FLOOR,
)
from app.engine.game.floor_state import FloorState
from app.engine.systems.loot import roll_drops


def _apply_floor_scaling(mob: MobEntity, floor_id: int) -> None:
    level = floor_id
    if isinstance(mob, TormentedSpirit):
        attack = 10 + round(1.5 * level)
        mob.floor_level = level
        mob.attack_skill = attack
        mob.defense_skill = attack * 5
        mob.damage_min = 1 + (round(1.5 * level) // 2)
        mob.damage_max = 2 + round(1.5 * level)
    elif isinstance(mob, Wraith):
        attack = 10 + level
        mob.floor_level = level
        mob.attack_skill = attack
        mob.defense_skill = attack * 5
        mob.damage_min = 1 + level // 2
        mob.damage_max = 2 + level
    elif isinstance(mob, Bee):
        max_hp = (2 + level) * 4
        mob.floor_level = level
        mob.max_hp = max_hp
        mob.hp = max_hp
        mob.defense_skill = 9 + level
        mob.attack_skill = mob.defense_skill
        mob.damage_min = max(1, max_hp // 10)
        mob.damage_max = max(1, max_hp // 4)
    elif isinstance(mob, EbonyMimic):
        max_hp = (1 + level) * 6
        mob.floor_level = level
        mob.max_hp = max_hp
        mob.hp = max_hp
        mob.defense_skill = 2 + level // 2
        mob.attack_skill = 6 + level
        mob.disguised = False


def _universal_extra_pool(floor_id: int) -> List[Type[MobEntity]]:
    extras: List[Type[MobEntity]] = [
        TormentedSpirit if random.random() < 0.01 else Wraith,
        Bee,
    ]
    if floor_id > 1:
        extras.append(EbonyMimic)
    return extras


class TickMixin:
    def update_tick(self):
        self._invalidate_fov_cache()

        dt = 0.05
        for player in self.players.values():
            removed = process_buffs(player.buffs, dt)
            if "invisibility" in removed or "shadows" in removed:
                player.invisible = max(0, player.invisible - 1)
        for floor in self.floors.values():
            for mob in floor.mobs.values():
                if mob.is_alive:
                    process_buffs(mob.buffs, dt)

        blob_events = tick_foliage_blobs(self.floors, self.players)
        for ev in blob_events:
            self.add_event(ev["type"], ev["data"])

        for floor_id, floor in self.floors.items():
            self._tick_tengu_blobs(floor, floor_id)

        for player in self.players.values():
            if not player.is_alive and not player.death_processed:
                self._kill_player(player, self._get_or_create_floor(player.floor_id), player.floor_id)

        for player in self.players.values():
            self._sync_effects(player)

        for player in self.players.values():
            if player.is_downed or not player.is_alive:
                continue

            if player.move_intent:
                now = time.time()
                if now - player.last_auto_move_time >= AUTO_MOVE_INTERVAL:
                    dx, dy = player.move_intent
                    player.last_auto_move_time = now
                    self.move_entity(player.id, dx, dy)
            elif player.path_queue:
                now = time.time()
                if now - player.last_auto_move_time >= AUTO_MOVE_INTERVAL:
                    dx, dy = player.path_queue.pop(0)
                    floor = self._get_or_create_floor(player.floor_id)
                    nx, ny = player.pos.x + dx, player.pos.y + dy
                    if any(m.is_alive and m.pos.x == nx and m.pos.y == ny for m in floor.mobs.values()):
                        player.path_queue = []
                    else:
                        player.last_auto_move_time = now
                        self.move_entity(player.id, dx, dy)

            self._apply_heal_tick(player)
            self._apply_aqua_heal_tick(player)
            self._apply_room_heal_tick(player)
            self._apply_passive_regen(player)

            seal = player.belongings.artifact
            has_seal = seal is not None and getattr(seal, "kind", "") == "broken_seal"
            if player.belongings.armor is not None and has_seal:
                existing = player.get_shield("warrior_shield")
                if existing:
                    existing.amount = min(6, existing.amount + 1)
                else:
                    player.add_shield("warrior_shield", 2, priority=2, decay=600)

            if player.armor_charge < 100:
                player.armor_charge = min(100, player.armor_charge + 2)

            moved = bool(player.move_intent or player.path_queue)
            self.tick_rogue(player, dt, moved=moved)

            if player.berserk_active:
                hp_ratio = player.hp / max(player.get_total_max_hp(), 1)
                decay = 0.05 * (hp_ratio ** 2)
                bd = player.subclass_info.talent_info.level("berserk_duration")
                if bd > 0:
                    decay *= 1.0 - bd * 0.15
                player.berserk_power = max(0.0, player.berserk_power - decay)
                if player.berserk_power <= 0:
                    player.berserk_active = False
                    player.berserk_cooldown = 200

            if player.combo_count > 0:
                combo_dt = dt
                sc = player.subclass_info.talent_info.level("slow_combo")
                if sc > 0:
                    combo_dt *= 1.0 - sc * 0.15
                player.combo_timer -= combo_dt
                if player.combo_timer <= 0:
                    player.combo_count = 0
                    player.combo_timer = 0.0

            if player.berserk_cooldown > 0:
                player.berserk_cooldown -= 1

            self._apply_hunger_tick(player)

            player.decay_shields()
            if player.has_fury:
                player.fury_turns_remaining -= 1
                if player.fury_turns_remaining <= 0:
                    player.has_fury = False
                    player.fury_turns_remaining = 0

        for floor_id, floor in self.floors.items():
            active_players = [p for p in self._players_on_floor(floor_id) if p.is_alive and not p.is_downed]
            if not active_players:
                continue

            self._process_bleed_ooze(floor_id, active_players)
            self._process_respawns(floor_id, floor, active_players)
            self._update_prison_boss(floor, floor_id)

            for mob in list(floor.mobs.values()):
                if not mob.is_alive:
                    continue

                if mob.faction == Faction.PLAYER:
                    self._update_shadow_ally(mob, floor, floor_id)
                    continue

                if isinstance(mob, Goo):
                    if self._update_goo(mob, floor, floor_id):
                        continue

                if isinstance(mob, DwarfKing):
                    self._update_dwarf_king(mob, floor, floor_id)
                    if "IMMOVABLE" in getattr(mob, "properties", []):
                        continue

                if isinstance(mob, YogDzewa):
                    self._update_yog_dzewa(mob, floor, floor_id)
                    continue

                if isinstance(mob, DM300):
                    if not mob.fight_started:
                        target = self._find_nearest_player(mob.pos, floor_id)
                        if target is not None:
                            mob.fight_started = True
                    if mob.supercharged:
                        self._update_dm300_chase(mob, floor, floor_id)
                        self._update_dm300_chase(mob, floor, floor_id)
                        continue

                if isinstance(mob, DemonSpawner):
                    self._update_demon_spawner(mob, floor, floor_id)
                    continue

                if isinstance(mob, Pylon):
                    self._update_pylon(mob, floor, floor_id)
                    continue

                if isinstance(mob, (BurningFist, SoiledFist, RottingFist,
                                     RustedFist, BrightFist, DarkFist)):
                    if self._update_yog_fist(mob, floor, floor_id):
                        continue

                if isinstance(mob, Necromancer):
                    if self._update_necromancer(mob, floor, floor_id):
                        continue

                if isinstance(mob, Tengu):
                    if self._update_tengu(mob, floor, floor_id):
                        continue

                target_player = self._find_nearest_player(mob.pos, floor_id)
                if mob.ai_state == "fleeing":
                    if target_player:
                        dx = mob.pos.x - target_player.pos.x
                        dy = mob.pos.y - target_player.pos.y
                        if abs(dx) >= abs(dy):
                            step = (1 if dx > 0 else -1, 0)
                        else:
                            step = (0, 1 if dy > 0 else -1)
                        nx, ny = mob.pos.x + step[0], mob.pos.y + step[1]
                        if 0 <= nx < floor.width and 0 <= ny < floor.height:
                            occupied = any(m.is_alive and m.pos.x == nx and m.pos.y == ny for m in floor.mobs.values() if m.id != mob.id)
                            if not occupied:
                                self.move_entity(mob.id, step[0], step[1])
                    continue

                if target_player and target_player.invisible > 0:
                    target_player = None

                if target_player and getattr(mob, "never_wakes", False):
                    target_player = None
                elif target_player and getattr(mob, "ai_state", "") in ("idle", "sleeping"):
                    dist = self._get_distance(mob.pos, target_player.pos)
                    if dist > self._view_distance(mob):
                        target_player = None
                    else:
                        stealth = target_player.get_stealth()
                        detect_chance = 1.0 / max(0.01, dist + stealth)
                        subclass_info = getattr(target_player, "subclass_info", None)
                        if subclass_info:
                            silent_level = subclass_info.talent_info.level("silent_steps")
                            if silent_level > 0 and dist >= 4 - silent_level:
                                detect_chance = 0.0
                        if random.random() >= detect_chance:
                            target_player = None
                        else:
                            mob.ai_state = "hunting"

                if target_player and getattr(mob, "ai_state", "") == "wandering":
                    dist = self._get_distance(mob.pos, target_player.pos)
                    if dist > self._view_distance(mob):
                        target_player = None
                    else:
                        stealth = target_player.get_stealth()
                        subclass_info = getattr(target_player, "subclass_info", None)
                        if subclass_info:
                            stealth += subclass_info.talent_info.level("heightened_senses") * 2
                        detect_chance = 1.0 / max(0.01, dist / 2 + stealth)
                        if random.random() >= detect_chance:
                            target_player = None
                        else:
                            mob.ai_state = "hunting"

                if (isinstance(mob, Goo) and mob.ai_state == "hunting" and not mob.fight_started
                        and target_player is not None
                        and self._is_in_los(mob.pos, target_player.pos, floor_id=floor_id,
                                             distance=self._view_distance(target_player))):
                    mob.fight_started = True
                    self.add_event("GOO_FIGHT_STARTED", {"mob": mob.id}, floor_id=floor_id)

                dist = self._get_distance(mob.pos, target_player.pos) if target_player else float("inf")
                atk_range = getattr(mob, "attack_range", 1)
                is_passive = getattr(mob, "ai_state", "") == "passive"

                if is_passive and mob.hp >= mob.max_hp:
                    if random.random() < 0.02:
                        dx, dy = random.choice([(0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (1, -1), (-1, 1), (-1, -1)])
                        self.move_entity(mob.id, dx, dy)
                    continue

                in_attack_range = target_player is not None and dist <= atk_range
                if in_attack_range:
                    if not mob.engaged:
                        mob.engaged = True
                        mob.last_attack_time = time.time() - max(
                            0.0, mob.attack_cooldown - mob.aggro_windup
                        )
                else:
                    mob.engaged = False

                if self.difficulty == Difficulty.EASY:
                    if target_player and dist <= atk_range:
                        dx, dy = target_player.pos.x - mob.pos.x, target_player.pos.y - mob.pos.y
                        self.move_entity(mob.id, dx, dy)
                    elif random.random() < 0.1 * max(1.0, mob.speed):
                        dx, dy = random.choice([(0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (1, -1), (-1, 1), (-1, -1)])
                        self.move_entity(mob.id, dx, dy)

                elif self.difficulty == Difficulty.NORMAL:
                    if target_player and dist <= atk_range:
                        dx, dy = target_player.pos.x - mob.pos.x, target_player.pos.y - mob.pos.y
                        self.move_entity(mob.id, dx, dy)
                    elif target_player and self._is_in_los(mob.pos, target_player.pos, floor_id=floor_id):
                        step = self._get_next_step_to(mob.pos, target_player.pos, floor_id=floor_id)
                        if step and (dist > atk_range or not any(
                            m.is_alive and m.pos.x == mob.pos.x + step[0] and m.pos.y == mob.pos.y + step[1]
                            for m in floor.mobs.values() if m.id != mob.id
                        )):
                            self.move_entity(mob.id, step[0], step[1])
                    elif random.random() < 0.1 * max(1.0, mob.speed):
                        dx, dy = random.choice([(0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (1, -1), (-1, 1), (-1, -1)])
                        self.move_entity(mob.id, dx, dy)

                elif self.difficulty == Difficulty.HARD:
                    if target_player and dist <= atk_range:
                        dx, dy = target_player.pos.x - mob.pos.x, target_player.pos.y - mob.pos.y
                        self.move_entity(mob.id, dx, dy)
                    elif target_player and dist < 20:
                        step = self._get_next_step_to(mob.pos, target_player.pos, floor_id=floor_id)
                        if step:
                            self.move_entity(mob.id, step[0], step[1])
                    elif random.random() < 0.1 * max(1.0, mob.speed):
                        dx, dy = random.choice([(0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (1, -1), (-1, 1), (-1, -1)])
                        self.move_entity(mob.id, dx, dy)

    def _update_shadow_ally(self, ally, floor: FloorState, floor_id: int):
        move_times = getattr(self, "_ally_move_times", None)
        if move_times is None:
            move_times = self._ally_move_times = {}
        now = time.time()
        if now - move_times.get(ally.id, 0.0) < AUTO_MOVE_INTERVAL:
            return

        enemies = [m for m in floor.mobs.values()
                   if m.is_alive and m.faction != Faction.PLAYER]
        target = None
        best = 999
        for m in enemies:
            d = self._get_distance(ally.pos, m.pos)
            if d < best and self._is_in_los(ally.pos, m.pos, floor_id=floor_id):
                best, target = d, m

        if target is not None:
            move_times[ally.id] = now
            if best <= 1:
                ally.last_attack_time = now - ally.attack_cooldown
                adx = (target.pos.x > ally.pos.x) - (target.pos.x < ally.pos.x)
                ady = (target.pos.y > ally.pos.y) - (target.pos.y < ally.pos.y)
                self.move_entity(ally.id, adx, ady)
            else:
                step = self._get_next_step_to(ally.pos, target.pos, floor_id=floor_id)
                if step:
                    self.move_entity(ally.id, step[0], step[1])
            return

        owner = self.players.get(getattr(ally, "owner_id", None) or "")
        if owner is not None and owner.floor_id == floor_id:
            if self._get_distance(ally.pos, owner.pos) > 1:
                move_times[ally.id] = now
                step = self._get_next_step_to(ally.pos, owner.pos, floor_id=floor_id)
                if step:
                    self.move_entity(ally.id, step[0], step[1])

    def _process_bleed_ooze(self, floor_id: int, active_players: List[Player]):
        floor = self._get_or_create_floor(floor_id)
        for player in active_players:
            if player.bleed_turns > 0 and player.bleed_amount > 0:
                dmg = player.bleed_amount
                player.take_damage(dmg)
                self.add_event("DAMAGE", {"target": player.id, "amount": dmg, "bleed": True}, floor_id=floor_id)
                player.bleed_turns -= 1
                if player.bleed_turns <= 0:
                    player.bleed_amount = 0

            if player.ooze_amount > 0:
                if floor.grid[player.pos.y][player.pos.x] == TileType.FLOOR_WATER:
                    player.ooze_amount = 0
                    player.ooze_cooldown = 0
                elif player.ooze_cooldown > 0:
                    player.ooze_cooldown -= 1
                else:
                    player.take_damage(1)
                    self.add_event("DAMAGE", {"target": player.id, "amount": 1, "ooze": True}, floor_id=floor_id)
                    player.ooze_amount -= 1
                    player.ooze_cooldown = OOZE_TICK_INTERVAL

        for floor in [self._get_or_create_floor(floor_id)]:
            for mob in floor.mobs.values():
                if mob.is_alive and mob.bleed_turns > 0 and mob.bleed_amount > 0:
                    dmg = mob.bleed_amount
                    mob.hp -= dmg
                    self.add_event("DAMAGE", {"target": mob.id, "amount": dmg, "bleed": True}, floor_id=floor_id)
                    mob.bleed_turns -= 1
                    if mob.hp <= 0:
                        mob.hp = 0
                        mob.is_alive = False
                        mob.die(
                            floor_mobs=floor.mobs,
                            tile_x=mob.pos.x,
                            tile_y=mob.pos.y,
                            players=list(self._players_on_floor(floor_id)),
                        )
                        self.add_event("DEATH", {"target": mob.id}, floor_id=floor_id)
                        self.handle_mob_death(mob, floor, floor_id)
                        for item in roll_drops(mob, self.drop_counters, mob.pos.x, mob.pos.y):
                            floor.items[item.id] = item
                    if mob.bleed_turns <= 0:
                        mob.bleed_amount = 0

    def _process_respawns(self, floor_id: int, floor: FloorState, active_players: List[Player]):
        if floor_id in NO_RESPAWN_FLOORS:
            return
        live_mobs = sum(1 for m in floor.mobs.values() if m.is_alive)
        if live_mobs >= floor.mob_limit:
            floor.respawn_counter = 0
            return
        floor.respawn_counter += 1
        if floor.respawn_counter < RESPAWN_TURNS:
            return
        floor.respawn_counter = 0
        universal_extra = random.random() < 0.01
        if universal_extra:
            cls = random.choice(_universal_extra_pool(floor_id))
        elif floor_id <= SEWERS_MAX_FLOOR:
            rotation = self._get_sewers_rotation(floor_id)
            cls = random.choice(rotation) if rotation else Rat
        elif floor_id <= PRISON_MAX_FLOOR:
            rotation = self._get_prison_rotation(floor_id)
            cls = random.choice(rotation) if rotation else Rat
        else:
            rotation = self._get_sewers_rotation(floor_id)
            cls = random.choice(rotation) if rotation else Rat
        floor_tiles = [
            (x, y) for y in range(floor.height) for x in range(floor.width)
            if floor.grid[y][x] in [TileType.FLOOR, TileType.FLOOR_WOOD, TileType.FLOOR_WATER, TileType.FLOOR_COBBLE, TileType.FLOOR_GRASS]
            and not self._is_in_safe_room(floor, x, y)
            and not any(m.pos.x == x and m.pos.y == y for m in floor.mobs.values() if m.is_alive)
        ]
        if not floor_tiles:
            return
        x, y = random.choice(floor_tiles)
        mob = self._spawn_mob_at(cls, x, y)
        if universal_extra:
            _apply_floor_scaling(mob, floor_id)
        floor.mobs[mob.id] = mob

    def _sync_effects(self, player: Player):
        from app.engine.entities.buffs import has_buff
        existing = {e.key: e for e in player.active_effects}
        effects = []
        if player.heal_left > 0:
            prev = existing.get("regen")
            duration = max(prev.duration if prev else 0.0, player.heal_left)
            effects.append(Effect(
                key="regen", name="Healing", icon=44,
                remaining=player.heal_left, duration=duration,
            ))
        if player.aqua_heal_left > 0:
            effects.append(Effect(
                key="aqua_rejuv", name="Aquatic Rejuvenation", icon=44,
                remaining=player.aqua_heal_left, duration=player.aqua_heal_left,
            ))
        if player.berserk_active:
            effects.append(Effect(
                key="berserk", name="Berserk", icon=13,
                remaining=player.berserk_power, duration=1.0,
            ))
        if has_buff(player.buffs, "endure"):
            effects.append(Effect(
                key="endure", name="Endure", icon=6,
                remaining=1.0, duration=1.0,
            ))
        if player.has_fury:
            effects.append(Effect(
                key="fury", name="Fury", icon=5,
                remaining=float(player.fury_turns_remaining), duration=10.0,
            ))
        player.active_effects = effects

    def _apply_heal_tick(self, player: Player):
        if player.heal_left <= 0:
            return

        player.heal_cooldown -= 1
        if player.heal_cooldown > 0:
            return

        amt = round(player.heal_left * player.heal_pct_per_tick) + player.heal_flat_per_tick
        amt = max(1, min(amt, player.heal_left))

        if player.hp < player.get_total_max_hp():
            player.hp = min(player.get_total_max_hp(), player.hp + amt)

        player.heal_left -= amt
        player.heal_cooldown = HEAL_TICK_INTERVAL

        self.add_event(
            "HEAL",
            {"target": player.id, "amount": int(amt), "x": player.pos.x, "y": player.pos.y},
            floor_id=player.floor_id,
        )

        if player.heal_left <= 0:
            player.heal_left = 0.0
            player.heal_pct_per_tick = 0.0
            player.heal_flat_per_tick = 0.0

    def _apply_aqua_heal_tick(self, player: Player):
        # Elixir of Aquatic Rejuvenation (SPD AquaHealing): heals
        # max(1, maxHP/50) per turn while standing in water, until the pool
        # (round(maxHP*1.5)) is exhausted. Fractional heal amounts are rounded
        # probabilistically (SPD's Random.round / chance-of-rounding-up).
        if player.aqua_heal_left <= 0:
            return

        max_hp = player.get_total_max_hp()
        if player.hp >= max_hp:
            return

        floor = self._get_or_create_floor(player.floor_id)
        if floor.grid[player.pos.y][player.pos.x] != TileType.FLOOR_WATER:
            return

        raw = max(1.0, max_hp / 50.0)
        whole = math.floor(raw)
        frac = raw - whole
        amt = whole + 1 if random.random() < frac else whole
        amt = max(1, amt)
        amt = min(amt, player.aqua_heal_left, max_hp - player.hp)

        player.hp = min(max_hp, player.hp + amt)
        player.aqua_heal_left -= amt
        if player.aqua_heal_left <= 0:
            player.aqua_heal_left = 0.0

        self.add_event(
            "HEAL",
            {"target": player.id, "amount": int(amt), "x": player.pos.x, "y": player.pos.y},
            floor_id=player.floor_id,
        )

    def _apply_room_heal_tick(self, player: Player):
        floor = self.floors.get(player.floor_id)
        if floor is None or not floor.rooms:
            return

        if not self._is_in_entrance_room(floor, player.pos.x, player.pos.y):
            player.room_heal_cooldown = 0
            return

        max_hp = player.get_total_max_hp()
        if player.hp >= max_hp:
            return

        player.room_heal_cooldown -= 1
        if player.room_heal_cooldown > 0:
            return

        amt = min(ROOM_HEAL_AMOUNT, max_hp - player.hp)
        player.hp += amt
        player.room_heal_cooldown = HEAL_TICK_INTERVAL

        self.add_event(
            "HEAL",
            {"target": player.id, "amount": int(amt), "x": player.pos.x, "y": player.pos.y},
            floor_id=player.floor_id,
        )

    _HUNGER_RATE = 1.0 / 20.0
    _HUNGER_HUNGRY = 300.0
    _HUNGER_STARVING = 450.0

    def _apply_hunger_tick(self, player: Player):
        if player.is_downed:
            return
        player.hunger = min(self._HUNGER_STARVING + 50, player.hunger + self._HUNGER_RATE)
        if player.hunger >= self._HUNGER_STARVING:
            dmg = max(1, player.max_hp // 100)
            player.take_damage(dmg)

    def _apply_passive_regen(self, player: Player):
        floor = self.floors.get(player.floor_id)
        if floor is None or not floor.rooms:
            return
        if not self._is_in_entrance_room(floor, player.pos.x, player.pos.y):
            return
        if player.hp <= 0 or player.hp >= player.get_total_max_hp():
            player._regen_cooldown = 0
            return
        cooldown = getattr(player, "_regen_cooldown", 0)
        cooldown -= 1
        if cooldown > 0:
            player._regen_cooldown = cooldown
            return
        player.hp = min(player.get_total_max_hp(), player.hp + 1)
        player._regen_cooldown = PASSIVE_REGEN_INTERVAL
