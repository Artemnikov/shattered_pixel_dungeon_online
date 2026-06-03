import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.engine.entities.base import Player, Position
from app.engine.manager import GameInstance
import uuid


def test_admin_player_takes_no_damage():
    player = Player(
        id="p1", name="Admin", pos=Position(x=0, y=0),
        hp=20, max_hp=20, attack=5, defense=0, faction="player",
        is_admin=True,
    )
    dmg = player.take_damage(5)
    assert dmg == 0
    assert player.hp == 20
    assert player.is_downed == False


def test_normal_player_takes_damage():
    player = Player(
        id="p2", name="Normal", pos=Position(x=0, y=0),
        hp=20, max_hp=20, attack=5, defense=0, faction="player",
        is_admin=False,
    )
    dmg = player.take_damage(5)
    assert dmg == 5
    assert player.hp == 15


def test_add_player_sets_is_admin():
    game = GameInstance("test-admin")
    player_id = str(uuid.uuid4())
    player = game.add_player(player_id, "Admin", is_admin=True)
    assert player.is_admin == True


def test_admin_get_state_shows_all_mobs():
    from app.engine.entities.base import Mob as MobEntity
    game = GameInstance("test-admin-vision")
    player_id = str(uuid.uuid4())
    player = game.add_player(player_id, "Admin", is_admin=True)

    floor = game._get_or_create_floor(player.floor_id)
    mob = MobEntity(
        id=str(uuid.uuid4()), name="FarRat",
        pos=Position(x=0, y=0),
        hp=5, max_hp=5, attack=1, defense=0, faction="dungeon",
    )
    floor.mobs[mob.id] = mob
    player.pos = Position(x=59, y=39)

    state = game.get_state(player_id)
    mob_ids = [m["id"] for m in state["mobs"]]
    assert mob.id in mob_ids, "Admin should see mobs outside normal LOS"


def test_admin_get_state_visible_tiles_is_full_grid():
    game = GameInstance("test-admin-tiles")
    player_id = str(uuid.uuid4())
    player = game.add_player(player_id, "Admin", is_admin=True)
    state = game.get_state(player_id)
    expected_count = game.width * game.height
    assert len(state["visible_tiles"]) == expected_count
