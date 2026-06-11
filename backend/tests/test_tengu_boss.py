import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.engine.entities.base import Position, Faction
from app.engine.entities.mobs import Tengu
from app.engine.dungeon.generator import TileType
from app.engine.game.floor_state import FloorState
from app.engine.manager import GameInstance


def make_floor(floor_id=10, w=10, h=10):
    grid = [[TileType.FLOOR for _ in range(w)] for _ in range(h)]
    floor = FloorState(floor_id=floor_id, grid=grid, rooms=[], mobs={}, items={}, region="prison")
    floor.rebuild_flags()
    return floor


def make_game(floor):
    game = GameInstance("test-tengu")
    game.players = {}
    game.depth = floor.floor_id
    game.floors[floor.floor_id] = floor
    return game


def test_tengu_base_stats_match_original():
    tengu = Tengu(id="t1", pos=Position(x=0, y=0), faction=Faction.DUNGEON)
    assert tengu.hp == tengu.max_hp == 200
    assert tengu.attack_skill == 20
    assert tengu.is_enraged() is False
    assert tengu.get_attack_skill() == 20

    tengu.hp = 100
    assert tengu.is_enraged() is True
    assert tengu.get_attack_skill() == 10


def test_tengu_jumps_when_dropping_an_hp_bracket():
    floor = make_floor()
    game = make_game(floor)

    tengu = Tengu(id="t1", pos=Position(x=5, y=5), faction=Faction.DUNGEON)
    floor.mobs[tengu.id] = tengu
    player = game.add_player("p1", "Hero")
    player.pos = Position(x=5, y=4)
    player.floor_id = floor.floor_id

    assert tengu.hp_bracket == 7

    # Drop from 200 -> 170 HP: bracket goes from 7 to 6, should trigger a jump.
    tengu.hp = 170
    consumed = game._update_tengu(tengu, floor, floor.floor_id)

    assert consumed is True
    assert tengu.hp_bracket == 6
    assert (tengu.pos.x, tengu.pos.y) != (5, 5)

    events = [e for e in game.flush_events() if e["type"] == "TENGU_JUMP"]
    assert len(events) == 1
    assert events[0]["data"]["mob"] == tengu.id


def test_tengu_no_jump_without_bracket_drop():
    floor = make_floor()
    game = make_game(floor)

    tengu = Tengu(id="t1", pos=Position(x=5, y=5), faction=Faction.DUNGEON)
    floor.mobs[tengu.id] = tengu
    player = game.add_player("p1", "Hero")
    player.pos = Position(x=8, y=8)
    player.floor_id = floor.floor_id

    # Not enraged, no LOS in range -> no ability, no jump.
    consumed = game._update_tengu(tengu, floor, floor.floor_id)
    assert consumed is False
    assert (tengu.pos.x, tengu.pos.y) == (5, 5)
    assert tengu.hp_bracket == 7


def test_tengu_throws_bomb_when_enraged_and_detonates():
    floor = make_floor()
    game = make_game(floor)

    tengu = Tengu(id="t1", pos=Position(x=5, y=5), faction=Faction.DUNGEON)
    tengu.hp = 100  # enraged (<= 50% HP)
    tengu.hp_bracket = (tengu.hp * 8 - 1) // tengu.max_hp  # already settled into this bracket
    floor.mobs[tengu.id] = tengu
    player = game.add_player("p1", "Hero")
    player.pos = Position(x=5, y=4)
    player.floor_id = floor.floor_id

    # SPD initial cooldown (ability_cooldown_until=2) needs 2 ticks before first ability
    consumed = game._update_tengu(tengu, floor, floor.floor_id)  # tick 1: decrement to 1
    consumed = game._update_tengu(tengu, floor, floor.floor_id)  # tick 2: decrement to 0, fire!
    assert consumed is True
    # SPD BombAbility: bomb placed on a free neighbor of the target closest to Tengu
    # Tengu at (5,5), player at (5,4). Neighbors: (4,3),(5,3),(6,3),(4,4),(6,4),(4,5),(5,5),(6,5)
    # (5,5) is occupied by Tengu, closest free is (4,4),(6,4),(4,5),(6,5) all at dist 1
    assert tengu.bomb_timer == 60
    assert tengu.bomb_x != -1 and tengu.bomb_y != -1
    assert not (tengu.bomb_x == 5 and tengu.bomb_y == 5)  # not on Tengu
    assert abs(tengu.bomb_x - 5) <= 1 and abs(tengu.bomb_y - 4) <= 1  # adjacent to player

    events = game.flush_events()
    assert any(e["type"] == "TENGU_BOMB" for e in events)

    # Tick until detonation; the bomb should deal AoE damage to the player.
    hp_before = player.hp
    for _ in range(59):
        game._update_tengu(tengu, floor, floor.floor_id)
        game.flush_events()

    consumed = game._update_tengu(tengu, floor, floor.floor_id)
    assert consumed is True
    assert tengu.bomb_timer == 0
    assert tengu.bomb_x == -1 and tengu.bomb_y == -1

    events = game.flush_events()
    assert any(e["type"] == "TENGU_BLAST" for e in events)
    assert player.hp < hp_before
