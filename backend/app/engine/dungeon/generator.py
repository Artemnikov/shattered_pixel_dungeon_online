import random
from collections import deque
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from app.engine.dungeon.constants import RoomKind, TileType, TrapType, TrapVisual  # noqa: F401 — re-exported
from app.engine.dungeon.models import Room, SewersGenerationResult, SewersProfile, TrapInfo  # noqa: F401 — re-exported
from app.engine.dungeon.corridors import CorridorsMixin
from app.engine.dungeon.sewers_generation import SewersGenerationMixin
from app.engine.dungeon.terrain import TerrainMixin


class DungeonGenerator(SewersGenerationMixin, CorridorsMixin, TerrainMixin):
    def __init__(self, width: int, height: int, seed: Optional[int] = None):
        self.width = width
        self.height = height
        self.grid = [[TileType.VOID for _ in range(width)] for _ in range(height)]
        self.rooms: List[Room] = []
        # Per-instance RNG — SPD equivalent of Random.pushGenerator(Dungeon.seedCurDepth()).
        # When seed is None, falls back to a random seed so generation stays varied
        # in contexts that don't thread seeds yet.
        self.seed = seed if seed is not None else random.Random().getrandbits(32)
        self.rng = random.Random(self.seed)

    def generate(
        self, max_rooms: int, min_room_size: int, max_room_size: int
    ) -> Tuple[List[List[int]], List[Room]]:
        self.rooms = []

        max_retries = 10
        for _ in range(max_retries):
            self.grid = [[TileType.VOID for _ in range(self.width)] for _ in range(self.height)]
            self.rooms = []

            for _ in range(max_rooms):
                w = self.rng.randint(min_room_size, max_room_size)
                h = self.rng.randint(min_room_size, max_room_size)
                x = self.rng.randint(1, self.width - w - 1)
                y = self.rng.randint(1, self.height - h - 1)

                new_room = Room(x, y, w, h)

                if any(new_room.intersects(other) for other in self.rooms):
                    continue

                self._create_room(new_room)

                if self.rooms:
                    prev_center = self.rooms[-1].center
                    new_center = new_room.center
                    self._create_tunnel(prev_center, new_center)

                self.rooms.append(new_room)

            if self.is_connected() and len(self.rooms) > 1:
                break

        if self.rooms:
            up_x, up_y = self.rooms[0].center
            down_x, down_y = self.rooms[-1].center
            self.grid[up_y][up_x] = TileType.STAIRS_UP
            self.grid[down_y][down_x] = TileType.STAIRS_DOWN

        return self.grid, self.rooms

    def generate_boss_floor(self) -> Tuple[List[List[int]], List[Room]]:
        self.grid = [[TileType.VOID for _ in range(self.width)] for _ in range(self.height)]
        self.rooms = []

        west_room  = Room(x=3,  y=17, width=7,  height=5)
        boss_room  = Room(x=22, y=14, width=14, height=10)
        north_room = Room(x=26, y=3,  width=7,  height=4)
        south_room = Room(x=26, y=31, width=7,  height=4)
        east_room  = Room(x=50, y=17, width=7,  height=5)

        self._paint_room(boss_room)
        for room in (west_room, north_room, south_room, east_room):
            self._create_room(room)

        self._create_tunnel(west_room.center,  boss_room.center)
        self._create_tunnel(boss_room.center,  east_room.center)
        self._create_tunnel(boss_room.center,  north_room.center)
        self._create_tunnel(boss_room.center,  south_room.center)

        # Water-filled arena (SPD GooBossRoom): a central pool with a 1-tile dry
        # ring inside the walls. Goo heals while standing in it, so the player has
        # to bait it out onto the dry border.
        for y in range(boss_room.y + 1, boss_room.y + boss_room.height - 1):
            for x in range(boss_room.x + 1, boss_room.x + boss_room.width - 1):
                if self.grid[y][x] == TileType.FLOOR:
                    self.grid[y][x] = TileType.FLOOR_WATER

        wx, wy = west_room.center
        ex, ey = east_room.center
        self.grid[wy][wx] = TileType.STAIRS_UP
        self.grid[ey][ex] = TileType.STAIRS_DOWN

        # Seal the exit: the east corridor leaving the arena (both rooms are
        # centred on y=19, so the tunnel carves a door at the arena's right wall)
        # is locked. Only Goo drops the matching key (see handle_boss_death).
        door_x, door_y = boss_room.x + boss_room.width, boss_room.center[1]
        self.grid[door_y][door_x] = TileType.LOCKED_DOOR
        self.boss_locked_doors = {(door_x, door_y): "goo_door"}

        self.rooms = [west_room, boss_room, north_room, south_room, east_room]
        self._save_debug_map(self.grid)
        return self.grid, self.rooms

    def generate_sewers(self, profile: Optional[SewersProfile] = None,
                         use_v2_pipeline: bool = True) -> SewersGenerationResult:
        """Generate a sewers floor.

        Default is the SPD-style Room/Builder/Painter pipeline. Pass
        `use_v2_pipeline=False` to fall back to the legacy monolithic
        flow (kept around as an escape hatch + as a baseline for tests).
        """
        profile = profile or SewersProfile()

        if use_v2_pipeline:
            from app.engine.dungeon.sewers_level import generate_sewers_level
            # Up to 5 attempts with the v2 pipeline before bailing to legacy.
            last_err: Optional[Exception] = None
            for attempt in range(5):
                try:
                    result = generate_sewers_level(
                        self.width, self.height, profile,
                        # Vary the seed slightly per retry so a "bad" seed
                        # doesn't deterministically loop on the same failure.
                        seed=self.seed + attempt,
                    )
                    self._save_debug_map(result.grid)
                    return result
                except RuntimeError as e:
                    last_err = e
            # If v2 keeps failing, fall through to the legacy generator
            # rather than crashing the game session.

        for _ in range(120):
            try:
                result = self._generate_sewers_attempt(profile)
                self._save_debug_map(result.grid)
                return result
            except RuntimeError:
                continue

        raise RuntimeError("Failed to generate Sewers layout after multiple attempts")

    def _save_debug_map(self, grid: List[List[int]]) -> None:
        _CHARS = {
            TileType.VOID:        ' ',
            TileType.WALL:        '#',
            TileType.FLOOR:       '.',
            TileType.DOOR:        '+',
            TileType.STAIRS_UP:   'U',
            TileType.STAIRS_DOWN: 'D',
            TileType.FLOOR_WOOD:  ',',
            TileType.FLOOR_WATER: '~',
            TileType.FLOOR_COBBLE:':',
            TileType.FLOOR_GRASS: '"',
            TileType.LOCKED_DOOR: 'X',
            TileType.WALL_DECO:   'W',
            TileType.EMPTY_DECO:  'e',
            TileType.HIGH_GRASS:  'G',
            TileType.SECRET_DOOR: 'S',
        }
        lines = [''.join(_CHARS.get(tile, '?') for tile in row) for row in grid]
        legend = (
            "Legend: ' '=VOID  #=WALL  W=WALL_DECO  S=SECRET_DOOR  .=FLOOR  +=DOOR  X=LOCKED_DOOR\n"
            "        U=STAIRS_UP  D=STAIRS_DOWN  ,=FLOOR_WOOD  ~=WATER  :=COBBLE  \"=GRASS  G=HIGH_GRASS  e=EMPTY_DECO\n"
        )
        out = Path(__file__).parents[3] / "debug_map.txt"
        try:
            out.write_text(legend + '\n'.join(lines) + '\n')
            print(f"[debug] map saved to {out}")
        except Exception as e:
            print(f"[debug] failed to save map: {e}")

    def is_connected(self) -> bool:
        if not self.rooms:
            return True

        start_x, start_y = self.rooms[0].center
        if self.grid[start_y][start_x] == TileType.WALL:
            return False

        q = deque([(start_x, start_y)])
        visited = {(start_x, start_y)}

        while q:
            cx, cy = q.popleft()
            for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0)):
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < self.width and 0 <= ny < self.height and (nx, ny) not in visited:
                    tile = self.grid[ny][nx]
                    if tile != TileType.WALL and tile != TileType.VOID:
                        visited.add((nx, ny))
                        q.append((nx, ny))

        for room in self.rooms:
            if room.center not in visited:
                return False
        return True

    def _bfs_distances(self, source: int, adjacency: Dict[int, List[int]]) -> Dict[int, int]:
        q = deque([source])
        dist = {source: 0}

        while q:
            node = q.popleft()
            for neigh in adjacency.get(node, []):
                if neigh in dist:
                    continue
                dist[neigh] = dist[node] + 1
                q.append(neigh)

        return dist

    def _center_distance(self, a: Tuple[int, int], b: Tuple[int, int]) -> float:
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    def _in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height


if __name__ == "__main__":
    gen = DungeonGenerator(60, 40)
    result = gen.generate_sewers()
    grid = result.grid
    for row in grid:
        print(
            "".join(
                [
                    "#" if t == TileType.WALL else "." if t in (TileType.FLOOR, TileType.FLOOR_GRASS) else "U" if t == TileType.STAIRS_UP else "D" if t == TileType.STAIRS_DOWN else " "
                    for t in row
                ]
            )
        )
