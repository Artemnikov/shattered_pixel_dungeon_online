import { useEffect, useRef, useState } from 'react';
import AudioManager from '../audio/AudioManager';
import ItemIcon from './ItemIcon';

export default function RadialMenu({ items, size = 140, onSelect, onClose }) {
  const containerRef = useRef(null);
  const [activeIdx, setActiveIdx] = useState(-1);
  const activeRef = useRef(-1);
  const onSelectRef = useRef(onSelect);
  const onCloseRef = useRef(onClose);
  const itemsRef = useRef(items);
  const slotCount = items.length;
  const cx = size;
  const cy = size;
  const radius = size * 0.6;
  const iconSize = 28;

  onSelectRef.current = onSelect;
  onCloseRef.current = onClose;
  itemsRef.current = items;

  useEffect(() => {
    const onKey = (e) => { if (e.key === 'Escape') onCloseRef.current(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  const angleForPoint = (clientX, clientY) => {
    const el = containerRef.current;
    if (!el) return -1;
    const rect = el.getBoundingClientRect();
    const px = clientX - rect.left - cx;
    const py = clientY - rect.top - cy;
    const dist = Math.sqrt(px * px + py * py);
    if (dist < radius * 0.3 || dist > radius * 1.3) return -1;
    const angle = (Math.atan2(py, px) + Math.PI * 2.5) % (Math.PI * 2);
    return angle / (Math.PI * 2 / slotCount);
  };

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const onPointerMove = (e) => {
      const raw = angleForPoint(e.clientX, e.clientY);
      const clamped = Math.max(0, Math.min(slotCount - 1, Math.round(raw)));
      if (raw < 0 || raw >= slotCount) {
        setActiveIdx(-1);
        activeRef.current = -1;
        return;
      }
      setActiveIdx(clamped);
      activeRef.current = clamped;
    };

    const onPointerUp = () => {
      const idx = activeRef.current;
      if (idx >= 0 && idx < slotCount && itemsRef.current[idx]) {
        AudioManager.play('CLICK');
        onSelectRef.current(idx);
      }
      onCloseRef.current();
    };

    el.addEventListener('pointermove', onPointerMove);
    el.addEventListener('pointerup', onPointerUp);
    el.addEventListener('pointerleave', () => { setActiveIdx(-1); activeRef.current = -1; });

    return () => {
      el.removeEventListener('pointermove', onPointerMove);
      el.removeEventListener('pointerup', onPointerUp);
    };
  }, [slotCount, cx, cy, radius]);

  const handleSlotClick = (idx) => {
    if (items[idx]) {
      AudioManager.play('CLICK');
      onSelect(idx);
    }
    onClose();
  };

  const slotPositions = [];
  for (let i = 0; i < slotCount; i++) {
    const angle = (2 * Math.PI * i / slotCount) - Math.PI / 2;
    slotPositions.push({
      x: cx + radius * Math.cos(angle) - iconSize / 2,
      y: cy + radius * Math.sin(angle) - iconSize / 2,
    });
  }

  return (
    <div className="radial-overlay" onClick={onClose}>
      <div
        ref={containerRef}
        className="radial-container"
        style={{ width: size * 2, height: size * 2 }}
        onClick={(e) => e.stopPropagation()}
      >
        <svg className="radial-svg" width={size * 2} height={size * 2}>
          <circle cx={cx} cy={cy} r={radius} fill="none" stroke="#4a4a55" strokeWidth="2" />
          {slotPositions.map((pos, i) => {
            const angleRad = (2 * Math.PI * i / slotCount) - Math.PI / 2;
            const halfAngle = Math.PI / slotCount;
            const innerR = radius - 22;
            const outerR = radius + 22;
            const x1 = cx + innerR * Math.cos(angleRad - halfAngle);
            const y1 = cy + innerR * Math.sin(angleRad - halfAngle);
            const x2 = cx + innerR * Math.cos(angleRad + halfAngle);
            const y2 = cy + innerR * Math.sin(angleRad + halfAngle);
            const x3 = cx + outerR * Math.cos(angleRad + halfAngle);
            const y3 = cy + outerR * Math.sin(angleRad + halfAngle);
            const x4 = cx + outerR * Math.cos(angleRad - halfAngle);
            const y4 = cy + outerR * Math.sin(angleRad - halfAngle);
            const largeArc = halfAngle * 2 > Math.PI ? 1 : 0;
            return (
              <path
                key={i}
                d={`M${x1},${y1} A${innerR},${innerR} 0 ${largeArc} 1 ${x2},${y2} L${x3},${y3} A${outerR},${outerR} 0 ${largeArc} 0 ${x4},${y4} Z`}
                fill={activeIdx === i ? 'rgba(241,196,15,0.2)' : 'transparent'}
                stroke={activeIdx === i ? '#f1c40f' : '#3a3a44'}
                strokeWidth="1.5"
              />
            );
          })}
        </svg>

        {items.map((item, i) => {
          const pos = slotPositions[i];
          return (
            <button
              key={i}
              className={`radial-slot ${activeIdx === i ? 'active' : ''} ${!item ? 'empty' : ''}`}
              style={{
                left: pos.x,
                top: pos.y,
                width: iconSize,
                height: iconSize,
              }}
              onClick={(e) => { e.stopPropagation(); handleSlotClick(i); }}
              onPointerDown={(e) => { e.stopPropagation(); activeRef.current = i; setActiveIdx(i); }}
            >
              {item ? (
                <ItemIcon item={item} size={iconSize} />
              ) : (
                <span className="radial-slot-num">{i + 1}</span>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
