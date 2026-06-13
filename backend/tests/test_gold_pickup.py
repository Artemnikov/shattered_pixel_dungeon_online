"""Tests for Gold pickup: adds to Player.gold counter, never enters inventory."""
from app.engine.entities.base import Gold, Position
from app.engine.manager import GameInstance


def test_gold_pickup_adds_to_counter_and_skips_inventory():
    g = GameInstance("t1")
    p = g.add_player("p1", "Bob")
    starting_gold = p.gold

    floor = g._get_or_create_floor(p.floor_id)
    floor.items["gold1"] = Gold(id="gold1", name="Gold", quantity=15, pos=Position(x=p.pos.x + 1, y=p.pos.y))

    g.move_entity("p1", 1, 0)

    assert p.gold == starting_gold + 15
    assert "gold1" not in floor.items
    assert all(not isinstance(i, Gold) for i in p.inventory)
