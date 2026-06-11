"""Convert SPD-parity GenLevel output into the remake's FloorState.

`gen_level_to_floor_state()` maps SPD's terrain constants, mob stubs, item
stubs, traps, and doors to the existing ``FloorState`` / ``MobEntity`` /
``Item`` types so that ``spd_levelgen.build_floor()`` results can be dropped
directly into the game loop.
"""

import uuid
from typing import Dict, List, Tuple

from app.engine.dungeon.constants import RoomKind, TrapType, TrapVisual
from app.engine.dungeon.models import Room as LegacyRoom, TrapInfo
from app.engine.dungeon.spd_levelgen import terrain as spd_terrain
from app.engine.dungeon.spd_levelgen.level import GenLevel
from app.engine.dungeon.spd_levelgen.mob_spawner import GenMob
from app.engine.dungeon.spd_levelgen.room import DoorType
from app.engine.dungeon.spd_levelgen.traps import Trap as SpdTrap
from app.engine.dungeon.generator import TileType
from app.engine.entities.base import (
    Armor,
    Dewdrop,
    EntityType,
    Faction,
    Food,
    Gold,
    HealthPotion,
    Item,
    Key,
    Mob as MobEntity,
    Position,
    Scroll,
    Seed,
    Stone,
    Wand,
    Weapon,
)
from app.engine.entities.mobs import (
    AcidicScorpio,
    AlbinoRat,
    ArmoredStatue,
    Bandit,
    Bat,
    Bee,
    BlueShaman,
    Brute,
    ArmoredBrute,
    BrightFist,
    BurningFist,
    CausticSlime,
    ChaosElemental,
    Crab,
    DarkFist,
    DKGhoul,
    DKGolem,
    DKMonk,
    DKWarlock,
    DM100,
    DM200,
    DM201,
    DM300,
    DemonSpawner,
    EbonyMimic,
    Eye,
    FireElemental,
    FrostElemental,
    Ghoul,
    Gnoll,
    GnollExile,
    GoldenMimic,
    Golem,
    Goo,
    Guard,
    HermitCrab,
    Mimic,
    Monk,
    Necromancer,
    PhantomPiranha,
    Piranha,
    PurpleShaman,
    Pylon,
    RatKing,
    Rat,
    RedShaman,
    RipperDemon,
    RottingFist,
    RustedFist,
    Scorpio,
    Senior,
    ShockElemental,
    Skeleton,
    Slime,
    Snake,
    SoiledFist,
    SpectralNecromancer,
    Spinner,
    Statue,
    Succubus,
    Swarm,
    Tengu,
    Thief,
    TormentedSpirit,
    Warlock,
    Wraith,
    YogDzewa,
    YogEye,
    YogRipper,
    YogScorpio,
    DwarfKing,
)
from app.engine.game.floor_state import FloorState
from app.engine.dungeon.spd_levelgen.generator import RolledItem

