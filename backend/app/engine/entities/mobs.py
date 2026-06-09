# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 ArtemNikov
#
# Adapted from Shattered Pixel Dungeon (C) 2014-2024 Evan Debenham
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
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
    # Stats mirror the original single-player Goo (Goo.java): 100 HP, attack 10
    # (15 enraged), damage 1-8 (1-12 enraged), DR 0-2. Enrage, water-heal and the
    # pumped-up charge are driven by GameInstance._update_goo / _process_bleed_ooze.
    type: str = "boss"
    name: str = "Goo"
    defense_verb: str = "blocked"
    hp: int = 100
    max_hp: int = 100
    attack_skill: int = 10
    defense_skill: int = 8
    damage_min: int = 1
    damage_max: int = 8
    dr_min: int = 0
    dr_max: int = 2
    speed: float = 1.0
    exp: int = 10
    max_lvl: int = 15
    # Paces both Goo's melee swing and each beat of the pumped-up charge.
    attack_cooldown: float = 1.5

    # Runtime boss state (serialized via model_dump so the client can render the
    # charge telegraph / pump animation, and so it survives reconnects).
    pumped_up: int = 0            # 0 idle, 1 charging, 2 ready to release
    heal_inc: int = 1            # water-heal ramp (SPD Goo.healInc)
    heal_cooldown: int = 0       # ticks until the next water-heal application
    enraged_announced: bool = False
    fight_started: bool = False  # one-shot: fires GOO_FIGHT_STARTED on first notice

    # 2-4 goo blobs on death (avg ~2.5, matching SPD Goo.die). The boss-floor key
    # is dropped separately (see GameInstance.handle_boss_death) because it needs
    # the floor-specific lock id.
    loot_table: List[DropEntry] = [
        DropEntry(item_kind="goo_blob", chance=1.0, max_global=0),
        DropEntry(item_kind="goo_blob", chance=1.0, max_global=0),
        DropEntry(item_kind="goo_blob", chance=0.3, max_global=0),
        DropEntry(item_kind="goo_blob", chance=0.2, max_global=0),
    ]

    def is_enraged(self) -> bool:
        # SPD: Goo enrages once at or below half health (HP*2 <= HT).
        return self.hp * 2 <= self.max_hp

    def get_damage_min(self) -> int:
        return 1

    def get_damage_max(self) -> int:
        return 12 if self.is_enraged() else 8

    def get_effective_defense_skill(self) -> int:
        base = self.defense_skill
        return int(base * 1.5) if self.is_enraged() else base

    def attack_proc(self, target: "Entity") -> None:
        # 1/3 chance to coat the target in caustic ooze (SPD Goo.attackProc).
        from app.engine.game.constants import OOZE_DURATION
        if random.randint(0, 2) == 0:
            target.ooze_amount = OOZE_DURATION


# ---------------------------------------------------------------------------
# Boss: Tengu (floor 10)
# ---------------------------------------------------------------------------

class Tengu(MobEntity):
    type: str = "boss"
    name: str = "Tengu"
    hp: int = 200
    max_hp: int = 200
    attack_skill: int = 20
    defense_skill: int = 15
    damage_min: int = 6
    damage_max: int = 12
    dr_min: int = 0
    dr_max: int = 5
    exp: int = 20
    max_lvl: int = 25
    attack_range: int = 6
    attack_cooldown: float = 1.5

    phase2: bool = False
    enrage_announced: bool = False
    fight_started: bool = False

    loot_table: List[DropEntry] = [
        DropEntry(item_kind="tengu_mask", chance=1.0, max_global=0),
    ]

    def is_enraged(self) -> bool:
        return self.hp * 2 <= self.max_hp

    def get_attack_skill(self) -> int:
        return 20 if not self.is_enraged() else 10


# ---------------------------------------------------------------------------
# Boss: DM-300 (floor 15)
# ---------------------------------------------------------------------------

class DM300(MobEntity):
    type: str = "boss"
    name: str = "DM-300"
    hp: int = 300
    max_hp: int = 300
    attack_skill: int = 22
    defense_skill: int = 10
    damage_min: int = 15
    damage_max: int = 35
    dr_min: int = 5
    dr_max: int = 10
    exp: int = 30
    max_lvl: int = 30
    attack_cooldown: float = 2.0
    properties: List[str] = ["INORGANIC"]

    phase2: bool = False
    rocket_cooldown: int = 0
    fight_started: bool = False

    loot_table: List[DropEntry] = [
        DropEntry(item_kind="overloaded_charger", chance=1.0, max_global=0),
    ]

    def is_enraged(self) -> bool:
        return self.hp * 2 <= self.max_hp


