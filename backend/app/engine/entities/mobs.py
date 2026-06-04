import math
import random
from typing import Optional, List, TYPE_CHECKING

from app.engine.entities.base import (
    Mob as MobEntity,
    DropEntry,
    Faction,
    Position,
)

if TYPE_CHECKING:
    from app.engine.entities.base import Entity


# ---------------------------------------------------------------------------
# Standard Sewer Enemies
# ---------------------------------------------------------------------------

class Rat(MobEntity):
    name: str = "Rat"
    hp: int = 8
    max_hp: int = 8
    attack_skill: int = 8
    defense_skill: int = 2
    damage_min: int = 1
    damage_max: int = 4
    dr_min: int = 0
    dr_max: int = 1
    exp: int = 1
    max_lvl: int = 5


class Snake(MobEntity):
    name: str = "Snake"
    hp: int = 4
    max_hp: int = 4
    attack_skill: int = 10
    defense_skill: int = 25
    damage_min: int = 1
    damage_max: int = 4
    dr_min: int = 0
    dr_max: int = 0
    exp: int = 2
    max_lvl: int = 7
    loot_table: List[DropEntry] = [
        DropEntry(item_kind="seed", chance=0.25, max_global=0),
    ]


class Gnoll(MobEntity):
    name: str = "Gnoll"
    defense_verb: str = "blocked"
    hp: int = 12
    max_hp: int = 12
    attack_skill: int = 10
    defense_skill: int = 4
    damage_min: int = 1
    damage_max: int = 6
    dr_min: int = 0
    dr_max: int = 2
    exp: int = 2
    max_lvl: int = 8
    loot_table: List[DropEntry] = [
        DropEntry(item_kind="gold", chance=0.5, max_global=0),
    ]


class Swarm(MobEntity):
    name: str = "Swarm"
    hp: int = 50
    max_hp: int = 50
    attack_skill: int = 10
    defense_skill: int = 5
    damage_min: int = 1
    damage_max: int = 4
    dr_min: int = 0
    dr_max: int = 0
    exp: int = 3
    max_lvl: int = 9
    flying: bool = True
    loot_table: List[DropEntry] = [
        DropEntry(item_kind="health_potion", chance=0.167, max_global=5),
    ]

    def defense_proc(self, damage: int, attacker: "Entity", floor_mobs: dict, tile_x: int, tile_y: int):
        # Splits into a clone on hit (SPD Swarm.defenseProc), but always returns
        # the unchanged damage so the resolver still applies it.
        if self.hp >= damage + 2 and self.is_alive:
            clone_id = f"{self.id}_split_{random.randint(0, 99999)}"
            clone = self.model_copy(deep=True)
            clone.id = clone_id
            clone.hp = self.hp // 2
            clone.max_hp = self.hp
            clone.exp = 0
            self.hp -= 1
            for ox, oy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                cx, cy = tile_x + ox, tile_y + oy
                pos = Position(x=cx, y=cy)
                occupied = any(
                    m.pos.x == cx and m.pos.y == cy and m.is_alive
                    for m in floor_mobs.values()
                )
                if not occupied:
                    clone.pos = pos
                    floor_mobs[clone_id] = clone
                    break
        return damage


class Crab(MobEntity):
    name: str = "Crab"
    defense_verb: str = "blocked"
    hp: int = 15
    max_hp: int = 15
    attack_skill: int = 12
    defense_skill: int = 5
    damage_min: int = 1
    damage_max: int = 7
    dr_min: int = 0
    dr_max: int = 4
    speed: float = 2.0
    exp: int = 4
    max_lvl: int = 9
    loot_table: List[DropEntry] = [
        DropEntry(item_kind="mystery_meat", chance=0.167, max_global=0),
    ]


