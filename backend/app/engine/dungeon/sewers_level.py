"""Orchestrator for the SPD-style sewers pipeline.

Builds a list of Rooms, hands them to a LoopBuilder or FigureEightBuilder
to assign rectangles + connections, then to a SewerPainter to stamp the
tile grid. Returns a SewersGenerationResult that's shape-compatible with
the legacy mixin's output so GameInstance can swap pipelines without
touching downstream code.

Coverage: entrance + exit, N standard rooms (EmptyRoom), tunnel
corridors, special rooms (Shop, Vault, plain), secret rooms via maze
connections, doors (regular/hidden/locked), water/grass blobs via Patch
CA, trap placement, region decorate pass, and key spawning for each
locked special room.
"""

from __future__ import annotations

import random
from collections import deque
from typing import Dict, List, Optional, Tuple

from app.engine.dungeon.builders import FigureEightBuilder, LoopBuilder
from app.engine.dungeon.constants import RoomKind, TileType
from app.engine.dungeon.models import (
    Room as LegacyRoom,
    SewersGenerationMetadata,
    SewersGenerationResult,
    SewersProfile,
)
from app.engine.dungeon.painters import LevelCanvas, SewerPainter
from app.engine.dungeon.rooms.connection import ConnectionRoom
from app.engine.dungeon.rooms.room import DoorType, Room
from app.engine.dungeon.rooms.secret import SecretRoom
from app.engine.dungeon.rooms.special import ShopRoom, SpecialRoom, VaultRoom
from app.engine.dungeon.rooms.standard import EmptyRoom, EntranceRoom, ExitRoom


