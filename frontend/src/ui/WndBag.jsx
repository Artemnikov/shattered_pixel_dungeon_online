import { useState } from 'react';
import AudioManager from '../audio/AudioManager';
import ItemIcon from './ItemIcon';

// SPD-style inventory window (port of WndBag + WndUseItem). Shows the five equip
// slots, the backpack grid, and a context action menu built from the
// server-provided `item.actions` list. All actions are dispatched generically via
// EXECUTE_ITEM_ACTION; targeted actions (THROW/ZAP) are handed back to App to
// enter cell-targeting.
const EQUIP_SLOTS = [
  { key: 'weapon', label: 'Weapon' },
  { key: 'armor', label: 'Armor' },
  { key: 'artifact', label: 'Artifact' },
  { key: 'misc', label: 'Misc' },
  { key: 'ring', label: 'Ring' },
];

const ACTION_LABELS = {
  EQUIP: 'Equip', UNEQUIP: 'Unequip', DROP: 'Drop', THROW: 'Throw',
  DRINK: 'Drink', READ: 'Read', ZAP: 'Zap', EAT: 'Eat', OPEN: 'Open',
};

function levelText(item) {
  if (!item || !item.level_known || !item.level) return null;
  const sign = item.level > 0 ? '+' : '';
  return `${sign}${item.level}`;
}

function ItemSlot({ item, label, onClick, selected }) {
  return (
    <button
      className={`wndbag-slot ${item ? 'filled' : 'empty'} ${selected ? 'selected' : ''}`}
      onClick={() => { if (item) { AudioManager.play('CLICK'); onClick(item); } }}
      title={item ? item.name : label}
    >
      {item && <ItemIcon item={item} size={32} />}
      {item && item.quantity > 1 && <span className="wndbag-qty">{item.quantity}</span>}
      {item && levelText(item) && (
        <span className={`wndbag-level ${item.level > 0 ? 'up' : 'down'}`}>{levelText(item)}</span>
      )}
      {item && item.cursed && item.cursed_known && <span className="wndbag-curse">✗</span>}
      {!item && label && <span className="wndbag-slot-label">{label}</span>}
    </button>
  );
}

// Mounted only while open (parent renders it conditionally), so there is no
// `open` prop; toggling visibility is the parent's job ('f' or the bag button).
export default function WndBag({ belongings, onAction, onAssignQuickslot }) {
  const [selected, setSelected] = useState(null);

  const backpack = (belongings && belongings.backpack) || { items: [], capacity: 20 };
  const items = backpack.items || [];
  const capacity = backpack.capacity || 20;
  const emptyCount = Math.max(0, capacity - items.filter(i => i.kind !== 'bag').length);

  const pick = (item) => setSelected(prev => (prev && prev.id === item.id ? null : item));

  const runAction = (item, action) => {
    AudioManager.play('CLICK');
    setSelected(null);
    onAction(item.id, action);
  };

  return (
      <div className="wndbag">
        <div className="wndbag-equipped">
          {EQUIP_SLOTS.map(s => (
            <ItemSlot
              key={s.key}
              item={belongings ? belongings[s.key] : null}
              label={s.label}
              selected={selected && belongings && belongings[s.key] && selected.id === belongings[s.key].id}
              onClick={pick}
            />
          ))}
        </div>

        <div className="wndbag-grid">
          {items.map((item) => (
            <ItemSlot key={item.id} item={item} selected={selected && selected.id === item.id} onClick={pick} />
          ))}
          {Array.from({ length: emptyCount }).map((_, i) => (
            <div key={`e${i}`} className="wndbag-slot empty" />
          ))}
        </div>

        {selected && (
          <div className="wndbag-actions">
            <div className="wndbag-actions-name">
              {selected.name}{levelText(selected) ? ` ${levelText(selected)}` : ''}
            </div>
            <div className="wndbag-actions-btns">
              {(selected.actions || []).map(action => (
                <button key={action} onClick={() => runAction(selected, action)}>
                  {ACTION_LABELS[action] || action}
                </button>
              ))}
              <button
                className="qs-assign"
                onClick={() => { AudioManager.play('CLICK'); onAssignQuickslot(selected.id); setSelected(null); }}
              >
                Quickslot
              </button>
            </div>
          </div>
        )}
      </div>
  );
}
