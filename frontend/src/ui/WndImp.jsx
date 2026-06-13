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

// Imp quest dialogue (WndImp.java): quest offer / reminder, with a claim
// button once enough DwarfTokens have been collected.
export default function WndImp({ npcId, text, canClaim, onClaim, onClose }) {
  useEffect(() => {
    const onKey = (e) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  return (
    <div className="wnd-overlay" onClick={onClose}>
      <div className="wnd-item" onClick={(e) => e.stopPropagation()}>
        <div className="wnd-item-title">Imp</div>
        <div className="wnd-item-desc">{text}</div>
        <div className="wnd-item-actions">
          {canClaim && (
            <button
              className="default"
              onClick={() => { AudioManager.play('CLICK'); onClaim(npcId); }}
            >
              Claim Reward
            </button>
          )}
          <button onClick={() => { AudioManager.play('CLICK'); onClose(); }}>Close</button>
        </div>
      </div>
    </div>
  );
}