def generate_sewers_level(width: int, height: int, profile: SewersProfile,
                           seed: Optional[int] = None) -> SewersGenerationResult:
    rng = random.Random(seed if seed is not None else random.Random().getrandbits(32))

    # --- 1. Build the room list -----------------------------------------
    # Legacy convention (shared by tests + downstream systems): the
    # STANDARD room bucket contains entrance + exit + regular rooms,
    # totalling profile.STANDARD_ROOMS_MIN..MAX. So `standard_count` is
    # the TOTAL standard-room count; we spawn `standard_count - 2`
    # EmptyRooms in addition to the mandatory entrance + exit.
    standard_count = rng.randint(profile.STANDARD_ROOMS_MIN, profile.STANDARD_ROOMS_MAX)
    special_count = rng.randint(profile.SPECIAL_ROOMS_MIN, profile.SPECIAL_ROOMS_MAX)

    entrance = EntranceRoom()
    entrance.size_cat = _roll_size_cat(entrance, rng)
    exit_room = ExitRoom()
    exit_room.size_cat = _roll_size_cat(exit_room, rng)

    init_rooms: List[Room] = [entrance, exit_room]
    empty_count = max(0, standard_count - 2)
    for _ in range(empty_count):
        r = EmptyRoom()
        r.size_cat = _roll_size_cat(r, rng)
        init_rooms.append(r)

    # Special rooms. One per floor can be a locked VaultRoom (requires a
    # key spawn elsewhere). Shops use ShopRoom, everything else uses the
    # SpecialRoom base. Mirrors legacy _place_special_rooms: at most one
    # locked vault per floor.
    special_rooms: List[SpecialRoom] = []
    vault_assigned = False
    for _ in range(special_count):
        pick = rng.random()
        if not vault_assigned and pick < 0.25:
            sp = VaultRoom()
            vault_assigned = True
        elif pick < 0.4:
            sp = ShopRoom()
        else:
            sp = SpecialRoom()
        special_rooms.append(sp)
        init_rooms.append(sp)

    # Hidden rooms — small, single-connection, accessed via SECRET_DOOR.
    secret_rooms: List[SecretRoom] = []
    for _ in range(profile.HIDDEN_ROOMS_COUNT):
        s = SecretRoom()
        secret_rooms.append(s)
        init_rooms.append(s)

    # --- 2. Run the builder with up to ~20 attempts ---------------------
    rooms: Optional[List[Room]] = None
    layout_kind = "loop"
    for _ in range(20):
        for r in init_rooms:
            r.clear_connections()
            r.set_empty()
        # Pick layout randomly like the legacy path did.
        if standard_count >= 5 and rng.random() < 0.5:
            layout_kind = "figure_eight"
            builder = (FigureEightBuilder(rng=rng)
                        .set_loop_shape(2, rng.uniform(0.3, 0.8), 0.0))
        else:
            layout_kind = "loop"
            builder = (LoopBuilder(rng=rng)
                        .set_loop_shape(2, rng.uniform(0.0, 0.65),
                                         rng.uniform(0.0, 0.50)))
        rooms = builder.build(list(init_rooms))
        if rooms is not None:
            break

    if rooms is None:
        raise RuntimeError("Sewers builder failed after 20 attempts")

    # --- 3. Paint -------------------------------------------------------
    canvas = LevelCanvas(width, height, rng, fill=TileType.WALL)
    n_traps = rng.randint(profile.TRAPS_MIN, profile.TRAPS_MAX)
    weights = tuple(1.0 for _ in profile.TRAP_TYPES)
    painter = (SewerPainter(rng=rng, depth=profile.depth)
               .set_water(profile.WATER_RATIO, 5)
               .set_grass(profile.GRASS_RATIO, 4)
               .set_traps(n_traps, profile.TRAP_TYPES, weights))
    if not painter.paint(canvas, rooms):
        raise RuntimeError("Sewers painter produced nothing")

    # --- 4. Convert to legacy shape (exclusive width/height) ------------
    # Downstream code (GameInstance, tests, AI) uses legacy Room where x,y
    # is the top-left floor cell and width/height count interior cells only.
    # ConnectionRooms are skipped — legacy treats corridors as implicit.
    id_for_new: Dict[int, int] = {}
    legacy_rooms: List[LegacyRoom] = []
    hidden_room_ids: List[int] = []
    special_room_ids: List[int] = []
    standard_room_ids: List[int] = []
    for new_r in rooms:
        if isinstance(new_r, ConnectionRoom):
            continue
        rid = len(legacy_rooms)
        id_for_new[id(new_r)] = rid
        if isinstance(new_r, SecretRoom):
            kind = RoomKind.HIDDEN
            hidden_room_ids.append(rid)
            template = "secret"
        elif isinstance(new_r, SpecialRoom):
            kind = RoomKind.SPECIAL
            special_room_ids.append(rid)
            template = new_r.template
        else:
            kind = RoomKind.STANDARD
            standard_room_ids.append(rid)
            template = "standard"
        legacy_rooms.append(LegacyRoom(
            x=new_r.left + 1,
            y=new_r.top + 1,
            width=max(0, new_r.right - new_r.left - 1),
            height=max(0, new_r.bottom - new_r.top - 1),
            kind=kind,
            template=template,
            room_id=rid,
        ))

    entrance_id = id_for_new.get(id(entrance), 0)
    exit_id = id_for_new.get(id(exit_room), legacy_rooms[-1].room_id if legacy_rooms else 0)

    # Collapse the builder's Room graph (which includes ConnectionRooms as
    # transit nodes) down to an edge list over just the "real" rooms.
    edges: List[Tuple[int, int]] = []
    seen_edges = set()
    for start_new in rooms:
        if id(start_new) not in id_for_new:
            continue
        a_id = id_for_new[id(start_new)]
        visited = {id(start_new)}
        q = deque(start_new.connected)
        while q:
            cur = q.popleft()
            if id(cur) in visited:
                continue
            visited.add(id(cur))
            if id(cur) in id_for_new:
                key = tuple(sorted((a_id, id_for_new[id(cur)])))
                if key not in seen_edges:
                    seen_edges.add(key)
                    edges.append(key)
                continue
            for onward in cur.connected:
                if id(onward) not in visited:
                    q.append(onward)

    # Walk every door once and build the three metadata maps.
    hidden_door_positions: Dict[Tuple[int, int], int] = {}
    locked_doors: Dict[Tuple[int, int], str] = {}
    processed_doors = set()
    for new_r in rooms:
        for other, door in new_r.connected.items():
            if door is None or id(door) in processed_doors:
                continue
            processed_doors.add(id(door))
            pos = (door.x, door.y)
            if door.type == DoorType.HIDDEN:
                # Save the tile to restore when the player searches it out.
                hidden_door_positions[pos] = TileType.DOOR
            elif door.type == DoorType.LOCKED:
                # The locked room is whichever side is a VaultRoom. Build a
                # deterministic per-floor key_id so the runtime unlock path
                # can match "which key opens which door".
                locked_side = new_r if isinstance(new_r, VaultRoom) else other
                lock_rid = id_for_new.get(id(locked_side))
                key_id = f"sewers_key_{lock_rid}"
                locked_doors[pos] = key_id

    # Key spawn: pick a reachable floor cell not inside the locked room.
    key_spawns: Dict[str, Tuple[int, int]] = {}
    for key_id in sorted(set(locked_doors.values())):
        pos = _pick_key_spawn(
            rng=rng,
            grid=canvas.grid,
            rooms=rooms,
            id_for_new=id_for_new,
            forbid_rooms=[r for r in rooms if isinstance(r, VaultRoom) or isinstance(r, SecretRoom)],
            forbid_positions=set(locked_doors.keys()) | hidden_door_positions.keys(),
            start=entrance.center() if not entrance.is_empty() else (1, 1),
        )
        if pos is None:
            raise RuntimeError("Could not place key for locked vault")
        key_spawns[key_id] = pos

    metadata = SewersGenerationMetadata(
        region="sewers",
        layout_kind=layout_kind,
        room_ids_by_kind={
            RoomKind.STANDARD: standard_room_ids,
            RoomKind.SPECIAL: special_room_ids,
            RoomKind.HIDDEN: hidden_room_ids,
        },
        room_connections=edges,
        hidden_doors=hidden_door_positions,
        locked_doors=locked_doors,
        key_spawns=key_spawns,
        traps=dict(painter.placed_traps),
        start_room_id=entrance_id,
        end_room_id=exit_id,
        seed=seed or 0,
    )
    return SewersGenerationResult(grid=canvas.grid, rooms=legacy_rooms, metadata=metadata)