# ---------------------------------------------------------------------------
# Prison Enemies (depths 6-9)
# ---------------------------------------------------------------------------

class Skeleton(MobEntity):
    name: str = "Skeleton"
    hp: int = 25
    max_hp: int = 25
    attack_skill: int = 12
    defense_skill: int = 9
    damage_min: int = 2
    damage_max: int = 10
    dr_min: int = 0
    dr_max: int = 5
    exp: int = 5
    max_lvl: int = 10
    properties: List[str] = ["UNDEAD", "INORGANIC", "BONES"]
    loot_table: List[DropEntry] = [
        DropEntry(item_kind="weapon", chance=0.1667, max_global=0),
    ]

    def die(self, attacker=None, floor_mobs=None, tile_x=0, tile_y=0, players=None):
        dmg = random.randint(6, 12)
        targets = []
        seen_ids = set()
        if floor_mobs:
            for m in floor_mobs.values():
                if m.is_alive and m.id != getattr(self, "id", "") and abs(m.pos.x - tile_x) + abs(m.pos.y - tile_y) <= 1:
                    if m.id not in seen_ids:
                        targets.append(m)
                        seen_ids.add(m.id)
        if players:
            for p in players:
                if p.is_alive and abs(p.pos.x - tile_x) + abs(p.pos.y - tile_y) <= 1:
                    if p.id not in seen_ids:
                        targets.append(p)
                        seen_ids.add(p.id)
        if attacker and attacker.id not in seen_ids and abs(attacker.pos.x - tile_x) + abs(attacker.pos.y - tile_y) <= 1:
            targets.append(attacker)
            seen_ids.add(attacker.id)
        for t in targets:
            t.take_damage(dmg)


class Thief(MobEntity):
    name: str = "Thief"
    hp: int = 20
    max_hp: int = 20
    attack_skill: int = 12
    defense_skill: int = 12
    damage_min: int = 1
    damage_max: int = 10
    dr_min: int = 0
    dr_max: int = 3
    speed: float = 1.5
    exp: int = 5
    max_lvl: int = 11
    attack_cooldown: float = 1.5
    properties: List[str] = ["UNDEAD"]
    loot_table: List[DropEntry] = [
        DropEntry(item_kind="ring", chance=0.03, max_global=0),
        DropEntry(item_kind="artifact", chance=0.03, max_global=0),
    ]

    def attack_proc(self, target):
        gold_stolen = min(getattr(target, "gold", 0), random.randint(5, 20))
        if gold_stolen > 0:
            target.gold -= gold_stolen
            self.ai_state = "fleeing"

    def defense_proc(self, damage: int, attacker, floor_mobs: dict, tile_x: int, tile_y: int):
        if self.ai_state == "fleeing":
            pass
        return damage


class DM100(MobEntity):
    name: str = "DM-100"
    hp: int = 20
    max_hp: int = 20
    attack_skill: int = 11
    defense_skill: int = 8
    damage_min: int = 2
    damage_max: int = 8
    dr_min: int = 0
    dr_max: int = 4
    exp: int = 6
    max_lvl: int = 13
    attack_range: int = 8
    properties: List[str] = ["ELECTRIC", "INORGANIC"]
    loot_table: List[DropEntry] = [
        DropEntry(item_kind="scroll", chance=0.25, max_global=0),
    ]


class Guard(MobEntity):
    name: str = "Guard"
    hp: int = 40
    max_hp: int = 40
    attack_skill: int = 12
    defense_skill: int = 10
    damage_min: int = 4
    damage_max: int = 12
    dr_min: int = 0
    dr_max: int = 7
    exp: int = 7
    max_lvl: int = 14
    properties: List[str] = ["UNDEAD"]
    loot_table: List[DropEntry] = [
        DropEntry(item_kind="armor", chance=0.2, max_global=0),
    ]


class Necromancer(MobEntity):
    name: str = "Necromancer"
    hp: int = 40
    max_hp: int = 40
    attack_skill: int = 10
    defense_skill: int = 14
    damage_min: int = 2
    damage_max: int = 5
    dr_min: int = 0
    dr_max: int = 5
    exp: int = 7
    max_lvl: int = 14
    properties: List[str] = ["UNDEAD", "DEMONIC"]
    loot_table: List[DropEntry] = [
        DropEntry(item_kind="health_potion", chance=0.2, max_global=0),
    ]


# ---------------------------------------------------------------------------
# Caves Enemies (depths 11-14)
# ---------------------------------------------------------------------------

