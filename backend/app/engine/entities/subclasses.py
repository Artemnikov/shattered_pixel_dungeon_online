from typing import Dict, Optional, List, Set

from pydantic import BaseModel, Field


class Subclass:
    WARDEN = "warden"
    BERSERKER = "berserker"
    GLADIATOR = "gladiator"
    # Rogue
    ASSASSIN = "assassin"
    FREERUNNER = "freerunner"
    # Mage
    BATTLEMAGE = "battlemage"
    WARLOCK = "warlock"
    # Huntress
    SNIPER = "sniper"


# Which subclasses each hero class may choose at level 6.
CLASS_SUBCLASSES: Dict[str, tuple[str, ...]] = {
    "warrior": (Subclass.BERSERKER, Subclass.GLADIATOR),
    "rogue": (Subclass.ASSASSIN, Subclass.FREERUNNER),
    "mage": (Subclass.BATTLEMAGE, Subclass.WARLOCK),
    "huntress": (Subclass.SNIPER, Subclass.WARDEN),
}


class ArmorAbilityType:
    HEROIC_LEAP = "heroic_leap"
    SHOCKWAVE = "shockwave"
    ENDURE = "endure"
    # Rogue
    SMOKE_BOMB = "smoke_bomb"
    DEATH_MARK = "death_mark"
    SHADOW_CLONE = "shadow_clone"
    # Mage
    ELEMENTAL_BLAST = "elemental_blast"
    WILD_MAGIC = "wild_magic"
    WARP_BEACON = "warp_beacon"
    # Huntress
    SPECTRAL_BLADES = "spectral_blades"
    NATURES_POWER = "natures_power"
    SPIRIT_HAWK = "spirit_hawk"


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

    # ===================== ROGUE =====================
    # Tier 1 (level 2)
    CACHED_RATIONS = "cached_rations"
    THIEFS_INTUITION = "thiefs_intuition"
    SUCKER_PUNCH = "sucker_punch"
    PROTECTIVE_SHADOWS = "protective_shadows"

    # Tier 2 (level 7)
    MYSTICAL_MEAL = "mystical_meal"
    INSCRIBED_STEALTH = "inscribed_stealth"
    WIDE_SEARCH = "wide_search"
    SILENT_STEPS = "silent_steps"
    ROGUES_FORESIGHT = "rogues_foresight"

    # Tier 3 (level 13) — class
    ENHANCED_RINGS = "enhanced_rings"
    LIGHT_CLOAK = "light_cloak"
    # Tier 3 — Assassin
    ENHANCED_LETHALITY = "enhanced_lethality"
    ASSASSINS_REACH = "assassins_reach"
    BOUNTY_HUNTER = "bounty_hunter"
    # Tier 3 — Freerunner
    EVASIVE_ARMOR = "evasive_armor"
    PROJECTILE_MOMENTUM = "projectile_momentum"
    SPEEDY_STEALTH = "speedy_stealth"
    # Tier 3 — armor ability selection
    SMOKE_BOMB = "smoke_bomb_talent"
    DEATH_MARK = "death_mark_talent"
    SHADOW_CLONE = "shadow_clone_talent"

    # Tier 4 (level 21) — Smoke Bomb
    HASTY_RETREAT = "hasty_retreat"
    BODY_REPLACEMENT = "body_replacement"
    SHADOW_STEP = "shadow_step"
    # Tier 4 — Death Mark
    FEAR_THE_REAPER = "fear_the_reaper"
    DEATHLY_DURABILITY = "deathly_durability"
    DOUBLE_MARK = "double_mark"
    # Tier 4 — Shadow Clone
    SHADOW_BLADE = "shadow_blade"
    CLONED_ARMOR = "cloned_armor"
    PERFECT_COPY = "perfect_copy"

    # ===================== MAGE =====================
    # Tier 1 (level 2)
    EMPOWERING_MEAL = "empowering_meal"
    SCHOLARS_INTUITION = "scholars_intuition"
    LINGERING_MAGIC = "lingering_magic"
    BACKUP_BARRIER = "backup_barrier"
    # Tier 2 (level 7)
    ENERGIZING_MEAL = "energizing_meal"
    INSCRIBED_POWER = "inscribed_power"
    WAND_PRESERVATION = "wand_preservation"
    ARCANE_VISION = "arcane_vision"
    SHIELD_BATTERY = "shield_battery"
    # Tier 3 (level 13) — class
    DESPERATE_POWER = "desperate_power"
    ALLY_WARP = "ally_warp"
    # Tier 3 — Battlemage
    EMPOWERED_STRIKE = "empowered_strike"
    MYSTICAL_CHARGE = "mystical_charge"
    EXCESS_CHARGE = "excess_charge"
    # Tier 3 — Warlock
    SOUL_EATER = "soul_eater"
    SOUL_SIPHON = "soul_siphon"
    NECROMANCERS_MINIONS = "necromancers_minions"
    # Tier 3 — armor ability selection
    ELEMENTAL_BLAST_ABILITY = "elemental_blast_talent"
    WILD_MAGIC_ABILITY = "wild_magic_talent"
    WARP_BEACON_ABILITY = "warp_beacon_talent"
    # Tier 4 (level 21) — Elemental Blast
    BLAST_RADIUS = "blast_radius"
    ELEMENTAL_POWER_TALENT = "elemental_power_talent"
    REACTIVE_BARRIER = "reactive_barrier"
    # Tier 4 — Wild Magic
    WILD_POWER = "wild_power"
    FIRE_EVERYTHING = "fire_everything"
    CONSERVED_MAGIC = "conserved_magic"
    # Tier 4 — Warp Beacon
    TELEFRAG = "telefrag"
    REMOTE_BEACON = "remote_beacon"
    LONGRANGE_WARP = "longrange_warp"

    # ===================== HUNTRESS =====================
    # Tier 1 (level 2)
    NATURES_BOUNTY = "natures_bounty"
    SURVIVALISTS_INTUITION = "survivalists_intuition"
    FOLLOWUP_STRIKE = "followup_strike"
    NATURES_AID = "natures_aid"
    # Tier 2 (level 7)
    INVIGORATING_MEAL = "invigorating_meal"
    LIQUID_NATURE = "liquid_nature"
    REJUVENATING_STEPS = "rejuvenating_steps"
    HEIGHTENED_SENSES = "heightened_senses"
    DURABLE_PROJECTILES = "durable_projectiles"
    # Tier 3 (level 13) — class
    POINT_BLANK = "point_blank"
    SEER_SHOT = "seer_shot"
    # Tier 3 — Sniper
    FARSIGHT = "farsight"
    SHARED_ENCHANTMENT = "shared_enchantment"
    SHARED_UPGRADES = "shared_upgrades"
    # Tier 3 — Warden
    DURABLE_TIPS = "durable_tips"
    BARKSKIN = "barkskin"
    SHIELDING_DEW = "shielding_dew"
    # Tier 3 — armor ability selection
    SPECTRAL_BLADES_ABILITY = "spectral_blades_talent"
    NATURES_POWER_ABILITY = "natures_power_talent"
    SPIRIT_HAWK_ABILITY = "spirit_hawk_talent"
    # Tier 4 (level 21) — Spectral Blades
    FAN_OF_BLADES = "fan_of_blades"
    PROJECTING_BLADES = "projecting_blades"
    SPIRIT_BLADES = "spirit_blades"
    # Tier 4 — Natures Power
    GROWING_POWER = "growing_power"
    NATURES_WRATH = "natures_wrath"
    WILD_MOMENTUM = "wild_momentum"
    # Tier 4 — Spirit Hawk
    EAGLE_EYE = "eagle_eye"
    GO_FOR_THE_EYES = "go_for_the_eyes"
    SWIFT_SPIRIT = "swift_spirit"


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

    # ===================== ROGUE =====================
    # Tier 1
    Talent.CACHED_RATIONS: (2, 1, None),
    Talent.THIEFS_INTUITION: (2, 1, None),
    Talent.SUCKER_PUNCH: (2, 1, None),
    Talent.PROTECTIVE_SHADOWS: (2, 1, None),
    # Tier 2
    Talent.MYSTICAL_MEAL: (2, 2, None),
    Talent.INSCRIBED_STEALTH: (2, 2, None),
    Talent.WIDE_SEARCH: (2, 2, None),
    Talent.SILENT_STEPS: (2, 2, None),
    Talent.ROGUES_FORESIGHT: (2, 2, None),
    # Tier 3 — class
    Talent.ENHANCED_RINGS: (3, 3, None),
    Talent.LIGHT_CLOAK: (3, 3, None),
    # Tier 3 — Assassin
    Talent.ENHANCED_LETHALITY: (3, 3, Subclass.ASSASSIN),
    Talent.ASSASSINS_REACH: (3, 3, Subclass.ASSASSIN),
    Talent.BOUNTY_HUNTER: (3, 3, Subclass.ASSASSIN),
    # Tier 3 — Freerunner
    Talent.EVASIVE_ARMOR: (3, 3, Subclass.FREERUNNER),
    Talent.PROJECTILE_MOMENTUM: (3, 3, Subclass.FREERUNNER),
    Talent.SPEEDY_STEALTH: (3, 3, Subclass.FREERUNNER),
    # Tier 3 — armor ability selection (exclusive — pick one of three)
    Talent.SMOKE_BOMB: (1, 3, None),
    Talent.DEATH_MARK: (1, 3, None),
    Talent.SHADOW_CLONE: (1, 3, None),
    # Tier 4 — Smoke Bomb
    Talent.HASTY_RETREAT: (4, 4, None),
    Talent.BODY_REPLACEMENT: (4, 4, None),
    Talent.SHADOW_STEP: (4, 4, None),
    # Tier 4 — Death Mark
    Talent.FEAR_THE_REAPER: (4, 4, None),
    Talent.DEATHLY_DURABILITY: (4, 4, None),
    Talent.DOUBLE_MARK: (4, 4, None),
    # Tier 4 — Shadow Clone
    Talent.SHADOW_BLADE: (4, 4, None),
    Talent.CLONED_ARMOR: (4, 4, None),
    Talent.PERFECT_COPY: (4, 4, None),

    # ===================== MAGE =====================
    # Tier 1
    Talent.EMPOWERING_MEAL: (2, 1, None),
    Talent.SCHOLARS_INTUITION: (2, 1, None),
    Talent.LINGERING_MAGIC: (2, 1, None),
    Talent.BACKUP_BARRIER: (2, 1, None),
    # Tier 2
    Talent.ENERGIZING_MEAL: (2, 2, None),
    Talent.INSCRIBED_POWER: (2, 2, None),
    Talent.WAND_PRESERVATION: (2, 2, None),
    Talent.ARCANE_VISION: (2, 2, None),
    Talent.SHIELD_BATTERY: (2, 2, None),
    # Tier 3 — class
    Talent.DESPERATE_POWER: (3, 3, None),
    Talent.ALLY_WARP: (3, 3, None),
    # Tier 3 — Battlemage
    Talent.EMPOWERED_STRIKE: (3, 3, Subclass.BATTLEMAGE),
    Talent.MYSTICAL_CHARGE: (3, 3, Subclass.BATTLEMAGE),
    Talent.EXCESS_CHARGE: (3, 3, Subclass.BATTLEMAGE),
    # Tier 3 — Warlock
    Talent.SOUL_EATER: (3, 3, Subclass.WARLOCK),
    Talent.SOUL_SIPHON: (3, 3, Subclass.WARLOCK),
    Talent.NECROMANCERS_MINIONS: (3, 3, Subclass.WARLOCK),
    # Tier 3 — armor ability selection
    Talent.ELEMENTAL_BLAST_ABILITY: (1, 3, None),
    Talent.WILD_MAGIC_ABILITY: (1, 3, None),
    Talent.WARP_BEACON_ABILITY: (1, 3, None),
    # Tier 4 — Elemental Blast
    Talent.BLAST_RADIUS: (4, 4, None),
    Talent.ELEMENTAL_POWER_TALENT: (4, 4, None),
    Talent.REACTIVE_BARRIER: (4, 4, None),
    # Tier 4 — Wild Magic
    Talent.WILD_POWER: (4, 4, None),
    Talent.FIRE_EVERYTHING: (4, 4, None),
    Talent.CONSERVED_MAGIC: (4, 4, None),
    # Tier 4 — Warp Beacon
    Talent.TELEFRAG: (4, 4, None),
    Talent.REMOTE_BEACON: (4, 4, None),
    Talent.LONGRANGE_WARP: (4, 4, None),

    # ===================== HUNTRESS =====================
    # Tier 1
    Talent.NATURES_BOUNTY: (2, 1, None),
    Talent.SURVIVALISTS_INTUITION: (2, 1, None),
    Talent.FOLLOWUP_STRIKE: (2, 1, None),
    Talent.NATURES_AID: (2, 1, None),
    # Tier 2
    Talent.INVIGORATING_MEAL: (2, 2, None),
    Talent.LIQUID_NATURE: (2, 2, None),
    Talent.REJUVENATING_STEPS: (2, 2, None),
    Talent.HEIGHTENED_SENSES: (2, 2, None),
    Talent.DURABLE_PROJECTILES: (2, 2, None),
    # Tier 3 — class
    Talent.POINT_BLANK: (3, 3, None),
    Talent.SEER_SHOT: (3, 3, None),
    # Tier 3 — Sniper
    Talent.FARSIGHT: (3, 3, Subclass.SNIPER),
    Talent.SHARED_ENCHANTMENT: (3, 3, Subclass.SNIPER),
    Talent.SHARED_UPGRADES: (3, 3, Subclass.SNIPER),
    # Tier 3 — Warden
    Talent.DURABLE_TIPS: (3, 3, Subclass.WARDEN),
    Talent.BARKSKIN: (3, 3, Subclass.WARDEN),
    Talent.SHIELDING_DEW: (3, 3, Subclass.WARDEN),
    # Tier 3 — armor ability selection
    Talent.SPECTRAL_BLADES_ABILITY: (1, 3, None),
    Talent.NATURES_POWER_ABILITY: (1, 3, None),
    Talent.SPIRIT_HAWK_ABILITY: (1, 3, None),
    # Tier 4 — Spectral Blades
    Talent.FAN_OF_BLADES: (4, 4, None),
    Talent.PROJECTING_BLADES: (4, 4, None),
    Talent.SPIRIT_BLADES: (4, 4, None),
    # Tier 4 — Natures Power
    Talent.GROWING_POWER: (4, 4, None),
    Talent.NATURES_WRATH: (4, 4, None),
    Talent.WILD_MOMENTUM: (4, 4, None),
    # Tier 4 — Spirit Hawk
    Talent.EAGLE_EYE: (4, 4, None),
    Talent.GO_FOR_THE_EYES: (4, 4, None),
    Talent.SWIFT_SPIRIT: (4, 4, None),
}


