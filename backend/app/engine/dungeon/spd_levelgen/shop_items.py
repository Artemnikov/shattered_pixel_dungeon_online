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
"""Port of ShopRoom.generateItems() (ShopRoom.java) for the depth-tiered
shops on floors 6/11/16 (Dungeon.shopOnLevel()).

Deviations from SPD, per the approved plan:
 - TippedDart -> 2x Stone
 - Alchemize -> skipped
 - Bag (ChooseBag) -> skipped (no Bag items implemented yet)
 - Bomb/DoubleBomb/Honeypot -> +1 Food ("Mystery Meat")
 - Ankh / StoneOfAugmentation / TimekeepersHourglass.sandBag -> skipped
 - Stylus (7/10 rare roll) -> redistributed to Wand/Ring
 - Torch x3 (depth 20/21) -> not reachable (shopOnLevel() is 6/11/16 only)

Item generation + shuffling runs inside a pushed RNG generator (seeded by a
single Long() draw from the main sequence), mirroring SPD's
`Random.pushGenerator(Random.Long())` isolation so shop stock never perturbs
levelgen RNG beyond that one draw.
"""

from __future__ import annotations

from typing import List

from app.engine.dungeon.spd_random import SPDRandom
from app.engine.entities.base import (
    Armor,
    Artifact,
    Food,
    HealthPotion,
    Item,
    MeleeWeapon,
    MissileWeapon,
    Ring,
    Scroll,
    ScrollOfIdentify,
    ScrollOfMagicMapping,
    ScrollOfRemoveCurse,
    Stone,
    Wand,
)

# depth -> (weapon/missile tier, armor tier) -- ShopRoom.generateItems()'s
# `case 6/11/16` use wepTiers[1]/[2]/[3] (1-indexed tiers 2/3/4) with
# LeatherArmor/MailArmor/ScaleArmor (tiers 1/2/3).
_SHOP_TIERS = {
    6: (2, 1),
    11: (3, 2),
    16: (4, 3),
    # ImpShopRoom (depth 20): wepTiers[4] -> 5, PlateArmor -> 4. The 3x Torch
    # added at case 20/21 are skipped per the existing not-yet-implemented-item
    # substitution table.
    20: (5, 4),
}


def generate_shop_items(rng: SPDRandom, depth: int) -> List[Item]:
    weapon_tier, armor_tier = _SHOP_TIERS.get(depth, (2, 1))

    items: List[Item] = [
        MeleeWeapon(name="Weapon", tier=weapon_tier),
        MissileWeapon(name="Missile Weapon", tier=weapon_tier),
        Armor(name="Armor", tier=armor_tier),
        # TippedDart.randomTipped(2) -> 2x Stone
        Stone(),
        Stone(),
        HealthPotion(name="Potion of Healing"),
        HealthPotion(),
        HealthPotion(),
        ScrollOfIdentify(),
        ScrollOfRemoveCurse(),
        ScrollOfMagicMapping(),
        Scroll(name="Scroll"),
        HealthPotion(),
        Food(name="Small Ration of Food"),
        Food(name="Small Ration of Food"),
        # Bomb/DoubleBomb/Honeypot substitution
        Food(name="Mystery Meat"),
    ]

    # Rare item roll (Random.Int(10)): 0=wand, 1=ring, 2=artifact, the
    # remaining 7 (Stylus) buckets redistribute evenly to wand/ring.
    roll = rng.IntMax(10)
    if roll == 0:
        rare: Item = Wand(name="Wand", cursed_known=True)
    elif roll == 1:
        rare = Ring(name="Ring", cursed_known=True)
    elif roll == 2:
        rare = Artifact(name="Artifact")
    elif roll % 2 == 1:
        rare = Wand(name="Wand", cursed_known=True)
    else:
        rare = Ring(name="Ring", cursed_known=True)
    items.append(rare)

    rng.shuffle(items)

    for item in items:
        item.for_sale = True
    return items


def shop_room_item_list(rng: SPDRandom, depth: int) -> List[Item]:
    """Generates shop stock isolated from the main RNG sequence (mirrors
    SPD's `Random.pushGenerator(Random.Long())` around the final shuffle,
    extended here to cover the whole generation+shuffle so shop contents
    never perturb levelgen RNG beyond the single Long() draw)."""
    seed = rng.Long()
    rng.push_generator(seed)
    try:
        return generate_shop_items(rng, depth)
    finally:
        rng.pop_generator()
