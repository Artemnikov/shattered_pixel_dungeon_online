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
"""Port of SewerBossLevel + its associated room types (SewerBossEntranceRoom,
SewerBossExitRoom, GooBossRoom + 4 layout variants, RatKingRoom) from
levels/SewerBossLevel.java and levels/rooms/sewerboss/*.java.

`build_boss_floor()` is the entry point, called instead of `build_floor()` for
depth 5 (and future boss depths).  It creates a FigureEightBuilder loop with
the GooBossRoom as landmark, paints with SewerPainter (0 water/grass, 0 traps),
and places a Goo mob via the Goo boss room's paint()."""

from __future__ import annotations

import math
from typing import List, Optional, Tuple

from app.engine.dungeon.spd_levelgen import terrain
from app.engine.dungeon.spd_levelgen.builders import FigureEightBuilder
from app.engine.dungeon.spd_levelgen.connection_rooms import _fill_perimeter_paths
from app.engine.dungeon.spd_levelgen.geom import Point
from app.engine.dungeon.spd_levelgen.level import Feeling, GenLevel
from app.engine.dungeon.spd_levelgen.mob_spawner import GenMob
from app.engine.dungeon.spd_levelgen.painter import Painter
from app.engine.dungeon.spd_levelgen.room import ALL, DoorType, Room
from app.engine.dungeon.spd_levelgen.room_types import SecretRoom, SizeCategory, StandardRoom
from app.engine.dungeon.spd_levelgen.run_state import RunState
from app.engine.dungeon.spd_levelgen.sewer_painter import SewerPainter
from app.engine.dungeon.spd_levelgen.standard_rooms import create_standard_room
from app.engine.dungeon.spd_random import SPDRandom


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def build_boss_floor(rng: SPDRandom, depth: int, run_state: RunState) -> Tuple[GenLevel, List[Room]]:
    if depth == 10:
        return _build_prison_boss_floor(rng, depth, run_state)
    if depth == 15:
        return _build_caves_boss_floor(rng, depth, run_state)
    if depth == 20:
        return _build_city_boss_floor(rng, depth, run_state)
    if depth == 25:
        return _build_halls_boss_floor(rng, depth, run_state)
    return _build_sewer_boss_floor(rng, depth, run_state)


def _build_sewer_boss_floor(rng: SPDRandom, depth: int, run_state: RunState) -> Tuple[GenLevel, List[Room]]:
    """Port of SewerBossLevel's build()/create() sequence.  Creates the
    figure-8 layout, paints via SewerPainter (water/grass/traps all zero),
    and spawns Bones items only."""

    level = GenLevel(depth, Feeling.NONE)
    level.run_state = run_state

    while True:
        builder = _boss_builder(rng)
        init_rooms = _boss_init_rooms(rng, depth)
        rng.shuffle(init_rooms)
        for r in init_rooms:
            r.neighbours.clear()
            r.connected.clear()
        rooms = builder.build(list(init_rooms), rng, depth)
        if rooms is not None:
            break

    painter = _boss_painter()
    painter.paint(rng, level, rooms)

    level.rooms = rooms
    level.room_entrance = next(r for r in rooms if r.is_entrance())
    level.room_exit = next(r for r in rooms if r.is_exit())
    level.build_flag_maps()

    _boss_create_items(rng, level)

    return level, rooms


def _build_prison_boss_floor(rng: SPDRandom, depth: int, run_state: RunState) -> Tuple[GenLevel, List[Room]]:
    """Hardcoded port of PrisonBossLevel.java (Tengu, depth 10): the START-state
    32x32 layout (entrance/start hallway/start cells/tengu cell), faithful to
    the original. Tengu itself is NOT spawned here -- it doesn't exist in the
    world until the FIGHT_START transition (engine/game/tengu_arena.py)."""
    from app.engine.dungeon.spd_levelgen import prison_boss_layout as layout

    level = layout.build_start_grid(rng, depth)
    level.run_state = run_state

    entrance_room = PrisonBossEntranceRoom()
    entrance_room.set(layout.ENTRANCE_ROOM.left, layout.ENTRANCE_ROOM.top,
                       layout.ENTRANCE_ROOM.right, layout.ENTRANCE_ROOM.bottom)
    exit_room = PrisonBossExitRoom()
    exit_room.set(layout.LEVEL_EXIT.x, layout.LEVEL_EXIT.y,
                   layout.LEVEL_EXIT.x + 2, layout.LEVEL_EXIT.y + 3)
    rooms: List[Room] = [entrance_room, exit_room]

    level.rooms = rooms
    level.room_entrance = entrance_room
    level.room_exit = exit_room
    level.build_flag_maps()

    _boss_create_items(rng, level)

    pos = layout.random_prison_cell_pos(rng, level)
    while level.solid[pos]:
        pos = layout.random_prison_cell_pos(rng, level)
    level.drop(frozenset({"IronKey"}), pos)

    return level, rooms


