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
"""Port of com.shatteredpixel.shatteredpixeldungeon.levels.rooms.connection.*
-- ConnectionRoom subclasses' sizing/connection-count overrides AND `paint()`
(tunnels, bridges, perimeter walkways, mazes); preserves the exact RNG call
order (TunnelRoom.getDoorCenter -> Float()x2, TunnelRoom.paint -> IntMax(4),
StandardBridgeRoom-style merging consumes none here, MazeConnectionRoom ->
Maze.generate's full RNG sequence)."""

from __future__ import annotations

import math
from typing import List, Optional

from app.engine.dungeon.spd_levelgen import maze, terrain
from app.engine.dungeon.spd_levelgen.geom import Point, PointF, Rect, _to_f32, gate
from app.engine.dungeon.spd_levelgen.painter import Painter
from app.engine.dungeon.spd_levelgen.room import ALL, Door, DoorType, Room
from app.engine.dungeon.spd_random import SPDRandom


def _circle8(width: int) -> tuple:
    """PathFinder.CIRCLE8 with the level's actual map width substituted."""
    return (-width - 1, -width, -width + 1, +1, +width + 1, +width, +width - 1, -1)


class ConnectionRoom(Room):
    def min_width(self) -> int:
        return 3

    def max_width(self) -> int:
        return 10

    def min_height(self) -> int:
        return 3

    def max_height(self) -> int:
        return 10

    def min_connections(self, direction: int) -> int:
        return 2 if direction == ALL else 0

    def paint(self, level, rng) -> None:
        raise NotImplementedError("connection room painting ported in the Painter phase")


# chances[depth] -> weights over [TunnelRoom, BridgeRoom, PerimeterRoom, WalkwayRoom,
#                                 RingTunnelRoom, RingBridgeRoom]
_CHANCES_1 = (20.0, 1.0, 0.0, 2.0, 2.0, 1.0)
_CHANCES_5 = (20.0, 0.0, 0.0, 0.0, 0.0, 0.0)
_CHANCES_6 = (0.0, 0.0, 22.0, 3.0, 0.0, 0.0)
_CHANCES_11 = (12.0, 0.0, 0.0, 5.0, 5.0, 3.0)
_CHANCES_16 = (0.0, 0.0, 18.0, 3.0, 3.0, 1.0)
_CHANCES_22 = (15.0, 4.0, 0.0, 2.0, 3.0, 2.0)

CONNECTION_ROOM_CHANCES = {
    1: _CHANCES_1, 2: _CHANCES_1, 3: _CHANCES_1, 4: _CHANCES_1,
    5: _CHANCES_5,
    6: _CHANCES_6, 7: _CHANCES_6, 8: _CHANCES_6, 9: _CHANCES_6, 10: _CHANCES_6,
    11: _CHANCES_11, 12: _CHANCES_11, 13: _CHANCES_11, 14: _CHANCES_11, 15: _CHANCES_11,
    16: _CHANCES_16, 17: _CHANCES_16, 18: _CHANCES_16, 19: _CHANCES_16, 20: _CHANCES_16,
    21: _CHANCES_5,
    22: _CHANCES_22, 23: _CHANCES_22, 24: _CHANCES_22, 25: _CHANCES_22, 26: _CHANCES_22,
}


def _fill_neighbour_chasm(level, room: Room) -> None:
    """Shared BridgeRoom/WalkwayRoom/RingBridgeRoom tail: chasm-fills the
    intersection with any neighbouring bridge/walkway room (no RNG)."""
    for r in room.neighbours:
        if isinstance(r, (BridgeRoom, RingBridgeRoom, WalkwayRoom)):
            i = room.intersect(r)
            if i.width() != 0:
                i.left += 1
                i.right -= 1
            else:
                i.top += 1
                i.bottom -= 1
            Painter.fill(level, i.left, i.top, i.width() + 1, i.height() + 1, terrain.CHASM)


