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
"""Port of com.shatteredpixel.shatteredpixeldungeon.levels.painters.Painter --
static tile-stamping helpers shared by all concrete painters."""

from __future__ import annotations

import math
from typing import Optional

from app.engine.dungeon.spd_levelgen.geom import Point, _f32_div, _to_f32
from app.engine.dungeon.spd_levelgen.room import Room


def _round_f32(x: float) -> int:
    """Java Math.round(float): floor(x + 0.5), computed in float32."""
    return math.floor(_to_f32(_to_f32(x) + 0.5))


class Painter:

    @staticmethod
    def set(level, x, y=None, value: Optional[int] = None) -> None:
        """Overload-collapsed: set(level, cell, value) / set(level, x, y, value) /
        set(level, point, value)."""
        if value is None:
            # set(level, cell_or_point, value) -- two positional args after level
            value = y
            if isinstance(x, Point):
                cell = x.x + x.y * level.width()
            else:
                cell = x
        else:
            cell = x + y * level.width()
        level.map[cell] = value

    @staticmethod
    def fill(level, *args) -> None:
        """Overload-collapsed:
        fill(level, x, y, w, h, value)               -- 5 args
        fill(level, rect, value)                     -- 2 args
        fill(level, rect, m, value)                  -- 3 args
        fill(level, rect, l, t, r, b, value)         -- 6 args
        """
        width = level.width()
        if len(args) == 5:
            x, y, w, h, value = args
            _fill_xywh(level, width, x, y, w, h, value)
        elif len(args) == 2:
            rect, value = args
            _fill_xywh(level, width, rect.left, rect.top, rect.width(), rect.height(), value)
        elif len(args) == 3:
            rect, m, value = args
            _fill_xywh(level, width, rect.left + m, rect.top + m,
                       rect.width() - m * 2, rect.height() - m * 2, value)
        elif len(args) == 6:
            rect, l, t, r, b, value = args
            _fill_xywh(level, width, rect.left + l, rect.top + t,
                       rect.width() - (l + r), rect.height() - (t + b), value)
        else:
            raise TypeError("unsupported Painter.fill overload")

    @staticmethod
    def draw_line(level, from_: Point, to: Point, value: int) -> None:
        x = float(from_.x)
        y = float(from_.y)
        dx = _to_f32(float(to.x - from_.x))
        dy = _to_f32(float(to.y - from_.y))

        moving_by_x = abs(dx) >= abs(dy)
        if moving_by_x:
            dy = _to_f32(_f32_div(dy, abs(dx)))
            dx = _to_f32(_f32_div(dx, abs(dx)))
        else:
            dx = _to_f32(_f32_div(dx, abs(dy)))
            dy = _to_f32(_f32_div(dy, abs(dy)))

        Painter.set(level, _round_f32(x), _round_f32(y), value)
        while (moving_by_x and to.x != x) or (not moving_by_x and to.y != y):
            x = _to_f32(x + dx)
            y = _to_f32(y + dy)
            Painter.set(level, _round_f32(x), _round_f32(y), value)

    @staticmethod
    def fill_ellipse(level, *args) -> None:
        """fill_ellipse(level, rect, value) / (level, rect, m, value) /
        (level, x, y, w, h, value)"""
        if len(args) == 2:
            rect, value = args
            _fill_ellipse_xywh(level, rect.left, rect.top, rect.width(), rect.height(), value)
        elif len(args) == 3:
            rect, m, value = args
            _fill_ellipse_xywh(level, rect.left + m, rect.top + m,
                               rect.width() - m * 2, rect.height() - m * 2, value)
        elif len(args) == 5:
            x, y, w, h, value = args
            _fill_ellipse_xywh(level, x, y, w, h, value)
        else:
            raise TypeError("unsupported Painter.fill_ellipse overload")

    @staticmethod
    def fill_diamond(level, *args) -> None:
        """fill_diamond(level, rect, value) / (level, rect, m, value) /
        (level, x, y, w, h, value)"""
        if len(args) == 2:
            rect, value = args
            _fill_diamond_xywh(level, rect.left, rect.top, rect.width(), rect.height(), value)
        elif len(args) == 3:
            rect, m, value = args
            _fill_diamond_xywh(level, rect.left + m, rect.top + m,
                               rect.width() - m * 2, rect.height() - m * 2, value)
        elif len(args) == 5:
            x, y, w, h, value = args
            _fill_diamond_xywh(level, x, y, w, h, value)
        else:
            raise TypeError("unsupported Painter.fill_diamond overload")

    @staticmethod
    def draw_inside(level, room: Room, from_: Point, n: int, value: int) -> Point:
        step = Point()
        if from_.x == room.left:
            step.x, step.y = +1, 0
        elif from_.x == room.right:
            step.x, step.y = -1, 0
        elif from_.y == room.top:
            step.x, step.y = 0, +1
        elif from_.y == room.bottom:
            step.x, step.y = 0, -1

        p = from_.clone().offset(step.x, step.y)
        for _ in range(n):
            if value != -1:
                Painter.set(level, p, value)
            p.offset(step.x, step.y)

        return p


def _fill_xywh(level, width: int, x: int, y: int, w: int, h: int, value: int) -> None:
    pos = y * width + x
    for _ in range(h):
        for k in range(pos, pos + w):
            level.map[k] = value
        pos += width


def _fill_ellipse_xywh(level, x: int, y: int, w: int, h: int, value: int) -> None:
    rad_h = h / 2.0
    rad_w = w / 2.0

    for i in range(h):
        row_y = -rad_h + 0.5 + i
        row_w = 2.0 * math.sqrt((rad_w * rad_w) * (1.0 - (row_y * row_y) / (rad_h * rad_h)))

        if w % 2 == 0:
            row_w = round(row_w / 2.0) * 2.0
        else:
            row_w = math.floor(row_w / 2.0) * 2.0
            row_w += 1

        cell = x + (w - int(row_w)) // 2 + ((y + i) * level.width())
        for k in range(cell, cell + int(row_w)):
            level.map[k] = value


def _fill_diamond_xywh(level, x: int, y: int, w: int, h: int, value: int) -> None:
    diamond_width = w - (h - 2 - h % 2)
    diamond_width = max(diamond_width, 2 if w % 2 == 0 else 3)

    for i in range(h + 1):
        _fill_xywh(level, level.width(), x + (w - diamond_width) // 2, y + i,
                   diamond_width, h - 2 * i, value)
        diamond_width += 2
        if diamond_width > w:
            break
