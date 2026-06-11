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
"""Port of levels/builders/{Builder,RegularBuilder,LoopBuilder,FigureEightBuilder}.java"""

from __future__ import annotations

import math
from typing import List, Optional

from app.engine.dungeon.spd_levelgen.connection_rooms import (
    ConnectionRoom,
    MazeConnectionRoom,
    create_connection_room,
)
from app.engine.dungeon.spd_levelgen.geom import PointF, Rect, _to_f32, angle_between_points
from app.engine.dungeon.spd_levelgen.room import BOTTOM, LEFT, RIGHT, TOP, Point, Room
from app.engine.dungeon.spd_levelgen.room_types import SecretRoom, ShopRoom, StandardRoom
from app.engine.dungeon.spd_random import SPDRandom

A = 180.0 / math.pi


class Builder:
    """Abstract: build(rooms, rng, depth) -> connected room list, or None on failure."""

    def build(self, rooms: List[Room], rng: SPDRandom, depth: int) -> Optional[List[Room]]:
        raise NotImplementedError

    @staticmethod
    def find_neighbours(rooms: List[Room]) -> None:
        for i in range(len(rooms) - 1):
            for j in range(i + 1, len(rooms)):
                rooms[i].add_neighbour(rooms[j])

    @staticmethod
    def find_free_space(start: Point, collision: List[Room], max_size: int) -> Rect:
        space = Rect(start.x - max_size, start.y - max_size, start.x + max_size, start.y + max_size)

        colliding = list(collision)
        while True:
            colliding = [
                room for room in colliding
                if not (room.is_empty()
                        or max(space.left, room.left) >= min(space.right, room.right)
                        or max(space.top, room.top) >= min(space.bottom, room.bottom))
            ]

            closest_room = None
            closest_diff = 0x7FFFFFFF
            inside = True
            cur_diff = 0
            for cur_room in colliding:
                if start.x <= cur_room.left:
                    inside = False
                    cur_diff += cur_room.left - start.x
                elif start.x >= cur_room.right:
                    inside = False
                    cur_diff += start.x - cur_room.right

                if start.y <= cur_room.top:
                    inside = False
                    cur_diff += cur_room.top - start.y
                elif start.y >= cur_room.bottom:
                    inside = False
                    cur_diff += start.y - cur_room.bottom

                if inside:
                    space.set(start.x, start.y, start.x, start.y)
                    return space

                if cur_diff < closest_diff:
                    closest_diff = cur_diff
                    closest_room = cur_room

            if closest_room is not None:
                w_diff = 0x7FFFFFFF
                if closest_room.left >= start.x:
                    w_diff = (space.right - closest_room.left) * (space.height() + 1)
                elif closest_room.right <= start.x:
                    w_diff = (closest_room.right - space.left) * (space.height() + 1)

                h_diff = 0x7FFFFFFF
                if closest_room.top >= start.y:
                    h_diff = (space.bottom - closest_room.top) * (space.width() + 1)
                elif closest_room.bottom <= start.y:
                    h_diff = (closest_room.bottom - space.top) * (space.width() + 1)

                if w_diff < h_diff or (w_diff == h_diff and Builder._rng.IntMax(2) == 0):
                    if closest_room.left >= start.x and closest_room.left < space.right:
                        space.right = closest_room.left
                    if closest_room.right <= start.x and closest_room.right > space.left:
                        space.left = closest_room.right
                else:
                    if closest_room.top >= start.y and closest_room.top < space.bottom:
                        space.bottom = closest_room.top
                    if closest_room.bottom <= start.y and closest_room.bottom > space.top:
                        space.top = closest_room.bottom
                colliding.remove(closest_room)
            else:
                colliding.clear()

            if not colliding:
                return space

    @staticmethod
    def angle_between_rooms(from_: Room, to: Room) -> float:
        from_center = PointF((from_.left + from_.right) / 2.0, (from_.top + from_.bottom) / 2.0)
        to_center = PointF((to.left + to.right) / 2.0, (to.top + to.bottom) / 2.0)
        return angle_between_points(from_center, to_center)

    @staticmethod
    def place_room(collision: List[Room], prev: Room, next_: Room, angle: float) -> float:
        angle = angle % 360.0
        if angle < 0:
            angle += 360.0

        prev_center = PointF((prev.left + prev.right) / 2.0, (prev.top + prev.bottom) / 2.0)

        m = math.tan(angle / A + math.pi / 2.0)
        b = prev_center.y - m * prev_center.x

        if abs(m) >= 1:
            if angle < 90 or angle > 270:
                direction = TOP
                start = Point(_round_double((prev.top - b) / m), prev.top)
            else:
                direction = BOTTOM
                start = Point(_round_double((prev.bottom - b) / m), prev.bottom)
        else:
            if angle < 180:
                direction = RIGHT
                start = Point(prev.right, _round_double(m * prev.right + b))
            else:
                direction = LEFT
                start = Point(prev.left, _round_double(m * prev.left + b))

        if direction == TOP or direction == BOTTOM:
            start.x = int(_gate(prev.left + 1, start.x, prev.right - 1))
        else:
            start.y = int(_gate(prev.top + 1, start.y, prev.bottom - 1))

        space = Builder.find_free_space(start, collision, max(next_.max_width(), next_.max_height()))
        if not next_.set_size_with_limit(Builder._rng, space.width() + 1, space.height() + 1):
            return -1

        # Java PointF fields are `float` (32-bit); every assignment/expression that
        # crosses into a float value gets implicitly rounded to float32, and
        # Math.round(float) operates on that rounded value -- _to_f32 reproduces
        # those truncation points so the resulting ints match exactly.
        target_center = PointF()
        if direction == TOP:
            target_center.y = _to_f32(prev.top - _to_f32((next_.height() - 1) / 2.0))
            target_center.x = _to_f32((target_center.y - b) / m)
            next_.set_pos(_round_float(_to_f32(target_center.x - _to_f32((next_.width() - 1) / 2.0))),
                          prev.top - (next_.height() - 1))
        elif direction == BOTTOM:
            target_center.y = _to_f32(prev.bottom + _to_f32((next_.height() - 1) / 2.0))
            target_center.x = _to_f32((target_center.y - b) / m)
            next_.set_pos(_round_float(_to_f32(target_center.x - _to_f32((next_.width() - 1) / 2.0))),
                          prev.bottom)
        elif direction == RIGHT:
            target_center.x = _to_f32(prev.right + _to_f32((next_.width() - 1) / 2.0))
            target_center.y = _to_f32(m * target_center.x + b)
            next_.set_pos(prev.right,
                          _round_float(_to_f32(target_center.y - _to_f32((next_.height() - 1) / 2.0))))
        elif direction == LEFT:
            target_center.x = _to_f32(prev.left - _to_f32((next_.width() - 1) / 2.0))
            target_center.y = _to_f32(m * target_center.x + b)
            next_.set_pos(prev.left - (next_.width() - 1),
                          _round_float(_to_f32(target_center.y - _to_f32((next_.height() - 1) / 2.0))))

        if direction == TOP or direction == BOTTOM:
            if next_.right < prev.left + 2:
                next_.shift(prev.left + 2 - next_.right, 0)
            elif next_.left > prev.right - 2:
                next_.shift(prev.right - 2 - next_.left, 0)

            if next_.right > space.right:
                next_.shift(space.right - next_.right, 0)
            elif next_.left < space.left:
                next_.shift(space.left - next_.left, 0)
        else:
            if next_.bottom < prev.top + 2:
                next_.shift(0, prev.top + 2 - next_.bottom)
            elif next_.top > prev.bottom - 2:
                next_.shift(0, prev.bottom - 2 - next_.top)

            if next_.bottom > space.bottom:
                next_.shift(0, space.bottom - next_.bottom)
            elif next_.top < space.top:
                next_.shift(0, space.top - next_.top)

        if next_.connect(prev):
            return Builder.angle_between_rooms(prev, next_)
        return -1

    # Builder.build() is a static-method-heavy abstract class in Java; the port
    # threads `rng`/`depth` through every call instead of relying on globals
    # (Random.* / Dungeon.depth). `_rng`/`_depth` are bound for the duration of
    # a single build() call so the static-style helpers above can use them --
    # mirrors how the Java code implicitly uses Random's thread-local stack.
    _rng: SPDRandom = None
    _depth: int = None


