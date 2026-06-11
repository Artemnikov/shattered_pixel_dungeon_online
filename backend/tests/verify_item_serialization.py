import json
from app.engine.entities.base import Player, KindOfWeapon, Item, Wearable

def test_serialization():
    w = KindOfWeapon(id="1", name="Sword", type="weapon", damage=10, range=1, strength_requirement=5)
    p = Player(id="p1", name="Test", type="player", pos={"x":0,"y":0}, hp=10, max_hp=10, attack=1, defense=0, faction="player", inventory=[w])
    
    data = p.dict()
    print(json.dumps(data, indent=2))
    
    if "damage" in data["inventory"][0]:
        print("PASS: damage field is present")
    else:
        print("FAIL: damage field is missing")

if __name__ == "__main__":
    test_serialization()