# SPD terrain constant -> remake TileType
_SPD_TO_TILE = {
    spd_terrain.CHASM: TileType.WALL,
    spd_terrain.EMPTY: TileType.FLOOR,
    spd_terrain.GRASS: TileType.FLOOR_GRASS,
    spd_terrain.EMPTY_WELL: TileType.FLOOR,
    spd_terrain.WALL: TileType.WALL,
    spd_terrain.DOOR: TileType.DOOR,
    spd_terrain.OPEN_DOOR: TileType.OPEN_DOOR,
    spd_terrain.ENTRANCE: TileType.STAIRS_UP,
    spd_terrain.ENTRANCE_SP: TileType.STAIRS_UP,
    spd_terrain.EXIT: TileType.STAIRS_DOWN,
    spd_terrain.EMBERS: TileType.FLOOR,
    spd_terrain.LOCKED_DOOR: TileType.LOCKED_DOOR,
    spd_terrain.HERO_LKD_DR: TileType.LOCKED_DOOR,
    spd_terrain.CRYSTAL_DOOR: TileType.LOCKED_DOOR,
    spd_terrain.PEDESTAL: TileType.FLOOR,
    spd_terrain.WALL_DECO: TileType.WALL_DECO,
    spd_terrain.BARRICADE: TileType.WALL,
    spd_terrain.EMPTY_SP: TileType.FLOOR,
    spd_terrain.HIGH_GRASS: TileType.HIGH_GRASS,
    spd_terrain.FURROWED_GRASS: TileType.FURROWED_GRASS,
    spd_terrain.SECRET_DOOR: TileType.SECRET_DOOR,
    spd_terrain.SECRET_TRAP: TileType.SECRET_TRAP,
    spd_terrain.TRAP: TileType.TRAP,
    spd_terrain.INACTIVE_TRAP: TileType.INACTIVE_TRAP,
    spd_terrain.EMPTY_DECO: TileType.EMPTY_DECO,
    spd_terrain.LOCKED_EXIT: TileType.LOCKED_DOOR,
    spd_terrain.UNLOCKED_EXIT: TileType.FLOOR,
    spd_terrain.WELL: TileType.FLOOR,
    spd_terrain.BOOKSHELF: TileType.WALL,
    spd_terrain.ALCHEMY: TileType.FLOOR,
    spd_terrain.CUSTOM_DECO: TileType.WALL_DECO,
    spd_terrain.CUSTOM_DECO_EMPTY: TileType.EMPTY_DECO,
    spd_terrain.STATUE: TileType.WALL,
    spd_terrain.STATUE_SP: TileType.WALL,
    spd_terrain.REGION_DECO: TileType.WALL_DECO,
    spd_terrain.REGION_DECO_ALT: TileType.WALL_DECO,
    spd_terrain.MINE_CRYSTAL: TileType.WALL,
    spd_terrain.MINE_BOULDER: TileType.WALL,
    spd_terrain.WATER: TileType.FLOOR_WATER,
}

# GenMob class-name string -> MobEntity subclass
_MOB_CLASSES: Dict[str, type[MobEntity]] = {
    "Rat": Rat,
    "Snake": Snake,
    "Gnoll": Gnoll,
    "Swarm": Swarm,
    "Crab": Crab,
    "Slime": Slime,
    "Albino": AlbinoRat,
    "GnollExile": GnollExile,
    "HermitCrab": HermitCrab,
    "CausticSlime": CausticSlime,
    "Goo": Goo,
    "Skeleton": Skeleton,
    "Thief": Thief,
    "DM100": DM100,
    "Guard": Guard,
    "Necromancer": Necromancer,
    "Bandit": Bandit,
    "SpectralNecromancer": SpectralNecromancer,
    "Bat": Bat,
    "Brute": Brute,
    "ArmoredBrute": ArmoredBrute,
    "Shaman": RedShaman,  # Java simple class name maps to RedShaman by convention
    "RedShaman": RedShaman,
    "BlueShaman": BlueShaman,
    "PurpleShaman": PurpleShaman,
    "Spinner": Spinner,
    "DM200": DM200,
    "DM201": DM201,
    "Ghoul": Ghoul,
    "FireElemental": FireElemental,
    "FrostElemental": FrostElemental,
    "ShockElemental": ShockElemental,
    "ChaosElemental": ChaosElemental,
    "Elemental": FireElemental,
    "Warlock": Warlock,
    "Monk": Monk,
    "Senior": Senior,
    "Golem": Golem,
    "Succubus": Succubus,
    "Eye": Eye,
    "Scorpio": Scorpio,
    "Acidic": AcidicScorpio,
    "AcidicScorpio": AcidicScorpio,
    "RipperDemon": RipperDemon,
    "Tengu": Tengu,
    "DM300": DM300,
    # Universal/Environmental
    "Wraith": Wraith,
    "TormentedSpirit": TormentedSpirit,
    "Piranha": Piranha,
    "PhantomPiranha": PhantomPiranha,
    "Mimic": Mimic,
    "GoldenMimic": GoldenMimic,
    "EbonyMimic": EbonyMimic,
    "Statue": Statue,
    "ArmoredStatue": ArmoredStatue,
    "Bee": Bee,
    # DwarfKing + minions
    "DwarfKing": DwarfKing,
    "DKGhoul": DKGhoul,
    "DKMonk": DKMonk,
    "DKWarlock": DKWarlock,
    "DKGolem": DKGolem,
    # YogDzewa + fists + summons
    "YogDzewa": YogDzewa,
    "BurningFist": BurningFist,
    "SoiledFist": SoiledFist,
    "RottingFist": RottingFist,
    "RustedFist": RustedFist,
    "BrightFist": BrightFist,
    "DarkFist": DarkFist,
    "YogEye": YogEye,
    "YogScorpio": YogScorpio,
    "YogRipper": YogRipper,
    # Static spawners
    "DemonSpawner": DemonSpawner,
    "Pylon": Pylon,
    "RatKing": RatKing,
}

