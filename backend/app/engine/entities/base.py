from __future__ import annotations

import uuid as _uuid
from typing import Annotated, ClassVar, Literal, Optional, List, Dict, Tuple, Union

from pydantic import BaseModel, Field, computed_field


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

    # --- behaviour ---------------------------------------------------------
    def actions(self, player: Optional["Player"] = None) -> List[str]:
        # SPD's Item.actions defaults to DROP + THROW for everything.
        return [Action.THROW, Action.DROP]

    def default_action(self) -> Optional[str]:
        return None

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


class KindOfWeapon(EquipableItem):
    type: str = "weapon"
    category: ClassVar[str] = ItemCategory.WEAPON
    damage: int = 1
    range: int = 1
    attack_cooldown: float = 1.0
    enchantment: Optional[str] = None
    projectile_type: Optional[str] = None


class MeleeWeapon(KindOfWeapon):
    kind: Literal["melee_weapon"] = "melee_weapon"


class Bow(KindOfWeapon):
    kind: Literal["bow"] = "bow"
    name: str = "Bow"
    range: int = 6
    projectile_type: str = "arrow"


class Staff(KindOfWeapon):
    kind: Literal["staff"] = "staff"
    name: str = "Staff"
    range: int = 4
    magic_damage: int = 0
    charges: int = 4
    projectile_type: str = "magic_bolt"


class MissileWeapon(KindOfWeapon):
    kind: Literal["missile_weapon"] = "missile_weapon"
    stackable: ClassVar[bool] = True

    def default_action(self) -> Optional[str]:
        return Action.THROW


class Armor(EquipableItem):
    kind: Literal["armor"] = "armor"
    type: str = "wearable"
    category: ClassVar[str] = ItemCategory.ARMOR
    health_boost: int = 0
    defense_bonus: int = 0


class KindofMisc(EquipableItem):
    pass


class Ring(KindofMisc):
    kind: Literal["ring"] = "ring"
    type: str = "ring"
    category: ClassVar[str] = ItemCategory.RING


class Artifact(KindofMisc):
    kind: Literal["artifact"] = "artifact"
    type: str = "artifact"
    category: ClassVar[str] = ItemCategory.ARTIFACT
    charge: int = 0
    charge_cap: int = 100


class Wand(ItemBase):
    kind: Literal["wand"] = "wand"
    type: str = "wand"
    category: ClassVar[str] = ItemCategory.WAND
    damage: int = 0
    charges: int = 2
    max_charges: int = 2
    range: int = 4
    projectile_type: str = "magic_bolt"

    def actions(self, player: Optional["Player"] = None) -> List[str]:
        return [Action.ZAP] + super().actions(player)

    def default_action(self) -> Optional[str]:
        return Action.ZAP


class Potion(ItemBase):
    kind: Literal["potion"] = "potion"
    type: str = "potion"
    category: ClassVar[str] = ItemCategory.POTION
    stackable: ClassVar[bool] = True
    effect: str = ""

    def actions(self, player: Optional["Player"] = None) -> List[str]:
        return [Action.DRINK] + super().actions(player)

    def default_action(self) -> Optional[str]:
        return Action.DRINK


class HealthPotion(Potion):
    kind: Literal["health_potion"] = "health_potion"
    name: str = "Health Potion"
    effect: str = "regen"


class RevivingPotion(Potion):
    kind: Literal["reviving_potion"] = "reviving_potion"
    name: str = "Reviving Potion"
    effect: str = "revive"


class Scroll(ItemBase):
    kind: Literal["scroll"] = "scroll"
    type: str = "scroll"
    category: ClassVar[str] = ItemCategory.SCROLL
    stackable: ClassVar[bool] = True

    def actions(self, player: Optional["Player"] = None) -> List[str]:
        return [Action.READ] + super().actions(player)

    def default_action(self) -> Optional[str]:
        return Action.READ


class Gold(ItemBase):
    kind: Literal["gold"] = "gold"
    type: str = "gold"
    category: ClassVar[str] = ItemCategory.GOLD
    stackable: ClassVar[bool] = True


class Food(ItemBase):
    kind: Literal["food"] = "food"
    type: str = "food"
    category: ClassVar[str] = ItemCategory.FOOD
    stackable: ClassVar[bool] = True

    def default_action(self) -> Optional[str]:
        return Action.EAT


class Key(ItemBase):
    kind: Literal["key"] = "key"
    type: str = "key"
    category: ClassVar[str] = ItemCategory.KEY
    key_id: str = ""


class Throwable(ItemBase):
    kind: Literal["throwable"] = "throwable"
    type: str = "throwable"
    category: ClassVar[str] = ItemCategory.STONE
    damage: int = 1
    range: int = 5
    consumable: bool = True
    projectile_type: str = "users_projectile"

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
        MeleeWeapon, Bow, Staff, MissileWeapon,
        Armor, Ring, Artifact, Wand,
        HealthPotion, RevivingPotion, Potion, Scroll, Gold, Food, Key,
        Stone, Boomerang, ThrowableDagger, Throwable,
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

class Mob(Entity):
    type: str = EntityType.MOB
    faction: str = Faction.DUNGEON
    ai_state: str = "idle"
    target_id: Optional[str] = None
    difficulty: str = Difficulty.NORMAL
    # Experience awarded to the killer, mirroring Mob.EXP in the original game.
    exp: int = 1

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
    last_auto_move_time: float = 0.0
    is_admin: bool = False

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
        w = self.belongings.weapon
        bonus = w.damage if isinstance(w, KindOfWeapon) else 0
        return self.attack + bonus

    def get_total_defense(self) -> int:
        a = self.belongings.armor
        bonus = getattr(a, "defense_bonus", 0) if a is not None else 0
        return self.defense + bonus

    def set_heal(self, amount: float, percent_per_tick: float, flat_per_tick: float):
        # Multiple healing sources don't stack; they combine the best of each
        # property (mirrors Healing.setHeal in the original game).
        self.heal_left = max(self.heal_left, amount)
        self.heal_pct_per_tick = max(self.heal_pct_per_tick, percent_per_tick)
        self.heal_flat_per_tick = max(self.heal_flat_per_tick, flat_per_tick)
        self.heal_cooldown = 0  # first tick applies immediately

    def get_total_max_hp(self) -> int:
        a = self.belongings.armor
        bonus = getattr(a, "health_boost", 0) if a is not None else 0
        return self.max_hp + bonus

    def add_to_inventory(self, item: ItemBase) -> bool:
        ok = self.belongings.backpack.collect(item)
        if ok:
            self.quickslot.replace_placeholder(item)
        return ok

    def equip_item(self, item_id: str) -> bool:
        item = self.belongings.backpack.find(item_id)
        if item is None or not isinstance(item, EquipableItem):
            return False
        if self.strength < item.strength_requirement:
            return False
        slot = self.belongings.slot_name_for(item)
        if slot is None:
            return False
        self.belongings.backpack.detach_all(item_id)
        prev = getattr(self.belongings, slot)
        setattr(self.belongings, slot, item)
        if prev is not None:
            self.belongings.backpack.collect(prev)
        if slot == "armor" and self.hp > self.get_total_max_hp():
            self.hp = self.get_total_max_hp()
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
                if slot == "armor" and self.hp > self.get_total_max_hp():
                    self.hp = self.get_total_max_hp()
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
            leveled_up = True
        if self.level >= self.MAX_LEVEL:
            self.experience = 0
        return leveled_up


# Legacy aliases — keep existing imports/constructors working during migration.
Item = ItemBase
Weapon = MeleeWeapon
Wearable = Armor
