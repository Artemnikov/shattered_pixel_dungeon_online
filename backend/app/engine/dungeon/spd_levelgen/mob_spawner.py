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
"""Port of com.shatteredpixel.shatteredpixeldungeon.actors.mobs.MobSpawner's
`getMobRotation` (the per-floor cached `mobsToSpawn` rotation `Level.createMob`
draws from FIFO, regenerated whenever empty) plus `ChampionEnemy.rollForChampion`.

Mobs are represented purely as class-name strings (matching the Java simple
class names) -- the only facts `createMobs`/`createMob` need are identity
(for `RARE_ALTS` lookups, `findMob`/dedup) and `Property.LARGE` membership
(see `LARGE_MOBS` -- empty for any mob spawnable on floors 1-10, confirmed by
reading every reachable class's `properties()`)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from app.engine.dungeon.spd_random import SPDRandom


@dataclass
class GenMob:
    """Stand-in for Mob -- just enough for createMobs/createItems' RNG-
    sequence- and placement-relevant facts: class identity (RARE_ALTS lookups,
    findMob dedup) and Char.Property.LARGE membership (openSpace gate)."""

    cls_name: str
    pos: int = -1
    items: List[object] = None
    depth: int = 1

    def __post_init__(self) -> None:
        if self.items is None:
            self.items = []

    @property
    def is_large(self) -> bool:
        return self.cls_name in LARGE_MOBS

# Char.Property.LARGE members among ALL mobs `getMobRotation` can ever place
# in `mobsToSpawn` for depths 1-26 (DM-200/300/Golem/YogFist -- the only LARGE
# mobs in the game -- first appear at depths 13/14/18/26 respectively).
LARGE_MOBS = frozenset({"DM200", "DM201", "DM300", "Golem", "YogFist"})


def _roll_shaman(rng: SPDRandom) -> str:
    """Shaman.random(): Float() < 0.4/0.8 thresholds -> Red/Blue/Purple."""
    roll = rng.Float()
    if roll < 0.4:
        return "RedShaman"
    if roll < 0.8:
        return "BlueShaman"
    return "PurpleShaman"


def _roll_elemental(rng: SPDRandom) -> str:
    """Elemental.random(): altChance = 1/50 * RatSkull.exoticChanceMultiplier()
    (baseline 1.0 -> altChance = 0.02); Float() < altChance -> ChaosElemental,
    else a second Float() picks Fire/Frost/Shock by 0.4/0.8 thresholds."""
    alt_chance = 1.0 / 50.0
    if rng.Float() < alt_chance:
        return "ChaosElemental"
    roll = rng.Float()
    if roll < 0.4:
        return "FireElemental"
    if roll < 0.8:
        return "FrostElemental"
    return "ShockElemental"


def _standard_mob_rotation(rng: SPDRandom, depth: int) -> List[str]:
    """Port of MobSpawner.standardMobRotation -- a per-depth literal list,
    EXCEPT for caves (Shaman.random()) and city (Elemental.random()) depths,
    where the listed factory calls consume RNG in left-to-right (i.e.
    Arrays.asList argument) evaluation order while the list is built."""
    if depth == 1:
        return ["Rat", "Rat", "Rat", "Snake"]
    if depth == 2:
        return ["Rat", "Rat", "Snake", "Gnoll", "Gnoll"]
    if depth == 3:
        return ["Rat", "Snake", "Gnoll", "Gnoll", "Gnoll", "Swarm", "Crab"]
    if depth in (4, 5):
        return ["Gnoll", "Swarm", "Crab", "Crab", "Slime", "Slime"]

    if depth == 6:
        return ["Skeleton", "Skeleton", "Skeleton", "Thief", "Swarm"]
    if depth == 7:
        return ["Skeleton", "Skeleton", "Skeleton", "Thief", "DM100", "Guard"]
    if depth == 8:
        return ["Skeleton", "Skeleton", "Thief", "DM100", "DM100", "Guard", "Guard", "Necromancer"]
    if depth in (9, 10):
        return ["Skeleton", "Thief", "DM100", "DM100", "Guard", "Guard", "Necromancer", "Necromancer"]

    if depth == 11:
        return ["Bat", "Bat", "Bat", "Brute", _roll_shaman(rng)]
    if depth == 12:
        return ["Bat", "Bat", "Brute", "Brute", _roll_shaman(rng), "Spinner"]
    if depth == 13:
        return ["Bat", "Brute", "Brute", _roll_shaman(rng), _roll_shaman(rng), "Spinner", "Spinner", "DM200"]
    if depth in (14, 15):
        return ["Bat", "Brute", _roll_shaman(rng), _roll_shaman(rng), "Spinner", "Spinner", "DM200", "DM200"]

    if depth == 16:
        return ["Ghoul", "Ghoul", "Ghoul", _roll_elemental(rng), "Warlock"]
    if depth == 17:
        return ["Ghoul", _roll_elemental(rng), _roll_elemental(rng), "Warlock", "Monk"]
    if depth == 18:
        return ["Ghoul", _roll_elemental(rng), "Warlock", "Warlock", "Monk", "Monk", "Golem"]
    if depth in (19, 20):
        return [_roll_elemental(rng), "Warlock", "Warlock", "Monk", "Monk", "Golem", "Golem", "Golem"]

    if depth == 21:
        return ["Succubus", "Succubus", "Eye"]
    if depth == 22:
        return ["Succubus", "Eye"]
    if depth == 23:
        return ["Succubus", "Eye", "Eye", "Scorpio"]
    if depth in (24, 25, 26):
        return ["Succubus", "Eye", "Eye", "Scorpio", "Scorpio", "Scorpio"]

    # `default:` shares depth 1's list (the `case 1: default:` fallthrough).
    return ["Rat", "Rat", "Rat", "Snake"]


# MobSpawner.addRareMobs -- depth -> (added class, threshold). Only these four
# depths roll; all others (incl. every sewers floor but 4) are zero-RNG no-ops.
_RARE_MOB_BY_DEPTH = {
    4: "Thief",
    9: "Bat",
    14: "Ghoul",
    19: "Succubus",
}


def _add_rare_mobs(rng: SPDRandom, depth: int, rotation: List[str]) -> None:
    """Port of MobSpawner.addRareMobs: Random.Float() < 0.025 gate, only for
    depths 4/9/14/19 (every other depth's `case` returns immediately, zero RNG)."""
    extra = _RARE_MOB_BY_DEPTH.get(depth)
    if extra is not None:
        if rng.Float() < 0.025:
            rotation.append(extra)


# MobSpawner.RARE_ALTS -- swap targets reachable among depths 1-26's rotations.
RARE_ALTS = {
    "Rat": "Albino",
    "Gnoll": "GnollExile",
    "Crab": "HermitCrab",
    "Slime": "CausticSlime",
    "Thief": "Bandit",
    "Necromancer": "SpectralNecromancer",
    "Brute": "ArmoredBrute",
    "DM200": "DM201",
    "Monk": "Senior",
    "Elemental": "ChaosElemental",  # unreachable here -- swap happens inside Elemental.random() instead
    "Scorpio": "Acidic",
}


def _swap_mob_alts(rng: SPDRandom, rotation: List[str]) -> None:
    """Port of MobSpawner.swapMobAlts: altChance = 1/50 * RatSkull.exoticChanceMultiplier()
    (baseline 1.0 -> 0.02); for each entry (in order), Float() < altChance gates
    a RARE_ALTS lookup-and-replace (no-op, but draw still consumed, if absent)."""
    alt_chance = 1.0 / 50.0
    for i in range(len(rotation)):
        if rng.Float() < alt_chance:
            alt = RARE_ALTS.get(rotation[i])
            if alt is not None:
                rotation[i] = alt


def get_mob_rotation(rng: SPDRandom, depth: int) -> List[str]:
    """Port of MobSpawner.getMobRotation: build the standard rotation (with
    any inline Shaman/Elemental.random() draws), add rare mobs, swap alts,
    then Random.shuffle (List overload -- reverse Fisher-Yates)."""
    rotation = _standard_mob_rotation(rng, depth)
    _add_rare_mobs(rng, depth, rotation)
    _swap_mob_alts(rng, rotation)
    rng.shuffle(rotation)
    return rotation


def roll_for_champion(rng: SPDRandom) -> None:
    """Port of ChampionEnemy.rollForChampion: ALWAYS consumes exactly one
    Random.Int(6), regardless of champion-mode state (explicit Java comment:
    this exists so mobsToChampion doesn't perturb levelgen RNG). The
    CHAMPION_ENEMIES challenge is off in the fresh-game baseline, so nothing
    past the roll itself ever executes."""
    rng.IntMax(6)
