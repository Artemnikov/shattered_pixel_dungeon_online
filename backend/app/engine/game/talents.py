from typing import Dict, List, Optional

from app.engine.entities.base import Player
from app.engine.entities.buffs import add_buff, get_buff, remove_buff
from app.engine.entities.subclasses import (
    Subclass,
    Talent,
    TALENT_DEFS,
    TALENT_CLASS_REQ,
    TIER_UNLOCK_LEVELS,
    TIER_MAX_POINTS,
    ArmorAbilityType,
    ABILITY_TALENTS,
    CLASS_SUBCLASSES,
    COMBO_MOVES,
)


class TalentsMixin:

    TIER_GRANT: Dict[int, int] = {1: 2, 2: 2, 3: 3, 4: 4}

    def init_class_talents(self, player: Player) -> None:
        if 1 not in player.subclass_info.talent_points:
            player.subclass_info.talent_points[1] = self.TIER_GRANT[1]

    def init_subclass_talents(self, player: Player) -> None:
        if 2 not in player.subclass_info.talent_points:
            player.subclass_info.talent_points[2] = self.TIER_GRANT[2]

    def init_armor_talents(self, player: Player) -> None:
        if 3 not in player.subclass_info.talent_points:
            player.subclass_info.talent_points[3] = self.TIER_GRANT[3]

    def init_tier4_talents(self, player: Player) -> None:
        if 4 not in player.subclass_info.talent_points:
            player.subclass_info.talent_points[4] = self.TIER_GRANT[4]

    MILESTONE_LEVELS: List[int] = [2, 6, 7, 13, 21]

    def on_talent_level_up(self, player: Player) -> None:
        self.init_talents_for_level(player)
        emitted = player.subclass_info.emitted_milestones

        tier_unlocked = None
        can_choose_armor = False

        for mlvl in self.MILESTONE_LEVELS:
            if player.level < mlvl or mlvl in emitted:
                continue
            emitted.add(mlvl)

            if mlvl == 2:
                tier_unlocked = 1

            elif mlvl == 6 and player.subclass_info.subclass is None:
                options = list(CLASS_SUBCLASSES.get(player.class_type, ()))
                self.add_event("SUBCLASS_CHOICE_AVAILABLE", {
                    "player": player.id, "options": options,
                }, floor_id=player.floor_id, source_player_id=player.id)

            elif mlvl == 7:
                tier_unlocked = 2

            elif mlvl == 13 and not player.armor_ability:
                tier_unlocked = 3
                can_choose_armor = True
                options = [t for t in ABILITY_TALENTS
                           if TALENT_CLASS_REQ.get(t) == player.class_type]
                self.add_event("ARMOR_ABILITY_CHOICE_AVAILABLE", {
                    "player": player.id, "options": options,
                }, floor_id=player.floor_id, source_player_id=player.id)

            elif mlvl == 21:
                tier_unlocked = 4

        self.add_event("LEVEL_UP", {
            "player": player.id, "level": player.level,
            "tier_unlocked": tier_unlocked,
            "talent_points": dict(player.subclass_info.talent_points),
            "can_choose_armor_ability": can_choose_armor,
            "can_choose_subclass": player.level >= 6 and player.subclass_info.subclass is None,
        }, floor_id=player.floor_id, source_player_id=player.id)
    def choose_subclass(self, player_id: str, subclass: str) -> bool:
        player = self.players.get(player_id)
        if not player:
            return False
        if player.level < 6:
            return False
        if player.subclass_info.subclass is not None:
            return False
        if subclass not in CLASS_SUBCLASSES.get(player.class_type, ()):
            return False
        player.subclass_info.subclass = subclass
        if subclass == Subclass.BERSERKER:
            add_buff(player.buffs, "berserk_ready", duration=0, level=1)
        elif subclass == Subclass.GLADIATOR:
            player.combo_count = 0
            player.combo_timer = 0.0
            player.combo_max = 10
        self.add_event("SUBCLASS_CHOSEN", {"player": player.id, "subclass": subclass}, floor_id=player.floor_id, source_player_id=player.id)
        return True

    def init_talents_for_level(self, player: Player) -> None:
        for tier_level in sorted(self.TIER_GRANT.keys()):
            unlock_lvl = TIER_UNLOCK_LEVELS.get(tier_level, 99)
            if player.level >= unlock_lvl and tier_level not in player.subclass_info.talent_points:
                player.subclass_info.talent_points[tier_level] = self.TIER_GRANT[tier_level]

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

        # Class check (talents not in the map are class-agnostic)
        class_req = TALENT_CLASS_REQ.get(talent_name)
        if class_req is not None and player.class_type != class_req:
            return False

        # Subclass check
        if subclass_req is not None and info.subclass != subclass_req:
            return False

        # Already maxed
        current = info.talent_info.get(talent_name)
        if current >= max_pts:
            return False

        # Lazy-grant talent points for tiers the player's level has unlocked
        self.init_talents_for_level(player)

        # Available talent points check
        avail = info.talent_points.get(tier, 0)
        if avail <= 0:
            return False

        info.talent_info.talents[talent_name] = current + 1
        info.talent_points[tier] = avail - 1

        # Armor ability selection (first point in any selector locks the choice)
        if talent_name in ABILITY_TALENTS:
            player.armor_ability = ABILITY_TALENTS[talent_name]

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
        dur = 10.0
        bd = player.subclass_info.talent_info.level("berserk_duration")
        if bd > 0:
            dur += 5.0 * bd
        add_buff(player.buffs, "berserk", duration=dur, level=1)
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

    # ------------------------------------------------------------------
    # Talent effect callbacks — called from item_actions, combat, tick
    # ------------------------------------------------------------------

    def on_food_eaten(self, player: Player, food_item) -> None:
        ti = player.subclass_info.talent_info

        # Iron Stomach (warrior T1): heal when HP < 1/3, +2 HP per point
        iron_stomach = ti.level(Talent.IRON_STOMACH)
        if iron_stomach > 0 and player.hp / max(player.get_total_max_hp(), 1) < 0.334:
            healing = 2 + 2 * iron_stomach
            player.hp = min(player.get_total_max_hp(), player.hp + healing)

        # Cached Rations (rogue T1): heal +2 per point on eat
        cached = ti.level(Talent.CACHED_RATIONS)
        if cached > 0:
            player.set_heal(float(4 + 4 * cached), 0.25, 0)

        # Empowering Meal (mage T1): gain wand charge per point
        empowering = ti.level(Talent.EMPOWERING_MEAL)
        if empowering > 0:
            from app.engine.entities.base import Wand
            for w in player.belongings.all_items():
                if isinstance(w, Wand) and w.charges < w.max_charges:
                    w.charges = min(w.max_charges, w.charges + empowering)

        # Mystical Meal (rogue T2): cloak charge on eat
        mystical = ti.level(Talent.MYSTICAL_MEAL)
        if mystical > 0:
            cloak = player.belongings.artifact
            if cloak is not None and getattr(cloak, "kind", "") == "cloak_of_shadows":
                cloak.charge = min(cloak.charge_cap, cloak.charge + mystical)

        # Energizing Meal (mage T2): recharge wand charges on eat
        energizing = ti.level(Talent.ENERGIZING_MEAL)
        if energizing > 0:
            from app.engine.entities.base import Wand as WandCls
            for item in player.belongings.all_items():
                if isinstance(item, WandCls) and item.max_charges > 0:
                    item.charges = min(item.max_charges, item.charges + energizing)

        # Invigorating Meal (huntress T2): speed boost on eat
        invigorating = ti.level(Talent.INVIGORATING_MEAL)
        if invigorating > 0:
            add_buff(player.buffs, "haste", duration=5.0 + 5.0 * invigorating, level=1)

    def on_potion_drunk(self, player: Player, potion_item) -> None:
        ti = player.subclass_info.talent_info

        # Backup Barrier (mage T1): shield on potion use
        barrier = ti.level(Talent.BACKUP_BARRIER)
        if barrier > 0:
            player.add_shield("backup_barrier", 3 + 3 * barrier, priority=1, decay=600)

        # Lingering Magic (mage T1): prolong buff durations
        lingering = ti.level(Talent.LINGERING_MAGIC)
        if lingering > 0:
            from app.engine.entities.buffs import Buff
            for b in player.buffs:
                if b.type in ("haste", "healing", "shield"):
                    b.duration *= 1.0 + 0.15 * lingering

        # Inscribed Power (mage T2): gain wand charges on potion
        inscribed = ti.level(Talent.INSCRIBED_POWER)
        if inscribed > 0:
            from app.engine.entities.base import Wand as WandCls
            for item in player.belongings.all_items():
                if isinstance(item, WandCls) and item.max_charges > 0:
                    item.charges = min(item.max_charges, item.charges + inscribed)

    def on_kill(self, player: Player, target, floor_mobs: dict, floor_id: int) -> None:
        ti = player.subclass_info.talent_info

        # Rampage (warrior T4 berserker): gain damage stacks on kill
        rampage = ti.level(Talent.RAMPAGE)
        if rampage > 0:
            stacks = getattr(player, "rampage_stacks", 0)
            player.rampage_stacks = min(stacks + 1, 5 * rampage)
            self.add_event("RAMPAGE", {"player": player.id, "stacks": player.rampage_stacks}, floor_id=floor_id, source_player_id=player.id)

        # Combo Aura (warrior T4 gladiator): AOE burst on kill at high combo
        combo_aura = ti.level(Talent.COMBO_AURA)
        if combo_aura > 0 and player.combo_count >= 6:
            for mob in list(floor_mobs.values()):
                if not mob.is_alive or mob.faction == "player":
                    continue
                if max(abs(mob.pos.x - target.pos.x), abs(mob.pos.y - target.pos.y)) <= 1:
                    dmg = combo_aura * player.combo_count
                    mob.hp -= dmg
                    self.add_event("DAMAGE", {"target": mob.id, "amount": dmg}, floor_id=floor_id)
                    if not mob.is_alive:
                        self.add_event("DEATH", {"target": mob.id}, floor_id=floor_id)

        # Soul Eater (mage T3 warlock): heal on kill
        soul_eater = ti.level(Talent.SOUL_EATER)
        if soul_eater > 0:
            healing = 2 + 2 * soul_eater
            player.hp = min(player.get_total_max_hp(), player.hp + healing)
            self.add_event("HEAL", {"target": player.id, "amount": healing, "x": player.pos.x, "y": player.pos.y}, floor_id=floor_id)
