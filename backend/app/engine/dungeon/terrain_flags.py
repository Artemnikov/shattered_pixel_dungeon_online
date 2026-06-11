"""Per-tile terrain flag bitmask and derived bool-map builder.

Mirrors SPD's `Terrain.flags[]` and `Level.buildFlagMaps()`. Gameplay systems
(LOS, pathfinding, AI, placement) should consult the derived bool arrays on a
Floor instead of scanning hardcoded tile-ID sets — matches how SPD separates
terrain identity (tile ID) from terrain behaviour (flag bits).
"""

from typing import List, Tuple

from app.engine.dungeon.constants import TileType


# --- Flag bits. Values mirror SPD Terrain.java:72-79. -----------------------
PASSABLE = 0x01
LOS_BLOCKING = 0x02
FLAMABLE = 0x04
SECRET = 0x08
SOLID = 0x10
AVOID = 0x20
LIQUID = 0x40
PIT = 0x80


# --- Per-tile flag table. Mirrors SPD Terrain.java:81-127 ------------------
#
# DOOR is flagged as both PASSABLE (SPD treats walking into a closed door as
# triggering the open action) AND LOS_BLOCKING + SOLID (closed doors block
# vision and physics). Open-state is tracked separately in floor.open_doors,
# so LOS/pathfinding callers must consult both the flag and the open-door map.
TILE_FLAGS = {
    # VOID is "outside the play area" in the remake, not SPD's CHASM. Mark it
    # solid + LOS-blocking so pathfinding can't escape the map and vision
    # doesn't tunnel through un-painted regions.
    TileType.VOID:         SOLID | LOS_BLOCKING,
    TileType.WALL:         LOS_BLOCKING | SOLID,
    TileType.FLOOR:        PASSABLE,
    TileType.DOOR:         PASSABLE | LOS_BLOCKING | FLAMABLE | SOLID,
    TileType.STAIRS_UP:    PASSABLE,
    TileType.STAIRS_DOWN:  PASSABLE,
    TileType.FLOOR_WOOD:   PASSABLE | FLAMABLE,
    TileType.FLOOR_WATER:  PASSABLE | LIQUID,
    TileType.FLOOR_COBBLE: PASSABLE,
    TileType.FLOOR_GRASS:  PASSABLE | FLAMABLE,
    TileType.LOCKED_DOOR:  LOS_BLOCKING | SOLID,
    TileType.WALL_DECO:    LOS_BLOCKING | SOLID,
    TileType.EMPTY_DECO:   PASSABLE,
    TileType.HIGH_GRASS:   PASSABLE | LOS_BLOCKING | FLAMABLE,
    TileType.FURROWED_GRASS: PASSABLE | LOS_BLOCKING | FLAMABLE,
    TileType.SECRET_DOOR:  LOS_BLOCKING | SOLID | SECRET,
    TileType.SECRET_TRAP:  PASSABLE | SECRET,
    TileType.TRAP:         PASSABLE,
    TileType.INACTIVE_TRAP: PASSABLE,
    TileType.OPEN_DOOR:    PASSABLE,
}


def flags_of(tile: int) -> int:
    """Look up the flag bitmask for a tile ID. Unknown tiles default to SOLID."""
    return TILE_FLAGS.get(tile, SOLID | LOS_BLOCKING)


# --- FloorFlagMaps: the pre-derived bool arrays game logic consults. -------
#
# Stored per-floor and rebuilt on generation or when a tile changes (e.g. a
# secret door becomes revealed). Indexed 2D like grid[y][x] to keep call
# sites readable.
class FloorFlagMaps:
    __slots__ = (
        "passable", "los_blocking", "flamable", "secret",
        "solid", "avoid", "liquid", "pit",
        "open_space", "discoverable",
    )

    def __init__(self, width: int, height: int):
        self.passable     = [[False] * width for _ in range(height)]
        self.los_blocking = [[False] * width for _ in range(height)]
        self.flamable     = [[False] * width for _ in range(height)]
        self.secret       = [[False] * width for _ in range(height)]
        self.solid        = [[False] * width for _ in range(height)]
        self.avoid        = [[False] * width for _ in range(height)]
        self.liquid       = [[False] * width for _ in range(height)]
        self.pit          = [[False] * width for _ in range(height)]
        # open_space: cell is non-solid AND has a corner where the cardinal
        # pair AND adjacent diagonal are all non-solid. Large mobs need it.
        self.open_space   = [[False] * width for _ in range(height)]
        # discoverable: any cell whose 3x3 neighbourhood contains a non-wall
        # tile. Used to skip deep wall interiors from FOV/minimap passes.
        self.discoverable = [[False] * width for _ in range(height)]


