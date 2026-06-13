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
"""World interaction for GameInstance: searching, locked doors, and traps.

Reveals hidden doors/traps around a searching player, consumes keys to open
locked doors, and resolves trap triggers when a player steps onto one.
"""

import uuid
from typing import List

from app.engine.dungeon.generator import TileType
from app.engine.entities.base import Key, Player, Position
from app.engine.entities.base import DwarfToken
from app.engine.entities.mobs import Imp, Shopkeeper
from app.engine.game.floor_state import FloorState


class WorldInteractionMixin:
    def handle_mob_death(self, mob, floor: FloorState, floor_id: int) -> None:
        """Boss-specific on-death drops, called at every mob-death site.

        The Goo drops the key that unlocks the sealed arena exit (SPD Goo.die
        drops a WornKey). Regular loot (goo blobs) is handled by roll_drops; the
        key is dropped here because it needs the floor-specific lock id, and it
        must drop no matter how Goo died (melee or bleed) so progression can't
        soft-lock."""
        from app.engine.entities.base import DwarfToken
        from app.engine.entities.mobs import DM300, Golem, Goo, Monk, Necromancer, Pylon, Tengu

        # Imp.Quest.process(): once the quest is given (and not yet
        # completed), killing a Monk (alternative) or Golem (!alternative)
        # anywhere in the dungeon (except floor 20) drops a DwarfToken.
        quest = self.run_state.imp_quest
        if quest.given and not quest.completed and floor_id != 20:
            wanted = Monk if quest.alternative else Golem
            if isinstance(mob, wanted):
                token = DwarfToken(id=str(uuid.uuid4()), pos=Position(x=mob.pos.x, y=mob.pos.y))
                floor.items[token.id] = token

        # CavesBossLevel.eliminatePylon -> DM300.loseSupercharge: when an
        # activated Pylon dies, DM300 becomes vulnerable again. No
        # chain-activation of another pylon.
        if isinstance(mob, Pylon):
            for other in floor.mobs.values():
                if isinstance(other, DM300):
                    other.supercharged = False
                    break

        # Necromancer.die(): kill the linked NecroSkeleton (mob.die already
        # zeroed its HP); emit DEATH so the frontend plays its death animation.
        if isinstance(mob, Necromancer) and mob.my_skeleton_id:
            skeleton = floor.mobs.get(mob.my_skeleton_id)
            if skeleton and not skeleton.is_alive:
                self.add_event("DEATH", {"target": skeleton.id}, floor_id=floor_id)

        # Tengu (floor 10): award base score + check badge qualification
        if isinstance(mob, Tengu):
            self.boss_scores[1] += 2000
            if self.qualified_for_boss_challenge:
                self.add_event("TENGU_BADGE_QUALIFIED", {}, floor_id=floor_id)
            return

        if not isinstance(mob, Goo):
            return
        key_id = next(iter(floor.locked_doors.values()), "goo_door")
        # Don't double-drop if the boss death is processed from two sites.
        if any(isinstance(i, Key) and getattr(i, "key_id", None) == key_id
               for i in floor.items.values()):
            return
        key = Key(
            id=str(uuid.uuid4()),
            name="Worn Key",
            pos=Position(x=mob.pos.x, y=mob.pos.y),
            key_id=key_id,
        )
        floor.items[key.id] = key
        self.add_event("PLAY_SOUND", {"sound": "BOSS"}, floor_id=floor_id)
    def search(self, player_id: str):
        player = self.players.get(player_id)
        if not player:
            return

        floor = self._get_or_create_floor(player.floor_id)
        patches: List[dict] = []
        # Every in-bounds cell scanned this search, so the client can sweep a
        # CheckedCell ring over the whole radius (mirrors the original drawing a
        # CheckedCell on each cell in range, not only the ones that revealed something).
        checked: List[List[int]] = []
        found_secret = False

        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                tx = player.pos.x + dx
                ty = player.pos.y + dy
                if not (0 <= tx < floor.width and 0 <= ty < floor.height):
                    continue

                checked.append([tx, ty])
                pos = (tx, ty)
                if pos in floor.hidden_doors:
                    actual_tile = floor.hidden_doors.pop(pos)
                    floor.grid[ty][tx] = actual_tile
                    patches.append({"x": tx, "y": ty, "tile": actual_tile})
                    found_secret = True

                trap = floor.traps.get(pos)
                if trap and trap.hidden:
                    trap.hidden = False
                    found_secret = True
                    if floor.grid[ty][tx] == TileType.SECRET_TRAP:
                        floor.grid[ty][tx] = TileType.TRAP
                        patches.append({"x": tx, "y": ty, "tile": TileType.TRAP})

        if patches:
            # Tile mutations changed the grid — refresh derived flag maps
            # so LOS / pathfinding / openSpace pick up the new state on
            # the next query (a revealed door is now passable + see-through).
            floor.rebuild_flags()
            self.add_event("MAP_PATCH", {"tiles": patches}, floor_id=player.floor_id)

        # Original plays the SECRET sound whenever a door OR a trap is revealed.
        if found_secret:
            self.add_event("PLAY_SOUND", {"sound": "SECRET"}, player_id=player_id)

        # Searcher-only: drives the operate (hand-raise) animation + the cyan ring
        # sweep on the searching client. x/y is the hero position the rings emanate from.
        self.add_event(
            "SEARCH",
            {
                "player": player_id,
                "x": player.pos.x,
                "y": player.pos.y,
                "cells": checked,
                "revealed_tiles": len(patches),
            },
            player_id=player_id,
        )

    def _try_unlock_locked_door(self, player: Player, floor: FloorState, x: int, y: int) -> bool:
        key_id = floor.locked_doors.get((x, y))
        if not key_id:
            return False

        key_idx = next(
            (
                idx
                for idx, item in enumerate(player.inventory)
                if isinstance(item, Key) and item.key_id == key_id
            ),
            -1,
        )
        if key_idx == -1:
            return False

        player.inventory.pop(key_idx)
        floor.locked_doors.pop((x, y), None)
        # The boss-arena exit (SPD's LOCKED_EXIT -> UNLOCKED_EXIT) becomes the
        # level's stairs down once unlocked, not a regular door.
        new_tile = TileType.STAIRS_DOWN if key_id == "goo_door" else TileType.DOOR
        floor.grid[y][x] = new_tile
        # Tile mutated from LOCKED_DOOR to DOOR/STAIRS_DOWN — refresh flag maps
        # so LOS/pathfinding sees the door as passable now.
        floor.rebuild_flags()

        self.add_event("MAP_PATCH", {"tiles": [{"x": x, "y": y, "tile": new_tile}]}, floor_id=player.floor_id)
        self.add_event("UNLOCK", {"player": player.id, "x": x, "y": y}, floor_id=player.floor_id)
        return True

    def _trigger_trap_if_needed(self, floor: FloorState, player: Player, floor_id: int):
        pos = (player.pos.x, player.pos.y)
        trap = floor.traps.get(pos)
        if not trap or not trap.active:
            return

        patches: List[dict] = []
        if trap.hidden:
            trap.hidden = False

        # Any trap tile -> INACTIVE_TRAP on trigger
        tile = floor.grid[player.pos.y][player.pos.x]
        if tile in (TileType.SECRET_TRAP, TileType.TRAP):
            floor.grid[player.pos.y][player.pos.x] = TileType.INACTIVE_TRAP
            patches.append({"x": player.pos.x, "y": player.pos.y, "tile": TileType.INACTIVE_TRAP})

        trap.active = False

        # SPD TenguDartTrap: 8 poison damage (15 on challenge, but no
        # challenge system yet), plus boss score penalty on floor 10.
        if trap.trap_type == "tengu_dart":
            damage = 8
            dealt = player.take_damage(damage)
            from app.engine.entities.buffs import add_buff
            add_buff(player.buffs, "poison", duration=8.0, level=1, stack_mode="extend")
            self.boss_scores[1] -= 100
            self.qualified_for_boss_challenge = False
        else:
            damage = 2
            dealt = player.take_damage(damage)

        if patches:
            self.add_event("MAP_PATCH", {"tiles": patches}, floor_id=floor_id)

        self.add_event(
            "TRAP_TRIGGERED",
            {"player": player.id, "trap": trap.trap_type, "damage": dealt},
            floor_id=floor_id,
        )
        if dealt > 0:
            self.add_event("DAMAGE", {"target": player.id, "amount": dealt}, floor_id=floor_id)
            self.add_event("PLAY_SOUND", {"sound": "HIT_BODY"}, floor_id=floor_id, source_player_id=player.id)
            if player.hp / max(1, player.get_total_max_hp()) <= 0.3:
                self.add_event("PLAY_SOUND", {"sound": "HEALTH_WARN"}, player_id=player.id)

    # -- Shop / NPC interaction --------------------------------------------

    def _buy_price(self, item, depth: int) -> int:
        # Shopkeeper.sellPrice(): the price the *shop* charges to sell an item
        # to the hero. Greedy 5x markup, scaling with depth.
        identified = item.kind in self.identified_kinds
        return item.value(identified=identified) * 5 * (depth // 5 + 1)

    def _can_sell(self, item, player: Player) -> bool:
        # Shopkeeper.canSell(): must have a positive value, not be a unique
        # non-stackable item, and not be cursed gear currently worn.
        identified = item.kind in self.identified_kinds
        if item.value(identified=identified) <= 0:
            return False
        if item.unique and not item.stackable:
            return False
        if player.belongings.is_equipped(item.id) and item.cursed:
            return False
        return True

    def npc_interact(self, player_id: str, npc_id: str) -> None:
        player = self.players.get(player_id)
        if not player:
            return
        floor = self._get_or_create_floor(player.floor_id)
        npc = floor.mobs.get(npc_id)
        if npc is None or npc.type != "npc":
            return
        if max(abs(npc.pos.x - player.pos.x), abs(npc.pos.y - player.pos.y)) > 1:
            return

        if isinstance(npc, Shopkeeper):
            stock = [
                self._serialize_floor_item(i)
                for i in floor.items.values()
                if i.for_sale and i.pos and max(abs(i.pos.x - npc.pos.x), abs(i.pos.y - npc.pos.y)) <= 1
            ]
            for item_dict in stock:
                source_item = floor.items.get(item_dict["id"])
                identified = source_item.kind in self.identified_kinds
                item_dict["value"] = self._buy_price(source_item, player.floor_id)
                item_dict["identified"] = identified
            self.add_event(
                "SHOP_OPEN",
                {"player": player.id, "npc": npc_id, "stock": stock, "gold": player.gold},
                player_id=player_id,
            )

        elif isinstance(npc, Imp):
            quest = self.run_state.imp_quest
            if not quest.given:
                quest.given = True
                quest.completed = False
                target = "Monks" if quest.alternative else "Golems"
                text = (
                    "Psst! Hey, "
                    f"{player.name}! I've lost a stash of tokens to the "
                    f"{target} around here. Bring me 5 of them"
                    + ("" if quest.alternative else " (4 will do)")
                    + " and I'll reward you handsomely."
                )
                self.add_event(
                    "IMP_DIALOGUE",
                    {"player": player.id, "npc": npc_id, "text": text, "can_claim": False},
                    player_id=player_id,
                )
            else:
                tokens_item = next(
                    (i for i in player.inventory if isinstance(i, DwarfToken)), None
                )
                tokens = tokens_item.quantity if tokens_item else 0
                required = 5 if quest.alternative else 4
                if tokens >= required:
                    self.add_event(
                        "IMP_DIALOGUE",
                        {
                            "player": player.id, "npc": npc_id,
                            "text": "You found them! Here, take this as thanks.",
                            "can_claim": True, "tokens": tokens,
                        },
                        player_id=player_id,
                    )
                else:
                    target = "Monks" if quest.alternative else "Golems"
                    self.add_event(
                        "IMP_DIALOGUE",
                        {
                            "player": player.id, "npc": npc_id,
                            "text": f"Still looking for those tokens? Check the {target}.",
                            "can_claim": False, "tokens": tokens,
                        },
                        player_id=player_id,
                    )

    def shop_buy(self, player_id: str, npc_id: str, item_id: str) -> None:
        player = self.players.get(player_id)
        if not player:
            return
        floor = self._get_or_create_floor(player.floor_id)
        npc = floor.mobs.get(npc_id)
        if npc is None or not isinstance(npc, Shopkeeper):
            return
        if max(abs(npc.pos.x - player.pos.x), abs(npc.pos.y - player.pos.y)) > 1:
            return

        item = floor.items.get(item_id)
        if item is None or not item.for_sale:
            return
        price = self._buy_price(item, player.floor_id)
        if player.gold < price:
            return
        item.for_sale = False
        item.pos = None
        if not player.add_to_inventory(item):
            item.for_sale = True
            item.pos = Position(x=npc.pos.x, y=npc.pos.y)
            return

        player.gold -= price
        del floor.items[item_id]
        self.add_event(
            "SHOP_BUY",
            {"player": player.id, "item": item.id, "price": price},
            floor_id=player.floor_id, source_player_id=player.id,
        )

    def shop_sell(self, player_id: str, item_id: str) -> None:
        player = self.players.get(player_id)
        if not player:
            return
        item = player.belongings.get_item(item_id)
        if item is None or not self._can_sell(item, player):
            return

        if player.belongings.is_equipped(item.id):
            for slot in ("weapon", "armor", "artifact", "misc", "ring"):
                if getattr(player.belongings, slot) is not None and getattr(player.belongings, slot).id == item.id:
                    setattr(player.belongings, slot, None)
                    break
            detached = item
        else:
            detached = player.belongings.backpack.detach(item.id)
        if detached is None:
            return

        identified = detached.kind in self.identified_kinds
        price = detached.value(identified=identified)
        player.gold += price
        player.quickslot.clear_item(detached.id)
        self.add_event(
            "SHOP_SELL",
            {"player": player.id, "item": detached.id, "price": price},
            floor_id=player.floor_id, source_player_id=player.id,
        )

    # -- Imp quest -----------------------------------------------------------

    def _spawn_imp_shop(self, floor: FloorState) -> None:
        """ImpShopRoom.spawnShop(): places the Shopkeeper + the stock decided
        at floor-20 levelgen time, once Imp.Quest is completed and floor 20
        already exists (the common case, since the alternative=Monk variant
        completes after Halls floors, well after floor 20 was generated)."""
        room = floor.generation_meta.get("imp_shop_room")
        if not room or floor.generation_meta.get("imp_shop_spawned"):
            return
        floor.generation_meta["imp_shop_spawned"] = True

        left, top, right, bottom = room["left"], room["top"], room["right"], room["bottom"]
        cx, cy = (left + right) // 2, (top + bottom) // 2
        shopkeeper = Shopkeeper(id=str(uuid.uuid4()), pos=Position(x=cx, y=cy))
        floor.mobs[shopkeeper.id] = shopkeeper

        # ShopRoom.placeItems(): clockwise spiral from the entrance, inset by
        # one ring at a time once the spiral returns to the entrance.
        ex, ey = room["entrance"]
        if ey == top:
            ey += 1
        elif ey == bottom:
            ey -= 1
        elif ex == left:
            ex += 1
        else:
            ex -= 1

        cur_x, cur_y = ex, ey
        inset = 1

        def step(x: int, y: int) -> tuple:
            if x == left + inset and y != top + inset:
                return x, y - 1
            if y == top + inset and x != right - inset:
                return x + 1, y
            if x == right - inset and y != bottom - inset:
                return x, y + 1
            return x - 1, y

        def occupied(x: int, y: int) -> bool:
            if any(m.pos.x == x and m.pos.y == y for m in floor.mobs.values()):
                return True
            return any(i.pos and i.pos.x == x and i.pos.y == y for i in floor.items.values())

        remaining = list(room["items"])
        while remaining:
            cur_x, cur_y = step(cur_x, cur_y)

            if (cur_x, cur_y) == (ex, ey):
                if ey == top + inset:
                    ey += 1
                elif ey == bottom - inset:
                    ey -= 1
                if ex == left + inset:
                    ex += 1
                elif ex == right - inset:
                    ex -= 1
                inset += 1

                if inset > (min(right - left + 1, bottom - top + 1) - 3) // 2:
                    break

                cur_x, cur_y = step(ex, ey)

            if occupied(cur_x, cur_y):
                continue

            item = remaining.pop(0)
            placed = item.model_copy(update={
                "id": str(uuid.uuid4()), "pos": Position(x=cur_x, y=cur_y), "for_sale": True,
            })
            floor.items[placed.id] = placed

        # Leftover items (spiral ran out of room) go anywhere free.
        for x in range(left, right + 1):
            for y in range(top, bottom + 1):
                if not remaining:
                    break
                if floor.grid[y][x] == TileType.FLOOR and not occupied(x, y):
                    item = remaining.pop(0)
                    placed = item.model_copy(update={
                        "id": str(uuid.uuid4()), "pos": Position(x=x, y=y), "for_sale": True,
                    })
                    floor.items[placed.id] = placed
            if not remaining:
                break

    def imp_claim_reward(self, player_id: str, npc_id: str) -> None:
        player = self.players.get(player_id)
        if not player:
            return
        floor = self._get_or_create_floor(player.floor_id)
        npc = floor.mobs.get(npc_id)
        if npc is None or not isinstance(npc, Imp):
            return
        if max(abs(npc.pos.x - player.pos.x), abs(npc.pos.y - player.pos.y)) > 1:
            return

        quest = self.run_state.imp_quest
        if not quest.given or quest.completed:
            return

        tokens_item = next((i for i in player.inventory if isinstance(i, DwarfToken)), None)
        tokens = tokens_item.quantity if tokens_item else 0
        required = 5 if quest.alternative else 4
        if tokens < required:
            return

        # WndImp.takeReward(): remove all tokens, identify the reward (level
        # only -- cursed_known stays False, hidden curse), grant or drop it.
        player.belongings.backpack.detach_all(tokens_item.id)
        player.quickslot.clear_item(tokens_item.id)

        reward = quest.reward.model_copy(update={"id": str(uuid.uuid4())})
        if not player.add_to_inventory(reward):
            reward.pos = Position(x=npc.pos.x, y=npc.pos.y)
            floor.items[reward.id] = reward

        # Imp.flee(): the Imp despawns once the quest is resolved.
        del floor.mobs[npc.id]
        quest.completed = True

        self.add_event("DEATH", {"target": npc.id}, floor_id=player.floor_id)
        self.add_event(
            "IMP_REWARD",
            {"player": player.id, "npc": npc_id, "item": reward.id},
            player_id=player_id,
        )

        # ImpShopRoom.onLevelLoad(): if floor 20 already exists, spawn the
        # shop immediately (otherwise paint() handles it when floor 20 is
        # first generated).
        floor20 = self.floors.get(20)
        if floor20 is not None:
            self._spawn_imp_shop(floor20)
