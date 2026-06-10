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
status effects (bleed/ooze), mob respawns, and difficulty-scaled mob AI.
"""

import random
import time
from typing import List, Optional, Type

from app.engine.dungeon.generator import TileType
from app.engine.dungeon.spd_levelgen.level import _CIRCLE8_OFFSETS
from app.engine.entities.base import Difficulty, Effect, Faction, Player, Position
from app.engine.entities.buffs import add_buff, process_buffs
from app.engine.game.blobs import tick_foliage_blobs
from app.engine.entities.mobs import (
    Rat, Goo, DwarfKing, DKGhoul, DKMonk, DKWarlock, DKGolem,
    YogDzewa, BurningFist, SoiledFist, RottingFist, RustedFist, BrightFist, DarkFist,
    YogRipper, DemonSpawner, Pylon, RipperDemon, DM300,
    Wraith, TormentedSpirit, Bee, EbonyMimic, MobEntity,
)
from app.engine.game.constants import (
    AUTO_MOVE_INTERVAL,
    GOO_WATER_HEAL_INTERVAL,
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
    """Apply SPD's adjustStats/spawn level-scaling formulas for the
    "universal extra" respawn pool (Wraith/TormentedSpirit, Bee, EbonyMimic).

    These mobs normally have their stats set when constructed via their
    item-gated spawn paths (Wraith.spawnAt, Bee.spawn, Mimic.spawnAt); since
    this ad-hoc respawn path bypasses those, we recompute the same formulas
    here using floor_id as the SPD "level"/"depth" value.
    """
    level = floor_id
    if isinstance(mob, TormentedSpirit):
        # TormentedSpirit.adjustStats: ~50% more accuracy/damage than Wraith.
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
        # Ad-hoc combat spawn: not disguised over a guarded item heap.
        mob.disguised = False


def _universal_extra_pool(floor_id: int) -> List[Type[MobEntity]]:
    """Build the "universal extra" mob pool for the ~1% ad-hoc respawn
    branch (see `_process_respawns`). EbonyMimic mirrors SPD's
    `Dungeon.depth > 1` guard on `MimicTooth.ebonyMimicChance`."""
    extras: List[Type[MobEntity]] = [
        TormentedSpirit if random.random() < 0.01 else Wraith,
        Bee,
    ]
    if floor_id > 1:
        extras.append(EbonyMimic)
    return extras


class TickMixin:
    def update_tick(self):
        # Occupancy (and thus open doors / FOV sources) may have changed since
        # the last tick; start each tick with fresh shadowcasting caches.
        self._invalidate_fov_cache()

        # Process buffs on all entities (decrement timers, remove expired)
        dt = 0.05  # assume 20Hz tick
        for player in self.players.values():
            removed = process_buffs(player.buffs, dt)
            if "invisibility" in removed or "shadows" in removed:
                player.invisible = max(0, player.invisible - 1)
        for floor in self.floors.values():
            for mob in floor.mobs.values():
                if mob.is_alive:
                    process_buffs(mob.buffs, dt)

        # Tick foliage blob areas (grant Shadows buff to entities in foliage)
        blob_events = tick_foliage_blobs(self.floors, self.players)
        for ev in blob_events:
            self.add_event(ev["type"], ev["data"])

        # Process any players that died since the last tick (from any source).
        for player in self.players.values():
            if not player.is_alive and not player.death_processed:
                self._kill_player(player, self._get_or_create_floor(player.floor_id), player.floor_id)

        # Keep each player's active_effects list in sync with current state so the
        # client can render the buff indicator (mirrors SPD's BuffIndicator).
        for player in self.players.values():
            self._sync_effects(player)

        for player in self.players.values():
            if player.is_downed or not player.is_alive:
                continue

            if player.move_intent:
                # Held keyboard direction: step at the same cadence as tap-to-path so
                # movement speed is server-authoritative (not tied to OS key-repeat).
                # move_entity no-ops on walls and bump-attacks mobs, so holding into an
                # obstacle is safe.
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
                    # Stop (don't auto-attack/desync) if a live mob physically blocks the
                    # next tile. Travel that leads away from enemies never hits this, so the
                    # player can always walk away even with an enemy right next to them.
                    if any(m.is_alive and m.pos.x == nx and m.pos.y == ny for m in floor.mobs.values()):
                        player.path_queue = []
                    else:
                        player.last_auto_move_time = now
                        self.move_entity(player.id, dx, dy)

            self._apply_heal_tick(player)
            self._apply_room_heal_tick(player)
            self._apply_passive_regen(player)

            # Warrior shield from Broken Seal (artifact slot)
            seal = player.belongings.artifact
            has_seal = seal is not None and getattr(seal, "kind", "") == "broken_seal"
            if player.belongings.armor is not None and has_seal:
                existing = player.get_shield("warrior_shield")
                if existing:
                    existing.amount = min(6, existing.amount + 1)
                else:
                    player.add_shield("warrior_shield", 2, priority=2, decay=600)

            # Armor charge generation (2 per tick, cap 100)
            if player.armor_charge < 100:
                player.armor_charge = min(100, player.armor_charge + 2)

            # Rogue: cloak stealth drain/recharge, Preparation accrual, Momentum
            # decay. `moved` is whether the player stepped this tick.
            moved = bool(player.move_intent or player.path_queue)
            self.tick_rogue(player, dt, moved=moved)

            # Berserk decay (berserk_duration talent slows decay)
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

            # Combo timer decay (slow_combo talent slows decay)
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

            for mob in list(floor.mobs.values()):
                if not mob.is_alive:
                    continue

                # Player-faction summons (Rogue's Shadow Clone) fight FOR the
                # party; they use a separate ally AI, not the hunt-the-player loop.
                if mob.faction == Faction.PLAYER:
                    self._update_shadow_ally(mob, floor, floor_id)
                    continue

                # Goo boss: water-heal, enrage and the pumped-up charge are handled
                # specially. If it consumes the turn (charging/releasing) skip the
                # generic AI; otherwise fall through so it still chases / melees.
                if isinstance(mob, Goo):
                    if self._update_goo(mob, floor, floor_id):
                        continue

                # DwarfKing boss: phase transitions and summon logic.
                # IMMOVABLE phases skip normal movement/chase entirely.
                if isinstance(mob, DwarfKing):
                    self._update_dwarf_king(mob, floor, floor_id)
                    if "IMMOVABLE" in getattr(mob, "properties", []):
                        continue

                # YogDzewa boss: phase transitions, fist spawns, death ray, summons.
                # Always IMMOVABLE — skip generic AI entirely.
                if isinstance(mob, YogDzewa):
                    self._update_yog_dzewa(mob, floor, floor_id)
                    continue

                # DM-300 boss: track fight start (used for AI gating elsewhere);
                # supercharge/pylon activation is now damage-triggered (see
                # DM300.take_damage / _activate_pylon), not proximity-triggered.
                if isinstance(mob, DM300):
                    if not mob.fight_started:
                        target = self._find_nearest_player(mob.pos, floor_id)
                        if target is not None:
                            mob.fight_started = True

                    if mob.supercharged:
                        # DM300.supercharge(): 2x speed, suppress gas/rock
                        # abilities, just chase the hero. Approximate the speed
                        # boost by running the chase/attack step twice.
                        self._update_dm300_chase(mob, floor, floor_id)
                        self._update_dm300_chase(mob, floor, floor_id)
                        continue

                # DemonSpawner: immovable, periodically spawns RipperDemons in
                # adjacent free cells (DemonSpawner.act).
                if isinstance(mob, DemonSpawner):
                    self._update_demon_spawner(mob, floor, floor_id)
                    continue

                # Pylon: immovable, passive+invulnerable until DM-300 activates it,
                # then fires lightning bolts at opposite shock cells each tick.
                if isinstance(mob, Pylon):
                    self._update_pylon(mob, floor, floor_id)
                    continue

                # YogDzewa fist minions: ranged zap attacks (BurningFist etc.)
                # plus per-fist quirks (viscosity release, water regen, teleport).
                if isinstance(mob, (BurningFist, SoiledFist, RottingFist,
                                     RustedFist, BrightFist, DarkFist)):
                    if self._update_yog_fist(mob, floor, floor_id):
                        continue

                target_player = self._find_nearest_player(mob.pos, floor_id)
                # Fleeing mob: run away from nearest player, don't attack
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

                # Stealth/invisibility check: skip players who are invisible
                if target_player and target_player.invisible > 0:
                    # Also check if Shadows buff — if active, mob can't see the player at all
                    target_player = None

                # Sleeping mob detection: only wake if detection check passes
                if target_player and getattr(mob, "never_wakes", False):
                    target_player = None
                elif target_player and getattr(mob, "ai_state", "") in ("idle", "sleeping"):
                    dist = self._get_distance(mob.pos, target_player.pos)
                    stealth = target_player.get_stealth()
                    detect_chance = 1.0 / max(0.01, dist + stealth)
                    # Silent Steps talent: cannot wake sleeping mobs from far away
                    subclass_info = getattr(target_player, "subclass_info", None)
                    if subclass_info:
                        silent_level = subclass_info.talent_info.level("silent_steps")
                        if silent_level > 0 and dist >= 4 - silent_level:
                            detect_chance = 0.0
                    if random.random() >= detect_chance:
                        target_player = None
                    else:
                        mob.ai_state = "hunting"

                # Wandering mob detection: easier to detect
                if target_player and getattr(mob, "ai_state", "") == "wandering":
                    dist = self._get_distance(mob.pos, target_player.pos)
                    stealth = target_player.get_stealth()
                    # Heightened Senses talent boosts stealth vs wandering mobs
                    subclass_info = getattr(target_player, "subclass_info", None)
                    if subclass_info:
                        stealth += subclass_info.talent_info.level("heightened_senses") * 2
                    detect_chance = 1.0 / max(0.01, dist / 2 + stealth)
                    if random.random() >= detect_chance:
                        target_player = None
                    else:
                        mob.ai_state = "hunting"

                # SPD's Goo.notice() (called once Goo is in the hero's FOV) locks
                # the boss room and starts the boss track. The generic wake-up
                # check above is purely distance-based (no LOS), so it can flip
                # Goo to "hunting" from clear across the level — gate the actual
                # "fight start" announcement on mutual visibility so it lines up
                # with the moment the hero can actually see Goo notice them.
                # _is_in_los defaults to shadowcaster.MAX_DISTANCE (20) when no
                # distance is given, which is *not* the hero's rendered sight
                # radius (view_distance, normally 8) — across the open boss
                # arena that let Goo count as "seen" while still off-screen, so
                # the track started the moment the hero stepped into the room.
                # Cap the check at the hero's actual view distance to match what
                # they can see on screen.
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

                # First-strike windup
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

    # ------------------------------------------------------------------
    # Goo boss AI (mirrors SPD Goo.act / doAttack / canAttack)
    # ------------------------------------------------------------------
    def _update_goo(self, goo: Goo, floor: FloorState, floor_id: int) -> bool:
        """Drive Goo's boss-specific behaviour. Returns True when it consumed the
        turn (charging or releasing) so the caller skips the generic chase/melee."""
        self._goo_sync_enrage(goo, floor_id)
        self._goo_water_heal(goo, floor, floor_id)

        target = self._find_nearest_player(goo.pos, floor_id)
        if target is None:
            self._goo_cancel_charge(goo, floor_id)
            return False

        dist = self._get_distance(goo.pos, target.pos)
        charge_ok = dist <= 2 and self._is_in_los(goo.pos, target.pos, floor_id=floor_id)
        now = time.time()

        # Already winding up: hold position and release on the next beat.
        if goo.pumped_up >= 1:
            if not charge_ok:
                self._goo_cancel_charge(goo, floor_id)  # lost the line — resume chase
                return False
            if now - goo.last_attack_time >= goo.attack_cooldown:
                goo.last_attack_time = now
                goo.pumped_up += 1
                if goo.pumped_up >= 2:
                    self._goo_release_charge(goo, target, floor_id)
                    goo.pumped_up = 0
            return True

        # Idle: sometimes begin a charge instead of a normal swing.
        if charge_ok and now - goo.last_attack_time >= goo.attack_cooldown:
            odds = 2 if goo.is_enraged() else 5  # 1/2 enraged, else 1/5 (SPD doAttack)
            if random.randint(0, odds - 1) == 0:
                goo.last_attack_time = now
                goo.pumped_up = 1
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

    def _goo_threatened_tiles(self, goo: Goo, floor_id: int):
        """Cells within charge range (<=2) of Goo with clear line of sight — the
        tiles the telegraphed strike can reach (SPD GooSprite.updateEmitters)."""
        tiles = []
        for dy in range(-2, 3):
            for dx in range(-2, 3):
                if dx == 0 and dy == 0:
                    continue
                if abs(dx) + abs(dy) > 2:
                    continue
                x, y = goo.pos.x + dx, goo.pos.y + dy
                from app.engine.entities.base import Position
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
        # Clear the telegraph regardless of outcome.
        self.add_event("GOO_CHARGE", {"mob": goo.id, "tiles": []}, floor_id=floor_id)
        # Accuracy roll at double attack skill (SPD pumped attack).
        acu = random.random() * goo.attack_skill * 2
        df = random.random() * target.get_effective_defense_skill()
        if acu < df:
            self.add_event("ATTACK", {"source": goo.id, "target": target.id,
                                      "damage": 0, "surprise": False}, floor_id=floor_id)
            self.add_event("MISS", {"source": goo.id, "target": target.id,
                                    "defense_verb": target.defense_verb}, floor_id=floor_id)
            return
        # 3x damage burst (SPD Goo.damageRoll pumped branch).
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
            goo.attack_proc(target)  # ooze can still apply on the pumped hit
        # Player death (grave drop + DEATH event) is finalised by the tick's
        # _kill_player pass next tick, so we don't emit a DEATH event here.

    # ------------------------------------------------------------------
    # DwarfKing boss AI (mirrors DwarfKing.java phases / summon logic)
    # ------------------------------------------------------------------
    def _update_dwarf_king(self, dk: DwarfKing, floor: FloorState, floor_id: int):
        """Drive DwarfKing's phase transitions and minion summons."""
        # Fight start detection
        if not dk.fight_started:
            target = self._find_nearest_player(dk.pos, floor_id)
            if target is not None:
                dk.fight_started = True
                self.add_event("DWARF_KING_FIGHT_STARTED", {"mob": dk.id}, floor_id=floor_id)
            return

        # Phase 2: become IMMOVABLE at 200 HP
        if dk.phase == 1 and dk.hp <= 200:
            dk.phase = 2
            # Runtime property mutation — DK becomes immovable in phase 2 (SPD DwarfKing.restoreFromBundle pattern)
            if "IMMOVABLE" not in dk.properties:
                dk.properties.append("IMMOVABLE")
            self.add_event("DWARF_KING_PHASE2", {"mob": dk.id}, floor_id=floor_id)

        # Phase 3: continuous summons at 100 HP
        if dk.phase == 2 and dk.hp <= 100:
            dk.phase = 3
            self.add_event("DWARF_KING_PHASE3", {"mob": dk.id}, floor_id=floor_id)

        # Summon cooldown
        if dk.summon_cooldown > 0:
            dk.summon_cooldown -= 1
            return

        # Determine minion type: every 4th is monk or warlock, rest are ghouls
        # Every 4th summon is elite (DKMonk or DKWarlock), per DwarfKing.java non-challenge logic
        if dk.summons_made % 4 == 3:
            cls = DKMonk if random.randint(0, 1) == 0 else DKWarlock
        else:
            cls = DKGhoul

        # Find a free summon spot
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
            return  # all spots blocked, try again next tick

        # DKGhoul pair mechanic: spawn a second ghoul and life-link them
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

        # Cooldown: phase 3 is rapid (3-5 ticks), otherwise normal (10-14)
        if dk.phase == 3:
            dk.summon_cooldown = random.randint(3, 5)
        else:
            dk.summon_cooldown = random.randint(10, 14)

    # ------------------------------------------------------------------
    # YogDzewa boss AI (mirrors YogDzewa.java phases / fist/summon logic)
    # ------------------------------------------------------------------
    def _update_yog_dzewa(self, yog: YogDzewa, floor: FloorState, floor_id: int):
        """Drive YogDzewa's phase transitions, fist spawns, death ray and summons."""

        # Fight start: triggered when any player comes within 12 tiles.
        if not yog.fight_started:
            target = self._find_nearest_player(yog.pos, floor_id)
            if target is not None and self._get_distance(yog.pos, target.pos) <= 12:
                yog.fight_started = True
                yog.phase = 1
                # Build random fist order: one from each pair, then shuffle.
                pair_a = random.choice(["BurningFist", "SoiledFist"])
                pair_b = random.choice(["RottingFist", "RustedFist"])
                pair_c = random.choice(["BrightFist", "DarkFist"])
                fist_order = [pair_a, pair_b, pair_c]
                random.shuffle(fist_order)
                yog.fist_order = fist_order
                self.add_event("YOG_FIGHT_STARTED", {"mob": yog.id}, floor_id=floor_id)
            return

        # Collect alive fists registered to this Yog.
        alive_fists = [m for m in floor.mobs.values()
                       if m.id in yog.fist_ids and m.is_alive]

        # HP floor per phase: Yog can't drop below this while the phase's fist
        # is still alive (phases 1-3 also trigger a transition + fist spawn;
        # phase 4's floor just holds Yog at 100 until the last fist dies).
        HP_FLOORS = {1: 700, 2: 400, 3: 100, 4: 100}

        # Phase transitions at HP thresholds — each spawns the next fist.
        if yog.phase in (1, 2, 3) and yog.hp <= HP_FLOORS[yog.phase]:
            # Enforce HP floor so Yog can't drop below threshold while fist lives.
            yog.hp = HP_FLOORS[yog.phase]
            # Spawn next fist from the pre-shuffled order.
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
            self.add_event("YOG_PHASE_CHANGE", {"mob": yog.id, "phase": yog.phase},
                           floor_id=floor_id)

        # Phase 4 → 5: all fists dead — Yog is now fully vulnerable.
        if yog.phase == 4 and len(alive_fists) == 0:
            yog.phase = 5
            self.add_event("YOG_FINAL_PHASE", {"mob": yog.id}, floor_id=floor_id)

        # HP floor while fists remain (phases 1-4): Yog can't die yet.
        if yog.phase < 5 and yog.hp < HP_FLOORS[yog.phase]:
            yog.hp = HP_FLOORS[yog.phase]

        # No target → do nothing else.
        target = self._find_nearest_player(yog.pos, floor_id)
        if target is None:
            return

        # ------------------------------------------------------------------
        # Death ray (ability)
        # ------------------------------------------------------------------
        if yog.ability_cooldown > 0:
            yog.ability_cooldown -= 1
        else:
            beams = max(1, 1 + (yog.max_hp - yog.hp) // 400)
            for _ in range(beams):
                # Infinite accuracy vs player defense (mirrors Java INFINITE_ACCURACY)
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

        # ------------------------------------------------------------------
        # Minion summons
        # ------------------------------------------------------------------
        if yog.summon_cooldown > 0:
            yog.summon_cooldown -= 1
        else:
            # Find free neighbor tile nearest to the target player.
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

    # ------------------------------------------------------------------
    # YogDzewa fist minions (mirrors YogFist.java's ranged-attack dispatch
    # plus per-fist quirks). Terrain mutation systems (Blob/Fire/ToxicGas/
    # grass-spread) are not ported -- simplifications are noted per-fist.
    # ------------------------------------------------------------------
    def _update_yog_fist(self, fist, floor: FloorState, floor_id: int) -> bool:
        # YogFist.act(): rangedCooldown ticks down each turn (no paralysis
        # field on these mobs, so always decrement).
        if fist.ranged_cooldown > 0:
            fist.ranged_cooldown -= 1

        # RustedFist: release deferred (viscosity) damage gradually, 10% per
        # tick (minimum 1 while stacks remain). Direct hp manipulation --
        # take_damage would re-defer it.
        if isinstance(fist, RustedFist) and fist.viscosity_stacks > 0:
            released = max(1, fist.viscosity_stacks // 10)
            released = min(released, fist.viscosity_stacks)
            fist.hp = max(0, fist.hp - released)
            fist.viscosity_stacks -= released
            if fist.hp <= 0:
                fist.is_alive = False
                fist.die(floor_mobs=floor.mobs, tile_x=fist.pos.x, tile_y=fist.pos.y,
                         players=self._players_on_floor(floor_id))

        # RottingFist: regen HP/50 per tick while standing in water (mirrors
        # RottingFist.act's `if (Dungeon.level.water[pos] && HP < HT)`).
        if isinstance(fist, RottingFist) and fist.is_alive:
            if floor.grid[fist.pos.y][fist.pos.x] == TileType.FLOOR_WATER and fist.hp < fist.max_hp:
                fist.hp = min(fist.max_hp, fist.hp + fist.max_hp // 50)

        # BrightFist/DarkFist: handle a pending post-damage teleport before
        # acting this tick (mirrors the teleport triggered in damage()).
        if isinstance(fist, (BrightFist, DarkFist)) and getattr(fist, "pending_teleport", False):
            self._yog_fist_teleport(fist, floor, floor_id)

        if not fist.is_alive:
            return True

        target = self._find_nearest_player(fist.pos, floor_id)
        if target is None:
            return False

        dist = self._get_distance(fist.pos, target.pos)

        # BrightFist/DarkFist: canRangedInMelee = False -- always zap, never
        # melee. If no LOS, fall through to generic chase AI to close in.
        if isinstance(fist, (BrightFist, DarkFist)):
            if self._is_in_los(fist.pos, target.pos, floor_id=floor_id):
                if isinstance(fist, BrightFist):
                    self._fist_zap_bright(fist, target, floor_id)
                else:
                    self._fist_zap_dark(fist, target, floor_id)
                return True
            return False

        # Other 4 fists: ranged zap when not adjacent, on cooldown==0, and in
        # LOS; otherwise fall through to generic melee/chase AI.
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
        """BrightFist/DarkFist post-damage teleport (SPD: teleport self away,
        apply a stronger Blindness to the hero, state -> WANDERING)."""
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

    def _fist_zap_burning(self, fist: "BurningFist", target, floor_id: int):
        """BurningFist.zap(): hit-roll; on hit, apply fire damage and
        (re)ignite Burning. (Java also evaporates water / ignites fire blobs
        around the target -- terrain mutation, out of scope.)"""
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

    def _fist_zap_soiled(self, fist: "SoiledFist", target, floor_id: int):
        """SoiledFist.zap(): hit-roll; on hit, root the target (no direct
        damage). (Java also spreads grass around the target -- out of scope.)"""
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

    def _fist_zap_rotting(self, fist: "RottingFist", target, floor_id: int):
        """RottingFist.zap(): seeds a ToxicGas blob on the target (Blob system
        not ported -- approximated as direct gas damage), with a 50% chance of
        applying Ooze on hit (mirrors RottingFist.attackProc)."""
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

    def _fist_zap_rusted(self, fist: "RustedFist", target, floor_id: int):
        """RustedFist.zap(): hit-roll; on hit, apply Cripple (no direct
        damage)."""
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

    def _fist_zap_bright(self, fist: "BrightFist", target, floor_id: int):
        """BrightFist.zap(): hit-roll; on hit, LightBeam damage + Blindness."""
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

    def _fist_zap_dark(self, fist: "DarkFist", target, floor_id: int):
        """DarkFist.zap(): hit-roll; on hit, DarkBolt damage. Java also weakens
        the hero's Light buff -- Light isn't ported, so simplified to the same
        Blindness debuff as BrightFist's zap."""
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

    # ------------------------------------------------------------------
    # DemonSpawner (mirrors DemonSpawner.act -- immovable miniboss that
    # periodically spawns RipperDemons in adjacent free cells).
    # ------------------------------------------------------------------
    def _update_demon_spawner(self, spawner: DemonSpawner, floor: FloorState, floor_id: int):
        spawner.spawn_cooldown -= 1
        if spawner.spawn_cooldown > 0:
            return

        # Java: clamp BEFORE searching for candidates so a spawner with no
        # free neighbours doesn't endlessly accumulate negative cooldown.
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

    # ------------------------------------------------------------------
    # Pylon (mirrors Pylon.act -- inactive/passive/invulnerable until
    # activated by DM-300; then fires lightning at opposite shock cells
    # every tick).
    # ------------------------------------------------------------------
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

    # ------------------------------------------------------------------
    # DM-300 supercharge / pylon activation (CavesBossLevel.activatePylon).
    # ------------------------------------------------------------------
    def _activate_pylon(self, floor: FloorState, floor_id: int, near_pos: Optional[Position] = None):
        """Activate one currently-inactive Pylon. If more than one remains,
        the one closest to `near_pos` is excluded from the random pool
        (CavesBossLevel.activatePylon)."""
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

    # ------------------------------------------------------------------
    # DM-300 supercharged chase (DM300.supercharge() AI: 2x speed, just
    # chase the hero, gas/rock abilities suppressed).
    # ------------------------------------------------------------------
    def _update_dm300_chase(self, mob: "DM300", floor: FloorState, floor_id: int):
        target_player = self._find_nearest_player(mob.pos, floor_id)
        if target_player is None:
            return

        dist = self._get_distance(mob.pos, target_player.pos)
        atk_range = getattr(mob, "attack_range", 1)

        if dist <= atk_range:
            current_time = time.time()
            if current_time - mob.last_attack_time >= mob.attack_cooldown:
                dx, dy = target_player.pos.x - mob.pos.x, target_player.pos.y - mob.pos.y
                self.move_entity(mob.id, dx, dy)
        elif self._is_in_los(mob.pos, target_player.pos, floor_id=floor_id):
            step = self._get_next_step_to(mob.pos, target_player.pos, floor_id=floor_id)
            if step:
                self.move_entity(mob.id, step[0], step[1])

    def _update_shadow_ally(self, ally, floor: FloorState, floor_id: int):
        # Shadow Clone AI: attack the nearest enemy mob in sight, else regroup
        # on its owner. Paced at the player step cadence so it doesn't zoom.
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
                # Adjacent: bump-attack (move_entity resolves the ally->enemy hit).
                ally.last_attack_time = now - ally.attack_cooldown
                adx = (target.pos.x > ally.pos.x) - (target.pos.x < ally.pos.x)
                ady = (target.pos.y > ally.pos.y) - (target.pos.y < ally.pos.y)
                self.move_entity(ally.id, adx, ady)
            else:
                step = self._get_next_step_to(ally.pos, target.pos, floor_id=floor_id)
                if step:
                    self.move_entity(ally.id, step[0], step[1])
            return

        # No enemy: follow the owner.
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

            # Caustic ooze: ~1 dmg per in-game turn, washed off by stepping into
            # water (SPD Ooze.act). Throttled so it ticks once per "turn".
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
                        # Boss key + loot must drop even on a bleed kill, else the
                        # sealed arena exit can never be opened.
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
        # --- Intentional fidelity divergence ---------------------------------
        # Wraith/TormentedSpirit, Bee, and EbonyMimic are normally only spawned
        # via systems this port doesn't implement (haunted cursed-item heaps,
        # MagicalHoneyPot, MimicTooth trinket respectively), so they would
        # otherwise never appear in-game. To make them reachable, give the
        # regular respawn roll a small (~1%) chance to produce one of these
        # "universal extra" mobs instead of picking from the region rotation.
        # This is a deliberate product decision, not a faithful SPD mechanic.
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
        existing = {e.key: e for e in player.active_effects}
        effects = []
        if player.heal_left > 0:
            prev = existing.get("regen")
            duration = max(prev.duration if prev else 0.0, player.heal_left)
            effects.append(Effect(
                key="regen", name="Healing", icon=44,
                remaining=player.heal_left, duration=duration,
            ))
        if player.berserk_active:
            effects.append(Effect(
                key="berserk", name="Berserk", icon=13,
                remaining=player.berserk_power, duration=1.0,
            ))
        from app.engine.entities.buffs import has_buff
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
        # Mirrors Healing.act() from the original game: heal a decaying chunk of the
        # remaining pool each application, emitting a HEAL event for the floating
        # number + sparkle particles on the client.
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

    def _apply_room_heal_tick(self, player: Player):
        # Passive sanctuary healing: standing in a floor's entrance (up-stairs) room
        # restores ROOM_HEAL_AMOUNT HP per second, reusing the same green HEAL event
        # as health potions for the floating number + sparkles on the client.
        floor = self.floors.get(player.floor_id)
        if floor is None or not floor.rooms:
            return

        if not self._is_in_entrance_room(floor, player.pos.x, player.pos.y):
            player.room_heal_cooldown = 0  # next heal fires immediately on re-entry
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

    # SPD hunger thresholds (scaled from turn-based to real-time at 20 Hz)
    _HUNGER_RATE = 1.0 / 20.0   # hunger units per tick (≈1 unit/s; full→starving ~450s)
    _HUNGER_HUNGRY = 300.0
    _HUNGER_STARVING = 450.0

    def _apply_hunger_tick(self, player: Player):
        if player.is_downed:
            return
        player.hunger = min(self._HUNGER_STARVING + 50, player.hunger + self._HUNGER_RATE)
        if player.hunger >= self._HUNGER_STARVING:
            dmg = max(1, player.max_hp // 100)
            player.hp -= dmg
            if player.hp <= 0:
                player.hp = 0
                player.is_downed = True

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
