import pytest
import time
from app.engine.manager import GameInstance
from app.engine.entities.base import Position, Bow, CharacterClass
from app.engine.dungeon.constants import TileType

def test_ranged_combat_basics():
    game = GameInstance("test-game")
    game.mobs = {}
    # Open room so the shot has clear LOS to the target (the generated floor
    # would put walls between the two cells).
    game.grid = [[TileType.FLOOR for _ in range(12)] for _ in range(12)]
    game._get_or_create_floor(game.depth).rebuild_flags()

    # Add a Huntress player (starts with Bow)
    player_id = "test-huntress"
    player = game.add_player(player_id, "Huntress", CharacterClass.HUNTRESS)
    player.pos = Position(x=5, y=5)
    
    # Ensure weapon is equipped
    assert isinstance(player.equipped_weapon, Bow)
    bow = player.equipped_weapon
    
    # Add a mob within range (Bow range is 6 usually)
    mob_id = "target-mob"
    from app.engine.entities.base import Mob as MobEntity
    mob = MobEntity(
        id=mob_id,
        name="Rat",
        pos=Position(x=5, y=8), # 3 tiles away
        hp=10,
        max_hp=10,
        attack=2,
        defense=0,
        defense_skill=0,  # can't dodge, so the shot deterministically lands
    )
    game.mobs[mob_id] = mob

    # Perform ranged attack
    # Note: perform_ranged_attack is not implemented yet, this is TDD
    initial_hp = mob.hp
    # We expect this method to return the damage dealt, or None if failed
    damage = game.perform_ranged_attack(player_id, bow.id, 5, 8)
    
    assert damage is not None
    assert damage > 0
    assert mob.hp < initial_hp
    
    # Check cooldown
    damage_cooldown = game.perform_ranged_attack(player_id, bow.id, 5, 8)
    assert damage_cooldown is None # Should fail due to cooldown

def test_ranged_combat_out_of_range():
    game = GameInstance("test-game")
    game.mobs = {}
    
    player_id = "test-huntress"
    player = game.add_player(player_id, "Huntress", CharacterClass.HUNTRESS)
    player.pos = Position(x=5, y=5)
    bow = player.equipped_weapon
    
    mob_id = "far-mob"
    from app.engine.entities.base import Mob as MobEntity
    mob = MobEntity(
        id=mob_id,
        name="Rat",
        pos=Position(x=5, y=20), # 15 tiles away, definitely out of range
        hp=10,
        max_hp=10,
        attack=2,
        defense=0
    )
    game.mobs[mob_id] = mob
    
    damage = game.perform_ranged_attack(player_id, bow.id, 5, 20)
    assert damage is None
    assert mob.hp == 10

def test_ranged_combat_los_blocked():
    game = GameInstance("test-game")
    game.mobs = {}
    
    player_id = "test-huntress"
    player = game.add_player(player_id, "Huntress", CharacterClass.HUNTRESS)
    player.pos = Position(x=5, y=5)
    bow = player.equipped_weapon
    
    # Place a wall between player and mob
    game.grid[6][5] = TileType.WALL
    
    mob_id = "hidden-mob"
    from app.engine.entities.base import Mob as MobEntity
    mob = MobEntity(
        id=mob_id,
        name="Rat",
        pos=Position(x=5, y=8),
        hp=10,
        max_hp=10,
        attack=2,
        defense=0
    )
    game.mobs[mob_id] = mob
    
    # Verify LoS is blocked
    assert game._is_in_los(player.pos, mob.pos) == False
    
    damage = game.perform_ranged_attack(player_id, bow.id, 5, 8)
    assert damage is None
    assert mob.hp == 10