def _gate(min_: float, value: float, max_: float) -> float:
    if value < min_:
        return min_
    if value > max_:
        return max_
    return value


def _round_double(x: float) -> int:
    """Math.round(double): (int)(long)floor(x + 0.5) in double precision."""
    return int(math.floor(x + 0.5))


def _round_float(x: float) -> int:
    """Math.round(float): (int)floor(x + 0.5f), with the addition done in float32 --
    differs from both Python's round() (banker's rounding) and _round_double."""
    return int(math.floor(_to_f32(x + 0.5)))


class RegularBuilder(Builder):
    def __init__(self):
        self.path_variance = 45.0
        self.path_length = 0.25
        self.path_len_jitter_chances = [0.0, 0.0, 0.0, 1.0]
        self.path_tunnel_chances = [2.0, 2.0, 1.0]
        self.branch_tunnel_chances = [1.0, 1.0, 0.0]
        self.extra_connection_chance = 0.30

        self.entrance: Optional[Room] = None
        self.exit: Optional[Room] = None
        self.shop: Optional[Room] = None

        self.main_path_rooms: List[Room] = []
        self.multi_connections: List[Room] = []
        self.single_connections: List[Room] = []

    def set_path_variance(self, var: float) -> "RegularBuilder":
        self.path_variance = var
        return self

    def set_path_length(self, length: float, jitter: List[float]) -> "RegularBuilder":
        self.path_length = length
        self.path_len_jitter_chances = jitter
        return self

    def set_tunnel_length(self, path: List[float], branch: List[float]) -> "RegularBuilder":
        self.path_tunnel_chances = path
        self.branch_tunnel_chances = branch
        return self

    def set_extra_connection_chance(self, chance: float) -> "RegularBuilder":
        self.extra_connection_chance = chance
        return self

    def setup_rooms(self, rooms: List[Room], rng: SPDRandom) -> None:
        for r in rooms:
            r.set_empty()

        self.entrance = self.exit = self.shop = None
        self.main_path_rooms.clear()
        self.single_connections.clear()
        self.multi_connections.clear()

        for r in rooms:
            if r.is_entrance():
                self.entrance = r
            elif r.is_exit():
                self.exit = r
            elif isinstance(r, ShopRoom) and r.max_connections(0) == 1:
                self.shop = r
            elif r.max_connections(0) > 1:
                self.multi_connections.append(r)
            elif r.max_connections(0) == 1:
                self.single_connections.append(r)

        self.weight_rooms(self.multi_connections)
        rng.shuffle(self.multi_connections)
        seen = []
        for r in self.multi_connections:
            if r not in seen:
                seen.append(r)
        self.multi_connections = seen
        rng.shuffle(self.multi_connections)

        rooms_on_main_path = int(len(self.multi_connections) * self.path_length) + rng.chances(self.path_len_jitter_chances)

        while rooms_on_main_path > 0 and self.multi_connections:
            r = self.multi_connections.pop(0)
            if isinstance(r, StandardRoom):
                rooms_on_main_path -= r.size_factor()
            else:
                rooms_on_main_path -= 1
            self.main_path_rooms.append(r)

    @staticmethod
    def weight_rooms(rooms: List[Room]) -> None:
        for r in list(rooms):
            if isinstance(r, StandardRoom):
                for _ in range(1, r.connection_weight()):
                    rooms.append(r)

    def create_branches(self, rooms: List[Room], branchable: List[Room],
                         rooms_to_branch: List[Room], conn_chances: List[float],
                         rng: SPDRandom, depth: int) -> bool:
        i = 0
        connecting_rooms_this_branch: List[Room] = []
        failed_branch_attempts = 0
        connection_chances = list(conn_chances)

        while i < len(rooms_to_branch):
            if failed_branch_attempts > 100:
                return False

            r = rooms_to_branch[i]
            connecting_rooms_this_branch.clear()

            while True:
                curr = rng.element(branchable)
                if not (isinstance(r, SecretRoom) and isinstance(curr, ConnectionRoom)):
                    break

            connecting_rooms = rng.chances(connection_chances)
            if connecting_rooms == -1:
                connection_chances = list(conn_chances)
                connecting_rooms = rng.chances(connection_chances)
            connection_chances[connecting_rooms] -= 1

            for _ in range(connecting_rooms):
                t: ConnectionRoom = MazeConnectionRoom() if isinstance(r, SecretRoom) else create_connection_room(rng, depth)
                tries = 3
                while True:
                    angle = Builder.place_room(rooms, curr, t, self.random_branch_angle(curr, rng))
                    tries -= 1
                    if angle != -1 or tries <= 0:
                        break

                if angle == -1:
                    t.clear_connections()
                    for c in connecting_rooms_this_branch:
                        c.clear_connections()
                        rooms.remove(c)
                    connecting_rooms_this_branch.clear()
                    break
                else:
                    connecting_rooms_this_branch.append(t)
                    rooms.append(t)

                curr = t

            if len(connecting_rooms_this_branch) != connecting_rooms:
                failed_branch_attempts += 1
                continue

            tries = 10
            while True:
                angle = Builder.place_room(rooms, curr, r, self.random_branch_angle(curr, rng))
                tries -= 1
                if angle != -1 or tries <= 0:
                    break

            if angle == -1:
                r.clear_connections()
                for t in connecting_rooms_this_branch:
                    t.clear_connections()
                    rooms.remove(t)
                connecting_rooms_this_branch.clear()
                failed_branch_attempts += 1
                continue

            for t in connecting_rooms_this_branch:
                if rng.IntMax(3) <= 1:
                    branchable.append(t)
            if r.max_connections(0) > 1 and rng.IntMax(3) == 0:
                if isinstance(r, StandardRoom):
                    for _ in range(r.connection_weight()):
                        branchable.append(r)
                else:
                    branchable.append(r)

            i += 1

        return True

    def random_branch_angle(self, r: Room, rng: SPDRandom) -> float:
        return rng.FloatMax(360.0)


