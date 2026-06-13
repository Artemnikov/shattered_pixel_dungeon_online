"""Tests for the Imp quest chain (AmbitiousImpRoom, DwarfToken drops,
ImpClaimReward) and the ImpShopRoom on floor 20."""
import uuid

from app.engine.entities.base import DwarfToken, Position, Ring
from app.engine.entities.mobs import Golem, Imp, Monk, Shopkeeper
from app.engine.manager import GameInstance


def test_ambitious_imp_room_spawns_with_imp_npc():
    g = GameInstance("imp-spawn", seed="1")
    floor = g._get_or_create_floor(17)

    imps = [m for m in floor.mobs.values() if isinstance(m, Imp)]
    assert len(imps) == 1
    assert g.run_state.imp_quest.spawned is True
    assert g.run_state.imp_quest.alternative is True  # depth 17 -> Monks


def test_npc_interact_with_imp_gives_quest():
    g = GameInstance("imp-give", seed="1")
    p = g.add_player("p1", "Bob")
    floor = g._get_or_create_floor(17)
    imp = next(m for m in floor.mobs.values() if isinstance(m, Imp))

    p.floor_id = 17
    p.pos = Position(x=imp.pos.x + 1, y=imp.pos.y)

    g.npc_interact("p1", imp.id)

    quest = g.run_state.imp_quest
    assert quest.given is True
    events = [e for e in g.events if e["type"] == "IMP_DIALOGUE"]
    assert len(events) == 1
    assert events[0]["data"]["can_claim"] is False
    assert "Monks" in events[0]["data"]["text"]


def test_mob_death_drops_dwarf_token_when_quest_given():
    g = GameInstance("imp-token", seed="1")
    floor = g._get_or_create_floor(17)
    quest = g.run_state.imp_quest
    quest.given = True
    quest.alternative = True  # Monks required

    monk = Monk(id=str(uuid.uuid4()), pos=Position(x=10, y=10))
    floor.mobs[monk.id] = monk

    g.handle_mob_death(monk, floor, 17)

    tokens = [i for i in floor.items.values() if isinstance(i, DwarfToken)]
    assert len(tokens) == 1
    assert tokens[0].pos == Position(x=10, y=10)


def test_mob_death_no_token_for_wrong_mob_type():
    g = GameInstance("imp-token-wrong", seed="1")
    floor = g._get_or_create_floor(17)
    quest = g.run_state.imp_quest
    quest.given = True
    quest.alternative = True  # Monks required, not Golems

    golem = Golem(id=str(uuid.uuid4()), pos=Position(x=10, y=10))
    floor.mobs[golem.id] = golem

    g.handle_mob_death(golem, floor, 17)

    tokens = [i for i in floor.items.values() if isinstance(i, DwarfToken)]
    assert len(tokens) == 0


def test_mob_death_no_token_on_floor_20():
    g = GameInstance("imp-token-floor20", seed="1")
    floor = g._get_or_create_floor(20)
    quest = g.run_state.imp_quest
    quest.given = True
    quest.alternative = False  # Golems required

    golem = Golem(id=str(uuid.uuid4()), pos=Position(x=10, y=10))
    floor.mobs[golem.id] = golem

    g.handle_mob_death(golem, floor, 20)

    tokens = [i for i in floor.items.values() if isinstance(i, DwarfToken)]
    assert len(tokens) == 0


def test_npc_interact_imp_reports_progress_when_not_enough_tokens():
    g = GameInstance("imp-progress", seed="1")
    p = g.add_player("p1", "Bob")
    floor = g._get_or_create_floor(17)
    imp = next(m for m in floor.mobs.values() if isinstance(m, Imp))
    g.run_state.imp_quest.given = True
    g.run_state.imp_quest.alternative = True

    p.floor_id = 17
    p.pos = Position(x=imp.pos.x + 1, y=imp.pos.y)
    p.inventory.append(DwarfToken(id="tok", quantity=2))

    g.npc_interact("p1", imp.id)

    events = [e for e in g.events if e["type"] == "IMP_DIALOGUE"]
    assert events[-1]["data"]["can_claim"] is False
    assert events[-1]["data"]["tokens"] == 2