def _build_caves_boss_floor(rng: SPDRandom, depth: int, run_state: RunState) -> Tuple[GenLevel, List[Room]]:
    """Simplified caves boss level (DM-300, depth 15). Open arena with pillars."""
    from app.engine.dungeon.spd_levelgen.caves_painter import CavesPainter

    level = GenLevel(depth, Feeling.NONE)
    level.run_state = run_state

    while True:
        builder = _boss_builder(rng)
        init_rooms = _caves_boss_init_rooms(rng, depth)
        rng.shuffle(init_rooms)
        for r in init_rooms:
            r.neighbours.clear()
            r.connected.clear()
        rooms = builder.build(list(init_rooms), rng, depth)
        if rooms is not None:
            break

    painter = (CavesPainter()
               .set_water(0.20, 6)
               .set_grass(0.10, 3)
               .set_traps(0, (), ()))
    painter.paint(rng, level, rooms)

    level.rooms = rooms
    level.room_entrance = next(r for r in rooms if r.is_entrance())
    level.room_exit = next(r for r in rooms if r.is_exit())
    level.build_flag_maps()

    _boss_create_items(rng, level)
    return level, rooms


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------

def _boss_builder(rng: SPDRandom) -> FigureEightBuilder:
    """Port of SewerBossLevel.builder()."""
    return (FigureEightBuilder()
            .set_loop_shape(2, rng.FloatRange(0.3, 0.8), 0.0)
            .set_path_length(1.0, [1.0])
            .set_tunnel_length([1.0, 2.0], [1.0]))


# ---------------------------------------------------------------------------
# Room initialisation
# ---------------------------------------------------------------------------

def _boss_init_rooms(rng: SPDRandom, depth: int) -> List[Room]:
    """Port of SewerBossLevel.initRooms().  Creates entrance, exit, 3×
    NORMAL-sized standard rooms, a random Goo boss room (landmark), and the
    Rat King side-room."""

    rooms: List[Room] = []

    entrance = SewerBossEntranceRoom()
    entrance.init_size_cat(rng)
    rooms.append(entrance)

    exit_ = SewerBossExitRoom()
    exit_.init_size_cat(rng)
    rooms.append(exit_)

    # standardRooms(true) -> forceMax -> 3
    for _ in range(_boss_standard_rooms(True)):
        s = create_standard_room(rng, depth)
        s.set_size_cat(rng, 0, 0)
        rooms.append(s)

    goo_room = GooBossRoom.random_goo_room(rng)
    goo_room.init_size_cat(rng)
    rooms.append(goo_room)

    rat_king = RatKingRoom()
    rooms.append(rat_king)

    return rooms


def _boss_standard_rooms(force_max: bool) -> int:
    """Port of SewerBossLevel.standardRooms()."""
    return 3  # always returns 3 when forceMax (and boss level always forces)


def _caves_boss_init_rooms(rng: SPDRandom, depth: int) -> List[Room]:
    rooms: List[Room] = []
    entrance = CavesBossEntranceRoom()
    entrance.init_size_cat(rng)
    rooms.append(entrance)
    exit_ = CavesBossExitRoom()
    exit_.init_size_cat(rng)
    rooms.append(exit_)
    for _ in range(3):
        s = create_standard_room(rng, depth)
        s.set_size_cat(rng, 0, 0)
        rooms.append(s)
    boss_room = DM300BossRoom()
    boss_room.init_size_cat(rng)
    rooms.append(boss_room)
    return rooms


# ---------------------------------------------------------------------------
# Painter
# ---------------------------------------------------------------------------

