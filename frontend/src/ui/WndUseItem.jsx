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
import { useEffect } from 'react';
import AudioManager from '../audio/AudioManager';
import ItemIcon from './ItemIcon';
import { actionLabel, orderedActions, titleColor } from './itemActions';

// SPD-style item info + actions popup (port of WndInfoItem + WndUseItem).
// Centered modal: icon title (coloured by upgrade level), description text, then
// a row of action buttons (default highlighted) plus a Quickslot button.
export default function WndUseItem({ item, onAction, onAssignQuickslot, onClose }) {
  useEffect(() => {
    const onKey = (e) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  if (!item) return null;

  const def = item.default_action;
  const actions = orderedActions(item);
  const level = levelText(item);

  const run = (action) => {
    AudioManager.play('CLICK');
    onClose();
    onAction(item.id, action);
  };

  return (
    <div className="wnd-overlay" onClick={onClose}>
      <div className="wnd-item" onClick={(e) => e.stopPropagation()}>
        <div className="wnd-item-title">
          <ItemIcon item={item} size={16} />
          <span style={{ color: titleColor(item) }}>
            {item.name}{level ? ` ${level}` : ''}
          </span>
        </div>

        {item.description && (
          <div className="wnd-item-desc">{item.description}</div>
        )}

        <div className="wnd-item-actions">
          {actions.map(action => (
            <button
              key={action}
              className={action === def ? 'default' : ''}
              onClick={() => run(action)}
            >
              {actionLabel(action)}
            </button>
          ))}
          {def && (
            <button
              className="qs-assign"
              onClick={() => { AudioManager.play('CLICK'); onAssignQuickslot(item.id); onClose(); }}
            >
              Quickslot
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

function levelText(item) {
  if (!item.level_known || !item.level) return null;
  return `${item.level > 0 ? '+' : ''}${item.level}`;
}
