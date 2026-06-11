import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import random

from app.engine.entities.base import Faction
from app.engine.entities.mobs import Wraith, TormentedSpirit, Bee, EbonyMimic
from app.engine.dungeon.generator import TileType
from app.engine.game.constants import RESPAWN_TURNS
from app.engine.game.floor_state import FloorState
from app.engine.manager import GameInstance


def make_floor(floor_id=2, w=10, h=10):
    grid = [[TileType.FLOOR for _ in range(w)] for _ in range(h)]
    floor = FloorState(floor_id=floor_id, grid=grid, rooms=[], mobs={}, items={}, region="prison")
    floor.rebuild_flags()
    floor.mob_limit = 99
    floor.respawn_counter = RESPAWN_TURNS  # force a respawn attempt this tick
    return floor


def make_game(floor):
    game = GameInstance("test-universal-spawns")
    game.players = {}
    game.floors[floor.floor_id] = floor
    game.depth = floor.floor_id
    return game


def trigger_respawn(game, floor, monkeypatch, random_value, choice_index=0):
    """Force the 1% universal-extra branch (and a non-exotic Wraith roll),
    then pick `extras[choice_index]`."""
    calls = {"n": 0}

    def fake_random():
        calls["n"] += 1
        if calls["n"] == 1:
            return random_value
        return 0.5  # second call (TormentedSpirit roll) -> stays Wraith

    monkeypatch.setattr(random, "random", fake_random)

    extras_choice = {"calls": 0}
    real_choice = random.choice

    def fake_choice(seq):
        extras_choice["calls"] += 1
        if extras_choice["calls"] == 1:
            return seq[choice_index]
        return real_choice(seq)

    monkeypatch.setattr(random, "choice", fake_choice)
    game._process_respawns(floor.floor_id, floor, [])


def test_universal_pool_spawns_wraith_with_floor_scaling(monkeypatch):
    floor = make_floor(floor_id=5)
    game = make_game(floor)

    # random.random() < 0.01 -> universal extra branch
    # second random.random() (TormentedSpirit roll) >= 0.01 -> Wraith
    trigger_respawn(game, floor, monkeypatch, random_value=0.005, choice_index=0)

    wraiths = [m for m in floor.mobs.values() if isinstance(m, Wraith) and not isinstance(m, TormentedSpirit)]
    assert len(wraiths) == 1
    w = wraiths[0]
    assert w.floor_level == 5
    assert w.attack_skill == 15        # 10 + 5
    assert w.defense_skill == 75       # 15 * 5
    assert w.damage_min == 3           # 1 + 5//2
    assert w.damage_max == 7           # 2 + 5
    assert w.hp == 1 and w.max_hp == 1


def test_universal_pool_spawns_tormented_spirit_with_scaling(monkeypatch):
    floor = make_floor(floor_id=10)
    game = make_game(floor)

    calls = {"n": 0}

    def fake_random():
        calls["n"] += 1
        # 1st call: enter universal branch (< 0.01)
        # 2nd call: TormentedSpirit roll (< 0.01)
        return 0.0

    monkeypatch.setattr(random, "random", fake_random)
    monkeypatch.setattr(random, "choice", lambda seq: seq[0])

    game._process_respawns(floor.floor_id, floor, [])

    spirits = [m for m in floor.mobs.values() if isinstance(m, TormentedSpirit)]
    assert len(spirits) == 1
    s = spirits[0]
    assert s.floor_level == 10
    expected_attack = 10 + round(1.5 * 10)  # 25
    assert s.attack_skill == expected_attack
    assert s.defense_skill == expected_attack * 5
    assert s.damage_min == 1 + (round(1.5 * 10) // 2)
    assert s.damage_max == 2 + round(1.5 * 10)


def test_universal_pool_spawns_bee_with_scaling(monkeypatch):
    floor = make_floor(floor_id=3)
    game = make_game(floor)

    trigger_respawn(game, floor, monkeypatch, random_value=0.005, choice_index=1)

    bees = [m for m in floor.mobs.values() if isinstance(m, Bee)]
    assert len(bees) == 1
    b = bees[0]
    assert b.floor_level == 3
    expected_max_hp = (2 + 3) * 4  # 20
    assert b.max_hp == expected_max_hp
    assert b.hp == expected_max_hp
    assert b.defense_skill == 9 + 3
    assert b.attack_skill == b.defense_skill
    assert b.damage_min == max(1, expected_max_hp // 10)
    assert b.damage_max == max(1, expected_max_hp // 4)


def test_universal_pool_spawns_ebony_mimic_with_scaling_when_floor_above_1(monkeypatch):
    floor = make_floor(floor_id=4)
    game = make_game(floor)

    trigger_respawn(game, floor, monkeypatch, random_value=0.005, choice_index=2)

    mimics = [m for m in floor.mobs.values() if isinstance(m, EbonyMimic)]
    assert len(mimics) == 1
    m = mimics[0]
    assert m.floor_level == 4
    expected_max_hp = (1 + 4) * 6  # 30
    assert m.max_hp == expected_max_hp
    assert m.hp == expected_max_hp
    assert m.defense_skill == 2 + 4 // 2
    assert m.attack_skill == 6 + 4
    assert m.disguised is False


def test_ebony_mimic_excluded_from_pool_on_floor_1(monkeypatch):
    from app.engine.game.tick import _universal_extra_pool

    monkeypatch.setattr(random, "random", lambda: 0.5)  # non-exotic Wraith roll

    assert EbonyMimic not in _universal_extra_pool(1)
    assert EbonyMimic in _universal_extra_pool(2)


def test_no_universal_spawn_when_above_one_percent_threshold(monkeypatch):
    floor = make_floor(floor_id=5)
    game = make_game(floor)

    monkeypatch.setattr(random, "random", lambda: 0.5)

    game._process_respawns(floor.floor_id, floor, [])

    for mob in floor.mobs.values():
        assert not isinstance(mob, (Wraith, Bee, EbonyMimic))
