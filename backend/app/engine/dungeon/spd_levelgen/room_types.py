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
"""Port of the StandardRoom/SpecialRoom/SecretRoom/ShopRoom base classes
(rooms/standard/StandardRoom.java, rooms/special/{SpecialRoom,ShopRoom}.java,
rooms/secret/SecretRoom.java) -- enough surface for Builder transliteration.
Concrete sewers-eligible subclasses are ported in Task #3.
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional

from app.engine.dungeon.spd_levelgen.room import ALL, Door, DoorType, Room
from app.engine.dungeon.spd_random import SPDRandom


class SizeCategory(Enum):
    NORMAL = (4, 10, 1)
    LARGE = (10, 14, 2)
    GIANT = (14, 18, 3)

    def __init__(self, min_dim: int, max_dim: int, room_value: int):
        self.min_dim = min_dim
        self.max_dim = max_dim
        self.room_value = room_value


_SIZE_CATEGORIES: List[SizeCategory] = [SizeCategory.NORMAL, SizeCategory.LARGE, SizeCategory.GIANT]


class StandardRoom(Room):
    def __init__(self):
        super().__init__()
        self.size_cat: SizeCategory = None
        # Java runs `{ setSizeCat(); }` as an instance initializer (needs Random);
        # the port instead requires callers to invoke init_size_cat(rng) right
        # after construction (see below).

    def size_cat_probs(self) -> List[float]:
        return [1.0, 0.0, 0.0]

    def set_size_cat(self, rng: SPDRandom, min_ordinal: int = 0, max_ordinal: int = None) -> bool:
        if max_ordinal is None:
            max_ordinal = len(_SIZE_CATEGORIES) - 1
        return self._set_size_cat_range(rng, min_ordinal, max_ordinal)

    def set_size_cat_max_room_value(self, rng: SPDRandom, max_room_value: int) -> bool:
        return self._set_size_cat_range(rng, 0, max_room_value - 1)

    def _set_size_cat_range(self, rng: SPDRandom, min_ordinal: int, max_ordinal: int) -> bool:
        probs = self.size_cat_probs()
        if len(probs) != len(_SIZE_CATEGORIES):
            return False

        for i in range(min_ordinal):
            probs[i] = 0.0
        for i in range(max_ordinal + 1, len(_SIZE_CATEGORIES)):
            probs[i] = 0.0

        ordinal = rng.chances(probs)
        if ordinal != -1:
            self.size_cat = _SIZE_CATEGORIES[ordinal]
            return True
        return False

    # NOTE: Java's instance initializer block `{ setSizeCat(); }` runs at construction
    # time, before the constructor body, and needs an RNG -- the Python port instead
    # exposes `init_size_cat(rng)` which callers (room factories) must invoke right
    # after instantiation.
    def init_size_cat(self, rng: SPDRandom) -> bool:
        return self.set_size_cat(rng)

    def min_width(self) -> int:
        return self.size_cat.min_dim

    def max_width(self) -> int:
        return self.size_cat.max_dim

    def min_height(self) -> int:
        return self.size_cat.min_dim

    def max_height(self) -> int:
        return self.size_cat.max_dim

    def size_factor(self) -> int:
        return self.size_cat.room_value

    def mob_spawn_weight(self) -> int:
        if self.is_entrance():
            return 1
        return self.size_factor()

    def connection_weight(self) -> int:
        return self.size_factor() * self.size_factor()

    def can_merge(self, level, other: "Room", p, merge_terrain: int) -> bool:
        from app.engine.dungeon.spd_levelgen import terrain
        cell = level.point_to_cell(self.point_inside(p, 1))
        return level.map[cell] not in terrain.SOLID


class SpecialRoom(Room):
    def __init__(self) -> None:
        super().__init__()
        self._entrance: Optional["Door"] = None

    def min_width(self) -> int:
        return 5

    def max_width(self) -> int:
        return 10

    def min_height(self) -> int:
        return 5

    def max_height(self) -> int:
        return 10

    def max_connections(self, direction: int) -> int:
        return 1

    def entrance(self) -> Optional["Door"]:
        if self._entrance is None:
            if not self.connected:
                return None
            self._entrance = next(iter(self.connected.values()))
        return self._entrance


class SecretRoom(SpecialRoom):
    pass


class AmbitiousImpRoom(SpecialRoom):
    """Port of rooms/quest/AmbitiousImpRoom.java (Imp quest, depths 17-19).
    Fixed 9x9 room with the Imp NPC near its entrance. The branch-level
    transition created by upstream SPD leads to the unrelated, unimplemented
    Daria's Vault feature and is intentionally omitted here."""

    def min_width(self) -> int:
        return 9

    def max_width(self) -> int:
        return 9

    def min_height(self) -> int:
        return 9

    def max_height(self) -> int:
        return 9

    def paint(self, level, rng: SPDRandom) -> None:
        from app.engine.dungeon.spd_levelgen import terrain
        from app.engine.dungeon.spd_levelgen.mob_spawner import GenMob
        from app.engine.dungeon.spd_levelgen.painter import Painter

        Painter.fill(level, self, terrain.WALL_DECO)
        Painter.fill(level, self, 1, terrain.EMPTY)

        c = self.center(rng)
        entrance = self.entrance()
        pos = level.point_to_cell(c)

        if entrance.x == self.left or entrance.x == self.right:
            pos += rng.IntRange(-1, 1) * level.width()
            pos += -2 if entrance.x == self.left else 2
        elif entrance.y == self.top or entrance.y == self.bottom:
            pos += rng.IntRange(-1, 1)
            pos += level.width() * (-2 if entrance.y == self.top else 2)

        level.mobs.append(GenMob(cls_name="Imp", pos=pos))

        Painter.draw_inside(level, self, entrance, 1, terrain.EMPTY)
        entrance.set(DoorType.REGULAR)


