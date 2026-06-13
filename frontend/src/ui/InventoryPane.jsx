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
import { useRef, useState } from 'react';
import AudioManager from '../audio/AudioManager';
import ItemIcon from './ItemIcon';
import ItemGlyph from './ItemGlyph';
import { HOLDER_SPRITES } from '../rendering/sprites';

// SPD-style persistent inventory pane (port of InventoryPane.java). Shows the
// five equip slots + an inline gold/energy readout, bag tabs for nested bags,
// and the grid of the active bag. Clicking a slot opens the info+actions popup
// (WndUseItem); right-click / long-press opens the context menu. Visual state on
// each slot mirrors SPD's ItemSlot (equipped tint, unidentified/curse tint,
// strength-requirement badge, upgrade level).
const EQUIP_SLOTS = [
  { key: 'weapon', label: 'Wep' },
  { key: 'armor', label: 'Arm' },
  { key: 'artifact', label: 'Art' },
  { key: 'misc', label: 'Misc' },
  { key: 'ring', label: 'Ring' },
];

const EQUIPPABLE_TYPES = new Set(['weapon', 'wearable', 'ring', 'artifact']);
const LONG_PRESS_MS = 450;

function levelText(item) {
  if (!item || !item.level_known || !item.level) return null;
  return `${item.level > 0 ? '+' : ''}${item.level}`;
}

function isIdentified(item) {
  return !!(item.level_known && item.cursed_known);
}

// Mirrors ItemSlot.java's background tint rules.
function tintClass(item) {
  if (item.cursed && item.cursed_known) return 'tint-cursed';
  const equippable = EQUIPPABLE_TYPES.has(item.type) || item.kind === 'wand';
  if (equippable && !isIdentified(item)) {
    return item.cursed_known ? 'tint-magic' : 'tint-unknown';
  }
  return '';
}

// Strength-requirement badge for weapons/armor (ItemSlot.java's `extra`).
function strBadge(item, strength) {
  if (item.type !== 'weapon' && item.type !== 'wearable') return null;
  const req = item.strength_requirement;
  if (req == null) return null;
  // SPD ItemSlot: unidentified gear shows the typical STR as "N?" in warning
  // orange; identified gear shows ":N", red when the hero lacks the strength.
  if (!item.level_known) return { text: `${req}?`, cls: 'str-warn' };
  return { text: `:${req}`, cls: strength != null && strength < req ? 'str-bad' : 'str-ok' };
}

function ItemSlot({ item, holderKey, equipped, strength, empty, onOpen, onContext, onDefaultAction, selectMode, onSelectItem }) {
  const timerRef = useRef(null);
  const longFiredRef = useRef(false);

  if (empty || !item) {
    // Empty equip slots show SPD's placeholder holder sprite; empty backpack
    // cells stay blank.
    const holder = holderKey && HOLDER_SPRITES[holderKey];
    return (
      <div className="inv-slot empty">
        {holder && <ItemIcon size={32} coords={holder} />}
      </div>
    );
  }

  const badge = strBadge(item, strength);

  const openContext = (clientX, clientY) => onContext(item, clientX, clientY);

  const selectable = item.default_action != null;

  const handleClick = () => {
    if (longFiredRef.current) { longFiredRef.current = false; return; }
    AudioManager.play('CLICK');
    if (selectMode) {
      if (selectable) onSelectItem(item);
      return;
    }
    onOpen(item);
  };

  return (
    <button
      className={`inv-slot filled ${equipped ? 'equipped' : ''} ${tintClass(item)} ${selectMode && !selectable ? 'inv-slot-unselectable' : ''}`}
      title={item.name}
      onClick={handleClick}
      onAuxClick={selectMode ? undefined : (e) => { if (e.button === 1) { e.preventDefault(); if (item.default_action) onDefaultAction(item); } }}
      onContextMenu={selectMode ? undefined : (e) => { e.preventDefault(); AudioManager.play('CLICK'); openContext(e.clientX, e.clientY); }}
      onPointerDown={selectMode ? undefined : (e) => {
        if (e.pointerType !== 'touch') return;
        longFiredRef.current = false;
        timerRef.current = setTimeout(() => {
          longFiredRef.current = true;
          openContext(e.clientX, e.clientY);
        }, LONG_PRESS_MS);
      }}
      onPointerUp={selectMode ? undefined : () => { clearTimeout(timerRef.current); }}
      onPointerLeave={selectMode ? undefined : () => { clearTimeout(timerRef.current); }}
    >
      <ItemIcon item={item} size={32} />
      <ItemGlyph item={item} />
      {item.kind === 'waterskin'
        ? <span className="inv-qty">{item.volume}/20</span>
        : item.quantity > 1 && <span className="inv-qty">{item.quantity}</span>}
      {badge && <span className={`inv-str ${badge.cls}`}>{badge.text}</span>}
      {levelText(item) && (
        <span className={`inv-level ${item.level > 0 ? 'up' : 'down'}`}>{levelText(item)}</span>
      )}
      {item.cursed && item.cursed_known && <span className="inv-curse">✗</span>}
    </button>
  );
}

