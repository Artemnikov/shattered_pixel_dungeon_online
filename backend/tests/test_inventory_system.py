"""Unit tests for the ported SPD inventory system: stacking, nested category
bags, equip slots, quickslot placeholders, and curse handling."""
import pytest
from app.engine.entities.base import (
    Player, Position, Belongings, Bag, PotionBandolier, ScrollHolder,
    MeleeWeapon, Armor, Ring, Wand, HealthPotion, RevivingPotion, Scroll,
    QuickSlot, Action,
)


def make_player(strength=10):
    return Player(id="p", type="player", name="T", pos=Position(x=0, y=0),
                  hp=20, max_hp=20, attack=5, defense=1, faction="player", strength=strength)


# --- stacking --------------------------------------------------------------
def test_stackable_potions_merge():
    p = make_player()
    assert p.add_to_inventory(HealthPotion(id="h1"))
    assert p.add_to_inventory(HealthPotion(id="h2"))
    pots = [i for i in p.inventory if i.kind == "health_potion"]
    assert len(pots) == 1 and pots[0].quantity == 2


def test_different_potions_do_not_merge():
    p = make_player()
    p.add_to_inventory(HealthPotion(id="h1"))
    p.add_to_inventory(RevivingPotion(id="r1"))
    assert len({i.kind for i in p.inventory}) == 2


def test_split_creates_fresh_id():
    stack = HealthPotion(id="h1", quantity=3)
    piece = stack.split(1)
    assert piece is not None
    assert piece.quantity == 1 and stack.quantity == 2
    assert piece.id != "h1"  # id-addressed protocol must not collide


def test_split_invalid_amounts():
    stack = HealthPotion(id="h1", quantity=2)
    assert stack.split(0) is None
    assert stack.split(2) is None  # can't split the whole stack


def test_detach_decrements_stack():
    p = make_player()
    p.add_to_inventory(HealthPotion(id="h1", quantity=3))
    one = p.belongings.backpack.detach("h1")
    assert one.quantity == 1
    assert [i for i in p.inventory if i.kind == "health_potion"][0].quantity == 2


# --- nested category bags --------------------------------------------------
def test_subbag_autosorts_items():
    p = make_player()
    p.add_to_inventory(PotionBandolier(id="band"))
    p.add_to_inventory(HealthPotion(id="h1"))
    band = p.belongings.backpack.find("band")
    assert band.find("h1") is not None  # potion auto-routed into the bandolier
    # the potion should not also sit at backpack top level
    assert all(i.id != "h1" for i in p.belongings.backpack.items)


def test_subbag_rejects_wrong_category():
    band = PotionBandolier(id="band")
    assert band.can_hold(HealthPotion(id="h")) is True
    assert band.can_hold(Scroll(id="s", name="Scroll")) is False


def test_grab_items_pulls_matching():
    p = make_player()
    # distinct names so they don't stack into one entry
    p.add_to_inventory(Scroll(id="s1", name="Scroll of A"))
    p.add_to_inventory(Scroll(id="s2", name="Scroll of B"))
    holder = ScrollHolder(id="holder")
    holder.grab_items(p.belongings.backpack)
    assert holder.contains("s1") and holder.contains("s2")
    assert all(i.category != "scroll" for i in p.belongings.backpack.items)


def test_capacity_limit():
    bag = Bag(id="b", name="B", capacity=2)
    assert bag.collect(MeleeWeapon(id="w1", name="a", damage=1))
    assert bag.collect(MeleeWeapon(id="w2", name="b", damage=1))
    assert not bag.collect(MeleeWeapon(id="w3", name="c", damage=1))


# --- equip slots -----------------------------------------------------------
def test_equip_routes_to_correct_slot():
    p = make_player()
    p.add_to_inventory(MeleeWeapon(id="w", name="Sword", damage=3, strength_requirement=0))
    p.add_to_inventory(Armor(id="a", name="Mail", health_boost=4, strength_requirement=0))
    p.add_to_inventory(Ring(id="r", name="Ring", strength_requirement=0))
    assert p.equip_item("w") and p.belongings.weapon.id == "w"
    assert p.equip_item("a") and p.belongings.armor.id == "a"
    assert p.equip_item("r") and p.belongings.ring.id == "r"
    # equipped items leave the backpack
    assert len(p.belongings.backpack.items) == 0


def test_equip_swaps_previous():
    p = make_player()
    p.add_to_inventory(MeleeWeapon(id="w1", name="A", damage=3, strength_requirement=0))
    p.add_to_inventory(MeleeWeapon(id="w2", name="B", damage=5, strength_requirement=0))
    p.equip_item("w1")
    p.equip_item("w2")
    assert p.belongings.weapon.id == "w2"
    assert any(i.id == "w1" for i in p.belongings.backpack.items)  # swapped back


