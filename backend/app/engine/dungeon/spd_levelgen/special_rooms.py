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
"""Port of concrete SpecialRoom/SecretRoom subclasses
(rooms/special/*.java, rooms/secret/*.java) -- sizing overrides only.

Only `min/max_width/height` matter for layout-RNG parity (they gate the
`set_size` -> `NormalIntRange` draw bounds); `paint()` is stubbed and
deferred to the Painter phase (Task #4) like the other room types."""

from __future__ import annotations

from app.engine.dungeon.spd_levelgen import terrain
from app.engine.dungeon.spd_levelgen.geom import Point, gate
from app.engine.dungeon.spd_levelgen.painter import Painter
from app.engine.dungeon.spd_levelgen.room import DoorType
from app.engine.dungeon.spd_levelgen.room_types import SecretRoom, SpecialRoom
from app.engine.dungeon.spd_levelgen.standard_rooms import EmptyRoom
from app.engine.dungeon.spd_random import SPDRandom

# IronKey descriptor -- distinguishable from other empty-frozenset placeholders
# (SPAWN_FOOD/SPAWN_STYLUS/etc.) so the adapter can spawn a real Key item.
# "IronKey" is never a findPrizeItem match-target, so this label is safe.
_IRON_KEY = frozenset({"IronKey"})


def _stub_paint(self, level, rng) -> None:
    Painter.fill(level, self, terrain.WALL)
    Painter.fill(level, self, 1, terrain.EMPTY)
    self.entrance().set(DoorType.REGULAR)


# Generator.floorSetTierProbs (Generator.java:613-619) -- weighted pick of a
# weapon/missile tier (T1-T5) based on `Dungeon.depth / 5`, gated [0,4].
_FLOOR_SET_TIER_PROBS = (
    (0.0, 75.0, 20.0, 4.0, 1.0),
    (0.0, 25.0, 50.0, 20.0, 5.0),
    (0.0, 0.0, 40.0, 50.0, 10.0),
    (0.0, 0.0, 20.0, 40.0, 40.0),
    (0.0, 0.0, 0.0, 20.0, 80.0),
)

# Weapon.Enchantment.{common,uncommon,rare} array sizes (Weapon.java:515-529) --
# Enchantment.random() -> Random.chances(typeChances) selects a rarity tier,
# then Random.element(<tier array>) -> Random.Int(<tier size>). Identity is
# irrelevant for layout-parity; only array length matters for the Int() draw.
_ENCHANT_TYPE_CHANCES = (50.0, 40.0, 10.0)
_ENCHANT_TIER_SIZES = (4, 6, 3)  # common, uncommon, rare


def _consume_random_equipment_floorset(rng: SPDRandom, floor_set: int) -> None:
    """Shared outer-sequence draw shape for Generator.randomWeapon(floorSet)
    and Generator.randomArmor(floorSet):
      1. Random.chances(floorSetTierProbs[gated floorSet]) -- selects the
         tier/class index (deck-backed for weapons -- push/pop is invisible
         to the parent -- and a direct array index for armor; either way
         it's exactly one outer chances() draw)
      2. The resulting MeleeWeapon/Armor instance's .random(): Int(4),
         conditionally Int(5), then Random.Long() to seed
         Random.pushGenerator() (contents invisible to the parent).
    Identity is irrelevant for layout-parity -- only the draw shape matters."""
    floor_set = int(gate(0, floor_set, len(_FLOOR_SET_TIER_PROBS) - 1))
    rng.chances(_FLOOR_SET_TIER_PROBS[floor_set])

    if rng.IntMax(4) == 0:
        rng.IntMax(5)
    rng.Long()  # Random.pushGenerator(Random.Long()) -- seed draw only; contents skipped


