import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import uuid
from app.engine.entities.base import Position
from app.engine.manager import GameInstance


def _floor_heights(game, depths):
    return {d: len(game.generate_floor(d).grid) for d in depths}


def test_los_uses_queried_floor_dimensions_not_global():
    """Regression: floors generate at different sizes. _is_in_los must use the
    queried floor's dimensions, not the most-recently-generated floor's. Before
    the fix this raised IndexError in _effective_blocking."""
    game = GameInstance("dim-test")
    heights = _floor_heights(game, range(1, 6))

    short = min(heights, key=heights.get)
    tall = max(heights, key=heights.get)
    assert heights[tall] > heights[short], "need two floors of differing height"

    # Regenerate the taller floor last so the (pre-fix) global dims point at it
    # while we query the shorter floor.
    game.generate_floor(tall)

    # A cell that is in-bounds for the short floor but past the global height
    # ordering is what used to overflow los[y].
    p1 = Position(x=1, y=1)
    p2 = Position(x=2, y=2)
    result = game._is_in_los(p1, p2, floor_id=short)
    assert isinstance(result, bool)


def test_get_state_reports_player_floor_dimensions():
    """State snapshot carries the player's own floor dims regardless of which
    floor was generated last."""
    game = GameInstance("dim-state-test")
    heights = _floor_heights(game, range(1, 6))
    short = min(heights, key=heights.get)
    tall = max(heights, key=heights.get)

    pid = str(uuid.uuid4())
    game.add_player(pid, "Hero")
    game.players[pid].floor_id = short

    # Generate the taller floor last.
    game.generate_floor(tall)

    state = game.get_state(pid)
    floor = game._get_or_create_floor(short)
    assert state["width"] == floor.width
    assert state["height"] == floor.height