def _boss_painter() -> SewerPainter:
    """Port of SewerBossLevel.painter().  Water/grass/traps are 0."""
    return (SewerPainter()
            .set_water(0.50, 5)
            .set_grass(0.20, 4)
            .set_traps(0, (), ()))


# ---------------------------------------------------------------------------
# Items (Bones only)
# ---------------------------------------------------------------------------

def _boss_create_items(rng: SPDRandom, level: GenLevel) -> None:
    """Port of SewerBossLevel.createItems().  Only Bones items from the
    shared saved-state generator (gated false on a fresh game)."""
    rng.push_generator(rng.Long())
    rng.pop_generator()


# ===========================================================================
# Room types
# ===========================================================================

def _goo_nest_index(x: int, y: int, tile_w: int, tile_h: int) -> int:
    """Port of GooBossRoom.GooNest.create()'s per-cell index pattern."""
    # corners
    if (x == 0 or x == tile_w - 1) and (y == 0 or y == tile_h - 1):
        return -1
    # adjacent to corners
    if (x == 1 and y == 0) or (x == 0 and y == 1):
        return 0
    if (x == tile_w - 2 and y == 0) or (x == tile_w - 1 and y == 1):
        return 1
    if (x == 1 and y == tile_h - 1) or (x == 0 and y == tile_h - 2):
        return 2
    if (x == tile_w - 2 and y == tile_h - 1) or (x == tile_w - 1 and y == tile_h - 2):
        return 3
    # sides
    if x == 0:
        return 4
    if y == 0:
        return 5
    if x == tile_w - 1:
        return 6
    if y == tile_h - 1:
        return 7
    # inside
    return 8


# ---- GooBossRoom base -----------------------------------------------------

class GooBossRoom(StandardRoom):
    """Abstract base for the four Goo boss arena layouts."""

    def size_cat_probs(self):
        return [0.0, 1.0, 0.0]

    def can_merge(self, level, other: Room, p: Point, merge_terrain: int) -> bool:
        return False

    def can_place_water(self, p: Point) -> bool:
        return False

    @staticmethod
    def random_goo_room(rng: SPDRandom) -> "GooBossRoom":
        """Port of GooBossRoom.randomGooRoom()."""
        idx = rng.IntMax(4)
        if idx == 0:
            return DiamondGooRoom()
        elif idx == 1:
            return WalledGooRoom()
        elif idx == 2:
            return ThinPillarsGooRoom()
        else:
            return ThickPillarsGooRoom()

    def _setup_goo_nest(self, level: GenLevel) -> None:
        """Port of GooBossRoom.setupGooNest() — decorative GooNest tilemap
        centered in the room (no RNG, no gameplay effect)."""
        tile_w = 4 + self.width() % 2
        tile_h = 4 + self.height() % 2
        ox = self.left + self.width() // 2 - 2
        oy = self.top + self.height() // 2 - 2
        tiles = [
            [_goo_nest_index(x, y, tile_w, tile_h) for x in range(tile_w)]
            for y in range(tile_h)
        ]
        level.custom_tiles.append({
            "texture": "sewer_boss",
            "x": ox,
            "y": oy,
            "w": tile_w,
            "h": tile_h,
            "tiles": tiles,
        })

    def _place_goo(self, level: GenLevel, rng: SPDRandom) -> None:
        """Creates the Goo mob at the room's center (consumes center() RNG)."""
        c = self.center(rng)
        pos = level.point_to_cell(c)
        level.mobs.append(GenMob(cls_name="Goo", pos=pos))


# ---- DiamondGooRoom -------------------------------------------------------