# --- curses ----------------------------------------------------------------
def test_cursed_known_blocks_unequip():
    p = make_player()
    p.add_to_inventory(MeleeWeapon(id="w", name="Sword", damage=3, strength_requirement=0,
                                   cursed=True, cursed_known=True))
    p.equip_item("w")
    assert p.unequip_item("w") is False
    assert p.belongings.weapon is not None


def test_unknown_curse_allows_unequip():
    p = make_player()
    p.add_to_inventory(MeleeWeapon(id="w", name="Sword", damage=3, strength_requirement=0,
                                   cursed=True, cursed_known=False))
    p.equip_item("w")
    assert p.unequip_item("w") is True
    assert p.belongings.weapon is None


# --- quickslot placeholders ------------------------------------------------
def test_quickslot_placeholder_lifecycle():
    p = make_player()
    pot = HealthPotion(id="h1", quantity=1)
    p.add_to_inventory(pot)
    p.quickslot.set_slot(0, pot)
    assert p.quickslot.slots[0].item_id == "h1"
    # deplete -> becomes a placeholder reserved by kind
    p.quickslot.convert_to_placeholder(pot)
    assert p.quickslot.slots[0].is_placeholder
    assert p.quickslot.slots[0].placeholder_kind == "health_potion"
    # collecting a like item re-binds the slot
    newpot = HealthPotion(id="h2")
    p.add_to_inventory(newpot)
    assert p.quickslot.slots[0].item_id == "h2"
    assert not p.quickslot.slots[0].is_placeholder


# --- actions list ----------------------------------------------------------
def test_actions_reflect_equipped_state():
    p = make_player()
    w = MeleeWeapon(id="w", name="Sword", damage=3, strength_requirement=0)
    p.add_to_inventory(w)
    assert Action.EQUIP in w.actions(p)
    p.equip_item("w")
    assert Action.UNEQUIP in p.belongings.weapon.actions(p)


def test_potion_default_action():
    assert HealthPotion(id="h").default_action() == Action.DRINK
    assert Wand(id="x", name="W").default_action() == Action.ZAP


# --- generic action dispatch (via GameInstance) ----------------------------
from app.engine.manager import GameInstance


def test_dispatch_drink_consumes_and_heals():
    g = GameInstance("t1")
    p = g.add_player("p1", "Bob")
    p.add_to_inventory(HealthPotion(id="h1"))
    g.execute_item_action("p1", "h1", Action.DRINK)
    assert p.heal_left > 0
    assert p.belongings.get_item("h1") is None


def test_dispatch_drop_equipped_to_floor():
    g = GameInstance("t2")
    p = g.add_player("p1", "Bob")
    wid = p.belongings.weapon.id
    g.execute_item_action("p1", wid, Action.DROP)
    assert p.belongings.weapon is None
    assert wid in g._get_or_create_floor(p.floor_id).items


def test_dispatch_rejects_illegal_action():
    g = GameInstance("t3")
    p = g.add_player("p1", "Bob")
    p.add_to_inventory(MeleeWeapon(id="w9", name="S", damage=2, strength_requirement=0))
    g.execute_item_action("p1", "w9", Action.DRINK)  # weapons can't be drunk
    assert p.belongings.get_item("w9") is not None


def test_unidentified_potion_masked_then_revealed():
    g = GameInstance("m1")
    p = g.add_player("p1", "Bob")
    p.add_to_inventory(HealthPotion(id="h1"))
    me = next(pl for pl in g.get_state("p1")["players"] if pl["id"] == "p1")
    pot = next(i for i in me["belongings"]["backpack"]["items"] if i["id"] == "h1")
    assert pot["kind"] == "potion"            # subtype collapsed
    assert "Potion" in pot["name"]            # scrambled label, not "Health Potion"
    assert pot["name"] != "Health Potion"
    assert "effect" not in pot

    # drinking identifies the kind for the whole party
    g.execute_item_action("p1", "h1", Action.DRINK)
    p.add_to_inventory(HealthPotion(id="h2"))
    me2 = next(pl for pl in g.get_state("p1")["players"] if pl["id"] == "p1")
    pot2 = next(i for i in me2["belongings"]["backpack"]["items"] if i["id"] == "h2")
    assert pot2["kind"] == "health_potion"
    assert pot2["name"] == "Health Potion"


def test_quickslot_set_and_use():
    g = GameInstance("t4")
    p = g.add_player("p1", "Bob")
    p.add_to_inventory(HealthPotion(id="h1"))
    g.set_quickslot("p1", 0, "h1")
    assert p.quickslot.slots[0].item_id == "h1"
    g.use_quickslot("p1", 0)  # default action = DRINK
    assert p.heal_left > 0
