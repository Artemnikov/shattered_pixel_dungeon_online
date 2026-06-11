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
"""Port of com.shatteredpixel.shatteredpixeldungeon.levels.features.Maze --
RNG-driven maze-carving used by MazeConnectionRoom. `maze[x][y]`: True == wall
(FILLED), False == space (EMPTY); matches the Java boolean semantics exactly
(note Maze.EMPTY = false, Maze.FILLED = true)."""

from __future__ import annotations

from typing import List

from app.engine.dungeon.spd_levelgen.room import Room
from app.engine.dungeon.spd_random import SPDRandom

EMPTY = False
FILLED = True

allow_diagonals = False


def generate_for_room(rng: SPDRandom, r: Room) -> List[List[bool]]:
    w, h = r.width(), r.height()
    maze = [[EMPTY] * h for _ in range(w)]

    for x in range(w):
        for y in range(h):
            if x == 0 or x == w - 1 or y == 0 or y == h - 1:
                maze[x][y] = FILLED

    for d in r.connected.values():
        maze[d.x - r.left][d.y - r.top] = EMPTY

    return _generate(rng, maze)


def _check_valid_move(maze: List[List[bool]], x: int, y: int, mov: tuple) -> bool:
    side_x = 1 - abs(mov[0])
    side_y = 1 - abs(mov[1])

    x += mov[0]
    y += mov[1]

    if x <= 0 or x >= len(maze) - 1 or y <= 0 or y >= len(maze[0]) - 1:
        return False
    elif maze[x][y] or maze[x + side_x][y + side_y] or maze[x - side_x][y - side_y]:
        return False

    x += mov[0]
    y += mov[1]

    if x <= 0 or x >= len(maze) - 1 or y <= 0 or y >= len(maze[0]) - 1:
        return False
    elif maze[x][y]:
        return False
    elif not allow_diagonals and (maze[x + side_x][y + side_y] or maze[x - side_x][y - side_y]):
        return False

    return True


def _decide_direction(rng: SPDRandom, maze: List[List[bool]], x: int, y: int):
    if rng.IntMax(4) == 0 and _check_valid_move(maze, x, y, (0, -1)):
        return (0, -1)
    if rng.IntMax(3) == 0 and _check_valid_move(maze, x, y, (1, 0)):
        return (1, 0)
    if rng.IntMax(2) == 0 and _check_valid_move(maze, x, y, (0, 1)):
        return (0, 1)
    if _check_valid_move(maze, x, y, (-1, 0)):
        return (-1, 0)
    return None


def _generate(rng: SPDRandom, maze: List[List[bool]]) -> List[List[bool]]:
    fails = 0
    while fails < 2500:
        while True:
            x = rng.IntMax(len(maze))
            y = rng.IntMax(len(maze[0]))
            if maze[x][y]:
                break

        mov = _decide_direction(rng, maze, x, y)
        if mov is None:
            fails += 1
        else:
            fails = 0
            moves = 0
            while True:
                x += mov[0]
                y += mov[1]
                maze[x][y] = FILLED
                moves += 1
                if not (rng.IntMax(moves) == 0 and _check_valid_move(maze, x, y, mov)):
                    break

    return maze
