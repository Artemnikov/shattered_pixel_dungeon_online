"""Parity tests for SPD LOS/FOV gaps (see docs/spd_line_of_sight.md):

- per-mob view_distance overrides + AI sight-range gating
- per-floor view_distance override (YogDzewa fight)
- Blindness blanks FOV, with the "discoverable" sense-radius fallback
- MindVision potion reveals mobs through walls
- Item heap `seen` first-discovery latch
"""

from app.engine.manager import GameInstance, FloorState
from app.engine.entities.base import Position, Mob, HealthPotion
from app.engine.entities.mobs import Bee, Tengu, Succubus, Eye, Scorpio, RipperDemon, YogDzewa, SoiledFist
from app.engine.dungeon.constants import TileType


def _game_with_grid(grid):
    game = GameInstance("test-game")
    floor = FloorState(floor_id=game.depth, grid=grid, rooms=[], mobs={}, items={})
    floor.rebuild_flags()
    game.floors[game.depth] = floor
    return game


def _open_grid(w, h):
    return [[TileType.FLOOR for _ in range(w)] for _ in range(h)]


# --- 1. mob view_distance overrides ----------------------------------------

def _mob_view_distance(cls):
    return cls(id="m", name="m", pos=Position(x=0, y=0), hp=1, max_hp=1).view_distance


def test_mob_view_distance_overrides():
    assert _mob_view_distance(Bee) == 4
    assert _mob_view_distance(Tengu) == 12
    assert _mob_view_distance(Succubus) == 6
    assert _mob_view_distance(Eye) == 6
    assert _mob_view_distance(Scorpio) == 6
    assert _mob_view_distance(RipperDemon) == 6
    assert _mob_view_distance(YogDzewa) == 12
    assert _mob_view_distance(SoiledFist) == 6


def test_idle_mob_ignores_player_beyond_view_distance():
    game = _game_with_grid(_open_grid(20, 20))
    player = game.add_player("p1", "Tester")
    player.pos = Position(x=10, y=10)

    mob = game._spawn_mob_at(Bee, 10, 16)  # Manhattan dist 6 > Bee view_distance 4
    game.floors[game.depth].mobs[mob.id] = mob
    assert mob.ai_state == "idle"

    for _ in range(50):
        game.update_tick()

    assert mob.ai_state == "idle"


# --- 2. per-floor view_distance override (YogDzewa fight) ------------------

def test_floor_view_distance_override():
    game = _game_with_grid(_open_grid(20, 20))
    player = game.add_player("p1", "Tester")
    player.pos = Position(x=10, y=10)

    assert game._view_distance(player) == 8

    game.floors[game.depth].view_distance = 2
    assert game._view_distance(player) == 2


def test_yog_dzewa_phase_view_distance_helper():
    from app.engine.game.ai_yog_dzewa import _yog_phase_view_distance
    assert _yog_phase_view_distance(1) == 4
    assert _yog_phase_view_distance(2) == 3
    assert _yog_phase_view_distance(3) == 2
    assert _yog_phase_view_distance(4) == 1
    assert _yog_phase_view_distance(5) == 1


# --- 3 & 4. Blindness blanks FOV + discoverable sense-radius fallback ------

def test_blind_player_only_senses_adjacent_cells():
    game = _game_with_grid(_open_grid(20, 20))
    player = game.add_player("p1", "Tester")
    player.pos = Position(x=10, y=10)

    player.add_buff("blindness", duration=10.0)

    visible = set(game.get_visible_tiles(player.pos, radius=game._view_distance(player),
                                          floor_id=player.floor_id, viewer_id=player.id))

    expected = {(x, y) for x in (9, 10, 11) for y in (9, 10, 11)}
    assert visible == expected


def test_sighted_player_sees_further_than_blind():
    game = _game_with_grid(_open_grid(20, 20))
    player = game.add_player("p1", "Tester")
    player.pos = Position(x=10, y=10)

    visible = set(game.get_visible_tiles(player.pos, radius=game._view_distance(player),
                                          floor_id=player.floor_id, viewer_id=player.id))
    assert (10, 5) in visible  # well beyond the 3x3 blind radius


# --- 5. MindVision potion reveals mobs through walls -----------------------

def _walled_off_grid(w, h):
    """Open room with a solid wall column at x=10 splitting it in two."""
    grid = _open_grid(w, h)
    for y in range(h):
        grid[y][10] = TileType.WALL
    return grid


def test_mind_vision_reveals_mob_through_wall():
    game = _game_with_grid(_walled_off_grid(20, 20))
    player = game.add_player("p1", "Tester")
    player.pos = Position(x=5, y=10)

    floor = game.floors[game.depth]
    floor.mobs["m1"] = Mob(id="m1", name="Rat1", pos=Position(x=15, y=10),
                            hp=10, max_hp=10, attack=1, defense=0, faction="dungeon")

    state = game.get_state("p1")
    assert "m1" not in [m["id"] for m in state["mobs"]]

    player.add_buff("mind_vision", duration=20.0)

    state = game.get_state("p1")
    assert "m1" in [m["id"] for m in state["mobs"]]


# --- item heap `seen` latch --------------------------------------------------

def test_item_seen_latch_set_on_fov_entry():
    game = _game_with_grid(_open_grid(20, 20))
    player = game.add_player("p1", "Tester")
    player.pos = Position(x=10, y=10)

    floor = game.floors[game.depth]
    item = HealthPotion(id="item1", pos=Position(x=10, y=10))
    floor.items["item1"] = item
    assert item.seen is False

    game.get_state("p1")
    assert item.seen is True
