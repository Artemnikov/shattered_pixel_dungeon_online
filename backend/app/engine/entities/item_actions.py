"""Generic item-action dispatch — the Python analogue of SPD's
Item.execute(hero, action).

Kept in its own module (not on the model classes) so item models stay free of a
GameInstance import cycle. Each handler has the signature
    (game, player, item, tx, ty) -> None
where `game` is the GameInstance, `tx/ty` are the optional target cell for
targeted actions (THROW/ZAP). Server validates `action in item.actions(player)`
before dispatch, so handlers can assume the action is legal for the item.
"""
from typing import Optional

from app.engine.dungeon.constants import TileType
from app.engine.entities.base import Action, Position, Player, Seed


def _floor_drop(game, player, item) -> None:
    item.pos = Position(x=player.pos.x, y=player.pos.y)
    floor = game._get_or_create_floor(player.floor_id)
    floor.items[item.id] = item


def action_equip(game, player, item, tx=None, ty=None) -> None:
    player.equip_item(item.id)


def action_unequip(game, player, item, tx=None, ty=None) -> None:
    player.unequip_item(item.id)


def action_drop(game, player, item, tx=None, ty=None) -> None:
    # Drop the whole stack/item, from the backpack or an equip slot.
    detached = player.belongings.backpack.detach_all(item.id)
    if detached is None and player.belongings.is_equipped(item.id):
        if item.cursed and item.cursed_known:
            return  # cursed gear can't be removed
        for slot in ("weapon", "armor", "artifact", "misc", "ring"):
            cur = getattr(player.belongings, slot)
            if cur is not None and cur.id == item.id:
                setattr(player.belongings, slot, None)
                detached = cur
                break
    if detached is None:
        return
    player.quickslot.clear_item(detached.id)
    _floor_drop(game, player, detached)
    game.add_event("DROP", {"player": player.id, "item": detached.id}, floor_id=player.floor_id)


def action_drink(game, player, item, tx=None, ty=None) -> None:
    # Mirrors PotionOfHealing: heal 0.8*maxHP+14 over time, 25% of the remaining
    # pool per heal-tick. Reviving potions are consumed by reviving a downed ally
    # (see move_entity), not by self-drinking, so they no-op here.
    game.identify_kind(item)  # drinking reveals the potion type to the party
    effect = getattr(item, "effect", "")
    if effect == "regen":
        amount = round(0.8 * player.get_total_max_hp() + 14)
        player.set_heal(amount, 0.25, 0)
        removed = player.belongings.backpack.detach(item.id)
        if removed is not None and player.belongings.get_item(item.id) is None:
            player.quickslot.convert_to_placeholder(removed)
        game.add_event("DRINK", {"player": player.id, "type": "regen"}, floor_id=player.floor_id, source_player_id=player.id)
    elif effect == "fury":
        player.has_fury = True
        player.fury_turns_remaining = 10
        removed = player.belongings.backpack.detach(item.id)
        if removed is not None and player.belongings.get_item(item.id) is None:
            player.quickslot.convert_to_placeholder(removed)
        game.add_event("DRINK", {"player": player.id, "type": "fury"}, floor_id=player.floor_id, source_player_id=player.id)


def action_affix(game, player, item, tx=None, ty=None) -> None:
    armor = player.belongings.armor
    if armor is None:
        return
    if item.cursed and item.cursed_known:
        return
    armor.level += max(1, item.level + 1)
    armor.level_known = True
    player.belongings.artifact = None
    player.quickslot.clear_item(item.id)
    player.seal_affixed = True
    game.add_event("AFFIX_SEAL", {"player": player.id, "armor": armor.id}, floor_id=player.floor_id, source_player_id=player.id)


def action_read(game, player, item, tx=None, ty=None) -> None:
    game.identify_kind(item)
    effect = getattr(item, "kind", "")
    if effect == "scroll_of_rage":
        player.has_fury = True
        player.fury_turns_remaining = 15
        removed = player.belongings.backpack.detach(item.id)
        if removed is not None and player.belongings.get_item(item.id) is None:
            player.quickslot.convert_to_placeholder(removed)
    game.add_event("READ", {"player": player.id, "item": item.id}, floor_id=player.floor_id)


def action_plant(game, player, item, tx=None, ty=None) -> None:
    if tx is None or ty is None:
        return
    floor = game._get_or_create_floor(player.floor_id)
    if not (0 <= tx < floor.width and 0 <= ty < floor.height):
        return
    tile = floor.grid[ty][tx]
    valid_terrains = [
        TileType.FLOOR_GRASS, TileType.HIGH_GRASS, TileType.FURROWED_GRASS,
        TileType.FLOOR, TileType.EMPTY_DECO,
    ]
    if tile not in valid_terrains:
        return  # can't plant here
    floor.grid[ty][tx] = TileType.FLOOR_GRASS
    from app.engine.game.terrain_effects import _plant_seed_at
    _plant_seed_at(floor, (tx, ty), item.plant_type)
    removed = player.belongings.backpack.detach(item.id)
    if removed is not None and player.belongings.get_item(item.id) is None:
        player.quickslot.convert_to_placeholder(removed)
    game.add_event("MAP_PATCH", {"tiles": [{"x": tx, "y": ty, "tile": TileType.FLOOR_GRASS}]}, floor_id=player.floor_id)
    # Warden bonus: surrounding cells become FURROWED_GRASS
    subclass_info = getattr(player, "subclass_info", None)
    if subclass_info and subclass_info.subclass == "warden":
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                nx, ny = tx + dx, ty + dy
                if 0 <= nx < floor.width and 0 <= ny < floor.height:
                    if floor.grid[ny][nx] != TileType.WALL and floor.grid[ny][nx] != TileType.VOID:
                        floor.grid[ny][nx] = TileType.FURROWED_GRASS
        floor.rebuild_flags()
        patches = [{"x": tx + dx, "y": ty + dy, "tile": floor.grid[ty + dy][tx + dx]}
                    for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                    if 0 <= tx + dx < floor.width and 0 <= ty + dy < floor.height]
        game.add_event("MAP_PATCH", {"tiles": patches}, floor_id=player.floor_id)
    floor.rebuild_flags()


def action_throw(game, player, item, tx=None, ty=None) -> None:
    if tx is None or ty is None:
        return
    # Seeds are planted, not thrown as items
    if isinstance(item, Seed):
        action_plant(game, player, item, tx, ty)
        return
    game.perform_ranged_attack(player.id, item.id, tx, ty)


def action_zap(game, player, item, tx=None, ty=None) -> None:
    if tx is None or ty is None:
        return
    game.perform_ranged_attack(player.id, item.id, tx, ty)


def action_noop(game, player, item, tx=None, ty=None) -> None:
    # OPEN (bag) / EAT (no food effects yet) are handled client-side or are no-ops.
    return


ITEM_ACTION_DISPATCH = {
    Action.EQUIP: action_equip,
    Action.UNEQUIP: action_unequip,
    Action.DROP: action_drop,
    Action.DRINK: action_drink,
    Action.READ: action_read,
    Action.THROW: action_throw,
    Action.ZAP: action_zap,
    Action.AFFIX: action_affix,
    Action.EAT: action_noop,
    Action.OPEN: action_noop,
    Action.INFO: action_noop,
}
