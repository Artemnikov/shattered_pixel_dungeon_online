import sys
import os
import time
import uuid

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.engine.manager import GameInstance
from app.engine.entities.base import CharacterClass, KindOfWeapon

def test_attack_rate():
    print("Initializing Game...")
    game = GameInstance("test_game")
    
    # Create player
    player_id = "player1"
    player = game.add_player(player_id, "TestPlayer", CharacterClass.WARRIOR)
    
    # Create a dummy mob right next to player
    mob_id = "target_rat"
    # Find a spot next to player
    px, py = player.pos.x, player.pos.y
    mx, my = px + 1, py
    
    # Ensure it's a valid spot (simple hack, assume floor 1 has space)
    # Actually, let's just force the mob position and grid to be valid for this test
    # We don't want to rely on random gen
    
    # Manually place mob
    from app.engine.entities.base import Mob, Position, Faction
    mob = Mob(
        id=mob_id,
        name="Test Rat",
        pos=Position(x=mx, y=my),
        hp=100,
        max_hp=100,
        attack=0,
        defense=0,
        faction=Faction.DUNGEON,
        attack_cooldown=5.0
    )
    game.mobs[mob_id] = mob
    
    # Ensure player can hit mob (different factions)
    print(f"Player Faction: {player.faction}, Mob Faction: {mob.faction}")
    
    # Test 1: Warrior Sword (Cooldown 3.0s)
    print("\n--- Testing Warrior Shortsword (3.0s cooldown) ---")
    current_weapon = player.equipped_weapon
    print(f"Weapon: {current_weapon.name}, Cooldown: {current_weapon.attack_cooldown}")
    
    # Attack 1: Should hit
    print("Attempting Attack 1 (Time 0.0s)...")
    initial_mob_hp = mob.hp
    game.move_entity(player_id, 1, 0) # Try to move into mob -> Attack
    
    if mob.hp < initial_mob_hp:
        print("Attack 1 Successful! (Expected)")
    else:
        print("Attack 1 Failed! (Unexpected)")
        return False
        
    last_hp = mob.hp
    
    # Attack 2: Immediate follow up (Should fail)
    print("Attempting Attack 2 (Time +0.1s)...")
    time.sleep(0.1)
    game.move_entity(player_id, 1, 0)
    
    if mob.hp == last_hp:
        print("Attack 2 Blocked by Cooldown! (Expected)")
    else:
        print(f"Attack 2 Succeeded! (Unexpected) HP went from {last_hp} to {mob.hp}")
        return False
        
    # Attack 3: After 1.5s (Should fail for Sword)
    print("Attempting Attack 3 (Time +1.6s)...")
    time.sleep(1.5) # Total ~1.6s elapsed
    game.move_entity(player_id, 1, 0)
    
    if mob.hp == last_hp:
        print("Attack 3 Blocked by Cooldown! (Expected - 1.6s < 3.0s)")
    else:
        print(f"Attack 3 Succeeded! (Unexpected) HP went from {last_hp} to {mob.hp}")
        return False
        
    # Attack 4: After 3.1s Total (Should succeed)
    print("Attempting Attack 4 (Time +3.1s)...")
    time.sleep(1.5) # Total ~3.1s elapsed
    game.move_entity(player_id, 1, 0)
    
    if mob.hp < last_hp:
        print("Attack 4 Successful! (Expected - > 3.0s)")
    else:
        print("Attack 4 Failed! (Unexpected)")
        return False
        
    last_hp = mob.hp

    # Test 2: Dagger (Cooldown 1.5s)
    print("\n--- Testing Rogue Dagger (1.5s cooldown) ---")
    dagger = KindOfWeapon(id=str(uuid.uuid4()), name="Dagger", damage=2, range=1, strength_requirement=10, attack_cooldown=1.5)
    player.inventory.append(dagger)
    player.equip_item(dagger.id)
    print(f"Equipped: {player.equipped_weapon.name}, Cooldown: {player.equipped_weapon.attack_cooldown}")
    
    # Reset attack time hack (Simulate time passing or just wait? Let's just rely on real time)
    # We just attacked at T+3.1s. Next available is T+4.6s if we kept sword.
    # But we switched weapon... cooldown is stored on ENTITY last_attack_time.
    # Changing weapon doesn't reset global cooldown usually, but let's see.
    # Our logic: `current_time - entity.last_attack_time < cooldown`
    # entity.last_attack_time was set at T+3.1s.
    # Dagger cooldown is 1.5s.
    # So we should be able to attack at T+3.1 + 1.5 = T+4.6s.
    
    print("Waiting for cooldown reset...")
    time.sleep(2.0)
    
    # Attack 1 with Dagger
    print("Attempting Dagger Attack 1...")
    game.move_entity(player_id, 1, 0)
    if mob.hp < last_hp:
        print("Dagger Attack 1 Successful!")
    else:
        print("Dagger Attack 1 Failed!")
        return False
        
    last_hp = mob.hp
    
    # Attack 2 Immediate (Fail)
    print("Attempting Dagger Attack 2 (Immediate)...")
    time.sleep(0.1)
    game.move_entity(player_id, 1, 0)
    if mob.hp == last_hp:
        print("Dagger Attack 2 Blocked (Expected)")
    else:
        print("Dagger Attack 2 Succeeded (Unexpected)")
        return False
        
    # Attack 3 after 1.6s (Succeed)
    print("Attempting Dagger Attack 3 (After 1.6s)...")
    time.sleep(1.6)
    game.move_entity(player_id, 1, 0)
    if mob.hp < last_hp:
        print("Dagger Attack 3 Successful! (Expected)")
    else:
        print("Dagger Attack 3 Failed! (Unexpected)")
        return False
        
    print("\nAll Rate of Attack Tests Passed!")
    return True

if __name__ == "__main__":
    test_attack_rate()
