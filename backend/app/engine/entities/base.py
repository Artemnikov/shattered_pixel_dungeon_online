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
from __future__ import annotations

import uuid as _uuid
from typing import Annotated, ClassVar, Literal, Optional, List, Dict, Tuple, Union

from pydantic import BaseModel, Field, computed_field

from app.engine.entities.buffs import Buff, add_buff, remove_buff, has_buff, get_buff
from app.engine.entities.subclasses import SubclassInfo, TalentInfo


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

class Shield(BaseModel):
    priority: int = 0
    amount: int = 0
    decay: int = 1  # min(1, amount/decay) removed per tick
    name: str = ""  # logical id for identifying a specific shield


class Entity(BaseModel):
    id: str
    type: str
    name: str
    pos: Position
    hp: int
    max_hp: int
    attack: int = 0
    defense: int = 0
    speed: float = 1.0
    is_alive: bool = True
    faction: str
    last_attack_time: float = 0.0
    attack_cooldown: float = 1.0

    # Vision range in tiles (SPD Char.viewDistance = 8). Single field that future
    # Light/Blindness/Farsight-style buffs adjust; 0 means effectively sightless.
    view_distance: int = 8

    # SPD combat stats
    attack_skill: int = 10
    defense_skill: int = 5
    damage_min: int = 1
    damage_max: int = 4
    dr_min: int = 0
    dr_max: int = 0
    max_lvl: int = 5

    defense_verb: str = "dodged"

    # Status effect fields (mutated by attack_proc/defense_proc)
    bleed_amount: int = 0
    bleed_turns: int = 0
    ooze_amount: int = 0       # remaining ooze "turns" (caustic DoT)
    ooze_cooldown: int = 0     # ticks until the next ooze damage application

    # Shields (absorption layers)
    shields: List[Shield] = Field(default_factory=list)

    # Crit / surprise-attack damage bonus multiplier (e.g. 0.5 = +50%)
    crit_damage_bonus: float = 0.0
    # Grim enchantment: max execute chance at 0 HP
    grim_max_chance: float = 0.0
    # Kinetic enchantment: overflow damage carried to next hit
    conserved_damage: int = 0
    # Fury buff: flat 1.5x damage multiplier
    has_fury: bool = False
    fury_turns_remaining: int = 0

    # Stealth / invisibility
    invisible: int = 0

    # Generic buff system
    buffs: List[Buff] = Field(default_factory=list)


    def add_buff(self, buff_type: str, duration: float, level: int = 0, source_id: str = None, stack_mode: str = "replace") -> Buff:
        result = add_buff(self.buffs, buff_type, duration, level, source_id, stack_mode)
        if buff_type == "invisibility" or buff_type == "shadows":
            self.invisible += 1
        return result

    def remove_buff(self, buff_type: str) -> Optional[Buff]:
        result = remove_buff(self.buffs, buff_type)
        if result and (result.type == "invisibility" or result.type == "shadows"):
            self.invisible = max(0, self.invisible - 1)
        return result

    def has_buff(self, buff_type: str) -> bool:
        return has_buff(self.buffs, buff_type)

    def get_buff(self, buff_type: str) -> Optional[Buff]:
        return get_buff(self.buffs, buff_type)

    def get_stealth(self) -> float:
        base = 0.0
        obf = self.get_buff("obfuscation")
        if obf:
            base += 1 + obf.level / 3
        prep = self.get_buff("preparation")
        if prep:
            base += 2
        return base

    def get_dr_min(self) -> int:
        base = self.dr_min
        barkskin = self.get_buff("barkskin")
        if barkskin:
            base += barkskin.level
        return base

    def get_dr_max(self) -> int:
        base = self.dr_max
        barkskin = self.get_buff("barkskin")
        if barkskin:
            base += barkskin.level * 2
        return base

    def get_damage_min(self) -> int:
        return self.damage_min

    def get_damage_max(self) -> int:
        return self.damage_max

    def get_surprise_damage_floor(self) -> float:
        return 0.0

    def get_effective_defense_skill(self) -> int:
        return self.defense_skill

    def move(self, dx: int, dy: int):
        self.pos.x += dx
        self.pos.y += dy

    def process_shields(self, amount: int) -> int:
        if not self.shields:
            return amount
        sorted_shields = sorted(self.shields, key=lambda s: s.priority, reverse=True)
        remaining = amount
        active = []
        for s in sorted_shields:
            if remaining <= 0:
                active.append(s)
            elif s.amount >= remaining:
                s.amount -= remaining
                remaining = 0
                if s.amount > 0:
                    active.append(s)
            else:
                remaining -= s.amount
        self.shields = active
        return remaining

    def get_shield(self, name: str) -> Optional[Shield]:
        return next((s for s in self.shields if s.name == name), None)

    def add_shield(self, name: str, amount: int, priority: int = 0, decay: int = 1) -> Shield:
        existing = self.get_shield(name)
        if existing:
            existing.amount += amount
            return existing
        s = Shield(name=name, amount=amount, priority=priority, decay=decay)
        self.shields.append(s)
        return s

    def decay_shields(self):
        active = []
        for s in self.shields:
            s.amount -= max(1, s.amount // max(1, s.decay))
            if s.amount > 0:
                active.append(s)
        self.shields = active

    def take_damage(self, amount: int):
        amount = self.process_shields(amount)
        self.hp -= amount
        if self.hp <= 0:
            self.hp = 0
            self.is_alive = False
        return max(0, amount)


# ---------------------------------------------------------------------------
# Inventory system — ported from Shattered Pixel Dungeon's Item/Bag/Belongings.
#
# SPD is single-player libGDX Java with object-identity comparisons and Bundle
# persistence. Here the server is authoritative and broadcasts full Pydantic
# snapshots over WebSocket, and clients only ever send {item_id, action}. So the
# port keeps SPD's *structure* (stacking, equip slots, nested category bags,
# quickslots, action dispatch) but:
#   * every lookup/compare is keyed by `id` (str), never object identity;
#   * `split` clones via model_copy(deep=True) + a fresh id (SPD uses a Bundle
#     round-trip clone);
#   * polymorphism uses a `kind` Literal discriminator so nested items serialize
#     cleanly and the client can switch on `kind`.
# ---------------------------------------------------------------------------

class ItemCategory:
    WEAPON = "weapon"
    ARMOR = "armor"
    RING = "ring"
    ARTIFACT = "artifact"
    WAND = "wand"
    POTION = "potion"
    SCROLL = "scroll"
    SEED = "seed"
    STONE = "stone"
    FOOD = "food"
    GOLD = "gold"
    KEY = "key"
    MISC = "misc"
    BAG = "bag"
    SCENERY = "scenery"

# Sort order inside a bag (mirrors SPD's itemComparator grouping by category).
CATEGORY_ORDER = [
    ItemCategory.WEAPON, ItemCategory.ARMOR, ItemCategory.RING, ItemCategory.ARTIFACT,
    ItemCategory.WAND, ItemCategory.SCROLL, ItemCategory.POTION, ItemCategory.SEED,
    ItemCategory.STONE, ItemCategory.FOOD, ItemCategory.KEY, ItemCategory.GOLD,
    ItemCategory.MISC, ItemCategory.BAG, ItemCategory.SCENERY,
]

class Action:
    DROP = "DROP"
    THROW = "THROW"
    EQUIP = "EQUIP"
    UNEQUIP = "UNEQUIP"
    DRINK = "DRINK"
    READ = "READ"
    ZAP = "ZAP"
    EAT = "EAT"
    OPEN = "OPEN"
    AFFIX = "AFFIX"
    INFO = "INFO"
    STEALTH = "STEALTH"  # Cloak of Shadows: toggle invisibility
    WEAR = "WEAR"        # TengusMask: choose subclass
    ALCHEMIZE = "ALCHEMIZE"  # GooBlob + HealthPotion at an Alchemy Pot -> Elixir of Aquatic Rejuvenation

# Actions that require the player to pick a target cell before resolving.
TARGETED_ACTIONS = {Action.THROW, Action.ZAP}


def _new_id() -> str:
    return str(_uuid.uuid4())


class ItemBase(BaseModel):
    # `kind` is the polymorphic discriminator (overridden as a Literal in each
    # concrete leaf). `type` is the legacy front-end category string kept for
    # backward-compat until the SPD-style UI lands.
    kind: Literal["item"] = "item"
    id: str = ""
    name: str
    type: str = "item"
    pos: Optional[Position] = None

    quantity: int = 1
    level: int = 0
    level_known: bool = False
    cursed: bool = False
    cursed_known: bool = False
    unique: bool = False
    kept_though_lost: bool = False
    # Sitting on a Shopkeeper's stock pile (SPD's Heap.Type.FOR_SALE) — not
    # auto-picked-up by walking over it; bought via SHOP_BUY instead.
    for_sale: bool = False

    # First-discovery latch: set true once this floor item's cell enters a
    # player's FOV (mirrors SPD's Heap.seen).
    seen: bool = False

    # Type-intrinsic, so kept off the wire as ClassVars.
    stackable: ClassVar[bool] = False
    category: ClassVar[str] = ItemCategory.MISC
    # Flavour text shown in the item info window (SPD's Item.desc()).
    DESC: ClassVar[str] = ""

    # --- behaviour ---------------------------------------------------------
    def actions(self, player: Optional["Player"] = None) -> List[str]:
        # SPD's Item.actions defaults to DROP + THROW for everything.
        return [Action.THROW, Action.DROP]

    def default_action(self) -> Optional[str]:
        return None

    def description(self, player: Optional["Player"] = None) -> str:
        # SPD's Item.info(): flavour text plus any dynamic lines. Subclasses add
        # context (strength requirement, upgrade level, curse) via _info_lines.
        lines = [self.DESC] if self.DESC else []
        lines += self._info_lines(player)
        return "\n\n".join(l for l in lines if l)

    def _info_lines(self, player: Optional["Player"] = None) -> List[str]:
        return []

    def uses_targeting(self, action: str) -> bool:
        return action in TARGETED_ACTIONS

    def is_identified(self) -> bool:
        return self.level_known and self.cursed_known

    def is_similar(self, other: "ItemBase") -> bool:
        return (
            type(self) is type(other)
            and not isinstance(self, Bag)
            and self.level == other.level
            and self.name == other.name
        )

    def merge(self, other: "ItemBase") -> "ItemBase":
        self.quantity += other.quantity
        other.quantity = 0
        return self

    def split(self, amount: int) -> Optional["ItemBase"]:
        if amount <= 0 or amount >= self.quantity:
            return None
        clone = self.model_copy(deep=True)
        clone.id = _new_id()      # id-addressed protocol: halves must not collide
        clone.quantity = amount
        self.quantity -= amount
        return clone

    def value(self, identified: bool = False) -> int:
        # SPD's Item.value(): base price for shop sell-back. `identified` is
        # whether this item's *kind* has been identified this run (used by
        # potions/scrolls whose price depends on identification, not just
        # this instance's level/curse state).
        return 0


def _tiered_value(tier: int, level: int, level_known: bool, cursed: bool, cursed_known: bool) -> int:
    # Shared by MeleeWeapon/Armor: SPD's `20 * tier` formula with
    # cursed/level price modifiers.
    price = 20 * tier
    if cursed_known and cursed:
        price /= 2
    if level_known and level > 0:
        price *= (level + 1)
    return max(1, round(price))


def _charm_value(level: int, level_known: bool, cursed: bool, cursed_known: bool) -> int:
    # Shared by Wand/Ring: SPD's flat 75 base with cursed/level price modifiers.
    price = 75
    if cursed and cursed_known:
        price /= 2
    if level_known:
        if level > 0:
            price *= (level + 1)
        elif level < 0:
            price /= (1 - level)
    return max(1, round(price))


class EquipableItem(ItemBase):
    strength_requirement: int = 10

    def actions(self, player: Optional["Player"] = None) -> List[str]:
        base = super().actions(player)
        equipped = bool(player and player.belongings.is_equipped(self.id))
        return [Action.UNEQUIP if equipped else Action.EQUIP] + base

    def default_action(self) -> Optional[str]:
        return Action.EQUIP

    def _info_lines(self, player: Optional["Player"] = None) -> List[str]:
        lines: List[str] = []
        req = f"It requires {self.strength_requirement} points of strength."
        if player is not None and player.strength < self.strength_requirement:
            req += f" Which is more than your {player.strength} points."
        lines.append(req)
        if self.level_known and self.level != 0:
            sign = "+" if self.level > 0 else ""
            lines.append(f"It is currently upgraded to {sign}{self.level}.")
        if self.cursed_known and self.cursed:
            lines.append("It is cursed, and you can't remove it.")
        return lines


class KindOfWeapon(EquipableItem):
    type: str = "weapon"
    category: ClassVar[str] = ItemCategory.WEAPON
    damage: int = 1
    range: int = 1
    attack_cooldown: float = 1.0
    enchantment: Optional[str] = None
    projectile_type: Optional[str] = None
    # On surprise attacks, damage floor is raised by this fraction of the range
    surprise_damage_floor: float = 0.0

    def _info_lines(self, player: Optional["Player"] = None) -> List[str]:
        lines: List[str] = []
        if isinstance(self, MeleeWeapon):
            lvl = self.level if self.level_known else 0
            lines.append(f"Deals {self.dmg_min(lvl)}-{self.dmg_max(lvl)} damage per hit.")
        else:
            lines.append(f"Deals {self.damage} damage per hit.")
        lines += super()._info_lines(player)
        return lines


class MeleeWeapon(KindOfWeapon):
    kind: Literal["melee_weapon"] = "melee_weapon"
    tier: int = 1
    DESC: ClassVar[str] = "A reliable melee weapon. Equip it to strike enemies in close combat."

    def dmg_min(self, lvl: int = 0) -> int:
        return self.tier + lvl

    def dmg_max(self, lvl: int = 0) -> int:
        return 5 * (self.tier + 1) + lvl * (self.tier + 1)

    def value(self, identified: bool = False) -> int:
        return _tiered_value(self.tier, self.level, self.level_known, self.cursed, self.cursed_known)


class Dagger(MeleeWeapon):
    kind: Literal["dagger"] = "dagger"
    name: str = "Dagger"
    attack_cooldown: float = 0.84
    strength_requirement: int = 9
    surprise_damage_floor: float = 0.75
    DESC: ClassVar[str] = "A quick dagger. Surprise attacks deal more consistent damage."

    def dmg_max(self, lvl: int = 0) -> int:
        return 4 * (self.tier + 1) + lvl * (self.tier + 1)


class WornShortsword(MeleeWeapon):
    kind: Literal["worn_shortsword"] = "worn_shortsword"
    name: str = "Worn Shortsword"
    attack_cooldown: float = 1.2
    strength_requirement: int = 10
    DESC: ClassVar[str] = "A basic shortsword, somewhat the worse for wear. All warriors start with one."


class Bow(KindOfWeapon):
    kind: Literal["bow"] = "bow"
    name: str = "Bow"
    range: int = 6
    projectile_type: str = "arrow"
    DESC: ClassVar[str] = "A ranged weapon that fires arrows at distant foes. Equip it, then target an enemy to shoot."


class Staff(KindOfWeapon):
    kind: Literal["staff"] = "staff"
    name: str = "Staff"
    range: int = 4
    magic_damage: int = 0
    charges: int = 4
    projectile_type: str = "magic_bolt"
    DESC: ClassVar[str] = "A magical staff that hurls bolts of energy at a distance."


class MissileWeapon(KindOfWeapon):
    kind: Literal["missile_weapon"] = "missile_weapon"
    tier: int = 1
    stackable: ClassVar[bool] = True
    DESC: ClassVar[str] = "A thrown weapon. Hurl it at an enemy from afar."

    def default_action(self) -> Optional[str]:
        return Action.THROW

    def value(self, identified: bool = False) -> int:
        price = 5 * self.tier * self.quantity
        if self.cursed_known and self.cursed:
            price /= 2
        if self.level_known and self.level > 0:
            price *= (self.level + 1)
        return max(1, round(price))


class ArmorEnchantment(BaseModel):
    type: str = "none"
    level: int = 0


class Armor(EquipableItem):
    kind: Literal["armor"] = "armor"
    type: str = "wearable"
    category: ClassVar[str] = ItemCategory.ARMOR
    tier: int = 1
    enchantment: ArmorEnchantment = Field(default_factory=ArmorEnchantment)
    DESC: ClassVar[str] = "Worn armor that absorbs a portion of incoming damage. Equip it for protection."

    def dr_min(self, upgrade_level: int = 0) -> int:
        return upgrade_level

    def dr_max(self, upgrade_level: int = 0) -> int:
        return self.tier * (2 + upgrade_level)

    def value(self, identified: bool = False) -> int:
        return _tiered_value(self.tier, self.level, self.level_known, self.cursed, self.cursed_known)


class KindofMisc(EquipableItem):
    pass


class Ring(KindofMisc):
    kind: Literal["ring"] = "ring"
    type: str = "ring"
    category: ClassVar[str] = ItemCategory.RING
    DESC: ClassVar[str] = "A magical ring that grants a passive bonus while worn."

    def value(self, identified: bool = False) -> int:
        return _charm_value(self.level, self.level_known, self.cursed, self.cursed_known)


class Artifact(KindofMisc):
    kind: Literal["artifact"] = "artifact"
    type: str = "artifact"
    category: ClassVar[str] = ItemCategory.ARTIFACT
    charge: int = 0
    charge_cap: int = 100
    DESC: ClassVar[str] = "A unique artifact with a special power that grows as you use it."


class Wand(ItemBase):
    kind: Literal["wand"] = "wand"
    type: str = "wand"
    category: ClassVar[str] = ItemCategory.WAND
    damage: int = 0
    charges: int = 2
    max_charges: int = 2
    range: int = 4
    projectile_type: str = "magic_bolt"
    DESC: ClassVar[str] = "A wand of magical power. Zap an enemy to spend a charge; charges recover over time."

    def actions(self, player: Optional["Player"] = None) -> List[str]:
        return [Action.ZAP] + super().actions(player)

    def default_action(self) -> Optional[str]:
        return Action.ZAP

    def _info_lines(self, player: Optional["Player"] = None) -> List[str]:
        lines = [f"Deals {self.damage} damage per hit."]
        lines.append(f"It currently holds {self.charges} of {self.max_charges} charges.")
        return lines

    def value(self, identified: bool = False) -> int:
        return _charm_value(self.level, self.level_known, self.cursed, self.cursed_known)


class Potion(ItemBase):
    kind: Literal["potion"] = "potion"
    type: str = "potion"
    category: ClassVar[str] = ItemCategory.POTION
    stackable: ClassVar[bool] = True
    effect: str = ""
    # Shown only once the potion's type is identified; the masked generic text is
    # substituted server-side for unidentified potions.
    DESC: ClassVar[str] = "A magical potion. Drink it to release its effect."

    def actions(self, player: Optional["Player"] = None) -> List[str]:
        return [Action.DRINK] + super().actions(player)

    def default_action(self) -> Optional[str]:
        return Action.DRINK

    def value(self, identified: bool = False) -> int:
        return 30 * self.quantity


class HealthPotion(Potion):
    kind: Literal["health_potion"] = "health_potion"
    name: str = "Health Potion"
    effect: str = "regen"
    DESC: ClassVar[str] = "Drinking this potion restores a good portion of your health over a short time."


class RevivingPotion(Potion):
    kind: Literal["reviving_potion"] = "reviving_potion"
    name: str = "Reviving Potion"
    effect: str = "revive"
    DESC: ClassVar[str] = "A potent elixir that can bring a fallen hero back from the brink."


class FuryPotion(Potion):
    kind: Literal["fury_potion"] = "fury_potion"
    name: str = "Potion of Fury"
    effect: str = "fury"
    DESC: ClassVar[str] = "Drinking this potion fills you with rage, empowering your attacks for a short time."


class PotionOfStrength(Potion):
    kind: Literal["potion_of_strength"] = "potion_of_strength"
    name: str = "Potion of Strength"
    effect: str = "strength"
    DESC: ClassVar[str] = "A fiery red liquid. Drinking it permanently increases your strength by 1."


class PotionOfHaste(Potion):
    kind: Literal["potion_of_haste"] = "potion_of_haste"
    name: str = "Potion of Haste"
    effect: str = "haste"
    DESC: ClassVar[str] = "Drinking this potion briefly doubles your speed."


class PotionOfInvisibility(Potion):
    kind: Literal["potion_of_invisibility"] = "potion_of_invisibility"
    name: str = "Potion of Invisibility"
    effect: str = "invisibility"
    DESC: ClassVar[str] = "Drinking this potion turns you invisible for a short time. Attacking breaks invisibility."


class PotionOfLevitation(Potion):
    kind: Literal["potion_of_levitation"] = "potion_of_levitation"
    name: str = "Potion of Levitation"
    effect: str = "levitation"
    DESC: ClassVar[str] = "Drinking this potion causes you to levitate briefly, letting you fly over pits and traps."


class PotionOfMindVision(Potion):
    kind: Literal["potion_of_mind_vision"] = "potion_of_mind_vision"
    name: str = "Potion of Mind Vision"
    effect: str = "mind_vision"
    DESC: ClassVar[str] = "Drinking this potion lets you sense the minds of nearby creatures through walls."


class PotionOfFrost(Potion):
    kind: Literal["potion_of_frost"] = "potion_of_frost"
    name: str = "Potion of Frost"
    effect: str = "frost"
    DESC: ClassVar[str] = "A cool blue liquid. Drinking it chills you and nearby enemies."


class PotionOfLiquidFlame(Potion):
    kind: Literal["potion_of_liquid_flame"] = "potion_of_liquid_flame"
    name: str = "Potion of Liquid Flame"
    effect: str = "liquid_flame"
    DESC: ClassVar[str] = "Throw or drink this to unleash a burst of fire."


class PotionOfToxicGas(Potion):
    kind: Literal["potion_of_toxic_gas"] = "potion_of_toxic_gas"
    name: str = "Potion of Toxic Gas"
    effect: str = "toxic_gas"
    DESC: ClassVar[str] = "Smashing this potion releases a choking cloud of poison gas."


class PotionOfParalyticGas(Potion):
    kind: Literal["potion_of_paralytic_gas"] = "potion_of_paralytic_gas"
    name: str = "Potion of Paralytic Gas"
    effect: str = "paralytic_gas"
    DESC: ClassVar[str] = "Smashing this releases a gas that paralyzes everything it touches."


class PotionOfPurity(Potion):
    kind: Literal["potion_of_purity"] = "potion_of_purity"
    name: str = "Potion of Purity"
    effect: str = "purity"
    DESC: ClassVar[str] = "Drinking this removes all negative effects and clears nearby gas clouds."


class PotionOfExperience(Potion):
    kind: Literal["potion_of_experience"] = "potion_of_experience"
    name: str = "Potion of Experience"
    effect: str = "experience"
    DESC: ClassVar[str] = "Drinking this immediately grants a full level's worth of experience."

    def value(self, identified: bool = False) -> int:
        return (50 if identified else 30) * self.quantity


class ElixirOfAquaticRejuvenation(Potion):
    kind: Literal["elixir_aqua_rejuv"] = "elixir_aqua_rejuv"
    name: str = "Elixir of Aquatic Rejuvenation"
    effect: str = "aqua_rejuv"
    DESC: ClassVar[str] = "A murky elixir brewed from a Health Potion and a Goo Blob. While its power lasts, you heal whenever you stand in water."

    def value(self, identified: bool = False) -> int:
        return 60 * self.quantity


class Scroll(ItemBase):
    kind: Literal["scroll"] = "scroll"
    type: str = "scroll"
    category: ClassVar[str] = ItemCategory.SCROLL
    stackable: ClassVar[bool] = True
    DESC: ClassVar[str] = "A magical scroll inscribed with arcane runes. Read it to invoke its power."

    def actions(self, player: Optional["Player"] = None) -> List[str]:
        return [Action.READ] + super().actions(player)

    def default_action(self) -> Optional[str]:
        return Action.READ

    def value(self, identified: bool = False) -> int:
        return 30 * self.quantity


class Gold(ItemBase):
    kind: Literal["gold"] = "gold"
    type: str = "gold"
    category: ClassVar[str] = ItemCategory.GOLD
    stackable: ClassVar[bool] = True
    DESC: ClassVar[str] = "A pile of gold coins. Spend it at shops scattered through the dungeon."


class Food(ItemBase):
    kind: Literal["food"] = "food"
    type: str = "food"
    category: ClassVar[str] = ItemCategory.FOOD
    stackable: ClassVar[bool] = True
    energy: int = 0
    DESC: ClassVar[str] = "Edible provisions. Eat it to stave off hunger."

    def default_action(self) -> Optional[str]:
        return Action.EAT

    def value(self, identified: bool = False) -> int:
        return 10 * self.quantity


class Key(ItemBase):
    kind: Literal["key"] = "key"
    type: str = "key"
    category: ClassVar[str] = ItemCategory.KEY
    key_id: str = ""
    DESC: ClassVar[str] = "A key that unlocks a matching door or chest somewhere on this floor."


class TenguMask(ItemBase):
    kind: Literal["tengu_mask"] = "tengu_mask"
    name: str = "Tengu's Mask"
    type: str = "misc"
    category: ClassVar[str] = ItemCategory.MISC
    unique: bool = True
    DESC: ClassVar[str] = "The mask of the infamous Tengu assassin. Wearing it grants the power to choose a subclass path."

    def actions(self, player: Optional["Player"] = None) -> List[str]:
        return [Action.WEAR, Action.THROW, Action.DROP]

    def default_action(self) -> Optional[str]:
        return Action.WEAR


class BrokenSeal(Artifact):
    kind: Literal["broken_seal"] = "broken_seal"
    name: str = "Broken Seal"
    charge: int = 0
    charge_cap: int = 100
    DESC: ClassVar[str] = "A broken seal from the warrior's armor. It can be affixed to armor to provide shielding as you fight."

    def actions(self, player: Optional["Player"] = None) -> List[str]:
        base = super().actions(player)
        equipped = bool(player and player.belongings.is_equipped(self.id))
        if not equipped:
            return base
        has_armor = bool(player and player.belongings.armor is not None)
        if has_armor:
            return [Action.AFFIX, Action.UNEQUIP] + base
        return [Action.UNEQUIP] + base


class CloakOfShadows(Artifact):
    # The Rogue's signature artifact. Toggling STEALTH turns the hero invisible,
    # draining one charge every few seconds (see tick.py's cloak drain). It self-
    # levels with use (charge_cap grows 3 -> 10). Charge regenerates while not
    # stealthed. Mirrors SPD's CloakOfShadows; turn-based timers are recast as
    # real seconds for this engine.
    kind: Literal["cloak_of_shadows"] = "cloak_of_shadows"
    name: str = "Cloak of Shadows"
    type: str = "artifact"
    unique: bool = True
    charge: int = 3
    charge_cap: int = 3
    level_cap: ClassVar[int] = 10
    exp: int = 0
    DESC: ClassVar[str] = (
        "This cloak is an heirloom, passed down from generation to generation. "
        "Activate it to vanish into the shadows; striking from stealth lands a "
        "guaranteed, more powerful surprise attack."
    )

    def actions(self, player: Optional["Player"] = None) -> List[str]:
        base = super().actions(player)
        if player is None:
            return base
        light_cloak = player.talent_info.has("light_cloak")
        usable = (player.belongings.is_equipped(self.id) or light_cloak) and not self.cursed
        has_charge = self.charge > 0 or player.cloak_stealth_active
        if usable and has_charge:
            return [Action.STEALTH] + base
        return base

    def default_action(self) -> Optional[str]:
        return Action.STEALTH

    def _info_lines(self, player: Optional["Player"] = None) -> List[str]:
        lines = super()._info_lines(player)
        lines.append(f"The cloak holds {self.charge} of {self.charge_cap} charges.")
        return lines

    def on_upgrade(self) -> None:
        self.charge_cap = min(self.charge_cap + 1, self.level_cap)


class ScrollOfRage(Scroll):
    kind: Literal["scroll_of_rage"] = "scroll_of_rage"
    name: str = "Scroll of Rage"
    DESC: ClassVar[str] = "A scroll that fills you with fury. Read it in the heat of battle to deliver devastating attacks."

    def actions(self, player: Optional["Player"] = None) -> List[str]:
        return [Action.READ, Action.THROW, Action.DROP]


class ScrollOfMetamorphosis(Scroll):
    kind: Literal["scroll_of_metamorphosis"] = "scroll_of_metamorphosis"
    name: str = "Scroll of Metamorphosis"
    DESC: ClassVar[str] = "A scroll that lets you replace one of your talents with a talent from another class."

    def actions(self, player: Optional["Player"] = None) -> List[str]:
        return [Action.READ, Action.THROW, Action.DROP]


class ScrollOfUpgrade(Scroll):
    kind: Literal["scroll_of_upgrade"] = "scroll_of_upgrade"
    name: str = "Scroll of Upgrade"
    DESC: ClassVar[str] = "Reading this scroll permanently upgrades one of your equipped items."

    def value(self, identified: bool = False) -> int:
        return (50 if identified else 30) * self.quantity


class ScrollOfIdentify(Scroll):
    kind: Literal["scroll_of_identify"] = "scroll_of_identify"
    name: str = "Scroll of Identify"
    DESC: ClassVar[str] = "Reading this scroll reveals the true nature of an unknown item."


class ScrollOfMagicMapping(Scroll):
    kind: Literal["scroll_of_magic_mapping"] = "scroll_of_magic_mapping"
    name: str = "Scroll of Magic Mapping"
    DESC: ClassVar[str] = "Reading this scroll reveals the entire layout of the current floor."

    def value(self, identified: bool = False) -> int:
        return (40 if identified else 30) * self.quantity


class ScrollOfTeleportation(Scroll):
    kind: Literal["scroll_of_teleportation"] = "scroll_of_teleportation"
    name: str = "Scroll of Teleportation"
    DESC: ClassVar[str] = "Reading this scroll teleports you to a random location on the floor."


class ScrollOfRemoveCurse(Scroll):
    kind: Literal["scroll_of_remove_curse"] = "scroll_of_remove_curse"
    name: str = "Scroll of Remove Curse"
    DESC: ClassVar[str] = "Reading this scroll removes all curses from your equipped items."


class ScrollOfRecharging(Scroll):
    kind: Literal["scroll_of_recharging"] = "scroll_of_recharging"
    name: str = "Scroll of Recharging"
    DESC: ClassVar[str] = "Reading this scroll fully recharges your wands."


class ScrollOfLullaby(Scroll):
    kind: Literal["scroll_of_lullaby"] = "scroll_of_lullaby"
    name: str = "Scroll of Lullaby"
    DESC: ClassVar[str] = "Reading this scroll causes nearby creatures to fall asleep."


class ScrollOfTerror(Scroll):
    kind: Literal["scroll_of_terror"] = "scroll_of_terror"
    name: str = "Scroll of Terror"
    DESC: ClassVar[str] = "Reading this scroll fills nearby enemies with overwhelming fear."


class ScrollOfMirrorImage(Scroll):
    kind: Literal["scroll_of_mirror_image"] = "scroll_of_mirror_image"
    name: str = "Scroll of Mirror Image"
    DESC: ClassVar[str] = "Reading this scroll creates illusory copies of yourself to confuse enemies."


class ScrollOfRetribution(Scroll):
    kind: Literal["scroll_of_retribution"] = "scroll_of_retribution"
    name: str = "Scroll of Retribution"
    DESC: ClassVar[str] = "Reading this scroll damages all nearby enemies proportional to your missing health."


class ScrollOfTransmutation(Scroll):
    kind: Literal["scroll_of_transmutation"] = "scroll_of_transmutation"
    name: str = "Scroll of Transmutation"
    DESC: ClassVar[str] = "Reading this scroll transforms a held item into another of the same category."


class Throwable(ItemBase):
    kind: Literal["throwable"] = "throwable"
    type: str = "throwable"
    category: ClassVar[str] = ItemCategory.STONE
    damage: int = 1
    range: int = 5
    consumable: bool = True
    projectile_type: str = "users_projectile"
    DESC: ClassVar[str] = "A thrown item. Hurl it at a target to deal damage."

    def actions(self, player: Optional["Player"] = None) -> List[str]:
        return [Action.THROW, Action.DROP]

    def default_action(self) -> Optional[str]:
        return Action.THROW


class Stone(Throwable):
    kind: Literal["stone"] = "stone"
    name: str = "Stone"
    damage: int = 1
    range: int = 5
    consumable: bool = True
    projectile_type: str = "stone"

    def value(self, identified: bool = False) -> int:
        return round(2.5 * self.quantity)


class Boomerang(Throwable):
    kind: Literal["boomerang"] = "boomerang"
    name: str = "Boomerang"
    damage: int = 3
    range: int = 6
    consumable: bool = False
    projectile_type: str = "boomerang"

    def value(self, identified: bool = False) -> int:
        return 20 * self.quantity


class ThrowableDagger(Throwable):
    kind: Literal["throwable_dagger"] = "throwable_dagger"
    name: str = "Throwable Dagger"
    damage: int = 4
    range: int = 4
    consumable: bool = True
    projectile_type: str = "dagger"

    def value(self, identified: bool = False) -> int:
        return 5 * self.quantity


class Seed(ItemBase):
    kind: Literal["seed"] = "seed"
    type: str = "seed"
    category: ClassVar[str] = ItemCategory.SEED
    stackable: ClassVar[bool] = True
    plant_type: str = "sungrass"
    DESC: ClassVar[str] = "A magical seed. Plant it to release its effect."

    def value(self, identified: bool = False) -> int:
        return 10 * self.quantity


class MysteryMeat(Food):
    kind: Literal["mystery_meat"] = "mystery_meat"
    name: str = "Mystery Meat"
    DESC: ClassVar[str] = "Raw meat from a defeated creature. Eat it to restore some health — if you dare."


class Dewdrop(ItemBase):
    kind: Literal["dewdrop"] = "dewdrop"
    name: str = "Dewdrop"
    type: str = "dewdrop"
    category: ClassVar[str] = ItemCategory.POTION
    stackable: ClassVar[bool] = True
    DESC: ClassVar[str] = "A drop of magical dew. It radiates healing energy."


class Waterskin(ItemBase):
    kind: Literal["waterskin"] = "waterskin"
    name: str = "Waterskin"
    type: str = "waterskin"
    category: ClassVar[str] = ItemCategory.MISC
    stackable: ClassVar[bool] = False
    unique: bool = True
    MAX_VOLUME: ClassVar[int] = 20
    volume: int = 0
    DESC: ClassVar[str] = (
        "A leather pouch that can hold magical dew. Drinking from it restores health."
    )

    def actions(self, player: Optional["Player"] = None) -> List[str]:
        base = super().actions(player)
        if self.volume > 0:
            return [Action.DRINK] + base
        return base

    def default_action(self) -> Optional[str]:
        return Action.DRINK if self.volume > 0 else None

    def is_full(self) -> bool:
        return self.volume >= self.MAX_VOLUME

    def _info_lines(self, player: Optional["Player"] = None) -> List[str]:
        if self.volume == 0:
            return ["It is currently empty."]
        return [f"It contains {self.volume}/{self.MAX_VOLUME} drops of dew."]


class Berry(Food):
    kind: Literal["berry"] = "berry"
    name: str = "Berry"
    energy: int = 100
    DESC: ClassVar[str] = "A sweet berry. Restores a small amount of food."


class SmallRation(Food):
    kind: Literal["small_ration"] = "small_ration"
    name: str = "Small Ration"
    energy: int = 150
    DESC: ClassVar[str] = "A small bundle of provisions. Better than nothing."


class Ration(Food):
    kind: Literal["ration"] = "ration"
    name: str = "Ration"
    energy: int = 300
    DESC: ClassVar[str] = "A satisfying portion of food. Keeps hunger at bay for a good while."


class Pasty(Food):
    kind: Literal["pasty"] = "pasty"
    name: str = "Pasty"
    energy: int = 450
    DESC: ClassVar[str] = "A hearty pastry stuffed with vegetables and meat. Very filling."


class ChargrilledMeat(Food):
    kind: Literal["chargrilled_meat"] = "chargrilled_meat"
    name: str = "Chargrilled Meat"
    energy: int = 300
    DESC: ClassVar[str] = "Properly cooked mystery meat. Smells delicious."


class GooBlob(ItemBase):
    # Goo's death drop (SPD GooBlob): stackable quest reagent, used with a
    # Health Potion at an Alchemy Pot to brew an Elixir of Aquatic Rejuvenation
    # (see Action.ALCHEMIZE / action_alchemize).
    kind: Literal["goo_blob"] = "goo_blob"
    name: str = "Goo Blob"
    type: str = "misc"
    category: ClassVar[str] = ItemCategory.MISC
    stackable: ClassVar[bool] = True
    DESC: ClassVar[str] = "A blob of black ooze left behind by Goo. Can be combined with a Health Potion at an Alchemy Pot."

    def actions(self, player: Optional["Player"] = None) -> List[str]:
        base = super().actions(player)
        if player is not None and any(isinstance(it, HealthPotion) for it in player.inventory):
            return [Action.ALCHEMIZE] + base
        return base

    def value(self, identified: bool = False) -> int:
        return 30 * self.quantity


class DwarfToken(ItemBase):
    # Imp quest reward token (SPD items.quest.DwarfToken): stackable, always
    # identified, dropped by Golems/Monks once the quest is given. Not sellable.
    kind: Literal["dwarf_token"] = "dwarf_token"
    name: str = "Dwarf token"
    type: str = "misc"
    category: ClassVar[str] = ItemCategory.MISC
    stackable: ClassVar[bool] = True
    level_known: bool = True
    cursed_known: bool = True
    DESC: ClassVar[str] = "A small clay token, traded by dwarves of the Imp's homeland."


class Scenery(ItemBase):
    # Non-pickable floor decoration (e.g. graves). Mirrors SPD heaps that aren't
    # collectable. Kept out of AnyItem since it only ever lives on the ground.
    kind: Literal["scenery"] = "scenery"
    type: str = "scenery"
    category: ClassVar[str] = ItemCategory.SCENERY


class Bag(ItemBase):
    kind: Literal["bag"] = "bag"
    type: str = "bag"
    category: ClassVar[str] = ItemCategory.BAG
    unique: bool = True
    capacity: int = 20
    items: List["AnyItem"] = Field(default_factory=list)
    DESC: ClassVar[str] = "A container that expands how much you can carry. Open it to view its contents."

    # None => general backpack (accepts everything). A set => a specialised
    # sub-bag that only accepts those item categories (SPD's pouches/holders).
    accepts: ClassVar[Optional[set]] = None

    def default_action(self) -> Optional[str]:
        return Action.OPEN

    # --- queries -----------------------------------------------------------
    def _local_get(self, item_id: str) -> Optional["ItemBase"]:
        return next((i for i in self.items if i.id == item_id), None)

    def find(self, item_id: str) -> Optional["ItemBase"]:
        local = self._local_get(item_id)
        if local is not None:
            return local
        for sub in self.items:
            if isinstance(sub, Bag):
                found = sub.find(item_id)
                if found is not None:
                    return found
        return None

    def contains(self, item_id: str) -> bool:
        return self.find(item_id) is not None

    def _used_slots(self) -> int:
        # Sub-bags expand storage in SPD rather than consuming a slot.
        return len([i for i in self.items if not isinstance(i, Bag)])

    def can_hold(self, item: "ItemBase") -> bool:
        if isinstance(item, Bag) and self.accepts is not None:
            return False  # specialised pouches can't nest bags
        if self.accepts is not None and item.category not in self.accepts:
            return False
        if item.stackable:
            for it in self.items:
                if it.is_similar(item):
                    return True
        return self._used_slots() < self.capacity

    # --- mutations ---------------------------------------------------------
    def _sort(self) -> None:
        self.items.sort(key=lambda i: CATEGORY_ORDER.index(i.category)
                        if i.category in CATEGORY_ORDER else len(CATEGORY_ORDER))

    def collect(self, item: "ItemBase") -> bool:
        if item.quantity <= 0:
            return True
        # Prefer a matching specialised sub-bag (SPD auto-sorts into pouches).
        for sub in self.items:
            if isinstance(sub, Bag) and sub.can_hold(item) and sub.collect(item):
                return True
        if item.stackable:
            for it in self.items:
                if it.is_similar(item):
                    it.merge(item)
                    return True
        if not self.can_hold(item):
            return False
        self.items.append(item)
        self._sort()
        return True

    def detach(self, item_id: str) -> Optional["ItemBase"]:
        # Remove a single unit (splits a stack), recursing into sub-bags.
        item = self._local_get(item_id)
        if item is None:
            for sub in self.items:
                if isinstance(sub, Bag):
                    r = sub.detach(item_id)
                    if r is not None:
                        return r
            return None
        if item.stackable and item.quantity > 1:
            return item.split(1)
        self.items.remove(item)
        return item

    def detach_all(self, item_id: str) -> Optional["ItemBase"]:
        item = self._local_get(item_id)
        if item is not None:
            self.items.remove(item)
            return item
        for sub in self.items:
            if isinstance(sub, Bag):
                r = sub.detach_all(item_id)
                if r is not None:
                    return r
        return None

    def grab_items(self, source: "Bag") -> None:
        # Pull every item this (specialised) bag accepts out of `source`.
        if self.accepts is None:
            return
        movable = [i for i in list(source.items)
                   if not isinstance(i, Bag) and i.category in self.accepts]
        for it in movable:
            source.items.remove(it)
            self.collect(it)


class VelvetPouch(Bag):
    kind: Literal["velvet_pouch"] = "velvet_pouch"
    name: str = "Velvet Pouch"
    accepts: ClassVar[Optional[set]] = {ItemCategory.SEED, ItemCategory.STONE}

    def value(self, identified: bool = False) -> int:
        return 30


class ScrollHolder(Bag):
    kind: Literal["scroll_holder"] = "scroll_holder"
    name: str = "Scroll Holder"
    accepts: ClassVar[Optional[set]] = {ItemCategory.SCROLL}

    def value(self, identified: bool = False) -> int:
        return 40


class MagicalHolster(Bag):
    kind: Literal["magical_holster"] = "magical_holster"
    name: str = "Magical Holster"
    accepts: ClassVar[Optional[set]] = {ItemCategory.WAND, ItemCategory.STONE}

    def value(self, identified: bool = False) -> int:
        return 60


class PotionBandolier(Bag):
    kind: Literal["potion_bandolier"] = "potion_bandolier"
    name: str = "Potion Bandolier"
    accepts: ClassVar[Optional[set]] = {ItemCategory.POTION}

    def value(self, identified: bool = False) -> int:
        return 40


# Discriminated union of everything that can live inside a Bag / equip slot.
# Keyed by `kind`, so member order is irrelevant and nested items serialize as
# their concrete type. Server never validates inbound items, so this exists only
# for clean outbound dumps + a stable client contract.
AnyItem = Annotated[
    Union[
        MeleeWeapon, Dagger, WornShortsword, Bow, Staff, MissileWeapon,
        Armor, Ring, Artifact, BrokenSeal, CloakOfShadows, Wand,
        HealthPotion, RevivingPotion, FuryPotion,
        PotionOfStrength, PotionOfHaste, PotionOfInvisibility, PotionOfLevitation,
        PotionOfMindVision, PotionOfFrost, PotionOfLiquidFlame, PotionOfToxicGas,
        PotionOfParalyticGas, PotionOfPurity, PotionOfExperience,
        ElixirOfAquaticRejuvenation,
        Potion,
        ScrollOfRage, ScrollOfMetamorphosis,
        ScrollOfUpgrade, ScrollOfIdentify, ScrollOfMagicMapping, ScrollOfTeleportation,
        ScrollOfRemoveCurse, ScrollOfRecharging, ScrollOfLullaby, ScrollOfTerror,
        ScrollOfMirrorImage, ScrollOfRetribution, ScrollOfTransmutation,
        Scroll,
        Gold,
        MysteryMeat, Berry, SmallRation, Ration, Pasty, ChargrilledMeat, Food,
        Key,
        Seed, Dewdrop, Waterskin, Stone, Boomerang, ThrowableDagger, Throwable,
        GooBlob, DwarfToken,
        VelvetPouch, ScrollHolder, MagicalHolster, PotionBandolier, Bag,
    ],
    Field(discriminator="kind"),
]


# --- quickslots ------------------------------------------------------------
QUICKSLOT_SIZE = 6


class QuickSlotEntry(BaseModel):
    item_id: Optional[str] = None
    is_placeholder: bool = False
    placeholder_kind: Optional[str] = None  # re-bind target when a like item returns


class QuickSlot(BaseModel):
    slots: List[QuickSlotEntry] = Field(
        default_factory=lambda: [QuickSlotEntry() for _ in range(QUICKSLOT_SIZE)]
    )

    def index_of(self, item_id: str) -> int:
        return next((i for i, s in enumerate(self.slots) if s.item_id == item_id), -1)

    def clear_item(self, item_id: str) -> None:
        for s in self.slots:
            if s.item_id == item_id:
                s.item_id = None
                s.is_placeholder = False
                s.placeholder_kind = None

    def set_slot(self, index: int, item: "ItemBase") -> None:
        if not (0 <= index < len(self.slots)):
            return
        self.clear_item(item.id)
        self.slots[index] = QuickSlotEntry(item_id=item.id)

    def convert_to_placeholder(self, item: "ItemBase") -> None:
        # Stackable depleted: keep the slot reserved by kind (SPD placeholders).
        for s in self.slots:
            if s.item_id == item.id:
                s.item_id = None
                s.is_placeholder = True
                s.placeholder_kind = item.kind

    def replace_placeholder(self, item: "ItemBase") -> None:
        for s in self.slots:
            if s.is_placeholder and s.placeholder_kind == item.kind:
                s.item_id = item.id
                s.is_placeholder = False
                s.placeholder_kind = None
                return


# --- belongings ------------------------------------------------------------
class Belongings(BaseModel):
    backpack: Bag = Field(default_factory=lambda: Bag(id="backpack", name="Backpack"))
    weapon: Optional[AnyItem] = None
    armor: Optional[AnyItem] = None
    artifact: Optional[AnyItem] = None
    misc: Optional[AnyItem] = None
    ring: Optional[AnyItem] = None

    def equipped_slots(self) -> List[Optional["ItemBase"]]:
        return [self.weapon, self.armor, self.artifact, self.misc, self.ring]

    def is_equipped(self, item_id: str) -> bool:
        return any(s is not None and s.id == item_id for s in self.equipped_slots())

    def all_items(self):
        for s in self.equipped_slots():
            if s is not None:
                yield s
        yield from self._iter_bag(self.backpack)

    def _iter_bag(self, bag: "Bag"):
        for it in bag.items:
            yield it
            if isinstance(it, Bag):
                yield from self._iter_bag(it)

    def get_item(self, item_id: str) -> Optional["ItemBase"]:
        for s in self.equipped_slots():
            if s is not None and s.id == item_id:
                return s
        return self.backpack.find(item_id)

    def slot_name_for(self, item: "ItemBase") -> Optional[str]:
        if isinstance(item, KindOfWeapon):
            return "weapon"
        if isinstance(item, Armor):
            return "armor"
        if isinstance(item, Ring):
            return "ring"
        if isinstance(item, Artifact):
            return "artifact"
        if isinstance(item, KindofMisc):
            return "misc"
        return None


Bag.model_rebuild()
Belongings.model_rebuild()


class Difficulty:
    EASY = "easy"
    NORMAL = "normal"
    HARD = "hard"


class CharacterClass:
    WARRIOR = "warrior"
    MAGE = "mage"
    ROGUE = "rogue"
    HUNTRESS = "huntress"


class Effect(BaseModel):
    # A generic active buff/debuff, mirroring SPD's Buff + BuffIndicator. `icon`
    # is the index into the buffs.png icon sheet (see BuffIndicator constants).
    key: str
    name: str
    icon: int
    remaining: float = 0.0
    duration: float = 0.0

class DropEntry(BaseModel):
    item_kind: str
    chance: float
    max_global: int = 0

class WeightedCountDrop(BaseModel):
    # Mirrors SPD's Random.chances({...}) weighted pick: weights[i] is the
    # relative weight of dropping (base_count + i) copies of item_kind.
    item_kind: str
    weights: List[float]
    base_count: int = 0
    max_global: int = 0

class Mob(Entity):
    type: str = EntityType.MOB
    faction: str = Faction.DUNGEON
    ai_state: str = "idle"
    target_id: Optional[str] = None
    difficulty: str = Difficulty.NORMAL
    exp: int = 1
    loot_table: List[DropEntry] = Field(default_factory=list)
    weighted_drops: List[WeightedCountDrop] = Field(default_factory=list)
    flying: bool = False
    properties: List[str] = Field(default_factory=list)
    attack_range: int = 1
    # Attack speed is an independent property from movement `speed` (mirrors SPD,
    # where a mob's attackDelay and moveSpeed are separate). Baselined to the
    # player's standard weapon cadence so a basic mob trades blow-for-blow rather
    # than landing several hits between player swings. Faster movers (e.g. Crab,
    # speed=2.0) still chase quicker but attack at this normal rate.
    attack_cooldown: float = 3.0
    # Delay before a mob's FIRST strike after reaching its target, so the player
    # gets a beat to react on contact rather than being hit instantly. `engaged`
    # is runtime state tracking whether the mob is currently in attack range (used
    # to arm the windup once per engagement); see GameInstance.update_tick.
    aggro_windup: float = 1.0
    engaged: bool = False
    # Summoned ally (e.g. Rogue's Shadow Clone): the owning player's id and the
    # remaining real-time lifespan in seconds (0 = permanent until killed).
    owner_id: Optional[str] = None
    summon_lifespan: float = 0.0

    def die(self, attacker=None, floor_mobs=None, tile_x=0, tile_y=0, players=None):
        pass

class Player(Entity):
    type: str = EntityType.PLAYER
    faction: str = Faction.PLAYER
    class_type: str = CharacterClass.WARRIOR # Default
    experience: int = 0
    level: int = 1
    active_effects: List[Effect] = []
    floor_id: int = 1
    strength: int = 10
    belongings: Belongings = Field(default_factory=Belongings)
    quickslot: QuickSlot = Field(default_factory=QuickSlot)
    gold: int = 0
    energy: int = 0
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
    # Throttles the passive +10/s healing while standing in a floor's entrance room.
    room_heal_cooldown: int = 0
    # Elixir of Aquatic Rejuvenation healing pool (SPD AquaHealing buff): heals
    # max(1, maxHP/50) per turn while standing in water, until exhausted.
    aqua_heal_left: float = 0.0
    path_queue: List[Tuple[int, int]] = []
    move_intent: Optional[Tuple[int, int]] = None
    last_auto_move_time: float = 0.0
    is_admin: bool = False

    # Subclass and talents
    subclass_info: SubclassInfo = Field(default_factory=SubclassInfo)

    # Berserker rage (0.0 – 1.0 + endless_rage bonus)
    berserk_power: float = 0.0
    berserk_active: bool = False
    berserk_cooldown: int = 0
    # Rampage (warrior T4 berserker): kill-stack damage bonus
    rampage_stacks: int = 0
    # Last action type (for followup strike tracking)
    _last_action: str = ""

    # Gladiator combo
    combo_count: int = 0
    combo_timer: float = 0.0
    combo_max: int = 10  # enhanced by talents

    # Armor ability charge (0–100, shared resource for Leap/Shockwave/Endure)
    armor_charge: int = 0

    # Armor ability selected by player (Leap/Shockwave/Endure), set via talent
    armor_ability: str = ""

    # Broken Seal was affixed to armor (permanently consumed)
    seal_affixed: bool = False

    # --- Rogue ----------------------------------------------------------------
    # Cloak of Shadows sustained stealth: while active the hero is invisible and
    # the cloak bleeds charge (see tick.py). `_cloak_drain_accum` accumulates
    # real seconds toward the next charge drain; `_cloak_recharge_accum` toward
    # the next regenerated charge while not stealthed.
    # Hunger: 0=full, 300=hungry warning, 450=starving (takes damage)
    hunger: float = 0.0

    cloak_stealth_active: bool = False
    _cloak_drain_accum: float = 0.0
    _cloak_recharge_accum: float = 0.0
    # Assassin Preparation: real seconds spent invisible this stealth window.
    # Drives the surprise damage tier / KO threshold / blink range (see combat).
    prep_seconds: float = 0.0
    # Freerunner Momentum: stacks build per move and decay while standing still;
    # spending them grants a short freerun (speed + evasion).
    momentum_stacks: int = 0
    _momentum_decay_accum: float = 0.0
    freerun_seconds: float = 0.0

    @property
    def talent_info(self):
        return self.subclass_info.talent_info

    # Backward-compat views over Belongings so existing engine/UI code and the
    # current front-end snapshot keep working until the SPD-style UI lands.
    # `inventory` returns the live backpack list, so .append/.pop/.remove still
    # mutate the real store; rebind sites (= []) were migrated to belongings.
    @computed_field
    @property
    def inventory(self) -> List[AnyItem]:
        return self.belongings.backpack.items

    @computed_field
    @property
    def equipped_weapon(self) -> Optional[AnyItem]:
        return self.belongings.weapon

    @computed_field
    @property
    def equipped_wearable(self) -> Optional[AnyItem]:
        return self.belongings.armor

    def take_damage(self, amount: int):
        if self.is_admin:
            return 0
        if self.is_downed:
            return 0

        # Enraged Catalyst (warrior T2 berserker): gain berserk power on damage taken
        if self.subclass_info.subclass == "berserker":
            ec = self.subclass_info.talent_info.level("enraged_catalyst")
            if ec > 0:
                from app.engine.entities.buffs import add_buff as _add_buff
                endless_level = self.subclass_info.talent_info.level("endless_rage")
                max_power = 1.0 + 0.1667 * endless_level
                power_gain = (amount / max(self.get_total_max_hp() * 4, 1)) * (1 + ec * 0.5)
                self.berserk_power = min(max_power, self.berserk_power + power_gain)

        self.hp -= amount
        if self.hp <= 0:
            self.hp = 0
            self.is_downed = True
            self.is_alive = False
        return max(0, amount)

    def get_total_attack(self) -> int:
        w = self.belongings.weapon
        bonus = w.damage if isinstance(w, KindOfWeapon) else 0
        return self.attack + bonus

    def get_damage_min(self) -> int:
        w = self.belongings.weapon
        if isinstance(w, MeleeWeapon):
            base = w.dmg_min(w.level)
        elif isinstance(w, KindOfWeapon):
            base = w.damage
        else:
            base = self.damage_min
        if self.subclass_info.subclass is not None:
            base += self.subclass_info.talent_info.level("sub_atk")
        return base

    def get_damage_max(self) -> int:
        w = self.belongings.weapon
        if isinstance(w, MeleeWeapon):
            base = w.dmg_max(w.level)
        elif isinstance(w, KindOfWeapon):
            base = w.damage
        else:
            base = self.damage_max
        if self.subclass_info.subclass is not None:
            base += self.subclass_info.talent_info.level("sub_atk")
        return base

    def get_surprise_damage_floor(self) -> float:
        w = self.belongings.weapon
        if isinstance(w, KindOfWeapon):
            return w.surprise_damage_floor
        return 0.0

    def get_dr_min(self) -> int:
        a = self.belongings.armor
        if a is not None and isinstance(a, Armor):
            base = a.dr_min(a.level)
            deficit = max(0, a.strength_requirement - self.strength)
            # Light Armor (warrior T1): reduce STR penalty
            la = self.subclass_info.talent_info.level("light_armor")
            if la > 0:
                deficit = max(0, deficit - la)
            return max(0, base - 2 * deficit)
        return 0

    def get_dr_max(self) -> int:
        a = self.belongings.armor
        if a is not None and isinstance(a, Armor):
            base = a.dr_max(a.level)
            deficit = max(0, a.strength_requirement - self.strength)
            la = self.subclass_info.talent_info.level("light_armor")
            if la > 0:
                deficit = max(0, deficit - la)
            return max(0, base - 2 * deficit)
        return 0

    def get_effective_defense_skill(self) -> int:
        base = self.defense_skill
        a = self.belongings.armor
        if a is not None:
            deficit = max(0, a.strength_requirement - self.strength)
            # Light Armor (warrior T1): reduce STR penalty
            la = self.subclass_info.talent_info.level("light_armor")
            if la > 0:
                deficit = max(0, deficit - la)
            if deficit > 0:
                base = int(base / (1.5 ** deficit))
        # Sub-Def (warrior T3): flat +2 per point if subclass chosen
        if self.subclass_info.subclass is not None:
            base += 2 * self.subclass_info.talent_info.level("sub_def")
        return base

    def set_heal(self, amount: float, percent_per_tick: float, flat_per_tick: float):
        # Multiple healing sources don't stack; they combine the best of each
        # property (mirrors Healing.setHeal in the original game).
        self.heal_left = max(self.heal_left, amount)
        self.heal_pct_per_tick = max(self.heal_pct_per_tick, percent_per_tick)
        self.heal_flat_per_tick = max(self.heal_flat_per_tick, flat_per_tick)
        self.heal_cooldown = 0  # first tick applies immediately

    def get_view_distance(self) -> int:
        base = self.view_distance
        fs = self.subclass_info.talent_info.level("farsight")
        if fs > 0:
            base += fs * 2
        return base

    def get_total_max_hp(self) -> int:
        return self.max_hp

    def add_to_inventory(self, item: ItemBase) -> bool:
        ok = self.belongings.backpack.collect(item)
        if ok:
            self.quickslot.replace_placeholder(item)
        return ok

    def equip_item(self, item_id: str) -> bool:
        item = self.belongings.backpack.find(item_id)
        if item is None or not isinstance(item, EquipableItem):
            return False
        slot = self.belongings.slot_name_for(item)
        if slot is None:
            return False
        self.belongings.backpack.detach_all(item_id)
        prev = getattr(self.belongings, slot)
        setattr(self.belongings, slot, item)
        if prev is not None:
            self.belongings.backpack.collect(prev)
        return True

    def unequip_item(self, item_id: str) -> bool:
        for slot in ("weapon", "armor", "artifact", "misc", "ring"):
            cur = getattr(self.belongings, slot)
            if cur is not None and cur.id == item_id:
                if cur.cursed and cur.cursed_known:
                    return False  # cursed gear can't be removed (SPD)
                if not self.belongings.backpack.can_hold(cur):
                    return False
                setattr(self.belongings, slot, None)
                self.belongings.backpack.collect(cur)
                return True
        return False

    def get_talent_damage_bonus(self) -> float:
        """Return a flat damage bonus from talents (added to damage roll)."""
        bonus = 0

        # Rampage (warrior T4 berserker): +1 damage per stack
        if self.subclass_info.subclass == "berserker":
            bonus += self.rampage_stacks

        return bonus

    def attack_proc(self, target) -> None:
        if self.subclass_info.subclass == "berserker":
            from app.engine.entities.buffs import add_buff
            endless_level = self.subclass_info.talent_info.level("endless_rage")
            max_power = 1.0 + 0.1667 * endless_level
            power_gain = 0.05
            self.berserk_power = min(max_power, self.berserk_power + power_gain)
            # Rampage: decaying stack gain
            if self.rampage_stacks > 0:
                self.rampage_stacks = max(0, self.rampage_stacks - 1)
        if self.subclass_info.subclass == "gladiator":
            # Combo cap from talents
            self.combo_max = 10
            ec = self.subclass_info.talent_info.level("enhanced_combo")
            if ec > 0:
                self.combo_max += 2 * ec
            sc = self.subclass_info.talent_info.level("savage_capacity")
            if sc > 0:
                self.combo_max += 2 * sc
            self.combo_count = min(self.combo_count + 1, self.combo_max)
            self.combo_timer = 5.0
            # Combo Shield (gladiator T2): shield per combo
            cs = self.subclass_info.talent_info.level("combo_shield")
            if cs > 0 and self.combo_count >= 3:
                shield_amt = cs * (self.combo_count // 3)
                if shield_amt > 0:
                    self.add_shield("combo_shield", shield_amt, priority=1, decay=600)

    def defense_proc(self, raw_damage: int, attacker, floor_mobs: dict, tile_x: int, tile_y: int) -> int:
        from app.engine.entities.buffs import has_buff
        if has_buff(self.buffs, "endure"):
            raw_damage = max(0, raw_damage - int(raw_damage * 0.3))

        # Iron Will (warrior T1): DR based on missing HP%
        iw = self.subclass_info.talent_info.level("iron_will")
        if iw > 0:
            hp_ratio = self.hp / max(self.get_total_max_hp(), 1)
            dr_pct = iw * 0.05 * (1 - hp_ratio)
            raw_damage = max(0, raw_damage - int(raw_damage * dr_pct))

        # Protective Shadows (rogue T1): DR while invisible
        ps = self.subclass_info.talent_info.level("protective_shadows")
        if ps > 0 and self.invisible > 0:
            dr_pct = 0.08 * ps
            raw_damage = max(0, raw_damage - int(raw_damage * dr_pct))

        return raw_damage

    MAX_LEVEL: ClassVar[int] = 30

    def max_exp(self) -> int:
        # Mirrors Hero.maxExp(lvl) = 5 + lvl*5 in the original game.
        return 5 + self.level * 5

    def earn_exp(self, amount: int) -> bool:
        # Award experience and apply any level-ups. Mirrors Hero.earnExp + updateHT:
        # each level grants +5 max HP and heals that gain. Returns True if at
        # least one level-up occurred (used to emit a LEVEL_UP event).
        if amount <= 0 or self.level >= self.MAX_LEVEL:
            return False
        self.experience += amount
        leveled_up = False
        while self.experience >= self.max_exp() and self.level < self.MAX_LEVEL:
            self.experience -= self.max_exp()
            self.level += 1
            self.max_hp += 5
            self.hp += 5
            self.attack_skill += 1
            self.defense_skill += 1
            leveled_up = True
        if self.level >= self.MAX_LEVEL:
            self.experience = 0
        return leveled_up


# Legacy aliases — keep existing imports/constructors working during migration.
Item = ItemBase
Weapon = MeleeWeapon
Wearable = Armor
