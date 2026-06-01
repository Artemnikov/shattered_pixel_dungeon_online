from pydantic import BaseModel
from typing import Optional, List, Dict, Tuple, Union

class EntityType:
    PLAYER = "player"
    MOB = "mob"
    BOSS = "boss"
    ITEM = "item"
    POTION = "potion"

class Faction:
    PLAYER = "player"
    DUNGEON = "dungeon"

class Position(BaseModel):
    x: int
    y: int

class Entity(BaseModel):
    id: str
    type: str
    name: str
    pos: Position
    hp: int
    max_hp: int
    attack: int
    defense: int
    speed: float = 1.0
    is_alive: bool = True
    faction: str
    last_attack_time: float = 0.0
    attack_cooldown: float = 1.0 # Default cooldown


    def move(self, dx: int, dy: int):
        self.pos.x += dx
        self.pos.y += dy

    def take_damage(self, amount: int):
        dmg = max(0, amount - self.defense)
        self.hp -= dmg
        if self.hp <= 0:
            self.hp = 0
            self.is_alive = False
        return dmg

class Item(BaseModel):
    id: str
    name: str
    type: str # "weapon", "wearable", "potion"
    pos: Optional[Position] = None


class Key(Item):
    type: str = "key"
    key_id: str

class Weapon(Item):
    type: str = "weapon"
    damage: int
    range: int
    enchantment: Optional[str] = None
    strength_requirement: int
    attack_cooldown: float = 1.0
    projectile_type: Optional[str] = None


class Wearable(Item):
    type: str = "wearable"
    strength_requirement: int
    health_boost: int
    enchantment: Optional[str] = None

class Potion(Item):
    type: str = EntityType.POTION
    effect: str

class RevivingPotion(Potion):
    effect: str = "revive"
    name: str = "Reviving Potion"

class HealthPotion(Potion):
    effect: str = "regen"
    name: str = "Health Potion"

class Difficulty:
    EASY = "easy"
    NORMAL = "normal"
    HARD = "hard"


class CharacterClass:
    WARRIOR = "warrior"
    MAGE = "mage"
    ROGUE = "rogue"
    HUNTRESS = "huntress"

class Bow(Weapon):
    type: str = "weapon"
    range: int = 6 # Longer range than standard weapons
    name: str = "Bow"
    projectile_type: str = "arrow"

class Staff(Weapon):
    type: str = "weapon"
    range: int = 4
    name: str = "Staff"
    magic_damage: int = 0
    charges: int = 4
    projectile_type: str = "magic_bolt"

class Throwable(Item):
    type: str = "weapon" # Treat as weapon for now so it fits in inventory/usage logic, or keep as item? 
    # Actually, if it's "weapon" type, frontend might try to equip it.
    # Let's use a specific type or handle it. Plan said "Item" or "Weapon" base.
    # Let's use "throwable" type to distinguish easily in frontend.
    type: str = "throwable"
    damage: int
    range: int
    consumable: bool = True
    projectile_type: str = "users_projectile" # default

class Stone(Throwable):
    name: str = "Stone"
    damage: int = 1
    range: int = 5
    consumable: bool = True
    projectile_type: str = "stone"

class Boomerang(Throwable):
    name: str = "Boomerang"
    damage: int = 3
    range: int = 6
    consumable: bool = False
    projectile_type: str = "boomerang"

class ThrowableDagger(Throwable):
    name: str = "Throwable Dagger"
    damage: int = 4
    range: int = 4
    consumable: bool = True
    projectile_type: str = "dagger"

class Mob(Entity):
    type: str = EntityType.MOB
    faction: str = Faction.DUNGEON
    ai_state: str = "idle"
    target_id: Optional[str] = None
    difficulty: str = Difficulty.NORMAL

class Player(Entity):
    type: str = EntityType.PLAYER
    faction: str = Faction.PLAYER
    class_type: str = CharacterClass.WARRIOR # Default
    experience: int = 0
    level: int = 1
    floor_id: int = 1
    strength: int = 10
    inventory: List[Union[Weapon, Wearable, Potion, Key, Item]] = []
    equipped_weapon: Optional[Weapon] = None
    equipped_wearable: Optional[Wearable] = None
    websocket_id: Optional[str] = None
    is_downed: bool = False
    death_processed: bool = False
    # Over-time healing, mirroring SPD's Healing buff. Each application heals
    # `heal_pct_per_tick` of the remaining `heal_left` (plus a flat amount), with a
    # minimum of 1, until exhausted. `heal_cooldown` throttles applications so heals
    # land at a readable cadence rather than every 20Hz tick.
    heal_left: float = 0.0
    heal_pct_per_tick: float = 0.0
    heal_flat_per_tick: float = 0.0
    heal_cooldown: int = 0
    path_queue: List[Tuple[int, int]] = []
    last_auto_move_time: float = 0.0
    is_admin: bool = False

    def take_damage(self, amount: int):
        if self.is_admin:
            return 0
        if self.is_downed:
            return 0
            
        dmg = max(0, amount - self.get_total_defense())
        self.hp -= dmg
        if self.hp <= 0:
            self.hp = 0
            self.is_downed = True
            # Death is permanent: HP reaching 0 is a real death. The full death
            # sequence (inventory scatter + grave) is run once in update_tick.
            self.is_alive = False
        return dmg

    def get_total_attack(self) -> int:
        bonus = 0
        if self.equipped_weapon:
            bonus = self.equipped_weapon.damage
        return self.attack + bonus

    def get_total_defense(self) -> int:
        # Wearables can provide defense in the future, for now they boost health
        return self.defense

    def set_heal(self, amount: float, percent_per_tick: float, flat_per_tick: float):
        # Multiple healing sources don't stack; they combine the best of each
        # property (mirrors Healing.setHeal in the original game).
        self.heal_left = max(self.heal_left, amount)
        self.heal_pct_per_tick = max(self.heal_pct_per_tick, percent_per_tick)
        self.heal_flat_per_tick = max(self.heal_flat_per_tick, flat_per_tick)
        self.heal_cooldown = 0  # first tick applies immediately

    def get_total_max_hp(self) -> int:
        bonus = 0
        if self.equipped_wearable:
            bonus = self.equipped_wearable.health_boost
        return self.max_hp + bonus

    def add_to_inventory(self, item: Item) -> bool:
        if len(self.inventory) < 20:
            self.inventory.append(item)
            return True
        return False

    def equip_item(self, item_id: str) -> bool:
        item = next((i for i in self.inventory if i.id == item_id), None)
        if not item:
            return False

        if isinstance(item, Weapon):
            if self.strength >= item.strength_requirement:
                self.equipped_weapon = item
                return True
        elif isinstance(item, Wearable):
            if self.strength >= item.strength_requirement:
                self.equipped_wearable = item
                # Recalculate health if needed
                if self.hp > self.get_total_max_hp():
                    self.hp = self.get_total_max_hp()
                return True
        return False
