import math
import random
from typing import Callable, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from app.engine.entities.base import Entity, Position


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
    }

    if not attacker.is_alive or not defender.is_alive:
        return result

    # Surprise attack: if defender can't see attacker, auto-hit
    if is_in_los and not is_in_los(defender.pos, attacker.pos):
        result["surprise"] = True
        result["hit"] = True
    else:
        acu_roll = random.random() * attacker.attack_skill
        def_roll = random.random() * defender.get_effective_defense_skill()
        if acu_roll < def_roll:
            result["missed"] = True
            return result
        result["hit"] = True

    result["rolled"] = True

    dmg_roll = random.randint(attacker.get_damage_min(), attacker.get_damage_max())
    dr_roll = random.randint(defender.get_dr_min(), defender.get_dr_max())
    raw_damage = max(0, dmg_roll - dr_roll)

    # Pre-DR defense proc (glyphs, abilities)
    if hasattr(defender, "defense_proc") and raw_damage > 0:
        raw_damage = defender.defense_proc(raw_damage, attacker, floor_mobs, tile_x, tile_y)
        if raw_damage <= 0:
            return result

    # Post-DR multipliers (Vulnerable, Resistances, etc.)
    effective_damage = raw_damage

    # Vulnerable: +33% after DR (can't be mitigated by armor)
    vuln = getattr(defender, "vulnerable", 0)
    if vuln > 0:
        effective_damage = int(effective_damage * 1.33)

    actual_damage = defender.take_damage(max(0, effective_damage))
    result["damage"] = actual_damage

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
    }

    if not attacker.is_alive or not defender.is_alive:
        return result

    if is_in_los and not is_in_los(defender.pos, attacker.pos):
        result["surprise"] = True
        result["hit"] = True
    else:
        acu_roll = random.random() * attacker.attack_skill
        def_roll = random.random() * defender.get_effective_defense_skill()
        if acu_roll < def_roll:
            result["missed"] = True
            return result
        result["hit"] = True

    result["rolled"] = True

    dmg_roll = random.randint(attacker.get_damage_min(), attacker.get_damage_max())
    dr_roll = random.randint(defender.get_dr_min(), defender.get_dr_max())
    raw_damage = max(0, dmg_roll - dr_roll)

    # Pre-DR defense proc
    if hasattr(defender, "defense_proc") and raw_damage > 0:
        raw_damage = defender.defense_proc(raw_damage, attacker, floor_mobs, tile_x, tile_y)
        if raw_damage <= 0:
            return result

    # Post-DR multipliers
    effective_damage = raw_damage
    vuln = getattr(defender, "vulnerable", 0)
    if vuln > 0:
        effective_damage = int(effective_damage * 1.33)

    actual_damage = defender.take_damage(max(0, effective_damage))
    result["damage"] = actual_damage

    if hasattr(attacker, "attack_proc") and actual_damage > 0:
        attacker.attack_proc(defender)

    return result
