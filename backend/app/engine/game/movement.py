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
"""Movement and combat for GameInstance.

Handles held-direction intent, stepping (with bump-attacks, pickups, door
unlocking, traps and stair traversal) and ranged/thrown/wand attacks.
"""

import random
import time
from typing import Optional

from app.engine.dungeon.generator import TileType
from app.engine.entities.base import (
    Dewdrop,
    Faction,
    Gold,
    Mob as MobEntity,
    Player,
    Position,
    RevivingPotion,
    Throwable,
    Wand,
    Waterskin,
    Weapon,
)
from app.engine.entities.mobs import DM300
from app.engine.systems.combat import resolve_melee_attack, resolve_ranged_attack
from app.engine.systems.loot import roll_drops
from app.engine.game.constants import MAX_FLOOR_ID
from app.engine.game.terrain_effects import press_cell


class MovementCombatMixin:
    def set_move_intent(self, entity_id: str, dx: int, dy: int):
        """Set/clear a player's held keyboard direction. The update tick paces the
        actual stepping at AUTO_MOVE_INTERVAL."""
        player = self.players.get(entity_id)
        if player is None:
            return
        if dx == 0 and dy == 0:
            player.move_intent = None
            return
        was_moving = player.move_intent is not None
        player.move_intent = (dx, dy)
        player.path_queue = []
        # Grant an immediate first step only when starting from rest. Changing
        # direction mid-walk keeps the existing cadence, so rapidly switching keys
        # (e.g. the two keydowns that begin a diagonal) can't burst multiple steps
        # inside one AUTO_MOVE_INTERVAL.
        if not was_moving:
            player.last_auto_move_time = 0.0

    def move_entity(self, entity_id: str, dx: int, dy: int):
        floor_id, entity = self._get_floor_for_entity(entity_id)
        if entity is None or floor_id is None:
            return

        floor = self._get_or_create_floor(floor_id)

        if isinstance(entity, Player) and entity.is_downed:
            return

        new_x = entity.pos.x + dx
        new_y = entity.pos.y + dy

        if not (0 <= new_x < floor.width and 0 <= new_y < floor.height):
            return

        # Diagonal moves past a wall corner are allowed, matching SPD's PathFinder
        # (it only checks the destination cell's passability, not the orthogonal cells).

        target_entity = None
        for p in self._players_on_floor(floor_id):
            if p.id != entity_id and p.is_alive and p.pos.x == new_x and p.pos.y == new_y:
                target_entity = p
                break

        if not target_entity:
            for m in floor.mobs.values():
                if m.id != entity_id and m.is_alive and m.pos.x == new_x and m.pos.y == new_y:
                    target_entity = m
                    break

        if target_entity:
            if (
                isinstance(entity, Player)
                and isinstance(target_entity, Player)
                and target_entity.is_downed
                and entity.faction == target_entity.faction
            ):
                revive_potion_idx = next(
                    (i for i, item in enumerate(entity.inventory) if isinstance(item, RevivingPotion)),
                    -1,
                )
                if revive_potion_idx != -1:
                    entity.inventory.pop(revive_potion_idx)
                    target_entity.is_downed = False
                    target_entity.hp = target_entity.get_total_max_hp() // 2
                    self.add_event("REVIVE", {"target": target_entity.id, "source": entity.id}, floor_id=floor_id)
                    return

            if entity.faction != target_entity.faction:
                if isinstance(entity, Player) and entity.is_downed:
                    return

                current_time = time.time()
                cooldown = entity.attack_cooldown
                if isinstance(entity, Player) and entity.equipped_weapon:
                    cooldown = entity.equipped_weapon.attack_cooldown

                if current_time - entity.last_attack_time < cooldown:
                    return

                entity.last_attack_time = current_time

                if isinstance(entity, Player):
                    entity._last_action = ""
                result = resolve_melee_attack(
                    entity, target_entity,
                    floor.mobs, entity.pos.x, entity.pos.y,
                    is_in_los=lambda a, b: self._is_in_los(a, b, floor_id=floor_id),
                )
                if result["missed"]:
                    self.add_event("MISS", {"source": entity.id, "target": target_entity.id, "defense_verb": result.get("defense_verb", "dodged")}, floor_id=floor_id)
                    self.add_event("ATTACK", {"source": entity.id, "target": target_entity.id, "damage": 0, "surprise": False}, floor_id=floor_id)
                    return
                dmg = result["damage"]
                self.add_event("ATTACK", {
                    "source": entity.id,
                    "target": target_entity.id,
                    "damage": dmg,
                    "surprise": result["surprise"],
                    "crit": result.get("crit", False),
                    "grim_proc": result.get("grim_proc", False),
                }, floor_id=floor_id)
                if isinstance(entity, Player):
                    sound = "HIT_STRONG" if result.get("crit") else "HIT_SLASH"
                    self.add_event("PLAY_SOUND", {"sound": sound}, floor_id=floor_id, source_player_id=entity.id)
                if dmg > 0:
                    self.add_event("DAMAGE", {
                        "target": target_entity.id,
                        "amount": dmg,
                        "grim_proc": result.get("grim_proc", False),
                    }, floor_id=floor_id)
                    if result.get("grim_proc"):
                        self.add_event("PLAY_SOUND", {"sound": "HIT_STRONG"}, floor_id=floor_id, source_player_id=entity.id)
                    if isinstance(target_entity, Player):
                        self.add_event("PLAY_SOUND", {"sound": "HIT_BODY"}, floor_id=floor_id, source_player_id=target_entity.id)
                        if target_entity.hp / target_entity.get_total_max_hp() <= 0.3:
                            self.add_event("PLAY_SOUND", {"sound": "HEALTH_WARN"}, player_id=target_entity.id)

                self._maybe_trigger_dm300_supercharge(target_entity, floor, floor_id, entity.pos)

                # Warrior subclass: combo / berserk events after successful damage
                if isinstance(entity, Player) and dmg > 0:
                    if entity.subclass_info.subclass == "gladiator":
                        self.add_event("COMBO_UPDATE", {"player": entity.id, "count": entity.combo_count}, floor_id=floor_id, source_player_id=entity.id)
                        if entity.combo_count in (2, 4, 6, 8, 10):
                            moves = {2: "clobber", 4: "slam", 6: "parry", 8: "crush", 10: "fury"}
                            self.add_event("COMBO_MOVE_UNLOCKED", {"player": entity.id, "move": moves[entity.combo_count]}, floor_id=floor_id, source_player_id=entity.id)
                    if entity.subclass_info.subclass == "berserker":
                        self.add_event("RAGE_CHANGED", {"player": entity.id, "power": entity.berserk_power}, floor_id=floor_id, source_player_id=entity.id)

                if not target_entity.is_alive:
                    if isinstance(target_entity, MobEntity):
                        self.process_death_mark_kill(entity, target_entity, floor, floor_id)
                        self.handle_mob_death(target_entity, floor, floor_id)
                    if isinstance(entity, Player):
                        self.on_kill(entity, target_entity, floor.mobs, floor_id)
                    self.add_event("DEATH", {"target": target_entity.id}, floor_id=floor_id)
                    if isinstance(target_entity, MobEntity):
                        target_entity.die(
                            attacker=entity,
                            floor_mobs=floor.mobs,
                            tile_x=target_entity.pos.x,
                            tile_y=target_entity.pos.y,
                            players=list(self._players_on_floor(floor_id)),
                        )
                    if isinstance(entity, Player) and isinstance(target_entity, MobEntity):
                        if entity.earn_exp(target_entity.exp):
                            self.on_talent_level_up(entity)
                        drops = roll_drops(target_entity, self.drop_counters, target_entity.pos.x, target_entity.pos.y)
                        for item in drops:
                            floor.items[item.id] = item
            return

        tile = floor.grid[new_y][new_x]
        if tile == TileType.LOCKED_DOOR:
            if not isinstance(entity, Player):
                return
            if not self._try_unlock_locked_door(entity, floor, new_x, new_y):
                return
            tile = floor.grid[new_y][new_x]

        if not floor.flags or not floor.flags.passable[new_y][new_x]:
            return

        if not isinstance(entity, Player) and self._is_in_safe_room(floor, new_x, new_y):
            return

        old_x, old_y = entity.pos.x, entity.pos.y
        entity.move(dx, dy)

        # Door enter/leave tile mutation: stepping onto a closed DOOR opens it;
        # leaving an open door closes it (if no other entity is on it).
        door_changed = False
        if floor.grid[entity.pos.y][entity.pos.x] == TileType.DOOR:
            floor.grid[entity.pos.y][entity.pos.x] = TileType.OPEN_DOOR
            door_changed = True
        if floor.grid[old_y][old_x] == TileType.OPEN_DOOR:
            has_entity = any(
                p.pos.x == old_x and p.pos.y == old_y
                for p in self._players_on_floor(floor_id)
            )
            if not has_entity:
                has_entity = any(
                    m.is_alive and m.pos.x == old_x and m.pos.y == old_y
                    for m in floor.mobs.values()
                )
            if not has_entity:
                floor.grid[old_y][old_x] = TileType.DOOR
                door_changed = True

        if door_changed:
            floor.rebuild_flags()

        # Position changed: door mutation may have changed flags and FOV.
        self._invalidate_fov_cache()

        # Terrain interaction (trample grass, trigger plants, etc.)
        result = press_cell(floor, (entity.pos.x, entity.pos.y), entity)
        if result["tile_changed"]:
            self.add_event("MAP_PATCH", {"tiles": [{"x": entity.pos.x, "y": entity.pos.y, "tile": floor.grid[entity.pos.y][entity.pos.x]}]}, floor_id=floor_id)
            self.add_event("PLAY_SOUND", {"sound": "STEP_GRASS"}, floor_id=floor_id, source_player_id=entity.id if isinstance(entity, Player) else None)
        if result["triggered_plant"]:
            self.add_event("PLAY_SOUND", {"sound": "PLANT_TRIGGER"}, floor_id=floor_id, source_player_id=entity.id if isinstance(entity, Player) else None)

        if isinstance(entity, Player):
            self.add_event("MOVE", {"entity": entity_id, "x": entity.pos.x, "y": entity.pos.y}, floor_id=floor_id)
            # Freerunner builds Momentum on each step.
            self.gain_momentum(entity)
            # Rejuvenating Steps (huntress T2): heal small amount per step
            rs = entity.talent_info.level("rejuvenating_steps")
            if rs > 0:
                heal = rs
                entity.hp = min(entity.get_total_max_hp(), entity.hp + heal)
                self.add_event("HEAL", {"target": entity.id, "amount": heal, "x": entity.pos.x, "y": entity.pos.y}, floor_id=floor_id)

        if isinstance(entity, Player):
            items_to_pickup = [
                i_id
                for i_id, i in floor.items.items()
                if i.pos and i.pos.x == entity.pos.x and i.pos.y == entity.pos.y
                and i.type != "grave"  # graves are scenery, not pickable
                and not i.for_sale  # shop stock is bought via SHOP_BUY, not auto-picked-up
            ]
            for i_id in items_to_pickup:
                item = floor.items[i_id]
                if isinstance(item, Gold):
                    entity.gold += item.quantity
                    del floor.items[i_id]
                    self.add_event("PICKUP_GOLD", {"player": entity.id, "amount": item.quantity}, floor_id=floor_id)
                    continue
                if isinstance(item, Dewdrop):
                    waterskin = next(
                        (i for i in entity.inventory if isinstance(i, Waterskin) and not i.is_full()),
                        None,
                    )
                    if waterskin is not None:
                        waterskin.volume = min(Waterskin.MAX_VOLUME, waterskin.volume + item.quantity)
                        del floor.items[i_id]
                        self.add_event("COLLECT_DEW", {"player": entity.id, "item": waterskin.id}, floor_id=floor_id)
                        continue
                if entity.add_to_inventory(item):
                    del floor.items[i_id]
                    self.add_event("PICKUP", {"player": entity.id, "item": item.id}, floor_id=floor_id)

            self._trigger_trap_if_needed(floor, entity, floor_id)

        if isinstance(entity, Player) and tile == TileType.STAIRS_DOWN and entity.floor_id < MAX_FLOOR_ID:
            self._move_player_to_floor(entity, entity.floor_id + 1, TileType.STAIRS_UP)
            self.add_event("STAIRS_DOWN", {"player": entity_id}, player_id=entity_id)

        if isinstance(entity, Player) and tile == TileType.STAIRS_UP and entity.floor_id > 1:
            self._move_player_to_floor(entity, entity.floor_id - 1, TileType.STAIRS_DOWN)
            self.add_event("STAIRS_UP", {"player": entity_id}, player_id=entity_id)

    def _maybe_trigger_dm300_supercharge(self, target: "MobEntity", floor, floor_id: int, near_pos: Position):
        """Trigger DM300 pylon activation if target is DM300 with pending activation."""
        if isinstance(target, DM300) and target.pending_pylon_activation:
            target.pending_pylon_activation = False
            self.add_event("DM300_SUPERCHARGE", {"mob": target.id}, floor_id=floor_id)
            self._activate_pylon(floor, floor_id, near_pos=near_pos)

    def perform_ranged_attack(self, player_id: str, item_id: str, target_x: int, target_y: int) -> Optional[int]:
        player = self.players.get(player_id)
        print(f"[perform_ranged_attack] player={player_id}, item={item_id}, target=({target_x},{target_y})")
        if not player or player.is_downed:
            print(f"[perform_ranged_attack] BAIL: player invalid")
            return None

        floor_id = player.floor_id
        floor = self._get_or_create_floor(floor_id)

        item = player.belongings.get_item(item_id)
        print(f"[perform_ranged_attack] item lookup: {item}")

        if not item:
            print(f"[perform_ranged_attack] BAIL: item not found")
            return None

        is_throwable = isinstance(item, Throwable)
        is_weapon = isinstance(item, Weapon)
        is_wand = isinstance(item, Wand)
        print(f"[perform_ranged_attack] is_throwable={is_throwable} is_weapon={is_weapon} is_wand={is_wand}")


        if is_wand and item.charges <= 0:
            print(f"[perform_ranged_attack] BAIL: wand out of charges")
            return None

        current_time = time.time()
        cooldown = 1.0
        if is_weapon:
            cooldown = item.attack_cooldown

        if (current_time - player.last_attack_time) < cooldown:
            print(f"[perform_ranged_attack] BAIL: cooldown ({current_time - player.last_attack_time} < {cooldown})")
            return None

        dist = abs(player.pos.x - target_x) + abs(player.pos.y - target_y)
        max_range = item.range if hasattr(item, "range") else 5
        print(f"[perform_ranged_attack] dist={dist}, max_range={max_range}")
        if dist > max_range:
            print(f"[perform_ranged_attack] BAIL: out of range")
            return None

        if not self._is_in_los(player.pos, Position(x=target_x, y=target_y), floor_id=floor_id):
            print(f"[perform_ranged_attack] BAIL: not in LOS")
            return None

        player.last_attack_time = current_time
        player._last_action = "ranged"
        projectile_type = getattr(item, "projectile_type", "arrow")

        target_entity = None
        for p in self._players_on_floor(floor_id):
            if p.id != player_id and p.pos.x == target_x and p.pos.y == target_y:
                target_entity = p
                break

        if not target_entity:
            for m in floor.mobs.values():
                if m.is_alive and m.pos.x == target_x and m.pos.y == target_y:
                    target_entity = m
                    break

        ranged_event_data = {
            "source": player_id,
            "x": player.pos.x,
            "y": player.pos.y,
            "target_x": target_x,
            "target_y": target_y,
            "projectile": projectile_type,
            "crit": False,
            "grim_proc": False,
        }
        # Thrown inventory items fly as their own sprite (not a generic dart).
        # Wands keep the magic_bolt projectile.
        if not is_wand:
            ranged_event_data["item"] = self._serialize_floor_item(item)
        self.add_event(
            "RANGED_ATTACK",
            ranged_event_data,
            floor_id=floor_id,
        )

        damage_dealt = 0
        if target_entity and player.faction != target_entity.faction:
            if isinstance(target_entity, MobEntity):
                result = resolve_ranged_attack(
                    player, target_entity, item,
                    floor.mobs, target_x, target_y,
                    is_in_los=lambda a, b: self._is_in_los(a, b, floor_id=floor_id),
                )
                if result["missed"]:
                    self.add_event("MISS", {"source": player.id, "target": target_entity.id, "defense_verb": result.get("defense_verb", "dodged")}, floor_id=floor_id)
                damage_dealt = result["damage"]
                ranged_event_data["crit"] = result.get("crit", False)
                ranged_event_data["grim_proc"] = result.get("grim_proc", False)
            else:
                if is_wand:
                    atk_min = atk_max = item.damage
                elif is_weapon:
                    if player.belongings.weapon and item.id == player.belongings.weapon.id:
                        atk_min = player.get_damage_min()
                        atk_max = player.get_damage_max()
                    else:
                        dmg = item.damage + (player.strength // 2)
                        atk_min = atk_max = dmg
                else:
                    dmg = item.damage + (player.strength // 2)
                    atk_min = atk_max = dmg
                old_min, old_max = player.damage_min, player.damage_max
                player.damage_min, player.damage_max = atk_min, atk_max
                result = resolve_ranged_attack(
                    player, target_entity, item,
                    floor.mobs, target_x, target_y,
                    is_in_los=lambda a, b: self._is_in_los(a, b, floor_id=floor_id),
                )
                player.damage_min, player.damage_max = old_min, old_max
                if result["missed"]:
                    self.add_event("MISS", {"source": player.id, "target": target_entity.id, "defense_verb": result.get("defense_verb", "dodged")}, floor_id=floor_id)
                damage_dealt = result["damage"]
                ranged_event_data["crit"] = result.get("crit", False)
                ranged_event_data["grim_proc"] = result.get("grim_proc", False)

            if damage_dealt > 0:
                self.add_event("DAMAGE", {
                    "target": target_entity.id,
                    "amount": damage_dealt,
                    "crit": result.get("crit", False),
                    "grim_proc": result.get("grim_proc", False),
                }, floor_id=floor_id)
                if result.get("grim_proc"):
                    self.add_event("PLAY_SOUND", {"sound": "HIT_STRONG"}, floor_id=floor_id, source_player_id=player.id)
                if projectile_type == "magic_bolt":
                    self.add_event("PLAY_SOUND", {"sound": "HIT_MAGIC"}, floor_id=floor_id, source_player_id=player.id)
                else:
                    self.add_event("PLAY_SOUND", {"sound": "HIT_ARROW"}, floor_id=floor_id, source_player_id=player.id)

                if isinstance(target_entity, Player):
                    self.add_event("PLAY_SOUND", {"sound": "HIT_BODY"}, floor_id=floor_id, source_player_id=target_entity.id)
                    if target_entity.hp / target_entity.get_total_max_hp() <= 0.3:
                        self.add_event("PLAY_SOUND", {"sound": "HEALTH_WARN"}, player_id=target_entity.id)

            self._maybe_trigger_dm300_supercharge(target_entity, floor, floor_id, player.pos)

            if not target_entity.is_alive:
                if isinstance(target_entity, MobEntity):
                    self.process_death_mark_kill(player, target_entity, floor, floor_id)
                self.on_kill(player, target_entity, floor.mobs, floor_id)
                self.add_event("DEATH", {"target": target_entity.id}, floor_id=floor_id)
                if isinstance(target_entity, MobEntity):
                    if player.earn_exp(target_entity.exp):
                        self.on_talent_level_up(player)
                    drops = roll_drops(target_entity, self.drop_counters, target_entity.pos.x, target_entity.pos.y)
                    for d in drops:
                        floor.items[d.id] = d

        if is_wand:
            # Wand Preservation (mage T2): chance to not consume charge
            wp = player.talent_info.level("wand_preservation")
            if wp <= 0 or random.random() >= wp * 0.17:
                item.charges -= 1
            # Shield Battery (mage T2): gain shield on wand zap
            sb = player.talent_info.level("shield_battery")
            if sb > 0:
                shield_amt = 1 + sb
                player.add_shield("shield_battery", shield_amt, priority=1, decay=600)
        else:
            removed = player.belongings.backpack.detach(item.id)
            if removed is not None and player.belongings.get_item(item.id) is None:
                player.quickslot.convert_to_placeholder(removed)
                removed.pos = Position(x=target_x, y=target_y)
                floor.items[removed.id] = removed

        return damage_dealt
