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
"""Client state serialization and per-run identification masking.

Builds the per-player game-state snapshot sent over the WebSocket, and scrambles
the names/appearance of still-unidentified potions and scrolls (SPD's randomised
potion colours / scroll runes, shared per-run across the co-op party).
"""

from typing import Dict, Optional

from app.engine.entities.base import Bag, Difficulty


class SerializationMixin:
    def change_difficulty(self, new_level: str):
        if new_level in [Difficulty.EASY, Difficulty.NORMAL, Difficulty.HARD]:
            self.difficulty = new_level

    KNOWN_CHALLENGES = {"stronger_bosses"}

    def set_challenges(self, challenges_str: str):
        self.challenges = {
            c for c in challenges_str.split(",") if c in self.KNOWN_CHALLENGES
        }

    # --- identification masking -------------------------------------------
    # Per-run scrambled display names for still-unidentified consumable kinds
    # (mirrors SPD's randomised potion colours / scroll runes).
    # Ordered to match the sprite columns in items.png (POTIONS row 22 / SCROLLS
    # row 19, ItemSpriteSheet.java), so a kind's appearance index doubles as its
    # sprite column.
    _POTION_LABELS = ["Crimson", "Amber", "Golden", "Jade", "Turquoise", "Azure",
                      "Indigo", "Magenta", "Bistre", "Charcoal", "Silver", "Ivory"]
    _SCROLL_LABELS = ["Kaunan", "Sowilo", "Laguz", "Yngvi", "Gyfu", "Raido",
                      "Isaz", "Mannaz", "Naudiz", "Berkanan", "Odal", "Tiwaz"]
    _APPEARANCE_ROW = {"potion": 22, "scroll": 19}

    def _kind_index(self, kind: str, typ: str) -> int:
        # Stable per-run colour/rune index for a potion/scroll kind. Assigns the
        # next free index of that type on first sight.
        if kind not in self.kind_appearance:
            used = self._appearance_used.get(typ)
            if used is None:
                used = self._appearance_used[typ] = set()
            idx = next((i for i in range(12) if i not in used), len(used))
            used.add(idx)
            self.kind_appearance[kind] = idx
        return self.kind_appearance[kind]

    def _label_for(self, kind: str, typ: str) -> str:
        if kind not in self.kind_labels:
            pool = self._POTION_LABELS if typ == "potion" else self._SCROLL_LABELS
            idx = self._kind_index(kind, typ)
            word = pool[idx] if idx < len(pool) else kind
            self.kind_labels[kind] = (f"{word} Potion" if typ == "potion"
                                      else f"Scroll of {word}")
        return self.kind_labels[kind]

    def _appearance_for(self, kind: str, typ: str) -> dict:
        # Sprite cell [col, row] for a potion/scroll's per-run colour/rune. Sent
        # for every potion/scroll regardless of identification.
        return {"col": self._kind_index(kind, typ), "row": self._APPEARANCE_ROW[typ]}

    def _mask_item_dict(self, d: Optional[dict]) -> Optional[dict]:
        # Recursively obscure unidentified potion/scroll types in a serialized
        # item dict: scramble the name, collapse `kind` to the generic category so
        # the client can't read the subtype, and hide subtype fields.
        if not d:
            return d
        items = d.get("items")
        if isinstance(items, list):
            for it in items:
                self._mask_item_dict(it)
        typ = d.get("type")
        if typ in ("potion", "scroll"):
            # Attach the per-run colour/rune sprite from the TRUE kind before any
            # masking collapses it. The bottle keeps its colour after ID (SPD).
            d["appearance"] = self._appearance_for(d["kind"], typ)
        if d.get("type") in ("potion", "scroll") and d.get("kind") not in self.identified_kinds:
            d["name"] = self._label_for(d["kind"], d["type"])
            d["kind"] = d["type"]
            d.pop("effect", None)
            d["level_known"] = False
            if "description" in d:
                d["description"] = (
                    "You'll have to drink it to find out what it does."
                    if d["type"] == "potion"
                    else "You'll have to read it to find out what it does."
                )
        return d

    def _serialize_player(self, p) -> dict:
        d = p.model_dump()

        # Map every live item by id so we can attach the server-authoritative
        # action list (SPD's Item.actions) the client renders its menu from.
        id2item: Dict[str, object] = {}

        def collect(bag):
            id2item[bag.id] = bag
            for it in bag.items:
                id2item[it.id] = it
                if isinstance(it, Bag):
                    collect(it)

        collect(p.belongings.backpack)
        for s in p.belongings.equipped_slots():
            if s is not None:
                id2item[s.id] = s

        def process(node):
            if not node:
                return
            for it in (node.get("items") or []):
                process(it)
            live = id2item.get(node.get("id"))
            if live is not None:
                node["actions"] = live.actions(p)
                node["default_action"] = live.default_action()
                node["description"] = live.description(p)
                node["value"] = live.value(identified=live.kind in self.identified_kinds)
            self._mask_item_dict(node)

        belongings = d.get("belongings", {})
        for slot in ("weapon", "armor", "artifact", "misc", "ring"):
            process(belongings.get(slot))
        process(belongings.get("backpack"))
        # Legacy computed views serialize as independent copies — process too.
        for it in (d.get("inventory") or []):
            process(it)
        process(d.get("equipped_weapon"))
        process(d.get("equipped_wearable"))
        hunger = d.get("hunger", 0.0)
        d["hunger_pct"] = round(min(1.0, hunger / 450.0), 3)
        return d

    def _serialize_floor_item(self, item) -> dict:
        d = item.model_dump()
        d["value"] = item.value(identified=item.kind in self.identified_kinds)
        return self._mask_item_dict(d)

    def get_state(self, player_id: Optional[str] = None):
        # Occupancy-based open doors and entity positions may have changed since
        # the last computation; rebuild FOV from a clean cache for this snapshot.
        self._invalidate_fov_cache()
        if player_id and player_id in self.players:
            player = self.players[player_id]
            floor = self._get_or_create_floor(player.floor_id)
            floor_players = [p for p in self._players_on_floor(player.floor_id)]

            admin_traps = [
                {"x": x, "y": y, "trap_type": t.trap_type}
                for (x, y), t in floor.traps.items()
            ]
            if player.is_admin:
                all_tiles = [(x, y) for y in range(floor.height) for x in range(floor.width)]
                return {
                    "depth": player.floor_id,
                    "players": [self._serialize_player(p) for p in floor_players],
                    "mobs": [m.model_dump() for m in floor.mobs.values() if m.is_alive],
                    "items": [self._serialize_floor_item(i) for i in floor.items.values() if i.pos],
                    "visible_tiles": all_tiles,
                    "open_doors": self._get_open_doors(floor),
                    "grid": floor.grid,
                    "width": floor.width,
                    "height": floor.height,
                    "traps": admin_traps,
                    "custom_tiles": floor.custom_tiles,
                }

            visible_tiles = self.get_visible_tiles(
                player.pos, radius=self._view_distance(player), floor_id=player.floor_id,
                viewer_id=player.id)
            visible_set = set(visible_tiles)

            player_traps = [
                {"x": x, "y": y, "trap_type": t.trap_type}
                for (x, y), t in floor.traps.items()
                if (x, y) in visible_set and not t.hidden
            ]

            # SPD MindVision: while active, every mob's 3x3 neighbourhood is
            # revealed regardless of walls/FOV.
            mind_vision_set = set()
            if player.has_buff("mind_vision"):
                for m in floor.mobs.values():
                    if not m.is_alive:
                        continue
                    for dx in (-1, 0, 1):
                        for dy in (-1, 0, 1):
                            mind_vision_set.add((m.pos.x + dx, m.pos.y + dy))

            # SPD heap.seen: first-discovery latch, set once an item's cell
            # enters FOV.
            for i in floor.items.values():
                if i.pos and (i.pos.x, i.pos.y) in visible_set:
                    i.seen = True

            return {
                "depth": player.floor_id,
                "players": [self._serialize_player(p) for p in floor_players],
                "mobs": [m.model_dump() for m in floor.mobs.values() if m.is_alive
                         and ((m.pos.x, m.pos.y) in visible_set or (m.pos.x, m.pos.y) in mind_vision_set)],
                "items": [self._serialize_floor_item(i) for i in floor.items.values() if i.pos and (i.pos.x, i.pos.y) in visible_set],
                "visible_tiles": visible_tiles,
                "open_doors": self._get_open_doors(floor),
                "grid": floor.grid,
                "width": floor.width,
                "height": floor.height,
                "traps": player_traps,
                "custom_tiles": floor.custom_tiles,
            }

        floor = self._get_or_create_floor(self.depth)
        return {
            "depth": self.depth,
            "players": [self._serialize_player(p) for p in self._players_on_floor(self.depth)],
            "mobs": [m.model_dump() for m in floor.mobs.values() if m.is_alive],
            "items": [self._serialize_floor_item(i) for i in floor.items.values() if i.pos],
            "open_doors": self._get_open_doors(floor),
            "grid": floor.grid,
            "width": floor.width,
            "height": floor.height,
            "traps": [],
            "custom_tiles": floor.custom_tiles,
        }
