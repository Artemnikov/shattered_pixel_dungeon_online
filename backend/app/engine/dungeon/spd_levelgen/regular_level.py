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
"""Port of the RegularLevel/SewerLevel build orchestration
(levels/RegularLevel.java `build`/`initRooms`/`builder`, levels/SewerLevel.java
overrides) -- the top-level sequence that selects rooms, runs the builder loop,
and invokes the painter, all consuming the per-floor seeded generator in the
exact order SPD does."""

from __future__ import annotations

import math
from collections import deque
from typing import List, Optional, Tuple

from app.engine.dungeon.spd_levelgen import generator as gen
from app.engine.dungeon.spd_levelgen import mob_spawner
from app.engine.dungeon.spd_levelgen import standard_rooms as std
from app.engine.dungeon.spd_levelgen import special_rooms as sr
from app.engine.dungeon.spd_levelgen import terrain
from app.engine.dungeon.spd_levelgen.builders import Builder, FigureEightBuilder, LoopBuilder
from app.engine.dungeon.spd_levelgen.geom import _to_f32
from app.engine.dungeon.spd_levelgen.level import Feeling, GenLevel, assign_feeling
from app.engine.dungeon.spd_levelgen.mob_spawner import GenMob
from app.engine.dungeon.spd_levelgen.room import Room
from app.engine.dungeon.spd_levelgen.room_types import SpecialRoom, StandardRoom
from app.engine.dungeon.spd_levelgen.run_state import (
    RunState, SPAWN_GOLDEN_KEY, SPAWN_GUIDE_PAGE_INTRO, is_boss_level, region_for_depth,
)
from app.engine.dungeon.spd_levelgen.caves_painter import CavesPainter
from app.engine.dungeon.spd_levelgen.regular_painter import RegularPainter
from app.engine.dungeon.spd_levelgen.city_painter import CityPainter
from app.engine.dungeon.spd_levelgen.halls_painter import HallsPainter
from app.engine.dungeon.spd_levelgen.prison_painter import PrisonPainter
from app.engine.dungeon.spd_levelgen.sewer_painter import SewerPainter
from app.engine.dungeon.spd_levelgen.traps import (
    caves_trap_chances, caves_trap_classes,
    city_trap_chances, city_trap_classes,
    halls_trap_chances, halls_trap_classes,
    prison_trap_chances, prison_trap_classes,
    sewer_trap_chances, sewer_trap_classes,
)
from app.engine.dungeon.spd_random import SPDRandom
from app.engine.mechanics.shadowcaster import cast_shadow

# Item-destroying trap classes (RegularLevel.randomDropCell's block list) --
# only ChillingTrap is reachable on sewers floors (see traps.sewer_trap_classes);
# the rest are listed for forward parity once prison/caves/city/halls land.
_ITEM_DESTROYING_TRAP_NAMES = frozenset({
    "BurningTrap", "BlazingTrap", "ChillingTrap", "FrostTrap",
    "ExplosiveTrap", "DisintegrationTrap", "PitfallTrap",
})

# PathFinder.dirLR (PathFinder.java:67) as (dx, dy) pairs, in left-to-right
# scan order: NW, W, SW, N, S, NE, E, SE.
_DIR_LR = ((-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1))


def _builder(rng: SPDRandom) -> Builder:
    """Port of RegularLevel.builder()."""
    if rng.IntMax(2) == 0:
        return LoopBuilder().set_loop_shape(2, rng.FloatRange(0.0, 0.65), rng.FloatRange(0.0, 0.50))
    else:
        return FigureEightBuilder().set_loop_shape(2, rng.FloatRange(0.3, 0.8), 0.0)


def _standard_rooms(rng: SPDRandom, depth: int, force_max: bool) -> int:
    region = region_for_depth(depth)
    if region == "sewers":
        return 6 if force_max else 4 + rng.chances((1.0, 3.0, 1.0))
    if region == "prison":
        return 6 if force_max else 5 + rng.chances((1.0, 1.0))
    if region == "caves":
        return 7 if force_max else 6 + rng.chances((2.0, 1.0))
    if region == "city":
        return 8 if force_max else 6 + rng.chances((1.0, 3.0, 1.0))
    return 9 if force_max else 8 + rng.chances((2.0, 1.0))


