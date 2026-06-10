import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import random

from app.engine.entities.base import Faction, Player, Position
from app.engine.entities.buffs import has_buff, get_buff
from app.engine.entities.mobs import (
    BurningFist, SoiledFist, RottingFist, RustedFist, BrightFist, DarkFist,
)
from app.engine.dungeon.generator import TileType
from app.engine.game.floor_state import FloorState
from app.engine.manager import GameInstance


def make_floor(floor_id=15, w=10, h=10):
    grid = [[TileType.FLOOR for _ in range(w)] for _ in range(h)]
    floor = FloorState(floor_id=floor_id, grid=grid, rooms=[], mobs={}, items={}, region="caves")
    floor.rebuild_flags()
    floor.mob_limit = 99
    return floor


def make_game(floor):
    game = GameInstance("test-yog-fists")
    game.players = {}
    game.floors[floor.floor_id] = floor
    game.depth = floor.floor_id
    return game


def make_player(x=5, y=5, defense_skill=0):
    p = Player(id="p1", name="Hero", pos=Position(x=x, y=y), hp=100, max_hp=100,
               attack=10, defense=0, floor_id=15)
    p.defense_skill = defense_skill
    return p


def add_player(game, floor, player):
    game.players[player.id] = player


# ---------------------------------------------------------------------------
# Ranged-vs-melee dispatch
# ---------------------------------------------------------------------------

def test_burning_fist_zaps_at_range_with_los_and_sets_cooldown(monkeypatch):
    floor = make_floor()
    game = make_game(floor)

    fist = BurningFist(id="f1", pos=Position(x=2, y=2), faction=Faction.DUNGEON)
    floor.mobs[fist.id] = fist
    fist.ranged_cooldown = 0

    target = make_player(x=5, y=2, defense_skill=0)
    add_player(game, floor, target)

    # Hit roll: acu (0.9*36) > df (0.1*0) -> hit. Then damage roll uses randint(8,16).
    rand_calls = iter([0.9, 0.1])
    monkeypatch.setattr(random, "random", lambda: next(rand_calls))
    monkeypatch.setattr(random, "randint", lambda a, b: 10)
    monkeypatch.setattr(random, "uniform", lambda a, b: 9.0)

    consumed = game._update_yog_fist(fist, floor, floor.floor_id)

    assert consumed is True
    assert fist.ranged_cooldown == 9.0
    assert target.hp == 90
    assert has_buff(target.buffs, "burning")


def test_burning_fist_melees_when_adjacent_and_on_cooldown(monkeypatch):
    floor = make_floor()
    game = make_game(floor)

    fist = BurningFist(id="f1", pos=Position(x=5, y=5), faction=Faction.DUNGEON)
    floor.mobs[fist.id] = fist
    fist.ranged_cooldown = 5  # on cooldown

    target = make_player(x=6, y=5)  # adjacent
    add_player(game, floor, target)

    monkeypatch.setattr(random, "random", lambda: 0.5)

    consumed = game._update_yog_fist(fist, floor, floor.floor_id)

    # Adjacent + cooldown>0 -> let generic melee/chase AI handle it.
    assert consumed is False
    assert fist.ranged_cooldown == 4  # decremented by one this tick


# ---------------------------------------------------------------------------
# Per-fist zap effects
# ---------------------------------------------------------------------------

def test_soiled_fist_zap_roots_on_hit(monkeypatch):
    floor = make_floor()
    game = make_game(floor)

    fist = SoiledFist(id="f1", pos=Position(x=2, y=2), faction=Faction.DUNGEON)
    floor.mobs[fist.id] = fist
    fist.ranged_cooldown = 0

    target = make_player(x=5, y=2, defense_skill=0)
    add_player(game, floor, target)

    rand_calls = iter([0.9, 0.1])  # hit
    monkeypatch.setattr(random, "random", lambda: next(rand_calls))
    monkeypatch.setattr(random, "uniform", lambda a, b: 9.0)

    assert game._update_yog_fist(fist, floor, floor.floor_id) is True
    assert has_buff(target.buffs, "rooted")
    assert target.hp == 100  # no direct damage


