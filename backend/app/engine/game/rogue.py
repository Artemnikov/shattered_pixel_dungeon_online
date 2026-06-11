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
"""Rogue class mechanics for GameInstance.

Ports SPD's Rogue systems into the real-time engine:

* **Cloak of Shadows** — sustained stealth that drains charge over real seconds
  (SPD spends 1 charge / 4 turns). Toggling it on makes the hero invisible;
  attacking, running out of charge, or toggling off ends it.
* **Preparation** (Assassin) — while invisible the Assassin accrues seconds of
  preparation, climbing four tiers that grant a surprise-attack damage bonus, an
  instant-KO threshold on low-HP foes, and a blink range toward a target.
* **Momentum** (Freerunner) — stacks build per move and decay while standing
  still; the engine grants a passive speed/evasion edge proportional to stacks.

Turn counts from SPD are reinterpreted as real seconds, per the remake's
real-time design.
"""

from typing import Optional

from app.engine.entities.base import Player, Position
from app.engine.entities.buffs import add_buff


# --- Cloak of Shadows ------------------------------------------------------
# Real seconds of stealth per charge consumed, and seconds to regenerate one
# charge while not stealthed (SPD: ~1 charge/4 turns drain, ~45-turn recharge).
CLOAK_DRAIN_INTERVAL = 3.0
CLOAK_RECHARGE_INTERVAL = 6.0
CLOAK_EXP_PER_DRAIN = 10  # cloak self-levels as it spends charge


# --- Preparation (Assassin) ------------------------------------------------
# Per tier: (seconds_required, damage_bonus, damage_rolls_keep_highest).
PREP_TIERS = [
    (1.0, 0.10, 1),
    (3.0, 0.20, 1),
    (5.0, 0.35, 2),
    (9.0, 0.50, 3),
]
# KO HP%-threshold[prep_tier][enhanced_lethality 0..3]
PREP_KO_THRESHOLDS = [
    [0.03, 0.04, 0.05, 0.06],
    [0.10, 0.13, 0.17, 0.20],
    [0.20, 0.27, 0.33, 0.40],
    [0.50, 0.67, 0.83, 1.00],
]
# Blink range[prep_tier][assassins_reach 0..3]
PREP_BLINK_RANGES = [
    [1, 1, 2, 2],
    [2, 3, 4, 5],
    [3, 4, 6, 7],
    [4, 6, 8, 10],
]


def prep_tier(seconds: float) -> int:
    """0-based Preparation tier for the given seconds invisible (-1 if none)."""
    tier = -1
    for i, (req, _b, _r) in enumerate(PREP_TIERS):
        if seconds >= req:
            tier = i
    return tier


def prep_damage_bonus(seconds: float) -> float:
    t = prep_tier(seconds)
    return PREP_TIERS[t][1] if t >= 0 else 0.0


def prep_damage_rolls(seconds: float) -> int:
    t = prep_tier(seconds)
    return PREP_TIERS[t][2] if t >= 0 else 1


def prep_ko_threshold(seconds: float, enhanced_lethality: int) -> float:
    t = prep_tier(seconds)
    if t < 0:
        return 0.0
    el = max(0, min(3, enhanced_lethality))
    return PREP_KO_THRESHOLDS[t][el]


def prep_blink_range(seconds: float, assassins_reach: int) -> int:
    t = prep_tier(seconds)
    if t < 0:
        return 0
    ar = max(0, min(3, assassins_reach))
    return PREP_BLINK_RANGES[t][ar]


# --- Momentum (Freerunner) -------------------------------------------------
MOMENTUM_MAX = 10
MOMENTUM_DECAY_INTERVAL = 1.0  # seconds to lose a stack while standing still


