import { useEffect } from 'react';
import AudioManager from '../audio/AudioManager';
import InventoryPane from './InventoryPane';

export default function WndBag({ belongings, gold, energy, strength, onOpenItem, onContextMenu, onDefaultAction, onClose, selectMode, onSelectItem, title }) {
  useEffect(() => {
    const onKey = (e) => { if (e.key === 'Escape' || e.key === 'f') onClose(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  return (
    <div className="wnd-overlay wnd-bag-overlay" onClick={onClose}>
      <div className="wnd-bag" onClick={(e) => e.stopPropagation()}>
        <button
          className="wnd-bag-close"
          onClick={() => { AudioManager.play('CLICK'); onClose(); }}
          aria-label="Close inventory"
        >
          ✕
        </button>
        {title && <div className="wnd-bag-title">{title}</div>}
        <InventoryPane
          belongings={belongings}
          gold={gold}
          energy={energy}
          strength={strength}
          onOpenItem={onOpenItem}
          onContextMenu={onContextMenu}
          onDefaultAction={onDefaultAction}
          selectMode={selectMode}
          onSelectItem={onSelectItem}
        />
      </div>
    </div>
  );
}
