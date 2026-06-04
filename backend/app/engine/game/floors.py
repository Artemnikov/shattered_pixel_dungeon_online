"""Floor access and lookup helpers for GameInstance.

The legacy single-floor API (``grid``, ``rooms``, ``mobs``, ``items``, ``width``,
``height``) is exposed here as compatibility properties that proxy to the current
depth's FloorState, alongside the multi-floor lookup helpers.
"""

from typing import Dict, List, Optional, Tuple

from app.engine.entities.base import Item, Mob as MobEntity, Player
from app.engine.game.constants import MAP_HEIGHT, MAP_WIDTH, MAX_FLOOR_ID
from app.engine.game.floor_state import FloorState


class FloorAccessMixin:
    @property
    def width(self) -> int:
        """Current-depth floor width. Read-only compatibility view for the
        generator seed, the client snapshot, and single-floor tests — never use
        for per-floor logic (use the floor's own width). Falls back to the seed
        constant before the current floor exists."""
        f = self.floors.get(self.depth)
        return f.width if f else MAP_WIDTH

    @property
    def height(self) -> int:
        f = self.floors.get(self.depth)
        return f.height if f else MAP_HEIGHT

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
