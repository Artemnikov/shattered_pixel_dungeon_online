import pytest
import uuid
from app.engine.manager import GameInstance
from app.engine.entities.base import Faction, Position

def test_faction_combat_restrictions():
    game = GameInstance("test_game")
    
    # Add two players (same faction)
    p1_id = "p1"
    p2_id = "p2"
    game.add_player(p1_id, "Player 1")
    game.add_player(p2_id, "Player 2")
    
    p1 = game.players[p1_id]
    p2 = game.players[p2_id]
    
    # Place them next to each other
    p1.pos = Position(x=1, y=1)
    p2.pos = Position(x=2, y=1)
    
    # Ensure they are on floor tiles for movement/combat
    game.grid[1][1] = 1 # Floor
    game.grid[1][2] = 1 # Floor
    
    initial_p2_hp = p2.hp
    
    # p1 tries to "move" onto p2 (should trigger combat check)
    game.move_entity(p1_id, 1, 0)
    
    # They are in the same faction, so p2 should NOT take damage
    assert p2.hp == initial_p2_hp, "Players should not damage each other"
    
    # Move p2 away so it doesn't interfere with mob targeting
    p2.pos = Position(x=5, y=5)
    # Manually move p1 so we know exact position
    p1.pos = Position(x=2, y=1)
    game.grid[1][3] = 1 # Floor at x=3, y=1
    
    # Add a mob (different faction) — orthogonally adjacent to p1 at (2,1)
    mob_id = "mob1"
    from app.engine.entities.base import Mob as MobEntity
    game.mobs[mob_id] = MobEntity(
        id=mob_id,
        name="Rat",
        pos=Position(x=3, y=1),
        hp=10,
        max_hp=10,
        attack=2,
        defense=0,
        attack_skill=100,
        defense_skill=0,
        dr_min=0,
        dr_max=0,
        damage_min=20,
        damage_max=20,
        faction=Faction.DUNGEON
    )
    mob = game.mobs[mob_id]
    p1.attack_skill = 100  # guarantee hits
    
    # p1 attacks mob (p1 at (2,1), mob at (3,1) — adjacent)
    game.move_entity(p1_id, 1, 0)
    
    # Different factions, mob SHOULD take damage
    assert mob.hp < 10, "Player should be able to attack mob"
    
    # Mob attacks player
    initial_p1_hp = p1.hp
    game.move_entity(mob_id, -1, 0)
    assert p1.hp < initial_p1_hp, "Mob should be able to attack player"

def test_mob_vs_mob_no_damage():
    game = GameInstance("test_game")
    
    mob1_id = "mob1"
    mob2_id = "mob2"
    from app.engine.entities.base import Mob as MobEntity
    
    game.mobs[mob1_id] = MobEntity(
        id=mob1_id,
        name="Rat 1",
        pos=Position(x=1, y=1),
        hp=10,
        max_hp=10,
        attack=2,
        defense=0,
        faction=Faction.DUNGEON
    )
    game.mobs[mob2_id] = MobEntity(
        id=mob2_id,
        name="Rat 2",
        pos=Position(x=2, y=1),
        hp=10,
        max_hp=10,
        attack=2,
        defense=0,
        faction=Faction.DUNGEON
    )
    game.grid[1][1] = 1
    game.grid[1][2] = 1
    
    mob2 = game.mobs[mob2_id]
    initial_mob2_hp = mob2.hp
    
    # Mob 1 tries to attack Mob 2
    game.move_entity(mob1_id, 1, 0)
    
    assert mob2.hp == initial_mob2_hp, "Mobs of the same faction should not damage each other"
