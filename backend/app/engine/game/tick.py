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
from app.engine.entities.mobs import Rat, Goo
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

                # Goo boss: water-heal, enrage and the pumped-up charge are handled
                # specially. If it consumes the turn (charging/releasing) skip the
                # generic AI; otherwise fall through so it still chases / melees.
                if isinstance(mob, Goo):
                    if self._update_goo(mob, floor, floor_id):
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
        if floor_id <= SEWERS_MAX_FLOOR:
            rotation = self._get_sewers_rotation(floor_id)
        elif floor_id <= PRISON_MAX_FLOOR:
            rotation = self._get_prison_rotation(floor_id)
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
