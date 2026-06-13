"""Incoming client -> server WebSocket messages.

A discriminated union (on `type`) validated at the socket boundary in main.py so
malformed input is rejected with a clear error instead of raising KeyError deep in
a handler. Mirrors the `ClientMessage` union in frontend/src/types/contract.ts and
the handler branches in main.py.

`extra="ignore"` keeps the layer forward/backward compatible: a client that sends
an extra field (or one we've since dropped) still validates on its known fields.
"""

from typing import Annotated, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from .common import Difficulty, Direction


class _ClientMessageBase(BaseModel):
    model_config = ConfigDict(extra="ignore")


class Ping(_ClientMessageBase):
    type: Literal["PING"]


class Move(_ClientMessageBase):
    type: Literal["MOVE"]
    direction: Direction


class MoveIntent(_ClientMessageBase):
    type: Literal["MOVE_INTENT"]
    dx: int = 0
    dy: int = 0


class MoveStop(_ClientMessageBase):
    type: Literal["MOVE_STOP"]


class MoveTo(_ClientMessageBase):
    type: Literal["MOVE_TO"]
    x: int
    y: int


class ExecuteItemAction(_ClientMessageBase):
    type: Literal["EXECUTE_ITEM_ACTION"]
    item_id: str
    action: str
    target_x: Optional[int] = None
    target_y: Optional[int] = None


class SetQuickslot(_ClientMessageBase):
    type: Literal["SET_QUICKSLOT"]
    index: int
    item_id: str


class UseQuickslot(_ClientMessageBase):
    type: Literal["USE_QUICKSLOT"]
    index: int
    target_x: Optional[int] = None
    target_y: Optional[int] = None


class EquipItem(_ClientMessageBase):
    type: Literal["EQUIP_ITEM"]
    item_id: str


class DropItem(_ClientMessageBase):
    type: Literal["DROP_ITEM"]
    item_id: str


class UseItem(_ClientMessageBase):
    type: Literal["USE_ITEM"]
    item_id: str


class RangedAttack(_ClientMessageBase):
    type: Literal["RANGED_ATTACK"]
    item_id: str
    target_x: int
    target_y: int


class ChangeDifficulty(_ClientMessageBase):
    type: Literal["CHANGE_DIFFICULTY"]
    difficulty: Difficulty


class Search(_ClientMessageBase):
    type: Literal["SEARCH"]


class Wait(_ClientMessageBase):
    type: Literal["WAIT"]


class ChooseSubclass(_ClientMessageBase):
    type: Literal["CHOOSE_SUBCLASS"]
    subclass: str


class UpgradeTalent(_ClientMessageBase):
    type: Literal["UPGRADE_TALENT"]
    talent: str


class UseArmorAbility(_ClientMessageBase):
    type: Literal["USE_ARMOR_ABILITY"]
    ability: str
    target_x: Optional[int] = None
    target_y: Optional[int] = None


class TriggerBerserk(_ClientMessageBase):
    type: Literal["TRIGGER_BERSERK"]


class PreparationStrike(_ClientMessageBase):
    type: Literal["PREPARATION_STRIKE"]
    target_x: int
    target_y: int


class MetamorphChoose(_ClientMessageBase):
    type: Literal["METAMORPH_CHOOSE"]
    talent: str


class MetamorphReplace(_ClientMessageBase):
    type: Literal["METAMORPH_REPLACE"]
    old_talent: str
    new_talent: str


class AdminTeleport(_ClientMessageBase):
    type: Literal["ADMIN_TELEPORT"]
    target_floor: int


class NpcInteract(_ClientMessageBase):
    type: Literal["NPC_INTERACT"]
    npc_id: str


class ShopBuy(_ClientMessageBase):
    type: Literal["SHOP_BUY"]
    npc_id: str
    item_id: str


class ShopSell(_ClientMessageBase):
    type: Literal["SHOP_SELL"]
    item_id: str


class ImpClaimReward(_ClientMessageBase):
    type: Literal["IMP_CLAIM_REWARD"]
    npc_id: str


ClientMessage = Annotated[
    Union[
        Ping,
        Move,
        MoveIntent,
        MoveStop,
        MoveTo,
        ExecuteItemAction,
        SetQuickslot,
        UseQuickslot,
        EquipItem,
        DropItem,
        UseItem,
        RangedAttack,
        ChangeDifficulty,
        Search,
        Wait,
        ChooseSubclass,
        UpgradeTalent,
        UseArmorAbility,
        TriggerBerserk,
        PreparationStrike,
        MetamorphChoose,
        MetamorphReplace,
        AdminTeleport,
        NpcInteract,
        ShopBuy,
        ShopSell,
        ImpClaimReward,
    ],
    Field(discriminator="type"),
]

CLIENT_MESSAGE_ADAPTER: TypeAdapter[ClientMessage] = TypeAdapter(ClientMessage)
