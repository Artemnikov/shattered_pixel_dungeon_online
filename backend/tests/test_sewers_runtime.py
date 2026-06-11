from app.engine.dungeon.generator import TileType
from app.engine.entities.base import Key
from app.engine.manager import GameInstance


WALKABLE_TILES = {
    TileType.FLOOR,
    TileType.DOOR,
    TileType.STAIRS_UP,
    TileType.STAIRS_DOWN,
    TileType.FLOOR_WOOD,
    TileType.FLOOR_WATER,
    TileType.FLOOR_COBBLE,
    TileType.FLOOR_GRASS,
    TileType.EMPTY_DECO,
    TileType.HIGH_GRASS,
}


def _find_adjacent_walkable(floor, x, y):
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        nx, ny = x + dx, y + dy
        if not (0 <= ny < len(floor.grid) and 0 <= nx < len(floor.grid[0])):
            continue
        if floor.grid[ny][nx] in WALKABLE_TILES:
            return nx, ny
    return None


def _find_floor_with_locked_door(max_tries=60):
    for idx in range(max_tries):
        game = GameInstance(f"locked-sewers-{idx}")
        floor = game._get_or_create_floor(1)
        if floor.locked_doors:
            return game, floor
    return None, None


def test_search_reveals_hidden_door_and_emits_map_patch():
    game = GameInstance("search-sewers")
    floor = game._get_or_create_floor(1)
    floor.mobs = {}

    assert floor.hidden_doors
    hidden_pos = next(iter(floor.hidden_doors.keys()))

    player = game.add_player("p-search", "Searcher")

    neighbor = _find_adjacent_walkable(floor, hidden_pos[0], hidden_pos[1])
    assert neighbor is not None
    player.pos.x, player.pos.y = neighbor

    game.flush_events()
    game.search(player.id)

    assert hidden_pos not in floor.hidden_doors
    assert floor.grid[hidden_pos[1]][hidden_pos[0]] in {TileType.DOOR, TileType.LOCKED_DOOR}

    events = game.flush_events()
    map_patches = [e for e in events if e["type"] == "MAP_PATCH"]
    assert map_patches

    revealed_positions = {
        (tile_patch["x"], tile_patch["y"])
        for event in map_patches
        for tile_patch in event["data"].get("tiles", [])
    }
    assert hidden_pos in revealed_positions


def test_locked_door_requires_matching_key_and_unlocks_with_patch():
    game, floor = _find_floor_with_locked_door()
    assert game is not None and floor is not None

    floor.mobs = {}

    (door_x, door_y), key_id = next(iter(floor.locked_doors.items()))

    player = game.add_player("p-lock", "Unlocker")

    neighbor = _find_adjacent_walkable(floor, door_x, door_y)
    assert neighbor is not None
    player.pos.x, player.pos.y = neighbor

    player.belongings.backpack.items = [item for item in player.inventory if not (isinstance(item, Key) and item.key_id == key_id)]

    game.flush_events()
    game.move_entity(player.id, door_x - player.pos.x, door_y - player.pos.y)

    assert (player.pos.x, player.pos.y) == neighbor
    assert floor.grid[door_y][door_x] == TileType.LOCKED_DOOR

    player.inventory.append(Key(id="test-key", name="Rusty Key", key_id=key_id))

    game.move_entity(player.id, door_x - player.pos.x, door_y - player.pos.y)

    assert (player.pos.x, player.pos.y) == (door_x, door_y)
    # Player stands on the door → it's OPEN_DOOR (runtime door-enter mutation)
    assert floor.grid[door_y][door_x] == TileType.OPEN_DOOR
    assert not any(isinstance(item, Key) and item.key_id == key_id for item in player.inventory)

    events = game.flush_events()
    map_patches = [e for e in events if e["type"] == "MAP_PATCH"]
    assert map_patches
    assert any(
        tile_patch["x"] == door_x and tile_patch["y"] == door_y and tile_patch["tile"] == TileType.DOOR
        for event in map_patches
        for tile_patch in event["data"].get("tiles", [])
    )


def test_worn_dart_trap_triggers_once_and_deals_low_damage():
    game = GameInstance("trap-sewers")
    floor = game._get_or_create_floor(1)
    floor.mobs = {}

    assert floor.traps
    (trap_x, trap_y), trap = next(iter(floor.traps.items()))

    player = game.add_player("p-trap", "Trapper")
    neighbor = _find_adjacent_walkable(floor, trap_x, trap_y)
    assert neighbor is not None

    player.pos.x, player.pos.y = neighbor

    game.flush_events()
    hp_before = player.hp
    game.move_entity(player.id, trap_x - player.pos.x, trap_y - player.pos.y)

    assert (player.pos.x, player.pos.y) == (trap_x, trap_y)
    assert trap.active is False
    assert player.hp < hp_before

    events = game.flush_events()
    assert any(event["type"] == "TRAP_TRIGGERED" for event in events)

    hp_after = player.hp
    game._trigger_trap_if_needed(floor, player, floor.floor_id)
    assert player.hp == hp_after