def _consume_generator_random_weapon(rng: SPDRandom, depth: int) -> None:
    """Port of Generator.randomWeapon()/randomWeapon(floorSet, false) ->
    Generator.random(WEP_Tn) -> Weapon.random()'s RNG draws against the
    OUTER (levelgen) sequence.

    Generator.random(Category) for deck-backed categories (WEP_T1-5) pushes
    a seeded sub-generator (`Random.pushGenerator(cat.seed)`, zero parent
    draws -- pure construction) and does ALL of its chances/skip-ahead work
    there before popping -- so from the parent's perspective those draws are
    invisible. Only `Random.chances(floorSetTierProbs[floorSet])` (selecting
    the tier, outside the push/pop) and `Weapon.random()` (called on the
    POPPED/outer generator, since popGenerator() runs before `.random()`)
    are real outer-sequence draws. The exotic-substitution check
    (`ExoticPotion/ScrollOfTransmutation.regToExo`) never matches a weapon
    class, so it draws nothing."""
    _consume_random_equipment_floorset(rng, depth // 5)


def _consume_generator_random_scroll(rng: SPDRandom) -> None:
    """Port of Generator.random(Category.SCROLL)'s OUTER-sequence draw.

    The deck push/pop and internal chances() picks are invisible to the
    parent (pure-construction sub-generator, per the WEAPON precedent). But
    *every* class in SCROLL.classes (including ScrollOfUpgrade) has an entry
    in ExoticScroll.regToExo, so the post-pop
    `if (regToExo.containsKey(itemCls)) if (Random.Float() < ...)` exotic
    check ALWAYS evaluates its Random.Float() against the outer generator,
    regardless of which scroll class was picked."""
    rng.Float()


def _consume_enchantment_random(rng: SPDRandom) -> None:
    """Port of Weapon.Enchantment.random() -- Random.chances(typeChances)
    picks a rarity tier, then Random.element(<tier array>) consumes
    Random.Int(<tier size>). Identity irrelevant for layout-parity."""
    tier = rng.chances(_ENCHANT_TYPE_CHANCES)
    rng.IntMax(_ENCHANT_TIER_SIZES[tier])


def _consume_statue_random(rng: SPDRandom, depth: int) -> None:
    """Port of Statue.random()/createWeapon(true) + the
    `weapon.enchant(Enchantment.random())` overwrite in StatueRoom.paint --
    the full RNG sequence Statue.random() draws against the levelgen
    generator (Statue.pos assignment and mob registration are zero-RNG,
    out of layout-parity scope)."""
    rng.Float()  # altChance roll (ArmoredStatue vs Statue) -- always consumed
    _consume_generator_random_weapon(rng, depth)
    _consume_enchantment_random(rng)


def _runestone_prize(level, rng: SPDRandom):
    """Port of RunestoneRoom.prize() -- findPrizeItem(Class) is a deterministic
    linear scan (no RNG); Generator.random(Category.STONE) is a deck-backed
    default-branch pick (Runestone.random() is the zero-RNG Item base no-op,
    and Runestone is never an Exotic{Potion,Scroll} substitution target) --
    so the whole fallback consumes zero RNG. Identity irrelevant."""
    prize = level.find_prize_item(rng, "TrinketCatalyst")
    if prize is None:
        prize = level.find_prize_item(rng, "Runestone")
        if prize is None:
            prize = frozenset()
    return prize


def _traps_room_prize(level, rng: SPDRandom, depth: int):
    """Port of TrapsRoom.prize(). findPrizeItem() (no-arg, may consume
    rng.IntMax(len(itemsToSpawn)) -- see GenLevel.find_prize_item) returns
    early 67% of the time if non-null. Otherwise: Int(2) branch selector,
    then randomWeapon/randomArmor(floorSet+1) (identical outer-draw shape --
    see _consume_random_equipment_floorset), then cursed/cursedKnown
    assignment (zero-RNG), then a 33% upgrade roll whose Item.upgrade() is
    zero-RNG for these fresh sub-level-4 items (enchantHardened/glyphHardened
    start false, hasCurseEnchant/hasCurseGlyph already cleared above, and
    level() < 4 so the loss-chance branches never evaluate their Float(10))."""
    if rng.IntMax(3) != 0:
        prize = level.find_prize_item(rng)
        if prize is not None:
            return prize
    rng.IntMax(2)  # weapon-vs-armor branch selector -- both consume the same shape
    _consume_random_equipment_floorset(rng, depth // 5 + 1)
    rng.IntMax(3)  # upgrade roll -- Item.upgrade() is zero-RNG here, see above
    return frozenset()


def _library_room_prize(level, rng: SPDRandom):
    """Port of LibraryRoom.prize() -- findPrizeItem(Class) is RNG-free;
    Generator.random(Category.SCROLL)'s only outer-sequence draw is the
    always-fires exotic-substitution roll (_consume_generator_random_scroll)."""
    prize = level.find_prize_item(rng, "TrinketCatalyst")
    if prize is None:
        prize = level.find_prize_item(rng, "Scroll")
        if prize is None:
            _consume_generator_random_scroll(rng)
            prize = frozenset()
    return prize


def _consume_gold_random(rng: SPDRandom, depth: int) -> None:
    """Port of `new Gold().random()`'s RNG draw (Gold.java:91 --
    `quantity = Random.IntRange(30 + Dungeon.depth*10, 60 + Dungeon.depth*20)`).
    Item identity/quantity is out of layout-parity scope (level.drop is
    zero-RNG and omitted), but the roll itself must still be consumed."""
    rng.IntRange(30 + depth * 10, 60 + depth * 20)


def _consumable_prize(level, rng: SPDRandom, depth: int):
    if rng.IntMax(3) != 0:
        prize = level.find_prize_item(rng)
        if prize is not None:
            return prize
    cat_idx = rng.IntMax(4)
    if cat_idx == 0 or cat_idx == 1:
        rng.Float()
    elif cat_idx == 3:
        rng.chances([1.0])
        _consume_gold_random(rng, depth)
    return frozenset()


def _pit_room_prize(rng: SPDRandom, depth: int):
    cat_idx = rng.IntMax(4)
    if cat_idx == 0 or cat_idx == 1:
        rng.Float()
    elif cat_idx == 3:
        rng.chances([1.0])
        _consume_gold_random(rng, depth)
    return frozenset()


def _laboratory_prize(level, rng: SPDRandom):
    prize = level.find_prize_item(rng, "TrinketCatalyst")
    if prize is None:
        prize = level.find_prize_item(rng, "PotionOfStrength")
        if prize is None:
            oneof_idx = rng.IntMax(2)
            if oneof_idx == 0:
                rng.Float()
            prize = frozenset()
    return prize


SpecialRoom.paint = _stub_paint
SecretRoom.paint = _stub_paint


# -- SpecialRoom subclasses (rooms/special/*.java) -------------------------

class WeakFloorRoom(SpecialRoom):
    def paint(self, level, rng: SPDRandom) -> None:
        Painter.fill(level, self, terrain.WALL)
        Painter.fill(level, self, 1, terrain.CHASM)

        door = self.entrance()
        door.set(DoorType.REGULAR)

        well = None

        if door.x == self.left:
            for i in range(self.top + 1, self.bottom):
                Painter.draw_inside(level, self, Point(self.left, i), rng.IntRange(1, self.width() - 4), terrain.EMPTY_SP)
            well = Point(self.right - 1, self.top + 2 if rng.IntMax(2) == 0 else self.bottom - 1)
        elif door.x == self.right:
            for i in range(self.top + 1, self.bottom):
                Painter.draw_inside(level, self, Point(self.right, i), rng.IntRange(1, self.width() - 4), terrain.EMPTY_SP)
            well = Point(self.left + 1, self.top + 2 if rng.IntMax(2) == 0 else self.bottom - 1)
        elif door.y == self.top:
            for i in range(self.left + 1, self.right):
                Painter.draw_inside(level, self, Point(i, self.top), rng.IntRange(1, self.height() - 4), terrain.EMPTY_SP)
            well = Point(self.left + 1 if rng.IntMax(2) == 0 else self.right - 1, self.bottom - 1)
        elif door.y == self.bottom:
            for i in range(self.left + 1, self.right):
                Painter.draw_inside(level, self, Point(i, self.bottom), rng.IntRange(1, self.height() - 4), terrain.EMPTY_SP)
            well = Point(self.left + 1 if rng.IntMax(2) == 0 else self.right - 1, self.top + 2)

        Painter.set(level, well, terrain.CHASM)
        # HiddenWell CustomTilemap + WellID Blob: runtime-only, zero-RNG, out of layout-parity scope


class CryptRoom(SpecialRoom):
    def paint(self, level, rng: SPDRandom) -> None:
        Painter.fill(level, self, terrain.WALL)
        Painter.fill(level, self, 1, terrain.EMPTY)

        c = self.center(rng)
        cx, cy = c.x, c.y

        entrance = self.entrance()
        entrance.set(DoorType.LOCKED)
        level.add_item_to_spawn(_IRON_KEY)

        if entrance.x == self.left:
            Painter.set(level, self.right - 1, self.top + 1, terrain.STATUE)
            Painter.set(level, self.right - 1, self.bottom - 1, terrain.STATUE)
            cx = self.right - 2
        elif entrance.x == self.right:
            Painter.set(level, self.left + 1, self.top + 1, terrain.STATUE)
            Painter.set(level, self.left + 1, self.bottom - 1, terrain.STATUE)
            cx = self.left + 2
        elif entrance.y == self.top:
            Painter.set(level, self.left + 1, self.bottom - 1, terrain.STATUE)
            Painter.set(level, self.right - 1, self.bottom - 1, terrain.STATUE)
            cy = self.bottom - 2
        elif entrance.y == self.bottom:
            Painter.set(level, self.left + 1, self.top + 1, terrain.STATUE)
            Painter.set(level, self.right - 1, self.top + 1, terrain.STATUE)
            cy = self.top + 2

        level.drop(_crypt_prize(level, rng, level.depth), cx + cy * level.width()).type = "TOMB"


def _crypt_prize(level, rng: SPDRandom, depth: int):
    """Port of CryptRoom.prize() -- Generator.randomArmor(floorSet+1)
    outer draw then Glyph.randomCurse() Int(8)."""
    _consume_random_equipment_floorset(rng, depth // 5 + 1)
    rng.IntMax(8)  # Armor.Glyph.randomCurse() -- Random.element(curses[8]); identity irrelevant
    return frozenset({"Armor"})


def _pool_room_prize(level, rng: SPDRandom, depth: int):
    """Port of PoolRoom.prize() -- findPrizeItem() returns early 33% of the
    time if non-null. Otherwise weapon/missile/armor at floorSet (depth/5)+1
    (identical outer-draw shape -- _consume_random_equipment_floorset covers
    weapon/missile/armor alike, see its docstring); the cursed/cursedKnown
    overwrite and the conditional `enchant(null)`/`inscribe(null)` are
    zero-RNG identity setters (per the cursed/hasCurseEnchant finding); the
    final 33% `prize.upgrade()` is zero-RNG too -- _roll_wam never rolls
    above level 2, so the extra +1 never reaches the >=4 loss-chance branch."""
    if rng.IntMax(3) == 0:
        prize = level.find_prize_item(rng)
        if prize is not None:
            return prize
    rng.IntMax(5)  # weapon (0,1) / missile (2) / armor (3,4) branch selector
    _consume_random_equipment_floorset(rng, depth // 5 + 1)
    rng.IntMax(3)  # extra-upgrade roll -- zero-RNG Item.upgrade() here
    return frozenset()


class PoolRoom(SpecialRoom):
    def min_width(self) -> int:
        return 6

    def min_height(self) -> int:
        return 6

    def paint(self, level, rng: SPDRandom) -> None:
        from app.engine.dungeon.spd_levelgen.mob_spawner import GenMob

        Painter.fill(level, self, terrain.WALL)
        Painter.fill(level, self, 1, terrain.WATER)

        door = self.entrance()
        door.set(DoorType.REGULAR)

        x = y = -1
        if door.x == self.left:
            x = self.right - 1
            y = self.top + self.height() // 2
            Painter.fill(level, self.left + 1, self.top + 1, 1, self.height() - 2, terrain.EMPTY_SP)
        elif door.x == self.right:
            x = self.left + 1
            y = self.top + self.height() // 2
            Painter.fill(level, self.right - 1, self.top + 1, 1, self.height() - 2, terrain.EMPTY_SP)
        elif door.y == self.top:
            x = self.left + self.width() // 2
            y = self.bottom - 1
            Painter.fill(level, self.left + 1, self.top + 1, self.width() - 2, 1, terrain.EMPTY_SP)
        elif door.y == self.bottom:
            x = self.left + self.width() // 2
            y = self.top + 1
            Painter.fill(level, self.left + 1, self.bottom - 1, self.width() - 2, 1, terrain.EMPTY_SP)

        pos = x + y * level.width()
        prize = _pool_room_prize(level, rng, level.depth)
        chest = level.drop(prize, pos)
        chest.type = "CHEST"
        Painter.set(level, pos, terrain.PEDESTAL)

        level.add_item_to_spawn(frozenset())  # PotionOfInvisibility -- never a findPrizeItem match-target

        for _ in range(3):
            cls_name = "PhantomPiranha" if rng.Float() < 0.02 else "Piranha"  # 1/50 * exoticChanceMultiplier (no RatSkull) == 0.02
            while True:
                ppos = level.point_to_cell(self.random(rng))
                if level.map[ppos] == terrain.WATER and level.find_mob(ppos) is None:
                    break
            level.mobs.append(GenMob(cls_name=cls_name, pos=ppos, depth=level.depth))


def _armory_prize(level, rng: SPDRandom, depth: int, prize_cats: list):
    """Port of ArmoryRoom.prize() -- Random.chances draws an index,
    then dispatches to Bomb/weapon/armor/missile generation. The chosen
    weight is zeroed for subsequent calls."""
    index = rng.chances(prize_cats)
    prize_cats[index] = 0.0
    if index == 0:
        rng.IntMax(4)  # Bomb.random() -- Random.Int(4)
        return frozenset({"Bomb"})
    elif index == 1:
        _consume_generator_random_weapon(rng, depth)
        return frozenset({"Weapon"})
    elif index == 2:
        _consume_random_equipment_floorset(rng, depth // 5)
        return frozenset({"Armor"})
    else:
        _consume_generator_random_weapon(rng, depth)
        return frozenset({"Missile"})


class ArmoryRoom(SpecialRoom):
    def paint(self, level, rng: SPDRandom) -> None:
        from app.engine.dungeon.spd_levelgen.mob_spawner import GenMob

        Painter.fill(level, self, terrain.WALL)
        Painter.fill(level, self, 1, terrain.EMPTY)

        entrance = self.entrance()
        statue = None
        if entrance.x == self.left:
            statue = Point(self.right - 1, self.top + 1 if rng.IntMax(2) == 0 else self.bottom - 1)
        elif entrance.x == self.right:
            statue = Point(self.left + 1, self.top + 1 if rng.IntMax(2) == 0 else self.bottom - 1)
        elif entrance.y == self.top:
            statue = Point(self.left + 1 if rng.IntMax(2) == 0 else self.right - 1, self.bottom - 1)
        elif entrance.y == self.bottom:
            statue = Point(self.left + 1 if rng.IntMax(2) == 0 else self.right - 1, self.top + 1)
        if statue is not None:
            Painter.set(level, statue, terrain.STATUE)

        n = rng.IntRange(2, 3)
        prize_cats = [1.0, 1.0, 1.0, 1.0]
        for _ in range(n):
            while True:
                pos = level.point_to_cell(self.random(rng))
                if level.map[pos] == terrain.EMPTY and level.heaps.get(pos) is None:
                    break
            level.drop(_armory_prize(level, rng, level.depth, prize_cats), pos)

        cata = level.find_prize_item(rng, "TrinketCatalyst")
        if cata is not None:
            while True:
                pos = level.point_to_cell(self.random(rng))
                if level.map[pos] == terrain.EMPTY and level.heaps.get(pos) is None:
                    break
            level.drop(cata, pos)

        entrance.set(DoorType.LOCKED)
        level.add_item_to_spawn(_IRON_KEY)


def _sentry_prize(level, rng: SPDRandom, depth: int):
    """Port of SentryRoom.prize() -- 50% chance for prize item (findPrizeItem
    no-arg), otherwise weapon/missile/armor at floorSet+1, never cursed."""
    if rng.IntMax(2) == 0:
        prize = level.find_prize_item(rng)
        if prize is not None:
            return prize
    switch_idx = rng.IntMax(5)
    _consume_random_equipment_floorset(rng, depth // 5 + 1)
    rng.IntMax(3)  # 33% upgrade roll -- zero-RNG Item.upgrade() here
    if switch_idx == 2:
        return frozenset({"Missile"})
    return frozenset({"Weapon"})


class SentryRoom(SpecialRoom):
    def min_width(self) -> int:
        return 7

    def min_height(self) -> int:
        return 7

    def paint(self, level, rng: SPDRandom) -> None:
        from app.engine.dungeon.spd_levelgen.mob_spawner import GenMob

        Painter.fill(level, self, terrain.WALL)
        Painter.fill(level, self, 1, terrain.EMPTY_SP)

        entrance = self.entrance()

        c = self.center(rng)
        sentry_pos = Point()
        treasure_pos = Point()

        if entrance.x == self.left:
            sentry_pos.x = self.right - 1
            sentry_pos.y = c.y
            Painter.fill(level, self.left + 1, self.top + 1, 1, self.height() - 2, terrain.EMPTY)
            if entrance.y > c.y:
                treasure_pos.x = self.left + 1
                treasure_pos.y = (self.top + 1 + c.y) // 2
                Painter.fill(level, self.left + 1, self.top + 1, 2, c.y - self.top - 1, terrain.EMPTY)
            else:
                treasure_pos.x = self.left + 1
                treasure_pos.y = (self.bottom + c.y) // 2
                Painter.fill(level, self.left + 1, c.y + 1, 2, self.bottom - c.y - 1, terrain.EMPTY)
            for x in range(self.right - 3, self.left, -1):
                if level.map[x + c.y * level.width()] == terrain.EMPTY_SP:
                    Painter.set(level, x, c.y, terrain.STATUE_SP)
                else:
                    Painter.set(level, x, c.y, terrain.STATUE)
        elif entrance.x == self.right:
            sentry_pos.x = self.left + 1
            sentry_pos.y = c.y
            Painter.fill(level, self.right - 1, self.top + 1, 1, self.height() - 2, terrain.EMPTY)
            if entrance.y > c.y:
                treasure_pos.x = self.right - 1
                treasure_pos.y = (self.top + 1 + c.y) // 2
                Painter.fill(level, self.right - 2, self.top + 1, 2, c.y - self.top - 1, terrain.EMPTY)
            else:
                treasure_pos.x = self.right - 1
                treasure_pos.y = (self.bottom + 1 + c.y) // 2
                Painter.fill(level, self.right - 2, c.y + 1, 2, self.bottom - c.y - 1, terrain.EMPTY)
            for x in range(self.left + 3, self.right):
                if level.map[x + c.y * level.width()] == terrain.EMPTY_SP:
                    Painter.set(level, x, c.y, terrain.STATUE_SP)
                else:
                    Painter.set(level, x, c.y, terrain.STATUE)
        elif entrance.y == self.top:
            sentry_pos.x = c.x
            sentry_pos.y = self.bottom - 1
            Painter.fill(level, self.left + 1, self.top + 1, self.width() - 2, 1, terrain.EMPTY)
            if entrance.x > c.x:
                treasure_pos.x = (self.left + 1 + c.x) // 2
                treasure_pos.y = self.top + 1
                Painter.fill(level, self.left + 1, self.top + 1, c.x - self.left - 1, 2, terrain.EMPTY)
            else:
                treasure_pos.x = (self.right + c.x) // 2
                treasure_pos.y = self.top + 1
                Painter.fill(level, c.x + 1, self.top + 1, self.right - c.x - 1, 2, terrain.EMPTY)
            for y in range(self.bottom - 3, self.top, -1):
                if level.map[c.x + y * level.width()] == terrain.EMPTY_SP:
                    Painter.set(level, c.x, y, terrain.STATUE_SP)
                else:
                    Painter.set(level, c.x, y, terrain.STATUE)
        elif entrance.y == self.bottom:
            sentry_pos.x = c.x
            sentry_pos.y = self.top + 1
            Painter.fill(level, self.left + 1, self.bottom - 1, self.width() - 2, 1, terrain.EMPTY)
            if entrance.x > c.x:
                treasure_pos.x = (self.left + 1 + c.x) // 2
                treasure_pos.y = self.bottom - 1
                Painter.fill(level, self.left + 1, self.bottom - 2, c.x - self.left - 1, 2, terrain.EMPTY)
            else:
                treasure_pos.x = (self.right + c.x) // 2
                treasure_pos.y = self.bottom - 1
                Painter.fill(level, c.x + 1, self.bottom - 2, self.right - c.x - 1, 2, terrain.EMPTY)
            for y in range(self.top + 3, self.bottom):
                if level.map[c.x + y * level.width()] == terrain.EMPTY_SP:
                    Painter.set(level, c.x, y, terrain.STATUE_SP)
                else:
                    Painter.set(level, c.x, y, terrain.STATUE)

        Painter.set(level, sentry_pos, terrain.PEDESTAL)
        # Sentry NPC: runtime-only, zero-RNG, deferred for integration
        level.mobs.append(GenMob(cls_name="Sentry", pos=level.point_to_cell(sentry_pos)))

        Painter.set(level, treasure_pos, terrain.PEDESTAL)
        level.drop(_sentry_prize(level, rng, level.depth), level.point_to_cell(treasure_pos)).type = "CHEST"

        level.add_item_to_spawn(frozenset())  # PotionOfHaste -- never a findPrizeItem match-target

        entrance.set(DoorType.REGULAR)


class StatueRoom(SpecialRoom):
    def paint(self, level, rng: SPDRandom) -> None:
        from app.engine.dungeon.spd_levelgen.mob_spawner import GenMob

        Painter.fill(level, self, terrain.WALL)
        Painter.fill(level, self, 1, terrain.EMPTY)

        c = self.center(rng)
        cx, cy = c.x, c.y

        door = self.entrance()
        door.set(DoorType.LOCKED)
        # level.addItemToSpawn(new IronKey(depth)) -- zero-RNG identity, omitted
        # (IronKey is never a findPrizeItem match-target).
        level.add_item_to_spawn(_IRON_KEY)

        if door.x == self.left:
            Painter.fill(level, self.right - 1, self.top + 1, 1, self.height() - 2, terrain.STATUE)
            cx = self.right - 2
        elif door.x == self.right:
            Painter.fill(level, self.left + 1, self.top + 1, 1, self.height() - 2, terrain.STATUE)
            cx = self.left + 2
        elif door.y == self.top:
            Painter.fill(level, self.left + 1, self.bottom - 1, self.width() - 2, 1, terrain.STATUE)
            cy = self.bottom - 2
        elif door.y == self.bottom:
            Painter.fill(level, self.left + 1, self.top + 1, self.width() - 2, 1, terrain.STATUE)
            cy = self.top + 2

        # Replicate _consume_statue_random inline so we can capture the altChance result
        # rng.Float() -- altChance roll (ArmoredStatue vs Statue, threshold 1/10)
        mob_cls = "ArmoredStatue" if rng.Float() < 0.1 else "Statue"
        _consume_generator_random_weapon(rng, level.depth)
        _consume_enchantment_random(rng)
        # Place the statue mob at the center position
        pos = cx + cy * level.width()
        level.mobs.append(GenMob(cls_name=mob_cls, pos=pos, depth=level.depth))


class CrystalVaultRoom(SpecialRoom):
    def min_width(self) -> int:
        return 7

    def max_width(self) -> int:
        return 7

    def min_height(self) -> int:
        return 7

    def max_height(self) -> int:
        return 7

    def paint(self, level, rng: SPDRandom) -> None:
        from app.engine.dungeon.spd_levelgen import generator as gen

        Painter.fill(level, self, terrain.WALL)
        Painter.fill(level, self, 1, terrain.EMPTY_SP)
        Painter.fill(level, self, 2, terrain.EMPTY)

        c = level.point_to_cell(self.center(rng))

        # Collections.shuffle(prizeClasses, Random) for [WAND, RING, ARTIFACT]
        prize_classes = ["WAND", "RING", "ARTIFACT"]
        j = rng.IntMax(3)
        prize_classes[2], prize_classes[j] = prize_classes[j], prize_classes[2]
        j = rng.IntMax(2)
        prize_classes[1], prize_classes[j] = prize_classes[j], prize_classes[1]

        gen._dispatch_random_category(level.run_state.generator_state, rng, level.depth, prize_classes[0])
        gen._dispatch_random_category(level.run_state.generator_state, rng, level.depth, prize_classes[1])

        door_pos = level.point_to_cell(self.entrance())
        _CIRCLE8 = ((-1, -1), (0, -1), (1, -1), (1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0))
        while True:
            neighbour_idx = rng.IntMax(8)
            off_x, off_y = _CIRCLE8[neighbour_idx]
            cx = self.left + self.width() // 2
            cy = self.top + self.height() // 2
            i1_pos = (cx + off_x) + (cy + off_y) * level.width()
            opp_idx = (neighbour_idx + 4) % 8
            opp_off_x, opp_off_y = _CIRCLE8[opp_idx]
            i2_pos = (cx + opp_off_x) + (cy + opp_off_y) * level.width()
            # level.adjacent check: Chebyshev distance > 1
            def _adj(a, b):
                ax, ay = a % level.width(), a // level.width()
                bx, by = b % level.width(), b // level.width()
                return abs(ax - bx) <= 1 and abs(ay - by) <= 1 and (ax != bx or ay != by)
            if not _adj(i1_pos, door_pos) and not _adj(i2_pos, door_pos):
                break

        level.drop(frozenset(), i1_pos).type = "CRYSTAL_CHEST"
        rng.Float()  # mimic altChance check (RatSkull * MimicTooth modifiers are zero-RNG)
        # Mimic would be spawned here; for layout parity we always drop a chest
        level.drop(frozenset(), i2_pos).type = "CRYSTAL_CHEST"
        Painter.set(level, i1_pos, terrain.PEDESTAL)
        Painter.set(level, i2_pos, terrain.PEDESTAL)

        level.add_item_to_spawn(frozenset({"CrystalKey"}))
        self.entrance().set(DoorType.LOCKED)
        level.add_item_to_spawn(_IRON_KEY)


class CrystalChoiceRoom(SpecialRoom):
    def min_width(self) -> int:
        return 7

    def min_height(self) -> int:
        return 7

    def paint(self, level, rng: SPDRandom) -> None:
        from app.engine.dungeon.spd_levelgen import generator as gen

        Painter.fill(level, self, terrain.WALL)

        entrance = self.entrance()

        entry = EmptyRoom()
        room1 = EmptyRoom()
        room2 = EmptyRoom()

        if entrance.x == self.left:
            entry.set(self.left + 1, self.top + 1, self.left + 2, self.bottom - 1)

            room1.set(entry.right + 2, self.top + 1, self.right - 1, self.center(rng).y - 1)
            room2.set(entry.right + 2, room1.bottom + 2, self.right - 1, self.bottom - 1)

            Painter.set(level, Point(entry.right + 1, (room1.top + room1.bottom + 1) // 2), terrain.CRYSTAL_DOOR)
            Painter.set(level, Point(entry.right + 1, (room2.top + room2.bottom) // 2), terrain.CRYSTAL_DOOR)

        elif entrance.y == self.top:
            entry.set(self.left + 1, self.top + 1, self.right - 1, self.top + 2)

            room1.set(self.left + 1, entry.bottom + 2, self.center(rng).x - 1, self.bottom - 1)
            room2.set(room1.right + 2, entry.bottom + 2, self.right - 1, self.bottom - 1)

            Painter.set(level, Point((room1.left + room1.right + 1) // 2, entry.bottom + 1), terrain.CRYSTAL_DOOR)
            Painter.set(level, Point((room2.left + room2.right) // 2, entry.bottom + 1), terrain.CRYSTAL_DOOR)

        elif entrance.x == self.right:
            entry.set(self.right - 2, self.top + 1, self.right - 1, self.bottom - 1)
            Painter.draw_line(level, Point(self.right - 1, self.top + 1), Point(self.right - 1, self.bottom - 1), terrain.EMPTY)

            room1.set(self.left + 1, self.top + 1, entry.left - 2, self.center(rng).y - 1)
            room2.set(self.left + 1, room1.bottom + 2, entry.left - 2, self.bottom - 1)

            Painter.set(level, Point(entry.left - 1, (room1.top + room1.bottom + 1) // 2), terrain.CRYSTAL_DOOR)
            Painter.set(level, Point(entry.left - 1, (room2.top + room2.bottom) // 2), terrain.CRYSTAL_DOOR)

        elif entrance.y == self.bottom:
            entry.set(self.left + 1, self.bottom - 2, self.right - 1, self.bottom - 1)

            room1.set(self.left + 1, self.top + 1, self.center(rng).x - 1, entry.top - 2)
            room2.set(room1.right + 2, self.top + 1, self.right - 1, entry.top - 2)

            Painter.set(level, Point((room1.left + room1.right + 1) // 2, entry.top - 1), terrain.CRYSTAL_DOOR)
            Painter.set(level, Point((room2.left + room2.right) // 2, entry.top - 1), terrain.CRYSTAL_DOOR)

        Painter.fill(level, entry, terrain.EMPTY)
        Painter.fill(level, room1, terrain.EMPTY_SP)
        Painter.fill(level, room2, terrain.EMPTY_SP)

        if rng.IntMax(2) == 0:
            room1, room2 = room2, room1

        n = rng.NormalIntRange(3, 4)
        for _ in range(n):
            cat = "POTION" if rng.IntMax(2) == 0 else "SCROLL"  # Random.oneOf(POTION, SCROLL)
            gen._dispatch_random_category(level.run_state.generator_state, rng, level.depth, cat)
            while True:
                if room1.square() >= 16:
                    pos = level.point_to_cell(room1.random(rng, 1))
                else:
                    pos = level.point_to_cell(room1.random(rng, 0))
                if level.heaps.get(pos) is None:
                    break
            level.drop(frozenset(), pos)

        oneof_idx = rng.IntMax(3)  # Random.oneOf(WAND, RING, ARTIFACT)
        hidden_cat = ("WAND", "RING", "ARTIFACT")[oneof_idx]
        gen._dispatch_random_category(level.run_state.generator_state, rng, level.depth, hidden_cat)
        chest_pos = level.point_to_cell(room2.center(rng))
        chest = level.drop(frozenset(), chest_pos)
        chest.type = "CHEST"
        # chest.autoExplored = true -- not modeled (GenHeap has no such field;
        # it only affects exploration-bonus bookkeeping, zero-RNG either way).

        level.add_item_to_spawn(frozenset({"CrystalKey"}))

        self.entrance().set(DoorType.LOCKED)
        level.add_item_to_spawn(_IRON_KEY)


def _sacrifice_crypt_curse(rng: SPDRandom):
    """RNG draw for randomCurse() -- same array size (8) for both
    Weapon.Enchantment and Armor.Glyph curses in SPD."""
    rng.IntMax(8)


def _sacrifice_prize(level, rng: SPDRandom, depth: int):
    """Port of SacrificeRoom.prize() -- Generator.randomWeapon(floorSet+1)
    outer draw + Enchantment.randomCurse()."""
    _consume_random_equipment_floorset(rng, depth // 5 + 1)
    _sacrifice_crypt_curse(rng)
    return frozenset({"Weapon"})


class SacrificeRoom(SpecialRoom):
    def min_width(self) -> int:
        return 7

    def min_height(self) -> int:
        return 7

    def paint(self, level, rng: SPDRandom) -> None:
        Painter.fill(level, self, terrain.WALL)
        Painter.fill(level, self, 1, terrain.CHASM)

        c = self.center(rng)
        door = self.entrance()
        if door.x == self.left or door.x == self.right:
            if door.y == c.y:
                c.y += -1 if rng.IntMax(2) == 0 else 1
            p = Painter.draw_inside(level, self, door, abs(door.x - c.x) - 2, terrain.EMPTY_SP)
            step_y = 1 if p.y < c.y else -1
            while p.y != c.y:
                p.y += step_y
                Painter.set(level, p, terrain.EMPTY_SP)
        else:
            if door.x == c.x:
                c.x += -1 if rng.IntMax(2) == 0 else 1
            p = Painter.draw_inside(level, self, door, abs(door.y - c.y) - 2, terrain.EMPTY_SP)
            step_x = 1 if p.x < c.x else -1
            while p.x != c.x:
                p.x += step_x
                Painter.set(level, p, terrain.EMPTY_SP)

        s = Point(c.x, c.y)
        s.x -= 2
        if s.x > self.left:
            Painter.set(level, s, terrain.STATUE)
        s.x += 2
        s.y -= 2
        if s.y > self.top:
            Painter.set(level, s, terrain.STATUE)
        s.y += 2
        s.x += 2
        if s.x < self.right:
            Painter.set(level, s, terrain.STATUE)
        s.x -= 2
        s.y += 2
        if s.y < self.bottom:
            Painter.set(level, s, terrain.STATUE)

        Painter.fill(level, c.x - 1, c.y - 1, 3, 3, terrain.EMBERS)
        Painter.set(level, c, terrain.PEDESTAL)

        _sacrifice_prize(level, rng, level.depth)
        # SacrificialFire Blob.seed -- zero-RNG runtime, out of layout-parity scope

        door.set(DoorType.EMPTY)


class RunestoneRoom(SpecialRoom):
    def min_width(self) -> int:
        return 6

    def min_height(self) -> int:
        return 6

    def paint(self, level, rng: SPDRandom) -> None:
        Painter.fill(level, self, terrain.WALL)
        Painter.fill(level, self, 1, terrain.CHASM)

        Painter.draw_inside(level, self, self.entrance(), 2, terrain.EMPTY_SP)
        Painter.fill(level, self, 2, terrain.EMPTY)

        n = rng.NormalIntRange(2, 3)
        for _ in range(n):
            while True:
                drop_pos = level.point_to_cell(self.random(rng))
                if level.map[drop_pos] == terrain.EMPTY and level.heaps.get(drop_pos) is None:
                    break
            prize = _runestone_prize(level, rng)
            level.drop(prize, drop_pos)  # registers the heap so later iterations' collision check sees it

        self.entrance().set(DoorType.LOCKED)
        level.add_item_to_spawn(_IRON_KEY)


class GardenRoom(SpecialRoom):
    def paint(self, level, rng: SPDRandom) -> None:
        Painter.fill(level, self, terrain.WALL)
        Painter.fill(level, self, 1, terrain.HIGH_GRASS)
        Painter.fill(level, self, 2, terrain.GRASS)

        self.entrance().set(DoorType.LOCKED)
        level.add_item_to_spawn(_IRON_KEY)

        bushes = rng.IntMax(3)
        if bushes == 0:
            level.point_to_cell(self.random(rng))
        elif bushes == 1:
            level.point_to_cell(self.random(rng))
        elif rng.IntMax(5) == 0:
            level.point_to_cell(self.random(rng))
            level.point_to_cell(self.random(rng))
        # Foliage blob seed loops: zero-RNG, omitted


class LibraryRoom(SpecialRoom):
    def paint(self, level, rng: SPDRandom) -> None:
        Painter.fill(level, self, terrain.WALL)
        Painter.fill(level, self, 1, terrain.EMPTY_SP)

        entrance = self.entrance()

        Painter.fill(level, self.left + 1, self.top + 1, self.width() - 2, 1, terrain.BOOKSHELF)
        Painter.draw_inside(level, self, entrance, 1, terrain.EMPTY_SP)

        n = rng.NormalIntRange(1, 3)
        for i in range(n):
            while True:
                pos = level.point_to_cell(self.random(rng))
                if level.map[pos] == terrain.EMPTY_SP and level.heaps.get(pos) is None:
                    break
            if i == 0:
                rng.IntMax(2)  # ScrollOfIdentify vs ScrollOfRemoveCurse -- identity irrelevant
                prize = frozenset({"Scroll"})
            else:
                prize = _library_room_prize(level, rng)
            level.drop(prize, pos)  # registers the heap so later iterations' collision check sees it

        entrance.set(DoorType.LOCKED)
        level.add_item_to_spawn(_IRON_KEY)


class StorageRoom(SpecialRoom):
    def paint(self, level, rng: SPDRandom) -> None:
        Painter.fill(level, self, terrain.WALL)
        Painter.fill(level, self, 1, terrain.EMPTY_SP)

        honey_pot = rng.IntMax(2) == 0
        n = rng.IntRange(3, 4)
        for _ in range(n):
            while True:
                pos = level.point_to_cell(self.random(rng))
                if level.map[pos] == terrain.EMPTY_SP and level.heaps.get(pos) is None:
                    break
            if honey_pot:
                level.drop(frozenset({"Honeypot"}), pos)
                honey_pot = False
            else:
                level.drop(_consumable_prize(level, rng, level.depth), pos)

        self.entrance().set(DoorType.BARRICADE)
        level.add_item_to_spawn(frozenset())  # PotionOfLiquidFlame


class TreasuryRoom(SpecialRoom):
    def paint(self, level, rng: SPDRandom) -> None:
        from app.engine.dungeon.spd_levelgen import generator as gen

        Painter.fill(level, self, terrain.WALL)
        Painter.fill(level, self, 1, terrain.EMPTY)

        Painter.set(level, self.center(rng), terrain.STATUE)

        heap_type = "CHEST" if rng.IntMax(2) == 0 else "HEAP"
        n = rng.IntRange(2, 3)

        for _ in range(n):
            item = level.find_prize_item(rng, "TrinketCatalyst")
            if item is None:
                rng.chances([1.0])
                _consume_gold_random(rng, level.depth)

            while True:
                pos = level.point_to_cell(self.random(rng))
                if level.map[pos] == terrain.EMPTY and level.heaps.get(pos) is None and level.find_mob(pos) is None:
                    break

            if heap_type == "CHEST" and level.depth > 1:
                if rng.Float() < 0.2:
                    gen.roll_mimic_prize(level.run_state.generator_state, rng, level.depth)

        if heap_type == "HEAP":
            for _ in range(6):
                while True:
                    pos = level.point_to_cell(self.random(rng))
                    if level.map[pos] == terrain.EMPTY:
                        break
                rng.IntRange(5, 12)

        self.entrance().set(DoorType.LOCKED)
        level.add_item_to_spawn(_IRON_KEY)


class MagicWellRoom(SpecialRoom):
    def paint(self, level, rng: SPDRandom) -> None:
        Painter.fill(level, self, terrain.WALL)
        Painter.fill(level, self, 1, terrain.EMPTY)

        c = self.center(rng)
        Painter.set(level, c.x, c.y, terrain.WELL)

        # overrideWater is only ever set by external quest wiring (always None
        # in fresh levelgen) -- Random.element(WATERS) always fires.
        rng.IntMax(2)  # WellWater class pick -- identity irrelevant
        # WellWater.seed(...) -- zero-RNG actor registration, omitted

        self.entrance().set(DoorType.LOCKED)
        level.add_item_to_spawn(_IRON_KEY)


class ToxicGasRoom(SpecialRoom):
    def min_width(self) -> int:
        return 7

    def min_height(self) -> int:
        return 7

    def paint(self, level, rng: SPDRandom) -> None:
        Painter.fill(level, self, terrain.WALL)
        Painter.fill(level, self, 1, terrain.EMPTY)

        Painter.set(level, self.center(rng), terrain.STATUE)

        # Blob.seed -- pure actor-state setup, zero RNG, out of layout-parity scope.

        traps = min(self.width() - 2, self.height() - 2)

        for _ in range(traps):
            while True:
                cell = level.point_to_cell(self.random(rng, 2))
                if level.map[cell] == terrain.EMPTY:
                    break
            # level.setTrap/Blob.seed/Painter.set -- zero-RNG side effects, omitted.

        gold_positions: list[int] = []
        for _ in range(8):
            while True:
                pos_to_add = level.point_to_cell(self.random(rng, 2))
                if level.map[pos_to_add] != terrain.STATUE and pos_to_add not in gold_positions:
                    break
            gold_positions.append(pos_to_add)

        entry_pos = level.point_to_cell(self.entrance())
        furthest_pos = -1
        for i in gold_positions:
            if furthest_pos == -1 or level.true_distance(entry_pos, i) > level.true_distance(entry_pos, furthest_pos):
                furthest_pos = i

        gold_positions.remove(furthest_pos)
        _consume_gold_random(rng, level.depth)
        # level.drop(mainGold, furthestPos) -- zero-RNG, omitted.

        for _ in range(2):
            item = level.find_prize_item(rng, "TrinketCatalyst")
            if item is None:
                _consume_gold_random(rng, level.depth)
            gold_positions.pop(0)
            # level.drop -- zero-RNG, omitted.

        # PotionOfPurity is never a findPrizeItem match-target -- empty
        # descriptor mirrors SPAWN_FOOD/SPAWN_STYLUS (identity doesn't matter).
        level.add_item_to_spawn(frozenset())

        self.entrance().set(DoorType.REGULAR)


class MagicalFireRoom(SpecialRoom):
    class EternalFire:
        pass

    def min_width(self) -> int:
        return 7

    def min_height(self) -> int:
        return 7

    def paint(self, level, rng: SPDRandom) -> None:
        from app.engine.dungeon.spd_levelgen.standard_rooms import EmptyRoom

        Painter.fill(level, self, terrain.WALL)
        Painter.fill(level, self, 1, terrain.EMPTY)

        door = self.entrance()
        door.set(DoorType.REGULAR)

        fire_pos = self.center(rng)
        behind_fire = EmptyRoom()

        if door.x == self.left or door.x == self.right:
            fire_pos.y = self.top + 1
            while fire_pos.y != self.bottom:
                Painter.set(level, fire_pos, terrain.EMPTY_SP)
                fire_pos.y += 1
            if door.x == self.left:
                behind_fire.set(fire_pos.x + 1, self.top + 1, self.right - 1, self.bottom - 1)
            else:
                behind_fire.set(self.left + 1, self.top + 1, fire_pos.x - 1, self.bottom - 1)
        else:
            fire_pos.x = self.left + 1
            while fire_pos.x != self.right:
                Painter.set(level, fire_pos, terrain.EMPTY_SP)
                fire_pos.x += 1
            if door.y == self.top:
                behind_fire.set(self.left + 1, fire_pos.y + 1, self.right - 1, self.bottom - 1)
            else:
                behind_fire.set(self.left + 1, self.top + 1, self.right - 1, fire_pos.y - 1)

        Painter.fill(level, behind_fire, terrain.EMPTY_SP)

        honey_pot = rng.IntMax(2) == 0
        n = rng.IntRange(3, 4)
        for _ in range(n):
            while True:
                pos = level.point_to_cell(behind_fire.random(rng, 0))
                if level.heaps.get(pos) is None:
                    break
            if honey_pot:
                level.drop(frozenset({"Honeypot"}), pos)
                honey_pot = False
            else:
                level.drop(_consumable_prize(level, rng, level.depth), pos)

        level.add_item_to_spawn(frozenset())  # PotionOfFrost


class TrapsRoom(SpecialRoom):
    def min_width(self) -> int:
        return 6

    def max_width(self) -> int:
        return 8

    def min_height(self) -> int:
        return 6

    def max_height(self) -> int:
        return 8

    # Class-identity-irrelevant per-region trap pools (TrapsRoom.java:160-171)
    # -- only the array length matters for Random.oneOf's Random.Int draw.
    _LEVEL_TRAP_COUNTS = (3, 3, 3, 3, 1)

    def paint(self, level, rng: SPDRandom) -> None:
        Painter.fill(level, self, terrain.WALL)

        trap_present = rng.IntMax(4) != 0
        if trap_present:
            rng.IntMax(self._LEVEL_TRAP_COUNTS[level.depth // 5])  # Random.oneOf -- identity irrelevant

        if not trap_present:
            Painter.fill(level, self, 1, terrain.CHASM)
        else:
            Painter.fill(level, self, 1, terrain.TRAP)

        door = self.entrance()
        door.set(DoorType.REGULAR)

        last_row = (terrain.CHASM
                    if level.map[self.left + 1 + (self.top + 1) * level.width()] == terrain.CHASM
                    else terrain.EMPTY)

        x = y = -1
        if door.x == self.left:
            x = self.right - 1
            y = self.top + self.height() // 2
            Painter.fill(level, x, self.top + 1, 1, self.height() - 2, last_row)
        elif door.x == self.right:
            x = self.left + 1
            y = self.top + self.height() // 2
            Painter.fill(level, x, self.top + 1, 1, self.height() - 2, last_row)
        elif door.y == self.top:
            x = self.left + self.width() // 2
            y = self.bottom - 1
            Painter.fill(level, self.left + 1, y, self.width() - 2, 1, last_row)
        elif door.y == self.bottom:
            x = self.left + self.width() // 2
            y = self.top + 1
            Painter.fill(level, self.left + 1, y, self.width() - 2, 1, last_row)

        # getPoints()/setTrap loop -- zero-RNG actor registration, omitted
        # (Reflection.newInstance(trapClass).reveal() is deterministic).

        pos = x + y * level.width()
        if rng.IntMax(3) == 0:
            if last_row == terrain.CHASM:
                Painter.set(level, pos, terrain.EMPTY)
            level.drop(_traps_room_prize(level, rng, level.depth), pos).type = "CHEST"
        else:
            Painter.set(level, pos, terrain.PEDESTAL)
            level.drop(_traps_room_prize(level, rng, level.depth), pos).type = "CHEST"

        level.add_item_to_spawn(frozenset())  # PotionOfLevitation -- never a findPrizeItem match-target


class CrystalPathRoom(SpecialRoom):
    def min_width(self) -> int:
        return 7

    def min_height(self) -> int:
        return 7

    def paint(self, level, rng: SPDRandom) -> None:
        # Deferred import: run_state imports special_rooms (room registries),
        # so importing it at module scope here would cycle.
        from app.engine.dungeon.spd_levelgen.run_state import (
            POTION_DEFAULT_PROBS_TOTAL, POTION_EXPERIENCE_INDEX,
            SCROLL_DEFAULT_PROBS_TOTAL, SCROLL_TRANSMUTATION_INDEX,
            generator_random_class_index,
        )

        Painter.fill(level, self, terrain.WALL)

        # rooms are ordered from closest to furthest from the entrance
        rooms = [EmptyRoom() for _ in range(6)]

        entry = self.entrance().clone()

        prize1 = prize2 = 0
        if entry.x == self.left or entry.x == self.right:

            Painter.draw_inside(level, self, entry, 5 if self.width() > 8 else 3, terrain.EMPTY)

            room_w1 = 2 if self.width() >= 9 else 1
            room_w2 = 2 if self.width() % 2 == 0 else 1
            room_h = 2 if self.height() >= 9 else 1

            if entry.x == self.left:
                rooms[0].set_pos(self.left + 1, entry.y - room_h - 1).resize(room_w1 - 1, room_h - 1)
                Painter.set(level, rooms[0].left, rooms[0].bottom + 1, terrain.CRYSTAL_DOOR)
                rooms[1].set_pos(self.left + 1, entry.y + 2).resize(room_w1 - 1, room_h - 1)
                Painter.set(level, rooms[1].left, rooms[1].top - 1, terrain.CRYSTAL_DOOR)

                rooms[2].set_pos(rooms[1].right + 2, entry.y - room_h - 1).resize(room_w1 - 1, room_h - 1)
                Painter.set(level, rooms[2].left, rooms[2].bottom + 1, terrain.CRYSTAL_DOOR)
                rooms[3].set_pos(rooms[1].right + 2, entry.y + 2).resize(room_w1 - 1, room_h - 1)
                Painter.set(level, rooms[3].left, rooms[3].top - 1, terrain.CRYSTAL_DOOR)

                rooms[4].set_pos(rooms[3].right + 2, entry.y - room_h - 1).resize(room_w2 - 1, room_h)
                Painter.set(level, rooms[4].left - 1, rooms[4].bottom - 1, terrain.CRYSTAL_DOOR)
                rooms[5].set_pos(rooms[3].right + 2, entry.y + 1).resize(room_w2 - 1, room_h)
                Painter.set(level, rooms[5].left - 1, rooms[5].top + 1, terrain.CRYSTAL_DOOR)

                prize1 = level.point_to_cell(Point(rooms[4].left, rooms[4].bottom))
                prize2 = level.point_to_cell(Point(rooms[5].left, rooms[5].top))
            else:
                rooms[0].set_pos(self.right - room_w1, entry.y - room_h - 1).resize(room_w1 - 1, room_h - 1)
                Painter.set(level, rooms[0].right, rooms[0].bottom + 1, terrain.CRYSTAL_DOOR)
                rooms[1].set_pos(self.right - room_w1, entry.y + 2).resize(room_w1 - 1, room_h - 1)
                Painter.set(level, rooms[1].right, rooms[1].top - 1, terrain.CRYSTAL_DOOR)

                rooms[2].set_pos(rooms[1].left - room_w1 - 1, entry.y - room_h - 1).resize(room_w1 - 1, room_h - 1)
                Painter.set(level, rooms[2].right, rooms[2].bottom + 1, terrain.CRYSTAL_DOOR)
                rooms[3].set_pos(rooms[1].left - room_w1 - 1, entry.y + 2).resize(room_w1 - 1, room_h - 1)
                Painter.set(level, rooms[3].right, rooms[3].top - 1, terrain.CRYSTAL_DOOR)

                rooms[4].set_pos(rooms[3].left - room_w2 - 1, entry.y - room_h - 1).resize(room_w2 - 1, room_h)
                Painter.set(level, rooms[4].right + 1, rooms[4].bottom - 1, terrain.CRYSTAL_DOOR)
                rooms[5].set_pos(rooms[3].left - room_w2 - 1, entry.y + 1).resize(room_w2 - 1, room_h)
                Painter.set(level, rooms[5].right + 1, rooms[5].top + 1, terrain.CRYSTAL_DOOR)

                prize1 = level.point_to_cell(Point(rooms[4].right, rooms[4].bottom))
                prize2 = level.point_to_cell(Point(rooms[5].right, rooms[5].top))

        else:
            Painter.draw_inside(level, self, entry, 5 if self.height() > 8 else 3, terrain.EMPTY)

            room_w = 2 if self.width() >= 9 else 1
            room_h1 = 2 if self.height() >= 9 else 1
            room_h2 = 2 if self.height() % 2 == 0 else 1

            if entry.y == self.top:
                rooms[0].set_pos(entry.x - room_w - 1, self.top + 1).resize(room_w - 1, room_h1 - 1)
                Painter.set(level, rooms[0].right + 1, rooms[0].top, terrain.CRYSTAL_DOOR)
                rooms[1].set_pos(entry.x + 2, self.top + 1).resize(room_w - 1, room_h1 - 1)
                Painter.set(level, rooms[1].left - 1, rooms[1].top, terrain.CRYSTAL_DOOR)

                rooms[2].set_pos(entry.x - room_w - 1, rooms[1].bottom + 2).resize(room_w - 1, room_h1 - 1)
                Painter.set(level, rooms[2].right + 1, rooms[2].top, terrain.CRYSTAL_DOOR)
                rooms[3].set_pos(entry.x + 2, rooms[1].bottom + 2).resize(room_w - 1, room_h1 - 1)
                Painter.set(level, rooms[3].left - 1, rooms[3].top, terrain.CRYSTAL_DOOR)

                rooms[4].set_pos(entry.x - room_w - 1, rooms[3].bottom + 2).resize(room_w, room_h2 - 1)
                Painter.set(level, rooms[4].right - 1, rooms[4].top - 1, terrain.CRYSTAL_DOOR)
                rooms[5].set_pos(entry.x + 1, rooms[3].bottom + 2).resize(room_w, room_h2 - 1)
                Painter.set(level, rooms[5].left + 1, rooms[5].top - 1, terrain.CRYSTAL_DOOR)

                prize1 = level.point_to_cell(Point(rooms[4].right, rooms[4].top))
                prize2 = level.point_to_cell(Point(rooms[5].left, rooms[5].top))
            else:
                rooms[0].set_pos(entry.x - room_w - 1, self.bottom - room_h1).resize(room_w - 1, room_h1 - 1)
                Painter.set(level, rooms[0].right + 1, rooms[0].bottom, terrain.CRYSTAL_DOOR)
                rooms[1].set_pos(entry.x + 2, self.bottom - room_h1).resize(room_w - 1, room_h1 - 1)
                Painter.set(level, rooms[1].left - 1, rooms[1].bottom, terrain.CRYSTAL_DOOR)

                rooms[2].set_pos(entry.x - room_w - 1, rooms[1].top - room_h1 - 1).resize(room_w - 1, room_h1 - 1)
                Painter.set(level, rooms[2].right + 1, rooms[2].bottom, terrain.CRYSTAL_DOOR)
                rooms[3].set_pos(entry.x + 2, rooms[1].top - room_h1 - 1).resize(room_w - 1, room_h1 - 1)
                Painter.set(level, rooms[3].left - 1, rooms[3].bottom, terrain.CRYSTAL_DOOR)

                rooms[4].set_pos(entry.x - room_w - 1, rooms[3].top - room_h2 - 1).resize(room_w, room_h2 - 1)
                Painter.set(level, rooms[4].right - 1, rooms[4].bottom + 1, terrain.CRYSTAL_DOOR)
                rooms[5].set_pos(entry.x + 1, rooms[3].top - room_h2 - 1).resize(room_w, room_h2 - 1)
                Painter.set(level, rooms[5].left + 1, rooms[5].bottom + 1, terrain.CRYSTAL_DOOR)

                prize1 = level.point_to_cell(Point(rooms[4].right, rooms[4].bottom))
                prize2 = level.point_to_cell(Point(rooms[5].left, rooms[5].bottom))

        for room in rooms:
            Painter.fill(level, room, terrain.EMPTY_SP)
        Painter.set(level, prize1, terrain.PEDESTAL)
        Painter.set(level, prize2, terrain.PEDESTAL)

        # random potion/scroll in rooms 1-4, with lower value ones going into
        # earlier rooms. Items are tracked as class indices into
        # POTION/SCROLL.classes (never as full Item objects -- see
        # generator_random_class_index's docstring for why class identity
        # alone suffices: the exotic-substitution roll never substitutes on
        # a fresh game, so the rolled regular-class index IS the final identity).
        run_state = level.run_state
        potion_deck = run_state.potion_deck
        scroll_deck = run_state.scroll_deck

        potions: list[int] = []
        scrolls: list[int] = []
        # (deck_name, index) pairs needing Generator.undoDrop after rolling
        duplicates: list[tuple[str, int]] = []

        def add_reward_item(deck, deck_name: str, items: list[int]) -> None:
            while True:
                idx = generator_random_class_index(deck, rng)
                if idx in items:
                    duplicates.append((deck_name, idx))
                else:
                    items.append(idx)
                    return

        if rng.IntMax(2) == 0:
            add_reward_item(potion_deck, "POTION", potions)
            rng.Float()  # Random.Float() < consumableExoticChance() -- always false: ScrollOfTransmutation
            scrolls.append(SCROLL_TRANSMUTATION_INDEX)
        else:
            rng.Float()  # Random.Float() < consumableExoticChance() -- always false: PotionOfExperience
            potions.append(POTION_EXPERIENCE_INDEX)
            add_reward_item(scroll_deck, "SCROLL", scrolls)
        add_reward_item(potion_deck, "POTION", potions)
        add_reward_item(scroll_deck, "SCROLL", scrolls)
        add_reward_item(potion_deck, "POTION", potions)
        add_reward_item(scroll_deck, "SCROLL", scrolls)

        # need to undo the changes to spawn chances that the duplicates created
        for deck_name, idx in duplicates:
            (potion_deck if deck_name == "POTION" else scroll_deck).undo_drop(idx)

        # rarer potions/scrolls go later in the order (stable sort, descending
        # by defaultProbsTotal -- matches Collections.sort/Comparator)
        potions.sort(key=lambda i: -POTION_DEFAULT_PROBS_TOTAL[i])
        scrolls.sort(key=lambda i: -SCROLL_DEFAULT_PROBS_TOTAL[i])

        # least valuable items go into rooms 2&3, then rooms 0&1, finally 4&5.
        # Item placement itself (level.drop/addItemToSpawn) draws no RNG and
        # is out of scope (layout parity only) -- but room.center(rng) DOES
        # draw, so it must still be consumed in the original call order.
        shuffle = rng.IntMax(2)
        level.point_to_cell(rooms[2 if shuffle == 1 else 3].center(rng))
        level.point_to_cell(rooms[3 if shuffle == 1 else 2].center(rng))

        level.point_to_cell(rooms[0 if shuffle == 1 else 1].center(rng))
        level.point_to_cell(rooms[1 if shuffle == 1 else 0].center(rng))

        # prize1/prize2 cells need no center() roll

        level.add_item_to_spawn(frozenset({"CrystalKey"}))
        level.add_item_to_spawn(frozenset({"CrystalKey"}))
        level.add_item_to_spawn(frozenset({"CrystalKey"}))

        self.entrance().set(DoorType.REGULAR)


class LaboratoryRoom(SpecialRoom):
    def paint(self, level, rng: SPDRandom) -> None:
        Painter.fill(level, self, terrain.WALL)
        Painter.fill(level, self, 1, terrain.EMPTY_SP)

        entrance = self.entrance()

        pot = None
        if entrance.x == self.left:
            pot = Point(self.right - 1, self.top + 1 if rng.IntMax(2) == 0 else self.bottom - 1)
        elif entrance.x == self.right:
            pot = Point(self.left + 1, self.top + 1 if rng.IntMax(2) == 0 else self.bottom - 1)
        elif entrance.y == self.top:
            pot = Point(self.left + 1 if rng.IntMax(2) == 0 else self.right - 1, self.bottom - 1)
        elif entrance.y == self.bottom:
            pot = Point(self.left + 1 if rng.IntMax(2) == 0 else self.right - 1, self.top + 1)
        Painter.set(level, pot, terrain.ALCHEMY)

        # Alchemy Blob.seed: zero-RNG, omitted

        while True:
            pos = level.point_to_cell(self.random(rng))
            if level.map[pos] == terrain.EMPTY_SP and level.heaps.get(pos) is None:
                break

        n = rng.NormalIntRange(1, 2)
        for _ in range(n):
            while True:
                pos = level.point_to_cell(self.random(rng))
                if level.map[pos] == terrain.EMPTY_SP and level.heaps.get(pos) is None:
                    break
            _laboratory_prize(level, rng)

        chapter = 1 + level.depth // 5
        pages_to_drop = chapter
        for _ in range(pages_to_drop):
            while True:
                pos = level.point_to_cell(self.random(rng))
                if level.map[pos] == terrain.EMPTY_SP and level.heaps.get(pos) is None:
                    break

        entrance.set(DoorType.LOCKED)
        level.add_item_to_spawn(_IRON_KEY)


class PitRoom(SpecialRoom):
    def min_width(self) -> int:
        return 6

    def max_width(self) -> int:
        return 9

    def min_height(self) -> int:
        return 6

    def max_height(self) -> int:
        return 9

    def paint(self, level, rng: SPDRandom) -> None:
        from app.engine.dungeon.spd_levelgen import generator as gen

        Painter.fill(level, self, terrain.WALL)
        Painter.fill(level, self, 1, terrain.EMPTY)

        entrance = self.entrance()
        entrance.set(DoorType.CRYSTAL)

        well = None
        if entrance.x == self.left:
            well = Point(self.right - 1, self.top + 1 if rng.IntMax(2) == 0 else self.bottom - 1)
        elif entrance.x == self.right:
            well = Point(self.left + 1, self.top + 1 if rng.IntMax(2) == 0 else self.bottom - 1)
        elif entrance.y == self.top:
            well = Point(self.left + 1 if rng.IntMax(2) == 0 else self.right - 1, self.bottom - 1)
        elif entrance.y == self.bottom:
            well = Point(self.left + 1 if rng.IntMax(2) == 0 else self.right - 1, self.top + 1)
        Painter.set(level, well, terrain.EMPTY_WELL)

        remains = level.point_to_cell(self.center(rng))

        category = rng.IntMax(3)
        if category == 0:
            gen._dispatch_random_category(level.run_state.generator_state, rng, level.depth, "RING")
        elif category == 1:
            gen._dispatch_random_category(level.run_state.generator_state, rng, level.depth, "ARTIFACT")
        else:
            oneof_idx = rng.IntMax(5)
            if oneof_idx == 2:
                gen._dispatch_random_category(level.run_state.generator_state, rng, level.depth, "MISSILE")
            elif oneof_idx >= 3:
                gen._dispatch_random_category(level.run_state.generator_state, rng, level.depth, "ARMOR")
            else:
                gen._dispatch_random_category(level.run_state.generator_state, rng, level.depth, "WEAPON")

        n = rng.IntRange(1, 2)
        for _ in range(n):
            _pit_room_prize(rng, level.depth)

        level.add_item_to_spawn(frozenset({"CrystalKey"}))

    def can_place_trap(self, p: Point) -> bool:
        return False

    def can_place_grass(self, p: Point) -> bool:
        return False


class DemonSpawnerRoom(SpecialRoom):
    """Port of DemonSpawnerRoom.java -- not part of the special-room rotation
    (SpecialRoom.java's static lists); HallsLevel.initRooms() adds exactly one
    of these directly to the init-room list for floors 21-24."""

    def paint(self, level, rng: SPDRandom) -> None:
        from app.engine.dungeon.spd_levelgen.mob_spawner import GenMob

        Painter.fill(level, self, terrain.WALL)
        Painter.fill(level, self, 1, terrain.EMPTY)

        door = self.entrance()
        if door is not None:
            door.set(DoorType.UNLOCKED)  # cannot be hidden randomly under any circumstance

        c = self.center(rng)
        level.mobs.append(GenMob(cls_name="DemonSpawner", pos=level.point_to_cell(c)))

    def connect(self, room: "Room") -> bool:
        # Cannot connect to the exit room, otherwise works normally.
        if room.is_exit():
            return False
        return super().connect(room)

    def can_place_trap(self, p: Point) -> bool:
        return False

    def can_place_water(self, p: Point) -> bool:
        return False

    def can_place_grass(self, p: Point) -> bool:
        return False


# Order matters: matches SpecialRoom.java's static list registration order
# (Random.shuffle consumes them in this order during initForRun).
EQUIP_SPECIALS = (
    WeakFloorRoom, CryptRoom, PoolRoom, ArmoryRoom, SentryRoom,
    StatueRoom, CrystalVaultRoom, CrystalChoiceRoom, SacrificeRoom,
)

CONSUMABLE_SPECIALS = (
    RunestoneRoom, GardenRoom, LibraryRoom, StorageRoom, TreasuryRoom,
    MagicWellRoom, ToxicGasRoom, MagicalFireRoom, TrapsRoom, CrystalPathRoom,
)

CRYSTAL_KEY_SPECIALS = (PitRoom, CrystalVaultRoom, CrystalChoiceRoom, CrystalPathRoom)

POTION_SPAWN_ROOMS = (PoolRoom, SentryRoom, StorageRoom, ToxicGasRoom, MagicalFireRoom, TrapsRoom)


# -- SecretRoom subclasses (rooms/secret/*.java) ---------------------------

_POTION_CHANCES = [
    ("Healing", 1.0),
    ("MindVision", 2.0),
    ("Frost", 3.0),
    ("LiquidFlame", 3.0),
    ("ToxicGas", 3.0),
    ("Haste", 4.0),
    ("Invisibility", 4.0),
    ("Levitation", 4.0),
    ("ParalyticGas", 4.0),
    ("Purity", 4.0),
    ("Experience", 6.0),
]

_WELL_WATERS_SIZE = 2


def _patch_generate(rng: SPDRandom, w: int, h: int, fill: float, clustering: int, force_fill_rate: bool) -> list[bool]:
    length = w * h
    cur = [False] * length
    off = [False] * length

    fill_diff = -round(length * fill)

    if force_fill_rate and clustering > 0:
        fill += (0.5 - fill) * 0.5

    for i in range(length):
        off[i] = rng.Float() < fill
        if off[i]:
            fill_diff += 1

    for _ in range(clustering):
        for y in range(h):
            for x in range(w):
                pos = x + y * w
                count = 0
                neighbours = 0
                if y > 0:
                    if x > 0:
                        if off[pos - w - 1]:
                            count += 1
                        neighbours += 1
                    if off[pos - w]:
                        count += 1
                    neighbours += 1
                    if x < w - 1:
                        if off[pos - w + 1]:
                            count += 1
                        neighbours += 1
                if x > 0:
                    if off[pos - 1]:
                        count += 1
                    neighbours += 1
                if off[pos]:
                    count += 1
                neighbours += 1
                if x < w - 1:
                    if off[pos + 1]:
                        count += 1
                    neighbours += 1
                if y < h - 1:
                    if x > 0:
                        if off[pos + w - 1]:
                            count += 1
                        neighbours += 1
                    if off[pos + w]:
                        count += 1
                    neighbours += 1
                    if x < w - 1:
                        if off[pos + w + 1]:
                            count += 1
                        neighbours += 1
                cur[pos] = 2 * count >= neighbours
                if cur[pos] != off[pos]:
                    fill_diff += 1 if cur[pos] else -1

        tmp = cur
        cur = off
        off = tmp

    if force_fill_rate and min(w, h) > 2:
        neighbour_offsets = [-w - 1, -w, -w + 1, -1, 0, +1, +w - 1, +w, +w + 1]
        growing = fill_diff < 0

        while fill_diff != 0:
            cell = 0
            tries = 0
            while True:
                cell = rng.IntRange(1, w - 1) + rng.IntRange(1, h - 1) * w
                tries += 1
                if off[cell] != growing or tries * 10 >= length:
                    break

            for ni in neighbour_offsets:
                if fill_diff != 0 and off[cell + ni] != growing:
                    off[cell + ni] = growing
                    fill_diff += 1 if growing else -1

    return off


def _maze_check_valid_move(maze: list[list[bool]], x: int, y: int, mov_x: int, mov_y: int) -> bool:
    h = len(maze)
    w = len(maze[0])
    side_x = 1 - abs(mov_x)
    side_y = 1 - abs(mov_y)

    x += mov_x
    y += mov_y

    if x <= 0 or x >= h - 1 or y <= 0 or y >= w - 1:
        return False
    if maze[x][y] or maze[x + side_x][y + side_y] or maze[x - side_x][y - side_y]:
        return False

    x += mov_x
    y += mov_y

    if x <= 0 or x >= h - 1 or y <= 0 or y >= w - 1:
        return False
    if maze[x][y]:
        return False
    if maze[x + side_x][y + side_y] or maze[x - side_x][y - side_y]:
        return False

    return True


def _maze_decide_direction(rng: SPDRandom, maze: list[list[bool]], x: int, y: int) -> tuple[int, int] | None:
    if rng.IntMax(4) == 0 and _maze_check_valid_move(maze, x, y, 0, -1):
        return (0, -1)
    if rng.IntMax(3) == 0 and _maze_check_valid_move(maze, x, y, 1, 0):
        return (1, 0)
    if rng.IntMax(2) == 0 and _maze_check_valid_move(maze, x, y, 0, 1):
        return (0, 1)
    if _maze_check_valid_move(maze, x, y, -1, 0):
        return (-1, 0)
    return None


def _maze_generate(rng: SPDRandom, maze: list[list[bool]]) -> None:
    """Mutates maze in-place — true=FILLED (wall), false=EMPTY (path)."""
    h = len(maze)
    w = len(maze[0])
    fails = 0
    while fails < 2500:
        while True:
            x = rng.IntMax(h)
            y = rng.IntMax(w)
            if maze[x][y]:
                break

        mov = _maze_decide_direction(rng, maze, x, y)
        if mov is None:
            fails += 1
        else:
            fails = 0
            moves = 0
            mov_x, mov_y = mov
            while True:
                x += mov_x
                y += mov_y
                maze[x][y] = True
                moves += 1
                if not (rng.IntMax(moves) == 0 and _maze_check_valid_move(maze, x, y, mov_x, mov_y)):
                    break


def _pathfinder_build_distance_map(maze_w: int, maze_h: int, start: int, passable: list[bool]) -> list[int]:
    size = maze_w * maze_h
    max_val = 10 ** 9
    distance = [max_val] * size
    queue = [0] * size

    head = 0
    tail = 0

    queue[tail] = start
    tail += 1
    distance[start] = 0

    while head < tail:
        step = queue[head]
        head += 1
        next_dist = distance[step] + 1
        x = step % maze_w
        start_i = 3 if x == 0 else 0
        end_i = 3 if (x + 1) == maze_w else 0
        dir_lr = [-1 - maze_w, -1, -1 + maze_w, -maze_w, +maze_w, +1 - maze_w, +1, +1 + maze_w]
        for i in range(start_i, len(dir_lr) - end_i):
            n = step + dir_lr[i]
            if 0 <= n < size and passable[n] and distance[n] > next_dist:
                queue[tail] = n
                tail += 1
                distance[n] = next_dist

    return distance


class SecretGardenRoom(SecretRoom):
    def paint(self, level, rng: SPDRandom) -> None:
        Painter.fill(level, self, terrain.WALL)
        Painter.fill(level, self, 1, terrain.GRASS)

        iw = self.width() - 2
        ih = self.height() - 2
        grass = _patch_generate(rng, iw, ih, 0.5, 0, True)
        for i in range(self.top + 1, self.bottom):
            for j in range(self.left + 1, self.right):
                px = (j - self.left - 1) + ((i - self.top - 1) * iw)
                if grass[px]:
                    level.map[i * level.width() + j] = terrain.HIGH_GRASS

        self.entrance().set(DoorType.HIDDEN)

        for _ in range(3):
            while True:
                pos = level.point_to_cell(self.random(rng))
                if level.plants.get(pos) is None:
                    break
            level.plant("Starflower", pos)

        if rng.IntMax(2) == 0:
            while True:
                pos = level.point_to_cell(self.random(rng))
                if level.plants.get(pos) is None:
                    break
            level.plant("Seedpod", pos)
        else:
            while True:
                pos = level.point_to_cell(self.random(rng))
                if level.plants.get(pos) is None:
                    break
            level.plant("Dewcatcher", pos)


class SecretLaboratoryRoom(SecretRoom):
    def paint(self, level, rng: SPDRandom) -> None:
        Painter.fill(level, self, terrain.WALL)
        Painter.fill(level, self, 1, terrain.EMPTY_SP)

        self.entrance().set(DoorType.HIDDEN)

        pot = self.center(rng)
        Painter.set(level, pot, terrain.ALCHEMY)

        for _ in range(2):
            while True:
                pos = level.point_to_cell(self.random(rng))
                if level.map[pos] == terrain.EMPTY_SP and level.heaps.get(pos) is None:
                    break
            qty = rng.IntRange(3, 5)
            level.drop(frozenset({"EnergyCrystal"}), pos)

        n = rng.IntRange(2, 3)
        weights = [w for _, w in _POTION_CHANCES]
        for _ in range(n):
            while True:
                pos = level.point_to_cell(self.random(rng))
                if level.map[pos] == terrain.EMPTY_SP and level.heaps.get(pos) is None:
                    break

            idx = rng.chances(weights)
            weights[idx] = 0.0
            exotic_chance = rng.Float()
            level.drop(frozenset({"Potion"}), pos)


class SecretLibraryRoom(SecretRoom):
    def min_width(self) -> int:
        return max(7, super().min_width())

    def min_height(self) -> int:
        return max(7, super().min_height())

    def paint(self, level, rng: SPDRandom) -> None:
        Painter.fill(level, self, terrain.WALL)
        Painter.fill(level, self, 1, terrain.BOOKSHELF)

        Painter.fill_ellipse(level, self, 2, terrain.EMPTY_SP)

        entrance = self.entrance()
        if entrance.x == self.left or entrance.x == self.right:
            Painter.draw_inside(level, self, entrance, (self.width() - 3) // 2, terrain.EMPTY_SP)
        else:
            Painter.draw_inside(level, self, entrance, (self.height() - 3) // 2, terrain.EMPTY_SP)
        entrance.set(DoorType.HIDDEN)

        n = rng.IntRange(2, 3)
        for _ in range(n):
            while True:
                pos = level.point_to_cell(self.random(rng))
                if level.map[pos] == terrain.EMPTY_SP and level.heaps.get(pos) is None:
                    break
            # Random.chances(HashMap<ScrollClass,Float>) -- one Float(sum) draw;
            # identity irrelevant (the chosen weight is zeroed for the next pick,
            # but that only changes the *value* drawn, not the draw count). Every
            # key in scrollChances has an entry in ExoticScroll.regToExo, so the
            # post-pick `Random.Float() < consumableExoticChance()` exotic roll
            # ALWAYS fires too -- exactly 2 Float() draws per iteration.
            rng.Float()
            rng.Float()
            level.drop(frozenset(), pos)  # registers the heap so later iterations' collision check sees it


class SecretLarderRoom(SecretRoom):
    def min_width(self) -> int:
        return 6

    def min_height(self) -> int:
        return 6

    def paint(self, level, rng: SPDRandom) -> None:
        Painter.fill(level, self, terrain.WALL)
        Painter.fill(level, self, 1, terrain.EMPTY_SP)

        c = self.center(rng)

        Painter.fill(level, c.x - 1, c.y - 1, 3, 3, terrain.WATER)
        Painter.set(level, c, terrain.GRASS)

        extra_food = int(300 * (1 + level.depth / 5))
        while extra_food > 0:
            if extra_food >= 600:
                extra_food -= 600
                food_type = "Pasty"
            else:
                extra_food -= 300
                food_type = "ChargrilledMeat"

            while True:
                food_pos = level.point_to_cell(self.random(rng))
                if level.map[food_pos] == terrain.EMPTY_SP and level.heaps.get(food_pos) is None:
                    break
            level.drop(frozenset({"Food", food_type}), food_pos)

        self.entrance().set(DoorType.HIDDEN)


class SecretWellRoom(SecretRoom):
    def can_connect_point(self, p: Point) -> bool:
        return super().can_connect_point(p) and ((p.x > self.left + 1 and p.x < self.right - 1) or (p.y > self.top + 1 and p.y < self.bottom - 1))

    def paint(self, level, rng: SPDRandom) -> None:
        Painter.fill(level, self, terrain.WALL)
        door = self.entrance()
        if door.x == self.left:
            well = Point(self.right - 2, door.y)
        elif door.x == self.right:
            well = Point(self.left + 2, door.y)
        elif door.y == self.top:
            well = Point(door.x, self.bottom - 2)
        else:
            well = Point(door.x, self.top + 2)

        Painter.fill(level, well.x - 1, well.y - 1, 3, 3, terrain.CHASM)
        Painter.draw_line(level, door, well, terrain.EMPTY)

        Painter.set(level, well, terrain.WELL)

        rng.IntMax(_WELL_WATERS_SIZE)

        self.entrance().set(DoorType.HIDDEN)


_STONE_PROBS = (0.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 0.0)


class SecretRunestoneRoom(SecretRoom):
    def paint(self, level, rng: SPDRandom) -> None:
        Painter.fill(level, self, terrain.WALL)
        Painter.fill(level, self, 1, terrain.EMPTY)

        entrance = self.entrance()
        center = self.center(rng)

        if entrance.x == self.left or entrance.x == self.right:
            Painter.draw_line(level, Point(center.x, self.top + 1), Point(center.x, self.bottom - 1), terrain.BOOKSHELF)
            if entrance.x == self.left:
                Painter.fill(level, center.x + 1, self.top + 1, self.right - center.x - 1, self.height() - 2, terrain.EMPTY_SP)
            else:
                Painter.fill(level, self.left + 1, self.top + 1, center.x - self.left - 1, self.height() - 2, terrain.EMPTY_SP)
        else:
            Painter.draw_line(level, Point(self.left + 1, center.y), Point(self.right - 1, center.y), terrain.BOOKSHELF)
            if entrance.y == self.top:
                Painter.fill(level, self.left + 1, center.y + 1, self.width() - 2, self.bottom - center.y - 1, terrain.EMPTY_SP)
            else:
                Painter.fill(level, self.left + 1, self.top + 1, self.width() - 2, center.y - self.top - 1, terrain.EMPTY_SP)

        while True:
            drop_pos = level.point_to_cell(self.random(rng))
            if level.map[drop_pos] == terrain.EMPTY:
                break
        rng.chances(_STONE_PROBS)
        level.drop(frozenset({"Runestone"}), drop_pos)

        while True:
            drop_pos = level.point_to_cell(self.random(rng))
            if level.map[drop_pos] == terrain.EMPTY and level.heaps.get(drop_pos) is None:
                break
        rng.chances(_STONE_PROBS)
        level.drop(frozenset({"Runestone"}), drop_pos)

        while True:
            drop_pos = level.point_to_cell(self.random(rng))
            if level.map[drop_pos] == terrain.EMPTY_SP:
                break

        self.entrance().set(DoorType.HIDDEN)

    def can_place_water(self, p: Point) -> bool:
        return False

    def can_place_grass(self, p: Point) -> bool:
        return False

    def can_place_character(self, p: Point, l) -> bool:
        return super().can_place_character(p, l) and l.map[l.point_to_cell(p)] != terrain.EMPTY_SP


class SecretArtilleryRoom(SecretRoom):
    def paint(self, level, rng: SPDRandom) -> None:
        Painter.fill(level, self, terrain.WALL)
        Painter.fill(level, self, 1, terrain.EMPTY_SP)

        Painter.set(level, self.center(rng), terrain.STATUE_SP)

        for i in range(3):
            while True:
                item_pos = level.point_to_cell(self.random(rng))
                if level.map[item_pos] == terrain.EMPTY_SP and level.heaps.get(item_pos) is None:
                    break

            if i != 0:
                _consume_random_equipment_floorset(rng, level.depth // 5)
            level.drop(frozenset({"Weapon"}), item_pos)

        self.entrance().set(DoorType.HIDDEN)


class SecretChestChasmRoom(SecretRoom):
    def min_width(self) -> int:
        return 8

    def max_width(self) -> int:
        return 9

    def min_height(self) -> int:
        return 8

    def max_height(self) -> int:
        return 9

    def paint(self, level, rng: SPDRandom) -> None:
        from app.engine.dungeon.spd_levelgen import generator as gen

        Painter.fill(level, self, terrain.WALL)
        Painter.fill(level, self, 1, terrain.CHASM)

        chests = 0

        p = Point(self.left + 3, self.top + 3)
        Painter.set(level, p, terrain.EMPTY_SP)
        gen.generator_random(level.run_state.generator_state, rng, level.depth)
        chests += 1

        p.x = self.right - 3
        Painter.set(level, p, terrain.EMPTY_SP)
        gen.generator_random(level.run_state.generator_state, rng, level.depth)
        chests += 1

        p.y = self.bottom - 3
        Painter.set(level, p, terrain.EMPTY_SP)
        gen.generator_random(level.run_state.generator_state, rng, level.depth)
        chests += 1

        p.x = self.left + 3
        Painter.set(level, p, terrain.EMPTY_SP)
        gen.generator_random(level.run_state.generator_state, rng, level.depth)
        chests += 1

        p = Point(self.left + 1, self.top + 1)
        Painter.set(level, p, terrain.EMPTY_SP)
        if chests > 0:
            chests -= 1

        p.x = self.right - 1
        Painter.set(level, p, terrain.EMPTY_SP)
        if chests > 0:
            chests -= 1

        p.y = self.bottom - 1
        Painter.set(level, p, terrain.EMPTY_SP)
        if chests > 0:
            chests -= 1

        p.x = self.left + 1
        Painter.set(level, p, terrain.EMPTY_SP)
        if chests > 0:
            chests -= 1

        self.entrance().set(DoorType.HIDDEN)


class SecretHoneypotRoom(SecretRoom):
    def paint(self, level, rng: SPDRandom) -> None:
        Painter.fill(level, self, terrain.WALL)
        Painter.fill(level, self, 1, terrain.EMPTY)

        broken_pot_pos = self.center(rng)

        broken_pot_pos.x = (broken_pot_pos.x + self.entrance().x) // 2
        broken_pot_pos.y = (broken_pot_pos.y + self.entrance().y) // 2

        broken_cell = level.point_to_cell(broken_pot_pos)
        level.drop(frozenset({"Bomb", "ShatteredPot"}), broken_cell)

        while True:
            item_pos = level.point_to_cell(self.random(rng))
            if level.heaps.get(item_pos) is None:
                break
        level.drop(frozenset({"Bomb", "Honeypot"}), item_pos)

        while True:
            item_pos = level.point_to_cell(self.random(rng))
            if level.heaps.get(item_pos) is None:
                break
        level.drop(frozenset({"Bomb"}), item_pos)

        rng.IntMax(2)

        self.entrance().set(DoorType.HIDDEN)


class SecretHoardRoom(SecretRoom):
    def paint(self, level, rng: SPDRandom) -> None:
        Painter.fill(level, self, terrain.WALL)
        Painter.fill(level, self, 1, terrain.EMPTY)

        rng.IntMax(2)

        total_gold = ((self.width() - 2) * (self.height() - 2)) // 2
        for _ in range(total_gold):
            while True:
                gold_pos = level.point_to_cell(self.random(rng))
                if level.heaps.get(gold_pos) is None:
                    break
            _consume_gold_random(rng, level.depth)
            level.drop(frozenset({"Gold"}), gold_pos)

        for x in range(self.left, self.right + 1):
            for y in range(self.top, self.bottom + 1):
                roll_hit = rng.IntMax(2) == 0
                if roll_hit and level.map[level.point_to_cell(Point(x, y))] == terrain.EMPTY:
                    Painter.set(level, x, y, terrain.TRAP)

        self.entrance().set(DoorType.HIDDEN)


class SecretMazeRoom(SecretRoom):
    def min_width(self) -> int:
        return 14

    def min_height(self) -> int:
        return 14

    def max_width(self) -> int:
        return 18

    def max_height(self) -> int:
        return 18

    def paint(self, level, rng: SPDRandom) -> None:
        Painter.fill(level, self, terrain.WALL)
        Painter.fill(level, self, 1, terrain.EMPTY)

        mw = self.width()
        mh = self.height()
        maze = [[False] * mh for _ in range(mw)]
        for x in range(mw):
            for y in range(mh):
                if x == 0 or x == mw - 1 or y == 0 or y == mh - 1:
                    maze[x][y] = True

        for d in self.connected.values():
            maze[d.x - self.left][d.y - self.top] = False

        _maze_generate(rng, maze)

        Painter.fill(level, self, 1, terrain.EMPTY)
        passable = [False] * (mw * mh)
        for x in range(mw):
            for y in range(mh):
                if maze[x][y]:
                    Painter.fill(level, x + self.left, y + self.top, 1, 1, terrain.WALL)
                passable[x + mw * y] = not maze[x][y]

        entrance = self.entrance()
        entrance_pos = (entrance.x - self.left) + mw * (entrance.y - self.top)
        distance = _pathfinder_build_distance_map(mw, mh, entrance_pos, passable)

        best_dist = 0
        best_p = Point()
        for i in range(mw * mh):
            if distance[i] != 10**9 and distance[i] > best_dist:
                best_dist = distance[i]
                best_p.x = (i % mw) + self.left
                best_p.y = (i // mw) + self.top

        rng.IntMax(2)
        _consume_random_equipment_floorset(rng, level.depth // 5 + 1)
        rng.IntMax(3)

        best_cell = level.point_to_cell(best_p)
        level.drop(frozenset({"Weapon"}), best_cell)

        self.entrance().set(DoorType.HIDDEN)


class SecretSummoningRoom(SecretRoom):
    def max_width(self) -> int:
        return 8

    def max_height(self) -> int:
        return 8

    def paint(self, level, rng: SPDRandom) -> None:
        from app.engine.dungeon.spd_levelgen import generator as gen
        from app.engine.dungeon.spd_levelgen.traps import SummoningTrap, reveal_hidden_trap_chance

        Painter.fill(level, self, terrain.WALL)
        Painter.fill(level, self, 1, terrain.SECRET_TRAP)

        center = self.center(rng)
        gen.generator_random(level.run_state.generator_state, rng, level.depth)

        center_cell = level.point_to_cell(center)
        level.drop(frozenset({"Scroll"}), center_cell)

        revealed_chance = reveal_hidden_trap_chance()
        reveal_inc = 0
        for p in self.get_points():
            cell_idx = level.point_to_cell(p)
            if level.map[cell_idx] == terrain.SECRET_TRAP:
                reveal_inc += revealed_chance
                if reveal_inc >= 1:
                    level.set_trap(SummoningTrap().reveal(), cell_idx)
                    Painter.set(level, cell_idx, terrain.TRAP)
                    reveal_inc -= 1
                else:
                    level.set_trap(SummoningTrap().hide(), cell_idx)

        self.entrance().set(DoorType.HIDDEN)


# Order matters: matches SecretRoom.ALL_SECRETS static list registration order.
ALL_SECRETS = (
    SecretGardenRoom, SecretLaboratoryRoom, SecretLibraryRoom, SecretLarderRoom,
    SecretWellRoom, SecretRunestoneRoom, SecretArtilleryRoom, SecretChestChasmRoom,
    SecretHoneypotRoom, SecretHoardRoom, SecretMazeRoom, SecretSummoningRoom,
)
