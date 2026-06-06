from typing import Optional

from app.engine.entities.base import Player
from app.engine.entities.buffs import add_buff, get_buff, remove_buff
from app.engine.entities.subclasses import (
    Subclass,
    Talent,
    TALENT_DEFS,
    TIER_UNLOCK_LEVELS,
    TIER_MAX_POINTS,
    ArmorAbilityType,
    COMBO_MOVES,
)


class TalentsMixin:
    def choose_subclass(self, player_id: str, subclass: str) -> bool:
        player = self.players.get(player_id)
        if not player:
            return False
        if player.level < 6:
            return False
        if player.subclass_info.subclass is not None:
            return False
        if subclass not in (Subclass.BERSERKER, Subclass.GLADIATOR):
            return False
        player.subclass_info.subclass = subclass
        if subclass == Subclass.BERSERKER:
            add_buff(player.buffs, "berserk_ready", duration=0, level=1)
        elif subclass == Subclass.GLADIATOR:
            player.combo_count = 0
            player.combo_timer = 0.0
        self.add_event("SUBCLASS_CHOSEN", {"player": player.id, "subclass": subclass}, floor_id=player.floor_id, source_player_id=player.id)
        return True

    def upgrade_talent(self, player_id: str, talent_name: str) -> bool:
        player = self.players.get(player_id)
        if not player:
            return False
        info = player.subclass_info
        if info is None:
            return False
        tal = TALENT_DEFS.get(talent_name)
        if tal is None:
            return False
        max_pts, tier, subclass_req = tal

        # Level check
        unlock_lvl = TIER_UNLOCK_LEVELS.get(tier, 99)
        if player.level < unlock_lvl:
            return False

        # Subclass check
        if subclass_req is not None and info.subclass != subclass_req:
            return False

        # Already maxed
        current = info.talent_info.get(talent_name)
        if current >= max_pts:
            return False

        # Total points spent in this tier limit
        tier_total = sum(info.talent_info.get(t) for t, tdef in TALENT_DEFS.items() if tdef[1] == tier)
        tier_max_total = TIER_MAX_POINTS.get(tier, 0)
        if tier_total >= tier_max_total:
            return False

        info.talent_info.talents[talent_name] = current + 1

        # Armor ability selection (first point in any of the three locks the choice)
        if talent_name == Talent.HEROIC_LEAP:
            player.armor_ability = ArmorAbilityType.HEROIC_LEAP
        elif talent_name == Talent.SHOCKWAVE:
            player.armor_ability = ArmorAbilityType.SHOCKWAVE
        elif talent_name == Talent.ENDURE_ABILITY:
            player.armor_ability = ArmorAbilityType.ENDURE

        self.add_event("TALENT_UPGRADED", {"player": player.id, "talent": talent_name, "level": current + 1}, floor_id=player.floor_id, source_player_id=player.id)
        return True

    def trigger_berserk(self, player_id: str) -> bool:
        player = self.players.get(player_id)
        if not player:
            return False
        if player.subclass_info.subclass != Subclass.BERSERKER:
            return False
        if player.berserk_active:
            return False
        if player.berserk_cooldown > 0:
            return False

        player.berserk_active = True
        player.berserk_power = max(player.berserk_power, 0.2)
        add_buff(player.buffs, "berserk", duration=10.0, level=1)
        remove_buff(player.buffs, "berserk_ready")
        self.add_event("BERSERK_ACTIVATED", {"player": player.id}, floor_id=player.floor_id, source_player_id=player.id)
        return True

    def update_berserk(self, player: Player) -> None:
        if player.subclass_info.subclass != Subclass.BERSERKER:
            return
        if not player.berserk_active:
            return
        berserk_buff = get_buff(player.buffs, "berserk")
        if berserk_buff is None:
            player.berserk_active = False
            player.berserk_power = 0.0
            player.berserk_cooldown = 200
            return
        hp_ratio = player.hp / max(player.get_total_max_hp(), 1)
        decay = 0.05 * (hp_ratio ** 2)
        player.berserk_power = max(0.0, player.berserk_power - decay)
        if player.berserk_power <= 0:
            player.berserk_active = False
            player.berserk_cooldown = 200

    def update_combo(self, player: Player, dt: float) -> None:
        if player.subclass_info.subclass != Subclass.GLADIATOR:
            return
        if player.combo_count <= 0:
            return
        player.combo_timer -= dt
        if player.combo_timer <= 0:
            player.combo_count = 0
            player.combo_timer = 0.0

    def on_melee_hit(self, player: Player, target) -> None:
        if player.subclass_info.subclass == Subclass.GLADIATOR:
            player.combo_count += 1
            player.combo_timer = 5.0
            self.add_event("COMBO_UPDATE", {"player": player.id, "count": player.combo_count}, floor_id=player.floor_id, source_player_id=player.id)
            if player.combo_count in COMBO_MOVES:
                self.add_event("COMBO_MOVE_UNLOCKED", {"player": player.id, "move": COMBO_MOVES[player.combo_count]}, floor_id=player.floor_id, source_player_id=player.id)

    def add_berserk_power(self, player: Player, damage: int) -> None:
        if player.subclass_info.subclass != Subclass.BERSERKER:
            return
        endless_level = player.subclass_info.talent_info.level(Talent.ENDLESS_RAGE)
        max_power = 1.0 + 0.1667 * endless_level
        power_gain = damage / max(player.get_total_max_hp() * 4, 1)
        player.berserk_power = min(max_power, player.berserk_power + power_gain)