class DiamondGooRoom(GooBossRoom):
    """Port of DiamondGooRoom — filled diamond arena with water cross."""

    def paint(self, level, rng) -> None:
        Painter.fill(level, self, terrain.WALL)
        Painter.fill_diamond(level, self, 1, terrain.EMPTY)

        for door in self.connected.values():
            door.set(DoorType.REGULAR)
            if door.x == self.left:
                dir_ = Point(1, 0)
            elif door.y == self.top:
                dir_ = Point(0, 1)
            elif door.x == self.right:
                dir_ = Point(-1, 0)
            else:
                dir_ = Point(0, -1)

            curr = Point(door.x, door.y)
            while True:
                curr = Point(curr.x + dir_.x, curr.y + dir_.y)
                cell = level.point_to_cell(curr)
                if level.map[cell] != terrain.WALL:
                    break
                Painter.set(level, curr, terrain.EMPTY_SP)

        w = self.width()
        h = self.height()
        Painter.fill(level,
                     self.left + w // 2 - 1, self.top + h // 2 - 2,
                     2 + w % 2, 4 + h % 2, terrain.WATER)
        Painter.fill(level,
                     self.left + w // 2 - 2, self.top + h // 2 - 1,
                     4 + w % 2, 2 + h % 2, terrain.WATER)

        self._setup_goo_nest(level)
        self._place_goo(level, rng)


# ---- WalledGooRoom --------------------------------------------------------

class WalledGooRoom(GooBossRoom):
    """Port of WalledGooRoom — L-shaped corner walls with water cross."""

    def paint(self, level, rng) -> None:
        Painter.fill(level, self, terrain.WALL)
        Painter.fill(level, self, 1, terrain.EMPTY_SP)
        Painter.fill(level, self, 2, terrain.EMPTY)

        pillar_w = (self.width() - 6) // 2
        pillar_h = (self.height() - 6) // 2

        Painter.fill(level, self.left + 2, self.top + 2, pillar_w, 1, terrain.WALL)
        Painter.fill(level, self.left + 2, self.top + 2, 1, pillar_h, terrain.WALL)

        Painter.fill(level, self.left + 2, self.bottom - 2, pillar_w, 1, terrain.WALL)
        Painter.fill(level, self.left + 2, self.bottom - 1 - pillar_h, 1, pillar_h, terrain.WALL)

        Painter.fill(level, self.right - 1 - pillar_w, self.top + 2, pillar_w, 1, terrain.WALL)
        Painter.fill(level, self.right - 2, self.top + 2, 1, pillar_h, terrain.WALL)

        Painter.fill(level, self.right - 1 - pillar_w, self.bottom - 2, pillar_w, 1, terrain.WALL)
        Painter.fill(level, self.right - 2, self.bottom - 1 - pillar_h, 1, pillar_h, terrain.WALL)

        for door in self.connected.values():
            door.set(DoorType.REGULAR)

        w = self.width()
        h = self.height()
        Painter.fill(level,
                     self.left + w // 2 - 1, self.top + h // 2 - 2,
                     2 + w % 2, 4 + h % 2, terrain.WATER)
        Painter.fill(level,
                     self.left + w // 2 - 2, self.top + h // 2 - 1,
                     4 + w % 2, 2 + h % 2, terrain.WATER)

        self._setup_goo_nest(level)
        self._place_goo(level, rng)


# ---- ThinPillarsGooRoom ---------------------------------------------------

class ThinPillarsGooRoom(GooBossRoom):
    """Port of ThinPillarsGooRoom — water floor with thin central pillars."""

    def paint(self, level, rng) -> None:
        Painter.fill(level, self, terrain.WALL)
        Painter.fill(level, self, 1, terrain.WATER)

        pillar_w = (4 if self.width() == 14 else 2) + self.width() % 2
        pillar_h = (4 if self.height() == 14 else 2) + self.height() % 2

        if self.height() < 12:
            Painter.fill(level,
                         self.left + (self.width() - pillar_w) // 2, self.top + 2,
                         pillar_w, 1, terrain.WALL)
            Painter.fill(level,
                         self.left + (self.width() - pillar_w) // 2, self.bottom - 2,
                         pillar_w, 1, terrain.WALL)
        else:
            Painter.fill(level,
                         self.left + (self.width() - pillar_w) // 2, self.top + 3,
                         pillar_w, 1, terrain.WALL)
            Painter.fill(level,
                         self.left + (self.width() - pillar_w) // 2, self.bottom - 3,
                         pillar_w, 1, terrain.WALL)

        if self.width() < 12:
            Painter.fill(level,
                         self.left + 2, self.top + (self.height() - pillar_h) // 2,
                         1, pillar_h, terrain.WALL)
            Painter.fill(level,
                         self.right - 2, self.top + (self.height() - pillar_h) // 2,
                         1, pillar_h, terrain.WALL)
        else:
            Painter.fill(level,
                         self.left + 3, self.top + (self.height() - pillar_h) // 2,
                         1, pillar_h, terrain.WALL)
            Painter.fill(level,
                         self.right - 3, self.top + (self.height() - pillar_h) // 2,
                         1, pillar_h, terrain.WALL)

        _fill_perimeter_paths(level, self, terrain.EMPTY_SP)

        for door in self.connected.values():
            door.set(DoorType.REGULAR)

        self._setup_goo_nest(level)
        self._place_goo(level, rng)


