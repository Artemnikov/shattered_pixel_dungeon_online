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
"""Port of com.watabou.utils.{Point,Rect,PointF,GameMath} -- minimal surface
needed by the level-gen port. Field/method names mirror the Java originals so
the generation code can be transliterated near-verbatim.
"""

from __future__ import annotations

import math
from typing import List

from app.engine.dungeon.spd_random import SPDRandom


class Point:
    __slots__ = ("x", "y")

    def __init__(self, x: int = 0, y: int = 0):
        self.x = x
        self.y = y

    def clone(self) -> "Point":
        return Point(self.x, self.y)

    def offset(self, dx: int, dy: int) -> "Point":
        self.x += dx
        self.y += dy
        return self

    def __eq__(self, other):
        return isinstance(other, Point) and self.x == other.x and self.y == other.y

    def __hash__(self):
        return hash((self.x, self.y))

    def __repr__(self):
        return f"Point({self.x}, {self.y})"


class PointF:
    __slots__ = ("x", "y")

    def __init__(self, x: float = 0.0, y: float = 0.0):
        self.x = x
        self.y = y


def gate(min_: float, value: float, max_: float) -> float:
    if value < min_:
        return min_
    if value > max_:
        return max_
    return value


class Rect:
    def __init__(self, left: int = 0, top: int = 0, right: int = 0, bottom: int = 0):
        self.left = left
        self.top = top
        self.right = right
        self.bottom = bottom

    @classmethod
    def from_rect(cls, other: "Rect") -> "Rect":
        return cls(other.left, other.top, other.right, other.bottom)

    def width(self) -> int:
        return self.right - self.left

    def height(self) -> int:
        return self.bottom - self.top

    def square(self) -> int:
        return self.width() * self.height()

    def set(self, left: int, top: int, right: int, bottom: int) -> "Rect":
        self.left, self.top, self.right, self.bottom = left, top, right, bottom
        return self

    def set_rect(self, rect: "Rect") -> "Rect":
        return self.set(rect.left, rect.top, rect.right, rect.bottom)

    def set_pos(self, x: int, y: int) -> "Rect":
        return self.set(x, y, x + (self.right - self.left), y + (self.bottom - self.top))

    def shift(self, x: int, y: int) -> "Rect":
        return self.set(self.left + x, self.top + y, self.right + x, self.bottom + y)

    def resize(self, w: int, h: int) -> "Rect":
        return self.set(self.left, self.top, self.left + w, self.top + h)

    def is_empty(self) -> bool:
        return self.right <= self.left or self.bottom <= self.top

    def set_empty(self) -> "Rect":
        self.left = self.right = self.top = self.bottom = 0
        return self

    def intersect(self, other: "Rect") -> "Rect":
        return Rect(
            max(self.left, other.left),
            max(self.top, other.top),
            min(self.right, other.right),
            min(self.bottom, other.bottom),
        )

    def union_rect(self, other: "Rect") -> "Rect":
        return Rect(
            min(self.left, other.left),
            min(self.top, other.top),
            max(self.right, other.right),
            max(self.bottom, other.bottom),
        )

    def union(self, x: int, y: int) -> "Rect":
        if self.is_empty():
            return self.set(x, y, x + 1, y + 1)
        if x < self.left:
            self.left = x
        elif x >= self.right:
            self.right = x + 1
        if y < self.top:
            self.top = y
        elif y >= self.bottom:
            self.bottom = y + 1
        return self

    def union_point(self, p: Point) -> "Rect":
        return self.union(p.x, p.y)

    def inside(self, p: Point) -> bool:
        return self.left <= p.x < self.right and self.top <= p.y < self.bottom

    def center(self, rng: SPDRandom) -> Point:
        return Point(
            (self.left + self.right) // 2 + (rng.IntMax(2) if (self.right - self.left) % 2 == 0 else 0),
            (self.top + self.bottom) // 2 + (rng.IntMax(2) if (self.bottom - self.top) % 2 == 0 else 0),
        )

    def shrink(self, d: int = 1) -> "Rect":
        return Rect(self.left + d, self.top + d, self.right - d, self.bottom - d)

    def scale(self, d: int) -> "Rect":
        return Rect(self.left * d, self.top * d, self.right * d, self.bottom * d)

    def get_points(self) -> List[Point]:
        points = []
        for i in range(self.left, self.right + 1):
            for j in range(self.top, self.bottom + 1):
                points.append(Point(i, j))
        return points


A = 180.0 / math.pi


def _f32_div(a: float, b: float) -> float:
    """Java/IEEE-754 float division: x/0 -> +-Infinity (sign of x times sign
    of zero), 0/0 -> NaN -- never raises, unlike Python's `/`."""
    if b != 0.0:
        return a / b
    if a == 0.0:
        return math.nan
    return math.copysign(math.inf, a) * math.copysign(1.0, b)


def angle_between_points(from_: PointF, to: PointF) -> float:
    """float(A * (atan(m) + pi/2)), m = dy/dx -- matches Builder.angleBetweenPoints.

    `m` is `(to.y - from.y)/(to.x - from.x)` computed as Java `float` (32-bit)
    division, then widened to double -- the float32 rounding of the
    intermediate subtractions and the division itself must be preserved.
    Java float division by zero yields +-Infinity/NaN rather than raising
    (Math.atan(+-Infinity) = +-pi/2, matching Python's math.atan)."""
    dy = _to_f32(to.y - from_.y)
    dx = _to_f32(to.x - from_.x)
    m = _to_f32(_f32_div(dy, dx))
    angle = _to_f32(A * (math.atan(m) + math.pi / 2.0))
    if from_.x > to.x:
        angle = _to_f32(angle - 180.0)
    return angle


def _to_f32(x: float) -> float:
    import struct

    return struct.unpack(">f", struct.pack(">f", x))[0]