class Bat(MobEntity):
    name: str = "Bat"
    hp: int = 30
    max_hp: int = 30
    attack_skill: int = 16
    defense_skill: int = 15
    damage_min: int = 5
    damage_max: int = 18
    dr_min: int = 0
    dr_max: int = 4
    speed: float = 2.0
    exp: int = 7
    max_lvl: int = 15
    flying: bool = True
    loot_table: List[DropEntry] = [
        DropEntry(item_kind="health_potion", chance=0.167, max_global=0),
    ]

    def attack_proc(self, target: "Entity") -> None:
        # SPD Bat.attackProc: heals self for damage dealt (handled in combat)
        heal = random.randint(1, 3)
        self.hp = min(self.max_hp, self.hp + heal)


class Brute(MobEntity):
    name: str = "Brute"
    hp: int = 40
    max_hp: int = 40
    attack_skill: int = 20
    defense_skill: int = 15
    damage_min: int = 5
    damage_max: int = 25
    dr_min: int = 0
    dr_max: int = 8
    exp: int = 8
    max_lvl: int = 16
    loot_table: List[DropEntry] = [
        DropEntry(item_kind="gold", chance=0.5, max_global=0),
    ]

    def get_damage_max(self) -> int:
        return 40 if self.hp * 2 <= self.max_hp else 25


class ArmoredBrute(Brute):
    name: str = "Armored Brute"
    dr_min: int = 4
    dr_max: int = 12


class Shaman(MobEntity):
    name: str = "Shaman"
    hp: int = 35
    max_hp: int = 35
    attack_skill: int = 18
    defense_skill: int = 15
    damage_min: int = 5
    damage_max: int = 10
    dr_min: int = 0
    dr_max: int = 6
    attack_range: int = 4
    exp: int = 8
    max_lvl: int = 16


class RedShaman(Shaman):
    name: str = "Red Shaman"


class BlueShaman(Shaman):
    name: str = "Blue Shaman"


class PurpleShaman(Shaman):
    name: str = "Purple Shaman"


class Spinner(MobEntity):
    name: str = "Spinner"
    hp: int = 50
    max_hp: int = 50
    attack_skill: int = 22
    defense_skill: int = 17
    damage_min: int = 10
    damage_max: int = 20
    dr_min: int = 0
    dr_max: int = 6
    exp: int = 9
    max_lvl: int = 17
    loot_table: List[DropEntry] = [
        DropEntry(item_kind="mystery_meat", chance=0.125, max_global=0),
    ]


class DM200(MobEntity):
    name: str = "DM-200"
    hp: int = 80
    max_hp: int = 80
    attack_skill: int = 20
    defense_skill: int = 12
    damage_min: int = 10
    damage_max: int = 25
    dr_min: int = 0
    dr_max: int = 8
    exp: int = 9
    max_lvl: int = 17
    properties: List[str] = ["INORGANIC"]
    loot_table: List[DropEntry] = [
        DropEntry(item_kind="weapon", chance=0.2, max_global=0),
    ]


class DM201(DM200):
    name: str = "DM-201"
    properties: List[str] = ["INORGANIC", "ELECTRIC"]


# ---------------------------------------------------------------------------
# City Enemies (depths 16-19)
# ---------------------------------------------------------------------------

class Ghoul(MobEntity):
    name: str = "Ghoul"
    hp: int = 45
    max_hp: int = 45
    attack_skill: int = 24
    defense_skill: int = 20
    damage_min: int = 16
    damage_max: int = 22
    dr_min: int = 0
    dr_max: int = 4
    exp: int = 5
    max_lvl: int = 20
    properties: List[str] = ["UNDEAD"]
    loot_table: List[DropEntry] = [
        DropEntry(item_kind="gold", chance=0.2, max_global=0),
    ]


class FireElemental(MobEntity):
    name: str = "Fire Elemental"
    hp: int = 60
    max_hp: int = 60
    attack_skill: int = 25
    defense_skill: int = 20
    damage_min: int = 20
    damage_max: int = 25
    dr_min: int = 0
    dr_max: int = 5
    exp: int = 10
    max_lvl: int = 20
    properties: List[str] = ["FIERY", "INORGANIC"]


class FrostElemental(FireElemental):
    name: str = "Frost Elemental"
    properties: List[str] = ["ICY", "INORGANIC"]


class ShockElemental(FireElemental):
    name: str = "Shock Elemental"
    properties: List[str] = ["ELECTRIC", "INORGANIC"]


class ChaosElemental(FireElemental):
    name: str = "Chaos Elemental"
    properties: List[str] = ["INORGANIC"]