# ---- ThickPillarsGooRoom --------------------------------------------------

class ThickPillarsGooRoom(GooBossRoom):
    """Port of ThickPillarsGooRoom — water floor with thick corner pillars."""

    def paint(self, level, rng) -> None:
        Painter.fill(level, self, terrain.WALL)
        Painter.fill(level, self, 1, terrain.WATER)

        pillar_w = (self.width() - 8) // 2
        pillar_h = (self.height() - 8) // 2

        Painter.fill(level, self.left + 2, self.top + 2, pillar_w + 1, pillar_h + 1, terrain.WALL)
        Painter.fill(level, self.left + 2, self.bottom - 2 - pillar_h, pillar_w + 1, pillar_h + 1, terrain.WALL)
        Painter.fill(level, self.right - 2 - pillar_w, self.top + 2, pillar_w + 1, pillar_h + 1, terrain.WALL)
        Painter.fill(level, self.right - 2 - pillar_w, self.bottom - 2 - pillar_h, pillar_w + 1, pillar_h + 1, terrain.WALL)

        _fill_perimeter_paths(level, self, terrain.EMPTY_SP)

        for door in self.connected.values():
            door.set(DoorType.REGULAR)

        self._setup_goo_nest(level)
        self._place_goo(level, rng)


# ---- SewerBossEntranceRoom -------------------------------------------------

class SewerBossEntranceRoom(StandardRoom):
    """Port of SewerBossEntranceRoom — entrance room with wall-decoration and
    water, big enough to prevent the player being boxed in."""

    def min_width(self) -> int:
        return max(super().min_width(), 7)

    def min_height(self) -> int:
        return max(super().min_height(), 7)

    def is_entrance(self) -> bool:
        return True

    def paint(self, level, rng) -> None:
        Painter.fill(level, self, terrain.WALL)
        Painter.fill(level, self, 1, terrain.EMPTY)

        Painter.fill(level, self.left + 1, self.top + 1, self.width() - 2, 1, terrain.WALL_DECO)
        Painter.fill(level, self.left + 1, self.top + 2, self.width() - 2, 1, terrain.WATER)

        entrance = level.point_to_cell(self.random(rng, 3))
        Painter.set(level, entrance, terrain.ENTRANCE)

        for door in self.connected.values():
            door.set(DoorType.REGULAR)
            if door.y == self.top or door.y == self.top + 1:
                Painter.draw_inside(level, self, door, 1, terrain.WATER)


# ---- SewerBossExitRoom -----------------------------------------------------

class SewerBossExitRoom(StandardRoom):
    """Port of SewerBossExitRoom — pedestal with LOCKED_EXIT and visual
    sewer exit custom tilemap (skipped)."""

    def min_width(self) -> int:
        return max(super().min_width(), 8)

    def min_height(self) -> int:
        return max(super().min_height(), 8)

    def is_exit(self) -> bool:
        return True

    def paint(self, level, rng) -> None:
        Painter.fill(level, self, terrain.WALL)
        Painter.fill(level, self, 1, terrain.EMPTY)

        for door in self.connected.values():
            door.set(DoorType.REGULAR)

        c = self.center(rng)
        Painter.fill(level, c.x - 1, c.y - 1, 3, 2, terrain.WALL)
        Painter.fill(level, c.x - 1, c.y + 1, 3, 1, terrain.EMPTY_SP)

        Painter.set(level, c, terrain.LOCKED_EXIT)


# ---- RatKingRoom -----------------------------------------------------------