export default function InventoryPane({ belongings, gold, energy, strength, onOpenItem, onContextMenu, onDefaultAction, selectMode, onSelectItem }) {
  const backpack = (belongings && belongings.backpack) || { items: [], capacity: 20 };

  // Bag tabs: backpack first, then any nested bags it contains.
  const nestedBags = (backpack.items || []).filter(i => i.kind === 'bag');
  const bags = [backpack, ...nestedBags];

  const [activeBagId, setActiveBagId] = useState(backpack.id);
  // Fall back to the backpack if the selected bag is gone (e.g. dropped) without
  // a state write — derive the effective id each render instead.
  const effectiveBagId = bags.some(b => b.id === activeBagId) ? activeBagId : backpack.id;

  const activeBag = bags.find(b => b.id === effectiveBagId) || backpack;
  const items = (activeBag.items || []).filter(i => i.kind !== 'bag');
  const capacity = activeBag.capacity || 20;
  const emptyCount = Math.max(0, capacity - items.length);

  const equippedIds = new Set(EQUIP_SLOTS.map(s => belongings && belongings[s.key]).filter(Boolean).map(i => i.id));

  return (
    <div className="inv-pane">
      <div className="inv-equip-row">
        {EQUIP_SLOTS.map(s => (
          <ItemSlot
            key={s.key}
            item={belongings ? belongings[s.key] : null}
            holderKey={s.key}
            equipped
            strength={strength}
            onOpen={onOpenItem}
            onContext={onContextMenu}
            onDefaultAction={onDefaultAction}
            selectMode={selectMode}
            onSelectItem={onSelectItem}
          />
        ))}
        <div className="inv-currency">
          <span className="inv-gold">{gold ?? 0}<i className="inv-gold-icon" /></span>
          {energy > 0 && <span className="inv-energy">{energy}<i className="inv-energy-icon" /></span>}
        </div>
      </div>

      {bags.length > 1 && (
        <div className="inv-bag-tabs">
          {bags.map(b => (
            <button
              key={b.id}
              className={`inv-bag-tab ${b.id === effectiveBagId ? 'active' : ''}`}
              onClick={() => { AudioManager.play('CLICK'); setActiveBagId(b.id); }}
              title={b.name || 'Backpack'}
            >
              <ItemIcon item={b.id === backpack.id ? { name: 'Backpack', type: 'bag' } : b} size={20} />
            </button>
          ))}
        </div>
      )}

      <div className="inv-grid">
        {items.map(item => (
          <ItemSlot
            key={item.id}
            item={item}
            equipped={equippedIds.has(item.id)}
            strength={strength}
            onOpen={onOpenItem}
            onContext={onContextMenu}
            onDefaultAction={onDefaultAction}
            selectMode={selectMode}
            onSelectItem={onSelectItem}
          />
        ))}
        {Array.from({ length: emptyCount }).map((_, i) => (
          <ItemSlot key={`e${i}`} empty />
        ))}
      </div>
    </div>
  );
}
