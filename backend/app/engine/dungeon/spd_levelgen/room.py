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
"""Port of com.shatteredpixel.shatteredpixeldungeon.levels.rooms.Room
(spatial + connection logic only -- painting is handled by concrete room
subclasses + Painter, see rooms.py / painter.py)."""

from __future__ import annotations

from enum import Enum
from typing import List, Optional

from app.engine.dungeon.spd_levelgen.geom import Point, Rect
from app.engine.dungeon.spd_random import SPDRandom

ALL, LEFT, TOP, RIGHT, BOTTOM = 0, 1, 2, 3, 4


class DoorType(Enum):
    """Ordinal order matters: Door.set() only upgrades to a 'higher' type
    (Type.compareTo), and Room.edges() checks against EMPTY/TUNNEL/UNLOCKED/REGULAR."""
    EMPTY = 0
    TUNNEL = 1
    WATER = 2
    REGULAR = 3
    UNLOCKED = 4
    HIDDEN = 5
    BARRICADE = 6
    LOCKED = 7
    CRYSTAL = 8
    WALL = 9


class Door(Point):
    def __init__(self, x: int = 0, y: int = 0):
        super().__init__(x, y)
        self.type = DoorType.EMPTY
        self._type_locked = False

    def lock_type_changes(self, lock: bool) -> None:
        self._type_locked = lock

    def set(self, type_: DoorType) -> None:
        if not self._type_locked and type_.value > self.type.value:
            self.type = type_