class RatKingRoom(SecretRoom):
    """Port of RatKingRoom — hidden room filled with chests and the Rat
    King NPC."""

    def can_connect(self, r: Room) -> bool:
        from app.engine.dungeon.spd_levelgen.boss_level import SewerBossEntranceRoom
        if isinstance(r, SewerBossEntranceRoom):
            return False
        return super().can_connect(r)

    def max_width(self) -> int:
        return 7

    def max_height(self) -> int:
        return 7

    def paint(self, level, rng) -> None:
        Painter.fill(level, self, terrain.WALL)
        Painter.fill(level, self, 1, terrain.EMPTY_SP)

        entrance = self.entrance()
        entrance.set(DoorType.HIDDEN)
        door_x, door_y = entrance.x, entrance.y
        door = door_x + door_y * level.width()

        for i in range(self.left + 1, self.right):
            self._add_chest(level, (self.top + 1) * level.width() + i, door)
            self._add_chest(level, (self.bottom - 1) * level.width() + i, door)

        for i in range(self.top + 2, self.bottom - 1):
            self._add_chest(level, i * level.width() + self.left + 1, door)
            self._add_chest(level, i * level.width() + self.right - 1, door)

        king_pos = level.point_to_cell(self.random(rng, 2))
        level.mobs.append(GenMob(cls_name="RatKing", pos=king_pos))

    @staticmethod
    def _add_chest(level: GenLevel, pos: int, door: int) -> None:
        if (pos == door - 1 or pos == door + 1
                or pos == door - level.width() or pos == door + level.width()):
            return
        level.drop(frozenset({"Gold", "CHEST"}), pos).type = "CHEST"


# ===========================================================================
# Prison Boss (Tengu, depth 10) room types
# ===========================================================================

class PrisonBossEntranceRoom(Room):
    """Marks the entranceRoom rect of the hardcoded PrisonBossLevel layout."""

    def is_entrance(self) -> bool:
        return True


class PrisonBossExitRoom(Room):
    """Marks the (walled-off) levelExit rect of the hardcoded PrisonBossLevel
    layout -- present for consistency with other levels, per the Java
    comment, even though it sits inside the END_MAP walls until WON."""

    def is_exit(self) -> bool:
        return True


# ===========================================================================
# Caves Boss (DM-300, depth 15) room types
# ===========================================================================

class CavesBossEntranceRoom(StandardRoom):
    def min_width(self) -> int:
        return max(super().min_width(), 7)

    def min_height(self) -> int:
        return max(super().min_height(), 7)

    def is_entrance(self) -> bool:
        return True

    def paint(self, level, rng) -> None:
        Painter.fill(level, self, terrain.WALL)
        Painter.fill(level, self, 1, terrain.EMPTY)
        entrance = level.point_to_cell(self.random(rng, 2))
        Painter.set(level, entrance, terrain.ENTRANCE)
        for door in self.connected.values():
            door.set(DoorType.REGULAR)


class CavesBossExitRoom(StandardRoom):
    def min_width(self) -> int:
        return max(super().min_width(), 7)

    def min_height(self) -> int:
        return max(super().min_height(), 7)

    def is_exit(self) -> bool:
        return True

    def paint(self, level, rng) -> None:
        Painter.fill(level, self, terrain.WALL)
        Painter.fill(level, self, 1, terrain.EMPTY)
        c = self.center(rng)
        Painter.set(level, c, terrain.LOCKED_EXIT)
        for door in self.connected.values():
            door.set(DoorType.REGULAR)


