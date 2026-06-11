"""Validation tests for the WebSocket message schemas (app/schemas).

Guards two contracts:
- incoming ClientMessage variants parse, and malformed input is rejected;
- outgoing INIT / STATE_UPDATE envelopes dump to exactly the keys the client
  already expects (so the Pydantic layer doesn't silently change the wire format).
"""

import pytest
from pydantic import ValidationError

from app.schemas import CLIENT_MESSAGE_ADAPTER, InitMessage, StateUpdateMessage
from app.schemas.common import Direction
from app.schemas import messages as msg


# --- incoming: ClientMessage ------------------------------------------------

@pytest.mark.parametrize("payload, expected_type", [
    ({"type": "PING"}, msg.Ping),
    ({"type": "MOVE", "direction": "UP"}, msg.Move),
    ({"type": "MOVE_INTENT", "dx": 1, "dy": -1}, msg.MoveIntent),
    ({"type": "MOVE_STOP"}, msg.MoveStop),
    ({"type": "MOVE_TO", "x": 3, "y": 4}, msg.MoveTo),
    ({"type": "EXECUTE_ITEM_ACTION", "item_id": "i1", "action": "EQUIP"}, msg.ExecuteItemAction),
    ({"type": "SET_QUICKSLOT", "index": 0, "item_id": "i1"}, msg.SetQuickslot),
    ({"type": "USE_QUICKSLOT", "index": 1}, msg.UseQuickslot),
    ({"type": "EQUIP_ITEM", "item_id": "i1"}, msg.EquipItem),
    ({"type": "DROP_ITEM", "item_id": "i1"}, msg.DropItem),
    ({"type": "USE_ITEM", "item_id": "i1"}, msg.UseItem),
    ({"type": "RANGED_ATTACK", "item_id": "i1", "target_x": 2, "target_y": 5}, msg.RangedAttack),
    ({"type": "CHANGE_DIFFICULTY", "difficulty": "hard"}, msg.ChangeDifficulty),
    ({"type": "SEARCH"}, msg.Search),
    ({"type": "WAIT"}, msg.Wait),
])
def test_valid_client_messages_parse(payload, expected_type):
    parsed = CLIENT_MESSAGE_ADAPTER.validate_python(payload)
    assert isinstance(parsed, expected_type)


@pytest.mark.parametrize("payload", [
    {"type": "MOVE"},                                  # missing direction
    {"type": "MOVE", "direction": "DIAGONAL"},         # bad enum value
    {"type": "MOVE_TO", "x": 1},                        # missing y
    {"type": "RANGED_ATTACK", "item_id": "i1"},        # missing target coords
    {"type": "CHANGE_DIFFICULTY", "difficulty": "insane"},  # bad enum value
    {"type": "SET_QUICKSLOT", "item_id": "i1"},        # missing index
    {"type": "NONSENSE"},                              # unknown discriminator
    {},                                                # no type
])
def test_invalid_client_messages_rejected(payload):
    with pytest.raises(ValidationError):
        CLIENT_MESSAGE_ADAPTER.validate_python(payload)


def test_extra_fields_ignored():
    parsed = CLIENT_MESSAGE_ADAPTER.validate_python({"type": "SEARCH", "stray": 123})
    assert isinstance(parsed, msg.Search)


def test_direction_delta_mapping():
    assert Direction.UP.delta == (0, -1)
    assert Direction.DOWN.delta == (0, 1)
    assert Direction.LEFT.delta == (-1, 0)
    assert Direction.RIGHT.delta == (1, 0)
    assert Direction.UP_LEFT.delta == (-1, -1)
    assert Direction.UP_RIGHT.delta == (1, -1)
    assert Direction.DOWN_LEFT.delta == (-1, 1)
    assert Direction.DOWN_RIGHT.delta == (1, 1)


# --- outgoing: envelope wire-format parity ----------------------------------

def test_init_first_connect_keys_match():
    init = InitMessage(player_id="p1", depth=1, grid=[[0]], width=1, height=1, traps=[])
    assert set(init.model_dump(exclude_none=True)) == {
        "type", "player_id", "depth", "grid", "width", "height", "traps", "custom_tiles",
    }


def test_init_floor_change_omits_player_id():
    init = InitMessage(depth=2, grid=[[0]], width=1, height=1, traps=[])
    dumped = init.model_dump(exclude_none=True)
    assert "player_id" not in dumped
    assert set(dumped) == {"type", "depth", "grid", "width", "height", "traps", "custom_tiles"}


def test_state_update_keys_match():
    update = StateUpdateMessage(
        depth=1, difficulty="normal", players=[], mobs=[], items=[],
        visible_tiles=[], traps=[], gold=0, energy=0, events=[],
    )
    assert set(update.model_dump(exclude_none=True)) == {
        "type", "depth", "difficulty", "players", "mobs", "items",
        "visible_tiles", "traps", "gold", "energy", "events",
    }


def test_state_update_passes_nested_payloads_through_untouched():
    player = {"id": "p1", "inventory": [], "equipped_weapon": None, "extra": 1}
    item = {"kind": "potion", "actions": ["DRINK"], "description": "x"}
    event = {"type": "ATTACK", "data": {"source": "a", "target": "b"}}
    update = StateUpdateMessage(
        depth=1, difficulty="normal", players=[player], mobs=[], items=[item],
        visible_tiles=[[1, 2]], traps=[], gold=5, energy=3, events=[event],
    )
    dumped = update.model_dump(exclude_none=True)
    assert dumped["players"][0] == player
    assert dumped["items"][0] == item
    assert dumped["events"][0] == event