class Room(Rect):
    def __init__(self):
        super().__init__()
        self.neighbours: List["Room"] = []
        self.connected: "dict[Room, Optional[Door]]" = {}
        self.distance = 0
        self.price = 1

    # -- spatial logic ----------------------------------------------------
    def min_width(self) -> int:
        return -1

    def max_width(self) -> int:
        return -1

    def min_height(self) -> int:
        return -1

    def max_height(self) -> int:
        return -1

    def set_size(self, rng: SPDRandom, min_w: Optional[int] = None, max_w: Optional[int] = None,
                 min_h: Optional[int] = None, max_h: Optional[int] = None) -> bool:
        if min_w is None:
            return self.set_size(rng, self.min_width(), self.max_width(), self.min_height(), self.max_height())

        if (min_w < self.min_width() or max_w > self.max_width()
                or min_h < self.min_height() or max_h > self.max_height()
                or min_w > max_w or min_h > max_h):
            return False
        # subtract one because rooms are inclusive to their right and bottom sides
        self.resize(rng.NormalIntRange(min_w, max_w) - 1, rng.NormalIntRange(min_h, max_h) - 1)
        return True

    def force_size(self, rng: SPDRandom, w: int, h: int) -> bool:
        return self.set_size(rng, w, w, h, h)

    def set_size_with_limit(self, rng: SPDRandom, w: int, h: int) -> bool:
        if w < self.min_width() or h < self.min_height():
            return False
        self.set_size(rng)
        if self.width() > w or self.height() > h:
            self.resize(min(self.width(), w) - 1, min(self.height(), h) - 1)
        return True

    def point_inside(self, from_: Point, n: int) -> Point:
        step = from_.clone()
        if from_.x == self.left:
            step.offset(n, 0)
        elif from_.x == self.right:
            step.offset(-n, 0)
        elif from_.y == self.top:
            step.offset(0, n)
        elif from_.y == self.bottom:
            step.offset(0, -n)
        return step

    def width(self) -> int:
        return super().width() + 1

    def height(self) -> int:
        return super().height() + 1

    def random(self, rng: SPDRandom, m: int = 1) -> Point:
        return Point(rng.IntRange(self.left + m, self.right - m),
                     rng.IntRange(self.top + m, self.bottom - m))

    def inside(self, p: Point) -> bool:
        """A point is only considered inside if within the 1-tile perimeter
        (note: stricter than Rect.inside, intentionally shadows it)."""
        return p.x > self.left and p.y > self.top and p.x < self.right and p.y < self.bottom

    def center(self, rng: SPDRandom) -> Point:
        """Note: Room overrides Rect.center with an INVERTED parity check (==1 not ==0)."""
        return Point(
            (self.left + self.right) // 2 + (rng.IntMax(2) if (self.right - self.left) % 2 == 1 else 0),
            (self.top + self.bottom) // 2 + (rng.IntMax(2) if (self.bottom - self.top) % 2 == 1 else 0),
        )

    # -- connection logic --------------------------------------------------
    def min_connections(self, direction: int) -> int:
        return 1 if direction == ALL else 0

    def cur_connections(self, direction: int) -> int:
        if direction == ALL:
            return len(self.connected)
        total = 0
        for r in self.connected.keys():
            i = self.intersect(r)
            if direction == LEFT and i.width() == 0 and i.left == self.left:
                total += 1
            elif direction == TOP and i.height() == 0 and i.top == self.top:
                total += 1
            elif direction == RIGHT and i.width() == 0 and i.right == self.right:
                total += 1
            elif direction == BOTTOM and i.height() == 0 and i.bottom == self.bottom:
                total += 1
        return total

    def rem_connections(self, direction: int) -> int:
        if self.cur_connections(ALL) >= self.max_connections(ALL):
            return 0
        return self.max_connections(direction) - self.cur_connections(direction)

    def max_connections(self, direction: int) -> int:
        return 16 if direction == ALL else 4

    def can_connect_point(self, p: Point) -> bool:
        on_vertical_edge = (p.x == self.left or p.x == self.right)
        on_horizontal_edge = (p.y == self.top or p.y == self.bottom)
        return on_vertical_edge != on_horizontal_edge

    def can_connect_dir(self, direction: int) -> bool:
        return self.rem_connections(direction) > 0

    def can_connect(self, r: "Room") -> bool:
        if (self.is_exit() and r.is_entrance()) or (self.is_entrance() and r.is_exit()):
            return False

        i = self.intersect(r)

        found_point = False
        for p in i.get_points():
            if self.can_connect_point(p) and r.can_connect_point(p):
                found_point = True
                break
        if not found_point:
            return False

        if i.width() == 0 and i.left == self.left:
            return self.can_connect_dir(LEFT) and r.can_connect_dir(RIGHT)
        elif i.height() == 0 and i.top == self.top:
            return self.can_connect_dir(TOP) and r.can_connect_dir(BOTTOM)
        elif i.width() == 0 and i.right == self.right:
            return self.can_connect_dir(RIGHT) and r.can_connect_dir(LEFT)
        elif i.height() == 0 and i.bottom == self.bottom:
            return self.can_connect_dir(BOTTOM) and r.can_connect_dir(TOP)
        return False

    def can_merge(self, level, other: "Room", p: Point, merge_terrain: int) -> bool:
        return False

    def merge(self, level, other: "Room", merge_rect: "Rect", merge_terrain: int) -> None:
        """Overridable for special merge logic between rooms; base just fills."""
        from app.engine.dungeon.spd_levelgen.painter import Painter
        Painter.fill(level, merge_rect, merge_terrain)

    def add_neighbour(self, other: "Room") -> bool:
        if other in self.neighbours:
            return True
        i = self.intersect(other)
        if (i.width() == 0 and i.height() >= 2) or (i.height() == 0 and i.width() >= 2):
            self.neighbours.append(other)
            other.neighbours.append(self)
            return True
        return False

    def connect(self, room: "Room") -> bool:
        if ((room in self.neighbours or self.add_neighbour(room))
                and room not in self.connected and self.can_connect(room)):
            self.connected[room] = None
            room.connected[self] = None
            return True
        return False

    def clear_connections(self) -> None:
        for r in self.neighbours:
            if self in r.neighbours:
                r.neighbours.remove(self)
        self.neighbours.clear()
        for r in self.connected.keys():
            r.connected.pop(self, None)
        self.connected.clear()

    def is_entrance(self) -> bool:
        return False

    def is_exit(self) -> bool:
        return False

    def edges(self) -> List["Room"]:
        """Graph.Node.edges() -- for path-building purposes, ignore doors that
        are locked, blocked, or hidden (only EMPTY/TUNNEL/UNLOCKED/REGULAR
        connections count as traversable)."""
        result = []
        for r, d in self.connected.items():
            if d.type in (DoorType.EMPTY, DoorType.TUNNEL, DoorType.UNLOCKED, DoorType.REGULAR):
                result.append(r)
        return result

    # -- painter-placeable-point hooks (overridden by concrete rooms) ------
    def can_place_water(self, p: Point) -> bool:
        return True

    def can_place_grass(self, p: Point) -> bool:
        return True

    def can_place_trap(self, p: Point) -> bool:
        return True

    def can_place_item(self, p: Point, level) -> bool:
        return self.inside(p)

    def can_place_character(self, p: Point, level) -> bool:
        return self.inside(p)

    def get_placeable_points(self, predicate) -> List[Point]:
        points = []
        for i in range(self.left, self.right + 1):
            for j in range(self.top, self.bottom + 1):
                p = Point(i, j)
                if predicate(p):
                    points.append(p)
        return points

    def water_placeable_points(self) -> List[Point]:
        return self.get_placeable_points(self.can_place_water)

    def grass_placeable_points(self) -> List[Point]:
        return self.get_placeable_points(self.can_place_grass)

    def trap_placeable_points(self) -> List[Point]:
        return self.get_placeable_points(self.can_place_trap)

    def char_placeable_points(self, level) -> List[Point]:
        return self.get_placeable_points(lambda p: self.can_place_character(p, level))

    def item_placeable_points(self, level) -> List[Point]:
        return self.get_placeable_points(lambda p: self.can_place_item(p, level))

    # -- painting (overridden by concrete rooms) --------------------------
    def paint(self, level, rng: SPDRandom) -> None:
        raise NotImplementedError