class Warlock(MobEntity):
    name: str = "Warlock"
    hp: int = 70
    max_hp: int = 70
    attack_skill: int = 25
    defense_skill: int = 18
    damage_min: int = 12
    damage_max: int = 18
    dr_min: int = 0
    dr_max: int = 8
    attack_range: int = 5
    exp: int = 11
    max_lvl: int = 21
    properties: List[str] = ["UNDEAD"]
    loot_table: List[DropEntry] = [
        DropEntry(item_kind="potion", chance=0.5, max_global=0),
    ]


class Monk(MobEntity):
    name: str = "Monk"
    hp: int = 70
    max_hp: int = 70
    attack_skill: int = 30
    defense_skill: int = 30
    damage_min: int = 12
    damage_max: int = 25
    dr_min: int = 0
    dr_max: int = 2
    exp: int = 11
    max_lvl: int = 21
    loot_table: List[DropEntry] = [
        DropEntry(item_kind="food", chance=0.083, max_global=0),
    ]


class Senior(Monk):
    name: str = "Senior"
    damage_min: int = 16
    damage_max: int = 25
    loot_table: List[DropEntry] = [
        DropEntry(item_kind="food", chance=1.0, max_global=0),
    ]


class Golem(MobEntity):
    name: str = "Golem"
    hp: int = 120
    max_hp: int = 120
    attack_skill: int = 28
    defense_skill: int = 15
    damage_min: int = 25
    damage_max: int = 30
    dr_min: int = 0
    dr_max: int = 12
    exp: int = 12
    max_lvl: int = 22
    properties: List[str] = ["INORGANIC"]
    loot_table: List[DropEntry] = [
        DropEntry(item_kind="weapon", chance=0.2, max_global=0),
        DropEntry(item_kind="armor", chance=0.2, max_global=0),
    ]


# ---------------------------------------------------------------------------
# Halls Enemies (depths 21-24)
# ---------------------------------------------------------------------------

class Succubus(MobEntity):
    name: str = "Succubus"
    hp: int = 80
    max_hp: int = 80
    attack_skill: int = 25
    defense_skill: int = 25
    damage_min: int = 25
    damage_max: int = 30
    dr_min: int = 0
    dr_max: int = 10
    exp: int = 12
    max_lvl: int = 25
    flying: bool = True
    properties: List[str] = ["DEMONIC"]
    loot_table: List[DropEntry] = [
        DropEntry(item_kind="scroll", chance=0.33, max_global=0),
    ]


class Eye(MobEntity):
    name: str = "Evil Eye"
    hp: int = 100
    max_hp: int = 100
    attack_skill: int = 30
    defense_skill: int = 20
    damage_min: int = 20
    damage_max: int = 30
    dr_min: int = 0
    dr_max: int = 10
    attack_range: int = 8
    exp: int = 13
    max_lvl: int = 26
    flying: bool = True
    loot_table: List[DropEntry] = [
        DropEntry(item_kind="health_potion", chance=1.0, max_global=0),
    ]


class Scorpio(MobEntity):
    name: str = "Scorpio"
    hp: int = 110
    max_hp: int = 110
    attack_skill: int = 36
    defense_skill: int = 24
    damage_min: int = 30
    damage_max: int = 40
    dr_min: int = 0
    dr_max: int = 16
    attack_range: int = 5
    exp: int = 14
    max_lvl: int = 27
    loot_table: List[DropEntry] = [
        DropEntry(item_kind="potion", chance=0.5, max_global=0),
    ]


class AcidicScorpio(Scorpio):
    name: str = "Acidic Scorpio"
    properties: List[str] = ["ACIDIC"]


class RipperDemon(MobEntity):
    name: str = "Ripper Demon"
    hp: int = 60
    max_hp: int = 60
    attack_skill: int = 22
    defense_skill: int = 22
    damage_min: int = 15
    damage_max: int = 25
    dr_min: int = 0
    dr_max: int = 4
    exp: int = 9
    max_lvl: int = -2
    flying: bool = True
    properties: List[str] = ["DEMONIC"]


# ---------------------------------------------------------------------------
# Prison Rare Alt Enemies
# ---------------------------------------------------------------------------

class Bandit(Thief):
    name: str = "Bandit"
    loot_table: List[DropEntry] = [
        DropEntry(item_kind="ring", chance=1.0, max_global=0),
    ]


class SpectralNecromancer(Necromancer):
    name: str = "Spectral Necromancer"
    properties: List[str] = ["UNDEAD", "DEMONIC"]
