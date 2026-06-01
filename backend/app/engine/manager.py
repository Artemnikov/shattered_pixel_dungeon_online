import random
import time
import uuid
import zlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from app.engine.dungeon.generator import (
    DungeonGenerator,
    SewersProfile,
    TileType,
    TrapInfo,
)
from app.engine.dungeon.terrain_flags import FloorFlagMaps, build_flag_maps
from app.engine.entities.base import (
    Bag,
    Belongings,
    Boomerang,
    Bow,
    CharacterClass,
    Difficulty,
    Effect,
    EntityType,
    Faction,
    HealthPotion,
    Item,
    Key,
    Mob as MobEntity,
    Player,
    Position,
    QuickSlot,
    RevivingPotion,
    Staff,
    Stone,
    Throwable,
    ThrowableDagger,
    Wand,
    Weapon,
    Wearable,
)
from app.engine.entities import item_actions


MAX_FLOOR_ID = 50
SEWERS_MAX_FLOOR = 4

AUTO_MOVE_INTERVAL = 0.15

# The tick loop runs at 20Hz; heal once per ~second so floating numbers stay
# readable and the cadence matches the original game's per-turn healing.
HEAL_TICK_INTERVAL = 20

# HP restored per second while a player stands in a floor's entrance (up-stairs) room.
ROOM_HEAL_AMOUNT = 10

@dataclass
class FloorState:
    floor_id: int
    grid: List[List[int]]
    rooms: List[object]
    mobs: Dict[str, MobEntity]
    items: Dict[str, Item]
    region: str = "generic"
    hidden_doors: Dict[Tuple[int, int], int] = field(default_factory=dict)
    locked_doors: Dict[Tuple[int, int], str] = field(default_factory=dict)
    traps: Dict[Tuple[int, int], TrapInfo] = field(default_factory=dict)
    key_spawns: Dict[str, Tuple[int, int]] = field(default_factory=dict)
    generation_meta: Dict[str, object] = field(default_factory=dict)
    # Derived bool-array flag maps. Populated by build_flag_maps() after the
    # grid is finalised. See terrain_flags.py.
    flags: Optional[FloorFlagMaps] = None

    def rebuild_flags(self) -> None:
        """Regenerate all bool-array flag maps from the current grid.

        Call after any tile-ID mutation (e.g. secret door revealed, trap
        triggered) so downstream LOS/pathfinding stays consistent.
        """
        self.flags = build_flag_maps(self.grid)


