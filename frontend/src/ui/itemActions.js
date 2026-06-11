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
// Shared helpers for rendering an item's action list in the info popup
// (WndUseItem) and the right-click context menu (RightClickMenu).
export const ACTION_LABELS = {
  EQUIP: 'Equip', UNEQUIP: 'Unequip', DROP: 'Drop', THROW: 'Throw',
  DRINK: 'Drink', READ: 'Read', ZAP: 'Zap', EAT: 'Eat', OPEN: 'Open',
  AFFIX: 'Affix', STEALTH: 'Stealth',
};

export const actionLabel = (a) => ACTION_LABELS[a] || a;

// Order an item's actions with its default action first, matching SPD's
// RightClickMenu/WndUseItem (which surface the default action prominently).
export function orderedActions(item) {
  const actions = [...(item.actions || [])];
  const def = item.default_action;
  if (def && actions.includes(def)) {
    return [def, ...actions.filter(a => a !== def)];
  }
  return actions;
}

export function titleColor(item) {
  if (item.level_known && item.level > 0) return '#5fd35f';
  if (item.level_known && item.level < 0) return '#e06666';
  return '#f1c40f';
}