# 8-neighbourhood offsets in clockwise order starting from N (SPD CIRCLE8).
# Odd indices are cardinals, even are diagonals.
_CIRCLE8: Tuple[Tuple[int, int], ...] = (
    ( 0, -1), ( 1, -1), ( 1,  0), ( 1,  1),
    ( 0,  1), (-1,  1), (-1,  0), (-1, -1),
)


def build_flag_maps(grid: List[List[int]]) -> FloorFlagMaps:
    """Derive all bool arrays from the grid's raw tile IDs.

    Mirrors SPD Level.buildFlagMaps() + cleanWalls(). Call once after the
    painter finishes writing the grid, and again whenever a tile mutates.
    """
    height = len(grid)
    width = len(grid[0]) if height > 0 else 0
    maps = FloorFlagMaps(width, height)

    # Pass 1: raw flags from the tile table.
    for y in range(height):
        row = grid[y]
        for x in range(width):
            f = flags_of(row[x])
            maps.passable[y][x]     = bool(f & PASSABLE)
            maps.los_blocking[y][x] = bool(f & LOS_BLOCKING)
            maps.flamable[y][x]     = bool(f & FLAMABLE)
            maps.secret[y][x]       = bool(f & SECRET)
            maps.solid[y][x]        = bool(f & SOLID)
            maps.avoid[y][x]        = bool(f & AVOID)
            maps.liquid[y][x]       = bool(f & LIQUID)
            maps.pit[y][x]          = bool(f & PIT)

    # Pass 2: force the map border to be impassable/solid/LOS-blocking so
    # nothing ever pathfinds off the grid, regardless of what generation did.
    if width > 0 and height > 0:
        for x in range(width):
            for y in (0, height - 1):
                maps.passable[y][x] = False
                maps.solid[y][x] = True
                maps.los_blocking[y][x] = True
                maps.avoid[y][x] = False
        for y in range(height):
            for x in (0, width - 1):
                maps.passable[y][x] = False
                maps.solid[y][x] = True
                maps.los_blocking[y][x] = True
                maps.avoid[y][x] = False

    # Pass 3: open_space — cell is non-solid AND has a 3-cell L (cardinal +
    # adjacent diagonal + the next cardinal) where all three are non-solid.
    # Matches SPD Level.java:861-877.
    solid = maps.solid
    for y in range(height):
        for x in range(width):
            if solid[y][x]:
                continue
            # Walk the 8 neighbourhood at odd indices (cardinals) and check
            # each cardinal + one adjacent diagonal + the next cardinal.
            for j in range(1, 8, 2):
                dcx, dcy = _CIRCLE8[j]
                cx, cy = x + dcx, y + dcy
                if not (0 <= cx < width and 0 <= cy < height) or solid[cy][cx]:
                    continue
                # The (j+1) diagonal and (j+2) cardinal positions (mod 8).
                dax, day = _CIRCLE8[(j + 1) % 8]
                dbx, dby = _CIRCLE8[(j + 2) % 8]
                ax, ay = x + dax, y + day
                bx, by = x + dbx, y + dby
                if not (0 <= ax < width and 0 <= ay < height):
                    continue
                if not (0 <= bx < width and 0 <= by < height):
                    continue
                if not solid[ay][ax] and not solid[by][bx]:
                    maps.open_space[y][x] = True
                    break

    # Pass 4: discoverable. Any cell with at least one 3x3 neighbour that is
    # not a wall tile is potentially revealable (SPD Level.cleanWalls).
    for y in range(height):
        for x in range(width):
            found = False
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    nx, ny = x + dx, y + dy
                    if not (0 <= nx < width and 0 <= ny < height):
                        continue
                    tile = grid[ny][nx]
                    if tile != TileType.WALL and tile != TileType.WALL_DECO:
                        found = True
                        break
                if found:
                    break
            maps.discoverable[y][x] = found

    return maps
