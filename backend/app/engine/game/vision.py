# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 ArtemNikov
#
# Adapted from Shattered Pixel Dungeon (C) 2014-2024 Evan Debenham
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
"""Vision / line-of-sight / pathfinding for GameInstance.

Shadowcasting-based FOV (mirrors Shattered Pixel Dungeon), per-tick caches, and
BFS pathfinding used by mob AI and tap-to-travel.
"""

from typing import List, Optional, Tuple

from app.engine.dungeon.generator import TileType
from app.engine.entities.base import Position
from app.engine.mechanics import shadowcaster

from app.engine.game.floor_state import FloorState


class VisionMixin:
    def _find_nearest_player(self, pos: Position, floor_id: int):
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

    def _get_open_doors(self, floor: FloorState):
        return [
            [x, y]
            for y in range(floor.height)
            for x in range(floor.width)
            if floor.grid[y][x] == TileType.OPEN_DOOR
        ]

    def _invalidate_fov_cache(self):
        """Drop cached shadowcasting results. Call whenever positions, doors, or
        terrain change (every tick and on movement)."""
        self._fov_cache.clear()
        self._blocking_cache.clear()

    def _view_distance(self, entity) -> int:
        """Resolve an entity's effective vision radius. Single hook point for
        future Light/Blindness/Farsight buffs (mirrors SPD
        Level.updateFieldOfView's viewDist scaling). Clamped to the
        shadowcaster's supported range; missing field defaults to SPD's 8."""
        dist = getattr(entity, "view_distance", 8)
        # Farsight talent: check for dynamic override
        get_view = getattr(entity, "get_view_distance", None)
        if get_view:
            dist = get_view()
        return max(0, min(dist, shadowcaster.MAX_DISTANCE))

    def _effective_blocking(self, floor: "FloorState", viewer_id: Optional[str] = None) -> List[bool]:
        """Flat (y*w+x) LOS-blocking map with open doors cleared and Warden
        exception for high grass.

        SPD bakes door open-state into losBlocking; here DOOR tiles are always
        LOS-blocking and OPEN_DOOR tiles (22) are not, so we just read the flag
        map directly without any occupancy-based override.

        If `viewer_id` is a Warden, HIGH_GRASS and FURROWED_GRASS cells do not
        block LOS."""
        cache_key = (floor.floor_id, viewer_id or "")
        cached = self._blocking_cache.get(cache_key)
        if cached is not None:
            return cached

        w, h = floor.width, floor.height
        los = floor.flags.los_blocking if floor.flags else None
        blocking = [False] * (w * h)

        # Check if viewer is a Warden (sees through high grass)
        is_warden = False
        if viewer_id:
            viewer = self.players.get(viewer_id)
            if viewer:
                subclass_info = getattr(viewer, "subclass_info", None)
                if subclass_info and subclass_info.subclass == "warden":
                    is_warden = True

        for y in range(h):
            row = los[y] if los else None
            grid_row = floor.grid[y]
            base = y * w
            for x in range(w):
                block = row[x] if row else True
                # Warden sees through high/furrowed grass
                if block and is_warden and grid_row[x] in (TileType.HIGH_GRASS, TileType.FURROWED_GRASS):
                    block = False
                blocking[base + x] = block

        self._blocking_cache[cache_key] = blocking
        return blocking

    def _fov_from(self, src: Position, floor: "FloorState", distance: int, viewer_id: Optional[str] = None) -> List[bool]:
        """Shadowcast FOV (flat bool list) from `src` on `floor`, cached per tick."""
        cache_key = (floor.floor_id, src.x, src.y, distance, viewer_id or "")
        cached = self._fov_cache.get(cache_key)
        if cached is not None:
            return cached

        blocking = self._effective_blocking(floor, viewer_id=viewer_id)
        fov = shadowcaster.compute_fov(blocking, floor.width, floor.height, src.x, src.y, distance)
        self._fov_cache[cache_key] = fov
        return fov

    def _is_in_los(self, p1: Position, p2: Position, floor_id: Optional[int] = None,
                   distance: Optional[int] = None, viewer_id: Optional[str] = None) -> bool:
        """True iff p2 lies within p1's shadowcast field of view.

        Unified LOS: vision, mob sight, event audibility, and ranged targeting
        all go through the same recursive shadowcasting as SPD, so none of them
        leak through wall corners."""
        floor = self._get_or_create_floor(floor_id or self.depth)

        if not (0 <= p1.x < floor.width and 0 <= p1.y < floor.height):
            return False
        if not (0 <= p2.x < floor.width and 0 <= p2.y < floor.height):
            return False

        if distance is None:
            distance = shadowcaster.MAX_DISTANCE

        fov = self._fov_from(p1, floor, distance, viewer_id=viewer_id)
        return fov[p2.y * floor.width + p2.x]

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

            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (1, -1), (-1, 1), (-1, -1)]:
                nx, ny = x + dx, y + dy
                if (
                    0 <= nx < floor.width
                    and 0 <= ny < floor.height
                    and floor.flags
                    and floor.flags.passable[ny][nx]
                    and (nx, ny) not in visited
                ):
                    if dx != 0 and dy != 0:
                        if not floor.flags.passable[y][x + dx] or not floor.flags.passable[y + dy][x]:
                            continue

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
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (1, -1), (-1, 1), (-1, -1)]:
                nx, ny = x + dx, y + dy
                if (
                    0 <= nx < floor.width
                    and 0 <= ny < floor.height
                    and floor.flags
                    and floor.flags.passable[ny][nx]
                    and (nx, ny) not in visited
                ):
                    # Diagonal corner-cut allowed (SPD-faithful): no orthogonal check.
                    visited.add((nx, ny))
                    queue.append((nx, ny, path + [(dx, dy)]))
            if len(visited) > 500:
                break
        return []

    def get_visible_tiles(self, pos: Position, radius: int = 8, floor_id: Optional[int] = None, viewer_id: Optional[str] = None) -> List[Tuple[int, int]]:
        """Tiles visible from `pos` within `radius`, via recursive shadowcasting
        (matches SPD). The circular cutoff comes from the shadowcaster's ROUNDING
        table, not a separate dist_sq test."""
        floor = self._get_or_create_floor(floor_id or self.depth)

        distance = max(0, min(radius, shadowcaster.MAX_DISTANCE))
        fov = self._fov_from(pos, floor, distance, viewer_id=viewer_id)

        w, h = floor.width, floor.height
        visible = []
        for y in range(h):
            base = y * w
            for x in range(w):
                if fov[base + x]:
                    visible.append((x, y))
        return visible