# Trap class (SPD) -> remake TrapType
_SPD_TRAP_TYPE: Dict[type[SpdTrap], str] = {}


def _register_trap(spd_cls: type[SpdTrap], trap_type: str) -> None:
    _SPD_TRAP_TYPE[spd_cls] = trap_type


_register_trap(type("WornDartTrap", (SpdTrap,), {}), TrapType.WORN_DART)


_SPD_TRAP_COLOR = TrapVisual.GREY
_SPD_TRAP_SHAPE = TrapVisual.CROSSHAIR


def _convert_tile(val: int) -> int:
    return _SPD_TO_TILE.get(val, TileType.FLOOR)


def _convert_room(spd_room) -> LegacyRoom:
    w = spd_room.right - spd_room.left + 1
    h = spd_room.bottom - spd_room.top + 1
    kind = RoomKind.STANDARD
    from app.engine.dungeon.spd_levelgen.room_types import SpecialRoom
    if isinstance(spd_room, SpecialRoom):
        kind = RoomKind.SPECIAL
    return LegacyRoom(
        x=spd_room.left,
        y=spd_room.top,
        width=w,
        height=h,
        kind=kind,
        room_id=id(spd_room) & 0xFFFF,
    )


def _spawn_mob(gen_mob: GenMob, width: int) -> MobEntity:
    cls = _MOB_CLASSES.get(gen_mob.cls_name)
    if cls is None:
        cls = Rat
    pos = gen_mob.pos
    x = pos % width
    y = pos // width
    mob = cls(id=str(uuid.uuid4()), pos=Position(x=x, y=y), faction=Faction.DUNGEON)
    # Set floor_level for depth-scaled mobs
    if hasattr(mob, 'floor_level'):
        mob.floor_level = gen_mob.depth
    return mob


def _spawn_item(heap_items: list, cell_x: int, cell_y: int) -> Item:
    for item in heap_items:
        if isinstance(item, RolledItem):
            return _rolled_item_to_item(item, cell_x, cell_y)
        if isinstance(item, frozenset):
            return _descriptor_to_item(item, cell_x, cell_y)
    return Gold(id=str(uuid.uuid4()), pos=Position(x=cell_x, y=cell_y))