class GameInstance:
    def __init__(self, game_id: str):
        self.game_id = game_id
        self.depth = 1  # Compatibility view for single-floor tests/legacy callers.
        self.width = 60
        self.height = 40

        self.players: Dict[str, Player] = {}
        self.floors: Dict[int, FloorState] = {}
        self.events: List[dict] = []

        self.difficulty = Difficulty.NORMAL
        self.player_count = 0

        # Shared per-run identification knowledge (co-op semantics, mirrors SPD's
        # per-Dungeon catalog): once any player IDs a potion/scroll kind, the whole
        # party knows it. `kind_labels` holds the scrambled per-run display names
        # for still-unidentified kinds.
        self.identified_kinds: set = set()
        self.kind_labels: Dict[str, str] = {}

        self.generate_floor(1)

    @property
    def grid(self) -> List[List[int]]:
        return self._get_or_create_floor(self.depth).grid

    @grid.setter
    def grid(self, value: List[List[int]]):
        self._get_or_create_floor(self.depth).grid = value

    @property
    def rooms(self) -> List[object]:
        return self._get_or_create_floor(self.depth).rooms

    @rooms.setter
    def rooms(self, value: List[object]):
        self._get_or_create_floor(self.depth).rooms = value

    @property
    def mobs(self) -> Dict[str, MobEntity]:
        return self._get_or_create_floor(self.depth).mobs

    @mobs.setter
    def mobs(self, value: Dict[str, MobEntity]):
        self._get_or_create_floor(self.depth).mobs = value

    @property
    def items(self) -> Dict[str, Item]:
        return self._get_or_create_floor(self.depth).items

    @items.setter
    def items(self, value: Dict[str, Item]):
        self._get_or_create_floor(self.depth).items = value

    def _get_or_create_floor(self, floor_id: int) -> FloorState:
        floor_id = max(1, min(MAX_FLOOR_ID, floor_id))
        if floor_id in self.floors:
            return self.floors[floor_id]
        return self.generate_floor(floor_id)

    def _find_mob_floor(self, mob_id: str) -> Optional[int]:
        for floor_id, floor in self.floors.items():
            if mob_id in floor.mobs:
                return floor_id
        return None

    def _get_floor_for_entity(self, entity_id: str) -> Tuple[Optional[int], Optional[object]]:
        if entity_id in self.players:
            player = self.players[entity_id]
            return player.floor_id, player

        mob_floor = self._find_mob_floor(entity_id)
        if mob_floor is None:
            return None, None

        floor = self._get_or_create_floor(mob_floor)
        return mob_floor, floor.mobs.get(entity_id)

    def _players_on_floor(self, floor_id: int) -> List[Player]:
        return [p for p in self.players.values() if p.floor_id == floor_id]

    def add_event(self, event_type: str, data: dict = None, floor_id: Optional[int] = None, player_id: Optional[str] = None):
        event = {
            "type": event_type,
            "data": data or {},
        }
        if floor_id is not None:
            event["_floor_id"] = floor_id
        if player_id is not None:
            event["_player_id"] = player_id
        self.events.append(event)

    def filter_events_for_player(self, events: List[dict], player_id: str) -> List[dict]:
        player = self.players.get(player_id)
        if not player:
            return []

        filtered = []
        for event in events:
            event_player = event.get("_player_id")
            event_floor = event.get("_floor_id")

            if event_player is not None and event_player != player_id:
                continue

            if event_floor is not None and event_floor != player.floor_id:
                continue

            filtered.append({k: v for k, v in event.items() if not k.startswith("_")})

        return filtered

    def flush_events(self):
        events = self.events
        self.events = []
        return events

    def generate_floor(self, depth: int) -> FloorState:
        depth = max(1, min(MAX_FLOOR_ID, depth))
        self.depth = depth

        # Deterministic per-(game_id, depth) seed so reconnects/reloads see the
        # same layout. Mirrors SPD's Dungeon.seedCurDepth(). Using CRC32
        # instead of Python's built-in hash() because hash() is randomised
        # per-process (PYTHONHASHSEED) — cross-process stability matters for
        # server restarts during a live game session.
        floor_seed = zlib.crc32(f"{self.game_id}:{depth}".encode("utf-8"))
        generator = DungeonGenerator(self.width, self.height, seed=floor_seed)
        floor: FloorState
        if depth <= SEWERS_MAX_FLOOR:
            sewers_result = generator.generate_sewers(SewersProfile(depth=depth))
            floor = FloorState(
                floor_id=depth,
                grid=sewers_result.grid,
                rooms=sewers_result.rooms,
                mobs={},
                items={},
                region=sewers_result.metadata.region,
                hidden_doors=dict(sewers_result.metadata.hidden_doors),
                locked_doors=dict(sewers_result.metadata.locked_doors),
                traps=dict(sewers_result.metadata.traps),
                key_spawns=dict(sewers_result.metadata.key_spawns),
                generation_meta={
                    "layout_kind": sewers_result.metadata.layout_kind,
                    "room_ids_by_kind": sewers_result.metadata.room_ids_by_kind,
                    "room_connections": sewers_result.metadata.room_connections,
                    "start_room_id": sewers_result.metadata.start_room_id,
                    "end_room_id": sewers_result.metadata.end_room_id,
                    "seed": sewers_result.metadata.seed,
                },
            )
        elif depth == 5:
            grid, rooms = generator.generate_boss_floor()
            floor = FloorState(
                floor_id=depth,
                grid=grid,
                rooms=rooms,
                mobs={},
                items={},
                region="sewers",
            )
        else:
            grid, rooms = generator.generate(10 + depth, 4, 8 + (depth // 10))
            floor = FloorState(
                floor_id=depth,
                grid=grid,
                rooms=rooms,
                mobs={},
                items={},
                region="legacy",
            )

        # The v2 generator pipeline resizes its canvas to fit the actual
        # room layout. Sync GameInstance dims to the real grid so every
        # self.width/self.height reader (spawn, LOS, BFS) stays in range.
        if floor.grid:
            actual_h = len(floor.grid)
            actual_w = len(floor.grid[0])
            self.height = actual_h
            self.width = actual_w

        floor.rebuild_flags()
        self.floors[depth] = floor
        self._spawn_content(floor)
        return floor

    def _is_in_safe_room(self, floor: FloorState, x: int, y: int) -> bool:
        if not floor.rooms:
            return False

        start_room = floor.rooms[0]
        end_room = floor.rooms[-1]

        if (
            start_room.x <= x < start_room.x + start_room.width
            and start_room.y <= y < start_room.y + start_room.height
        ):
            return True

        if (
            end_room.x <= x < end_room.x + end_room.width
            and end_room.y <= y < end_room.y + end_room.height
        ):
            return True

        return False

    def _is_in_entrance_room(self, floor: FloorState, x: int, y: int) -> bool:
        if not floor.rooms:
            return False

        room = floor.rooms[0]  # entrance / up-stairs room
        return (
            room.x <= x < room.x + room.width
            and room.y <= y < room.y + room.height
        )

    def _spawn_content(self, floor: FloorState):
        floor_tiles = [
            (x, y)
            for y in range(self.height)
            for x in range(self.width)
            if floor.grid[y][x] in [
                TileType.FLOOR,
                TileType.FLOOR_WOOD,
                TileType.FLOOR_WATER,
                TileType.FLOOR_COBBLE,
                TileType.FLOOR_GRASS,
            ]
        ]

        unsafe_floor_tiles = [
            pos for pos in floor_tiles if not self._is_in_safe_room(floor, pos[0], pos[1])
        ]

        self._spawn_floor_keys(floor)
        blocked_item_tiles = {
            (item.pos.x, item.pos.y) for item in floor.items.values() if item.pos is not None
        }
        if blocked_item_tiles:
            floor_tiles = [pos for pos in floor_tiles if pos not in blocked_item_tiles]
            unsafe_floor_tiles = [pos for pos in unsafe_floor_tiles if pos not in blocked_item_tiles]

        if floor.floor_id % 5 == 0:
            self._spawn_boss(floor, unsafe_floor_tiles)

        if floor.floor_id != 5:
            num_mobs = 5 + (floor.floor_id * 2)
            is_gnoll_floor = floor.floor_id == 2
            is_scorpio_floor = floor.floor_id == 4
            for _ in range(num_mobs):
                if not unsafe_floor_tiles:
                    break
                x, y = unsafe_floor_tiles.pop(random.randint(0, len(unsafe_floor_tiles) - 1))
                mob_id = str(uuid.uuid4())
                if is_gnoll_floor:
                    floor.mobs[mob_id] = MobEntity(
                        id=mob_id,
                        name="Gnoll",
                        pos=Position(x=x, y=y),
                        hp=15,
                        max_hp=15,
                        attack=3,
                        defense=1,
                        attack_cooldown=4.0,
                        faction=Faction.DUNGEON,
                        exp=2 + floor.floor_id,
                    )
                elif is_scorpio_floor:
                    floor.mobs[mob_id] = MobEntity(
                        id=mob_id,
                        name="Scorpio",
                        pos=Position(x=x, y=y),
                        hp=20,
                        max_hp=20,
                        attack=4,
                        defense=1,
                        attack_cooldown=3.5,
                        faction=Faction.DUNGEON,
                        exp=2 + floor.floor_id,
                    )
                else:
                    floor.mobs[mob_id] = MobEntity(
                        id=mob_id,
                        name="Rat",
                        pos=Position(x=x, y=y),
                        hp=10,
                        max_hp=10,
                        attack=2,
                        defense=0,
                        attack_cooldown=5.0,
                        faction=Faction.DUNGEON,
                        exp=2 + floor.floor_id,
                    )

        num_items = 4 + random.randint(0, 3)
        for _ in range(num_items):
            if not floor_tiles:
                break
            x, y = floor_tiles.pop(random.randint(0, len(floor_tiles) - 1))
            item_id = str(uuid.uuid4())

            rand = random.random()
            if rand < 0.2:
                floor.items[item_id] = Weapon(
                    id=item_id,
                    name=random.choice(["Rusty Sword", "Wooden Club", "Dagger"]),
                    pos=Position(x=x, y=y),
                    damage=2 + random.randint(0, 2),
                    range=1,
                    strength_requirement=10 + random.randint(-2, 2),
                    attack_cooldown=3.0 if "Dagger" not in "Rusty Sword, Wooden Club" else 1.5,
                )
            elif rand < 0.3:
                floor.items[item_id] = Bow(
                    id=item_id,
                    name="Old Bow",
                    pos=Position(x=x, y=y),
                    damage=2 + random.randint(0, 2),
                    strength_requirement=10,
                    attack_cooldown=3.5,
                )
            elif rand < 0.4:
                floor.items[item_id] = Staff(
                    id=item_id,
                    name="Magic Staff",
                    pos=Position(x=x, y=y),
                    damage=1 + random.randint(0, 2),
                    magic_damage=2 + random.randint(0, 2),
                    strength_requirement=10,
                )
            elif rand < 0.7:
                floor.items[item_id] = Wearable(
                    id=item_id,
                    name=random.choice(["Cloth Armor", "Leather Vest", "Broken Shield"]),
                    pos=Position(x=x, y=y),
                    strength_requirement=10 + random.randint(-2, 2),
                    health_boost=5 + random.randint(0, 5),
                )
            elif rand < 0.8:
                t_rand = random.random()
                if t_rand < 0.5:
                    floor.items[item_id] = Stone(id=item_id, pos=Position(x=x, y=y), damage=1, range=5)
                elif t_rand < 0.8:
                    floor.items[item_id] = ThrowableDagger(id=item_id, pos=Position(x=x, y=y), damage=4, range=4)
                else:
                    floor.items[item_id] = Boomerang(id=item_id, pos=Position(x=x, y=y), damage=3, range=6)
            elif rand < 0.9:
                floor.items[item_id] = HealthPotion(id=item_id, pos=Position(x=x, y=y))
            else:
                floor.items[item_id] = RevivingPotion(id=item_id, pos=Position(x=x, y=y))

    def _spawn_floor_keys(self, floor: FloorState):
        for key_id, (x, y) in floor.key_spawns.items():
            item_id = str(uuid.uuid4())
            floor.items[item_id] = Key(
                id=item_id,
                name="Rusty Key",
                pos=Position(x=x, y=y),
                key_id=key_id,
            )

    def _spawn_boss(self, floor: FloorState, floor_tiles: List[Tuple[int, int]]):
        if floor.floor_id == 5:
            x, y = floor.rooms[1].center
        else:
            if not floor_tiles:
                return
            x, y = floor_tiles.pop(random.randint(0, len(floor_tiles) - 1))

        is_goo = floor.floor_id == 5
        boss_id = str(uuid.uuid4())
        floor.mobs[boss_id] = MobEntity(
            id=boss_id,
            type=EntityType.BOSS,
            name="Goo" if is_goo else f"Floor {floor.floor_id} Boss",
            pos=Position(x=x, y=y),
            hp=300 if is_goo else 100 + (floor.floor_id * 20),
            max_hp=300 if is_goo else 100 + (floor.floor_id * 20),
            attack=12 if is_goo else 10 + floor.floor_id,
            defense=3 if is_goo else 5 + floor.floor_id,
            attack_cooldown=2.5 if is_goo else 3.0,
            faction=Faction.DUNGEON,
            exp=10 + floor.floor_id,
        )

    def add_player(self, player_id: str, name: str, class_type: str = CharacterClass.WARRIOR, is_admin: bool = False) -> Player:
        floor = self._get_or_create_floor(1)
        spawn_pos = self._get_stairs_pos(TileType.STAIRS_UP, floor_id=floor.floor_id)

        self.player_count += 1

        # Starting gear goes straight into the relevant equip slots (SPD-style:
        # equipped items live in Belongings, not the backpack).
        belongings = Belongings()

        if class_type == CharacterClass.WARRIOR:
            belongings.weapon = Weapon(
                id=str(uuid.uuid4()),
                name="Shortsword",
                damage=3,
                range=1,
                strength_requirement=10,
                attack_cooldown=3.0,
            )
            belongings.armor = Wearable(id=str(uuid.uuid4()), name="Cloth Armor", strength_requirement=10, health_boost=5)

        elif class_type == CharacterClass.MAGE:
            belongings.weapon = Staff(
                id=str(uuid.uuid4()),
                name="Mage's Staff",
                damage=2,
                magic_damage=3,
                strength_requirement=10,
                charges=4,
                attack_cooldown=3.0,
            )

        elif class_type == CharacterClass.ROGUE:
            belongings.weapon = Weapon(
                id=str(uuid.uuid4()),
                name="Dagger",
                damage=2,
                range=1,
                strength_requirement=9,
                attack_cooldown=1.5,
            )
            belongings.armor = Wearable(id=str(uuid.uuid4()), name="Rogue's Cloak", strength_requirement=9, health_boost=2)

        elif class_type == CharacterClass.HUNTRESS:
            belongings.weapon = Bow(
                id=str(uuid.uuid4()),
                name="Spirit Bow",
                damage=2,
                strength_requirement=10,
                attack_cooldown=3.5,
            )

        player = Player(
            id=player_id,
            name=name,
            pos=spawn_pos,
            hp=10,
            max_hp=10,
            attack=3,
            defense=1,
            faction=Faction.PLAYER,
            class_type=class_type,
            belongings=belongings,
            floor_id=1,
            is_admin=is_admin,
        )

        player.hp = player.get_total_max_hp()

        self.players[player_id] = player
        self.depth = 1
        return player

    def _get_stairs_pos(self, tile_type: int, floor_id: Optional[int] = None) -> Position:
        floor = self._get_or_create_floor(floor_id or self.depth)
        for y in range(self.height):
            for x in range(self.width):
                if floor.grid[y][x] == tile_type:
                    return Position(x=x, y=y)
        return Position(x=0, y=0)

    def _move_player_to_floor(self, player: Player, target_floor_id: int, spawn_tile: int):
        target_floor_id = max(1, min(MAX_FLOOR_ID, target_floor_id))
        self._get_or_create_floor(target_floor_id)

        player.floor_id = target_floor_id
        player.pos = self._get_stairs_pos(spawn_tile, floor_id=target_floor_id)

        self.depth = target_floor_id

    def search(self, player_id: str):
        player = self.players.get(player_id)
        if not player:
            return

        floor = self._get_or_create_floor(player.floor_id)
        patches: List[dict] = []
        found_secret_door = False

        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                tx = player.pos.x + dx
                ty = player.pos.y + dy
                if not (0 <= tx < self.width and 0 <= ty < self.height):
                    continue

                pos = (tx, ty)
                if pos in floor.hidden_doors:
                    actual_tile = floor.hidden_doors.pop(pos)
                    floor.grid[ty][tx] = actual_tile
                    patches.append({"x": tx, "y": ty, "tile": actual_tile})
                    found_secret_door = True

                trap = floor.traps.get(pos)
                if trap and trap.hidden:
                    trap.hidden = False
                    if floor.grid[ty][tx] == TileType.FLOOR:
                        floor.grid[ty][tx] = TileType.FLOOR_COBBLE
                        patches.append({"x": tx, "y": ty, "tile": TileType.FLOOR_COBBLE})

        if patches:
            # Tile mutations changed the grid — refresh derived flag maps
            # so LOS / pathfinding / openSpace pick up the new state on
            # the next query (a revealed door is now passable + see-through).
            floor.rebuild_flags()
            self.add_event("MAP_PATCH", {"tiles": patches}, floor_id=player.floor_id)

        if found_secret_door:
            self.add_event("PLAY_SOUND", {"sound": "SECRET"}, player_id=player_id)

        self.add_event("SEARCH", {"player": player_id, "revealed_tiles": len(patches)}, player_id=player_id)

    def _try_unlock_locked_door(self, player: Player, floor: FloorState, x: int, y: int) -> bool:
        key_id = floor.locked_doors.get((x, y))
        if not key_id:
            return False

        key_idx = next(
            (
                idx
                for idx, item in enumerate(player.inventory)
                if isinstance(item, Key) and item.key_id == key_id
            ),
            -1,
        )
        if key_idx == -1:
            return False

        player.inventory.pop(key_idx)
        floor.locked_doors.pop((x, y), None)
        floor.grid[y][x] = TileType.DOOR
        # Tile mutated from LOCKED_DOOR to DOOR — refresh flag maps so
        # LOS/pathfinding sees the door as passable now.
        floor.rebuild_flags()

        self.add_event("MAP_PATCH", {"tiles": [{"x": x, "y": y, "tile": TileType.DOOR}]}, floor_id=player.floor_id)
        self.add_event("UNLOCK", {"player": player.id, "x": x, "y": y}, floor_id=player.floor_id)
        return True

    def _trigger_trap_if_needed(self, floor: FloorState, player: Player, floor_id: int):
        pos = (player.pos.x, player.pos.y)
        trap = floor.traps.get(pos)
        if not trap or not trap.active:
            return

        patches: List[dict] = []
        if trap.hidden:
            trap.hidden = False

        if floor.grid[player.pos.y][player.pos.x] == TileType.FLOOR:
            floor.grid[player.pos.y][player.pos.x] = TileType.FLOOR_COBBLE
            patches.append({"x": player.pos.x, "y": player.pos.y, "tile": TileType.FLOOR_COBBLE})

        trap.active = False

        damage = 2
        dealt = player.take_damage(damage)

        if patches:
            self.add_event("MAP_PATCH", {"tiles": patches}, floor_id=floor_id)

        self.add_event(
            "TRAP_TRIGGERED",
            {"player": player.id, "trap": trap.trap_type, "damage": dealt},
            floor_id=floor_id,
        )
        if dealt > 0:
            self.add_event("DAMAGE", {"target": player.id, "amount": dealt}, floor_id=floor_id)
            self.add_event("PLAY_SOUND", {"sound": "HIT_BODY"}, floor_id=floor_id)
            if player.hp / max(1, player.get_total_max_hp()) <= 0.3:
                self.add_event("PLAY_SOUND", {"sound": "HEALTH_WARN"}, floor_id=floor_id)

    def move_entity(self, entity_id: str, dx: int, dy: int):
        floor_id, entity = self._get_floor_for_entity(entity_id)
        if entity is None or floor_id is None:
            return

        floor = self._get_or_create_floor(floor_id)

        if isinstance(entity, Player) and entity.is_downed:
            return

        new_x = entity.pos.x + dx
        new_y = entity.pos.y + dy

        if not (0 <= new_x < self.width and 0 <= new_y < self.height):
            return

        target_entity = None
        for p in self._players_on_floor(floor_id):
            if p.id != entity_id and p.pos.x == new_x and p.pos.y == new_y:
                target_entity = p
                break

        if not target_entity:
            for m in floor.mobs.values():
                if m.id != entity_id and m.pos.x == new_x and m.pos.y == new_y and m.is_alive:
                    target_entity = m
                    break

        if target_entity:
            if (
                isinstance(entity, Player)
                and isinstance(target_entity, Player)
                and target_entity.is_downed
                and target_entity.is_alive  # death is permanent: cannot revive a dead player
                and entity.faction == target_entity.faction
            ):
                revive_potion_idx = next(
                    (i for i, item in enumerate(entity.inventory) if isinstance(item, RevivingPotion)),
                    -1,
                )
                if revive_potion_idx != -1:
                    entity.inventory.pop(revive_potion_idx)
                    target_entity.is_downed = False
                    target_entity.hp = target_entity.get_total_max_hp() // 2
                    self.add_event("REVIVE", {"target": target_entity.id, "source": entity.id}, floor_id=floor_id)
                    return

            if entity.faction != target_entity.faction:
                if isinstance(entity, Player) and entity.is_downed:
                    return

                current_time = time.time()
                cooldown = entity.attack_cooldown
                if isinstance(entity, Player) and entity.equipped_weapon:
                    cooldown = entity.equipped_weapon.attack_cooldown

                if current_time - entity.last_attack_time < cooldown:
                    return

                entity.last_attack_time = current_time

                attack_power = entity.attack
                if isinstance(entity, Player):
                    attack_power = entity.get_total_attack()

                dmg = target_entity.take_damage(attack_power)
                self.add_event(
                    "ATTACK",
                    {"source": entity.id, "target": target_entity.id, "damage": dmg},
                    floor_id=floor_id,
                )
                if isinstance(entity, Player):
                    self.add_event("PLAY_SOUND", {"sound": "HIT_SLASH"}, floor_id=floor_id)

                if dmg > 0:
                    self.add_event("DAMAGE", {"target": target_entity.id, "amount": dmg}, floor_id=floor_id)

                    if isinstance(target_entity, Player):
                        self.add_event("PLAY_SOUND", {"sound": "HIT_BODY"}, floor_id=floor_id)
                        if target_entity.hp / target_entity.get_total_max_hp() <= 0.3:
                            self.add_event("PLAY_SOUND", {"sound": "HEALTH_WARN"}, floor_id=floor_id)

                    if not target_entity.is_alive:
                        self.add_event("DEATH", {"target": target_entity.id}, floor_id=floor_id)
                        if isinstance(entity, Player) and isinstance(target_entity, MobEntity):
                            if entity.earn_exp(target_entity.exp):
                                self.add_event("LEVEL_UP", {"player": entity.id}, floor_id=floor_id)
            return

        tile = floor.grid[new_y][new_x]
        if tile == TileType.LOCKED_DOOR:
            if not isinstance(entity, Player):
                return
            if not self._try_unlock_locked_door(entity, floor, new_x, new_y):
                return
            tile = floor.grid[new_y][new_x]

        if not floor.flags or not floor.flags.passable[new_y][new_x]:
            return

        if not isinstance(entity, Player) and self._is_in_safe_room(floor, new_x, new_y):
            return

        entity.move(dx, dy)
        if isinstance(entity, Player):
            self.add_event("MOVE", {"entity": entity_id, "x": entity.pos.x, "y": entity.pos.y}, floor_id=floor_id)

        if isinstance(entity, Player):
            items_to_pickup = [
                i_id
                for i_id, i in floor.items.items()
                if i.pos and i.pos.x == entity.pos.x and i.pos.y == entity.pos.y
                and i.type != "grave"  # graves are scenery, not pickable
            ]
            for i_id in items_to_pickup:
                item = floor.items[i_id]
                if entity.add_to_inventory(item):
                    del floor.items[i_id]
                    self.add_event("PICKUP", {"player": entity.id, "item": item.id}, floor_id=floor_id)

            self._trigger_trap_if_needed(floor, entity, floor_id)

        if isinstance(entity, Player) and tile == TileType.STAIRS_DOWN and entity.floor_id < MAX_FLOOR_ID:
            self._move_player_to_floor(entity, entity.floor_id + 1, TileType.STAIRS_UP)
            self.add_event("STAIRS_DOWN", {"player": entity_id}, player_id=entity_id)

        if isinstance(entity, Player) and tile == TileType.STAIRS_UP and entity.floor_id > 1:
            self._move_player_to_floor(entity, entity.floor_id - 1, TileType.STAIRS_DOWN)
            self.add_event("STAIRS_UP", {"player": entity_id}, player_id=entity_id)

    def perform_ranged_attack(self, player_id: str, item_id: str, target_x: int, target_y: int) -> Optional[int]:
        player = self.players.get(player_id)
        if not player or player.is_downed:
            return None

        floor_id = player.floor_id
        floor = self._get_or_create_floor(floor_id)

        item = player.belongings.get_item(item_id)

        if not item:
            return None

        is_throwable = isinstance(item, Throwable)
        is_weapon = isinstance(item, Weapon)
        is_wand = isinstance(item, Wand)

        if not (is_throwable or is_wand or (is_weapon and getattr(item, "projectile_type", None))):
            return None

        if is_wand and item.charges <= 0:
            return None

        current_time = time.time()
        cooldown = 1.0
        if is_weapon:
            cooldown = item.attack_cooldown

        if (current_time - player.last_attack_time) < cooldown:
            return None

        dist = abs(player.pos.x - target_x) + abs(player.pos.y - target_y)
        max_range = item.range if hasattr(item, "range") else 1
        if dist > max_range:
            return None

        if not self._is_in_los(player.pos, Position(x=target_x, y=target_y), floor_id=floor_id):
            return None

        player.last_attack_time = current_time
        projectile_type = getattr(item, "projectile_type", "arrow")

        target_entity = None
        for p in self._players_on_floor(floor_id):
            if p.id != player_id and p.pos.x == target_x and p.pos.y == target_y:
                target_entity = p
                break

        if not target_entity:
            for m in floor.mobs.values():
                if m.is_alive and m.pos.x == target_x and m.pos.y == target_y:
                    target_entity = m
                    break

        self.add_event(
            "RANGED_ATTACK",
            {
                "source": player_id,
                "x": player.pos.x,
                "y": player.pos.y,
                "target_x": target_x,
                "target_y": target_y,
                "projectile": projectile_type,
            },
            floor_id=floor_id,
        )

        damage_dealt = 0
        if target_entity and player.faction != target_entity.faction:
            if is_wand:
                attack_power = item.damage  # wands don't scale with strength
            elif is_weapon:
                if player.belongings.weapon and item.id == player.belongings.weapon.id:
                    attack_power = player.get_total_attack()
                else:
                    attack_power = item.damage + (player.strength // 2)
            else:
                attack_power = item.damage + (player.strength // 2)

            damage_dealt = target_entity.take_damage(attack_power)
            self.add_event("DAMAGE", {"target": target_entity.id, "amount": damage_dealt}, floor_id=floor_id)

            if damage_dealt > 0:
                if projectile_type == "magic_bolt":
                    self.add_event("PLAY_SOUND", {"sound": "HIT_MAGIC"}, floor_id=floor_id)
                else:
                    self.add_event("PLAY_SOUND", {"sound": "HIT_ARROW"}, floor_id=floor_id)

                if isinstance(target_entity, Player):
                    self.add_event("PLAY_SOUND", {"sound": "HIT_BODY"}, floor_id=floor_id)
                    if target_entity.hp / target_entity.get_total_max_hp() <= 0.3:
                        self.add_event("PLAY_SOUND", {"sound": "HEALTH_WARN"}, floor_id=floor_id)

            if not target_entity.is_alive:
                self.add_event("DEATH", {"target": target_entity.id}, floor_id=floor_id)
                if isinstance(target_entity, MobEntity):
                    if player.earn_exp(target_entity.exp):
                        self.add_event("LEVEL_UP", {"player": player.id}, floor_id=floor_id)

        if is_wand:
            item.charges -= 1
        elif is_throwable and item.consumable:
            removed = player.belongings.backpack.detach(item.id)
            if removed is not None and player.belongings.get_item(item.id) is None:
                player.quickslot.convert_to_placeholder(removed)

        return damage_dealt

    # --- generic item-action dispatch -------------------------------------
    def execute_item_action(self, player_id: str, item_id: str, action: str,
                            target_x: Optional[int] = None, target_y: Optional[int] = None):
        player = self.players.get(player_id)
        if not player or not player.is_alive or player.is_downed:
            return
        item = player.belongings.get_item(item_id)
        if item is None:
            return
        if action not in item.actions(player):
            return  # server-authoritative: reject actions the item doesn't offer
        handler = item_actions.ITEM_ACTION_DISPATCH.get(action)
        if handler is not None:
            handler(self, player, item, target_x, target_y)

    def set_quickslot(self, player_id: str, index: int, item_id: str):
        player = self.players.get(player_id)
        if not player:
            return
        item = player.belongings.get_item(item_id)
        if item is not None:
            player.quickslot.set_slot(index, item)

    def use_quickslot(self, player_id: str, index: int,
                      target_x: Optional[int] = None, target_y: Optional[int] = None):
        player = self.players.get(player_id)
        if not player or not (0 <= index < len(player.quickslot.slots)):
            return
        entry = player.quickslot.slots[index]
        if not entry.item_id:
            return
        item = player.belongings.get_item(entry.item_id)
        if item is None:
            return
        action = item.default_action()
        if action:
            self.execute_item_action(player_id, item.id, action, target_x, target_y)

    def use_item(self, player_id: str, item_id: str,
                 target_x: Optional[int] = None, target_y: Optional[int] = None):
        player = self.players.get(player_id)
        if not player:
            return
        item = player.belongings.get_item(item_id)
        if item is None:
            return
        action = item.default_action()
        if action:
            self.execute_item_action(player_id, item_id, action, target_x, target_y)

    def identify_kind(self, item):
        # Reveal a potion/scroll kind for the whole party (co-op shared knowledge).
        self.identified_kinds.add(item.kind)
        item.level_known = True
        item.cursed_known = True

    def next_floor(self, player_id: Optional[str] = None):
        target_players = []
        if player_id and player_id in self.players:
            target_players = [self.players[player_id]]
        elif not player_id and len(self.players) == 1:
            target_players = list(self.players.values())

        for player in target_players:
            if player.floor_id < MAX_FLOOR_ID:
                self._move_player_to_floor(player, player.floor_id + 1, TileType.STAIRS_UP)

    def prev_floor(self, player_id: Optional[str] = None):
        target_players = []
        if player_id and player_id in self.players:
            target_players = [self.players[player_id]]
        elif not player_id and len(self.players) == 1:
            target_players = list(self.players.values())

        for player in target_players:
            if player.floor_id > 1:
                self._move_player_to_floor(player, player.floor_id - 1, TileType.STAIRS_DOWN)

    def _kill_player(self, player: Player, floor: FloorState, floor_id: int):
        # Run the death sequence once: scatter the backpack and mark the spot
        # with a grave (mirrors Hero.reallyDie in Shattered Pixel Dungeon).
        player.death_processed = True

        # Collect passable 8-neighbour cells with no item on them, shuffled.
        free_cells: List[Tuple[int, int]] = []
        for ox in (-1, 0, 1):
            for oy in (-1, 0, 1):
                if ox == 0 and oy == 0:
                    continue
                cx, cy = player.pos.x + ox, player.pos.y + oy
                if not (0 <= cx < self.width and 0 <= cy < self.height):
                    continue
                if not floor.flags or not floor.flags.passable[cy][cx]:
                    continue
                if any(i.pos and i.pos.x == cx and i.pos.y == cy for i in floor.items.values()):
                    continue
                free_cells.append((cx, cy))
        random.shuffle(free_cells)

        # Drop everything the hero carried — equipped gear plus the backpack's
        # top-level items (sub-bags drop whole). Overflow lands on the death tile.
        dropped_items = [s for s in player.belongings.equipped_slots() if s is not None]
        dropped_items += list(player.belongings.backpack.items)
        for idx, item in enumerate(dropped_items):
            if idx < len(free_cells):
                cx, cy = free_cells[idx]
            else:
                cx, cy = player.pos.x, player.pos.y
            item.pos = Position(x=cx, y=cy)
            floor.items[item.id] = item
        player.belongings = Belongings()
        player.quickslot = QuickSlot()

        # Grave marker on the death tile.
        grave_id = f"grave_{uuid.uuid4().hex[:8]}"
        floor.items[grave_id] = Item(
            id=grave_id,
            name="Grave",
            type="grave",
            pos=Position(x=player.pos.x, y=player.pos.y),
        )

        self.add_event("DEATH", {"target": player.id}, floor_id=floor_id)

    def update_tick(self):
        # Process any players that died since the last tick (from any source).
        for player in self.players.values():
            if not player.is_alive and not player.death_processed:
                self._kill_player(player, self._get_or_create_floor(player.floor_id), player.floor_id)

        # Keep each player's active_effects list in sync with current state so the
        # client can render the buff indicator (mirrors SPD's BuffIndicator).
        for player in self.players.values():
            self._sync_effects(player)

        for player in self.players.values():
            if player.is_downed or not player.is_alive:
                continue

            if player.path_queue:
                now = time.time()
                if now - player.last_auto_move_time >= AUTO_MOVE_INTERVAL:
                    dx, dy = player.path_queue.pop(0)
                    floor = self._get_or_create_floor(player.floor_id)
                    nx, ny = player.pos.x + dx, player.pos.y + dy
                    # Stop (don't auto-attack/desync) if a live mob physically blocks the
                    # next tile. Travel that leads away from enemies never hits this, so the
                    # player can always walk away even with an enemy right next to them.
                    if any(m.is_alive and m.pos.x == nx and m.pos.y == ny for m in floor.mobs.values()):
                        player.path_queue = []
                    else:
                        player.last_auto_move_time = now
                        self.move_entity(player.id, dx, dy)

            self._apply_heal_tick(player)
            self._apply_room_heal_tick(player)

        for floor_id, floor in self.floors.items():
            active_players = [p for p in self._players_on_floor(floor_id) if p.is_alive and not p.is_downed]
            if not active_players:
                continue

            for mob in list(floor.mobs.values()):
                if not mob.is_alive:
                    continue

                target_player = self._find_nearest_player(mob.pos, floor_id)
                dist = self._get_distance(mob.pos, target_player.pos) if target_player else float("inf")

                if self.difficulty == Difficulty.EASY:
                    if target_player and dist <= 1:
                        dx, dy = target_player.pos.x - mob.pos.x, target_player.pos.y - mob.pos.y
                        self.move_entity(mob.id, dx, dy)
                    elif random.random() < 0.05:
                        dx, dy = random.choice([(0, 1), (0, -1), (1, 0), (-1, 0)])
                        self.move_entity(mob.id, dx, dy)

                elif self.difficulty == Difficulty.NORMAL:
                    if target_player and dist <= 1:
                        dx, dy = target_player.pos.x - mob.pos.x, target_player.pos.y - mob.pos.y
                        self.move_entity(mob.id, dx, dy)
                    elif target_player and self._is_in_los(mob.pos, target_player.pos, floor_id=floor_id):
                        step = self._get_next_step_to(mob.pos, target_player.pos, floor_id=floor_id)
                        if step:
                            self.move_entity(mob.id, step[0], step[1])
                    elif random.random() < 0.05:
                        dx, dy = random.choice([(0, 1), (0, -1), (1, 0), (-1, 0)])
                        self.move_entity(mob.id, dx, dy)

                elif self.difficulty == Difficulty.HARD:
                    if target_player and dist <= 1:
                        dx, dy = target_player.pos.x - mob.pos.x, target_player.pos.y - mob.pos.y
                        self.move_entity(mob.id, dx, dy)
                    elif target_player and dist < 20:
                        step = self._get_next_step_to(mob.pos, target_player.pos, floor_id=floor_id)
                        if step:
                            self.move_entity(mob.id, step[0], step[1])
                    elif random.random() < 0.05:
                        dx, dy = random.choice([(0, 1), (0, -1), (1, 0), (-1, 0)])
                        self.move_entity(mob.id, dx, dy)

    def _sync_effects(self, player: Player):
        # Derive the generic active_effects list from current state. Currently the
        # only active effect is the regen/healing buff (icon 44 = BuffIndicator.HEALING).
        # `duration` tracks the largest pool seen so the client can show progress.
        existing = {e.key: e for e in player.active_effects}
        effects = []
        if player.heal_left > 0:
            prev = existing.get("regen")
            duration = max(prev.duration if prev else 0.0, player.heal_left)
            effects.append(Effect(
                key="regen", name="Healing", icon=44,
                remaining=player.heal_left, duration=duration,
            ))
        player.active_effects = effects

    def _apply_heal_tick(self, player: Player):
        # Mirrors Healing.act() from the original game: heal a decaying chunk of the
        # remaining pool each application, emitting a HEAL event for the floating
        # number + sparkle particles on the client.
        if player.heal_left <= 0:
            return

        player.heal_cooldown -= 1
        if player.heal_cooldown > 0:
            return

        amt = round(player.heal_left * player.heal_pct_per_tick) + player.heal_flat_per_tick
        amt = max(1, min(amt, player.heal_left))

        if player.hp < player.get_total_max_hp():
            player.hp = min(player.get_total_max_hp(), player.hp + amt)

        player.heal_left -= amt
        player.heal_cooldown = HEAL_TICK_INTERVAL

        self.add_event(
            "HEAL",
            {"target": player.id, "amount": int(amt), "x": player.pos.x, "y": player.pos.y},
            floor_id=player.floor_id,
        )

        if player.heal_left <= 0:
            player.heal_left = 0.0
            player.heal_pct_per_tick = 0.0
            player.heal_flat_per_tick = 0.0

    def _apply_room_heal_tick(self, player: Player):
        # Passive sanctuary healing: standing in a floor's entrance (up-stairs) room
        # restores ROOM_HEAL_AMOUNT HP per second, reusing the same green HEAL event
        # as health potions for the floating number + sparkles on the client.
        floor = self.floors.get(player.floor_id)
        if floor is None or not floor.rooms:
            return

        if not self._is_in_entrance_room(floor, player.pos.x, player.pos.y):
            player.room_heal_cooldown = 0  # next heal fires immediately on re-entry
            return

        max_hp = player.get_total_max_hp()
        if player.hp >= max_hp:
            return

        player.room_heal_cooldown -= 1
        if player.room_heal_cooldown > 0:
            return

        amt = min(ROOM_HEAL_AMOUNT, max_hp - player.hp)
        player.hp += amt
        player.room_heal_cooldown = HEAL_TICK_INTERVAL

        self.add_event(
            "HEAL",
            {"target": player.id, "amount": int(amt), "x": player.pos.x, "y": player.pos.y},
            floor_id=player.floor_id,
        )

    def _find_nearest_player(self, pos: Position, floor_id: int) -> Optional[Player]:
        candidates = [p for p in self._players_on_floor(floor_id) if p.is_alive and not p.is_downed]
        if not candidates:
            return None

        nearest = None
        min_dist = float("inf")
        for player in candidates:
            distance = self._get_distance(pos, player.pos)
            if distance < min_dist:
                min_dist = distance
                nearest = player
        return nearest

    def _get_distance(self, p1: Position, p2: Position) -> int:
        return abs(p1.x - p2.x) + abs(p1.y - p2.y)

    def _is_door_open(self, floor: FloorState, x: int, y: int) -> bool:
        for player in self.players.values():
            if player.floor_id == floor.floor_id and player.pos.x == x and player.pos.y == y:
                return True
        for mob in floor.mobs.values():
            if mob.is_alive and mob.pos.x == x and mob.pos.y == y:
                return True
        for item in floor.items.values():
            if item.pos and item.pos.x == x and item.pos.y == y:
                return True
        return False

    def _get_open_doors(self, floor: FloorState):
        occupied = set()
        for player in self.players.values():
            if player.floor_id == floor.floor_id:
                occupied.add((player.pos.x, player.pos.y))
        for mob in floor.mobs.values():
            if mob.is_alive:
                occupied.add((mob.pos.x, mob.pos.y))
        for item in floor.items.values():
            if item.pos:
                occupied.add((item.pos.x, item.pos.y))
        return [
            [x, y] for x, y in occupied
            if 0 <= x < self.width and 0 <= y < self.height
            and floor.grid[y][x] == TileType.DOOR
        ]

    def _is_in_los(self, p1: Position, p2: Position, floor_id: Optional[int] = None) -> bool:
        floor = self._get_or_create_floor(floor_id or self.depth)

        x1, y1 = p1.x, p1.y
        x2, y2 = p2.x, p2.y
        dx = abs(x2 - x1)
        dy = -abs(y2 - y1)
        sx = 1 if x1 < x2 else -1
        sy = 1 if y1 < y2 else -1
        err = dx + dy

        curr_x, curr_y = x1, y1
        while True:
            if curr_x == x2 and curr_y == y2:
                return True

            if 0 <= curr_x < self.width and 0 <= curr_y < self.height:
                if not (curr_x == x1 and curr_y == y1):
                    tile = floor.grid[curr_y][curr_x]
                    if tile == TileType.DOOR:
                        if not self._is_door_open(floor, curr_x, curr_y):
                            return False
                    elif floor.flags and floor.flags.los_blocking[curr_y][curr_x]:
                        return False

            e2 = 2 * err
            if e2 >= dy:
                err += dy
                curr_x += sx
            if e2 <= dx:
                err += dx
                curr_y += sy

    def _get_next_step_to(self, start: Position, target: Position, floor_id: Optional[int] = None) -> Optional[tuple]:
        floor = self._get_or_create_floor(floor_id or self.depth)

        queue = [(start.x, start.y, [])]
        visited = {(start.x, start.y)}

        while queue:
            x, y, path = queue.pop(0)

            if x == target.x and y == target.y:
                if path:
                    return path[0]
                return None

            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nx, ny = x + dx, y + dy
                if (
                    0 <= nx < self.width
                    and 0 <= ny < self.height
                    and floor.flags
                    and floor.flags.passable[ny][nx]
                    and (nx, ny) not in visited
                ):
                    blocked = False
                    for mob in floor.mobs.values():
                        if mob.is_alive and mob.pos.x == nx and mob.pos.y == ny:
                            blocked = True
                            break

                    if not blocked:
                        visited.add((nx, ny))
                        queue.append((nx, ny, path + [(dx, dy)]))

            if len(visited) > 400:
                break

        return None

    def _bfs_full_path(self, start: Position, target: Position, floor_id: int) -> List[Tuple[int, int]]:
        floor = self._get_or_create_floor(floor_id)
        queue = [(start.x, start.y, [])]
        visited = {(start.x, start.y)}
        while queue:
            x, y, path = queue.pop(0)
            if x == target.x and y == target.y:
                return path
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nx, ny = x + dx, y + dy
                if (
                    0 <= nx < self.width
                    and 0 <= ny < self.height
                    and floor.flags
                    and floor.flags.passable[ny][nx]
                    and (nx, ny) not in visited
                ):
                    visited.add((nx, ny))
                    queue.append((nx, ny, path + [(dx, dy)]))
            if len(visited) > 500:
                break
        return []

    def change_difficulty(self, new_level: str):
        if new_level in [Difficulty.EASY, Difficulty.NORMAL, Difficulty.HARD]:
            self.difficulty = new_level

    def get_visible_tiles(self, pos: Position, radius: int = 8, floor_id: Optional[int] = None) -> List[Tuple[int, int]]:
        floor = self._get_or_create_floor(floor_id or self.depth)

        visible = []
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                tx, ty = pos.x + dx, pos.y + dy
                if 0 <= tx < self.width and 0 <= ty < self.height:
                    dist_sq = dx * dx + dy * dy
                    if dist_sq <= radius * radius:
                        if self._is_in_los(pos, Position(x=tx, y=ty), floor_id=floor.floor_id):
                            visible.append((tx, ty))
        return visible

    # --- identification masking -------------------------------------------
    # Per-run scrambled display names for still-unidentified consumable kinds
    # (mirrors SPD's randomised potion colours / scroll runes).
    _POTION_LABELS = ["Crimson", "Azure", "Charcoal", "Ivory", "Golden", "Magenta",
                      "Turquoise", "Jade", "Indigo", "Amber", "Bistre", "Rose"]
    _SCROLL_LABELS = ["Kaunan", "Sowilo", "Laguz", "Yngvi", "Gyfu", "Raido",
                      "Isaz", "Mannaz", "Naudiz", "Berkanan", "Odal", "Tiwaz"]

    def _label_for(self, kind: str, typ: str) -> str:
        if kind not in self.kind_labels:
            pool = self._POTION_LABELS if typ == "potion" else self._SCROLL_LABELS
            used = set(self.kind_labels.values())
            nxt = next((f"{w} Potion" if typ == "potion" else f"Scroll of {w}"
                        for w in pool
                        if (f"{w} Potion" if typ == "potion" else f"Scroll of {w}") not in used),
                       kind)
            self.kind_labels[kind] = nxt
        return self.kind_labels[kind]

    def _mask_item_dict(self, d: Optional[dict]) -> Optional[dict]:
        # Recursively obscure unidentified potion/scroll types in a serialized
        # item dict: scramble the name, collapse `kind` to the generic category so
        # the client can't read the subtype, and hide subtype fields.
        if not d:
            return d
        items = d.get("items")
        if isinstance(items, list):
            for it in items:
                self._mask_item_dict(it)
        if d.get("type") in ("potion", "scroll") and d.get("kind") not in self.identified_kinds:
            d["name"] = self._label_for(d["kind"], d["type"])
            d["kind"] = d["type"]
            d.pop("effect", None)
            d["level_known"] = False
        return d

    def _serialize_player(self, p: Player) -> dict:
        d = p.model_dump()

        # Map every live item by id so we can attach the server-authoritative
        # action list (SPD's Item.actions) the client renders its menu from.
        id2item: Dict[str, object] = {}

        def collect(bag):
            id2item[bag.id] = bag
            for it in bag.items:
                id2item[it.id] = it
                if isinstance(it, Bag):
                    collect(it)

        collect(p.belongings.backpack)
        for s in p.belongings.equipped_slots():
            if s is not None:
                id2item[s.id] = s

        def process(node):
            if not node:
                return
            for it in (node.get("items") or []):
                process(it)
            live = id2item.get(node.get("id"))
            if live is not None:
                node["actions"] = live.actions(p)
                node["default_action"] = live.default_action()
            self._mask_item_dict(node)

        belongings = d.get("belongings", {})
        for slot in ("weapon", "armor", "artifact", "misc", "ring"):
            process(belongings.get(slot))
        process(belongings.get("backpack"))
        # Legacy computed views serialize as independent copies — process too.
        for it in (d.get("inventory") or []):
            process(it)
        process(d.get("equipped_weapon"))
        process(d.get("equipped_wearable"))
        return d

    def _serialize_floor_item(self, item) -> dict:
        return self._mask_item_dict(item.model_dump())

    def get_state(self, player_id: Optional[str] = None):
        if player_id and player_id in self.players:
            player = self.players[player_id]
            floor = self._get_or_create_floor(player.floor_id)
            floor_players = [p for p in self._players_on_floor(player.floor_id)]

            if player.is_admin:
                all_tiles = [(x, y) for y in range(self.height) for x in range(self.width)]
                return {
                    "depth": player.floor_id,
                    "players": [self._serialize_player(p) for p in floor_players],
                    "mobs": [m.model_dump() for m in floor.mobs.values() if m.is_alive],
                    "items": [self._serialize_floor_item(i) for i in floor.items.values() if i.pos],
                    "visible_tiles": all_tiles,
                    "open_doors": self._get_open_doors(floor),
                    "grid": floor.grid,
                }

            visible_tiles = self.get_visible_tiles(player.pos, floor_id=player.floor_id)
            visible_set = set(visible_tiles)

            return {
                "depth": player.floor_id,
                "players": [self._serialize_player(p) for p in floor_players],
                "mobs": [m.model_dump() for m in floor.mobs.values() if m.is_alive and (m.pos.x, m.pos.y) in visible_set],
                "items": [self._serialize_floor_item(i) for i in floor.items.values() if i.pos and (i.pos.x, i.pos.y) in visible_set],
                "visible_tiles": visible_tiles,
                "open_doors": self._get_open_doors(floor),
                "grid": floor.grid,
            }

        floor = self._get_or_create_floor(self.depth)
        return {
            "depth": self.depth,
            "players": [self._serialize_player(p) for p in self._players_on_floor(self.depth)],
            "mobs": [m.model_dump() for m in floor.mobs.values() if m.is_alive],
            "items": [self._serialize_floor_item(i) for i in floor.items.values() if i.pos],
            "open_doors": self._get_open_doors(floor),
            "grid": floor.grid,
        }