def test_rotting_fist_zap_damage_and_ooze_chance(monkeypatch):
    floor = make_floor()
    game = make_game(floor)

    fist = RottingFist(id="f1", pos=Position(x=2, y=2), faction=Faction.DUNGEON)
    floor.mobs[fist.id] = fist
    fist.ranged_cooldown = 0

    target = make_player(x=5, y=2, defense_skill=0)
    add_player(game, floor, target)

    # random.random() sequence: hit-roll acu, hit-roll df, ooze-chance roll
    rand_calls = iter([0.9, 0.1, 0.0])
    monkeypatch.setattr(random, "random", lambda: next(rand_calls))
    monkeypatch.setattr(random, "randint", lambda a, b: 15)
    monkeypatch.setattr(random, "uniform", lambda a, b: 9.0)

    assert game._update_yog_fist(fist, floor, floor.floor_id) is True
    assert target.hp == 85
    assert has_buff(target.buffs, "ooze")


def test_rusted_fist_zap_applies_cripple_no_damage(monkeypatch):
    floor = make_floor()
    game = make_game(floor)

    fist = RustedFist(id="f1", pos=Position(x=2, y=2), faction=Faction.DUNGEON)
    floor.mobs[fist.id] = fist
    fist.ranged_cooldown = 0

    target = make_player(x=5, y=2, defense_skill=0)
    add_player(game, floor, target)

    rand_calls = iter([0.9, 0.1])  # hit
    monkeypatch.setattr(random, "random", lambda: next(rand_calls))
    monkeypatch.setattr(random, "uniform", lambda a, b: 9.0)

    assert game._update_yog_fist(fist, floor, floor.floor_id) is True
    assert has_buff(target.buffs, "cripple")
    assert target.hp == 100


def test_bright_fist_zap_damages_and_blinds(monkeypatch):
    floor = make_floor()
    game = make_game(floor)

    fist = BrightFist(id="f1", pos=Position(x=2, y=2), faction=Faction.DUNGEON)
    floor.mobs[fist.id] = fist

    target = make_player(x=5, y=2, defense_skill=0)
    add_player(game, floor, target)

    rand_calls = iter([0.9, 0.1])  # hit
    monkeypatch.setattr(random, "random", lambda: next(rand_calls))
    monkeypatch.setattr(random, "randint", lambda a, b: 15)

    # BrightFist always zaps when in LOS, regardless of distance/cooldown.
    assert game._update_yog_fist(fist, floor, floor.floor_id) is True
    assert target.hp == 85
    assert has_buff(target.buffs, "blindness")


def test_dark_fist_zap_damages_and_blinds(monkeypatch):
    floor = make_floor()
    game = make_game(floor)

    fist = DarkFist(id="f1", pos=Position(x=2, y=2), faction=Faction.DUNGEON)
    floor.mobs[fist.id] = fist

    target = make_player(x=5, y=2, defense_skill=0)
    add_player(game, floor, target)

    rand_calls = iter([0.9, 0.1])  # hit
    monkeypatch.setattr(random, "random", lambda: next(rand_calls))
    monkeypatch.setattr(random, "randint", lambda a, b: 12)

    assert game._update_yog_fist(fist, floor, floor.floor_id) is True
    assert target.hp == 88
    assert has_buff(target.buffs, "blindness")


def test_burning_fist_zap_miss(monkeypatch):
    floor = make_floor()
    game = make_game(floor)

    fist = BurningFist(id="f1", pos=Position(x=2, y=2), faction=Faction.DUNGEON)
    floor.mobs[fist.id] = fist
    fist.ranged_cooldown = 0

    target = make_player(x=5, y=2, defense_skill=999)
    add_player(game, floor, target)

    # acu (low) < df (high) -> miss
    rand_calls = iter([0.0, 0.9])
    monkeypatch.setattr(random, "random", lambda: next(rand_calls))
    monkeypatch.setattr(random, "uniform", lambda a, b: 9.0)

    assert game._update_yog_fist(fist, floor, floor.floor_id) is True
    assert target.hp == 100
    assert not has_buff(target.buffs, "burning")
    assert fist.ranged_cooldown == 9.0


