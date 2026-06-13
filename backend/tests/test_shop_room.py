"""Tests for the depth-tiered ShopRoom (floors 6/11/16)."""
import pytest

from app.engine.entities.mobs import Shopkeeper
from app.engine.manager import GameInstance


@pytest.mark.parametrize("depth", [6, 11, 16])
def test_shop_floor_has_shopkeeper_and_stock(depth):
    g = GameInstance("shoptest")
    floor = g._get_or_create_floor(depth)

    shopkeepers = [m for m in floor.mobs.values() if isinstance(m, Shopkeeper)]
    assert len(shopkeepers) == 1

    for_sale = [i for i in floor.items.values() if i.for_sale]
    assert len(for_sale) == 17

    # Artifacts are intentionally priceless (value()==0, matches SPD); every
    # other shop item should have a positive sell-back value.
    for item in for_sale:
        if item.kind != "artifact":
            assert item.value() > 0


@pytest.mark.parametrize("depth", [6, 11, 16])
def test_shop_floor_generation_is_deterministic(depth):
    g1 = GameInstance("shoptest_a")
    g2 = GameInstance("shoptest_a")

    floor1 = g1._get_or_create_floor(depth)
    floor2 = g2._get_or_create_floor(depth)

    names1 = sorted(i.name for i in floor1.items.values() if i.for_sale)
    names2 = sorted(i.name for i in floor2.items.values() if i.for_sale)
    assert names1 == names2