class ShopRoom(SpecialRoom):
    def paint(self, level, rng: SPDRandom) -> None:
        from app.engine.dungeon.spd_levelgen import terrain
        from app.engine.dungeon.spd_levelgen.mob_spawner import GenMob
        from app.engine.dungeon.spd_levelgen.painter import Painter
        from app.engine.dungeon.spd_levelgen.shop_items import shop_room_item_list
        from app.engine.dungeon.spd_levelgen.geom import Point

        Painter.fill(level, self, terrain.WALL)
        Painter.fill(level, self, 1, terrain.EMPTY_SP)

        pos = level.point_to_cell(self.center(rng))
        level.mobs.append(GenMob(cls_name="Shopkeeper", pos=pos))

        items = shop_room_item_list(rng, level.depth)
        _place_shop_items(level, self, items)

        for door in self.connected.values():
            door.set(DoorType.REGULAR)


def _place_shop_items(level, room: "ShopRoom", items: list) -> None:
    """Port of ShopRoom.placeItems()'s clockwise spiral placement."""
    from app.engine.dungeon.spd_levelgen import terrain
    from app.engine.dungeon.spd_levelgen.geom import Point

    entrance = room.entrance()
    entry_inset = Point(entrance.x, entrance.y)
    if entry_inset.y == room.top:
        entry_inset.y += 1
    elif entry_inset.y == room.bottom:
        entry_inset.y -= 1
    elif entry_inset.x == room.left:
        entry_inset.x += 1
    else:
        entry_inset.x -= 1

    cur = entry_inset.clone()
    inset = 1

    def _step(p: Point) -> None:
        if p.x == room.left + inset and p.y != room.top + inset:
            p.y -= 1
        elif p.y == room.top + inset and p.x != room.right - inset:
            p.x += 1
        elif p.x == room.right - inset and p.y != room.bottom - inset:
            p.y += 1
        else:
            p.x -= 1

    remaining = list(items)
    while remaining:
        item = remaining[0]

        _step(cur)

        if cur == entry_inset:
            if entry_inset.y == room.top + inset:
                entry_inset.y += 1
            elif entry_inset.y == room.bottom - inset:
                entry_inset.y -= 1
            if entry_inset.x == room.left + inset:
                entry_inset.x += 1
            elif entry_inset.x == room.right - inset:
                entry_inset.x -= 1
            inset += 1

            if inset > (min(room.width(), room.height()) - 3) // 2:
                break  # out of space

            cur = entry_inset.clone()
            _step(cur)

        cell = level.point_to_cell(cur)
        if level.map[cell] == terrain.HIGH_GRASS:
            level.map[cell] = terrain.GRASS
            level.los_blocking[cell] = False

        level.drop(item, cell)
        remaining.pop(0)

    # fill in any leftover items wherever there's free space
    if remaining:
        for x in range(room.left, room.right + 1):
            for y in range(room.top, room.bottom + 1):
                if not remaining:
                    break
                p = Point(x, y)
                cell = level.point_to_cell(p)
                if (level.map[cell] in (terrain.EMPTY_SP, terrain.EMPTY)
                        and level.heaps.get(cell) is None
                        and level.find_mob(cell) is None):
                    level.drop(remaining.pop(0), cell)
            if not remaining:
                break


class ImpShopRoom(SpecialRoom):
    """Port of rooms/standard/ImpShopRoom.java (city boss floor 20). Fixed
    9x9 room, carved like a normal ShopRoom but only populated once
    Imp.Quest is completed -- immediately if already completed when floor 20
    is generated, otherwise the Shopkeeper + stock are decided here and
    stashed on the level for retroactive placement (see
    GameInstance._spawn_imp_shop)."""

    def min_width(self) -> int:
        return 9

    def max_width(self) -> int:
        return 9

    def min_height(self) -> int:
        return 9

    def max_height(self) -> int:
        return 9

    def max_connections(self, direction: int) -> int:
        return 2

    def paint(self, level, rng: SPDRandom) -> None:
        from app.engine.dungeon.spd_levelgen import terrain
        from app.engine.dungeon.spd_levelgen.mob_spawner import GenMob
        from app.engine.dungeon.spd_levelgen.painter import Painter
        from app.engine.dungeon.spd_levelgen.shop_items import shop_room_item_list

        Painter.fill(level, self, terrain.WALL)
        Painter.fill(level, self, 1, terrain.EMPTY_SP)

        for door in self.connected.values():
            door.set(DoorType.REGULAR)

        items = shop_room_item_list(rng, level.depth)

        if level.run_state.imp_quest.completed:
            pos = level.point_to_cell(self.center(rng))
            level.mobs.append(GenMob(cls_name="Shopkeeper", pos=pos))
            _place_shop_items(level, self, items)
        else:
            entrance = self.entrance()
            level.imp_shop_room = {
                "left": self.left, "top": self.top,
                "right": self.right, "bottom": self.bottom,
                "entrance": (entrance.x, entrance.y),
                "items": items,
            }
