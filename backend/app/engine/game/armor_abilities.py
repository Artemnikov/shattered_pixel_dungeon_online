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
import math
import random
import uuid
from typing import Optional

from app.engine.dungeon.generator import TileType
from app.engine.entities.base import Faction, Mob, Player, Position
from app.engine.entities.buffs import add_buff
from app.engine.entities.subclasses import ArmorAbilityType, COST_ARMOR_ABILITY, COST_ENDURE, Talent
from app.engine.systems.combat import resolve_melee_attack

# Rogue armor ability charge costs (SPD baseChargeUse).
COST_SMOKE_BOMB = 50
COST_DEATH_MARK = 25
COST_SHADOW_CLONE = 35


class ArmorAbilitiesMixin:
    def use_armor_ability(self, player_id: str, ability: str, target_x: Optional[int] = None, target_y: Optional[int] = None) -> None:
        player = self.players.get(player_id)
        if not player or player.is_downed or not player.is_alive:
            return

        floor_id = player.floor_id
        floor = self._get_or_create_floor(floor_id)

        if ability == ArmorAbilityType.HEROIC_LEAP:
            if player.armor_charge < COST_ARMOR_ABILITY:
                return
            if target_x is None or target_y is None:
                return
            if not (0 <= target_x < floor.width and 0 <= target_y < floor.height):
                return
            if floor.grid[target_y][target_x] == TileType.WALL:
                return
            dx = target_x - player.pos.x
            dy = target_y - player.pos.y
            dist = max(abs(dx), abs(dy))
            if dist < 1 or dist > 4:
                return
            player.armor_charge -= COST_ARMOR_ABILITY
            player.pos.x = target_x
            player.pos.y = target_y
            self._invalidate_fov_cache()
            self.add_event("MOVE", {"entity": player.id, "x": target_x, "y": target_y}, floor_id=floor_id)
            self.add_event("PLAY_SOUND", {"sound": "HIT_STRONG"}, floor_id=floor_id, source_player_id=player.id)
            for dy_off in (-1, 0, 1):
                for dx_off in (-1, 0, 1):
                    if dx_off == 0 and dy_off == 0:
                        continue
                    cx, cy = target_x + dx_off, target_y + dy_off
                    if not (0 <= cx < floor.width and 0 <= cy < floor.height):
                        continue
                    for mob in list(floor.mobs.values()):
                        if mob.is_alive and mob.pos.x == cx and mob.pos.y == cy:
                            dmg = random.randint(2 + player.level, 6 + player.level * 2)
                            mob.hp -= dmg
                            self.add_event("DAMAGE", {"target": mob.id, "amount": dmg}, floor_id=floor_id)
                            if not mob.is_alive:
                                self.add_event("DEATH", {"target": mob.id}, floor_id=floor_id)

        elif ability == ArmorAbilityType.SHOCKWAVE:
            if player.armor_charge < COST_ARMOR_ABILITY:
                return
            player.armor_charge -= COST_ARMOR_ABILITY
            self.add_event("PLAY_SOUND", {"sound": "HIT_STRONG"}, floor_id=floor_id, source_player_id=player.id)
            for dy_off in (-1, 0, 1):
                for dx_off in (-1, 0, 1):
                    if dx_off == 0 and dy_off == 0:
                        continue
                    cx, cy = player.pos.x + dx_off, player.pos.y + dy_off
                    if not (0 <= cx < floor.width and 0 <= cy < floor.height):
                        continue
                    for mob in list(floor.mobs.values()):
                        if mob.is_alive and mob.pos.x == cx and mob.pos.y == cy:
                            dmg = random.randint(1 + player.level, 4 + player.level * 2)
                            knock_x = cx + (cx - player.pos.x)
                            knock_y = cy + (cy - player.pos.y)
                            if 0 <= knock_x < floor.width and 0 <= knock_y < floor.height and floor.grid[knock_y][knock_x] != TileType.WALL:
                                mob.pos.x = knock_x
                                mob.pos.y = knock_y
                            mob.hp -= dmg
                            self.add_event("DAMAGE", {"target": mob.id, "amount": dmg}, floor_id=floor_id)
                            if not mob.is_alive:
                                self.add_event("DEATH", {"target": mob.id}, floor_id=floor_id)

        elif ability == ArmorAbilityType.ENDURE:
            if player.armor_charge < COST_ENDURE:
                return
            player.armor_charge -= COST_ENDURE
            add_buff(player.buffs, "endure", duration=5.0, level=1)
            self.add_event("PLAY_SOUND", {"sound": "HIT_STRONG"}, floor_id=floor_id, source_player_id=player.id)

        elif ability == ArmorAbilityType.SMOKE_BOMB:
            self._ability_smoke_bomb(player, floor, floor_id, target_x, target_y)

        elif ability == ArmorAbilityType.DEATH_MARK:
            self._ability_death_mark(player, floor, floor_id, target_x, target_y)

        elif ability == ArmorAbilityType.SHADOW_CLONE:
            self._ability_shadow_clone(player, floor, floor_id, target_x, target_y)

    # --- Rogue abilities ---------------------------------------------------
    def _ability_smoke_bomb(self, player, floor, floor_id, target_x, target_y) -> None:
        # Blink up to 6 tiles in line-of-sight, blinding adjacent foes. Free-ish
        # for an invisible hero with Shadow Step. Mirrors SPD's SmokeBomb.
        if target_x is None or target_y is None:
            return
        if not (0 <= target_x < floor.width and 0 <= target_y < floor.height):
            return
        if floor.grid[target_y][target_x] == TileType.WALL:
            return
        dist = max(abs(target_x - player.pos.x), abs(target_y - player.pos.y))
        if dist < 1 or dist > 6:
            return
        if any(m.is_alive and m.pos.x == target_x and m.pos.y == target_y for m in floor.mobs.values()):
            return

        shadow_step = player.invisible > 0 and player.talent_info.has(Talent.SHADOW_STEP)
        cost = COST_SMOKE_BOMB
        if shadow_step:
            cost = int(cost * (0.84 ** player.talent_info.level(Talent.SHADOW_STEP)))
        if player.armor_charge < cost:
            return
        player.armor_charge -= cost

        player.pos.x, player.pos.y = target_x, target_y
        self._invalidate_fov_cache()
        self.add_event("MOVE", {"entity": player.id, "x": target_x, "y": target_y}, floor_id=floor_id)
        self.add_event("PLAY_SOUND", {"sound": "PUFF"}, floor_id=floor_id, source_player_id=player.id)

        if not shadow_step:
            for mob in list(floor.mobs.values()):
                if not mob.is_alive or mob.faction == Faction.PLAYER:
                    continue
                if max(abs(mob.pos.x - target_x), abs(mob.pos.y - target_y)) <= 1:
                    add_buff(mob.buffs, "blinded", duration=5.0, level=1)
                    if getattr(mob, "ai_state", "") == "hunting":
                        mob.ai_state = "wandering"
            if player.talent_info.has(Talent.HASTY_RETREAT):
                dur = 1.0 + player.talent_info.level(Talent.HASTY_RETREAT)
                add_buff(player.buffs, "haste", duration=dur, level=1)
                player.add_buff("invisibility", duration=dur, level=1)

    def _ability_death_mark(self, player, floor, floor_id, target_x, target_y) -> None:
        # Mark a visible enemy: it takes +25% damage and, if slain while marked,
        # triggers Deathly Durability / Fear the Reaper talents.
        if target_x is None or target_y is None:
            return
        target = next((m for m in floor.mobs.values()
                       if m.is_alive and m.faction != Faction.PLAYER
                       and m.pos.x == target_x and m.pos.y == target_y), None)
        if target is None:
            return
        if not self._is_in_los(player.pos, target.pos, floor_id=floor_id):
            return

        # Double Mark: every other cast is free (and otherwise cheaper).
        double = player.talent_info.has(Talent.DOUBLE_MARK)
        cost = COST_DEATH_MARK
        if double and player.get_buff("double_mark_ready"):
            cost = 0
            player.remove_buff("double_mark_ready")
        elif double:
            cost = int(cost * (0.707 ** player.talent_info.level(Talent.DOUBLE_MARK)))
        if player.armor_charge < cost:
            return
        player.armor_charge -= cost
        if double and not player.get_buff("double_mark_ready"):
            player.add_buff("double_mark_ready", duration=999.0, level=1)

        add_buff(target.buffs, "death_mark", duration=5.0, level=1, source_id=player.id)
        self.add_event("DEATH_MARK", {"player": player.id, "target": target.id}, floor_id=floor_id, source_player_id=player.id)
        self.add_event("PLAY_SOUND", {"sound": "MELD"}, floor_id=floor_id, source_player_id=player.id)

    def _ability_shadow_clone(self, player, floor, floor_id, target_x, target_y) -> None:
        # Summon a shadow ally beside the hero. It fights nearby enemies; its HP
        # and combat scale with the Shadow Clone talents (see tick ally AI).
        if player.armor_charge < COST_SHADOW_CLONE:
            return
        spawn = None
        for ddx, ddy in ((0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (1, -1), (-1, 1), (-1, -1)):
            cx, cy = player.pos.x + ddx, player.pos.y + ddy
            if not (0 <= cx < floor.width and 0 <= cy < floor.height):
                continue
            if not floor.flags or not floor.flags.passable[cy][cx]:
                continue
            if any(m.is_alive and m.pos.x == cx and m.pos.y == cy for m in floor.mobs.values()):
                continue
            spawn = (cx, cy)
            break
        if spawn is None:
            return
        player.armor_charge -= COST_SHADOW_CLONE

        perfect_copy = player.talent_info.level(Talent.PERFECT_COPY)
        hp = 80 + round(0.1 * perfect_copy * (15 + 5 * player.level))
        clone = Mob(
            id=f"shadow_clone_{uuid.uuid4().hex[:8]}",
            name="Shadow Clone",
            type="shadow_clone",
            pos=Position(x=spawn[0], y=spawn[1]),
            hp=hp, max_hp=hp,
            attack=10, defense=player.level + 4,
            defense_skill=player.level + 4,
            dr_min=0, dr_max=2,
            attack_cooldown=1.0,
            faction=Faction.PLAYER,
        )
        clone.owner_id = player.id
        floor.mobs[clone.id] = clone
        self.add_event("PLAY_SOUND", {"sound": "PUFF"}, floor_id=floor_id, source_player_id=player.id)
        self.add_event("SHADOW_CLONE", {"player": player.id, "clone": clone.id, "x": spawn[0], "y": spawn[1]}, floor_id=floor_id)
