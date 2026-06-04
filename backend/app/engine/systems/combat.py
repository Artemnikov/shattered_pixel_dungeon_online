import random
from typing import Callable, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from app.engine.entities.base import Entity, Position


def _roll_damage(attacker: "Entity", result: dict) -> int:
    """Roll base damage, applying surprise damage floor if applicable."""
    dmg_min = attacker.get_damage_min()
    dmg_max = attacker.get_damage_max()

    if result.get("surprise"):
        floor = attacker.get_surprise_damage_floor()
        if floor > 0:
            diff = dmg_max - dmg_min
            dmg_min = dmg_min + int(diff * floor)

    dmg_roll = random.randint(dmg_min, dmg_max)

    # Kinetic conserved damage
    if attacker.conserved_damage > 0:
        dmg_roll += attacker.conserved_damage
        attacker.conserved_damage = 0

    return dmg_roll


def _apply_post_dr_multipliers(raw_damage: int, attacker: "Entity", defender: "Entity", result: dict) -> int:
    """Apply post-DR multipliers: crit bonus, Fury, Vulnerable."""
    effective = raw_damage

    if result.get("surprise") and attacker.crit_damage_bonus > 0:
        effective = int(effective * (1 + attacker.crit_damage_bonus))

    if attacker.has_fury:
        effective = int(effective * 1.5)

    vuln = getattr(defender, "vulnerable", 0)
    if vuln > 0:
        effective = int(effective * 1.33)

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

    dmg_roll = _roll_damage(attacker, result)
    dr_roll = random.randint(defender.get_dr_min(), defender.get_dr_max())
    raw_damage = max(0, dmg_roll - dr_roll)

    # Invisibility dispel on attack
    if getattr(attacker, "invisible", 0) > 0:
        attacker.invisible = 0
        attacker.remove_buff("invisibility")
        attacker.remove_buff("preparation")

    # Pre-DR defense proc (glyphs, abilities)
    if hasattr(defender, "defense_proc") and raw_damage > 0:
        raw_damage = defender.defense_proc(raw_damage, attacker, floor_mobs, tile_x, tile_y)
        if raw_damage <= 0:
            return result

    # Post-DR multipliers
    effective_damage = _apply_post_dr_multipliers(raw_damage, attacker, defender, result)

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
    if getattr(attacker, "invisible", 0) > 0:
        attacker.invisible = 0
        attacker.remove_buff("invisibility")
        attacker.remove_buff("preparation")

    # Pre-DR defense proc
    if hasattr(defender, "defense_proc") and raw_damage > 0:
        raw_damage = defender.defense_proc(raw_damage, attacker, floor_mobs, tile_x, tile_y)
        if raw_damage <= 0:
            return result

    # Post-DR multipliers
    effective_damage = _apply_post_dr_multipliers(raw_damage, attacker, defender, result)

    hp_before = defender.hp
    actual_damage = defender.take_damage(max(0, effective_damage))
    result["damage"] = actual_damage

    if attacker.grim_max_chance > 0 and actual_damage > 0:
        _check_grim(attacker, defender, result)

    _check_kinetic(attacker, raw_damage, defender, hp_before)

    if hasattr(attacker, "attack_proc") and actual_damage > 0:
        attacker.attack_proc(defender)

    return result
