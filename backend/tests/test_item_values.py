"""Tests for ItemBase.value() — the SPD shop sell-price table."""
import pytest

from app.engine.entities.base import (
    Armor,
    ArmorEnchantment,
    Bag,
    Boomerang,
    Dagger,
    Dewdrop,
    ElixirOfAquaticRejuvenation,
    GooBlob,
    HealthPotion,
    Key,
    MagicalHolster,
    PotionOfExperience,
    Ring,
    Scroll,
    ScrollOfMagicMapping,
    ScrollOfUpgrade,
    Seed,
    SmallRation,
    Stone,
    ThrowableDagger,
    VelvetPouch,
    Wand,
    Waterskin,
    WornShortsword,
)


@pytest.mark.parametrize("item, expected", [
    (WornShortsword(id="i", tier=1), 20),
    (Dagger(id="i", tier=2), 40),
    (Armor(id="i", name="Armor", tier=2), 40),
    (Wand(id="i", name="Wand"), 75),
    (Ring(id="i", name="Ring"), 75),
    (HealthPotion(id="i"), 30),
    (HealthPotion(id="i", quantity=3), 90),
    (Scroll(id="i", name="Scroll"), 30),
    (SmallRation(id="i"), 10),
    (Seed(id="i", name="Seed", quantity=2), 20),
    (GooBlob(id="i", quantity=2), 60),
    (Stone(id="i", quantity=2), 5),
    (Boomerang(id="i", quantity=2), 40),
    (ThrowableDagger(id="i", quantity=2), 10),
    (ElixirOfAquaticRejuvenation(id="i", quantity=2), 120),
    (VelvetPouch(id="i"), 30),
    (MagicalHolster(id="i"), 60),
    (Bag(id="i", name="Bag"), 0),
    (Key(id="i", name="Key"), 0),
    (Dewdrop(id="i", quantity=5), 0),
    (Waterskin(id="i", volume=20), 0),
])
def test_base_values(item, expected):
    assert item.value() == expected


def test_melee_weapon_level_and_curse_modifiers():
    sword = WornShortsword(id="i", tier=1, level=2, level_known=True)
    assert sword.value() == 20 * 3  # *(level+1)

    cursed = WornShortsword(id="i", tier=1, cursed=True, cursed_known=True)
    assert cursed.value() == 10  # /2


def test_armor_seal_not_specially_handled_without_seal_field():
    armor = Armor(id="i", name="Armor", tier=3)
    assert armor.value() == 60


def test_wand_and_ring_level_modifiers():
    ring = Ring(id="i", name="Ring", level=1, level_known=True)
    assert ring.value() == 75 * 2

    wand = Wand(id="i", name="Wand", level=-2, level_known=True)
    assert wand.value() == round(75 / 3)

    cursed_ring = Ring(id="i", name="Ring", cursed=True, cursed_known=True)
    assert cursed_ring.value() == round(75 / 2)


def test_potion_of_experience_identification():
    pot = PotionOfExperience(id="i")
    assert pot.value(identified=False) == 30
    assert pot.value(identified=True) == 50


def test_scroll_upgrade_and_magic_mapping_identification():
    upgrade = ScrollOfUpgrade(id="i")
    assert upgrade.value(identified=False) == 30
    assert upgrade.value(identified=True) == 50

    mapping = ScrollOfMagicMapping(id="i")
    assert mapping.value(identified=False) == 30
    assert mapping.value(identified=True) == 40