# ---------------------------------------------------------------------------
# RustedFist damage deferral / gradual release / death
# ---------------------------------------------------------------------------

def test_rusted_fist_defers_damage_and_releases_gradually(monkeypatch):
    floor = make_floor()
    game = make_game(floor)

    fist = RustedFist(id="f1", pos=Position(x=2, y=2), faction=Faction.DUNGEON)
    floor.mobs[fist.id] = fist

    dealt = fist.take_damage(50)
    assert dealt == 0
    assert fist.hp == 300  # no immediate HP loss
    assert fist.viscosity_stacks == 50

    # No target -> the dispatcher still releases viscosity each tick.
    monkeypatch.setattr(random, "random", lambda: 0.5)
    fist.ranged_cooldown = 0

    game._update_yog_fist(fist, floor, floor.floor_id)
    assert fist.hp == 295  # 50 // 10 == 5 released
    assert fist.viscosity_stacks == 45


def test_rusted_fist_eventually_dies_from_released_viscosity(monkeypatch):
    floor = make_floor()
    game = make_game(floor)

    fist = RustedFist(id="f1", pos=Position(x=2, y=2), faction=Faction.DUNGEON)
    fist.hp = 4
    floor.mobs[fist.id] = fist

    fist.viscosity_stacks = 100  # release = 10 > hp
    monkeypatch.setattr(random, "random", lambda: 0.5)

    game._update_yog_fist(fist, floor, floor.floor_id)

    assert fist.hp == 0
    assert fist.is_alive is False


# ---------------------------------------------------------------------------
# BrightFist/DarkFist teleport at 50% HP
# ---------------------------------------------------------------------------

def test_bright_fist_teleports_at_half_hp(monkeypatch):
    floor = make_floor()
    game = make_game(floor)

    fist = BrightFist(id="f1", pos=Position(x=2, y=2), faction=Faction.DUNGEON)
    floor.mobs[fist.id] = fist

    fist.take_damage(200)  # 300 -> 100, crosses below 150
    assert fist.hp == 150  # clamped to half max_hp
    assert fist.teleport_used is True
    assert fist.pending_teleport is True

    target = make_player(x=5, y=5)
    add_player(game, floor, target)

    monkeypatch.setattr(random, "random", lambda: 0.9)  # subsequent hit-roll, if any
    monkeypatch.setattr(random, "choice", lambda seq: seq[0])

    game._update_yog_fist(fist, floor, floor.floor_id)

    assert fist.pending_teleport is False
    assert (fist.pos.x, fist.pos.y) != (2, 2)
    blindness = get_buff(target.buffs, "blindness")
    assert blindness is not None
    assert blindness.level == 2


def test_dark_fist_teleports_at_half_hp(monkeypatch):
    floor = make_floor()
    game = make_game(floor)

    fist = DarkFist(id="f1", pos=Position(x=2, y=2), faction=Faction.DUNGEON)
    floor.mobs[fist.id] = fist

    fist.take_damage(160)  # 300 -> 140, crosses below 150
    assert fist.hp == 150
    assert fist.teleport_used is True
    assert fist.pending_teleport is True


# ---------------------------------------------------------------------------
# SoiledFist 25% damage reduction
# ---------------------------------------------------------------------------

def test_soiled_fist_takes_reduced_damage():
    fist = SoiledFist(id="f1", pos=Position(x=0, y=0), faction=Faction.DUNGEON)
    dealt = fist.take_damage(100)
    assert dealt == 75
    assert fist.hp == 225
