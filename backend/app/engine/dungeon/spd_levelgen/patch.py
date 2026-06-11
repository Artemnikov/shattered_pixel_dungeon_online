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
"""Port of com.shatteredpixel.shatteredpixeldungeon.levels.Patch.generate --
cellular-automaton "blob" generator used for water/grass paint passes.

Returns a flat `List[bool]` of length `w*h` (row-major, matching `level.map`
indexing) so callers can index it the same way as the Java `boolean[]`."""

from __future__ import annotations

import math
from typing import List

from app.engine.dungeon.spd_levelgen.geom import _to_f32
from app.engine.dungeon.spd_random import SPDRandom


def _round_f32(x: float) -> int:
    """Java Math.round(float): floor(x + 0.5), computed in float32."""
    return math.floor(_to_f32(_to_f32(x) + 0.5))


def generate(rng: SPDRandom, w: int, h: int, fill: float, clustering: int,
             force_fill_rate: bool) -> List[bool]:
    length = w * h

    cur = [False] * length
    off = [False] * length

    fill = _to_f32(fill)
    fill_diff = -_round_f32(_to_f32(_to_f32(float(length)) * fill))

    if force_fill_rate and clustering > 0:
        diff = _to_f32(0.5 - fill)
        scaled = _to_f32(diff * 0.5)
        fill = _to_f32(fill + scaled)

    for i in range(length):
        off[i] = rng.Float() < fill
        if off[i]:
            fill_diff += 1

    for _ in range(clustering):
        for y in range(h):
            for x in range(w):
                pos = x + y * w
                count = 0
                neighbours = 0

                if y > 0:
                    if x > 0:
                        if off[pos - w - 1]:
                            count += 1
                        neighbours += 1
                    if off[pos - w]:
                        count += 1
                    neighbours += 1
                    if x < w - 1:
                        if off[pos - w + 1]:
                            count += 1
                        neighbours += 1

                if x > 0:
                    if off[pos - 1]:
                        count += 1
                    neighbours += 1
                if off[pos]:
                    count += 1
                neighbours += 1
                if x < w - 1:
                    if off[pos + 1]:
                        count += 1
                    neighbours += 1

                if y < h - 1:
                    if x > 0:
                        if off[pos + w - 1]:
                            count += 1
                        neighbours += 1
                    if off[pos + w]:
                        count += 1
                    neighbours += 1
                    if x < w - 1:
                        if off[pos + w + 1]:
                            count += 1
                        neighbours += 1

                cur[pos] = 2 * count >= neighbours
                if cur[pos] != off[pos]:
                    fill_diff += 1 if cur[pos] else -1

        cur, off = off, cur

    if force_fill_rate and min(w, h) > 2:
        neighbours_offsets = (-w - 1, -w, -w + 1, -1, 0, 1, w - 1, w, w + 1)
        growing = fill_diff < 0

        while fill_diff != 0:
            tries = 0
            cell = 0
            while True:
                cell = rng.IntMinMax(1, w - 1) + rng.IntMinMax(1, h - 1) * w
                tries += 1
                if off[cell] == growing or tries * 10 >= length:
                    break

            for offset in neighbours_offsets:
                if fill_diff != 0 and off[cell + offset] != growing:
                    off[cell + offset] = growing
                    fill_diff += 1 if growing else -1

    return off
