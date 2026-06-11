"""Outgoing server -> client message envelopes: INIT, STATE_UPDATE, PONG.

These wrap the per-tick frames that main.py used to build as bare dicts. The nested
entity / item / event payloads are deliberately left loose (`list[Any]` /
`dict[str, Any]`, `extra="allow"`): they're already serialized, unidentified-masked
and augmented with computed fields (actions/description/appearance) in
engine/game/serialization.py, so re-validating them strictly here would drop keys
the client relies on.

Build a model, then `model_dump(exclude_none=True)` for `send_json` — this produces
byte-identical keys to the old hand-built dicts (e.g. INIT only carries `player_id`
on first connect, where it's set; floor-change INIT leaves it None -> excluded).
"""

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict

from .common import Difficulty


class _Envelope(BaseModel):
    model_config = ConfigDict(extra="allow")


class PongMessage(_Envelope):
    type: Literal["PONG"] = "PONG"


class InitMessage(_Envelope):
    type: Literal["INIT"] = "INIT"
    depth: int
    grid: List[List[int]]
    width: int
    height: int
    traps: List[Dict[str, Any]]
    custom_tiles: List[Dict[str, Any]] = []
    # Only set on the very first INIT after connecting; omitted on floor change.
    player_id: Optional[str] = None


class StateUpdateMessage(_Envelope):
    type: Literal["STATE_UPDATE"] = "STATE_UPDATE"
    depth: int
    difficulty: Difficulty
    players: List[Any]
    mobs: List[Any]
    items: List[Any]
    visible_tiles: List[Any]
    traps: List[Dict[str, Any]]
    gold: int
    energy: int
    events: List[Any]
