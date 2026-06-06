import math
import random
from typing import Optional

from app.engine.dungeon.generator import TileType
from app.engine.entities.base import Player, Position
from app.engine.entities.buffs import add_buff
from app.engine.entities.subclasses import ArmorAbilityType, COST_ARMOR_ABILITY, COST_ENDURE
from app.engine.systems.combat import resolve_melee_attack


class ArmorAbilitiesMixin:
    def use_armor_ability(self, player_id: str, ability: str, target_x: Optional[int] = None, target_y: Optional[int] = None) -> None:
        player = self.players.get(player_id)
        if not player or player.is_downed or not player.is_alive:
            return

        floor_id = player.floor_id
        floor = self._get_or_create_floor(floor_id)

        if ability == ArmorAbilityType.HEROIC_LEAP:
            if player.armor_charge < COST_ARMOR_ABILITY:
                return
            if target_x is None or target_y is None:
                return
            if not (0 <= target_x < floor.width and 0 <= target_y < floor.height):
                return
            if floor.grid[target_y][target_x] == TileType.WALL:
                return
            dx = target_x - player.pos.x
            dy = target_y - player.pos.y
            dist = max(abs(dx), abs(dy))
            if dist < 1 or dist > 4:
                return
            player.armor_charge -= COST_ARMOR_ABILITY
            player.pos.x = target_x
            player.pos.y = target_y
            self._invalidate_fov_cache()
            self.add_event("MOVE", {"entity": player.id, "x": target_x, "y": target_y}, floor_id=floor_id)
            self.add_event("PLAY_SOUND", {"sound": "HIT_STRONG"}, floor_id=floor_id, source_player_id=player.id)
            for dy_off in (-1, 0, 1):
                for dx_off in (-1, 0, 1):
                    if dx_off == 0 and dy_off == 0:
                        continue
                    cx, cy = target_x + dx_off, target_y + dy_off
                    if not (0 <= cx < floor.width and 0 <= cy < floor.height):
                        continue
                    for mob in list(floor.mobs.values()):
                        if mob.is_alive and mob.pos.x == cx and mob.pos.y == cy:
                            dmg = random.randint(2 + player.level, 6 + player.level * 2)
                            mob.hp -= dmg
                            self.add_event("DAMAGE", {"target": mob.id, "amount": dmg}, floor_id=floor_id)
                            if not mob.is_alive:
                                self.add_event("DEATH", {"target": mob.id}, floor_id=floor_id)

        elif ability == ArmorAbilityType.SHOCKWAVE:
            if player.armor_charge < COST_ARMOR_ABILITY:
                return
            player.armor_charge -= COST_ARMOR_ABILITY
            self.add_event("PLAY_SOUND", {"sound": "HIT_STRONG"}, floor_id=floor_id, source_player_id=player.id)
            for dy_off in (-1, 0, 1):
                for dx_off in (-1, 0, 1):
                    if dx_off == 0 and dy_off == 0:
                        continue
                    cx, cy = player.pos.x + dx_off, player.pos.y + dy_off
                    if not (0 <= cx < floor.width and 0 <= cy < floor.height):
                        continue
                    for mob in list(floor.mobs.values()):
                        if mob.is_alive and mob.pos.x == cx and mob.pos.y == cy:
                            dmg = random.randint(1 + player.level, 4 + player.level * 2)
                            knock_x = cx + (cx - player.pos.x)
                            knock_y = cy + (cy - player.pos.y)
                            if 0 <= knock_x < floor.width and 0 <= knock_y < floor.height and floor.grid[knock_y][knock_x] != TileType.WALL:
                                mob.pos.x = knock_x
                                mob.pos.y = knock_y
                            mob.hp -= dmg
                            self.add_event("DAMAGE", {"target": mob.id, "amount": dmg}, floor_id=floor_id)
                            if not mob.is_alive:
                                self.add_event("DEATH", {"target": mob.id}, floor_id=floor_id)

        elif ability == ArmorAbilityType.ENDURE:
            if player.armor_charge < COST_ENDURE:
                return
            player.armor_charge -= COST_ENDURE
            add_buff(player.buffs, "endure", duration=5.0, level=1)
            self.add_event("PLAY_SOUND", {"sound": "HIT_STRONG"}, floor_id=floor_id, source_player_id=player.id)
