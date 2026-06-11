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
"""Port of com.watabou.utils.Graph -- BFS distance map over Room graphs
(used by RegularPainter.paintDoors to decide whether a hidden door would
disconnect a room)."""

from __future__ import annotations

from collections import deque
from typing import Iterable

from app.engine.dungeon.spd_levelgen.room import Room

INFINITY = 0x7FFFFFFF  # Integer.MAX_VALUE


def build_distance_map(nodes: Iterable[Room], focus: Room) -> None:
    for node in nodes:
        node.distance = INFINITY

    queue = deque()
    focus.distance = 0
    queue.append(focus)

    while queue:
        node = queue.popleft()
        distance = node.distance
        price = node.price

        for edge in node.edges():
            if edge.distance > distance + price:
                queue.append(edge)
                edge.distance = distance + price
