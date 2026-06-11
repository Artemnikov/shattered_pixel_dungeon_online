
import sys
import os
import uuid

# Add backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.engine.manager import GameInstance, CharacterClass
from app.engine.entities.base import Position, Bow, Mob, Faction

def test_audio_events():
    print("Setting up GameInstance...")
    game = GameInstance("test_game")
    
    # Create Player
    player = game.add_player("player-1", "Hero", CharacterClass.WARRIOR)
    game.players["player-1"].strength = 20 # strong boi for testing
    
    # Create Monster
    # Find a floor tile to spawn
    spawn_pos = None
    for y in range(game.height):
        for x in range(game.width):
            if game.grid[y][x] == 2: # Floor
                spawn_pos = Position(x=x, y=y)
                break
        if spawn_pos: break
        
    player.pos = spawn_pos
    
    # Spawn monster next to player
    mob_id = "mob-1"
    
    # I'll just rely on game.mobs dict injection for simplicity or use a valid tile
    mob_pos = Position(x=spawn_pos.x + 1, y=spawn_pos.y)
    
    # Mock Mob
    mob = Mob(
        id=mob_id,
        name="Test Rat",
        pos=mob_pos,
        hp=50,
        max_hp=50,
        attack=2,
        defense=0,
        attack_cooldown=0.0,
        faction=Faction.DUNGEON
    )
    game.mobs[mob_id] = mob
    
    print("\n--- Testing Melee Hit Sound (Sword) ---")
    game.move_entity(player.id, 1, 0) # Move towards mob -> Attack
    
    events = game.flush_events()
    sound_events = [e for e in events if e['type'] == 'PLAY_SOUND']
    print("Events:", sound_events)
    
    hit_slash_present = any(e['data']['sound'] == 'HIT_SLASH' for e in sound_events)
    if hit_slash_present:
        print("PASS: HIT_SLASH event emitted")
    else:
        print("FAIL: HIT_SLASH event NOT emitted")
        
    print("\n--- Testing Ranged Hit Sound (Bow) ---")
    # Equip Bow
    bow = Bow(id="bow-1", name="Test Bow", pos=Position(x=0,y=0), damage=5, strength_requirement=10, attack_cooldown=0)
    player.belongings.weapon = bow
    
    # Back off separate
    game.mobs[mob_id].pos.x = player.pos.x + 2 
    
    game.perform_ranged_attack(player.id, bow.id, game.mobs[mob_id].pos.x, game.mobs[mob_id].pos.y)
    
    events = game.flush_events()
    sound_events = [e for e in events if e['type'] == 'PLAY_SOUND']
    print("Events:", sound_events)
    
    hit_arrow_present = any(e['data']['sound'] == 'HIT_ARROW' for e in sound_events)
    if hit_arrow_present:
        print("PASS: HIT_ARROW event emitted")
    else:
        print("FAIL: HIT_ARROW event NOT emitted")

    print("\n--- Testing Ranged Hit Sound (Magic Staff) ---")
    # Equip Staff
    from app.engine.entities.base import Staff
    staff = Staff(id="staff-1", name="Test Staff", pos=Position(x=0,y=0), damage=2, magic_damage=5, strength_requirement=10, attack_cooldown=0, charges=10)
    player.belongings.weapon = staff
    
    # Ensure mob is alive/reset
    game.mobs[mob_id].hp = 50
    game.mobs[mob_id].is_alive = True
    
    game.perform_ranged_attack(player.id, staff.id, game.mobs[mob_id].pos.x, game.mobs[mob_id].pos.y)
    
    events = game.flush_events()
    sound_events = [e for e in events if e['type'] == 'PLAY_SOUND']
    print("Events:", sound_events)
    
    hit_magic_present = any(e['data']['sound'] == 'HIT_MAGIC' for e in sound_events)
    if hit_magic_present:
        print("PASS: HIT_MAGIC event emitted")
    else:
        print("FAIL: HIT_MAGIC event NOT emitted")

    print("\n--- Testing Player Taking Damage & Low Health Warn ---")
    # Monster attacks Player
    # Force damage
    print(f"Player HP before: {player.hp}/{player.max_hp}")
    # Reduce player HP to triggering level manually first to test warning
    player.hp = 3 # 3/10 is <= 30%
    
    # Monster attacks player
    game.move_entity(mob_id, -1, 0) # Move mob towards player is trickier as I need to use move_entity on mob
    # Actually manager.move_entity handles logic. 
    # Mob at x+2, Player at x. 
    # Move mob to x+1 (where it was?) No, player didn't move. Player at x, mob at x+2.
    # Move mob to x+1.
    game.mobs[mob_id].pos = Position(x=player.pos.x + 1, y=player.pos.y)
    game.move_entity(mob_id, -1, 0) # Try to move onto player -> ATTACK
    
    events = game.flush_events()
    sound_events = [e for e in events if e['type'] == 'PLAY_SOUND']
    print("Events:", sound_events)
    
    hit_body_present = any(e['data']['sound'] == 'HIT_BODY' for e in sound_events)
    warn_present = any(e['data']['sound'] == 'HEALTH_WARN' for e in sound_events)
    
    if hit_body_present:
        print("PASS: HIT_BODY event emitted")
    else:
        print("FAIL: HIT_BODY event NOT emitted")
        
    if warn_present:
        print("PASS: HEALTH_WARN event emitted")
    else:
        print("FAIL: HEALTH_WARN event NOT emitted")

if __name__ == "__main__":
    test_audio_events()
