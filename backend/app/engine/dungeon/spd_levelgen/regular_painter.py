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
"""Port of com.shatteredpixel.shatteredpixeldungeon.levels.painters.RegularPainter
-- room shuffling/placement, door placement & hiding, water/grass cellular-automaton
overlays, and trap placement. Concrete region painters (e.g. SewerPainter) supply
`decorate()` plus water/grass/trap parameters via the `set_water`/`set_grass`/
`set_traps` builder methods (mirroring the Java fluent-setter pattern).

Fresh-game baseline assumptions (per the project's locked-in layout-parity scope):
- `SPDSettings.intro()` == True (default for a new install)
- `Document.ADVENTURERS_GUIDE.isPageFound(GUIDE_SEARCHING)` == False (no docs found)
  -> both make floor 1 & 2 entrance-door hiding paths active, exactly as for a
  brand new game.
"""

from __future__ import annotations

from typing import List, Optional

from app.engine.dungeon.spd_levelgen import graph, patch, terrain
from app.engine.dungeon.spd_levelgen.connection_rooms import ConnectionRoom
from app.engine.dungeon.spd_levelgen.geom import Point, Rect, _to_f32
from app.engine.dungeon.spd_levelgen.level import Feeling, GenLevel
from app.engine.dungeon.spd_levelgen.painter import Painter
from app.engine.dungeon.spd_levelgen.room import Door, DoorType, Room
from app.engine.dungeon.spd_levelgen.room_types import SizeCategory, SpecialRoom, StandardRoom
from app.engine.dungeon.spd_random import SPDRandom


def _circle4(width: int) -> tuple:
    """PathFinder.CIRCLE4 with the level's actual map width substituted."""
    return (-width, 1, width, -1)


def _neighbours8(width: int) -> tuple:
    """PathFinder.NEIGHBOURS8 with the level's actual map width substituted."""
    return (-width - 1, -width, -width + 1, -1, 1, width - 1, width, width + 1)