class RogueMixin:
    # --- Cloak of Shadows --------------------------------------------------
    def toggle_cloak_stealth(self, player_id: str) -> bool:
        player = self.players.get(player_id)
        if not player or not player.is_alive or player.is_downed:
            return False
        cloak = player.belongings.artifact
        if cloak is None or getattr(cloak, "kind", "") != "cloak_of_shadows":
            return False

        if player.cloak_stealth_active:
            self._end_cloak_stealth(player)
            return True

        light_cloak = player.talent_info.has("light_cloak")
        if not (player.belongings.is_equipped(cloak.id) or light_cloak):
            return False
        if cloak.cursed or cloak.charge <= 0:
            return False

        player.cloak_stealth_active = True
        player._cloak_drain_accum = 0.0
        player.add_buff("shadows", duration=999999.0, level=1)
        player.prep_seconds = 0.0
        self.add_event("PLAY_SOUND", {"sound": "MELD"}, floor_id=player.floor_id, source_player_id=player.id)
        self.add_event("STEALTH", {"player": player.id, "active": True}, floor_id=player.floor_id, source_player_id=player.id)
        return True

    def _end_cloak_stealth(self, player: Player) -> None:
        if not player.cloak_stealth_active:
            return
        player.cloak_stealth_active = False
        player.remove_buff("shadows")
        player.prep_seconds = 0.0
        self.add_event("STEALTH", {"player": player.id, "active": False}, floor_id=player.floor_id, source_player_id=player.id)

    def _tick_cloak(self, player: Player, dt: float) -> None:
        cloak = player.belongings.artifact
        is_cloak = cloak is not None and getattr(cloak, "kind", "") == "cloak_of_shadows"

        if player.cloak_stealth_active:
            if not is_cloak:
                self._end_cloak_stealth(player)
                return
            player._cloak_drain_accum += dt
            while player._cloak_drain_accum >= CLOAK_DRAIN_INTERVAL:
                player._cloak_drain_accum -= CLOAK_DRAIN_INTERVAL
                cloak.charge -= 1
                self._cloak_gain_exp(cloak)
                if cloak.charge <= 0:
                    cloak.charge = 0
                    self._end_cloak_stealth(player)
                    return
        elif is_cloak and cloak.charge < cloak.charge_cap and not cloak.cursed:
            # Light Cloak lets the cloak recharge even while unequipped, slower.
            rate = 1.0
            if not player.belongings.is_equipped(cloak.id):
                lc = player.talent_info.level("light_cloak")
                if lc <= 0:
                    return
                rate = 0.75 * lc / 3.0
            player._cloak_recharge_accum += dt * rate
            while player._cloak_recharge_accum >= CLOAK_RECHARGE_INTERVAL:
                player._cloak_recharge_accum -= CLOAK_RECHARGE_INTERVAL
                cloak.charge = min(cloak.charge + 1, cloak.charge_cap)
                if cloak.charge >= cloak.charge_cap:
                    player._cloak_recharge_accum = 0.0
                    break

    def _cloak_gain_exp(self, cloak) -> None:
        if cloak.level >= cloak.level_cap:
            return
        cloak.exp += CLOAK_EXP_PER_DRAIN
        if cloak.exp >= (cloak.level + 1) * 50:
            cloak.exp -= (cloak.level + 1) * 50
            cloak.level += 1
            cloak.level_known = True
            cloak.on_upgrade()

    # --- Preparation (Assassin) -------------------------------------------
    def _tick_preparation(self, player: Player, dt: float) -> None:
        from app.engine.entities.subclasses import Subclass
        if player.subclass_info.subclass != Subclass.ASSASSIN:
            return
        if player.invisible > 0:
            player.prep_seconds += dt
        else:
            player.prep_seconds = 0.0

    # --- Momentum (Freerunner) --------------------------------------------
    def gain_momentum(self, player: Player) -> None:
        from app.engine.entities.subclasses import Subclass
        if player.subclass_info.subclass != Subclass.FREERUNNER:
            return
        player.momentum_stacks = min(player.momentum_stacks + 1, MOMENTUM_MAX)
        player._momentum_decay_accum = 0.0

    def _tick_momentum(self, player: Player, dt: float, moved: bool) -> None:
        from app.engine.entities.subclasses import Subclass
        if player.subclass_info.subclass != Subclass.FREERUNNER:
            return
        if player.freerun_seconds > 0:
            player.freerun_seconds = max(0.0, player.freerun_seconds - dt)
        if moved or player.momentum_stacks <= 0:
            return
        player._momentum_decay_accum += dt
        while player._momentum_decay_accum >= MOMENTUM_DECAY_INTERVAL and player.momentum_stacks > 0:
            player._momentum_decay_accum -= MOMENTUM_DECAY_INTERVAL
            player.momentum_stacks -= 1

    def tick_rogue(self, player: Player, dt: float, moved: bool = False) -> None:
        self._tick_cloak(player, dt)
        self._tick_preparation(player, dt)
        self._tick_momentum(player, dt, moved)

    # --- Death Mark on-kill talents ---------------------------------------
    def process_death_mark_kill(self, killer, mob, floor, floor_id: int) -> None:
        """When a Death-Marked foe is slain, fire the killer's Death Mark
        talents: Deathly Durability (barrier) and Fear the Reaper (terror /
        cripple on the victim and nearby enemies)."""
        if not mob.has_buff("death_mark"):
            return
        from app.engine.entities.base import Player as PlayerCls, Faction
        if not isinstance(killer, PlayerCls):
            return
        ti = killer.talent_info

        dd = ti.level("deathly_durability")
        if dd > 0:
            shield = round(mob.max_hp * 0.125 * dd)
            if shield > 0:
                killer.add_shield("death_mark", shield, priority=1, decay=600)
                self.add_event("SHIELD", {"player": killer.id, "amount": shield}, floor_id=floor_id, source_player_id=killer.id)

        ftr = ti.level("fear_the_reaper")
        if ftr > 0:
            add_buff(mob.buffs, "cripple", duration=5.0, level=1)
            if ftr >= 2:
                add_buff(mob.buffs, "terror", duration=5.0, level=1)
            if ftr >= 3:
                for other in floor.mobs.values():
                    if other is mob or not other.is_alive or other.faction == Faction.PLAYER:
                        continue
                    if self._get_distance(mob.pos, other.pos) <= 3:
                        add_buff(other.buffs, "cripple", duration=5.0, level=1)
                        if ftr == 4:
                            add_buff(other.buffs, "terror", duration=5.0, level=1)

    # --- Assassin Preparation blink-strike --------------------------------
    def preparation_strike(self, player_id: str, target_x: int, target_y: int) -> bool:
        """Blink adjacent to a target within Preparation's blink range, then
        strike. Requires an invisible Assassin with Preparation accrued."""
        player = self.players.get(player_id)
        if not player or not player.is_alive or player.is_downed:
            return False
        from app.engine.entities.subclasses import Subclass
        if player.subclass_info.subclass != Subclass.ASSASSIN or player.invisible <= 0:
            return False
        if prep_tier(player.prep_seconds) < 0:
            return False

        floor = self._get_or_create_floor(player.floor_id)
        target = next((m for m in floor.mobs.values()
                       if m.is_alive and m.faction != "player"
                       and m.pos.x == target_x and m.pos.y == target_y), None)
        if target is None:
            return False

        reach = player.talent_info.level("assassins_reach")
        rng = prep_blink_range(player.prep_seconds, reach)
        if self._get_distance(player.pos, target.pos) > rng + 1:
            return False

        # Hop to a passable cell adjacent to the target, closest to the hero.
        best = None
        best_d = 1e9
        for ddx, ddy in ((0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (1, -1), (-1, 1), (-1, -1)):
            cx, cy = target.pos.x + ddx, target.pos.y + ddy
            if not (0 <= cx < floor.width and 0 <= cy < floor.height):
                continue
            if not floor.flags or not floor.flags.passable[cy][cx]:
                continue
            if any(m.is_alive and m.pos.x == cx and m.pos.y == cy for m in floor.mobs.values()):
                continue
            d = self._get_distance(player.pos, Position(x=cx, y=cy))
            if d < best_d:
                best_d, best = d, (cx, cy)
        if best is None:
            return False

        player.pos.x, player.pos.y = best
        self._invalidate_fov_cache()
        self.add_event("MOVE", {"entity": player.id, "x": best[0], "y": best[1]}, floor_id=player.floor_id)
        self.add_event("PLAY_SOUND", {"sound": "PUFF"}, floor_id=player.floor_id, source_player_id=player.id)
        # Attack the target from stealth (surprise + preparation applies).
        self.move_entity(player.id, target.pos.x - best[0], target.pos.y - best[1])
        return True
