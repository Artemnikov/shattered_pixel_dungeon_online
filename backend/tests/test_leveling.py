from app.engine.manager import GameInstance
from app.engine.entities.base import Mob as MobEntity, Player, Position


def _kill_adjacent_mob(mob_exp):
    """Spawn a 1-HP mob next to a player and have the player kill it in one hit."""
    game = GameInstance("xp-test")
    game.mobs = {}
    pid = "p"
    player = game.add_player(pid, "Tester")
    player.pos = Position(x=1, y=1)
    player.attack = 50  # one-shot
    mob = MobEntity(id="m", name="Rat", pos=Position(x=2, y=1),
                    hp=1, max_hp=1, attack=1, defense=0, exp=mob_exp)
    game.mobs["m"] = mob
    game.move_entity(pid, 1, 0)  # attack into the mob
    return game, player, mob


def test_kill_awards_exp():
    game, player, mob = _kill_adjacent_mob(mob_exp=3)
    assert mob.is_alive is False
    assert player.experience == 3
    assert player.level == 1
    assert not any(e["type"] == "LEVEL_UP" for e in game.events)


def test_kill_that_levels_up_emits_event():
    game, player, mob = _kill_adjacent_mob(mob_exp=10)  # maxExp(1) == 10
    assert mob.is_alive is False
    assert player.level == 2
    assert any(e["type"] == "LEVEL_UP" and e["data"]["player"] == player.id
               for e in game.events)


def _player():
    return Player(
        id="p1",
        name="Tester",
        pos=Position(x=1, y=1),
        hp=10,
        max_hp=10,
        attack=3,
        defense=1,
        faction="player",
    )


def test_max_exp_formula():
    p = _player()
    assert p.level == 1
    assert p.max_exp() == 10  # 5 + 1*5


def test_earn_exp_below_threshold_no_levelup():
    p = _player()
    leveled = p.earn_exp(9)
    assert leveled is False
    assert p.level == 1
    assert p.experience == 9
    assert p.max_hp == 10


def test_earn_exp_levels_up_and_boosts_hp():
    p = _player()
    leveled = p.earn_exp(10)  # exactly maxExp(1)
    assert leveled is True
    assert p.level == 2
    assert p.experience == 0
    assert p.max_hp == 15  # +5 per level
    assert p.hp == 15  # healed the gain


def test_earn_exp_multi_level_in_one_award():
    p = _player()
    # maxExp(1)=10, maxExp(2)=15 -> 25 total spans two levels
    leveled = p.earn_exp(25)
    assert leveled is True
    assert p.level == 3
    assert p.experience == 0
    assert p.max_hp == 20  # +5 twice


def test_earn_exp_caps_at_max_level():
    p = _player()
    p.level = Player.MAX_LEVEL
    leveled = p.earn_exp(1000)
    assert leveled is False
    assert p.level == Player.MAX_LEVEL
