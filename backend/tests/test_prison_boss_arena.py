import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.engine.entities.base import Position
from app.engine.entities.mobs import Tengu
from app.engine.dungeon.generator import TileType
from app.engine.dungeon.spd_levelgen import prison_boss_layout as layout
from app.engine.manager import GameInstance


def make_game():
    game = GameInstance("test-prison-boss")
    game.players = {}
    floor = game.generate_floor(10)
    return game, floor


def test_start_to_fight_start_spawns_tengu_and_locks_door():
    game, floor = make_game()
    assert floor.tengu_state == "START"

    player = game.add_player("p1", "Hero")
    player.floor_id = 10
    player.pos = Position(x=layout.TENGU_CELL_CENTER.x, y=layout.TENGU_CELL.top + 2)

    game._update_prison_boss(floor, 10)

    assert floor.tengu_state == "FIGHT_START"
    door = layout.TENGU_CELL_DOOR
    assert floor.grid[door.y][door.x] == TileType.LOCKED_DOOR

    tengus = [m for m in floor.mobs.values() if isinstance(m, Tengu)]
    assert len(tengus) == 1
    assert tengus[0].fight_started is True

    events = [e["type"] for e in game.flush_events()]
    assert "TENGU_FIGHT_STARTED" in events


def test_fight_start_to_pause_rebuilds_map_and_removes_tengu():
    game, floor = make_game()
    player = game.add_player("p1", "Hero")
    player.floor_id = 10
    player.pos = Position(x=layout.TENGU_CELL_CENTER.x, y=layout.TENGU_CELL.top + 2)

    game._update_prison_boss(floor, 10)
    assert floor.tengu_state == "FIGHT_START"
    version_before = floor.map_version

    tengu = next(m for m in floor.mobs.values() if isinstance(m, Tengu))
    tengu.hp = tengu.max_hp // 2  # is_enraged() == True

    game._update_prison_boss(floor, 10)

    assert floor.tengu_state == "FIGHT_PAUSE"
    assert floor.map_version == version_before + 1
    assert not any(isinstance(m, Tengu) for m in floor.mobs.values())
    assert floor.generation_meta["tengu_pending"].id == tengu.id


def test_pause_to_arena_rebuilds_map_and_restores_tengu():
    game, floor = make_game()
    player = game.add_player("p1", "Hero")
    player.floor_id = 10
    player.pos = Position(x=layout.TENGU_CELL_CENTER.x, y=layout.TENGU_CELL.top + 2)

    game._update_prison_boss(floor, 10)  # -> FIGHT_START
    tengu = next(m for m in floor.mobs.values() if isinstance(m, Tengu))
    tengu.hp = tengu.max_hp // 2
    game._update_prison_boss(floor, 10)  # -> FIGHT_PAUSE
    version_before = floor.map_version

    player.pos = Position(x=layout.START_HALLWAY.left + 2, y=layout.START_HALLWAY.top)
    game._update_prison_boss(floor, 10)  # -> FIGHT_ARENA

    assert floor.tengu_state == "FIGHT_ARENA"
    assert floor.map_version == version_before + 1
    tengus = [m for m in floor.mobs.values() if isinstance(m, Tengu)]
    assert len(tengus) == 1
    assert tengus[0].id == tengu.id
    expected_x = layout.ARENA.left + layout.ARENA.width() // 2
    expected_y = layout.ARENA.top + 2
    assert (tengus[0].pos.x, tengus[0].pos.y) == (expected_x, expected_y)


def test_arena_to_won_on_tengu_death():
    game, floor = make_game()
    player = game.add_player("p1", "Hero")
    player.floor_id = 10
    player.pos = Position(x=layout.TENGU_CELL_CENTER.x, y=layout.TENGU_CELL.top + 2)

    game._update_prison_boss(floor, 10)  # -> FIGHT_START
    tengu = next(m for m in floor.mobs.values() if isinstance(m, Tengu))
    tengu.hp = tengu.max_hp // 2
    game._update_prison_boss(floor, 10)  # -> FIGHT_PAUSE
    player.pos = Position(x=layout.START_HALLWAY.left + 2, y=layout.START_HALLWAY.top)
    game._update_prison_boss(floor, 10)  # -> FIGHT_ARENA
    version_before = floor.map_version

    del floor.mobs[tengu.id]  # simulate Tengu's death/removal

    game._update_prison_boss(floor, 10)  # -> WON

    assert floor.tengu_state == "WON"
    assert floor.map_version == version_before + 1
    assert (player.pos.x, player.pos.y) == (layout.TENGU_CELL.left + 4, layout.TENGU_CELL.top + 2)
    # endMap chasm cells should now be present somewhere on the floor
    assert any(TileType.STAIRS_DOWN in row for row in floor.grid)
