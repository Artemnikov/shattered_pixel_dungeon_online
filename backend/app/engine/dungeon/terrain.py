import random
from collections import deque
from typing import Dict, List, Optional, Set, Tuple

from app.engine.dungeon.constants import TileType, TrapType
from app.engine.dungeon.models import Room, SewersProfile, TrapInfo


class TerrainMixin:
    """Mixin for terrain decoration and trap/key placement."""

    def _cellular_automaton_blob(self, smooth: int) -> List[List[bool]]:
        # Seed at 0.55 so blobs form stably with threshold=5 (majority of 9)
        alive = [[self.rng.random() < 0.55 for _ in range(self.width)] for _ in range(self.height)]
        for _ in range(smooth):
            next_alive = [[False] * self.width for _ in range(self.height)]
            for y in range(self.height):
                for x in range(self.width):
                    count = sum(
                        alive[y + dy][x + dx]
                        for dy in range(-1, 2)
                        for dx in range(-1, 2)
                        if 0 <= y + dy < self.height and 0 <= x + dx < self.width
                    )
                    next_alive[y][x] = count >= 5
            alive = next_alive
        return alive

    def _pick_blob_tiles(
        self,
        candidates: List[Tuple[int, int]],
        mask: List[List[bool]],
        target: int,
    ) -> List[Tuple[int, int]]:
        in_blob = [c for c in candidates if mask[c[1]][c[0]]]
        out_blob = [c for c in candidates if not mask[c[1]][c[0]]]
        self.rng.shuffle(in_blob)
        self.rng.shuffle(out_blob)
        chosen = in_blob[:target]
        if len(chosen) < target:
            chosen += out_blob[: target - len(chosen)]
        return chosen

    def _apply_terrain(
        self,
        profile: SewersProfile,
        traps: Dict[Tuple[int, int], TrapInfo],
        excluded: Set[Tuple[int, int]],
    ):
        trap_positions = set(traps.keys())
        candidates: List[Tuple[int, int]] = []

        for y in range(self.height):
            for x in range(self.width):
                if self.grid[y][x] != TileType.FLOOR:
                    continue
                if (x, y) in excluded or (x, y) in trap_positions:
                    continue
                candidates.append((x, y))

        if not candidates:
            return

        water_target = int(len(candidates) * profile.WATER_RATIO)
        water_mask = self._cellular_automaton_blob(smooth=5)
        for x, y in self._pick_blob_tiles(candidates, water_mask, water_target):
            self.grid[y][x] = TileType.FLOOR_WATER

        remaining = [(x, y) for x, y in candidates if self.grid[y][x] == TileType.FLOOR]
        grass_target = int(len(candidates) * profile.GRASS_RATIO)
        grass_mask = self._cellular_automaton_blob(smooth=4)
        for x, y in self._pick_blob_tiles(remaining, grass_mask, grass_target):
            self.grid[y][x] = TileType.FLOOR_GRASS

        grass_tiles = {TileType.FLOOR_GRASS, TileType.HIGH_GRASS}
        for x, y in candidates:
            if self.grid[y][x] != TileType.FLOOR_GRASS:
                continue
            grass_neighbors = sum(
                1
                for dy in range(-1, 2)
                for dx in range(-1, 2)
                if (dx != 0 or dy != 0)
                and 0 <= y + dy < self.height
                and 0 <= x + dx < self.width
                and self.grid[y + dy][x + dx] in grass_tiles
            )
            if self.rng.random() < grass_neighbors / 12:
                self.grid[y][x] = TileType.HIGH_GRASS

    def _decorate_sewers(self) -> None:
        # Mirrors SPD SewerPainter.decorate: WALL -> WALL_DECO when it has
        # water directly below it (hanging plants above water). Higher chance
        # when the tile above is also a wall (deeper into the mass).
        for y in range(self.height - 1):
            for x in range(self.width):
                if self.grid[y][x] != TileType.WALL:
                    continue
                if self.grid[y + 1][x] != TileType.FLOOR_WATER:
                    continue
                above = self.grid[y - 1][x] if y > 0 else TileType.VOID
                chance = 0.25 if above != TileType.WALL else 0.50
                if self.rng.random() < chance:
                    self.grid[y][x] = TileType.WALL_DECO

        # FLOOR -> EMPTY_DECO scatter, more likely near walls.
        all_wall = {TileType.WALL, TileType.WALL_DECO}
        for y in range(self.height):
            for x in range(self.width):
                if self.grid[y][x] != TileType.FLOOR:
                    continue
                wall_count = sum(
                    1
                    for dy in range(-1, 2)
                    for dx in range(-1, 2)
                    if (dx != 0 or dy != 0)
                    and 0 <= y + dy < self.height
                    and 0 <= x + dx < self.width
                    and self.grid[y + dy][x + dx] in all_wall
                )
                if self.rng.random() < (wall_count ** 2) / 16:
                    self.grid[y][x] = TileType.EMPTY_DECO

    def _spawn_sewers_traps(
        self,
        profile: SewersProfile,
        entrance_room: Room,
        exit_room: Room,
    ) -> Dict[Tuple[int, int], TrapInfo]:
        candidates: List[Tuple[int, int]] = []

        for y in range(self.height):
            for x in range(self.width):
                if self.grid[y][x] != TileType.FLOOR:
                    continue
                if entrance_room.contains(x, y) or exit_room.contains(x, y):
                    continue
                candidates.append((x, y))

        if not candidates:
            return {}

        self.rng.shuffle(candidates)
        trap_count = min(len(candidates), self.rng.randint(profile.TRAPS_MIN, profile.TRAPS_MAX))
        traps: Dict[Tuple[int, int], TrapInfo] = {}

        for x, y in candidates[:trap_count]:
            trap_type = profile.TRAP_TYPES[0] if profile.TRAP_TYPES else TrapType.WORN_DART
            hidden = TrapType.CAN_BE_HIDDEN.get(trap_type, True)
            traps[(x, y)] = TrapInfo(x=x, y=y, trap_type=trap_type, hidden=hidden)
            self.grid[y][x] = TileType.SECRET_TRAP if hidden else TileType.TRAP

        return traps

    def _pick_key_spawn_position(
        self,
        entrance_room: Room,
        exit_room: Room,
        hidden_rooms: List[Room],
        locked_doors: Dict[Tuple[int, int], str],
    ) -> Optional[Tuple[int, int]]:
        hidden_room_set = hidden_rooms
        locked_positions = set(locked_doors.keys())
        reachable: Set[Tuple[int, int]] = set()
        start = entrance_room.center
        q = deque([start])
        reachable.add(start)
        passable = {
            TileType.FLOOR,
            TileType.FLOOR_WATER,
            TileType.FLOOR_GRASS,
            TileType.HIGH_GRASS,
            TileType.EMPTY_DECO,
            TileType.FLOOR_COBBLE,
            TileType.DOOR,
            TileType.STAIRS_UP,
            TileType.STAIRS_DOWN,
            TileType.SECRET_TRAP,
            TileType.TRAP,
            TileType.INACTIVE_TRAP,
        }

        while q:
            cx, cy = q.popleft()
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = cx + dx, cy + dy
                if not self._in_bounds(nx, ny):
                    continue
                if (nx, ny) in reachable:
                    continue
                if self.grid[ny][nx] not in passable:
                    continue
                reachable.add((nx, ny))
                q.append((nx, ny))

        candidates: List[Tuple[int, int]] = []
        for x, y in reachable:
            tile = self.grid[y][x]
            if tile not in (TileType.FLOOR, TileType.FLOOR_WATER, TileType.FLOOR_GRASS,
                            TileType.HIGH_GRASS, TileType.EMPTY_DECO,
                            TileType.SECRET_TRAP, TileType.TRAP, TileType.INACTIVE_TRAP):
                continue
            if entrance_room.contains(x, y) or exit_room.contains(x, y):
                continue
            if any(room.contains(x, y) for room in hidden_room_set):
                continue
            if (x, y) in locked_positions:
                continue
            candidates.append((x, y))

        if not candidates:
            return None

        return self.rng.choice(candidates)
