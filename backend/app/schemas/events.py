"""Typed payloads for the per-tick game events placed in STATE_UPDATE.events.

Mirrors the `GameEvent` union in frontend/src/types/contract.ts and the
add_event(...) call sites across engine/game/*.py and engine/entities/item_actions.py.

These models do NOT change the wire format: `add_event` still appends plain dicts.
They exist as a single source of truth and to power an opt-in development check
(see EventsMixin.add_event, gated on the PXD_VALIDATE_EVENTS env var) that validates
each event's `data` against the model below and warns on drift — catching payload
mistakes while building new features without touching production behaviour.
"""

from typing import List, Optional, Tuple

from pydantic import BaseModel, ConfigDict


class _EventData(BaseModel):
    # Events may carry extra context fields; only flag missing/mistyped known ones.
    model_config = ConfigDict(extra="allow")


class AttackData(_EventData):
    source: str
    target: str
    damage: int
    surprise: bool
    crit: bool
    grim_proc: bool


class MissData(_EventData):
    source: str
    target: str
    defense_verb: str


class DamageData(_EventData):
    target: str
    amount: int
    crit: Optional[bool] = None
    grim_proc: Optional[bool] = None
    bleed: Optional[bool] = None


class DeathData(_EventData):
    target: str


class MoveData(_EventData):
    entity: str
    x: int
    y: int


class RangedAttackData(_EventData):
    source: str
    x: int
    y: int
    target_x: int
    target_y: int
    projectile: str
    crit: bool
    grim_proc: bool
    # Present for thrown inventory items (not wands); a serialized item dict.
    item: Optional[dict] = None


class PlaySoundData(_EventData):
    sound: str


class SearchData(_EventData):
    player: str
    x: int
    y: int
    cells: List[Tuple[int, int]]
    revealed_tiles: int


class HealData(_EventData):
    target: str
    amount: int
    x: int
    y: int


class TrapTriggeredData(_EventData):
    player: str
    trap: str
    damage: int


class DrinkData(_EventData):
    player: str
    type: str


class ReadData(_EventData):
    player: str
    item: str


class _Tile(_EventData):
    x: int
    y: int
    tile: int


class MapPatchData(_EventData):
    tiles: List[_Tile]


class PickupData(_EventData):
    player: str
    item: str


class DropData(_EventData):
    player: str
    item: str


class StairsDownData(_EventData):
    player: str


class StairsUpData(_EventData):
    player: str


class ReviveData(_EventData):
    target: str
    source: str


class UnlockData(_EventData):
    player: str
    x: int
    y: int


class LevelUpData(_EventData):
    player: str
    level: int = 0
    tier_unlocked: Optional[int] = None
    talent_points: Optional[dict] = None
    can_choose_subclass: bool = False
    can_choose_armor_ability: bool = False


class SubclassChosenData(_EventData):
    player: str
    subclass: str


class TalentUpgradedData(_EventData):
    player: str
    talent: str
    level: int


class SubclassChoiceAvailableData(_EventData):
    player: str
    options: List[str]


class ArmorAbilityChoiceAvailableData(_EventData):
    player: str
    options: List[str]


class ComboUpdateData(_EventData):
    player: str
    count: int


class ComboMoveUnlockedData(_EventData):
    player: str
    move: str


class BerserkActivatedData(_EventData):
    player: str


class RageChangedData(_EventData):
    player: str
    power: float


class AffixSealData(_EventData):
    player: str
    armor: str


# event "type" -> payload model. Used by the opt-in dev validation hook.
EVENT_MODELS = {
    "ATTACK": AttackData,
    "MISS": MissData,
    "DAMAGE": DamageData,
    "DEATH": DeathData,
    "MOVE": MoveData,
    "RANGED_ATTACK": RangedAttackData,
    "PLAY_SOUND": PlaySoundData,
    "SEARCH": SearchData,
    "HEAL": HealData,
    "TRAP_TRIGGERED": TrapTriggeredData,
    "DRINK": DrinkData,
    "READ": ReadData,
    "MAP_PATCH": MapPatchData,
    "PICKUP": PickupData,
    "DROP": DropData,
    "STAIRS_DOWN": StairsDownData,
    "STAIRS_UP": StairsUpData,
    "REVIVE": ReviveData,
    "UNLOCK": UnlockData,
    "LEVEL_UP": LevelUpData,
    "SUBCLASS_CHOSEN": SubclassChosenData,
    "TALENT_UPGRADED": TalentUpgradedData,
    "SUBCLASS_CHOICE_AVAILABLE": SubclassChoiceAvailableData,
    "ARMOR_ABILITY_CHOICE_AVAILABLE": ArmorAbilityChoiceAvailableData,
    "COMBO_UPDATE": ComboUpdateData,
    "COMBO_MOVE_UNLOCKED": ComboMoveUnlockedData,
    "BERSERK_ACTIVATED": BerserkActivatedData,
    "RAGE_CHANGED": RageChangedData,
    "AFFIX_SEAL": AffixSealData,
}
