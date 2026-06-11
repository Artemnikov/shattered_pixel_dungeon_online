import random
import uuid
from typing import Dict, List, Optional

from app.engine.entities.base import (
    DropEntry,
    ItemBase,
    Mob,
    Position,
    Seed,
    Gold,
    HealthPotion,
    MysteryMeat,
    MeleeWeapon,
    Armor,
    Potion,
    Key,
    TenguMask,
    GooBlob,
)

TIER2_WEAPONS = [
    ("Sword", 4, 10),
    ("War Hammer", 5, 12),
    ("Battle Axe", 6, 13),
]

RANDOM_WEAPONS = [
    ("Rusty Sword", 2, 10),
    ("Wooden Club", 3, 10),
    ("Dagger", 2, 8),
    ("Mace", 4, 11),
    ("Spear", 3, 10),
    ("Shortsword", 3, 10),
]

RANDOM_ARMORS = [
    ("Cloth Armor", 1, 10),
    ("Leather Armor", 2, 12),
    ("Mail Armor", 3, 14),
    ("Scale Armor", 4, 16),
    ("Plate Armor", 5, 18),
]

RANDOM_POTIONS = [
    "regen",
    "heal",
]


def roll_drops(
    mob: Mob,
    drop_counters: Dict[str, int],
    death_x: int,
    death_y: int,
) -> List[ItemBase]:
    items: List[ItemBase] = []
    for entry in mob.loot_table:
        if entry.max_global > 0 and drop_counters.get(entry.item_kind, 0) >= entry.max_global:
            continue
        if random.random() >= entry.chance:
            continue
        item = _make_item(entry.item_kind)
        if item is None:
            continue
        item.id = str(uuid.uuid4())
        item.pos = Position(x=death_x, y=death_y)
        items.append(item)
        if entry.max_global > 0:
            drop_counters[entry.item_kind] = drop_counters.get(entry.item_kind, 0) + 1

    for wd in mob.weighted_drops:
        if wd.max_global > 0 and drop_counters.get(wd.item_kind, 0) >= wd.max_global:
            continue
        count = wd.base_count + _weighted_choice(wd.weights)
        for _ in range(count):
            item = _make_item(wd.item_kind)
            if item is None:
                continue
            item.id = str(uuid.uuid4())
            item.pos = Position(x=death_x, y=death_y)
            items.append(item)
        if wd.max_global > 0:
            drop_counters[wd.item_kind] = drop_counters.get(wd.item_kind, 0) + count

    return items


def _weighted_choice(weights: List[float]) -> int:
    # Mirrors SPD's Random.chances(): pick index i with probability
    # weights[i] / sum(weights).
    total = sum(weights)
    r = random.random() * total
    acc = 0.0
    for i, w in enumerate(weights):
        acc += w
        if r < acc:
            return i
    return len(weights) - 1


def _make_item(item_kind: str) -> Optional[ItemBase]:
    if item_kind == "seed":
        return Seed(name="Seed of Sunlight")
    elif item_kind == "gold":
        return Gold(name="Gold", quantity=random.randint(5, 20))
    elif item_kind == "health_potion":
        return HealthPotion()
    elif item_kind == "mystery_meat":
        return MysteryMeat()
    elif item_kind == "tier2_weapon":
        name, dmg, str_req = random.choice(TIER2_WEAPONS)
        return MeleeWeapon(name=name, damage=dmg, strength_requirement=str_req)
    elif item_kind == "weapon":
        name, dmg, str_req = random.choice(RANDOM_WEAPONS)
        return MeleeWeapon(name=name, damage=dmg, strength_requirement=str_req)
    elif item_kind == "armor":
        name, tier, str_req = random.choice(RANDOM_ARMORS)
        return Armor(name=name, tier=tier, strength_requirement=str_req)
    elif item_kind == "potion":
        effect = random.choice(RANDOM_POTIONS)
        return Potion(name="Potion", effect=effect)
    elif item_kind == "goo_blob":
        return GooBlob()
    elif item_kind == "tengu_mask":
        return TenguMask(name="Tengu's Mask")
    return None
