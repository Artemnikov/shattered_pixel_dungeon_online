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
"""Minimal port of com.shatteredpixel.shatteredpixeldungeon.levels.Level --
just enough surface for the Painter to run standalone against a synthetic room
layout: map storage, size bookkeeping, the Feeling assignment RNG sequence,
and the placeable-points/trap/heap/mob hooks the painter touches.

Painting always happens before mob/item spawning in `Level.create()`, so
`heaps`/`findMob` are guaranteed empty/None at paint-time -- this stub
hardcodes that and is therefore lossless for layout-parity purposes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, List, Optional

from app.engine.dungeon.spd_levelgen import terrain
from app.engine.dungeon.spd_levelgen.geom import Point
from app.engine.dungeon.spd_levelgen.room import Room
from app.engine.dungeon.spd_levelgen.traps import Trap
from app.engine.dungeon.spd_random import SPDRandom

# PathFinder.CIRCLE8 (PathFinder.java:74) -- built relative to a width below.
_CIRCLE8_OFFSETS = ((-1, -1), (0, -1), (1, -1), (1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0))


@dataclass
class GenHeap:
    """Stand-in for Heap -- structural facts only (the contained item
    descriptors, Heap.Type, hidden flag); enough for placement-parity since
    drop()'s RNG-consuming branches never trigger in the createItems context
    (see Level.drop note on RegularLevel.randomDropCell guarantees)."""

    items: List[Any] = field(default_factory=list)
    type: str = "HEAP"
    hidden: bool = False
    pos: int = -1


class Feeling(Enum):
    NONE = auto()
    CHASM = auto()
    WATER = auto()
    GRASS = auto()
    DARK = auto()
    LARGE = auto()
    TRAPS = auto()
    SECRETS = auto()


def assign_feeling(rng: SPDRandom, depth: int) -> Feeling:
    """Port of the `switch (Random.Int(14))` block in Level.create()
    (Level.java:259-294), hardcoded to the fresh-game baseline:
    MossyClump/TrapMechanism overrideNormalLevelChance() both -> 0, so the
    `default` branch always draws exactly 2 Random.Float() and lands on NONE
    (both `< 0f` comparisons are always false). Only called when depth > 1,
    matching the `if (Dungeon.depth > 1)` guard at the call site."""
    outcome = rng.IntMax(14)
    if outcome == 0:
        return Feeling.CHASM
    elif outcome == 1:
        return Feeling.WATER
    elif outcome == 2:
        return Feeling.GRASS
    elif outcome == 3:
        return Feeling.DARK
    elif outcome == 4:
        return Feeling.LARGE
    elif outcome == 5:
        return Feeling.TRAPS
    elif outcome == 6:
        return Feeling.SECRETS
    else:
        rng.Float()  # MossyClump.overrideNormalLevelChance() == 0 -> always false
        rng.Float()  # TrapMechanism.overrideNormalLevelChance() == 0 -> always false
        return Feeling.NONE


class GenLevel:
    """Stand-in for Level -- map storage + the hooks RegularPainter/SewerPainter
    touch (`width`/`height`/`length`, `setSize`, `pointToCell`, `tunnelTile`,
    `passable`, `heaps`/`findMob` (always empty pre-spawn), `setTrap`)."""

    def __init__(self, depth: int, feeling: Feeling = Feeling.NONE):
        self.depth = depth
        self.feeling = feeling
        # Set by build_floor right after construction -- gives room paint()
        # methods (e.g. CrystalPathRoom) access to the threaded RunState
        # (Generator POTION/SCROLL deck state) without changing every room's
        # paint(level, rng) signature. Untyped here to avoid an import cycle
        # (run_state -> special_rooms -> level).
        self.run_state = None
        # itemsToSpawn (Level.create()'s preamble queues PotionOfStrength/
        # ScrollOfUpgrade/Stylus/StoneOf*/TrinketCatalyst/a FOOD roll before
        # special rooms paint -- see RunState.consume_item_preamble); entries
        # are frozenset descriptors (run_state.SPAWN_*), matched/popped by
        # find_prize_item exactly like Level.findPrizeItem.
        self.items_to_spawn: list[frozenset] = []
        self.map: list[int] = []
        self._width = 0
        self._height = 0
        self._length = 0
        self.passable: list[bool] = []
        self.solid: list[bool] = []
        self.los_blocking: list[bool] = []
        self.open_space: list[bool] = []
        self.traps: dict[int, Trap] = {}
        self.heaps: dict[int, object] = {}
        self.plants: dict[int, object] = {}
        self.mobs: list = []
        # Level.mobsToSpawn -- per-level rotation cache, regenerated by
        # createMob/get_mob_rotation whenever it runs empty.
        self.mobs_to_spawn: list = []
        # Set by build_floor after painting -- the final connected room list
        # plus the EntranceRoom/ExitRoom instances (RegularLevel.roomEntrance/
        # roomExit), needed by createMobs/createItems' room-membership checks.
        self.rooms: List[Room] = []
        self.room_entrance: Optional[Room] = None
        self.room_exit: Optional[Room] = None
        # City boss (DwarfKing) summon pedestal positions; set by DwarfKingBossRoom.paint()
        self.dk_summon_spots: list = []
        # Halls boss (YogDzewa) spawn position; set by YogDzewaBossRoom.paint()
        self.yog_pos: Optional[tuple] = None

    def width(self) -> int:
        return self._width

    def height(self) -> int:
        return self._height

    def length(self) -> int:
        return self._length

    def set_size(self, w: int, h: int) -> None:
        self._width = w
        self._height = h
        self._length = w * h
        fill = terrain.CHASM if self.feeling == Feeling.CHASM else terrain.WALL
        self.map = [fill] * self._length
        self.passable = [False] * self._length

    def point_to_cell(self, p: Point) -> int:
        return p.x + p.y * self._width

    def cell_to_point(self, cell: int) -> Point:
        return Point(cell % self._width, cell // self._width)

    def tunnel_tile(self) -> int:
        return terrain.EMPTY_SP if self.feeling == Feeling.CHASM else terrain.EMPTY

    def true_distance(self, a: int, b: int) -> float:
        ax, ay = a % self._width, a // self._width
        bx, by = b % self._width, b // self._width
        return ((ax - bx) ** 2 + (ay - by) ** 2) ** 0.5

    def add_item_to_spawn(self, item: Optional[frozenset]) -> Optional[frozenset]:
        """Port of Level.addItemToSpawn -- queues a descriptor (no-op for None,
        mirroring the `if (item != null)` guard; Generator.random/randomArtifact
        etc can return null e.g. when the artifact deck is exhausted)."""
        if item is not None:
            self.items_to_spawn.append(item)
        return item

    def find_prize_item(self, rng: SPDRandom, match: Optional[str] = None) -> Optional[frozenset]:
        """Port of Level.findPrizeItem()/findPrizeItem(Class<?extends Item>).
        `match` is the supertype label this is checked against (None |
        'TrinketCatalyst' | 'Scroll' | 'Runestone' | 'PotionOfStrength' --
        the only matches any special room ever queries); satisfied when
        `match in descriptor`. Pops by index (not value) to mirror Java's
        reference-identity `itemsToSpawn.remove(item)`."""
        if not self.items_to_spawn:
            return None
        if match is None:
            for i, item in enumerate(self.items_to_spawn):
                if "TrinketCatalyst" in item:
                    return self.items_to_spawn.pop(i)
            idx = rng.IntMax(len(self.items_to_spawn))
            return self.items_to_spawn.pop(idx)
        for i, item in enumerate(self.items_to_spawn):
            if match in item:
                return self.items_to_spawn.pop(i)
        return None

    def find_mob(self, pos: int) -> Optional[object]:
        """Port of Level.findMob -- linear scan over placed mobs by position."""
        for mob in self.mobs:
            if mob.pos == pos:
                return mob
        return None

    def drop(self, item: Any, cell: int) -> GenHeap:
        """Port of Level.drop -- ALWAYS takes the `heap == null -> new Heap`
        branch here: every call site in createItems is preceded by
        randomDropCell(), which guarantees heaps.get(pos) == null and
        passable[pos] (excluding CHASM), so the heap-merge-into-LOCKED_CHEST
        (Random.Int(8) neighbour search) and dropToChasm RNG-consuming
        branches can never trigger."""
        heap = GenHeap(items=[item], type="HEAP", pos=cell)
        self.heaps[cell] = heap
        return heap

    def plant(self, seed: Any, pos: int) -> None:
        self.plants[pos] = seed

    def set_trap(self, trap: Trap, pos: int) -> Trap:
        self.traps.pop(pos, None)
        trap.set(pos)
        self.traps[pos] = trap
        return trap

    def _unique_terrain_cell(self, tile_id: int) -> int:
        for cell, value in enumerate(self.map):
            if value == tile_id:
                return cell
        raise ValueError(f"no terrain id {tile_id} found on the painted map")

    def entrance(self) -> int:
        """Port of Level.entrance() -- the cell EntranceRoom painted ENTRANCE/
        ENTRANCE_SP onto (LevelTransition.cell(), scanned directly since
        exactly one such tile exists per floor and no transition machinery
        is otherwise needed for layout/spawn parity)."""
        for cell, value in enumerate(self.map):
            if value == terrain.ENTRANCE or value == terrain.ENTRANCE_SP:
                return cell
        raise ValueError("no ENTRANCE/ENTRANCE_SP tile found on the painted map")

    def exit(self) -> int:
        """Port of Level.exit() -- the cell ExitRoom painted EXIT onto."""
        return self._unique_terrain_cell(terrain.EXIT)

    def room(self, pos: int) -> Optional[Room]:
        """Port of RegularLevel.room(int) -- linear search over `rooms`."""
        p = self.cell_to_point(pos)
        for r in self.rooms:
            if r.inside(p):
                return r
        return None

    def build_flag_maps(self) -> None:
        """Port of Level.buildFlagMaps()/updateOpenSpace (Level.java:829-883):
        zero-RNG, derives passable/losBlocking/solid/openSpace purely from the
        final painted `map`. Border cells are forced solid+losBlocking, never
        passable/avoid. openSpace[i] uses an 8-direction CIRCLE8 scan: any
        solid diagonal/orthogonal neighbour at an odd index disqualifies the
        cell; otherwise two consecutive non-solid neighbours qualify it."""
        length = self._length
        width = self._width
        height = self._height
        passable = [False] * length
        solid = [False] * length
        los_blocking = [False] * length

        for i in range(length):
            tile = self.map[i]
            passable[i] = tile in terrain.PASSABLE
            solid[i] = tile in terrain.SOLID
            los_blocking[i] = tile in terrain.LOS_BLOCKING

        for x in range(width):
            for cell in (x, x + (height - 1) * width):
                passable[cell] = False
                solid[cell] = True
                los_blocking[cell] = True
        for y in range(height):
            for cell in (y * width, (width - 1) + y * width):
                passable[cell] = False
                solid[cell] = True
                los_blocking[cell] = True

        self.passable = passable
        self.solid = solid
        self.los_blocking = los_blocking
        self._update_open_space()

    def _update_open_space(self) -> None:
        length = self._length
        width = self._width
        height = self._height
        solid = self.solid
        open_space = [False] * length

        for i in range(length):
            x, y = i % width, i // width
            if x == 0 or y == 0 or x == width - 1 or y == height - 1:
                continue
            neighbours = []
            for dx, dy in _CIRCLE8_OFFSETS:
                neighbours.append(solid[(x + dx) + (y + dy) * width])
            qualifies = False
            for j in (1, 3, 5, 7):
                if neighbours[j]:
                    qualifies = False
                    break
                if not neighbours[(j + 1) % 8] and not neighbours[(j + 2) % 8]:
                    qualifies = True
                    break
            open_space[i] = qualifies

        self.open_space = open_space
