// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 ArtemNikov
//
// Adapted from Shattered Pixel Dungeon (C) 2014-2024 Evan Debenham
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
// See the GNU General Public License for more details.
//
// Top-of-screen boss HP bar, shown while a boss (e.g. Goo) is alive on the floor.
// Mirrors the original SPD's BossHealthBar HUD element.
export default function BossHealthBar({ boss }) {
  if (!boss) return null;
  const pct = Math.max(0, Math.min(1, boss.maxHp > 0 ? boss.hp / boss.maxHp : 0));

  return (
    <div className="boss-health-bar">
      <div className="boss-health-bar__box">
        <div className="boss-health-bar__name">{boss.name}</div>
        <div className="boss-health-bar__track">
          <div className="boss-health-bar__fill" style={{ width: `${pct * 100}%` }} />
        </div>
      </div>
    </div>
  );
}
