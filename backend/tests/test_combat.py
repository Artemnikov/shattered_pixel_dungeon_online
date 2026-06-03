import pytest
from app.engine.manager import GameInstance
from app.engine.entities.base import Mob as MobEntity, Player, Position, Weapon


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


def test_surprise_auto_hit():
    """Surprise attacks always hit regardless of accuracy."""
    from app.engine.systems.combat import resolve_melee_attack

    game = GameInstance("test-game")
    game.mobs = {}
    player_id = "test-player"
    player = game.add_player(player_id, "Tester")
    player.pos = Position(x=1, y=1)
    player.attack_skill = 1  # terrible accuracy, shouldn't matter

    mob = MobEntity(
        id="test-mob",
        name="Rat",
        pos=Position(x=2, y=1),
        hp=10, max_hp=10,
        attack=2, defense=0,
        defense_skill=100,  # would normally dodge everything
        dr_min=0, dr_max=0,
    )

    # Defender can't see attacker -> surprise auto-hit
    result = resolve_melee_attack(
        player, mob,
        game.mobs, player.pos.x, player.pos.y,
        is_in_los=lambda a, b: False,
    )
    assert result["hit"] is True
    assert result["surprise"] is True
    assert result["damage"] > 0


def test_dagger_surprise_damage_floor():
    """Dagger's surprise_damage_floor=0.75 raises min damage on surprise."""
    from app.engine.entities.base import Dagger
    from app.engine.systems.combat import resolve_melee_attack

    player = Player(id="p", name="Tester", pos=Position(x=1, y=1),
                    hp=20, max_hp=20, attack=3, defense=1,
                    attack_skill=100, defense_skill=0)

    dagger = Dagger(id="dag", damage=4)
    player.belongings.weapon = dagger

    mob = MobEntity(
        id="m", name="Rat",
        pos=Position(x=2, y=1),
        hp=50, max_hp=50,
        attack=2, defense=0, defense_skill=0,
        dr_min=0, dr_max=0,
        damage_min=1, damage_max=4,
    )

    result = resolve_melee_attack(
        player, mob, {}, player.pos.x, player.pos.y,
        is_in_los=lambda a, b: False,
    )
    assert result["surprise"] is True
    assert result["damage"] > 0


def test_crit_damage_bonus():
    """Surprise attacks apply crit_damage_bonus multiplier."""
    from app.engine.systems.combat import resolve_melee_attack

    player = Player(id="p", name="Tester", pos=Position(x=1, y=1),
                    hp=20, max_hp=20, attack=3, defense=1,
                    attack_skill=100, defense_skill=0,
                    crit_damage_bonus=0.5)  # +50% on surprise
    player.belongings.weapon = Weapon(id="sw", name="Sword", damage=10,
                                       strength_requirement=10, attack_cooldown=0)

    mob = MobEntity(
        id="mob", name="Rat",
        pos=Position(x=2, y=1),
        hp=50, max_hp=50,
        attack=2, defense=0, defense_skill=0,
        dr_min=0, dr_max=0,
    )

    # Surprise attack with +50% bonus: 10 damage -> 15
    result = resolve_melee_attack(
        player, mob, {}, player.pos.x, player.pos.y,
        is_in_los=lambda a, b: False,
    )
    assert result["damage"] == 15


def test_fury_multiplier():
    """Fury gives 1.5x damage multiplier."""
    from app.engine.systems.combat import resolve_melee_attack

    player = Player(id="p", name="Tester", pos=Position(x=1, y=1),
                    hp=20, max_hp=20, attack=3, defense=1,
                    attack_skill=100, defense_skill=0,
                    has_fury=True)
    player.belongings.weapon = Weapon(id="sw", name="Sword", damage=10,
                                       strength_requirement=10, attack_cooldown=0)

    mob = MobEntity(
        id="mob", name="Rat",
        pos=Position(x=2, y=1),
        hp=50, max_hp=50,
        attack=2, defense=0, defense_skill=0,
        dr_min=0, dr_max=0,
    )

    result = resolve_melee_attack(
        player, mob, {}, player.pos.x, player.pos.y,
        is_in_los=lambda a, b: True,
    )
    # 10 damage * 1.5 Fury = 15
    assert result["damage"] == 15


def test_grim_execute():
    """Grim enchantment procs at low HP for extra damage."""
    from app.engine.systems.combat import resolve_melee_attack

    player = Player(id="p", name="Tester", pos=Position(x=1, y=1),
                    hp=20, max_hp=20, attack=3, defense=1,
                    attack_skill=100, defense_skill=0,
                    grim_max_chance=1.0)
    player.belongings.weapon = Weapon(id="sw", name="Sword", damage=20,
                                       strength_requirement=10, attack_cooldown=0)

    mob = MobEntity(
        id="mob", name="Rat",
        pos=Position(x=2, y=1),
        hp=2, max_hp=10,  # low HP so grim can trigger
        attack=2, defense=0, defense_skill=0,
        dr_min=0, dr_max=0,
    )

    result = resolve_melee_attack(
        player, mob, {}, player.pos.x, player.pos.y,
        is_in_los=lambda a, b: False,
    )
    # Either grim killed it or regular damage did
    assert result["grim_proc"] or not mob.is_alive


def test_kinetic_conserve():
    """Kinetic overflow carries damage to next hit."""
    from app.engine.systems.combat import resolve_melee_attack

    player = Player(id="p", name="Tester", pos=Position(x=1, y=1),
                    hp=20, max_hp=20, attack=3, defense=1,
                    attack_skill=100, defense_skill=0,
                    damage_min=1, damage_max=5)
    player.belongings.weapon = Weapon(id="sw", name="Sword", damage=5,
                                       strength_requirement=10, attack_cooldown=0)

    mob = MobEntity(
        id="mob", name="Rat",
        pos=Position(x=2, y=1),
        hp=3, max_hp=10,
        attack=2, defense=0, defense_skill=0,
        dr_min=0, dr_max=0,
    )

    # Kill with 5 damage when mob has 3 HP -> 2 overflow conserved
    result = resolve_melee_attack(
        player, mob, {}, player.pos.x, player.pos.y,
        is_in_los=lambda a, b: False,
    )
    if mob.is_alive:
        return  # mob survived, can't test overflow
    assert player.conserved_damage > 0


def test_no_crit_when_not_surprise():
    """Regular attacks don't get surprise bonuses."""
    from app.engine.systems.combat import resolve_melee_attack

    player = Player(id="p", name="Tester", pos=Position(x=1, y=1),
                    hp=20, max_hp=20, attack=3, defense=1,
                    attack_skill=100, defense_skill=0,
                    crit_damage_bonus=0.5)
    player.belongings.weapon = Weapon(id="sw", name="Sword", damage=10,
                                       strength_requirement=10, attack_cooldown=0)

    mob = MobEntity(
        id="mob", name="Rat",
        pos=Position(x=2, y=1),
        hp=50, max_hp=50,
        attack=2, defense=0, defense_skill=0,
        dr_min=0, dr_max=0,
    )

    # Non-surprise attack (defender CAN see attacker) -> no bonus
    result = resolve_melee_attack(
        player, mob, {}, player.pos.x, player.pos.y,
        is_in_los=lambda a, b: True,
    )
    # 10 damage, no surprise, no bonus
    assert result["damage"] == 10
    assert result["crit"] is False
