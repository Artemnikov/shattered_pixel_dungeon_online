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
    ooze_amount: int = 0

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

# Actions that require the player to pick a target cell before resolving.
TARGETED_ACTIONS = {Action.THROW, Action.ZAP}


def _new_id() -> str:
    return str(_uuid.uuid4())


class ItemBase(BaseModel):
    # `kind` is the polymorphic discriminator (overridden as a Literal in each
    # concrete leaf). `type` is the legacy front-end category string kept for
    # backward-compat until the SPD-style UI lands.
    kind: Literal["item"] = "item"
    id: str
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


class MeleeWeapon(KindOfWeapon):
    kind: Literal["melee_weapon"] = "melee_weapon"
    DESC: ClassVar[str] = "A reliable melee weapon. Equip it to strike enemies in close combat."


class Dagger(MeleeWeapon):
    kind: Literal["dagger"] = "dagger"
    name: str = "Dagger"
    damage: int = 2
    attack_cooldown: float = 1.5
    strength_requirement: int = 9
    surprise_damage_floor: float = 0.75
    DESC: ClassVar[str] = "A quick dagger. Surprise attacks deal more consistent damage."


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
    stackable: ClassVar[bool] = True
    DESC: ClassVar[str] = "A thrown weapon. Hurl it at an enemy from afar."

    def default_action(self) -> Optional[str]:
        return Action.THROW


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


class KindofMisc(EquipableItem):
    pass


class Ring(KindofMisc):
    kind: Literal["ring"] = "ring"
    type: str = "ring"
    category: ClassVar[str] = ItemCategory.RING
    DESC: ClassVar[str] = "A magical ring that grants a passive bonus while worn."


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
        return [f"It currently holds {self.charges} of {self.max_charges} charges."]


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
    DESC: ClassVar[str] = "Edible provisions. Eat it to stave off hunger."

    def default_action(self) -> Optional[str]:
        return Action.EAT


class Key(ItemBase):
    kind: Literal["key"] = "key"
    type: str = "key"
    category: ClassVar[str] = ItemCategory.KEY
    key_id: str = ""
    DESC: ClassVar[str] = "A key that unlocks a matching door or chest somewhere on this floor."


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


class Boomerang(Throwable):
    kind: Literal["boomerang"] = "boomerang"
    name: str = "Boomerang"
    damage: int = 3
    range: int = 6
    consumable: bool = False
    projectile_type: str = "boomerang"


class ThrowableDagger(Throwable):
    kind: Literal["throwable_dagger"] = "throwable_dagger"
    name: str = "Throwable Dagger"
    damage: int = 4
    range: int = 4
    consumable: bool = True
    projectile_type: str = "dagger"


class Seed(ItemBase):
    kind: Literal["seed"] = "seed"
    type: str = "seed"
    category: ClassVar[str] = ItemCategory.SEED
    stackable: ClassVar[bool] = True
    plant_type: str = "sungrass"
    DESC: ClassVar[str] = "A magical seed. Plant it to release its effect."


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


class Berry(Food):
    kind: Literal["berry"] = "berry"
    name: str = "Berry"
    DESC: ClassVar[str] = "A sweet berry. Restores a small amount of food."


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


class ScrollHolder(Bag):
    kind: Literal["scroll_holder"] = "scroll_holder"
    name: str = "Scroll Holder"
    accepts: ClassVar[Optional[set]] = {ItemCategory.SCROLL}


class MagicalHolster(Bag):
    kind: Literal["magical_holster"] = "magical_holster"
    name: str = "Magical Holster"
    accepts: ClassVar[Optional[set]] = {ItemCategory.WAND, ItemCategory.STONE}


class PotionBandolier(Bag):
    kind: Literal["potion_bandolier"] = "potion_bandolier"
    name: str = "Potion Bandolier"
    accepts: ClassVar[Optional[set]] = {ItemCategory.POTION}


# Discriminated union of everything that can live inside a Bag / equip slot.
# Keyed by `kind`, so member order is irrelevant and nested items serialize as
# their concrete type. Server never validates inbound items, so this exists only
# for clean outbound dumps + a stable client contract.
AnyItem = Annotated[
    Union[
        MeleeWeapon, Dagger, Bow, Staff, MissileWeapon,
        Armor, Ring, Artifact, Wand,
        HealthPotion, RevivingPotion, FuryPotion, Potion, Scroll, Gold, Food, MysteryMeat, Berry, Key,
        Seed, Dewdrop, Stone, Boomerang, ThrowableDagger, Throwable,
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

class Mob(Entity):
    type: str = EntityType.MOB
    faction: str = Faction.DUNGEON
    ai_state: str = "idle"
    target_id: Optional[str] = None
    difficulty: str = Difficulty.NORMAL
    exp: int = 1
    loot_table: List[DropEntry] = Field(default_factory=list)
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
    path_queue: List[Tuple[int, int]] = []
    # Held keyboard direction; the update tick steps the player at AUTO_MOVE_INTERVAL
    # while this is set, mirroring tap-to-path pacing. None when no key is held.
    move_intent: Optional[Tuple[int, int]] = None
    last_auto_move_time: float = 0.0
    is_admin: bool = False

    # Subclass and talents
    subclass_info: SubclassInfo = Field(default_factory=SubclassInfo)

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
        if isinstance(w, KindOfWeapon):
            return w.damage
        return self.damage_min

    def get_damage_max(self) -> int:
        w = self.belongings.weapon
        if isinstance(w, KindOfWeapon):
            return w.damage
        return self.damage_max

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
            return max(0, base - 2 * deficit)
        return 0

    def get_dr_max(self) -> int:
        a = self.belongings.armor
        if a is not None and isinstance(a, Armor):
            base = a.dr_max(a.level)
            deficit = max(0, a.strength_requirement - self.strength)
            return max(0, base - 2 * deficit)
        return 0

    def get_effective_defense_skill(self) -> int:
        a = self.belongings.armor
        if a is not None:
            deficit = max(0, a.strength_requirement - self.strength)
            if deficit > 0:
                return int(self.defense_skill / (1.5 ** deficit))
        return self.defense_skill

    def set_heal(self, amount: float, percent_per_tick: float, flat_per_tick: float):
        # Multiple healing sources don't stack; they combine the best of each
        # property (mirrors Healing.setHeal in the original game).
        self.heal_left = max(self.heal_left, amount)
        self.heal_pct_per_tick = max(self.heal_pct_per_tick, percent_per_tick)
        self.heal_flat_per_tick = max(self.heal_flat_per_tick, flat_per_tick)
        self.heal_cooldown = 0  # first tick applies immediately

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