class DM300BossRoom(StandardRoom):
    def size_cat_probs(self):
        return [0.0, 1.0, 0.0]

    def min_width(self) -> int:
        return max(super().min_width(), 12)

    def min_height(self) -> int:
        return max(super().min_height(), 12)

    def paint(self, level, rng) -> None:
        Painter.fill(level, self, terrain.WALL)
        Painter.fill(level, self, 1, terrain.EMPTY)

        # Place 3 boulder pillars
        w, h = self.width(), self.height()
        for px, py in [
            (self.left + w // 4, self.top + h // 4),
            (self.right - w // 4, self.top + h // 4),
            (self.left + w // 2, self.bottom - h // 4),
        ]:
            Painter.fill(level, px - 1, py - 1, 2, 2, terrain.MINE_BOULDER)

        for door in self.connected.values():
            door.set(DoorType.REGULAR)

        c = self.center(rng)
        dm300_pos = level.point_to_cell(c)
        level.mobs.append(GenMob(cls_name="DM300", pos=dm300_pos))

        # Pylons at the four corners of the arena interior (CavesBossLevel.pylonPositions),
        # inset 2 tiles from the walls so they don't sit directly on the inset-1 floor edge.
        for px, py in [
            (self.left + 2, self.top + 2),
            (self.right - 2, self.top + 2),
            (self.left + 2, self.bottom - 2),
            (self.right - 2, self.bottom - 2),
        ]:
            level.mobs.append(GenMob(cls_name="Pylon", pos=level.point_to_cell(Point(px, py))))


# ===========================================================================
# City Boss (DwarfKing, depth 20) room types
# ===========================================================================

def _build_city_boss_floor(rng: SPDRandom, depth: int, run_state: RunState) -> Tuple[GenLevel, List[Room]]:
    """Simplified city boss level (DwarfKing, depth 20). Throne room arena."""
    from app.engine.dungeon.spd_levelgen.city_painter import CityPainter

    level = GenLevel(depth, Feeling.NONE)
    level.run_state = run_state

    while True:
        builder = _boss_builder(rng)
        init_rooms = _city_boss_init_rooms(rng, depth)
        rng.shuffle(init_rooms)
        for r in init_rooms:
            r.neighbours.clear()
            r.connected.clear()
        rooms = builder.build(list(init_rooms), rng, depth)
        if rooms is not None:
            break

    painter = (CityPainter()
               .set_water(0.10, 4)
               .set_grass(0.05, 3)
               .set_traps(0, (), ()))
    painter.paint(rng, level, rooms)

    level.rooms = rooms
    level.room_entrance = next(r for r in rooms if r.is_entrance())
    level.room_exit = next(r for r in rooms if r.is_exit())
    level.build_flag_maps()

    _boss_create_items(rng, level)
    return level, rooms


def _city_boss_init_rooms(rng: SPDRandom, depth: int) -> List[Room]:
    rooms: List[Room] = []
    entrance = CityBossEntranceRoom()
    entrance.init_size_cat(rng)
    rooms.append(entrance)
    exit_ = CityBossExitRoom()
    exit_.init_size_cat(rng)
    rooms.append(exit_)
    for _ in range(3):
        s = create_standard_room(rng, depth)
        s.set_size_cat(rng, 0, 0)
        rooms.append(s)
    boss_room = DwarfKingBossRoom()
    boss_room.init_size_cat(rng)
    rooms.append(boss_room)
    return rooms


class CityBossEntranceRoom(StandardRoom):
    def min_width(self) -> int:
        return max(super().min_width(), 7)

    def min_height(self) -> int:
        return max(super().min_height(), 7)

    def is_entrance(self) -> bool:
        return True

    def paint(self, level, rng) -> None:
        Painter.fill(level, self, terrain.WALL)
        Painter.fill(level, self, 1, terrain.EMPTY)
        entrance = level.point_to_cell(self.random(rng, 2))
        Painter.set(level, entrance, terrain.ENTRANCE)
        for door in self.connected.values():
            door.set(DoorType.REGULAR)


class CityBossExitRoom(StandardRoom):
    def min_width(self) -> int:
        return max(super().min_width(), 7)

    def min_height(self) -> int:
        return max(super().min_height(), 7)

    def is_exit(self) -> bool:
        return True

    def paint(self, level, rng) -> None:
        Painter.fill(level, self, terrain.WALL)
        Painter.fill(level, self, 1, terrain.EMPTY)
        c = self.center(rng)
        Painter.set(level, c, terrain.LOCKED_EXIT)
        for door in self.connected.values():
            door.set(DoorType.REGULAR)


class DwarfKingBossRoom(StandardRoom):
    def size_cat_probs(self):
        return [0.0, 1.0, 0.0]

    def min_width(self) -> int:
        return max(super().min_width(), 12)

    def min_height(self) -> int:
        return max(super().min_height(), 12)

    def paint(self, level, rng) -> None:
        Painter.fill(level, self, terrain.WALL)
        Painter.fill(level, self, 1, terrain.EMPTY)

        for door in self.connected.values():
            door.set(DoorType.REGULAR)

        c = self.center(rng)
        dk_pos = level.point_to_cell(c)
        level.mobs.append(GenMob(cls_name="DwarfKing", pos=dk_pos))

        # 4 summon pedestals at room corners (inset 2 from wall)
        level.dk_summon_spots = [
            (self.left + 2, self.top + 2),
            (self.right - 2, self.top + 2),
            (self.right - 2, self.bottom - 2),
            (self.left + 2, self.bottom - 2),
        ]


# ===========================================================================
# Halls Boss (YogDzewa, depth 25) room types
# ===========================================================================

def _build_halls_boss_floor(rng: SPDRandom, depth: int, run_state: RunState) -> Tuple[GenLevel, List[Room]]:
    """Halls boss level (YogDzewa, depth 25). Demonic arena."""
    from app.engine.dungeon.spd_levelgen.halls_painter import HallsPainter

    level = GenLevel(depth, Feeling.NONE)
    level.run_state = run_state

    while True:
        builder = _boss_builder(rng)
        init_rooms = _halls_boss_init_rooms(rng, depth)
        rng.shuffle(init_rooms)
        for r in init_rooms:
            r.neighbours.clear()
            r.connected.clear()
        rooms = builder.build(list(init_rooms), rng, depth)
        if rooms is not None:
            break

    painter = (HallsPainter()
               .set_water(0.10, 4)
               .set_grass(0.05, 3)
               .set_traps(0, (), ()))
    painter.paint(rng, level, rooms)

    level.rooms = rooms
    level.room_entrance = next(r for r in rooms if r.is_entrance())
    level.room_exit = next(r for r in rooms if r.is_exit())
    level.build_flag_maps()

    _boss_create_items(rng, level)
    return level, rooms


def _halls_boss_init_rooms(rng: SPDRandom, depth: int) -> List[Room]:
    rooms: List[Room] = []
    entrance = HallsBossEntranceRoom()
    entrance.init_size_cat(rng)
    rooms.append(entrance)
    exit_ = HallsBossExitRoom()
    exit_.init_size_cat(rng)
    rooms.append(exit_)
    for _ in range(3):
        s = create_standard_room(rng, depth)
        s.set_size_cat(rng, 0, 0)
        rooms.append(s)
    boss_room = YogDzewaBossRoom()
    boss_room.init_size_cat(rng)
    rooms.append(boss_room)
    return rooms


class HallsBossEntranceRoom(StandardRoom):
    def min_width(self) -> int:
        return max(super().min_width(), 7)

    def min_height(self) -> int:
        return max(super().min_height(), 7)

    def is_entrance(self) -> bool:
        return True

    def paint(self, level, rng) -> None:
        Painter.fill(level, self, terrain.WALL)
        Painter.fill(level, self, 1, terrain.EMPTY)
        entrance = level.point_to_cell(self.random(rng, 2))
        Painter.set(level, entrance, terrain.ENTRANCE)
        for door in self.connected.values():
            door.set(DoorType.REGULAR)


class HallsBossExitRoom(StandardRoom):
    def min_width(self) -> int:
        return max(super().min_width(), 7)

    def min_height(self) -> int:
        return max(super().min_height(), 7)

    def is_exit(self) -> bool:
        return True

    def paint(self, level, rng) -> None:
        Painter.fill(level, self, terrain.WALL)
        Painter.fill(level, self, 1, terrain.EMPTY)
        c = self.center(rng)
        Painter.set(level, c, terrain.LOCKED_EXIT)
        for door in self.connected.values():
            door.set(DoorType.REGULAR)


class YogDzewaBossRoom(StandardRoom):
    def size_cat_probs(self):
        return [0.0, 1.0, 0.0]

    def min_width(self) -> int:
        return max(super().min_width(), 14)

    def min_height(self) -> int:
        return max(super().min_height(), 14)

    def paint(self, level, rng) -> None:
        Painter.fill(level, self, terrain.WALL)
        Painter.fill(level, self, 1, terrain.EMPTY)

        for door in self.connected.values():
            door.set(DoorType.REGULAR)

        # Yog-Dzewa sits at center-top (upper third of room)
        cx = (self.left + self.right) // 2
        cy = self.top + (self.height() // 3)
        yog_pos = level.point_to_cell(Point(cx, cy))
        level.mobs.append(GenMob(cls_name="YogDzewa", pos=yog_pos))
        level.yog_pos = (cx, cy)