def test_npc_interact_imp_offers_reward_when_enough_tokens():
    g = GameInstance("imp-ready", seed="1")
    p = g.add_player("p1", "Bob")
    floor = g._get_or_create_floor(17)
    imp = next(m for m in floor.mobs.values() if isinstance(m, Imp))
    g.run_state.imp_quest.given = True
    g.run_state.imp_quest.alternative = False  # Golems, 4 required

    p.floor_id = 17
    p.pos = Position(x=imp.pos.x + 1, y=imp.pos.y)
    p.inventory.append(DwarfToken(id="tok", quantity=4))

    g.npc_interact("p1", imp.id)

    events = [e for e in g.events if e["type"] == "IMP_DIALOGUE"]
    assert events[-1]["data"]["can_claim"] is True
    assert events[-1]["data"]["tokens"] == 4


def test_imp_claim_reward_grants_hidden_cursed_ring_and_despawns_imp():
    g = GameInstance("imp-claim", seed="1")
    p = g.add_player("p1", "Bob")
    floor = g._get_or_create_floor(17)
    imp = next(m for m in floor.mobs.values() if isinstance(m, Imp))
    quest = g.run_state.imp_quest
    quest.given = True
    quest.alternative = True  # Monks, 5 required

    p.floor_id = 17
    p.pos = Position(x=imp.pos.x + 1, y=imp.pos.y)
    p.inventory.append(DwarfToken(id="tok", quantity=5))

    g.imp_claim_reward("p1", imp.id)

    assert quest.completed is True
    assert imp.id not in floor.mobs
    assert not any(isinstance(i, DwarfToken) for i in p.inventory)

    rings = [i for i in p.inventory if isinstance(i, Ring)]
    assert len(rings) == 1
    assert rings[0].cursed is True
    assert rings[0].cursed_known is False
    assert rings[0].level == 2
    assert rings[0].level_known is True

    reward_events = [e for e in g.events if e["type"] == "IMP_REWARD"]
    assert len(reward_events) == 1


def test_imp_claim_reward_fails_with_insufficient_tokens():
    g = GameInstance("imp-claim-fail", seed="1")
    p = g.add_player("p1", "Bob")
    floor = g._get_or_create_floor(17)
    imp = next(m for m in floor.mobs.values() if isinstance(m, Imp))
    quest = g.run_state.imp_quest
    quest.given = True
    quest.alternative = True  # Monks, 5 required

    p.floor_id = 17
    p.pos = Position(x=imp.pos.x + 1, y=imp.pos.y)
    p.inventory.append(DwarfToken(id="tok", quantity=2))

    g.imp_claim_reward("p1", imp.id)

    assert quest.completed is False
    assert imp.id in floor.mobs


# ---------------------------------------------------------------------------
# ImpShopRoom (floor 20)
# ---------------------------------------------------------------------------

def test_floor_20_has_pending_imp_shop_room_when_quest_incomplete():
    g = GameInstance("imp-shop-pending", seed="0")
    floor = g._get_or_create_floor(20)

    assert "imp_shop_room" in floor.generation_meta
    assert floor.generation_meta["imp_shop_spawned"] is False
    assert not any(isinstance(m, Shopkeeper) for m in floor.mobs.values())


def test_floor_20_imp_shop_populated_immediately_when_quest_already_completed():
    g = GameInstance("imp-shop-immediate", seed="0")
    g.run_state.imp_quest.completed = True
    g.run_state.imp_quest.reward = Ring(name="Ring", level=2, level_known=True, cursed=True, cursed_known=False)

    floor = g._get_or_create_floor(20)

    assert "imp_shop_room" not in floor.generation_meta
    assert any(isinstance(m, Shopkeeper) for m in floor.mobs.values())
    assert any(getattr(i, "for_sale", False) for i in floor.items.values())


def test_imp_claim_reward_retroactively_spawns_floor_20_shop():
    g = GameInstance("imp-shop-retro", seed="0")
    floor20 = g._get_or_create_floor(20)
    assert "imp_shop_room" in floor20.generation_meta

    p = g.add_player("p1", "Bob")
    imp = None
    imp_floor = None
    for depth in (17, 18, 19):
        floor = g._get_or_create_floor(depth)
        imp = next((m for m in floor.mobs.values() if isinstance(m, Imp)), None)
        if imp:
            imp_floor = floor
            break
    quest = g.run_state.imp_quest
    quest.given = True

    p.floor_id = imp_floor.floor_id
    p.pos = Position(x=imp.pos.x + 1, y=imp.pos.y)
    required = 5 if quest.alternative else 4
    p.inventory.append(DwarfToken(id="tok", quantity=required))

    g.imp_claim_reward("p1", imp.id)

    assert floor20.generation_meta["imp_shop_spawned"] is True
    assert any(isinstance(m, Shopkeeper) for m in floor20.mobs.values())
    for_sale = [i for i in floor20.items.values() if getattr(i, "for_sale", False)]
    assert len(for_sale) > 0
