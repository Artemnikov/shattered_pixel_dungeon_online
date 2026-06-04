class TileType:
    VOID = 0
    WALL = 1
    FLOOR = 2
    DOOR = 3
    STAIRS_UP = 4
    STAIRS_DOWN = 5
    FLOOR_WOOD = 6
    FLOOR_WATER = 7
    FLOOR_COBBLE = 8
    FLOOR_GRASS = 9
    LOCKED_DOOR = 10
    SECRET_TRAP = 11
    TRAP = 12
    INACTIVE_TRAP = 13
    WALL_DECO = 17
    EMPTY_DECO = 18
    HIGH_GRASS = 19
    SECRET_DOOR = 20
    FURROWED_GRASS = 21


class RoomKind:
    STANDARD = "standard"
    SPECIAL = "special"
    HIDDEN = "hidden"


class TrapType:
    WORN_DART = "worn_dart"

    # Whether each trap type can be hidden (SECRET_TRAP).
    # False → always placed as visible TRAP terrain.
    # Mirrors original SPD's Trap.canBeHidden.
    CAN_BE_HIDDEN = {
        WORN_DART: False,
    }


class TrapVisual:
    RED = 0
    ORANGE = 1
    YELLOW = 2
    GREEN = 3
    TEAL = 4
    VIOLET = 5
    WHITE = 6
    GREY = 7
    BLACK = 8

    DOTS = 0
    WAVES = 1
    GRILL = 2
    STARS = 3
    DIAMOND = 4
    CROSSHAIR = 5
    LARGE_DOT = 6

    MAPPING = {
        TrapType.WORN_DART: (GREY, CROSSHAIR),
    }

    @staticmethod
    def sprite_index(color: int, shape: int) -> int:
        return color + shape * 16

    @staticmethod
    def disarmed_index(shape: int) -> int:
        return TrapVisual.BLACK + shape * 16
