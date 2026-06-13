"""Per-floor runtime state container.

`FloorState` holds everything that varies between dungeon floors: the tile grid,
rooms, live mobs/items, door/trap metadata and derived terrain flag maps.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from app.engine.dungeon.generator import TrapInfo
from app.engine.dungeon.terrain_flags import FloorFlagMaps, build_flag_maps
from app.engine.entities.base import Item, Mob as MobEntity


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
    flags: Optional[FloorFlagMaps] = None
    respawn_counter: int = 0
    mob_limit: int = 0
    plants: Dict[Tuple[int, int], Any] = field(default_factory=dict)
    blob_areas: Dict[str, Any] = field(default_factory=dict)
    dk_summon_spots: List[Tuple[int, int]] = field(default_factory=list)
    yog_pos: Optional[Tuple[int, int]] = None
    custom_tiles: List[dict] = field(default_factory=list)
    alchemy_pots: List[Tuple[int, int]] = field(default_factory=list)

    # PrisonBossLevel (floor 10, Tengu) state machine -- mirrors
    # PrisonBossLevel.State (START/FIGHT_START/FIGHT_PAUSE/FIGHT_ARENA/WON)
    # and the storedItems list preserved across map rebuilds.
    tengu_state: str = "START"
    map_version: int = 0
    prison_stored_items: List[Item] = field(default_factory=list)

    # Dynamic per-floor view-distance override (mirrors SPD Level.viewDistance).
    # Set by YogDzewa's fight to shrink hero vision per phase; None = use the
    # viewer's own view_distance.
    view_distance: Optional[int] = None

    def rebuild_flags(self) -> None:
        self.flags = build_flag_maps(self.grid)

    def update_open_space(self) -> None:
        """Recompute open_space in-place (lighter than full rebuild_flags).
        Call after door open/close or similar single-cell solid changes."""
        if self.flags is None:
            self.rebuild_flags()
            return
        w, h = self.width, self.height
        solid = self.flags.solid
        CIRCLE8 = (
            (0, -1), (1, -1), (1, 0), (1, 1),
            (0, 1), (-1, 1), (-1, 0), (-1, -1),
        )
        for y in range(h):
            for x in range(w):
                if solid[y][x]:
                    self.flags.open_space[y][x] = False
                    continue
                found = False
                for j in range(1, 8, 2):
                    dcx, dcy = CIRCLE8[j]
                    cx, cy = x + dcx, y + dcy
                    if not (0 <= cx < w and 0 <= cy < h) or solid[cy][cx]:
                        continue
                    dax, day = CIRCLE8[(j + 1) % 8]
                    dbx, dby = CIRCLE8[(j + 2) % 8]
                    ax, ay = x + dax, y + day
                    bx, by = x + dbx, y + dby
                    if not (0 <= ax < w and 0 <= ay < h):
                        continue
                    if not (0 <= bx < w and 0 <= by < h):
                        continue
                    if not solid[ay][ax] and not solid[by][bx]:
                        self.flags.open_space[y][x] = True
                        found = True
                        break
                if not found:
                    self.flags.open_space[y][x] = False

    @property
    def width(self) -> int:
        return len(self.grid[0]) if self.grid else 0

    @property
    def height(self) -> int:
        return len(self.grid) if self.grid else 0
