import sys, os, uuid
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.engine.entities.base import Position, Faction, Player, Key
from app.engine.entities.mobs import Goo
from app.engine.dungeon.generator import DungeonGenerator, TileType
from app.engine.game.constants import MAP_WIDTH, MAP_HEIGHT, OOZE_DURATION
from app.engine.game.floor_state import FloorState
from app.engine.manager import GameInstance


def make_goo_floor(seed=1):
    gen = DungeonGenerator(MAP_WIDTH, MAP_HEIGHT, seed=seed)
    grid, rooms = gen.generate_boss_floor()
    floor = FloorState(
        floor_id=5, grid=grid, rooms=rooms, mobs={}, items={}, region="sewers",
        locked_doors=dict(getattr(gen, "boss_locked_doors", {})),
    )
    floor.rebuild_flags()
    return floor, rooms


# ---------------------------------------------------------------------------
# Stats / enrage
# ---------------------------------------------------------------------------

def test_goo_base_stats_match_original():
    goo = Goo(id="g1", pos=Position(x=0, y=0), faction=Faction.DUNGEON)
    assert goo.hp == goo.max_hp == 100
    assert goo.attack_skill == 10
    assert goo.defense_skill == 8
    assert goo.get_damage_min() == 1
    assert goo.get_damage_max() == 8
    assert goo.exp == 10
    assert goo.is_enraged() is False


def test_goo_enrages_at_half_hp():
    goo = Goo(id="g1", pos=Position(x=0, y=0), faction=Faction.DUNGEON)
    goo.hp = 51
    assert goo.is_enraged() is False
    assert goo.get_damage_max() == 8
    assert goo.get_effective_defense_skill() == 8

    goo.hp = 50
    assert goo.is_enraged() is True
    assert goo.get_damage_max() == 12
    assert goo.get_effective_defense_skill() == 12  # 8 * 1.5


# ---------------------------------------------------------------------------
# Ooze on hit
# ---------------------------------------------------------------------------

def test_goo_attack_proc_can_apply_ooze():
    goo = Goo(id="g1", pos=Position(x=0, y=0), faction=Faction.DUNGEON)
    target = Player(id="p1", name="Hero", pos=Position(x=1, y=0), hp=50, max_hp=50, faction=Faction.PLAYER)

    import random
    random.seed(0)
    applied = False
    for _ in range(200):
        target.ooze_amount = 0
        goo.attack_proc(target)
        if target.ooze_amount == OOZE_DURATION:
            applied = True
            break
    assert applied, "attack_proc should eventually apply ooze (~1/3 chance per the original)"


# ---------------------------------------------------------------------------
# Boss floor generation: water arena + locked exit
# ---------------------------------------------------------------------------

def test_boss_floor_has_water_arena_and_locked_door():
    floor, rooms = make_goo_floor()

    water_tiles = sum(
        1 for row in floor.grid for cell in row if cell == TileType.FLOOR_WATER
    )
    assert water_tiles > 0, "Boss arena should contain a water pool (Goo heals there)"

    assert len(floor.locked_doors) == 1
    (dx, dy), key_id = next(iter(floor.locked_doors.items()))
    assert key_id == "goo_door"
    assert floor.grid[dy][dx] == TileType.LOCKED_DOOR
    assert floor.flags.passable[dy][dx] is False, "Locked door must block movement until unlocked"


# ---------------------------------------------------------------------------
# Boss death: key + loot drops, idempotent
# ---------------------------------------------------------------------------

def test_goo_death_drops_key_matching_locked_door():
    floor, rooms = make_goo_floor()
    goo = Goo(id=str(uuid.uuid4()), pos=Position(x=rooms[1].center[0], y=rooms[1].center[1]),
              faction=Faction.DUNGEON)
    floor.mobs[goo.id] = goo

    game = GameInstance("test-goo-death")
    game.handle_mob_death(goo, floor, 5)

    keys = [i for i in floor.items.values() if isinstance(i, Key)]
    assert len(keys) == 1
    assert keys[0].key_id == "goo_door"
    assert keys[0].name == "Worn Key"

    door_key_id = next(iter(floor.locked_doors.values()))
    assert keys[0].key_id == door_key_id


def test_goo_death_is_idempotent_single_key():
    floor, rooms = make_goo_floor()
    goo = Goo(id=str(uuid.uuid4()), pos=Position(x=rooms[1].center[0], y=rooms[1].center[1]),
              faction=Faction.DUNGEON)
    floor.mobs[goo.id] = goo

    game = GameInstance("test-goo-death-2")
    game.handle_mob_death(goo, floor, 5)
    game.handle_mob_death(goo, floor, 5)

    keys = [i for i in floor.items.values() if isinstance(i, Key)]
    assert len(keys) == 1, "Calling the death handler twice must not drop a second key"


def test_key_unlocks_the_boss_door():
    floor, rooms = make_goo_floor()
    (dx, dy), key_id = next(iter(floor.locked_doors.items()))

    game = GameInstance("test-goo-unlock")
    player = Player(id="p1", name="Hero", pos=Position(x=dx - 1, y=dy), hp=50, max_hp=50, faction=Faction.PLAYER)
    player.inventory.append(Key(id="k1", name="Worn Key", pos=Position(x=dx - 1, y=dy), key_id=key_id))

    assert game._try_unlock_locked_door(player, floor, dx, dy) is True
    assert floor.grid[dy][dx] == TileType.DOOR
    assert floor.locked_doors == {}
    assert floor.flags.passable[dy][dx] is True
    assert player.inventory == []


def test_locked_door_blocks_without_matching_key():
    floor, rooms = make_goo_floor()
    (dx, dy), key_id = next(iter(floor.locked_doors.items()))

    game = GameInstance("test-goo-no-key")
    player = Player(id="p1", name="Hero", pos=Position(x=dx - 1, y=dy), hp=50, max_hp=50, faction=Faction.PLAYER)

    assert game._try_unlock_locked_door(player, floor, dx, dy) is False
    assert floor.grid[dy][dx] == TileType.LOCKED_DOOR
    assert (dx, dy) in floor.locked_doors