def _special_rooms(rng: SPDRandom, depth: int, force_max: bool) -> int:
    region = region_for_depth(depth)
    if region == "sewers":
        return 2 if force_max else 1 + rng.chances((1.0, 4.0))
    if region == "prison":
        return 3 if force_max else 1 + rng.chances((1.0, 3.0, 1.0))
    if region == "caves":
        return 3 if force_max else 2 + rng.chances((4.0, 1.0))
    if region == "city":
        return 3 if force_max else 2 + rng.chances((2.0, 1.0))
    return 3 if force_max else 2 + rng.chances((1.0, 1.0))


def _n_traps(rng: SPDRandom, depth: int) -> int:
    """Port of RegularLevel.nTraps()."""
    return rng.NormalIntRange(2, 3 + depth // 5)


def _painter(rng: SPDRandom, depth: int, feeling: Feeling) -> RegularPainter:
    """Dispatch to the region-appropriate painter with correct water/grass/trap params."""
    region = region_for_depth(depth)
    n = _n_traps(rng, depth)
    if region == "sewers":
        return (SewerPainter()
                .set_water(0.85 if feeling == Feeling.WATER else 0.30, 5)
                .set_grass(0.80 if feeling == Feeling.GRASS else 0.20, 4)
                .set_traps(n, sewer_trap_classes(depth), sewer_trap_chances(depth)))
    if region == "prison":
        return (PrisonPainter()
                .set_water(0.90 if feeling == Feeling.WATER else 0.30, 4)
                .set_grass(0.80 if feeling == Feeling.GRASS else 0.20, 3)
                .set_traps(n, prison_trap_classes(), prison_trap_chances()))
    if region == "caves":
        return (CavesPainter()
                .set_water(0.85 if feeling == Feeling.WATER else 0.30, 6)
                .set_grass(0.65 if feeling == Feeling.GRASS else 0.15, 3)
                .set_traps(n, caves_trap_classes(), caves_trap_chances()))
    if region == "city":
        return (CityPainter(depth)
                .set_water(0.90 if feeling == Feeling.WATER else 0.30, 4)
                .set_grass(0.80 if feeling == Feeling.GRASS else 0.20, 3)
                .set_traps(n, city_trap_classes(), city_trap_chances()))
    return (HallsPainter()
            .set_water(0.70 if feeling == Feeling.WATER else 0.15, 6)
            .set_grass(0.65 if feeling == Feeling.GRASS else 0.10, 3)
            .set_traps(n, halls_trap_classes(), halls_trap_chances()))


def _init_rooms(rng: SPDRandom, depth: int, feeling: Feeling, run_state: RunState) -> List[Room]:
    """Port of RegularLevel.initRooms() (SewerLevel does not override it)."""
    init_rooms: List[Room] = []

    entrance = std.create_entrance(rng, depth)
    init_rooms.append(entrance)
    exit_room = std.create_exit(rng, depth)
    init_rooms.append(exit_room)

    standards = _standard_rooms(rng, depth, feeling == Feeling.LARGE)
    if feeling == Feeling.LARGE:
        standards = math.ceil(standards * 1.5)

    i = 0
    while i < standards:
        while True:
            s = std.create_standard_room(rng, depth)
            if s.set_size_cat_max_room_value(rng, standards - i):
                break
        i += s.size_factor() - 1
        init_rooms.append(s)
        i += 1

    if depth in (6, 11, 16):
        from app.engine.dungeon.spd_levelgen.room_types import ShopRoom
        init_rooms.append(ShopRoom())

    # HallsLevel.initRooms(): adds one DemonSpawnerRoom on every Halls floor.
    if region_for_depth(depth) == "halls":
        init_rooms.append(sr.DemonSpawnerRoom())

    # Dungeon.shopOnLevel() is only true for depths 6/11/16 -- never on sewers floors.

    specials = _special_rooms(rng, depth, feeling == Feeling.LARGE)
    if feeling == Feeling.LARGE:
        specials += 1

    run_state.init_for_floor(rng, depth)
    i = 0
    while i < specials:
        s = run_state.create_special_room(rng, depth)
        if isinstance(s, sr.PitRoom):
            specials += 1
        init_rooms.append(s)
        i += 1

    secrets = run_state.secrets_for_floor(rng, depth)
    if feeling == Feeling.SECRETS:
        secrets += 1
    for _ in range(secrets):
        init_rooms.append(run_state.create_secret_room(rng))

    # CityLevel.initRooms(): Imp.Quest.spawn() rolls for AmbitiousImpRoom on
    # depths 17-19 (after all other rooms are decided).
    if region_for_depth(depth) == "city":
        imp_room = run_state.imp_quest.maybe_spawn(rng, depth)
        if imp_room is not None:
            init_rooms.append(imp_room)

    return init_rooms


def build_floor(rng: SPDRandom, depth: int, run_state: RunState) -> Tuple[GenLevel, List[Room]]:
    """Port of Level.create()'s pre-spawn sequence + RegularLevel.build():
    assign feeling (depth > 1), pick the builder, generate+shuffle init rooms,
    retry the builder loop until it succeeds, then paint. Returns the painted
    level and its final connected room list."""

    # Level.create(): the item preamble + feeling switch are both nested
    # inside `if (!Dungeon.bossLevel() && Dungeon.branch == 0)` -- on boss
    # floors (5/10/15/20/25) neither runs and feeling stays NONE.
    if is_boss_level(depth):
        feeling = Feeling.NONE
        preamble_items: List[object] = []
    else:
        preamble_items = run_state.consume_item_preamble(rng, depth)
        feeling = assign_feeling(rng, depth) if depth > 1 else Feeling.NONE

    level = GenLevel(depth, feeling)
    level.run_state = run_state
    level.items_to_spawn.extend(preamble_items)

    while True:
        builder = _builder(rng)
        init_rooms = _init_rooms(rng, depth, feeling, run_state)
        rng.shuffle(init_rooms)
        for r in init_rooms:
            r.neighbours.clear()
            r.connected.clear()
        rooms = builder.build(list(init_rooms), rng, depth)
        if rooms is not None:
            break

    painter = _painter(rng, depth, feeling)
    painter.paint(rng, level, rooms)

    # RegularLevel.build()'s tail (post-paint, pre-spawn): roomEntrance/
    # roomExit are the same instances queued first into initRooms (identity
    # preserved through shuffle/builder regardless of what `rooms` retains),
    # buildFlagMaps derives passable/solid/losBlocking/openSpace, then
    # Level.create() spawns mobs and items in that order.
    level.rooms = rooms
    # Port of RegularLevel.build()'s `r.isEntrance()`/`r.isExit()` scan
    # (RegularLevel.java:901-905) -- region-deco/water-bridge entrance/exit
    # variants override these methods rather than subclassing
    # EntranceRoom/ExitRoom directly, so an isinstance check misses them.
    level.room_entrance = next(r for r in rooms if r.is_entrance())
    level.room_exit = next(r for r in rooms if r.is_exit())
    level.build_flag_maps()

    create_mobs(rng, level)
    create_items(rng, level, run_state)

    return level, rooms


def _build_distance_map_limited(to_idx: int, passable: List[bool], width: int,
                                height: int, limit: int) -> List[Optional[int]]:
    """Port of PathFinder.buildDistanceMap(int to, boolean[] passable, int
    limit) (PathFinder.java:248-282) -- BFS that bails out entirely the first
    time the frontier distance would exceed `limit` (FIFO queue guarantees
    non-decreasing distances, so this is a safe early-out, not a per-node
    skip). `dirLR` order + the `start`/`end` edge-wrap guards are reproduced
    exactly; `None` stands in for Integer.MAX_VALUE."""
    size = width * height
    distance: List[Optional[int]] = [None] * size
    distance[to_idx] = 0
    queue: deque = deque([to_idx])
    while queue:
        step = queue.popleft()
        next_distance = distance[step] + 1
        if next_distance > limit:
            return distance
        x = step % width
        start = 3 if x == 0 else 0
        end = 3 if (x + 1) % width == 0 else 0
        for i in range(start, 8 - end):
            dx, dy = _DIR_LR[i]
            n = step + dx + dy * width
            if 0 <= n < size and passable[n] and (distance[n] is None or distance[n] > next_distance):
                queue.append(n)
                distance[n] = next_distance
    return distance


def _create_mob(rng: SPDRandom, level: GenLevel) -> GenMob:
    """Port of Level.createMob -- regenerates the per-level rotation cache
    from MobSpawner.getMobRotation when empty, then rolls (and discards) a
    champion buff to keep the RNG-call count constant."""
    if not level.mobs_to_spawn:
        level.mobs_to_spawn = mob_spawner.get_mob_rotation(rng, level.depth)
    cls_name = level.mobs_to_spawn.pop(0)
    mob_spawner.roll_for_champion(rng)
    return GenMob(cls_name=cls_name)


def _mob_limit(rng: SPDRandom, depth: int, feeling: Feeling) -> int:
    """Port of RegularLevel.mobLimit -- the `depth <= 1` branch is dead code
    from createMobs's call site (`Dungeon.depth == 1 ? 8 : mobLimit()` only
    invokes mobLimit for depth > 1), reproduced for fidelity regardless."""
    if depth <= 1:
        return 0  # Statistics.amuletObtained baseline false on a fresh game
    mobs = 3 + depth % 5 + rng.IntMax(3)
    if feeling == Feeling.LARGE:
        mobs = math.ceil(_to_f32(float(mobs) * _to_f32(1.33)))
    return mobs


def _mob_spawn_rejected(level: GenLevel, mob: GenMob, room_to_spawn: Room,
                        entrance_fov: List[bool], distance: List[Optional[int]]) -> bool:
    """Shared rejection predicate for both the primary and "second mob in this
    room" placement loops in createMobs (the `while (tries >= 0 && (...))`
    condition body, identical in both copies)."""
    pos = mob.pos
    return (level.find_mob(pos) is not None
            or entrance_fov[pos]
            or distance[pos] is not None
            or not level.passable[pos]
            or level.solid[pos]
            or not room_to_spawn.can_place_character(level.cell_to_point(pos), level)
            or pos == level.exit()
            or level.traps.get(pos) is not None
            or level.plants.get(pos) is not None
            or (not level.open_space[pos] and mob.is_large))


def _place_mob(rng: SPDRandom, level: GenLevel, mob: GenMob, room_to_spawn: Room,
               entrance_fov: List[bool], distance: List[Optional[int]]) -> bool:
    """Port of the `do { mob.pos = ...; tries--; } while (tries >= 0 && (...))`
    placement loop -- up to 31 draws of `room.random()`. Returns whether
    placement succeeded (`tries >= 0` after the loop)."""
    tries = 30
    while True:
        mob.pos = level.point_to_cell(room_to_spawn.random(rng))
        tries -= 1
        if not (tries >= 0 and _mob_spawn_rejected(level, mob, room_to_spawn, entrance_fov, distance)):
            break
    return tries >= 0


def _ghost_quest_spawn(rng: SPDRandom, level: GenLevel) -> None:
    """Port of Ghost.Quest.spawn() — consumes the exact RNG calls to maintain
    sequence parity (SewerLevel.createMobs() calls this before super). Only
    relevant on depths 2-4 (sewers non-boss); depth ≤ 1 and boss levels skip."""
    depth = level.depth
    if depth <= 1:
        return
    roll = rng.IntMax(max(1, 5 - depth))
    if roll != 0:
        return
    exit_room = level.room_exit
    rng.IntRange(exit_room.left + 1, exit_room.right - 1)
    rng.IntRange(exit_room.top + 1, exit_room.bottom - 1)
    rng.chances((0, 0, 10, 6, 3, 1))
    rng.chances((0, 0, 10, 6, 3, 1))
    rng.Long()


def create_mobs(rng: SPDRandom, level: GenLevel) -> None:
    """Port of RegularLevel.createMobs (RegularLevel.java:220-326)."""
    depth = level.depth
    _ghost_quest_spawn(rng, level)
    mobs_to_spawn = 8 if depth == 1 else _mob_limit(rng, depth, level.feeling)

    std_rooms: List[Room] = []
    for room in level.rooms:
        if isinstance(room, StandardRoom):
            for _ in range(room.mob_spawn_weight()):
                std_rooms.append(room)
    rng.shuffle(std_rooms)
    std_room_index = 0

    width = level.width()
    entrance_cell = level.entrance()
    entrance_fov = [False] * level.length()
    c = level.cell_to_point(entrance_cell)
    cast_shadow(c.x, c.y, width, entrance_fov, level.los_blocking, 8)

    entrance_walkable = [not s for s in level.solid]
    re = level.room_entrance
    for y in range(re.top + 1, re.bottom):
        for x in range(re.left + 1, re.right):
            cell = x + y * width
            if level.passable[cell]:
                entrance_walkable[cell] = True

    distance = _build_distance_map_limited(entrance_cell, entrance_walkable, width, level.height(), 8)

    mob: Optional[GenMob] = None
    while mobs_to_spawn > 0:
        if mob is None:
            mob = _create_mob(rng, level)

        if std_room_index >= len(std_rooms):
            std_room_index = 0
        room_to_spawn = std_rooms[std_room_index]
        std_room_index += 1

        if _place_mob(rng, level, mob, room_to_spawn, entrance_fov, distance):
            mobs_to_spawn -= 1
            level.mobs.append(mob)
            mob = None

            # chance to add a second mob to this room, except on floor 1
            if depth > 1 and mobs_to_spawn > 0 and rng.IntMax(4) == 0:
                mob = _create_mob(rng, level)
                if _place_mob(rng, level, mob, room_to_spawn, entrance_fov, distance):
                    mobs_to_spawn -= 1
                    level.mobs.append(mob)
                    mob = None

    for m in level.mobs:
        if level.map[m.pos] in (terrain.HIGH_GRASS, terrain.FURROWED_GRASS):
            level.map[m.pos] = terrain.GRASS
            level.los_blocking[m.pos] = False


def _random_room(rng: SPDRandom, level: GenLevel, room_type) -> Optional[Room]:
    """Port of RegularLevel.randomRoom -- shuffles `rooms` in place (consuming
    RNG every call) then returns the first instance of `room_type`."""
    rng.shuffle(level.rooms)
    for r in level.rooms:
        if isinstance(r, room_type):
            return r
    return None


def random_drop_cell(rng: SPDRandom, level: GenLevel, room_type=StandardRoom) -> int:
    """Port of RegularLevel.randomDropCell (both overloads; the no-arg form
    defaults `roomType` to StandardRoom). Up to 100 tries; -1 on exhaustion
    or when `randomRoom` itself returns null."""
    tries = 100
    while tries > 0:
        tries -= 1
        room = _random_room(rng, level, room_type)
        if room is None:
            return -1
        if room is not level.room_entrance:
            pos = level.point_to_cell(room.random(rng))
            if (level.passable[pos] and not level.solid[pos]
                    and pos != level.exit()
                    and level.heaps.get(pos) is None
                    and room.can_place_item(level.cell_to_point(pos), level)
                    and level.find_mob(pos) is None):
                trap = level.traps.get(pos)
                if trap is None or type(trap).__name__ not in _ITEM_DESTROYING_TRAP_NAMES:
                    return pos
    return -1


def _ungrass(level: GenLevel, cell: int) -> None:
    """The `if (map[cell] == HIGH_GRASS || FURROWED_GRASS) { ... }` snippet
    repeated at every drop site in createItems -- trampling clears tall grass."""
    if level.map[cell] in (terrain.HIGH_GRASS, terrain.FURROWED_GRASS):
        level.map[cell] = terrain.GRASS
        level.los_blocking[cell] = False


# Random.chances bucket weights for createItems's `nItems` roll (the literal
# `new float[]{6, 3, 1}` -- drops 3/4/5 items 60%/30%/10% of the time).
_N_ITEMS_CHANCES = (6.0, 3.0, 1.0)


def create_items(rng: SPDRandom, level: GenLevel, run_state: RunState) -> None:
    """Port of RegularLevel.createItems (RegularLevel.java:377-608), against
    the fresh-game baseline (no talents/documents found/Bones/DriedRose/
    trinkets/challenges -- see module-level baseline notes in run_state.py)."""
    depth = level.depth
    state = run_state.generator_state

    n_items = 3 + rng.chances(_N_ITEMS_CHANCES)
    if level.feeling == Feeling.LARGE:
        n_items += 2

    for _ in range(n_items):
        to_drop = gen.generator_random(state, rng, depth)
        if to_drop is None:
            continue

        cell = random_drop_cell(rng, level)
        _ungrass(level, cell)

        heap_type: Optional[str] = None
        roll = rng.IntMax(20)
        if roll == 0:
            heap_type = "SKELETON"
        elif 1 <= roll <= 4:
            # base mimic chance is 1/20, regular chest is 4/20 -- each +1x
            # mimic spawn rate converts to a 25% chance here
            if rng.Float() < (gen.MIMIC_CHANCE_MULTIPLIER - 1.0) / 4.0 and level.find_mob(cell) is None:
                level.mobs.append(gen.spawn_mimic(rng, level, cell, to_drop, depth))
                continue
            heap_type = "CHEST"
        elif roll == 5:
            if depth > 1 and level.find_mob(cell) is None:
                level.mobs.append(gen.spawn_mimic(rng, level, cell, to_drop, depth))
                continue
            heap_type = "CHEST"
        else:
            heap_type = "HEAP"

        if ((to_drop.is_artifact and rng.IntMax(2) == 0)
                or (to_drop.is_upgradable and rng.IntMax(4 - to_drop.level) == 0)):
            mimic_chance = (1.0 / 10.0) * gen.MIMIC_CHANCE_MULTIPLIER
            if depth > 1 and rng.Float() < mimic_chance and level.find_mob(cell) is None:
                level.mobs.append(gen.spawn_golden_mimic(rng, level, cell, to_drop, depth))
            else:
                dropped = level.drop(to_drop, cell)
                if level.heaps.get(cell) is dropped:
                    dropped.type = "LOCKED_CHEST"
                    level.add_item_to_spawn(SPAWN_GOLDEN_KEY)
        else:
            dropped = level.drop(to_drop, cell)
            dropped.type = heap_type
            # setHauntedIfCursed() -- cursed-state RNG is drawn from a
            # separately-pushed generator inside Item.random/Generator paths
            # and never reaches here on the fresh-game baseline (see notes
            # on Item.random's cursed roll in generator.py); a no-op here.

    for item in list(level.items_to_spawn):
        cell = random_drop_cell(rng, level)
        if "TrinketCatalyst" in item:
            level.drop(item, cell).type = "LOCKED_CHEST"
            key_cell = random_drop_cell(rng, level)
            level.drop(SPAWN_GOLDEN_KEY, key_cell).type = "HEAP"
            _ungrass(level, key_cell)
        else:
            level.drop(item, cell).type = "HEAP"
        _ungrass(level, cell)

    # Separate-generator blocks (RegularLevel.java:472-end): each pushes a
    # fresh generator seeded by exactly one Random.Long() drawn from the main
    # sequence, so only that single draw matters for outer-sequence parity --
    # what happens inside never perturbs subsequent main-sequence draws.
    # DARKNESS challenge / Bones / DriedRose / CACHED_RATIONS talent / lore
    # pages / ebony mimics / spyglass loot are all gated false on the
    # fresh-game baseline (challenges off, no bones file, no DriedRose item,
    # no talent, ADVENTURERS_GUIDE not yet fully read, MimicTooth.ebonyMimicChance
    # == 0, CrackedSpyglass.extraLootChance == 0) -- each consumes its seed
    # Long() (and any zero-RNG-gated draws inside) and produces nothing.

    rng.push_generator(rng.Long())  # DARKNESS challenge torch -- gated false
    rng.pop_generator()

    rng.push_generator(rng.Long())  # Bones.get() -- gated false (no bones file)
    rng.pop_generator()

    rng.push_generator(rng.Long())  # DriedRose petals -- gated false (no item)
    rng.pop_generator()

    rng.push_generator(rng.Long())  # CACHED_RATIONS talent -- gated false
    rng.pop_generator()

    # Guide pages: the only separate-generator block that can actually drop
    # something on a fresh game (no pages found yet -> missingPages is the
    # fixed 13-name list below, pageToDrop is always "Intro").
    rng.push_generator(rng.Long())
    drop_chance = _to_f32(0.25 * (depth - 1))
    if rng.Float() < drop_chance:
        cell = random_drop_cell(rng, level)
        _ungrass(level, cell)
        level.drop(SPAWN_GUIDE_PAGE_INTRO, cell)
    rng.pop_generator()

    rng.push_generator(rng.Long())  # lore pages -- gated false (guide incomplete)
    rng.pop_generator()

    rng.push_generator(rng.Long())  # ebony mimics -- ebonyMimicChance == 0
    rng.Float()
    rng.pop_generator()

    rng.push_generator(rng.Long())  # extra spyglass loot -- extraLootChance == 0
    rng.Float()
    rng.pop_generator()
