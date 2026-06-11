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
"""Port of com.shatteredpixel.shatteredpixeldungeon.items.Generator -- the
full no-arg `Generator.random()` category dispatcher plus persistent deck
state (`categoryProbs`/`usingFirstDeck`/per-category `probs`/`seed`/`dropped`).

Scope: only what's reachable from a fresh-game baseline during levelgen
(`SecretSummoningRoom.paint` and `RegularLevel.createItems`/`createMobs`,
floors 1-26). Item *behaviour* is irrelevant here -- only enough of each
rolled item's identity to replicate (a) its own `.random()` RNG-consumption
shape and resulting `level()`/`isUpgradable()`/`instanceof Artifact` facts
(the only properties `createItems` branches on), and (b) `Generator`'s
mutated deck state for subsequent draws. Represented as a lightweight
`RolledItem` descriptor rather than a full Item simulation.

Every POTION and SCROLL class is in ExoticPotion/ExoticScroll.regToExo
(verified 12-for-12), so the post-pick exotic-substitution
`Random.Float() < ExoticCrystals.consumableExoticChance()` check ALWAYS
fires for those two categories (consumableExoticChance() == 0 baseline,
so it never actually substitutes -- see `_consume_generator_random_scroll`
precedent in special_rooms.py). No other category's classes appear in
either map, so their dispatch never consumes that extra Float()."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from app.engine.dungeon.spd_levelgen.geom import _to_f32, gate
from app.engine.dungeon.spd_random import SPDRandom

# Generator.floorSetTierProbs (Generator.java:614-620).
_FLOOR_SET_TIER_PROBS: Tuple[Tuple[float, ...], ...] = (
    (0.0, 75.0, 20.0, 4.0, 1.0),
    (0.0, 25.0, 50.0, 20.0, 5.0),
    (0.0, 0.0, 40.0, 50.0, 10.0),
    (0.0, 0.0, 20.0, 40.0, 40.0),
    (0.0, 0.0, 0.0, 20.0, 80.0),
)

# Item-roll RNG-consumption "shapes" (the only thing that matters for outer-
# sequence parity + the level()/isUpgradable()/isArtifact facts createItems
# branches on):
#   WAM    -- Weapon/Armor/MissileWeapon.random(): Int(4), cond Int(5),
#             pushGenerator(Long()) [inner draws don't touch the outer seq]
#   WANDRING -- Wand/Ring.random(): Int(3), cond Int(5), Float() (no push)
#   ARTIFACT -- Artifact.random(): Float() (30% cursed roll, no push)
#   NOOP   -- Item.random() base no-op (Potion/Scroll/Runestone/Seed/Food/
#             Trinket -- none override .random())
#   GOLD   -- Gold.random(): IntRange(30+depth*10, 60+depth*20)
WAM = "wam"
WANDRING = "wandring"
NOOP = "noop"
GOLD_KIND = "gold"  # descriptive only -- GOLD is special-cased in _dispatch_random_category, never reaches _finish_roll


@dataclass(frozen=True)
class RolledItem:
    category: str
    is_artifact: bool
    is_upgradable: bool
    level: int


# Generator.Category enum order + (firstProb, secondProb, kind, defaultProbs,
# defaultProbs2). Categories with firstProb == secondProb == 0 are never
# selected by chances(categoryProbs) (zero-width bucket) -- their probs/seed/
# dropped fields still exist and get reset/seeded in fullReset, and (for
# WEP_Tx/MIS_Tx) get drawn from indirectly via randomWeapon/randomMissile.
_WEP_T1 = (2.0, 0.0, 2.0, 2.0, 2.0, 2.0)
_WEP_T2 = (2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 0.0)
_WEP_T3 = (2.0, 2.0, 2.0, 2.0, 2.0, 2.0)
_WEP_T4 = (2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0)
_WEP_T5 = (2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0)
_MIS_T1 = (3.0, 3.0, 3.0, 0.0)
_MIS_T2 = (3.0, 3.0, 3.0)
_MIS_T3 = (3.0, 3.0, 3.0)
_MIS_T4 = (3.0, 3.0, 3.0)
_MIS_T5 = (3.0, 3.0, 3.0)
_WAND = (3.0,) * 13
_RING = (3.0,) * 12
_ARTIFACT = (1.0, 1.0, 0.0, 1.0, 1.0, 0.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0)
_FOOD = (4.0, 1.0, 0.0)
_POTION = (0.0, 3.0, 2.0, 1.0, 2.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0)
_POTION2 = (0.0, 3.0, 2.0, 2.0, 1.0, 2.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.0)
_SEED = (0.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 1.0)
_SCROLL = (0.0, 3.0, 2.0, 1.0, 2.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0)
_SCROLL2 = (0.0, 3.0, 2.0, 2.0, 1.0, 2.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.0)
_STONE = (0.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 0.0)
_TRINKET = (1.0,) * 17

# (name, firstProb, secondProb, kind, defaultProbs, defaultProbs2, exotic)
# `exotic` -- whether this deck category's classes intersect
# ExoticPotion/ExoticScroll.regToExo (only POTION/SCROLL do).
_CAT_TABLE: Tuple[tuple, ...] = (
    ("TRINKET", 0.0, 0.0, NOOP, _TRINKET, None, False),
    ("WEAPON", 2.0, 2.0, None, None, None, False),
    ("WEP_T1", 0.0, 0.0, WAM, _WEP_T1, None, False),
    ("WEP_T2", 0.0, 0.0, WAM, _WEP_T2, None, False),
    ("WEP_T3", 0.0, 0.0, WAM, _WEP_T3, None, False),
    ("WEP_T4", 0.0, 0.0, WAM, _WEP_T4, None, False),
    ("WEP_T5", 0.0, 0.0, WAM, _WEP_T5, None, False),
    ("ARMOR", 2.0, 1.0, None, None, None, False),
    ("MISSILE", 1.0, 2.0, None, None, None, False),
    ("MIS_T1", 0.0, 0.0, WAM, _MIS_T1, None, False),
    ("MIS_T2", 0.0, 0.0, WAM, _MIS_T2, None, False),
    ("MIS_T3", 0.0, 0.0, WAM, _MIS_T3, None, False),
    ("MIS_T4", 0.0, 0.0, WAM, _MIS_T4, None, False),
    ("MIS_T5", 0.0, 0.0, WAM, _MIS_T5, None, False),
    ("WAND", 1.0, 1.0, WANDRING, _WAND, None, False),
    ("RING", 1.0, 0.0, WANDRING, _RING, None, False),
    ("ARTIFACT", 0.0, 1.0, None, _ARTIFACT, None, False),
    ("FOOD", 0.0, 0.0, NOOP, _FOOD, None, False),
    ("POTION", 8.0, 8.0, NOOP, _POTION, _POTION2, True),
    ("SEED", 1.0, 1.0, NOOP, _SEED, None, False),
    ("SCROLL", 8.0, 8.0, NOOP, _SCROLL, _SCROLL2, True),
    ("STONE", 1.0, 1.0, NOOP, _STONE, None, False),
    ("GOLD", 10.0, 10.0, GOLD_KIND, None, None, False),
)
_CAT_INDEX: Dict[str, int] = {row[0]: i for i, row in enumerate(_CAT_TABLE)}

_WEP_TIERS = ("WEP_T1", "WEP_T2", "WEP_T3", "WEP_T4", "WEP_T5")
_MIS_TIERS = ("MIS_T1", "MIS_T2", "MIS_T3", "MIS_T4", "MIS_T5")


class _CategoryDeck:
    """Mirrors Generator.Category's mutable deck fields (probs/seed/dropped/
    using2ndProbs) for one deck-backed category."""

    __slots__ = ("default_probs", "default_probs2", "using_2nd", "probs", "seed", "dropped")

    def __init__(self, default_probs: Tuple[float, ...], default_probs2: Optional[Tuple[float, ...]],
                 using_2nd: bool, seed: int) -> None:
        self.default_probs = default_probs
        self.default_probs2 = default_probs2
        self.using_2nd = using_2nd
        self.probs: List[float] = list(default_probs2 if (using_2nd and default_probs2) else default_probs)
        self.seed = seed
        self.dropped = 0

    def reset(self) -> None:
        """Generator.reset(cat) -- no RNG."""
        if self.default_probs2 is not None:
            self.using_2nd = not self.using_2nd
            self.probs = list(self.default_probs2 if self.using_2nd else self.default_probs)
        else:
            self.probs = list(self.default_probs)

    def undo_drop(self, index: int) -> None:
        """Generator.undoDrop -- reverts a probs decrement (no RNG)."""
        self.probs[index] += 1


@dataclass
class GeneratorState:
    """Mirrors Generator's static persistent state -- threaded across the
    whole run via RunState, mutated in strict floor-creation order."""

    using_first_deck: bool
    category_probs: Dict[str, float] = field(default_factory=dict)
    decks: Dict[str, _CategoryDeck] = field(default_factory=dict)

    def general_reset(self) -> None:
        """Generator.generalReset() -- no RNG; (re)populates categoryProbs
        from firstProb/secondProb per usingFirstDeck. defaultCatProbs is not
        modeled: it only feeds Generator.randomUsingDefaults() (no-arg),
        which is unreachable here (see _consume_extra_spyglass_loot)."""
        for name, first, second, *_ in _CAT_TABLE:
            self.category_probs[name] = first if self.using_first_deck else second


def init_generator_state(rng: SPDRandom) -> GeneratorState:
    """Port of Generator.fullReset() -- called once at run start via
    RunState.init_for_run, constructing the full persistent-state mirror
    (categoryProbs/usingFirstDeck/per-category decks) threaded across the
    run. usingFirstDeck = Random.Int(2)==0; generalReset(); then per
    category (enum order): using2ndProbs = defaultProbs2!=null && Int(2)==0,
    reset(cat) [no RNG], and if defaultProbs!=null: seed = Random.Long(),
    dropped = 0."""
    using_first_deck = rng.IntMax(2) == 0
    state = GeneratorState(using_first_deck=using_first_deck)
    state.general_reset()

    for name, _first, _second, kind, default_probs, default_probs2, _exotic in _CAT_TABLE:
        using_2nd = False
        if default_probs2 is not None:
            using_2nd = rng.IntMax(2) == 0
        seed = None
        if default_probs is not None:
            seed = rng.Long()
        if default_probs is not None:
            state.decks[name] = _CategoryDeck(default_probs, default_probs2, using_2nd, seed)

    return state


def _chances_map(rng: SPDRandom, ordered: List[Tuple[str, float]]) -> Optional[str]:
    """Port of Random.chances(HashMap<K,Float>) -- NO Math.max(0,...)
    clamping (unlike the array overload); cumulative walk in (Linked-)
    HashMap insertion order, which for `categoryProbs` is Category enum
    declaration order (populated by generalReset() iterating values())."""
    n = len(ordered)
    probs = [w for _, w in ordered]
    total = 0.0
    for w in probs:
        total = _to_f32(total + w)
    if total <= 0:
        return None
    value = rng.FloatMax(total)
    running = probs[0]
    for i in range(n):
        if value < running:
            return ordered[i][0]
        if i + 1 < n:
            running = _to_f32(running + probs[i + 1])
    return None


def _roll_wam(rng: SPDRandom) -> int:
    """Weapon/Armor/MissileWeapon.random(): Int(4), cond Int(5),
    pushGenerator(Random.Long()) -- inner draws (Float() effect roll) consume
    from the freshly-pushed generator and never touch the outer sequence."""
    n = 0
    if rng.IntMax(4) == 0:
        n = 1
        if rng.IntMax(5) == 0:
            n = 2
    rng.Long()
    return n


def _roll_wandring(rng: SPDRandom) -> int:
    """Wand/Ring.random(): Int(3), cond Int(5), Float() (cursed roll, no push)."""
    n = 0
    if rng.IntMax(3) == 0:
        n = 1
        if rng.IntMax(5) == 0:
            n = 2
    rng.Float()
    return n


def _roll_artifact_item(rng: SPDRandom) -> None:
    """Artifact.random(): Float() < 0.3 cursed roll, always +0, no push."""
    rng.Float()


def _roll_gold_item(rng: SPDRandom, depth: int) -> None:
    """Gold.random(): Random.IntRange(30 + depth*10, 60 + depth*20)."""
    rng.IntRange(30 + depth * 10, 60 + depth * 20)


def _finish_roll(rng: SPDRandom, cat: str, kind: str) -> RolledItem:
    if kind == WAM:
        n = _roll_wam(rng)
        return RolledItem(category=cat, is_artifact=False, is_upgradable=True, level=n)
    if kind == WANDRING:
        n = _roll_wandring(rng)
        return RolledItem(category=cat, is_artifact=False, is_upgradable=True, level=n)
    if kind == NOOP:
        return RolledItem(category=cat, is_artifact=False, is_upgradable=False, level=0)
    raise AssertionError(f"unexpected roll kind {kind!r} for category {cat!r}")


def _random_deck_category(state: GeneratorState, rng: SPDRandom, cat: str) -> RolledItem:
    """Port of Generator.random(Category) `default:` branch -- deck-backed
    categories (WAND/RING/FOOD/POTION/SEED... wait SEED routes elsewhere,
    SCROLL/STONE/WEP_Tx/MIS_Tx). All of these have non-null defaultProbs AND
    non-null seed (set in fullReset for every `defaultProbs != null` entry),
    so the push/pop+dropped-replay always runs."""
    _name, _f, _s, kind, _dp, _dp2, exotic = _CAT_TABLE[_CAT_INDEX[cat]]
    deck = state.decks[cat]

    rng.push_generator(deck.seed)
    for _ in range(deck.dropped):
        rng.Long()
    i = rng.chances(deck.probs)
    if i == -1:
        deck.reset()
        i = rng.chances(deck.probs)
    deck.probs[i] -= 1
    rng.pop_generator()
    deck.dropped += 1

    if exotic:
        rng.Float()  # always fires for POTION/SCROLL (every class in regToExo); never substitutes (baseline chance == 0)

    return _finish_roll(rng, cat, kind)


def _random_armor(rng: SPDRandom, depth: int) -> RolledItem:
    """Generator.randomArmor() -- direct creation via floorSetTierProbs, NOT
    deck-based (no push/pop, no probs decrement, no exotic check)."""
    floor_set = int(gate(0, depth // 5, len(_FLOOR_SET_TIER_PROBS) - 1))
    rng.chances(_FLOOR_SET_TIER_PROBS[floor_set])
    n = _roll_wam(rng)  # Armor.random() -- identical shape to Weapon/MissileWeapon
    return RolledItem(category="ARMOR", is_artifact=False, is_upgradable=True, level=n)


def _random_weapon_or_missile(state: GeneratorState, rng: SPDRandom, depth: int, tiers: Tuple[str, ...]) -> RolledItem:
    """Generator.randomWeapon()/randomMissile(): pick a tier via
    floorSetTierProbs, then random(tierCategory) (deck dispatch, no exotic)."""
    floor_set = int(gate(0, depth // 5, len(_FLOOR_SET_TIER_PROBS) - 1))
    tier_idx = rng.chances(_FLOOR_SET_TIER_PROBS[floor_set])
    return _random_deck_category(state, rng, tiers[tier_idx])


def _random_artifact(state: GeneratorState, rng: SPDRandom) -> Optional[RolledItem]:
    """Generator.randomArtifact() -- deck draw with NO reset-on-exhaustion
    (returns None instead, the caller falls back to RING); no exotic check."""
    deck = state.decks["ARTIFACT"]
    rng.push_generator(deck.seed)
    for _ in range(deck.dropped):
        rng.Long()
    i = rng.chances(deck.probs)
    rng.pop_generator()
    deck.dropped += 1

    if i == -1:
        return None
    deck.probs[i] -= 1
    _roll_artifact_item(rng)
    return RolledItem(category="ARTIFACT", is_artifact=True, is_upgradable=False, level=0)


def _random_gold(rng: SPDRandom, depth: int) -> RolledItem:
    """GOLD's `default:` dispatch with `defaultProbs == null`: no push/pop,
    no decrement, no dropped++; chances(probs=[1f]) always picks index 0
    (consumes one FloatMax(1f)); no exotic check; new Gold().random()."""
    rng.chances([1.0])
    _roll_gold_item(rng, depth)
    return RolledItem(category="GOLD", is_artifact=False, is_upgradable=False, level=0)


def _random_using_defaults_seed(rng: SPDRandom) -> RolledItem:
    """Generator.randomUsingDefaults(Category.SEED): SEED.defaultProbs2 is
    null and defaultProbsTotal stays null, so it falls into the array-chances
    branch -- chances(SEED.defaultProbs) (NOT the deck), exotic-map check
    (Plant.Seed classes are in neither regToExo map -- never fires), then
    base Item.random() no-op (Plant.Seed doesn't override .random())."""
    rng.chances(_SEED)
    return RolledItem(category="SEED", is_artifact=False, is_upgradable=True, level=0)


def roll_mimic_prize(state: GeneratorState, rng: SPDRandom, depth: int) -> RolledItem:
    """Port of Mimic.generatePrize(useDecks=true) -- the reward-roll
    `Mimic.spawnAt` always performs when constructing a Mimic/GoldenMimic
    (the only mimicType values `RegularLevel.createItems` ever passes).

    `Challenges.isItemBlocked` is always false on the fresh-game baseline (no
    NO_HERBALISM challenge => Dewdrop check never matters, and none of these
    five reward kinds can ever be null), so the `do {} while(...)` loop body
    runs exactly once. `Dungeon.scalingDepth()` == `Dungeon.depth` absent an
    AscensionChallenge buff (never present on a fresh game). The
    stealthy-mimic second-item draw (`MimicTooth.stealthyMimics()`) is always
    false (no MimicTooth trinket owned), so no second item is ever queued."""
    roll = rng.IntMax(5)
    if roll == 0:
        _roll_gold_item(rng, depth)
        return RolledItem(category="GOLD", is_artifact=False, is_upgradable=False, level=0)
    if roll == 1:
        return _random_weapon_or_missile(state, rng, depth, _MIS_TIERS)
    if roll == 2:
        return _random_armor(rng, depth)
    if roll == 3:
        return _random_weapon_or_missile(state, rng, depth, _WEP_TIERS)
    return _random_deck_category(state, rng, "RING")


# MimicTooth.mimicChanceMultiplier() baseline -- 1.0 absent the trinket (the
# `(mult-1)/4` heap-switch gate and the `0.1*mult` golden-upgrade gate both
# reduce to their no-trinket forms; see RegularLevel.createItems).
MIMIC_CHANCE_MULTIPLIER = 1.0


def spawn_mimic(rng: SPDRandom, level, pos: int, item: RolledItem, depth: int):
    """Port of `Mimic.spawnAt(pos, toDrop)` -> `spawnAt(pos, Mimic.class,
    true, toDrop)` -- consumes generatePrize(useDecks=true)'s reward roll and
    constructs the placed Mimic carrying [toDrop, prize]."""
    from app.engine.dungeon.spd_levelgen.mob_spawner import GenMob
    prize = roll_mimic_prize(level.run_state.generator_state, rng, depth)
    return GenMob(cls_name="Mimic", pos=pos, items=[item, prize])


def spawn_golden_mimic(rng: SPDRandom, level, pos: int, item: RolledItem, depth: int):
    """Port of `Mimic.spawnAt(pos, GoldenMimic.class, toDrop)` -- same
    useDecks=true reward roll, GoldenMimic identity."""
    from app.engine.dungeon.spd_levelgen.mob_spawner import GenMob
    prize = roll_mimic_prize(level.run_state.generator_state, rng, depth)
    return GenMob(cls_name="GoldenMimic", pos=pos, items=[item, prize])


def generator_random(state: GeneratorState, rng: SPDRandom, depth: int) -> RolledItem:
    """Port of Generator.random() (no-arg) -- the full no-arg dispatcher.
    Never returns null (unlike randomArtifact/randomUsingDefaults): the
    ARTIFACT branch substitutes RING on deck exhaustion, and
    chances(categoryProbs) always eventually finds a positive-weight bucket
    after a usingFirstDeck flip + generalReset (both decks have positive
    weights for every selectable category)."""
    ordered = [(name, state.category_probs[name]) for name, *_ in _CAT_TABLE]
    cat = _chances_map(rng, ordered)
    if cat is None:
        state.using_first_deck = not state.using_first_deck
        state.general_reset()
        ordered = [(name, state.category_probs[name]) for name, *_ in _CAT_TABLE]
        cat = _chances_map(rng, ordered)
        assert cat is not None

    state.category_probs[cat] = state.category_probs[cat] - 1

    if cat == "SEED":
        return _random_using_defaults_seed(rng)
    return _dispatch_random_category(state, rng, depth, cat)


def _dispatch_random_category(state: GeneratorState, rng: SPDRandom, depth: int, cat: str) -> RolledItem:
    """Port of Generator.random(Category cat)'s switch -- ARMOR/WEAPON/
    MISSILE/ARTIFACT get bespoke handling, everything else is deck dispatch."""
    if cat == "ARMOR":
        return _random_armor(rng, depth)
    if cat == "WEAPON":
        return _random_weapon_or_missile(state, rng, depth, _WEP_TIERS)
    if cat == "MISSILE":
        return _random_weapon_or_missile(state, rng, depth, _MIS_TIERS)
    if cat == "ARTIFACT":
        result = _random_artifact(state, rng)
        if result is not None:
            return result
        return _random_deck_category(state, rng, "RING")
    if cat == "GOLD":
        return _random_gold(rng, depth)
    return _random_deck_category(state, rng, cat)