# Talents restricted to a hero class (the engine otherwise gates only by
# subclass). Talents absent from this map are available to any class.
TALENT_CLASS_REQ: Dict[str, str] = {
    # Warrior
    Talent.IRON_WILL: "warrior", Talent.IRON_STOMACH: "warrior",
    Talent.RESTORED_STRENGTH: "warrior", Talent.LIGHT_ARMOR: "warrior",
    Talent.HEROIC_LEAP: "warrior", Talent.SHOCKWAVE: "warrior",
    Talent.ENDURE_ABILITY: "warrior", Talent.SUB_ATK: "warrior", Talent.SUB_DEF: "warrior",
    # Rogue
    Talent.CACHED_RATIONS: "rogue", Talent.THIEFS_INTUITION: "rogue",
    Talent.SUCKER_PUNCH: "rogue", Talent.PROTECTIVE_SHADOWS: "rogue",
    Talent.MYSTICAL_MEAL: "rogue", Talent.INSCRIBED_STEALTH: "rogue",
    Talent.WIDE_SEARCH: "rogue", Talent.SILENT_STEPS: "rogue", Talent.ROGUES_FORESIGHT: "rogue",
    Talent.ENHANCED_RINGS: "rogue", Talent.LIGHT_CLOAK: "rogue",
    Talent.SMOKE_BOMB: "rogue", Talent.DEATH_MARK: "rogue", Talent.SHADOW_CLONE: "rogue",
    Talent.HASTY_RETREAT: "rogue", Talent.BODY_REPLACEMENT: "rogue", Talent.SHADOW_STEP: "rogue",
    Talent.FEAR_THE_REAPER: "rogue", Talent.DEATHLY_DURABILITY: "rogue", Talent.DOUBLE_MARK: "rogue",
    Talent.SHADOW_BLADE: "rogue", Talent.CLONED_ARMOR: "rogue", Talent.PERFECT_COPY: "rogue",
    # Mage
    Talent.EMPOWERING_MEAL: "mage", Talent.SCHOLARS_INTUITION: "mage",
    Talent.LINGERING_MAGIC: "mage", Talent.BACKUP_BARRIER: "mage",
    Talent.ENERGIZING_MEAL: "mage", Talent.INSCRIBED_POWER: "mage",
    Talent.WAND_PRESERVATION: "mage", Talent.ARCANE_VISION: "mage", Talent.SHIELD_BATTERY: "mage",
    Talent.DESPERATE_POWER: "mage", Talent.ALLY_WARP: "mage",
    Talent.ELEMENTAL_BLAST_ABILITY: "mage", Talent.WILD_MAGIC_ABILITY: "mage", Talent.WARP_BEACON_ABILITY: "mage",
    Talent.BLAST_RADIUS: "mage", Talent.ELEMENTAL_POWER_TALENT: "mage", Talent.REACTIVE_BARRIER: "mage",
    Talent.WILD_POWER: "mage", Talent.FIRE_EVERYTHING: "mage", Talent.CONSERVED_MAGIC: "mage",
    Talent.TELEFRAG: "mage", Talent.REMOTE_BEACON: "mage", Talent.LONGRANGE_WARP: "mage",
    # Huntress
    Talent.NATURES_BOUNTY: "huntress", Talent.SURVIVALISTS_INTUITION: "huntress",
    Talent.FOLLOWUP_STRIKE: "huntress", Talent.NATURES_AID: "huntress",
    Talent.INVIGORATING_MEAL: "huntress", Talent.LIQUID_NATURE: "huntress",
    Talent.REJUVENATING_STEPS: "huntress", Talent.HEIGHTENED_SENSES: "huntress", Talent.DURABLE_PROJECTILES: "huntress",
    Talent.POINT_BLANK: "huntress", Talent.SEER_SHOT: "huntress",
    Talent.SPECTRAL_BLADES_ABILITY: "huntress", Talent.NATURES_POWER_ABILITY: "huntress", Talent.SPIRIT_HAWK_ABILITY: "huntress",
    Talent.FAN_OF_BLADES: "huntress", Talent.PROJECTING_BLADES: "huntress", Talent.SPIRIT_BLADES: "huntress",
    Talent.GROWING_POWER: "huntress", Talent.NATURES_WRATH: "huntress", Talent.WILD_MOMENTUM: "huntress",
    Talent.EAGLE_EYE: "huntress", Talent.GO_FOR_THE_EYES: "huntress", Talent.SWIFT_SPIRIT: "huntress",
}


