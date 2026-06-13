"""Tests for the Waterskin item: Dewdrop collection on pickup and the DRINK
action's missing-HP%-based instant heal (and Shielding Dew shield top-up)."""
from app.engine.entities.base import Action, Dewdrop, Position, Waterskin
from app.engine.manager import GameInstance


def _clear_starting_waterskin(p):
    """Players start with a Waterskin (HeroClass.initHero) — remove it so
    tests can control the Waterskin's id/volume directly."""
    for item in list(p.inventory):
        if isinstance(item, Waterskin):
            p.belongings.backpack.items.remove(item)
            p.quickslot.clear_item(item.id)


def test_dew_collection_fills_waterskin_and_skips_inventory():
    g = GameInstance("t1")
    p = g.add_player("p1", "Bob")
    _clear_starting_waterskin(p)
    p.add_to_inventory(Waterskin(id="ws1"))

    floor = g._get_or_create_floor(p.floor_id)
    floor.items["dew1"] = Dewdrop(id="dew1", quantity=3, pos=Position(x=p.pos.x + 1, y=p.pos.y))

    g.move_entity("p1", 1, 0)

    ws = p.belongings.get_item("ws1")
    assert ws.volume == 3
    assert "dew1" not in floor.items
    assert all(not isinstance(i, Dewdrop) for i in p.inventory)


def test_dew_collection_caps_at_max_volume():
    g = GameInstance("t1")
    p = g.add_player("p1", "Bob")
    _clear_starting_waterskin(p)
    p.add_to_inventory(Waterskin(id="ws1", volume=19))

    floor = g._get_or_create_floor(p.floor_id)
    floor.items["dew1"] = Dewdrop(id="dew1", quantity=5, pos=Position(x=p.pos.x + 1, y=p.pos.y))

    g.move_entity("p1", 1, 0)

    ws = p.belongings.get_item("ws1")
    assert ws.volume == Waterskin.MAX_VOLUME


def test_dew_falls_through_to_normal_pickup_without_waterskin():
    g = GameInstance("t1")
    p = g.add_player("p1", "Bob")
    _clear_starting_waterskin(p)

    floor = g._get_or_create_floor(p.floor_id)
    floor.items["dew1"] = Dewdrop(id="dew1", quantity=2, pos=Position(x=p.pos.x + 1, y=p.pos.y))

    g.move_entity("p1", 1, 0)

    assert any(isinstance(i, Dewdrop) for i in p.inventory)


def test_drink_heals_based_on_missing_hp():
    g = GameInstance("t1")
    p = g.add_player("p1", "Bob")
    max_hp = p.get_total_max_hp()
    p.hp = max_hp // 2  # 50% missing -> needs 10 drops (5% each)
    p.add_to_inventory(Waterskin(id="ws1", volume=20))

    g.execute_item_action("p1", "ws1", Action.DRINK)

    ws = p.belongings.get_item("ws1")
    assert p.hp > max_hp // 2
    assert ws.volume < 20


def test_drink_unavailable_when_empty():
    ws = Waterskin(id="ws1", volume=0)
    assert Action.DRINK not in ws.actions()
    assert ws.default_action() is None


def test_shielding_dew_grants_shield_with_excess_drops():
    g = GameInstance("t1")
    p = g.add_player("p1", "Bob")
    p.subclass_info.talent_info.talents["shielding_dew"] = 1
    p.hp = p.get_total_max_hp()  # full HP, so all drops go to shield
    p.add_to_inventory(Waterskin(id="ws1", volume=20))

    g.execute_item_action("p1", "ws1", Action.DRINK)

    shield = p.get_shield("dew")
    assert shield is not None and shield.amount > 0
