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

    def rebuild_flags(self) -> None:
        self.flags = build_flag_maps(self.grid)

    @property
    def width(self) -> int:
        return len(self.grid[0]) if self.grid else 0

    @property
    def height(self) -> int:
        return len(self.grid) if self.grid else 0
