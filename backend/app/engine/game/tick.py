"""The per-tick game loop for GameInstance.

Advances death processing, buff sync, player auto-movement, healing/regen,
status effects (bleed/ooze), mob respawns, and difficulty-scaled mob AI.
"""

import random
import time
from typing import List

from app.engine.dungeon.generator import TileType
from app.engine.entities.base import Difficulty, Effect, Faction, Player
from app.engine.entities.buffs import process_buffs
from app.engine.game.blobs import tick_foliage_blobs
from app.engine.entities.mobs import Rat
from app.engine.game.constants import (
    AUTO_MOVE_INTERVAL,
    HEAL_TICK_INTERVAL,
    NO_RESPAWN_FLOORS,
    PASSIVE_REGEN_INTERVAL,
    RESPAWN_TURNS,
    ROOM_HEAL_AMOUNT,
)
from app.engine.game.floor_state import FloorState


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

                target_player = self._find_nearest_player(mob.pos, floor_id)
                # Stealth/invisibility check: skip players who are invisible
                if target_player and target_player.invisible > 0:
                    # Also check if Shadows buff — if active, mob can't see the player at all
                    target_player = None

                # Sleeping mob detection: only wake if detection check passes
                if target_player and getattr(mob, "ai_state", "") in ("idle", "sleeping"):
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
        for player in active_players:
            if player.bleed_turns > 0 and player.bleed_amount > 0:
                dmg = player.bleed_amount
                player.take_damage(dmg)
                self.add_event("DAMAGE", {"target": player.id, "amount": dmg, "bleed": True}, floor_id=floor_id)
                player.bleed_turns -= 1
                if player.bleed_turns <= 0:
                    player.bleed_amount = 0

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
                        self.add_event("DEATH", {"target": mob.id}, floor_id=floor_id)
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