def _roll_size_cat(room, rng):
    room.set_size_cat(rng)
    return room.size_cat


# Tiles that count as "walkable floor" for the key-spawn flood fill.
_FLOOD_PASSABLE = {
    TileType.FLOOR, TileType.DOOR, TileType.STAIRS_UP, TileType.STAIRS_DOWN,
    TileType.FLOOR_GRASS, TileType.HIGH_GRASS, TileType.FLOOR_WATER,
    TileType.EMPTY_DECO, TileType.SECRET_TRAP, TileType.TRAP, TileType.INACTIVE_TRAP,
}


def _pick_key_spawn(rng, grid, rooms, id_for_new, forbid_rooms,
                     forbid_positions, start):
    """Flood-fill from `start` over passable tiles, then pick a random cell
    that isn't inside a forbidden room and isn't on a door.

    Mirrors SPD's KeyRoom logic: the key must be reachable from the
    entrance WITHOUT crossing the locked door, so a player can always
    find the key before the door. We flood-fill through DOOR tiles but
    NOT through LOCKED_DOOR/SECRET_DOOR — callers add those to
    `forbid_positions` so the flood stops at them.
    """
    h = len(grid)
    w = len(grid[0]) if h else 0
    sx, sy = start
    if not (0 <= sx < w and 0 <= sy < h):
        return None

    forbidden_cells = {(x, y)
                        for room in forbid_rooms
                        for y in range(room.top, room.bottom + 1)
                        for x in range(room.left, room.right + 1)}

    reachable: set = set()
    q = deque([(sx, sy)])
    reachable.add((sx, sy))
    while q:
        cx, cy = q.popleft()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = cx + dx, cy + dy
            if not (0 <= nx < w and 0 <= ny < h):
                continue
            if (nx, ny) in reachable:
                continue
            # Don't flood past a locked/secret door.
            if (nx, ny) in forbid_positions:
                continue
            if grid[ny][nx] not in _FLOOD_PASSABLE:
                continue
            reachable.add((nx, ny))
            q.append((nx, ny))

    candidates = [(x, y) for (x, y) in reachable
                  if (x, y) not in forbidden_cells
                  and grid[y][x] in (TileType.FLOOR, TileType.EMPTY_DECO,
                                       TileType.FLOOR_GRASS)]
    if not candidates:
        return None
    return rng.choice(candidates)