class RegularPainter(Painter):

    def __init__(self):
        self.water_fill = 0.0
        self.water_smoothness = 0
        self.grass_fill = 0.0
        self.grass_smoothness = 0
        self.n_traps = 0
        self.trap_classes: tuple = ()
        self.trap_chances: tuple = ()

    def set_water(self, fill: float, smoothness: int) -> "RegularPainter":
        self.water_fill = fill
        self.water_smoothness = smoothness
        return self

    def set_grass(self, fill: float, smoothness: int) -> "RegularPainter":
        self.grass_fill = fill
        self.grass_smoothness = smoothness
        return self

    def set_traps(self, num: int, classes: tuple, chances: tuple) -> "RegularPainter":
        self.n_traps = num
        self.trap_classes = classes
        self.trap_chances = chances
        return self

    def padding(self, level: GenLevel) -> int:
        return 2 if level.feeling == Feeling.CHASM else 1

    def paint(self, rng: SPDRandom, level: GenLevel, rooms: Optional[List[Room]]) -> bool:
        if rooms is not None:
            padding = self.padding(level)

            left_most = top_most = None
            for r in rooms:
                if left_most is None or r.left < left_most:
                    left_most = r.left
                if top_most is None or r.top < top_most:
                    top_most = r.top

            left_most -= padding
            top_most -= padding

            right_most = bottom_most = 0
            for r in rooms:
                r.shift(-left_most, -top_most)
                if r.right > right_most:
                    right_most = r.right
                if r.bottom > bottom_most:
                    bottom_most = r.bottom

            right_most += padding
            bottom_most += padding

            level.set_size(right_most + 1, bottom_most + 1)
        else:
            if level.length() == 0:
                return False
            rooms = []

        rng.shuffle(rooms)

        for r in list(rooms):
            if not r.connected:
                if isinstance(r, SpecialRoom):
                    return False
            self._place_doors(rng, r)
            r.paint(level, rng)

        self._paint_doors(rng, level, rooms)

        # use a separate RNG here so that extra painting variance doesn't
        # affect the rest of levelgen (e.g. minimizes mossy clump's effect)
        rng.push_generator(rng.Long())

        if self.water_fill > 0.0:
            self._paint_water(rng, level, rooms)

        if self.grass_fill > 0.0:
            self._paint_grass(rng, level, rooms)

        if self.n_traps > 0:
            self._paint_traps(rng, level, rooms)

        self.decorate(rng, level, rooms)

        rng.pop_generator()

        return True

    def decorate(self, rng: SPDRandom, level: GenLevel, rooms: List[Room]) -> None:
        raise NotImplementedError

    # -- door placement -----------------------------------------------------

    def _place_doors(self, rng: SPDRandom, r: Room) -> None:
        for n, door in list(r.connected.items()):
            if door is None:
                i = r.intersect(n)
                door_spots = []
                for p in i.get_points():
                    if r.can_connect_point(p) and n.can_connect_point(p):
                        door_spots.append(p)
                if not door_spots:
                    continue
                spot = rng.element(door_spots)
                door = Door(spot.x, spot.y)
                r.connected[n] = door
                n.connected[r] = door

    def _paint_doors(self, rng: SPDRandom, l: GenLevel, rooms: List[Room]) -> None:
        hidden_door_chance = 0.0
        if l.depth > 1:
            hidden_door_chance = min(1.0, l.depth / 20.0)
        if l.feeling == Feeling.SECRETS:
            hidden_door_chance = (0.5 + hidden_door_chance) / 2.0

        room_merges: dict = {}

        for r in rooms:
            for n in list(r.connected.keys()):

                if room_merges.get(r) is n or room_merges.get(n) is r:
                    continue
                elif (r not in room_merges and n not in room_merges
                        and self._merge_rooms(rng, l, r, n, r.connected[n], terrain.EMPTY)):
                    if isinstance(r, StandardRoom) and r.size_cat == SizeCategory.NORMAL:
                        room_merges[r] = n
                    if isinstance(n, StandardRoom) and n.size_cat == SizeCategory.NORMAL:
                        room_merges[n] = r
                    continue

                d = r.connected[n]
                door = d.x + d.y * l.width()

                if d.type == DoorType.REGULAR:
                    if rng.Float() < hidden_door_chance:
                        d.type = DoorType.HIDDEN
                        if l.feeling != Feeling.SECRETS:
                            graph.build_distance_map(rooms, r)
                            if n.distance == graph.INFINITY:
                                d.type = DoorType.UNLOCKED
                        else:
                            rooms_in_graph = 0
                            graph.build_distance_map(rooms, r)
                            for r_dest in rooms:
                                if r_dest.distance != graph.INFINITY and not isinstance(r_dest, ConnectionRoom):
                                    rooms_in_graph += 1
                            if rooms_in_graph < 2:
                                d.type = DoorType.UNLOCKED
                            else:
                                rooms_in_graph = 0
                                graph.build_distance_map(rooms, n)
                                for n_dest in rooms:
                                    if n_dest.distance != graph.INFINITY and not isinstance(n_dest, ConnectionRoom):
                                        rooms_in_graph += 1
                                if rooms_in_graph < 2:
                                    d.type = DoorType.UNLOCKED
                        graph.build_distance_map(rooms, r)
                        if l.feeling != Feeling.SECRETS and n.distance == graph.INFINITY:
                            d.type = DoorType.UNLOCKED
                    else:
                        d.type = DoorType.UNLOCKED

                # fresh-game baseline: SPDSettings.intro() == True (depth 1),
                # !Document.ADVENTURERS_GUIDE.isPageFound(GUIDE_SEARCHING) == True (depth 2)
                if d.type == DoorType.UNLOCKED and (r.is_entrance() or n.is_entrance()):
                    if l.depth == 1 or l.depth == 2:
                        d.type = DoorType.HIDDEN

                if d.type == DoorType.EMPTY:
                    l.map[door] = terrain.EMPTY
                elif d.type == DoorType.TUNNEL:
                    l.map[door] = l.tunnel_tile()
                elif d.type == DoorType.WATER:
                    l.map[door] = terrain.WATER
                elif d.type == DoorType.UNLOCKED:
                    l.map[door] = terrain.DOOR
                elif d.type == DoorType.HIDDEN:
                    l.map[door] = terrain.SECRET_DOOR
                elif d.type == DoorType.BARRICADE:
                    l.map[door] = terrain.BARRICADE
                elif d.type == DoorType.LOCKED:
                    l.map[door] = terrain.LOCKED_DOOR
                elif d.type == DoorType.CRYSTAL:
                    l.map[door] = terrain.CRYSTAL_DOOR
                elif d.type == DoorType.WALL:
                    l.map[door] = terrain.WALL

    def _merge_rooms(self, rng: SPDRandom, l: GenLevel, r: Room, n: Room,
                     start: Optional[Point], merge_terrain: int) -> bool:
        intersect = r.intersect(n)
        if intersect.left == intersect.right:
            merge = Rect()
            merge.left = merge.right = intersect.left
            merge.top = merge.bottom = start.y if start is not None else intersect.center(rng).y

            p = Point(merge.left, merge.top)
            while (merge.top > intersect.top
                   and n.can_merge(l, r, p, merge_terrain) and r.can_merge(l, n, p, merge_terrain)):
                merge.top -= 1
                p.y -= 1
            p.y = merge.bottom
            while (merge.bottom < intersect.bottom
                   and n.can_merge(l, r, p, merge_terrain) and r.can_merge(l, n, p, merge_terrain)):
                merge.bottom += 1
                p.y += 1

            if merge.height() >= 3:
                r.merge(l, n, Rect(merge.left, merge.top + 1, merge.left + 1, merge.bottom), merge_terrain)
                return True
            return False

        elif intersect.top == intersect.bottom:
            merge = Rect()
            merge.left = merge.right = start.x if start is not None else intersect.center(rng).x
            merge.top = merge.bottom = intersect.top

            p = Point(merge.left, merge.top)
            while (merge.left > intersect.left
                   and n.can_merge(l, r, p, merge_terrain) and r.can_merge(l, n, p, merge_terrain)):
                merge.left -= 1
                p.x -= 1
            p.x = merge.right
            while (merge.right < intersect.right
                   and n.can_merge(l, r, p, merge_terrain) and r.can_merge(l, n, p, merge_terrain)):
                merge.right += 1
                p.x += 1

            if merge.width() >= 3:
                r.merge(l, n, Rect(merge.left + 1, merge.top, merge.right, merge.top + 1), merge_terrain)
                return True
            return False

        else:
            return False

    # -- water / grass / traps ----------------------------------------------

    def _paint_water(self, rng: SPDRandom, l: GenLevel, rooms: List[Room]) -> None:
        lake = patch.generate(rng, l.width(), l.height(), self.water_fill, self.water_smoothness, True)

        if rooms:
            for r in rooms:
                for p in r.water_placeable_points():
                    i = l.point_to_cell(p)
                    if lake[i] and l.map[i] == terrain.EMPTY:
                        l.map[i] = terrain.WATER
        else:
            for i in range(l.length()):
                if lake[i] and l.map[i] == terrain.EMPTY:
                    l.map[i] = terrain.WATER

    def _paint_grass(self, rng: SPDRandom, l: GenLevel, rooms: List[Room]) -> None:
        grass = patch.generate(rng, l.width(), l.height(), self.grass_fill, self.grass_smoothness, True)

        grass_cells: List[int] = []
        if rooms:
            for r in rooms:
                for p in r.grass_placeable_points():
                    i = l.point_to_cell(p)
                    if grass[i] and l.map[i] == terrain.EMPTY:
                        grass_cells.append(i)
        else:
            for i in range(l.length()):
                if grass[i] and l.map[i] == terrain.EMPTY:
                    grass_cells.append(i)

        neighbours8 = _neighbours8(l.width())
        for i in grass_cells:
            if l.heaps.get(i) is not None or l.find_mob(i) is not None:
                l.map[i] = terrain.GRASS
                continue

            count = 1
            for n in neighbours8:
                if grass[i + n]:
                    count += 1
            l.map[i] = terrain.HIGH_GRASS if rng.Float() < _to_f32(count / 12.0) else terrain.GRASS

    def _paint_traps(self, rng: SPDRandom, l: GenLevel, rooms: List[Room]) -> None:
        valid_cells: List[int] = []
        if rooms:
            for r in rooms:
                for p in r.trap_placeable_points():
                    i = l.point_to_cell(p)
                    if l.map[i] == terrain.EMPTY:
                        valid_cells.append(i)
        else:
            for i in range(l.length()):
                if l.map[i] == terrain.EMPTY:
                    valid_cells.append(i)

        n_traps = min(self.n_traps, len(valid_cells) // 5)

        valid_non_hallways: List[int] = []

        for i in range(l.length()):
            l.passable[i] = l.map[i] in terrain.PASSABLE

        circle4 = _circle4(l.width())
        for i in valid_cells:
            if ((l.passable[i + circle4[0]] or l.passable[i + circle4[2]])
                    and (l.passable[i + circle4[1]] or l.passable[i + circle4[3]])):
                valid_non_hallways.append(i)

        n_traps = min(n_traps, len(valid_cells) // 5)

        revealed_chance = self._reveal_hidden_trap_chance()
        reveal_inc = 0.0

        count = 5 * n_traps if l.feeling == Feeling.TRAPS else n_traps
        for i in range(count):
            trap = self.trap_classes[rng.chances(self.trap_chances)]()

            if trap.avoids_hallways and valid_non_hallways:
                trap_pos = rng.element(valid_non_hallways)
            else:
                trap_pos = rng.element(valid_cells)

            valid_cells.remove(trap_pos)
            if trap_pos in valid_non_hallways:
                valid_non_hallways.remove(trap_pos)

            reveal_inc += revealed_chance
            if i >= n_traps or reveal_inc >= 1.0:
                trap.reveal()
                reveal_inc -= 1.0
            else:
                trap.hide()

            l.set_trap(trap, trap_pos)
            l.map[trap_pos] = terrain.TRAP if trap.visible else terrain.SECRET_TRAP

    @staticmethod
    def _reveal_hidden_trap_chance() -> float:
        from app.engine.dungeon.spd_levelgen.traps import reveal_hidden_trap_chance
        return reveal_hidden_trap_chance()
