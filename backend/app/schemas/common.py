"""Shared scalar types for the WebSocket message schemas.

These mirror the hand-written helpers in `frontend/src/types/contract.ts`
(Direction, Difficulty) so the typed message layer stays in sync with the client.
"""

from enum import Enum
from typing import Literal, Tuple

# Mirrors `Difficulty` in contract.ts and the `Difficulty` constants in
# app/engine/entities/base.py.
Difficulty = Literal["easy", "normal", "hard"]


class Direction(str, Enum):
    """The eight movement directions a MOVE message can carry.

    `delta` returns the (dx, dy) step for the direction, replacing the
    if/elif ladder that used to live in the websocket handler in main.py.
    """

    UP = "UP"
    DOWN = "DOWN"
    LEFT = "LEFT"
    RIGHT = "RIGHT"
    UP_LEFT = "UP_LEFT"
    UP_RIGHT = "UP_RIGHT"
    DOWN_LEFT = "DOWN_LEFT"
    DOWN_RIGHT = "DOWN_RIGHT"

    @property
    def delta(self) -> Tuple[int, int]:
        return _DELTAS[self]


_DELTAS = {
    Direction.UP: (0, -1),
    Direction.DOWN: (0, 1),
    Direction.LEFT: (-1, 0),
    Direction.RIGHT: (1, 0),
    Direction.UP_LEFT: (-1, -1),
    Direction.UP_RIGHT: (1, -1),
    Direction.DOWN_LEFT: (-1, 1),
    Direction.DOWN_RIGHT: (1, 1),
}