class _CurvedLoopMixin:
    """Shared loop-shape math for LoopBuilder/FigureEightBuilder."""

    curve_exponent = 0
    curve_intensity = 1.0
    curve_offset = 0.0

    def set_loop_shape(self, exponent: int, intensity: float, offset: float):
        self.curve_exponent = abs(exponent)
        self.curve_intensity = math.fmod(intensity, 1.0)
        self.curve_offset = math.fmod(offset, 0.5)
        return self

    def _target_angle(self, percent_along: float) -> float:
        # Mirrors Java's float32 truncation points: percentAlong += curveOffset
        # (float), the big expression cast to float BEFORE the 360f multiply,
        # then the final float*float product.
        percent_along = _to_f32(percent_along + self.curve_offset)
        inner = _to_f32(
            self.curve_intensity * self._curve_equation(percent_along)
            + _to_f32((1.0 - self.curve_intensity) * percent_along)
            - self.curve_offset
        )
        return _to_f32(360.0 * inner)

    def _curve_equation(self, x: float) -> float:
        return (math.pow(4, 2 * self.curve_exponent)
                * math.pow(math.fmod(x, 0.5) - 0.25, 2 * self.curve_exponent + 1)
                + 0.25 + 0.5 * math.floor(2 * x))


class LoopBuilder(RegularBuilder, _CurvedLoopMixin):
    def __init__(self):
        RegularBuilder.__init__(self)
        self.loop_center: Optional[PointF] = None

    def build(self, rooms: List[Room], rng: SPDRandom, depth: int) -> Optional[List[Room]]:
        Builder._rng, Builder._depth = rng, depth
        self.setup_rooms(rooms, rng)

        if self.entrance is None:
            return None

        self.entrance.set_size(rng)
        self.entrance.set_pos(0, 0)

        start_angle = rng.FloatRange(0.0, 360.0)

        self.main_path_rooms.insert(0, self.entrance)
        if self.exit is not None:
            self.main_path_rooms.insert((len(self.main_path_rooms) + 1) // 2, self.exit)

        loop: List[Room] = []
        path_tunnels = list(self.path_tunnel_chances)
        for r in self.main_path_rooms:
            loop.append(r)

            tunnels = rng.chances(path_tunnels)
            if tunnels == -1:
                path_tunnels = list(self.path_tunnel_chances)
                tunnels = rng.chances(path_tunnels)
            path_tunnels[tunnels] -= 1

            for _ in range(tunnels):
                loop.append(create_connection_room(rng, depth))

        prev = self.entrance
        for i in range(1, len(loop)):
            r = loop[i]
            target_angle = _to_f32(start_angle + self._target_angle(_to_f32(i / float(len(loop)))))
            if Builder.place_room(rooms, prev, r, target_angle) != -1:
                prev = r
                if prev not in rooms:
                    rooms.append(prev)
            else:
                return None

        while not prev.connect(self.entrance):
            c = create_connection_room(rng, depth)
            if Builder.place_room(loop, prev, c, Builder.angle_between_rooms(prev, self.entrance)) == -1:
                return None
            loop.append(c)
            rooms.append(c)
            prev = c

        if self.shop is not None:
            tries = 10
            while True:
                angle = Builder.place_room(loop, self.entrance, self.shop, rng.FloatMax(360.0))
                tries -= 1
                if not (angle == -1 and tries >= 0):
                    break
            if angle == -1:
                return None

        self.loop_center = PointF()
        for r in loop:
            self.loop_center.x = _to_f32(self.loop_center.x + (r.left + r.right) / 2.0)
            self.loop_center.y = _to_f32(self.loop_center.y + (r.top + r.bottom) / 2.0)
        self.loop_center.x = _to_f32(self.loop_center.x / len(loop))
        self.loop_center.y = _to_f32(self.loop_center.y / len(loop))

        branchable = list(loop)

        rooms_to_branch = list(self.multi_connections) + list(self.single_connections)
        self.weight_rooms(branchable)
        if not self.create_branches(rooms, branchable, rooms_to_branch, self.branch_tunnel_chances, rng, depth):
            return None

        Builder.find_neighbours(rooms)

        for r in rooms:
            for n in r.neighbours:
                if r not in n.connected and rng.Float() < self.extra_connection_chance:
                    r.connect(n)

        return rooms

    def random_branch_angle(self, r: Room, rng: SPDRandom) -> float:
        if self.loop_center is None:
            return super().random_branch_angle(r, rng)

        to_center = angle_between_points(PointF((r.left + r.right) / 2.0, (r.top + r.bottom) / 2.0), self.loop_center)
        if to_center < 0:
            to_center = _to_f32(to_center + 360.0)

        curr_angle = rng.FloatMax(360.0)
        for _ in range(4):
            new_angle = rng.FloatMax(360.0)
            if abs(_to_f32(to_center - new_angle)) < abs(_to_f32(to_center - curr_angle)):
                curr_angle = new_angle
        return curr_angle


class FigureEightBuilder(RegularBuilder, _CurvedLoopMixin):
    def __init__(self):
        RegularBuilder.__init__(self)
        self.landmark_room: Optional[Room] = None
        self.first_loop: List[Room] = []
        self.second_loop: List[Room] = []
        self.first_loop_center: Optional[PointF] = None
        self.second_loop_center: Optional[PointF] = None

    def set_landmark_room(self, room: Room) -> "FigureEightBuilder":
        self.landmark_room = room
        return self

    def build(self, rooms: List[Room], rng: SPDRandom, depth: int) -> Optional[List[Room]]:
        Builder._rng, Builder._depth = rng, depth
        self.setup_rooms(rooms, rng)

        if self.landmark_room is None:
            for r in self.main_path_rooms:
                if (r.max_connections(0) >= 4
                        and (self.landmark_room is None
                             or self.landmark_room.min_width() * self.landmark_room.min_height()
                             < r.min_width() * r.min_height())):
                    self.landmark_room = r
            if self.multi_connections:
                self.main_path_rooms.append(self.multi_connections.pop(0))

        if self.landmark_room in self.main_path_rooms:
            self.main_path_rooms.remove(self.landmark_room)
        if self.landmark_room in self.multi_connections:
            self.multi_connections.remove(self.landmark_room)

        start_angle = rng.FloatRange(0.0, 360.0)

        rooms_on_first_loop = len(self.main_path_rooms) // 2
        if len(self.main_path_rooms) % 2 == 1:
            rooms_on_first_loop += rng.IntMax(2)

        rooms_to_loop = list(self.main_path_rooms)

        first_loop_temp = [self.landmark_room]
        for _ in range(rooms_on_first_loop):
            first_loop_temp.append(rooms_to_loop.pop(0))
        first_loop_temp.insert((len(first_loop_temp) + 1) // 2, self.entrance)

        path_tunnels = list(self.path_tunnel_chances)

        self.first_loop = []
        for r in first_loop_temp:
            self.first_loop.append(r)
            tunnels = rng.chances(path_tunnels)
            if tunnels == -1:
                path_tunnels = list(self.path_tunnel_chances)
                tunnels = rng.chances(path_tunnels)
            path_tunnels[tunnels] -= 1
            for _ in range(tunnels):
                self.first_loop.append(create_connection_room(rng, depth))

        second_loop_temp = [self.landmark_room] + rooms_to_loop
        if self.exit is not None:
            second_loop_temp.insert((len(second_loop_temp) + 1) // 2, self.exit)

        self.second_loop = []
        for r in second_loop_temp:
            self.second_loop.append(r)
            tunnels = rng.chances(path_tunnels)
            if tunnels == -1:
                path_tunnels = list(self.path_tunnel_chances)
                tunnels = rng.chances(path_tunnels)
            path_tunnels[tunnels] -= 1
            for _ in range(tunnels):
                self.second_loop.append(create_connection_room(rng, depth))

        self.landmark_room.set_size(rng)
        self.landmark_room.set_pos(0, 0)

        prev = self.landmark_room
        for i in range(1, len(self.first_loop)):
            r = self.first_loop[i]
            target_angle = _to_f32(start_angle + self._target_angle(_to_f32(i / float(len(self.first_loop)))))
            if Builder.place_room(rooms, prev, r, target_angle) != -1:
                prev = r
                if prev not in rooms:
                    rooms.append(prev)
            else:
                return None

        while not prev.connect(self.landmark_room):
            c = create_connection_room(rng, depth)
            if Builder.place_room(rooms, prev, c, Builder.angle_between_rooms(prev, self.landmark_room)) == -1:
                return None
            self.first_loop.append(c)
            rooms.append(c)
            prev = c

        prev = self.landmark_room
        start_angle = _to_f32(start_angle + 180.0)
        for i in range(1, len(self.second_loop)):
            r = self.second_loop[i]
            target_angle = _to_f32(start_angle + self._target_angle(_to_f32(i / float(len(self.second_loop)))))
            if Builder.place_room(rooms, prev, r, target_angle) != -1:
                prev = r
                if prev not in rooms:
                    rooms.append(prev)
            else:
                return None

        while not prev.connect(self.landmark_room):
            c = create_connection_room(rng, depth)
            if Builder.place_room(rooms, prev, c, Builder.angle_between_rooms(prev, self.landmark_room)) == -1:
                return None
            self.second_loop.append(c)
            rooms.append(c)
            prev = c

        if self.shop is not None:
            tries = 10
            while True:
                angle = Builder.place_room(rooms, self.entrance, self.shop, rng.FloatMax(360.0))
                tries -= 1
                if not (angle == -1 and tries >= 0):
                    break
            if angle == -1:
                return None

        self.first_loop_center = PointF()
        for r in self.first_loop:
            self.first_loop_center.x = _to_f32(self.first_loop_center.x + (r.left + r.right) / 2.0)
            self.first_loop_center.y = _to_f32(self.first_loop_center.y + (r.top + r.bottom) / 2.0)
        self.first_loop_center.x = _to_f32(self.first_loop_center.x / len(self.first_loop))
        self.first_loop_center.y = _to_f32(self.first_loop_center.y / len(self.first_loop))

        self.second_loop_center = PointF()
        for r in self.second_loop:
            self.second_loop_center.x = _to_f32(self.second_loop_center.x + (r.left + r.right) / 2.0)
            self.second_loop_center.y = _to_f32(self.second_loop_center.y + (r.top + r.bottom) / 2.0)
        self.second_loop_center.x = _to_f32(self.second_loop_center.x / len(self.second_loop))
        self.second_loop_center.y = _to_f32(self.second_loop_center.y / len(self.second_loop))

        branchable = list(self.first_loop) + list(self.second_loop)
        if self.landmark_room in branchable:
            branchable.remove(self.landmark_room)

        rooms_to_branch = list(self.multi_connections) + list(self.single_connections)
        self.weight_rooms(branchable)
        if not self.create_branches(rooms, branchable, rooms_to_branch, self.branch_tunnel_chances, rng, depth):
            return None

        Builder.find_neighbours(rooms)

        for r in rooms:
            for n in r.neighbours:
                if r not in n.connected and rng.Float() < self.extra_connection_chance:
                    r.connect(n)

        return rooms

    def random_branch_angle(self, r: Room, rng: SPDRandom) -> float:
        center = self.first_loop_center if r in self.first_loop else self.second_loop_center
        if center is None:
            return super().random_branch_angle(r, rng)

        to_center = angle_between_points(PointF((r.left + r.right) / 2.0, (r.top + r.bottom) / 2.0), center)
        if to_center < 0:
            to_center = _to_f32(to_center + 360.0)

        curr_angle = rng.FloatMax(360.0)
        for _ in range(4):
            new_angle = rng.FloatMax(360.0)
            if abs(_to_f32(to_center - new_angle)) < abs(_to_f32(to_center - curr_angle)):
                curr_angle = new_angle
        return curr_angle
