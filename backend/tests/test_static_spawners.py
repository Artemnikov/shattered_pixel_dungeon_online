import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.engine.entities.base import Position, Faction, Player
from app.engine.entities.mobs import DemonSpawner, Pylon, RipperDemon, DM300
from app.engine.dungeon.generator import TileType
from app.engine.game.constants import MAP_WIDTH, MAP_HEIGHT
from app.engine.game.floor_state import FloorState
from app.engine.manager import GameInstance


def make_floor(floor_id=15, w=10, h=10):
    grid = [[TileType.FLOOR for _ in range(w)] for _ in range(h)]
    floor = FloorState(floor_id=floor_id, grid=grid, rooms=[], mobs={}, items={}, region="halls")
    floor.rebuild_flags()
    floor.mob_limit = 99  # avoid respawn churn during the test
    return floor


def make_game(floor):
    game = GameInstance("test-static-spawners")
    game.players = {}
    game.floors[floor.floor_id] = floor
    game.depth = floor.floor_id
    return game


# ---------------------------------------------------------------------------
# DemonSpawner
# ---------------------------------------------------------------------------

def test_demon_spawner_spawns_ripper_demon_when_cooldown_elapses():
    floor = make_floor()
    game = make_game(floor)

    spawner = DemonSpawner(id="spawner1", pos=Position(x=5, y=5), faction=Faction.DUNGEON)
    spawner.spawn_cooldown = 1
    floor.mobs[spawner.id] = spawner

    player = game.add_player("p1", "Hero")
    player.floor_id = floor.floor_id
    player.pos = Position(x=0, y=0)

    game.update_tick()

    rippers = [m for m in floor.mobs.values() if isinstance(m, RipperDemon)]
    assert len(rippers) == 1
    ripper = rippers[0]
    assert ripper.ai_state == "hunting"
    # Spawned adjacent (8-dir) to the spawner.
    assert abs(ripper.pos.x - spawner.pos.x) <= 1
    assert abs(ripper.pos.y - spawner.pos.y) <= 1
    assert (ripper.pos.x, ripper.pos.y) != (spawner.pos.x, spawner.pos.y)

    # Cooldown reset to 60 (floor <= 21, no reduction).
    assert spawner.spawn_cooldown == 60
    # Spawner itself never moves.
    assert (spawner.pos.x, spawner.pos.y) == (5, 5)


def test_demon_spawner_cooldown_clamped_when_no_free_neighbours():
    floor = make_floor(w=3, h=3)
    game = make_game(floor)

    spawner = DemonSpawner(id="spawner1", pos=Position(x=1, y=1), faction=Faction.DUNGEON)
    spawner.spawn_cooldown = -25  # already deeply negative
    floor.mobs[spawner.id] = spawner

    # Fill all 8 neighbours with blocking mobs so no candidate cell exists.
    n = 0
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            if dx == 0 and dy == 0:
                continue
            blocker = DemonSpawner(id=f"blk{n}", pos=Position(x=1 + dx, y=1 + dy), faction=Faction.DUNGEON)
            floor.mobs[blocker.id] = blocker
            n += 1

    player = game.add_player("p1", "Hero")
    player.floor_id = floor.floor_id
    player.pos = Position(x=0, y=0)

    game.update_tick()

    # No new RipperDemon spawned (only the 8 blockers + spawner remain).
    rippers = [m for m in floor.mobs.values() if isinstance(m, RipperDemon)]
    assert len(rippers) == 0
    # Clamped to -20 (not further decremented to -21 etc.)
    assert spawner.spawn_cooldown == -20


def test_demon_spawner_floor_22_reduces_cooldown():
    floor = make_floor(floor_id=22)
    game = make_game(floor)

    spawner = DemonSpawner(id="spawner1", pos=Position(x=5, y=5), faction=Faction.DUNGEON)
    spawner.spawn_cooldown = 0
    floor.mobs[spawner.id] = spawner

    player = game.add_player("p1", "Hero")
    player.floor_id = floor.floor_id
    player.pos = Position(x=0, y=0)

    game.update_tick()

    rippers = [m for m in floor.mobs.values() if isinstance(m, RipperDemon)]
    assert len(rippers) == 1
    # cooldown-- (0 -> -1), += 60 (-> 59), -= min(20, (22-21)*6.67)=6 (-> 53)
    assert spawner.spawn_cooldown == 53


# ---------------------------------------------------------------------------
# Pylon
# ---------------------------------------------------------------------------

def test_inactive_pylon_does_nothing_and_is_invulnerable():
    floor = make_floor()
    game = make_game(floor)

    pylon = Pylon(id="pylon1", pos=Position(x=5, y=5), faction=Faction.DUNGEON)
    assert pylon.activated is False
    floor.mobs[pylon.id] = pylon

    player = game.add_player("p1", "Hero")
    player.floor_id = floor.floor_id
    player.pos = Position(x=5, y=4)  # adjacent N -- would be a shock cell if active

    hp_before = player.hp
    for _ in range(5):
        game.update_tick()

    assert player.hp == hp_before  # never shocked while inactive

    taken = pylon.take_damage(30)
    assert taken == 0
    assert pylon.hp == pylon.max_hp


