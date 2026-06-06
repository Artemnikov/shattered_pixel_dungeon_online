from typing import Dict, Optional, List

from pydantic import BaseModel, Field


class Subclass:
    WARDEN = "warden"
    BERSERKER = "berserker"
    GLADIATOR = "gladiator"


class ArmorAbilityType:
    HEROIC_LEAP = "heroic_leap"
    SHOCKWAVE = "shockwave"
    ENDURE = "endure"


class Talent:
    # Tier 1 (level 2, 2pts)
    IRON_WILL = "iron_will"
    IRON_STOMACH = "iron_stomach"
    RESTORED_STRENGTH = "restored_strength"
    LIGHT_ARMOR = "light_armor"

    # Tier 2 (level 7, 2pts) — Berserker
    BERSERK_RESTORATION = "berserk_restoration"
    DEATHLESS_FURY = "deathless_fury"
    ENRAGED_CATALYST = "enraged_catalyst"
    BERSERK_RUSH = "berserk_rush"

    # Tier 2 (level 7, 2pts) — Gladiator
    COMBO_SHIELD = "combo_shield"
    COMBO_RESTORATION = "combo_restoration"
    SLOW_COMBO = "slow_combo"
    LETHAL_HIT = "lethal_hit"

    # Tier 3 (level 13, 3pts)
    ENDLESS_RAGE = "endless_rage"
    IMPOSING_PRESENCE = "imposing_presence"
    SUB_ATK = "sub_atk"
    SUB_DEF = "sub_def"
    ENHANCED_COMBO = "enhanced_combo"
    COMBO_SURGE = "combo_surge"

    # Tier 4 (level 21, 4pts) — Berserker
    RISK_REWARD = "risk_reward"
    BERSERK_DURATION = "berserk_duration"
    RAMPAGE = "rampage"

    # Tier 4 (level 21, 4pts) — Gladiator
    COMBO_AURA = "combo_aura"
    SAVAGE_CAPACITY = "savage_capacity"
    DEADLY_FOLLOWUP = "deadly_followup"

    # Armor abilities (Tier 3 talents that choose the ability)
    HEROIC_LEAP = "heroic_leap_talent"
    SHOCKWAVE = "shockwave_talent"
    ENDURE_ABILITY = "endure_ability_talent"


# Maps talent name → (max_points, tier, subclass_required_or_None)
TALENT_DEFS: Dict[str, tuple[int, int, Optional[str]]] = {
    # Tier 1 — universal
    Talent.IRON_WILL: (2, 1, None),
    Talent.IRON_STOMACH: (2, 1, None),
    Talent.RESTORED_STRENGTH: (2, 1, None),
    Talent.LIGHT_ARMOR: (2, 1, None),
    # Tier 2 — Berserker
    Talent.BERSERK_RESTORATION: (2, 2, Subclass.BERSERKER),
    Talent.DEATHLESS_FURY: (2, 2, Subclass.BERSERKER),
    Talent.ENRAGED_CATALYST: (2, 2, Subclass.BERSERKER),
    Talent.BERSERK_RUSH: (2, 2, Subclass.BERSERKER),
    # Tier 2 — Gladiator
    Talent.COMBO_SHIELD: (2, 2, Subclass.GLADIATOR),
    Talent.COMBO_RESTORATION: (2, 2, Subclass.GLADIATOR),
    Talent.SLOW_COMBO: (2, 2, Subclass.GLADIATOR),
    Talent.LETHAL_HIT: (2, 2, Subclass.GLADIATOR),
    # Tier 3 — universal (but some are subclass-specific)
    Talent.ENDLESS_RAGE: (3, 3, Subclass.BERSERKER),
    Talent.IMPOSING_PRESENCE: (3, 3, Subclass.BERSERKER),
    Talent.ENHANCED_COMBO: (3, 3, Subclass.GLADIATOR),
    Talent.COMBO_SURGE: (3, 3, Subclass.GLADIATOR),
    Talent.SUB_ATK: (3, 3, None),
    Talent.SUB_DEF: (3, 3, None),
    # Armor ability talents (Tier 3, exclusive — pick one of three)
    Talent.HEROIC_LEAP: (1, 3, None),
    Talent.SHOCKWAVE: (1, 3, None),
    Talent.ENDURE_ABILITY: (1, 3, None),
    # Tier 4 — Berserker
    Talent.RISK_REWARD: (4, 4, Subclass.BERSERKER),
    Talent.BERSERK_DURATION: (4, 4, Subclass.BERSERKER),
    Talent.RAMPAGE: (4, 4, Subclass.BERSERKER),
    # Tier 4 — Gladiator
    Talent.COMBO_AURA: (4, 4, Subclass.GLADIATOR),
    Talent.SAVAGE_CAPACITY: (4, 4, Subclass.GLADIATOR),
    Talent.DEADLY_FOLLOWUP: (4, 4, Subclass.GLADIATOR),
}


# Level thresholds where talent tiers unlock
TIER_UNLOCK_LEVELS: Dict[int, int] = {
    1: 2,
    2: 7,
    3: 13,
    4: 21,
}

# Tier → max points per talent
TIER_MAX_POINTS: Dict[int, int] = {
    1: 2,
    2: 2,
    3: 3,
    4: 4,
}

# Combo moves unlocked by combo count threshold
COMBO_MOVES: Dict[int, str] = {
    2: "clobber",
    4: "slam",
    6: "parry",
    8: "crush",
    10: "fury",
}

COST_ARMOR_ABILITY = 35  # Leap/Shockwave charge cost
COST_ENDURE = 50  # Endure charge cost (slightly higher)


class TalentInfo(BaseModel):
    talents: Dict[str, int] = Field(default_factory=dict)

    def get(self, name: str) -> int:
        return self.talents.get(name, 0)

    def has(self, name: str) -> bool:
        return self.talents.get(name, 0) > 0

    def level(self, name: str) -> int:
        return self.talents.get(name, 0)

    def max_level(self, name: str) -> int:
        return TALENT_DEFS.get(name, (0, 0, None))[0]


class SubclassInfo(BaseModel):
    subclass: Optional[str] = None
    talent_info: TalentInfo = Field(default_factory=TalentInfo)