def _rolled_item_to_item(ri: RolledItem, cx: int, cy: int) -> Item:
    iid = str(uuid.uuid4())
    pos = Position(x=cx, y=cy)
    if ri.category == "GOLD":
        return Gold(id=iid, pos=pos, name="Gold")
    if ri.category == "POTION":
        return HealthPotion(id=iid, pos=pos)
    if ri.category == "SCROLL":
        return Scroll(id=iid, pos=pos, name="Scroll")
    if ri.category == "FOOD":
        return Food(id=iid, pos=pos, name="Food")
    if ri.category == "SEED":
        return Seed(id=iid, pos=pos, name="Seed")
    if ri.category == "STONE":
        return Stone(id=iid, pos=pos, damage=1, range=5)
    if ri.category in ("WAND",):
        return Wand(id=iid, pos=pos, name="Wand")
    if ri.category in ("WEAPON", "WEP_T1", "WEP_T2", "WEP_T3", "WEP_T4", "WEP_T5"):
        return Weapon(id=iid, pos=pos, name="Weapon", damage=2 + ri.level, range=1,
                      strength_requirement=10, attack_cooldown=2.0)
    if ri.category == "ARMOR":
        return Armor(id=iid, pos=pos, name="Armor", tier=1 + ri.level,
                     strength_requirement=10)
    if ri.category in ("MISSILE", "MIS_T1", "MIS_T2", "MIS_T3", "MIS_T4", "MIS_T5"):
        return Stone(id=iid, pos=pos, name="Missile", damage=1 + ri.level, range=5)
    if ri.category == "RING":
        from app.engine.entities.base import Ring
        return Ring(id=iid, pos=pos, name="Ring")
    if ri.category == "ARTIFACT":
        from app.engine.entities.base import Artifact
        return Artifact(id=iid, pos=pos, name="Artifact")
    return Gold(id=iid, pos=pos, name="Gold")


_DESCRIPTOR_ITEM_MAP = {
    "PotionOfStrength": lambda iid, pos: HealthPotion(id=iid, pos=pos),
    "Scroll": lambda iid, pos: Scroll(id=iid, pos=pos, name="Scroll"),
    "Runestone": lambda iid, pos: Stone(id=iid, pos=pos, name="Runestone", damage=1, range=5),
    "TrinketCatalyst": lambda iid, pos: Dewdrop(id=iid, pos=pos, name="Trinket Catalyst"),
    "IronKey": lambda iid, pos: Key(id=iid, pos=pos, name="Iron Key", key_id="iron"),
    "GoldenKey": lambda iid, pos: Key(id=iid, pos=pos, name="Golden Key", key_id="golden"),
    "CrystalKey": lambda iid, pos: Key(id=iid, pos=pos, name="Crystal Key", key_id="crystal"),
    "GuidePage": lambda iid, pos: Scroll(id=iid, pos=pos, name="Guide Page"),
    "DocumentPage": lambda iid, pos: Scroll(id=iid, pos=pos, name="Document Page"),
    "Food": lambda iid, pos: Food(id=iid, pos=pos, name="Food"),
    "EnergyCrystal": lambda iid, pos: Stone(id=iid, pos=pos, name="Energy Crystal", damage=1, range=3),
    "Potion": lambda iid, pos: HealthPotion(id=iid, pos=pos),
    "Bomb": lambda iid, pos: Stone(id=iid, pos=pos, name="Bomb", damage=5, range=1),
    "Gold": lambda iid, pos: Gold(id=iid, pos=pos, name="Gold"),
    "Weapon": lambda iid, pos: Weapon(id=iid, pos=pos, name="Weapon", damage=2, range=1, strength_requirement=10, attack_cooldown=2.0),
    "Armor": lambda iid, pos: Armor(id=iid, pos=pos, name="Armor", tier=1, strength_requirement=10),
}


def _descriptor_to_item(descriptor: frozenset, cx: int, cy: int) -> Item:
    iid = str(uuid.uuid4())
    pos = Position(x=cx, y=cy)
    for key, factory in _DESCRIPTOR_ITEM_MAP.items():
        if key in descriptor:
            return factory(iid, pos)
    return HealthPotion(id=iid, pos=pos)


def _convert_traps(gen_level: GenLevel, w: int) -> Dict[Tuple[int, int], TrapInfo]:
    traps: Dict[Tuple[int, int], TrapInfo] = {}
    for cell, spd_trap in gen_level.traps.items():
        x = cell % w
        y = cell // w
        trap_type_name = type(spd_trap).__name__
        trap_type = _SPD_TRAP_TYPE.get(type(spd_trap), TrapType.WORN_DART)
        traps[(x, y)] = TrapInfo(
            x=x, y=y, trap_type=trap_type,
            hidden=not spd_trap.visible,
            active=True,
        )
    return traps


