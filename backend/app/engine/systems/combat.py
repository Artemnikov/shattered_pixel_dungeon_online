import random
from typing import Callable, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from app.engine.entities.base import Entity, Position


def _preparation(attacker: "Entity", defender: "Entity") -> Optional[dict]:
    """Assassin Preparation effect for a surprise melee strike, or None.

    Returns {ko, dmg_mult, rolls} where `ko` flags an instant kill of a
    sufficiently-wounded foe. Requires the attacker to be an invisible Assassin
    with at least one Preparation tier accrued.
    """
    info = getattr(attacker, "subclass_info", None)
    if info is None or info.subclass != "assassin":
        return None
    if getattr(attacker, "invisible", 0) <= 0:
        return None
    from app.engine.game.rogue import (
        prep_tier, prep_damage_bonus, prep_damage_rolls, prep_ko_threshold,
    )
    secs = getattr(attacker, "prep_seconds", 0.0)
    if prep_tier(secs) < 0:
        return None
    enhanced_lethality = attacker.talent_info.level("enhanced_lethality")
    threshold = prep_ko_threshold(secs, enhanced_lethality)
    if getattr(defender, "is_boss", False) or getattr(defender, "is_miniboss", False):
        threshold /= 5.0
    hp_ratio = defender.hp / max(defender.max_hp, 1)
    return {
        "ko": hp_ratio < threshold,
        "dmg_mult": 1.0 + prep_damage_bonus(secs),
        "rolls": prep_damage_rolls(secs),
    }


def _dispel_stealth(attacker: "Entity") -> None:
    """Attacking breaks stealth: clear invisibility, the cloak's sustained
    stealth flag, and Preparation."""
    if getattr(attacker, "invisible", 0) > 0:
        attacker.invisible = 0
    attacker.remove_buff("invisibility")
    attacker.remove_buff("shadows")
    if getattr(attacker, "cloak_stealth_active", False):
        attacker.cloak_stealth_active = False
    if hasattr(attacker, "prep_seconds"):
        attacker.prep_seconds = 0.0


def _roll_damage(attacker: "Entity", result: dict, prep: Optional[dict] = None) -> int:
    """Roll base damage, applying surprise damage floor if applicable."""
    dmg_min = attacker.get_damage_min()
    dmg_max = attacker.get_damage_max()

    if result.get("surprise"):
        floor = attacker.get_surprise_damage_floor()
        if floor > 0:
            diff = dmg_max - dmg_min
            dmg_min = dmg_min + int(diff * floor)

    dmg_roll = random.randint(dmg_min, dmg_max)
    # Preparation: keep the highest of N rolls.
    if prep is not None:
        for _ in range(prep["rolls"] - 1):
            r = random.randint(dmg_min, dmg_max)
            if r > dmg_roll:
                dmg_roll = r

    # Sucker Punch (rogue T1): bonus damage on a surprise attack.
    if result.get("surprise"):
        sp = getattr(attacker, "talent_info", None)
        if sp is not None and sp.level("sucker_punch") > 0:
            dmg_roll += random.randint(sp.level("sucker_punch"), 2)

    # Talent flat damage bonus (rampage stacks, etc.)
    talent_bonus = getattr(attacker, "get_talent_damage_bonus", lambda: 0)()
    dmg_roll += talent_bonus

    # Kinetic conserved damage
    if attacker.conserved_damage > 0:
        dmg_roll += attacker.conserved_damage
        attacker.conserved_damage = 0

    return dmg_roll


