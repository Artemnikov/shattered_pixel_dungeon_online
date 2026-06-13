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

from pydantic import BaseModel, Field

from app.engine.entities.base import (
    Mob as MobEntity,
    DropEntry,
    WeightedCountDrop,
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

    # 2-4 goo blobs on death: SPD's Random.chances({0,0,6,3,1}) -> 60% chance of
    # 2, 30% of 3, 10% of 4 (avg 2.5). The boss-floor key is dropped separately
    # (see GameInstance.handle_boss_death) because it needs the floor-specific
    # lock id.
    weighted_drops: List[WeightedCountDrop] = [
        WeightedCountDrop(item_kind="goo_blob", weights=[6, 3, 1], base_count=2),
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
    view_distance: int = 12

    phase2: bool = False
    enrage_announced: bool = False
    fight_started: bool = False

    # Ability/jump state (mirrors Tengu.java's HP-bracket jump and the
    # bomb/fire/shocker ability rotation used while enraged).
    hp_bracket: int = 7
    ability_cooldown_until: float = 2.0  # SPD: starts at 2 so 1-turn delay before first ability
    abilities_used: int = 0
    last_ability: int = -1  # SPD: 90% no-repeat; -1 = none yet
    arena_jumps: int = 0     # SPD: affects targetAbilityUses() cooldown
    bomb_x: int = -1
    bomb_y: int = -1
    bomb_timer: int = 0

    # SPD Tengu immunities
    immunities: List[str] = Field(default_factory=lambda: ["roots", "blindness", "dread", "terror"])

    loot_table: List[DropEntry] = [
        DropEntry(item_kind="tengu_mask", chance=1.0, max_global=0),
    ]

    def is_enraged(self) -> bool:
        return self.hp * 2 <= self.max_hp

    def get_attack_skill(self) -> int:
        return 20 if not self.is_enraged() else 10

    def target_ability_uses(self) -> int:
        target = 1 + 2 * self.arena_jumps
        target += max(0, self.arena_jumps - 2)
        return target

    # HP bracket clamping: Tengu cannot be hit through multiple HP/8 brackets
    # at once (mirrors Tengu.damage()). Called after damage is dealt.
    def clamp_bracket(self) -> None:
        hp_bracket = self.max_hp // 8
        if hp_bracket == 0:
            return
        curbracket = max(0, (self.hp * 8 - 1) // self.max_hp)  # SPD-style bracket
        if self.hp <= curbracket * hp_bracket:
            self.hp = curbracket * hp_bracket + 1
            if self.hp > self.max_hp:
                self.hp = self.max_hp


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

    # Supercharge mechanic (DM300.java damage/supercharge/loseSupercharge).
    pylons_activated: int = 0
    supercharged: bool = False
    # Set by take_damage when a supercharge threshold is crossed; the combat
    # mixin reads/clears this to trigger CavesBossLevel.activatePylon (which
    # needs floor/player context that take_damage doesn't have).
    pending_pylon_activation: bool = False

    loot_table: List[DropEntry] = [
        DropEntry(item_kind="overloaded_charger", chance=1.0, max_global=0),
    ]

    def is_enraged(self) -> bool:
        return self.hp * 2 <= self.max_hp

    def total_pylons_to_activate(self) -> int:
        # SPD: Challenges.STRONGER_BOSSES would raise this to 3; not implemented.
        return 2

    def take_damage(self, amount: int):
        # DM300.isInvulnerable(): true while supercharged.
        if self.supercharged:
            return 0

        dealt = super().take_damage(amount)

        # DM300.damage(): after applying damage, check the supercharge
        # threshold for the *next* pylon (HT/3 * (2 - pylonsActivated)).
        threshold = self.max_hp // 3 * (2 - self.pylons_activated)
        if self.hp <= threshold and threshold > 0:
            self.hp = threshold
            self.is_alive = True
            self.supercharged = True
            self.pylons_activated += 1
            self.pending_pylon_activation = True

        return dealt


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


class NecroSkeleton(Skeleton):
    """Summoned by Necromancer (SPD NecroSkeleton). Weaker than a regular
    Skeleton, gives no exp/loot (Java maxLvl=-5), starts wandering, and is
    rendered with a 0.75 brightness tint on the frontend."""
    name: str = "NecroSkeleton"
    hp: int = 20
    max_hp: int = 25
    exp: int = 0
    max_lvl: int = -5
    ai_state: str = "wandering"
    loot_table: List[DropEntry] = []
    tinted: bool = True


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

    # Summon-minion state (mirrors SPD Necromancer summoning/summoningPos/firstSummon/mySkeleton)
    summoning: bool = False
    summoning_x: int = -1
    summoning_y: int = -1
    first_summon: bool = True
    my_skeleton_id: str = ""

    def die(self, attacker=None, floor_mobs=None, tile_x=0, tile_y=0, players=None):
        # SPD Necromancer.die(): kill the linked NecroSkeleton when its master dies.
        if floor_mobs and self.my_skeleton_id:
            skeleton = floor_mobs.get(self.my_skeleton_id)
            if skeleton and skeleton.is_alive:
                skeleton.hp = 0
                skeleton.is_alive = False


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
    view_distance: int = 6
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
    view_distance: int = 6
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
    view_distance: int = 6
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
    view_distance: int = 6
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


# ---------------------------------------------------------------------------
# Universal / Environmental Enemies
# ---------------------------------------------------------------------------

class Wraith(MobEntity):
    """HP=1, stats scale with floor_level. spawningWeight=0 (never regular spawn).
    adjustStats(level) must be called after creation."""
    name: str = "Wraith"
    hp: int = 1
    max_hp: int = 1
    attack_skill: int = 10     # 10 + level (scaled by GameInstance on spawn)
    defense_skill: int = 50    # base default, scaled by GameInstance on spawn
    damage_min: int = 1
    damage_max: int = 2        # 1 + level/2 .. 2 + level (set via floor_level)
    dr_min: int = 0
    dr_max: int = 0
    exp: int = 0
    max_lvl: int = -2
    flying: bool = True
    properties: List[str] = ["UNDEAD", "INORGANIC"]
    # Runtime: floor depth used to scale attack/damage
    floor_level: int = 1


class TormentedSpirit(Wraith):
    """Exotic wraith variant (1/100 chance). 50% more damage/accuracy scaling."""
    name: str = "Tormented Spirit"
    pacified: bool = False


class Piranha(MobEntity):
    """HP and defense scale with depth: HP=10+depth*5, defense=10+depth*2.
    Dies on land (out of water). EXP=0. Always drops mystery_meat."""
    name: str = "Piranha"
    hp: int = 30        # default depth=4: 10+4*5=30
    max_hp: int = 30
    attack_skill: int = 20
    defense_skill: int = 18    # 10 + depth*2 (depth=4)
    damage_min: int = 3
    damage_max: int = 8
    dr_min: int = 0
    dr_max: int = 0
    speed: float = 2.0
    exp: int = 0
    max_lvl: int = -2
    loot_table: List[DropEntry] = [
        DropEntry(item_kind="mystery_meat", chance=1.0, max_global=0),
    ]
    # Runtime: set to current depth so stats can be recalculated
    floor_level: int = 4


class PhantomPiranha(Piranha):
    """Exotic piranha variant. Drops phantom_meat instead of mystery_meat."""
    name: str = "Phantom Piranha"
    loot_table: List[DropEntry] = [
        DropEntry(item_kind="phantom_meat", chance=1.0, max_global=0),
    ]


class Mimic(MobEntity):
    """Disguised as a chest until attacked. HP=(1+level)*6, stats scale with level.
    EXP=0. DEMONIC property. setLevel() must be called after creation."""
    name: str = "Mimic"
    hp: int = 12       # level=1: (1+1)*6=12
    max_hp: int = 12
    attack_skill: int = 7      # 6 + level
    defense_skill: int = 2     # 2 + level/2
    damage_min: int = 2        # 1+level .. 2+2*level (attacking state)
    damage_max: int = 4
    dr_min: int = 0
    dr_max: int = 1            # 0 .. 1+level/2
    exp: int = 0
    max_lvl: int = -2
    properties: List[str] = ["DEMONIC"]
    # Runtime
    floor_level: int = 1
    disguised: bool = True
    stealthy: bool = False


class GoldenMimic(Mimic):
    """Golden variant — better loot, same base stats as Mimic at level."""
    name: str = "Golden Mimic"


class EbonyMimic(Mimic):
    """Ebony variant — deals double damage on surprise attack."""
    name: str = "Ebony Mimic"


class Statue(MobEntity):
    """Passive until attacked (activated=False). HP=15+depth*5.
    attackSkill scales with depth. Drops its weapon on death. EXP=0. INORGANIC."""
    name: str = "Statue"
    hp: int = 35       # depth=4: 15+4*5=35
    max_hp: int = 35
    attack_skill: int = 15     # scales with depth (approx 10+depth)
    defense_skill: int = 8     # 4+depth
    damage_min: int = 3
    damage_max: int = 10
    dr_min: int = 0
    dr_max: int = 0
    exp: int = 0
    max_lvl: int = -2
    properties: List[str] = ["INORGANIC"]
    loot_table: List[DropEntry] = [
        DropEntry(item_kind="weapon", chance=1.0, max_global=0),
    ]
    # Runtime
    floor_level: int = 4
    activated: bool = False


class ArmoredStatue(Statue):
    """Armored variant — HP=30+depth*10, has armor glyph DR bonus."""
    name: str = "Armored Statue"
    hp: int = 70       # depth=4: 30+4*10=70
    max_hp: int = 70
    dr_min: int = 2
    dr_max: int = 10
    loot_table: List[DropEntry] = [
        DropEntry(item_kind="armor", chance=1.0, max_global=0),
    ]


class Bee(MobEntity):
    """Flying. Neutral faction initially; turns ENEMY if honey pot is destroyed.
    HP=(2+level)*4, defense=9+level. EXP=0. spawn(level) sets stats."""
    name: str = "Bee"
    hp: int = 12       # level=1: (2+1)*4=12
    max_hp: int = 12
    attack_skill: int = 10     # = defenseSkill
    defense_skill: int = 10    # 9+level
    damage_min: int = 1        # HT/10
    damage_max: int = 3        # HT/4
    dr_min: int = 0
    dr_max: int = 0
    exp: int = 0
    max_lvl: int = -2
    flying: bool = True
    view_distance: int = 4
    # Runtime
    floor_level: int = 1
    honey_pot_id: str = ""


# ---------------------------------------------------------------------------
# Boss: DwarfKing (floor 20)
# ---------------------------------------------------------------------------

class DwarfKing(MobEntity):
    type: str = "boss"
    name: str = "Dwarf King"
    hp: int = 300
    max_hp: int = 300
    attack_skill: int = 26
    defense_skill: int = 22
    damage_min: int = 15
    damage_max: int = 25
    dr_min: int = 0
    dr_max: int = 10
    exp: int = 40
    max_lvl: int = -2
    properties: List[str] = ["UNDEAD"]
    attack_cooldown: float = 1.0
    loot_table: List[DropEntry] = [
        DropEntry(item_kind="kings_crown", chance=1.0, max_global=0),
    ]

    # Boss runtime state
    phase: int = 1
    summons_made: int = 0
    summon_cooldown: float = 0.0
    ability_cooldown: float = 0.0
    fight_started: bool = False
    enrage_announced: bool = False


class DKGhoul(Ghoul):
    """DwarfKing minion — enhanced Ghoul, always starts hunting."""
    name: str = "DK Ghoul"
    properties: List[str] = ["UNDEAD", "BOSS_MINION"]
    max_lvl: int = -2
    # Runtime: life-link pairing
    linked_ghoul_id: str = ""


class DKMonk(Monk):
    """DwarfKing minion — enhanced Monk, always starts hunting."""
    name: str = "DK Monk"
    properties: List[str] = ["BOSS_MINION"]
    max_lvl: int = -2


class DKWarlock(Warlock):
    """DwarfKing minion — enhanced Warlock, always starts hunting."""
    name: str = "DK Warlock"
    properties: List[str] = ["UNDEAD", "BOSS_MINION"]
    max_lvl: int = -2


class DKGolem(Golem):
    """DwarfKing minion — enhanced Golem, always starts hunting."""
    name: str = "DK Golem"
    properties: List[str] = ["INORGANIC", "BOSS_MINION"]
    max_lvl: int = -2


# ---------------------------------------------------------------------------
# Boss: YogDzewa (floor 25)
# ---------------------------------------------------------------------------

class YogDzewa(MobEntity):
    """Final boss. IMMOVABLE+DEMONIC. Invulnerable while fists are alive.
    Phases 0-5: phase 0=pre-fight, 1-4=fist phases, 5=finale."""
    type: str = "boss"
    name: str = "Yog-Dzewa"
    hp: int = 1000
    max_hp: int = 1000
    attack_skill: int = 999    # INFINITE_ACCURACY for beam attacks
    defense_skill: int = 0
    damage_min: int = 20
    damage_max: int = 30
    dr_min: int = 0
    dr_max: int = 0
    exp: int = 50
    max_lvl: int = -2
    flying: bool = True
    view_distance: int = 12
    properties: List[str] = ["DEMONIC", "IMMOVABLE"]
    loot_table: List[DropEntry] = []

    # Boss runtime state
    phase: int = 0
    fist_ids: List[str] = Field(default_factory=list)  # currently-alive spawned fist instance IDs
    fist_order: List[str] = Field(default_factory=list)  # ordered fist class names yet to be spawned
    ability_cooldown: float = 10.0
    summon_cooldown: float = 10.0
    fight_started: bool = False

    def defense_proc(self, damage: int, attacker, floor_mobs: dict, tile_x: int, tile_y: int) -> int:
        # Invincible while any fist is alive (phases 0-4).
        if self.phase < 5:
            alive_fists = [m for m in floor_mobs.values()
                           if m.id in self.fist_ids and getattr(m, 'is_alive', False)]
            if alive_fists:
                return 0
        return damage


# Fists are invincible while standing within this many tiles (Manhattan) of
# their Yog-Dzewa.
FIST_INVINCIBILITY_RADIUS = 4


def _is_fist_near_yog(fist, floor_mobs: dict) -> bool:
    """Return True when `fist` is within FIST_INVINCIBILITY_RADIUS tiles of its Yog (Manhattan)."""
    if not fist.yog_id:
        return False
    yog = floor_mobs.get(fist.yog_id)
    if yog is None or not yog.is_alive:
        return False
    return (abs(fist.pos.x - yog.pos.x) + abs(fist.pos.y - yog.pos.y)
            <= FIST_INVINCIBILITY_RADIUS)


class _YogFistMixin(BaseModel):
    """Shared state/behavior for YogDzewa's six fist minions."""
    paired_fist_id: str = ""
    yog_id: str = ""
    view_distance: int = 6

    def defense_proc(self, damage: int, attacker, floor_mobs: dict, tile_x: int, tile_y: int) -> int:
        if _is_fist_near_yog(self, floor_mobs):
            return 0
        return damage


class BurningFist(_YogFistMixin, MobEntity):
    """YogDzewa fist. HP=300. FIERY+DEMONIC. Ranged fire attack."""
    type: str = "boss"
    name: str = "Burning Fist"
    hp: int = 300
    max_hp: int = 300
    attack_skill: int = 36
    defense_skill: int = 20
    damage_min: int = 18
    damage_max: int = 36
    dr_min: int = 0
    dr_max: int = 15
    exp: int = 25
    max_lvl: int = -2
    properties: List[str] = ["DEMONIC", "FIERY"]
    attack_range: int = 8
    loot_table: List[DropEntry] = []

    # Boss runtime state
    ranged_cooldown: float = 0.0


class SoiledFist(_YogFistMixin, MobEntity):
    """YogDzewa fist. HP=300. DEMONIC. Roots enemies, spreads grass."""
    type: str = "boss"
    name: str = "Soiled Fist"
    hp: int = 300
    max_hp: int = 300
    attack_skill: int = 36
    defense_skill: int = 20
    damage_min: int = 18
    damage_max: int = 36
    dr_min: int = 0
    dr_max: int = 15
    exp: int = 25
    max_lvl: int = -2
    properties: List[str] = ["DEMONIC"]
    attack_range: int = 8
    loot_table: List[DropEntry] = []

    ranged_cooldown: float = 0.0

    def take_damage(self, amount: int):
        # SoiledFist.damage(): SPD reduces damage based on nearby grass cells
        # (0-6 -> up to 100% reduction). Grass spread isn't ported, so apply a
        # flat 25% reduction as a documented simplification. (SPD also makes
        # Soiled immune to Burning-sourced damage, but take_damage here has no
        # damage-source param to check, so that part is omitted.)
        amount = round(amount * 0.75)
        return super().take_damage(amount)


class RottingFist(_YogFistMixin, MobEntity):
    """YogDzewa fist. HP=300. ACIDIC+DEMONIC. Converts damage to bleeding; zap=toxic gas."""
    type: str = "boss"
    name: str = "Rotting Fist"
    hp: int = 300
    max_hp: int = 300
    attack_skill: int = 36
    defense_skill: int = 20
    damage_min: int = 18
    damage_max: int = 36
    dr_min: int = 0
    dr_max: int = 15
    exp: int = 25
    max_lvl: int = -2
    properties: List[str] = ["DEMONIC", "ACIDIC"]
    attack_range: int = 8
    loot_table: List[DropEntry] = []

    ranged_cooldown: float = 0.0


class RustedFist(_YogFistMixin, MobEntity):
    """YogDzewa fist. HP=300. INORGANIC+DEMONIC. Defers all damage as viscosity. Higher damage (22-44)."""
    type: str = "boss"
    name: str = "Rusted Fist"
    hp: int = 300
    max_hp: int = 300
    attack_skill: int = 36
    defense_skill: int = 20
    damage_min: int = 22
    damage_max: int = 44
    dr_min: int = 0
    dr_max: int = 15
    exp: int = 25
    max_lvl: int = -2
    properties: List[str] = ["DEMONIC", "INORGANIC"]
    attack_range: int = 8
    loot_table: List[DropEntry] = []

    ranged_cooldown: float = 0.0
    viscosity_stacks: int = 0

    def take_damage(self, amount: int):
        # RustedFist.damage(): all incoming damage is deferred via the
        # Viscosity.DeferedDamage buff and released gradually (10%/tick) by
        # _update_yog_fist in tick.py. No immediate HP loss.
        if amount > 0:
            self.viscosity_stacks += amount
        return 0


class BrightFist(_YogFistMixin, MobEntity):
    """YogDzewa fist. HP=300. ELECTRIC+DEMONIC. Light beam blinds; teleports at half HP."""
    type: str = "boss"
    name: str = "Bright Fist"
    hp: int = 300
    max_hp: int = 300
    attack_skill: int = 36
    defense_skill: int = 20
    damage_min: int = 18
    damage_max: int = 36
    dr_min: int = 0
    dr_max: int = 15
    exp: int = 25
    max_lvl: int = -2
    properties: List[str] = ["DEMONIC", "ELECTRIC"]
    attack_range: int = 8
    loot_table: List[DropEntry] = []

    ranged_cooldown: float = 0.0
    teleport_used: bool = False
    pending_teleport: bool = False

    def take_damage(self, amount: int):
        dealt = super().take_damage(amount)
        # BrightFist.damage(): on first crossing below 50% HP, clamp to
        # exactly half HP and teleport away (handled in _update_yog_fist).
        if self.hp <= self.max_hp // 2 and not self.teleport_used:
            self.hp = self.max_hp // 2
            self.is_alive = self.hp > 0
            self.teleport_used = True
            self.pending_teleport = True
        return dealt


class DarkFist(_YogFistMixin, MobEntity):
    """YogDzewa fist. HP=300. DEMONIC. Dark bolt extinguishes light; teleports at half HP."""
    type: str = "boss"
    name: str = "Dark Fist"
    hp: int = 300
    max_hp: int = 300
    attack_skill: int = 36
    defense_skill: int = 20
    damage_min: int = 18
    damage_max: int = 36
    dr_min: int = 0
    dr_max: int = 15
    exp: int = 25
    max_lvl: int = -2
    properties: List[str] = ["DEMONIC"]
    attack_range: int = 8
    loot_table: List[DropEntry] = []

    ranged_cooldown: float = 0.0
    teleport_used: bool = False
    pending_teleport: bool = False

    def take_damage(self, amount: int):
        dealt = super().take_damage(amount)
        # DarkFist.damage(): same 50%-HP teleport pattern as BrightFist.
        if self.hp <= self.max_hp // 2 and not self.teleport_used:
            self.hp = self.max_hp // 2
            self.is_alive = self.hp > 0
            self.teleport_used = True
            self.pending_teleport = True
        return dealt


class YogEye(Eye):
    """YogDzewa summon — Eye minion variant. BOSS_MINION."""
    name: str = "Yog Eye"
    properties: List[str] = ["DEMONIC", "BOSS_MINION"]
    max_lvl: int = -2


class YogScorpio(Scorpio):
    """YogDzewa summon — Scorpio minion variant. BOSS_MINION."""
    name: str = "Yog Scorpio"
    properties: List[str] = ["DEMONIC", "BOSS_MINION"]
    max_lvl: int = -2


class YogRipper(RipperDemon):
    """YogDzewa summon — RipperDemon minion variant. BOSS_MINION."""
    name: str = "Yog Ripper"
    properties: List[str] = ["DEMONIC", "BOSS_MINION"]
    max_lvl: int = -2


# ---------------------------------------------------------------------------
# Static Spawners
# ---------------------------------------------------------------------------

class DemonSpawner(MobEntity):
    """Immovable. Spawns RipperDemons periodically. DEMONIC+IMMOVABLE.
    HP=120, DR 0-12. loot=health_potion 100%. Passive until damaged."""
    name: str = "Demon Spawner"
    hp: int = 120
    max_hp: int = 120
    attack_skill: int = 0
    defense_skill: int = 0
    damage_min: int = 0
    damage_max: int = 0
    dr_min: int = 0
    dr_max: int = 12
    exp: int = 15
    max_lvl: int = 29
    properties: List[str] = ["DEMONIC", "INORGANIC", "IMMOVABLE"]
    loot_table: List[DropEntry] = [
        DropEntry(item_kind="health_potion", chance=1.0, max_global=0),
    ]

    # Runtime
    spawn_cooldown: int = 20
    first_spawn_done: bool = False


class Pylon(MobEntity):
    """Immovable. Fires lightning bolts when activated. ELECTRIC+INORGANIC+IMMOVABLE.
    HP=50 (normal) / 80 (challenge). Inactive until DM-300 fight begins."""
    name: str = "Pylon"
    hp: int = 50
    max_hp: int = 50
    attack_skill: int = 0
    defense_skill: int = 0
    damage_min: int = 10
    damage_max: int = 20
    dr_min: int = 0
    dr_max: int = 0
    exp: int = 0
    max_lvl: int = -2
    properties: List[str] = ["ELECTRIC", "INORGANIC", "IMMOVABLE"]
    loot_table: List[DropEntry] = []

    # Runtime
    bolt_cooldown: int = 5
    linked_pylon_id: str = ""
    activated: bool = False
    # Pylon.targetNeighbor = Random.Int(8) at spawn.
    fire_target_idx: int = Field(default_factory=lambda: random.randint(0, 7))

    def take_damage(self, amount: int):
        # Immune to all damage while inactive (Pylon.isInvulnerable: alignment == NEUTRAL).
        if not self.activated:
            return 0
        if amount >= 15:
            amount = 14 + int((math.sqrt(8 * (amount - 14) + 1) - 1) / 2)
        return super().take_damage(amount)


# ---------------------------------------------------------------------------
# Sewer Boss (floor 5) hidden room NPC
# ---------------------------------------------------------------------------

class RatKing(MobEntity):
    """Cosmetic NPC in the sewer boss secret treasure room (RatKing.java).
    Sleeps forever, never wakes/attacks, takes no damage and dodges everything."""
    name: str = "Rat King"
    type: str = "npc"
    faction: str = Faction.PLAYER
    hp: int = 1
    max_hp: int = 1
    attack_skill: int = 0
    defense_skill: int = 0
    damage_min: int = 0
    damage_max: int = 0
    dr_min: int = 0
    dr_max: int = 0
    exp: int = 0
    max_lvl: int = -2
    loot_table: List[DropEntry] = []
    ai_state: str = "sleeping"
    # Mirrors RatKing.java: never transitions out of SLEEPING (chooseEnemy()
    # always returns null), so the generic wake-up check in tick.py skips it.
    never_wakes: bool = True

    def take_damage(self, amount: int):
        # RatKing.damage(): does nothing — immune to all damage.
        return 0

    def get_effective_defense_skill(self) -> int:
        # RatKing.defenseSkill(): INFINITE_EVASION — always dodges.
        return 10 ** 9


class Shopkeeper(MobEntity):
    """Friendly trader NPC (Shopkeeper.java): immune, never wakes/attacks,
    sells from a fixed stock and buys items from the player."""
    name: str = "Shopkeeper"
    type: str = "npc"
    faction: str = Faction.PLAYER
    hp: int = 1
    max_hp: int = 1
    attack_skill: int = 0
    defense_skill: int = 0
    damage_min: int = 0
    damage_max: int = 0
    dr_min: int = 0
    dr_max: int = 0
    exp: int = 0
    max_lvl: int = -2
    loot_table: List[DropEntry] = []
    ai_state: str = "sleeping"
    never_wakes: bool = True

    def take_damage(self, amount: int):
        # Shopkeeper.damage(): immune to all damage.
        return 0


class Imp(MobEntity):
    """Imp quest-giver NPC (actors/mobs/npcs/Imp.java): immune, never wakes
    or attacks; offers the Golem/Monk token-collection quest."""
    name: str = "Imp"
    type: str = "npc"
    faction: str = Faction.PLAYER
    hp: int = 1
    max_hp: int = 1
    attack_skill: int = 0
    defense_skill: int = 0
    damage_min: int = 0
    damage_max: int = 0
    dr_min: int = 0
    dr_max: int = 0
    exp: int = 0
    max_lvl: int = -2
    loot_table: List[DropEntry] = []
    ai_state: str = "sleeping"
    never_wakes: bool = True

    def take_damage(self, amount: int):
        # Imp.damage(): immune to all damage.
        return 0

    def get_effective_defense_skill(self) -> int:
        return 10 ** 9
