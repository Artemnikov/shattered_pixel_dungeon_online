import pytest
from app.engine.manager import GameInstance
from app.engine.entities.base import Position, Weapon


def test_combat_logic():
    game = GameInstance("test-game")
    
    # Clear mobs for controlled test
    game.mobs = {}
    
    # Add a player
    player_id = "test-player"
    player = game.add_player(player_id, "Tester")
    player.pos = Position(x=1, y=1)
    # Ensure guaranteed hit + known damage
    player.attack_skill = 100
    player.belongings.weapon = Weapon(
        id="sword", name="Test Sword", damage=5,
        strength_requirement=10, attack_cooldown=0.0,
    )
    
    # Add a mob with 0 DR and 0 defense skill (guaranteed hit)
    from app.engine.entities.base import Mob as MobEntity
    mob = MobEntity(
        id="test-mob",
        name="Rat",
        pos=Position(x=2, y=1),
        hp=10,
        max_hp=10,
        attack=2,
        defense=0,
        defense_skill=0,
        dr_min=0,
        dr_max=0,
    )
    game.mobs[mob.id] = mob
    
    # Attack the mob by moving into it
    game.move_entity(player_id, 1, 0)
    
    # Player deals 5 damage (Shortsword) - DR is 0, no miss
    assert mob.hp == 5
    assert mob.is_alive == True
    
    # Attack again to kill it
    game.move_entity(player_id, 1, 0)
    assert mob.hp == 0
    assert mob.is_alive == False


def test_player_takes_damage():
    game = GameInstance("test-game")
    game.mobs = {}
    
    # Add a player
    player_id = "test-player"
    player = game.add_player(player_id, "Tester")
    player.pos = Position(x=1, y=1)
    player.hp = 20
    player.max_hp = 20
    # Remove armor so DR is 0
    player.belongings.armor = None
    # Set low defense_skill so mob hits
    player.defense_skill = 0
    
    # Add a mob with known damage
    mob_id = "test-mob"
    from app.engine.entities.base import Mob as MobEntity
    mob = MobEntity(
        id=mob_id,
        name="Rat",
        pos=Position(x=2, y=1),
        hp=10,
        max_hp=10,
        attack=2,
        defense=0,
        attack_skill=100,
        defense_skill=0,
        damage_min=2,
        damage_max=2,
        dr_min=0,
        dr_max=0,
    )
    game.mobs[mob_id] = mob
    
    # Mob attacks player by moving into them
    game.move_entity(mob_id, -1, 0)

    # Mob deals 2 damage, no DR
    assert player.hp == 18


def test_mob_attack_cooldown_decoupled_from_speed():
    """A fast-moving mob must not attack faster than a slow one — attack speed is
    independent of movement `speed`, and is raised to the player's weapon cadence
    so enemies can't land several hits between player swings (regression)."""
    from app.engine.entities.mobs import Rat, Crab

    game = GameInstance("test-game")
    rat = game._spawn_mob_at(Rat, 1, 1)
    crab = game._spawn_mob_at(Crab, 1, 1)

    # Crab moves at speed 2.0, Rat at 1.0 — but they attack at the same rate.
    assert crab.speed > rat.speed
    assert crab.attack_cooldown == rat.attack_cooldown

    # Baseline matches the standard player weapon cadence (3.0s), so a basic mob
    # trades blow-for-blow instead of attacking 3-4× per player swing.
    assert rat.attack_cooldown == 3.0