class Slime(MobEntity):
    name: str = "Slime"
    defense_verb: str = "blocked"
    hp: int = 20
    max_hp: int = 20
    attack_skill: int = 12
    defense_skill: int = 5
    damage_min: int = 2
    damage_max: int = 5
    dr_min: int = 0
    dr_max: int = 0
    exp: int = 4
    max_lvl: int = 9
    loot_table: List[DropEntry] = [
        DropEntry(item_kind="tier2_weapon", chance=0.2, max_global=1),
    ]

    def take_damage(self, amount: int):
        if amount > 5:
            amount = 4 + int((math.sqrt(8 * (amount - 4) + 1) - 1) / 2)
        return super().take_damage(amount)


# ---------------------------------------------------------------------------
# Rare Alt Enemies (2% chance to replace a normal spawn)
# ---------------------------------------------------------------------------

class AlbinoRat(MobEntity):
    name: str = "Albino Rat"
    hp: int = 12
    max_hp: int = 12
    attack_skill: int = 8
    defense_skill: int = 2
    damage_min: int = 1
    damage_max: int = 4
    dr_min: int = 0
    dr_max: int = 1
    exp: int = 2
    max_lvl: int = 7
    loot_table: List[DropEntry] = [
        DropEntry(item_kind="mystery_meat", chance=1.0, max_global=0),
    ]

    def attack_proc(self, target: "Entity"):
        if random.random() < 0.5:
            target.bleed_amount = max(getattr(target, "bleed_amount", 0), random.randint(2, 3))
            target.bleed_turns = max(getattr(target, "bleed_turns", 0), 5)


class GnollExile(MobEntity):
    name: str = "Gnoll Exile"
    defense_verb: str = "blocked"
    hp: int = 24
    max_hp: int = 24
    attack_skill: int = 15
    defense_skill: int = 6
    damage_min: int = 1
    damage_max: int = 10
    dr_min: int = 0
    dr_max: int = 1
    exp: int = 5
    max_lvl: int = 10
    ai_state: str = "passive"
    attack_range: int = 2
    loot_table: List[DropEntry] = [
        DropEntry(item_kind="weapon", chance=0.5, max_global=0),
        DropEntry(item_kind="armor", chance=0.5, max_global=0),
        DropEntry(item_kind="potion", chance=0.5, max_global=0),
        DropEntry(item_kind="gold", chance=0.8, max_global=0),
    ]


class HermitCrab(MobEntity):
    name: str = "Hermit Crab"
    defense_verb: str = "blocked"
    hp: int = 25
    max_hp: int = 25
    attack_skill: int = 12
    defense_skill: int = 5
    damage_min: int = 1
    damage_max: int = 7
    dr_min: int = 2
    dr_max: int = 6
    speed: float = 1.0
    exp: int = 5
    max_lvl: int = 10
    loot_table: List[DropEntry] = [
        DropEntry(item_kind="armor", chance=1.0, max_global=0),
        DropEntry(item_kind="mystery_meat", chance=0.5, max_global=0),
    ]


class CausticSlime(MobEntity):
    name: str = "Caustic Slime"
    defense_verb: str = "blocked"
    hp: int = 20
    max_hp: int = 20
    attack_skill: int = 12
    defense_skill: int = 5
    damage_min: int = 2
    damage_max: int = 5
    dr_min: int = 0
    dr_max: int = 0
    exp: int = 5
    max_lvl: int = 10
    properties: List[str] = ["ACIDIC"]
    loot_table: List[DropEntry] = [
        DropEntry(item_kind="goo_blob", chance=1.0, max_global=0),
    ]

    def attack_proc(self, target: "Entity"):
        if random.random() < 0.5:
            target.ooze_amount = 1


class Goo(MobEntity):
    type: str = "boss"
    name: str = "Goo"
    defense_verb: str = "blocked"
    hp: int = 300
    max_hp: int = 300
    attack_skill: int = 14
    defense_skill: int = 6
    damage_min: int = 5
    damage_max: int = 12
    dr_min: int = 0
    dr_max: int = 2
    speed: float = 1.5
    exp: int = 15
    max_lvl: int = 15
    attack_cooldown: float = 2.5
