"""Tests for Shopkeeper NPC interaction and buy/sell mechanics."""
from app.engine.entities.base import HealthPotion, Position, SmallRation, WornShortsword
from app.engine.entities.mobs import Shopkeeper
from app.engine.manager import GameInstance


def _add_shopkeeper(game, floor, pos):
    shop = Shopkeeper(id="shop1", pos=Position(x=pos[0], y=pos[1]))
    floor.mobs["shop1"] = shop
    return shop


def test_npc_interact_opens_shop_with_stock():
    g = GameInstance("t1")
    p = g.add_player("p1", "Bob")
    floor = g._get_or_create_floor(p.floor_id)

    shop_pos = (p.pos.x + 1, p.pos.y)
    _add_shopkeeper(g, floor, shop_pos)
    potion = HealthPotion(id="pot1", pos=Position(x=shop_pos[0], y=shop_pos[1]), for_sale=True)
    floor.items["pot1"] = potion

    g.npc_interact("p1", "shop1")

    events = [e for e in g.events if e["type"] == "SHOP_OPEN"]
    assert len(events) == 1
    stock = events[0]["data"]["stock"]
    assert any(i["id"] == "pot1" for i in stock)
    sold_item = next(i for i in stock if i["id"] == "pot1")
    assert sold_item["value"] == 30 * 5 * (p.floor_id // 5 + 1)


def test_npc_interact_too_far_does_nothing():
    g = GameInstance("t1")
    p = g.add_player("p1", "Bob")
    floor = g._get_or_create_floor(p.floor_id)
    _add_shopkeeper(g, floor, (p.pos.x + 5, p.pos.y + 5))

    g.npc_interact("p1", "shop1")

    assert not any(e["type"] == "SHOP_OPEN" for e in g.events)


def test_shop_buy_deducts_gold_and_grants_item():
    g = GameInstance("t1")
    p = g.add_player("p1", "Bob")
    floor = g._get_or_create_floor(p.floor_id)
    shop_pos = (p.pos.x + 1, p.pos.y)
    _add_shopkeeper(g, floor, shop_pos)

    potion = HealthPotion(id="pot1", pos=Position(x=shop_pos[0], y=shop_pos[1]), for_sale=True)
    floor.items["pot1"] = potion
    p.gold = 1000

    price = g._buy_price(potion, p.floor_id)
    g.shop_buy("p1", "shop1", "pot1")

    assert p.gold == 1000 - price
    assert "pot1" not in floor.items
    assert any(isinstance(i, HealthPotion) for i in p.inventory)


def test_shop_buy_fails_without_enough_gold():
    g = GameInstance("t1")
    p = g.add_player("p1", "Bob")
    floor = g._get_or_create_floor(p.floor_id)
    shop_pos = (p.pos.x + 1, p.pos.y)
    _add_shopkeeper(g, floor, shop_pos)

    potion = HealthPotion(id="pot1", pos=Position(x=shop_pos[0], y=shop_pos[1]), for_sale=True)
    floor.items["pot1"] = potion
    p.gold = 0

    g.shop_buy("p1", "shop1", "pot1")

    assert "pot1" in floor.items
    assert not any(isinstance(i, HealthPotion) for i in p.inventory)


def test_shop_sell_grants_gold_and_removes_item():
    g = GameInstance("t1")
    p = g.add_player("p1", "Bob")
    p.gold = 0
    ration = SmallRation(id="r1")
    p.add_to_inventory(ration)

    g.shop_sell("p1", "r1")

    assert p.gold == ration.value()
    assert p.belongings.get_item("r1") is None


def test_shop_sell_rejects_zero_value_items():
    g = GameInstance("t1")
    p = g.add_player("p1", "Bob")
    p.gold = 0

    from app.engine.entities.base import Key
    key = Key(id="k1", name="Key")
    p.add_to_inventory(key)

    g.shop_sell("p1", "k1")

    assert p.gold == 0
    assert p.belongings.get_item("k1") is not None


def test_for_sale_items_not_auto_picked_up():
    g = GameInstance("t1")
    p = g.add_player("p1", "Bob")
    floor = g._get_or_create_floor(p.floor_id)
    floor.items["pot1"] = HealthPotion(id="pot1", pos=Position(x=p.pos.x + 1, y=p.pos.y), for_sale=True)

    g.move_entity("p1", 1, 0)

    assert "pot1" in floor.items
    assert not any(isinstance(i, HealthPotion) for i in p.inventory)
