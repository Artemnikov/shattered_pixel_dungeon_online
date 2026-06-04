"""Field-of-view / line-of-sight tests.

The remake's LOS is a port of Shattered Pixel Dungeon's recursive
shadowcasting (`app/engine/mechanics/shadowcaster.py`). These tests cover the
algorithm directly and through the GameInstance LOS API, including that vision
never penetrates a solid wall (the defect the old Bresenham trace had).
"""

import pytest

from app.engine.manager import GameInstance, FloorState
from app.engine.entities.base import Position, Mob
from app.engine.dungeon.constants import TileType
from app.engine.mechanics import shadowcaster


# --- helpers ---------------------------------------------------------------

def _game_with_grid(grid):
    """Build a GameInstance whose only floor is `grid` (list of rows of tile
    ids), with flags derived from it."""
    # width/height now derive from the installed floor's grid.
    game = GameInstance("test-game")
    floor = FloorState(floor_id=game.depth, grid=grid, rooms=[], mobs={}, items={})
    floor.rebuild_flags()
    game.floors[game.depth] = floor
    return game


def _open_grid(w, h):
    return [[TileType.FLOOR for _ in range(w)] for _ in range(h)]


# --- shadowcaster unit tests ----------------------------------------------

def test_rounding_table_is_circular():
    # The rounding table trims square corners so FOV is a disc; the diagonal
    # extent must never exceed the row index.
    for i in range(1, shadowcaster.MAX_DISTANCE + 1):
        for j in range(1, i + 1):
            assert shadowcaster.ROUNDING[i][j] <= j


def test_open_room_fully_visible_within_radius():
    w = h = 21
    blocking = [False] * (w * h)
    fov = shadowcaster.compute_fov(blocking, w, h, 10, 10, 8)
    # Source visible; a tile straight out at distance 8 visible; distance 9 not.
    assert fov[10 * w + 10]
    assert fov[10 * w + 18]      # (18,10): dx=8
    assert not fov[10 * w + 19]  # (19,10): dx=9 > radius


def test_wall_casts_shadow():
    # Wall directly east of source hides the tile behind it.
    w = h = 21
    blocking = [False] * (w * h)
    blocking[10 * w + 12] = True  # wall at (12,10)
    fov = shadowcaster.compute_fov(blocking, w, h, 10, 10, 8)
    assert fov[10 * w + 11]       # in front of wall: visible
    assert fov[10 * w + 12]       # the wall itself: visible
    assert not fov[10 * w + 13]   # directly behind wall: shadowed


def test_symmetric_in_all_octants():
    w = h = 21
    blocking = [False] * (w * h)
    fov = shadowcaster.compute_fov(blocking, w, h, 10, 10, 8)
    # Mirror a sample of offsets across all 8 octants; an open disc is symmetric.
    for dx, dy in [(8, 0), (0, 8), (5, 5), (3, 7), (7, 3)]:
        vals = {
            fov[(10 + sy) * w + (10 + sx)]
            for sx in (dx, -dx) for sy in (dy, -dy)
        }
        assert len(vals) == 1, f"asymmetric at ({dx},{dy})"


def test_distance_two_fills_corners():
    # At distance 2 the diagonal corner is deliberately filled in.
    w = h = 7
    blocking = [False] * (w * h)
    fov = shadowcaster.compute_fov(blocking, w, h, 3, 3, 2)
    assert fov[(3 + 2) * w + (3 + 2)]  # (5,5): the filled corner


# --- GameInstance LOS API --------------------------------------------------

def test_los_blocked_by_wall():
    grid = _open_grid(10, 10)
    grid[1][1] = TileType.WALL
    game = _game_with_grid(grid)

    p1 = Position(x=0, y=1)
    p2 = Position(x=2, y=1)
    assert game._is_in_los(p1, p2) is False

    grid[1][1] = TileType.FLOOR
    game.floors[game.depth].rebuild_flags()
    game._invalidate_fov_cache()
    assert game._is_in_los(p1, p2) is True


def test_get_visible_tiles_is_circular():
    game = _game_with_grid(_open_grid(20, 20))
    pos = Position(x=10, y=10)
    visible = set(game.get_visible_tiles(pos, radius=2))
    assert (10, 12) in visible      # dy=2 in
    assert (10, 13) not in visible  # dy=3 out


def test_vision_does_not_penetrate_wall():
    """Recursive shadowcasting (unlike the old Bresenham trace) never reveals a
    tile that lies fully behind a solid wall relative to the viewer."""
    # Solid horizontal wall (y=8, x=6..14) with the viewer below it at (10,10).
    grid = _open_grid(21, 21)
    for x in range(6, 15):
        grid[8][x] = TileType.WALL
    game = _game_with_grid(grid)

    viewer = Position(x=10, y=10)
    assert game._is_in_los(viewer, Position(x=10, y=8)) is True   # the wall face
    assert game._is_in_los(viewer, Position(x=10, y=7)) is False  # directly behind
    assert game._is_in_los(viewer, Position(x=10, y=6)) is False  # further behind
    assert game._is_in_los(viewer, Position(x=8, y=7)) is False   # behind, offset


def test_corridor_sightline_matches_shadowcasting():
    """A genuine (unobstructed centre-line) diagonal sightline up a 1-wide
    corridor is visible — matches SPD shadowcasting, where the old Bresenham
    trace wrongly reported it blocked."""
    M = {'#': TileType.WALL, '.': TileType.FLOOR, 'W': TileType.WALL,
         'e': TileType.FLOOR, 'P': TileType.FLOOR}
    layout = [
        "#########",
        "####W####",
        "###..e###",
        "###.#####",
        "###P#####",
        "#########",
    ]
    grid = [[M[c] for c in row] for row in layout]
    game = _game_with_grid(grid)

    player = Position(x=3, y=4)
    # Straight up the corridor: visible.
    assert game._is_in_los(player, Position(x=3, y=3)) is True
    assert game._is_in_los(player, Position(x=3, y=2)) is True
    # (4,2) floor: centre-line (3,4)->(4,2) only grazes the corner, so visible.
    assert game._is_in_los(player, Position(x=4, y=2)) is True
    # (5,2) room interior is NOT reachable without passing through a wall: hidden.
    assert game._is_in_los(player, Position(x=5, y=2)) is False


def test_get_state_filters_mobs_by_los():
    game = _game_with_grid(_open_grid(20, 20))
    game.add_player("p1", "Tester")
    game.players["p1"].pos = Position(x=10, y=10)

    game.floors[game.depth].mobs["m1"] = Mob(
        id="m1", name="Rat1", pos=Position(x=11, y=11),
        hp=10, max_hp=10, attack=1, defense=0, faction="dungeon")
    game.floors[game.depth].mobs["m2"] = Mob(
        id="m2", name="Rat2", pos=Position(x=0, y=0),
        hp=10, max_hp=10, attack=1, defense=0, faction="dungeon")

    state = game.get_state("p1")
    mob_ids = [m["id"] for m in state["mobs"]]
    assert "m1" in mob_ids       # adjacent, visible
    assert "m2" not in mob_ids   # far away, out of FOV


def test_view_distance_zero_is_sightless():
    game = _game_with_grid(_open_grid(20, 20))
    pos = Position(x=10, y=10)
    visible = set(game.get_visible_tiles(pos, radius=0))
    assert visible == {(10, 10)}  # only own tile