def test_activated_pylon_fires_lightning_at_opposite_shock_cells():
    floor = make_floor()
    game = make_game(floor)

    pylon = Pylon(id="pylon1", pos=Position(x=5, y=5), faction=Faction.DUNGEON)
    pylon.activated = True
    pylon.fire_target_idx = 1  # CIRCLE8[1] = N (0,-1); opposite (idx 5) = S (0, 1)
    pylon.bolt_cooldown = 1
    floor.mobs[pylon.id] = pylon

    player = game.add_player("p1", "Hero")
    player.floor_id = floor.floor_id
    player.pos = Position(x=5, y=4)  # N of pylon -- shock cell idx 1
    player.hp = player.get_total_max_hp()

    game.update_tick()

    assert player.hp < player.get_total_max_hp()
    assert pylon.fire_target_idx == 2
    assert pylon.bolt_cooldown == 1


def test_activated_pylon_takes_damage_with_dr_cap():
    pylon = Pylon(id="pylon1", pos=Position(x=5, y=5), faction=Faction.DUNGEON)
    pylon.activated = True
    taken = pylon.take_damage(30)
    # 14 + (sqrt(8*(30-14)+1)-1)/2 = 14 + (sqrt(129)-1)/2 = 14 + 5 = 19 (int)
    assert taken == 19
    assert pylon.hp == pylon.max_hp - 19


# ---------------------------------------------------------------------------
# DM-300 supercharge mechanic: damage-threshold pylon activation, invulnerability
# while supercharged, and de-supercharge on activated-pylon death.
# ---------------------------------------------------------------------------

def test_dm300_supercharge_triggers_at_two_thirds_hp_and_activates_one_pylon():
    floor = make_floor()
    game = make_game(floor)

    dm300 = DM300(id="dm300", pos=Position(x=5, y=5), faction=Faction.DUNGEON)
    floor.mobs[dm300.id] = dm300

    pylons = []
    for i, (px, py) in enumerate([(1, 1), (8, 1), (1, 8), (8, 8)]):
        p = Pylon(id=f"pylon{i}", pos=Position(x=px, y=py), faction=Faction.DUNGEON)
        floor.mobs[p.id] = p
        pylons.append(p)

    assert all(not p.activated for p in pylons)
    assert dm300.pylons_activated == 0
    assert dm300.supercharged is False

    # threshold = 300/3 * (2 - 0) = 200 -- damage that drops HP to <= 200
    # crosses the first supercharge threshold.
    taken = dm300.take_damage(150)

    assert taken == 150
    assert dm300.hp == 200  # clamped to threshold
    assert dm300.supercharged is True
    assert dm300.pylons_activated == 1
    assert dm300.pending_pylon_activation is True
    assert dm300.is_alive is True


def test_dm300_invulnerable_while_supercharged():
    dm300 = DM300(id="dm300", pos=Position(x=5, y=5), faction=Faction.DUNGEON)
    dm300.supercharged = True
    hp_before = dm300.hp

    taken = dm300.take_damage(50)

    assert taken == 0
    assert dm300.hp == hp_before


def test_pylon_death_desupercharges_dm300_without_chain_activation():
    floor = make_floor()
    game = make_game(floor)

    dm300 = DM300(id="dm300", pos=Position(x=5, y=5), faction=Faction.DUNGEON)
    dm300.supercharged = True
    dm300.pylons_activated = 1
    floor.mobs[dm300.id] = dm300

    pylon_a = Pylon(id="pylon_a", pos=Position(x=1, y=1), faction=Faction.DUNGEON)
    pylon_a.activated = True
    pylon_a.hp = 1

    pylon_b = Pylon(id="pylon_b", pos=Position(x=8, y=8), faction=Faction.DUNGEON)
    pylon_b.activated = False

    floor.mobs[pylon_a.id] = pylon_a
    floor.mobs[pylon_b.id] = pylon_b

    # Kill pylon_a via the bleed-death path, which calls handle_mob_death.
    pylon_a.bleed_turns = 1
    pylon_a.bleed_amount = 5

    player = game.add_player("p1", "Hero")
    player.floor_id = floor.floor_id
    player.pos = Position(x=0, y=0)

    game.update_tick()

    assert pylon_a.is_alive is False
    # No chain-activation of the next pylon (CavesBossLevel.eliminatePylon
    # only calls DM300.loseSupercharge).
    assert pylon_b.activated is False
    # DM300 becomes vulnerable again.
    assert dm300.supercharged is False


def test_dm300_overkill_hit_clamps_to_threshold_instead_of_dying():
    # With pylonsActivated < 2, the supercharge thresholds (200, then 100) are
    # always > 0, so even a massive overkill hit clamps HP to the threshold
    # and supercharges rather than killing DM300 outright.
    dm300 = DM300(id="dm300", pos=Position(x=5, y=5), faction=Faction.DUNGEON)

    taken = dm300.take_damage(1000)

    assert taken == 1000  # take_damage reports the raw amount (matches Entity.take_damage)
    assert dm300.hp == 200  # clamped to the first threshold, not 0
    assert dm300.supercharged is True
    assert dm300.pylons_activated == 1
    assert dm300.is_alive is True


def test_dm300_dies_normally_once_both_pylons_activated():
    # threshold = HT/3 * (2 - pylonsActivated) == 0 once both pylons have
    # been activated -- the "isAlive" override no longer applies and a
    # killing blow behaves like a normal mob death.
    dm300 = DM300(id="dm300", pos=Position(x=5, y=5), faction=Faction.DUNGEON)
    dm300.hp = 50
    dm300.pylons_activated = 2

    dm300.take_damage(50)

    assert dm300.hp == 0
    assert dm300.is_alive is False
