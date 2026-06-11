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

from app.engine.dungeon.spd_levelgen.room import ALL, Door, Room
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


class ShopRoom(SpecialRoom):
    pass