def _apply_talent_multipliers(effective: int, attacker: "Entity", defender: "Entity", result: dict, is_ranged: bool = False) -> int:
    """Apply talent-based post-DR damage modifiers."""
    ti = getattr(attacker, "talent_info", None)
    if ti is None:
        return effective

    # Risk Reward (warrior T4 berserker): +dmg based on missing HP
    rr = ti.level("risk_reward")
    if rr > 0:
        hp_ratio = attacker.hp / max(attacker.get_total_max_hp(), 1)
        mult = 1.0 + rr * 0.1 * (1 - hp_ratio)
        effective = int(effective * mult)

    # Deadly Followup (warrior T4 gladiator): +dmg based on combo count
    df = ti.level("deadly_followup")
    if df > 0:
        combo = getattr(attacker, "combo_count", 0)
        if combo > 0:
            mult = 1.0 + df * 0.04 * combo
            effective = int(effective * mult)

    # Lethal Hit (warrior T2 gladiator): bonus at high combo
    lh = ti.level("lethal_hit")
    if lh > 0:
        combo = getattr(attacker, "combo_count", 0)
        if combo >= 4:
            effective = int(effective * (1.0 + lh * 0.1))

    # Followup Strike (huntress T1): +dmg on melee after ranged hit
    if not is_ranged:
        fs = ti.level("followup_strike")
        if fs > 0 and getattr(attacker, "_last_action", None) == "ranged":
            effective = int(effective * (1.0 + fs * 0.17))

    # Point Blank (huntress T3): extra ranged damage at close range
    if is_ranged:
        pb = ti.level("point_blank")
        if pb > 0:
            effective = int(effective * (1.0 + pb * 0.25))

    return effective


def _apply_post_dr_multipliers(raw_damage: int, attacker: "Entity", defender: "Entity", result: dict, is_ranged: bool = False) -> int:
    """Apply post-DR multipliers: crit bonus, Fury, Vulnerable, Berserk."""
    effective = raw_damage

    if result.get("surprise") and attacker.crit_damage_bonus > 0:
        effective = int(effective * (1 + attacker.crit_damage_bonus))

    if attacker.has_fury:
        effective = int(effective * 1.5)

    berserk_power = getattr(attacker, "berserk_power", 0.0)
    berserk_active = getattr(attacker, "berserk_active", False)
    if berserk_active and berserk_power > 0:
        effective = int(effective * (1.0 + berserk_power * 0.5))

    effective = _apply_talent_multipliers(effective, attacker, defender, result, is_ranged)

    vuln = getattr(defender, "vulnerable", 0)
    if vuln > 0:
        effective = int(effective * 1.33)

    # Rogue Death Mark: marked foes take 25% more damage.
    if defender.has_buff("death_mark"):
        effective = int(effective * 1.25)

    return effective


def _check_grim(attacker: "Entity", defender: "Entity", result: dict):
    """Grim enchantment: % max-HP execute scaling with missing HP."""
    grim_chance = attacker.grim_max_chance
    if grim_chance <= 0 or not defender.is_alive:
        return 0
    hp_ratio = defender.hp / max(defender.max_hp, 1)
    final_chance = grim_chance * (1 - hp_ratio) ** 2
    if random.random() < final_chance:
        extra_dmg = int(defender.hp * 0.5)
        if extra_dmg > 0:
            defender.hp -= extra_dmg
            result["grim_proc"] = True
            if defender.hp <= 0:
                defender.hp = 0
                defender.is_alive = False
            return extra_dmg
    return 0


def _check_kinetic(attacker: "Entity", raw_damage: int, defender: "Entity", hp_before: int):
    """Kinetic enchantment: overflow damage beyond fatality is conserved."""
    if not defender.is_alive and hp_before > 0:
        overflow = raw_damage - hp_before
        if overflow > 0:
            attacker.conserved_damage += overflow


