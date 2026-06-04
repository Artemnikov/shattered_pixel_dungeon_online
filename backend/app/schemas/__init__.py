"""Pydantic schemas for the WebSocket message layer.

- messages:  incoming client -> server (validated at the socket boundary)
- envelopes: outgoing server -> client frames (INIT / STATE_UPDATE / PONG)
- events:    typed per-tick event payloads (source of truth + opt-in dev check)
"""

from .common import Difficulty, Direction
from .envelopes import InitMessage, PongMessage, StateUpdateMessage
from .events import EVENT_MODELS
from .messages import CLIENT_MESSAGE_ADAPTER, ClientMessage

__all__ = [
    "Difficulty",
    "Direction",
    "InitMessage",
    "PongMessage",
    "StateUpdateMessage",
    "EVENT_MODELS",
    "CLIENT_MESSAGE_ADAPTER",
    "ClientMessage",
]