def _extract_doors(gen_level: GenLevel, width: int, height: int) -> Tuple[Dict[Tuple[int, int], int], Dict[Tuple[int, int], str]]:
    hidden_doors: Dict[Tuple[int, int], int] = {}
    locked_doors: Dict[Tuple[int, int], str] = {}
    for cell in range(len(gen_level.map)):
        spd_val = gen_level.map[cell]
        x = cell % width
        y = cell // width
        if spd_val == spd_terrain.SECRET_DOOR:
            hidden_doors[(x, y)] = TileType.DOOR
        elif spd_val in (spd_terrain.LOCKED_DOOR, spd_terrain.HERO_LKD_DR):
            locked_doors[(x, y)] = "iron"
        elif spd_val == spd_terrain.CRYSTAL_DOOR:
            locked_doors[(x, y)] = "crystal"
        elif spd_val == spd_terrain.LOCKED_EXIT:
            locked_doors[(x, y)] = "goo_door"
    return hidden_doors, locked_doors


def gen_level_to_floor_state(gen_level: GenLevel, depth: int) -> FloorState:
    w = gen_level.width()
    h = gen_level.height()
    grid: List[List[int]] = []
    for y in range(h):
        row: List[int] = []
        for x in range(w):
            cell = x + y * w
            spd_val = gen_level.map[cell]
            row.append(_convert_tile(spd_val))
        grid.append(row)

    rooms = [_convert_room(r) for r in gen_level.rooms if hasattr(r, 'left')]

    mobs: Dict[str, MobEntity] = {}
    for gen_mob in gen_level.mobs:
        if isinstance(gen_mob, GenMob):
            mob = _spawn_mob(gen_mob, w)
            mobs[mob.id] = mob

    items: Dict[str, Item] = {}
    for cell, heap in gen_level.heaps.items():
        x = cell % w
        y = cell // w
        item = _spawn_item(heap.items, x, y)
        items[item.id] = item

    # Extract items from mimics (not yet implemented as entities) so keys
    # they carry are not permanently lost.
    for gen_mob in gen_level.mobs:
        if isinstance(gen_mob, GenMob) and gen_mob.cls_name in ("Mimic", "GoldenMimic") and gen_mob.items:
            pos = gen_mob.pos
            x = pos % w
            y = pos // w
            item = _spawn_item(gen_mob.items, x, y)
            items[item.id] = item

    traps = _convert_traps(gen_level, w)
    hidden_doors, locked_doors = _extract_doors(gen_level, w, h)

    key_spawns: Dict[str, Tuple[int, int]] = {}

    alchemy_pots: List[Tuple[int, int]] = []
    for cell, spd_val in enumerate(gen_level.map):
        if spd_val == spd_terrain.ALCHEMY:
            alchemy_pots.append((cell % w, cell // w))

    region = "sewers" if depth <= 5 else "prison" if depth <= 10 else "caves" if depth <= 15 else "city" if depth <= 20 else "halls"

    floor = FloorState(
        floor_id=depth,
        grid=grid,
        rooms=rooms,
        mobs=mobs,
        items=items,
        region=region,
        hidden_doors=hidden_doors,
        locked_doors=locked_doors,
        traps=traps,
        key_spawns=key_spawns,
        generation_meta={
            "seed": str(getattr(gen_level, '_seed', '')),
            "spd_generated": True,
        },
        dk_summon_spots=list(getattr(gen_level, 'dk_summon_spots', [])),
        yog_pos=getattr(gen_level, 'yog_pos', None),
        custom_tiles=list(getattr(gen_level, 'custom_tiles', [])),
        alchemy_pots=alchemy_pots,
    )
    floor.rebuild_flags()
    return floor