def resolve_melee_attack(
    attacker: "Entity",
    defender: "Entity",
    floor_mobs: dict,
    tile_x: int,
    tile_y: int,
    is_in_los: Optional[Callable[["Position", "Position"], bool]] = None,
) -> dict:
    result = {
        "hit": False,
        "damage": 0,
        "rolled": False,
        "missed": False,
        "surprise": False,
        "crit": False,
        "grim_proc": False,
    }

    if not attacker.is_alive or not defender.is_alive:
        return result

    # Invisible attacker: always surprise attack (auto-hit)
    if getattr(attacker, "invisible", 0) > 0:
        result["surprise"] = True
        result["hit"] = True
    # Surprise attack: if defender can't see attacker, auto-hit
    elif is_in_los and not is_in_los(defender.pos, attacker.pos):
        result["surprise"] = True
        result["hit"] = True
    else:
        acu_roll = random.random() * attacker.attack_skill
        def_roll = random.random() * defender.get_effective_defense_skill()
        if acu_roll < def_roll:
            result["missed"] = True
            result["defense_verb"] = defender.defense_verb
            return result
        result["hit"] = True

    result["rolled"] = True
    result["crit"] = result["surprise"]

    # Assassin Preparation: instant-KO a wounded foe, else amplify the strike.
    prep = _preparation(attacker, defender) if result["surprise"] else None
    if prep is not None and prep["ko"]:
        hp_before = defender.hp
        defender.take_damage(max(1, defender.hp))
        result["damage"] = hp_before
        result["ko"] = True
        _dispel_stealth(attacker)
        return result

    dmg_roll = _roll_damage(attacker, result, prep)
    dr_roll = random.randint(defender.get_dr_min(), defender.get_dr_max())
    raw_damage = max(0, dmg_roll - dr_roll)

    # Invisibility dispel on attack
    _dispel_stealth(attacker)

    # Pre-DR defense proc (glyphs, abilities)
    if hasattr(defender, "defense_proc") and raw_damage > 0:
        raw_damage = defender.defense_proc(raw_damage, attacker, floor_mobs, tile_x, tile_y)
        if raw_damage <= 0:
            return result

    # Post-DR multipliers (melee = not ranged)
    effective_damage = _apply_post_dr_multipliers(raw_damage, attacker, defender, result, is_ranged=False)
    if prep is not None:
        effective_damage = int(effective_damage * prep["dmg_mult"])

    hp_before = defender.hp
    actual_damage = defender.take_damage(max(0, effective_damage))
    result["damage"] = actual_damage

    # Grim execute check (inverse: grim is on the ATTACKER's weapon)
    if attacker.grim_max_chance > 0 and actual_damage > 0:
        _check_grim(attacker, defender, result)

    # Kinetic overflow
    _check_kinetic(attacker, raw_damage, defender, hp_before)

    if hasattr(attacker, "attack_proc") and actual_damage > 0:
        attacker.attack_proc(defender)

    return result


def resolve_ranged_attack(
    attacker: "Entity",
    defender: "Entity",
    item,
    floor_mobs: dict,
    tile_x: int,
    tile_y: int,
    is_in_los: Optional[Callable[["Position", "Position"], bool]] = None,
) -> dict:
    result = {
        "hit": False,
        "damage": 0,
        "rolled": False,
        "missed": False,
        "surprise": False,
        "crit": False,
        "grim_proc": False,
    }

    if not attacker.is_alive or not defender.is_alive:
        return result

    if getattr(attacker, "invisible", 0) > 0:
        result["surprise"] = True
        result["hit"] = True
    elif is_in_los and not is_in_los(defender.pos, attacker.pos):
        result["surprise"] = True
        result["hit"] = True
    else:
        acu_roll = random.random() * attacker.attack_skill
        def_roll = random.random() * defender.get_effective_defense_skill()
        if acu_roll < def_roll:
            result["missed"] = True
            result["defense_verb"] = defender.defense_verb
            return result
        result["hit"] = True

    result["rolled"] = True
    result["crit"] = result["surprise"]

    dmg_roll = _roll_damage(attacker, result)
    dr_roll = random.randint(defender.get_dr_min(), defender.get_dr_max())
    raw_damage = max(0, dmg_roll - dr_roll)

    # Invisibility dispel on attack
    _dispel_stealth(attacker)

    # Pre-DR defense proc
    if hasattr(defender, "defense_proc") and raw_damage > 0:
        raw_damage = defender.defense_proc(raw_damage, attacker, floor_mobs, tile_x, tile_y)
        if raw_damage <= 0:
            return result

    # Post-DR multipliers (ranged)
    effective_damage = _apply_post_dr_multipliers(raw_damage, attacker, defender, result, is_ranged=True)

    hp_before = defender.hp
    actual_damage = defender.take_damage(max(0, effective_damage))
    result["damage"] = actual_damage

    if attacker.grim_max_chance > 0 and actual_damage > 0:
        _check_grim(attacker, defender, result)

    _check_kinetic(attacker, raw_damage, defender, hp_before)

    if hasattr(attacker, "attack_proc") and actual_damage > 0:
        attacker.attack_proc(defender)

    return result
