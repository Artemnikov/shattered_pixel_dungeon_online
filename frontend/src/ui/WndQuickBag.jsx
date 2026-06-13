import { useEffect, useMemo, useRef } from 'react';
import AudioManager from '../audio/AudioManager';
import ItemIcon from './ItemIcon';

const LONG_PRESS_MS = 450;

function isEquipped(item, belongings) {
  if (!belongings || !item) return false;
  for (const key of ['weapon', 'armor', 'artifact', 'misc', 'ring']) {
    if (belongings[key] && belongings[key].id === item.id) return true;
  }
  return false;
}

function categoryOrder(item) {
  if (item.kind === 'potion') return 0;
  if (item.kind === 'scroll') return 1;
  if (item.kind === 'wand') return 2;
  if (item.type === 'throwable') return 3;
  if (item.kind === 'food') return 4;
  return 9;
}

function filteredQuickItems(backpack, belongings) {
  const all = [];
  const walk = (bag) => {
    (bag?.items || []).forEach(it => {
      if (it.items) { walk(it); return; }
      if (!it.default_action) return;
      if (it.kind === 'bag') return;
      if (it.type === 'artifact' && !isEquipped(it, belongings)) return;
      all.push(it);
    });
  };
  walk(backpack);
  all.sort((a, b) => {
    const aEq = isEquipped(a, belongings) ? 0 : 1;
    const bEq = isEquipped(b, belongings) ? 0 : 1;
    if (aEq !== bEq) return aEq - bEq;
    return categoryOrder(a) - categoryOrder(b);
  });
  return all;
}

export default function WndQuickBag({ belongings, onUse, onClose }) {
  const items = useMemo(
    () => filteredQuickItems(belongings?.backpack, belongings),
    [belongings]
  );

  useEffect(() => {
    const onKey = (e) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  const handleClick = (item) => {
    AudioManager.play('CLICK');
    onClose();
    if (item.default_action) onUse(item.id, item.default_action);
  };

  return (
    <div className="wnd-overlay wnd-qb-overlay" onClick={onClose}>
      <div className="wnd-qb" onClick={(e) => e.stopPropagation()}>
        <div className="wnd-qb-title">Quick-use</div>
        <div className="wnd-qb-grid">
          {items.map(item => (
            <QuickItemButton key={item.id} item={item} onClick={handleClick} />
          ))}
        </div>
      </div>
    </div>
  );
}

function QuickItemButton({ item, onClick }) {
  const timerRef = useRef(null);
  const longFiredRef = useRef(false);

  const handlePointerDown = (e) => {
    if (e.pointerType !== 'touch') return;
    longFiredRef.current = false;
    timerRef.current = setTimeout(() => {
      longFiredRef.current = true;
    }, LONG_PRESS_MS);
  };

  const handlePointerUp = () => {
    clearTimeout(timerRef.current);
  };

  const handleClick = () => {
    if (longFiredRef.current) { longFiredRef.current = false; return; }
    onClick(item);
  };

  return (
    <button
      className="wnd-qb-item"
      onClick={handleClick}
      onPointerDown={handlePointerDown}
      onPointerUp={handlePointerUp}
      onPointerLeave={handlePointerUp}
    >
      <ItemIcon item={item} size={24} />
      <span className="wnd-qb-item-name">{item.name}</span>
    </button>
  );
}