# Armor-ability talents → the ability they unlock (first point locks the choice).
ABILITY_TALENTS: Dict[str, str] = {
    Talent.HEROIC_LEAP: ArmorAbilityType.HEROIC_LEAP,
    Talent.SHOCKWAVE: ArmorAbilityType.SHOCKWAVE,
    Talent.ENDURE_ABILITY: ArmorAbilityType.ENDURE,
    Talent.SMOKE_BOMB: ArmorAbilityType.SMOKE_BOMB,
    Talent.DEATH_MARK: ArmorAbilityType.DEATH_MARK,
    Talent.SHADOW_CLONE: ArmorAbilityType.SHADOW_CLONE,
    # Mage
    Talent.ELEMENTAL_BLAST_ABILITY: ArmorAbilityType.ELEMENTAL_BLAST,
    Talent.WILD_MAGIC_ABILITY: ArmorAbilityType.WILD_MAGIC,
    Talent.WARP_BEACON_ABILITY: ArmorAbilityType.WARP_BEACON,
    # Huntress
    Talent.SPECTRAL_BLADES_ABILITY: ArmorAbilityType.SPECTRAL_BLADES,
    Talent.NATURES_POWER_ABILITY: ArmorAbilityType.NATURES_POWER,
    Talent.SPIRIT_HAWK_ABILITY: ArmorAbilityType.SPIRIT_HAWK,
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
    # Available talent points per tier (tier → count). Player earns these when a
    # new tier unlocks (level 2, 7, 13, 21) and consumes them on upgrade_talent().
    talent_points: Dict[int, int] = Field(default_factory=dict)
    # Tracks which milestone levels (2, 6, 13) have had their events emitted.
    # Prevents re-emission on subsequent level-ups and ensures events fire even
    # when a multi-level jump skips the exact milestone level.
    emitted_milestones: Set[int] = Field(default_factory=set, exclude=True)
