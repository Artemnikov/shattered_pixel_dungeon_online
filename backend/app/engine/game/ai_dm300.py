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

import time

from app.engine.entities.mobs import DM300
from app.engine.game.floor_state import FloorState


class DM300AIMixin:
    def _update_dm300_chase(self, mob: DM300, floor: FloorState, floor_id: int):
        target_player = self._find_nearest_player(mob.pos, floor_id)
        if target_player is None:
            return

        dist = self._get_distance(mob.pos, target_player.pos)
        atk_range = getattr(mob, "attack_range", 1)

        if dist <= atk_range:
            current_time = time.time()
            if current_time - mob.last_attack_time >= mob.attack_cooldown:
                dx, dy = target_player.pos.x - mob.pos.x, target_player.pos.y - mob.pos.y
                self.move_entity(mob.id, dx, dy)
        elif self._is_in_los(mob.pos, target_player.pos, floor_id=floor_id):
            step = self._get_next_step_to(mob.pos, target_player.pos, floor_id=floor_id)
            if step:
                self.move_entity(mob.id, step[0], step[1])