class TunnelRoom(ConnectionRoom):
    """Tunnels along the room's center, with straight lines."""

    def paint(self, level, rng: SPDRandom) -> None:
        floor = level.tunnel_tile()

        c = self._get_connection_space(rng)

        for door in self.connected.values():
            start = door.clone()
            if start.x == self.left:
                start.x += 1
            elif start.y == self.top:
                start.y += 1
            elif start.x == self.right:
                start.x -= 1
            elif start.y == self.bottom:
                start.y -= 1

            if start.x < c.left:
                right_shift = c.left - start.x
            elif start.x > c.right:
                right_shift = c.right - start.x
            else:
                right_shift = 0

            if start.y < c.top:
                down_shift = c.top - start.y
            elif start.y > c.bottom:
                down_shift = c.bottom - start.y
            else:
                down_shift = 0

            if door.x == self.left or door.x == self.right:
                mid = Point(start.x + right_shift, start.y)
                end = Point(mid.x, mid.y + down_shift)
            else:
                mid = Point(start.x, start.y + down_shift)
                end = Point(mid.x + right_shift, mid.y)

            Painter.draw_line(level, start, mid, floor)
            Painter.draw_line(level, mid, end, floor)

        if (self.width() >= 7 and self.height() >= 7
                and len(self.connected) >= 4 and c.square() == 0):
            cell = level.point_to_cell(Point(c.left, c.top))
            ofs = 2 * rng.IntMax(4)
            circle8 = _circle8(level.width())
            if (level.map[cell + circle8[(ofs + 7) % 8]] == floor
                    and level.map[cell + circle8[(ofs + 1) % 8]] == floor):
                Painter.set(level, cell + circle8[ofs], floor)

        for door in self.connected.values():
            door.set(DoorType.TUNNEL)

    def _get_connection_space(self, rng: SPDRandom) -> Rect:
        """Returns the space which all doors must connect to (usually 1 cell).
        Subclasses (RingTunnelRoom) override + cache."""
        c = self._get_door_center(rng)
        return Rect(c.x, c.y, c.x, c.y)

    def _get_door_center(self, rng: SPDRandom) -> Point:
        """Returns a point equidistant from all doors this room has."""
        door_center_x = 0.0
        door_center_y = 0.0
        for door in self.connected.values():
            door_center_x = _to_f32(door_center_x + door.x)
            door_center_y = _to_f32(door_center_y + door.y)

        n = len(self.connected)
        c = Point(int(door_center_x) // n, int(door_center_y) // n)
        if rng.Float() < math.fmod(door_center_x, 1.0):
            c.x += 1
        if rng.Float() < math.fmod(door_center_y, 1.0):
            c.y += 1
        c.x = int(gate(self.left + 1, c.x, self.right - 1))
        c.y = int(gate(self.top + 1, c.y, self.bottom - 1))
        return c


class BridgeRoom(TunnelRoom):
    def paint(self, level, rng: SPDRandom) -> None:
        if min(self.width(), self.height()) > 3:
            Painter.fill(level, self, 1, terrain.CHASM)

        super().paint(level, rng)

        _fill_neighbour_chasm(level, self)

    def can_merge(self, level, other: "Room", p: Point, merge_terrain: int) -> bool:
        return merge_terrain == terrain.CHASM


_corners_cache: Optional[List[Point]] = None


def _space_between(a: int, b: int) -> int:
    return abs(a - b) - 1


def _distance_between_points(r: Room, a: Point, b: Point) -> int:
    if (((a.x == r.left + 1 or a.x == r.right - 1) and a.y == b.y)
            or ((a.y == r.top + 1 or a.y == r.bottom - 1) and a.x == b.x)):
        return max(_space_between(a.x, b.x), _space_between(a.y, b.y))

    return (min(_space_between(r.left, a.x) + _space_between(r.left, b.x),
                _space_between(r.right, a.x) + _space_between(r.right, b.x))
            + min(_space_between(r.top, a.y) + _space_between(r.top, b.y),
                  _space_between(r.bottom, a.y) + _space_between(r.bottom, b.y))
            - 1)


def _fill_between_points(level, r: Room, from_: Point, to: Point, floor: int) -> None:
    global _corners_cache

    if (((from_.x == r.left + 1 or from_.x == r.right - 1) and from_.x == to.x)
            or ((from_.y == r.top + 1 or from_.y == r.bottom - 1) and from_.y == to.y)):
        Painter.fill(level,
                     min(from_.x, to.x), min(from_.y, to.y),
                     _space_between(from_.x, to.x) + 2, _space_between(from_.y, to.y) + 2,
                     floor)
        return

    if _corners_cache is None:
        _corners_cache = [
            Point(r.left + 1, r.top + 1),
            Point(r.right - 1, r.top + 1),
            Point(r.right - 1, r.bottom - 1),
            Point(r.left + 1, r.bottom - 1),
        ]

    for c in _corners_cache:
        if (c.x == from_.x or c.y == from_.y) and (c.x == to.x or c.y == to.y):
            Painter.draw_line(level, from_, c, floor)
            Painter.draw_line(level, c, to, floor)
            return

    if from_.y == r.top + 1 or from_.y == r.bottom - 1:
        if (_space_between(r.left, from_.x) + _space_between(r.left, to.x)
                <= _space_between(r.right, from_.x) + _space_between(r.right, to.x)):
            side = Point(r.left + 1, r.top + r.height() // 2)
        else:
            side = Point(r.right - 1, r.top + r.height() // 2)
    else:
        if (_space_between(r.top, from_.y) + _space_between(r.top, to.y)
                <= _space_between(r.bottom, from_.y) + _space_between(r.bottom, to.y)):
            side = Point(r.left + r.width() // 2, r.top + 1)
        else:
            side = Point(r.left + r.width() // 2, r.bottom - 1)

    _fill_between_points(level, r, from_, side, floor)
    _fill_between_points(level, r, side, to, floor)


def _fill_perimeter_paths(level, r: Room, floor: int) -> None:
    global _corners_cache
    _corners_cache = None

    points_to_fill: List[Point] = []
    for door in r.connected.values():
        p = door.clone()
        if p.y == r.top:
            p.y += 1
        elif p.y == r.bottom:
            p.y -= 1
        elif p.x == r.left:
            p.x += 1
        else:
            p.x -= 1
        points_to_fill.append(p)

    points_filled = [points_to_fill.pop(0)]

    while points_to_fill:
        shortest_distance = None
        from_ = to = None
        for f in points_filled:
            for t in points_to_fill:
                dist = _distance_between_points(r, f, t)
                if shortest_distance is None or dist < shortest_distance:
                    from_, to, shortest_distance = f, t, dist
        _fill_between_points(level, r, from_, to, floor)
        points_filled.append(to)
        points_to_fill.remove(to)


class PerimeterRoom(ConnectionRoom):
    """Tunnels along the room's perimeter."""

    def paint(self, level, rng: SPDRandom) -> None:
        floor = level.tunnel_tile()

        _fill_perimeter_paths(level, self, floor)

        for door in self.connected.values():
            door.set(DoorType.TUNNEL)


class WalkwayRoom(PerimeterRoom):
    def paint(self, level, rng: SPDRandom) -> None:
        if min(self.width(), self.height()) > 3:
            Painter.fill(level, self, 1, terrain.CHASM)

        super().paint(level, rng)

        _fill_neighbour_chasm(level, self)

    def can_merge(self, level, other: "Room", p: Point, merge_terrain: int) -> bool:
        return merge_terrain == terrain.CHASM


class RingTunnelRoom(TunnelRoom):
    def __init__(self):
        super().__init__()
        self._conn_space: Optional[Rect] = None

    def min_width(self) -> int:
        return max(5, super().min_width())

    def min_height(self) -> int:
        return max(5, super().min_height())

    def paint(self, level, rng: SPDRandom) -> None:
        super().paint(level, rng)

        floor = level.tunnel_tile()
        ring = self._get_connection_space(rng)

        Painter.fill(level, ring.left, ring.top, 3, 3, floor)
        Painter.fill(level, ring.left + 1, ring.top + 1, 1, 1, terrain.WALL)

    def _get_connection_space(self, rng: SPDRandom) -> Rect:
        """Caches the value so multiple calls always return the same."""
        if self._conn_space is None:
            c = self._get_door_center(rng)
            c.x = int(gate(self.left + 2, c.x, self.right - 2))
            c.y = int(gate(self.top + 2, c.y, self.bottom - 2))
            self._conn_space = Rect(c.x - 1, c.y - 1, c.x + 1, c.y + 1)
        return self._conn_space


class RingBridgeRoom(RingTunnelRoom):
    def paint(self, level, rng: SPDRandom) -> None:
        Painter.fill(level, self, 1, terrain.CHASM)

        super().paint(level, rng)

        _fill_neighbour_chasm(level, self)

    def can_merge(self, level, other: "Room", p: Point, merge_terrain: int) -> bool:
        return merge_terrain == terrain.CHASM


# Order matters: matches ConnectionRoom.rooms registration order, indexed by Random.chances()
CONNECTION_ROOM_TYPES = (
    TunnelRoom,
    BridgeRoom,
    PerimeterRoom,
    WalkwayRoom,
    RingTunnelRoom,
    RingBridgeRoom,
)


def create_connection_room(rng, depth: int) -> ConnectionRoom:
    """Port of ConnectionRoom.createRoom() -- picks a class via Random.chances(chances[depth])."""
    weights = CONNECTION_ROOM_CHANCES[depth]
    idx = rng.chances(weights)
    return CONNECTION_ROOM_TYPES[idx]()


class MazeConnectionRoom(ConnectionRoom):
    def max_connections(self, direction: int) -> int:
        return 2

    def paint(self, level, rng: SPDRandom) -> None:
        Painter.fill(level, self, 1, terrain.EMPTY)

        maze.allow_diagonals = False
        m = maze.generate_for_room(rng, self)

        while (self.width() >= 5 and self.height() >= 5
                and (self.width() <= 7 or self.height() <= 7)
                and m[self.width() // 2][self.height() // 2] == maze.EMPTY):
            m = maze.generate_for_room(rng, self)

        Painter.fill(level, self, 1, terrain.EMPTY)
        for x in range(len(m)):
            for y in range(len(m[0])):
                if m[x][y] == maze.FILLED:
                    Painter.fill(level, x + self.left, y + self.top, 1, 1, terrain.WALL)

        for door in self.connected.values():
            door.set(DoorType.HIDDEN)
