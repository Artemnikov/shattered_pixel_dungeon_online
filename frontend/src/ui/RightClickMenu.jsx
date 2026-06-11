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
import { useEffect, useLayoutEffect, useRef } from 'react';
import AudioManager from '../audio/AudioManager';
import { actionLabel, orderedActions } from './itemActions';

// Compact context menu shown at the cursor (port of RightClickMenu.java).
// Lists the item's actions (default first/highlighted) plus a Quickslot entry.
// Closes on selection or any outside interaction.
export default function RightClickMenu({ item, x, y, onAction, onAssignQuickslot, onClose }) {
  const ref = useRef(null);

  // Clamp inside the viewport once measured, mutating style directly to avoid a
  // reposition re-render flash.
  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    const { width, height } = el.getBoundingClientRect();
    const nx = x + width > window.innerWidth ? Math.max(0, window.innerWidth - width - 4) : x;
    const ny = y + height > window.innerHeight ? Math.max(0, window.innerHeight - height - 4) : y;
    el.style.left = `${nx}px`;
    el.style.top = `${ny}px`;
  }, [x, y]);

  useEffect(() => {
    const close = () => onClose();
    const onKey = (e) => { if (e.key === 'Escape') onClose(); };
    // Defer so the opening click/contextmenu doesn't immediately dismiss it.
    const id = setTimeout(() => {
      window.addEventListener('pointerdown', close);
      window.addEventListener('keydown', onKey);
    }, 0);
    return () => {
      clearTimeout(id);
      window.removeEventListener('pointerdown', close);
      window.removeEventListener('keydown', onKey);
    };
  }, [onClose]);

  if (!item) return null;

  const def = item.default_action;
  const run = (action) => {
    AudioManager.play('CLICK');
    onClose();
    onAction(item.id, action);
  };

  return (
    <div
      ref={ref}
      className="rc-menu"
      style={{ left: x, top: y }}
      onPointerDown={(e) => e.stopPropagation()}
    >
      <div className="rc-menu-title">{item.name}</div>
      {orderedActions(item).map(action => (
        <button key={action} className={action === def ? 'default' : ''} onClick={() => run(action)}>
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
  );
}
