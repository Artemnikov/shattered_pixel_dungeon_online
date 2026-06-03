import { useEffect, useRef } from 'react';

const DIRECTION_KEYS = new Set(['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'w', 'a', 's', 'd']);

function isUp(key) { return key === 'ArrowUp' || key === 'w'; }
function isDown(key) { return key === 'ArrowDown' || key === 's'; }
function isLeft(key) { return key === 'ArrowLeft' || key === 'a'; }
function isRight(key) { return key === 'ArrowRight' || key === 'd'; }

// Net movement vector from the set of currently held direction keys. Opposite keys
// cancel out (e.g. holding left+right yields dx=0). Diagonals are just dx,dy = ±1 each.
function getVector(pressed) {
  let dx = 0, dy = 0;
  for (const key of pressed) {
    if (isUp(key)) dy = -1;
    if (isDown(key)) dy = 1;
    if (isLeft(key)) dx = -1;
    if (isRight(key)) dx = 1;
  }
  return { dx, dy };
}

export default function useKeyboardControls({
  socketRef,
  inventory,
  setShowInventory,
  handleToolbarClick,
  handleToolbarDoubleClick,
  onExamineOrReveal,
  onCancelModes,
  triggerWait,
  isRefocusingRef,
  isDraggingRef,
  quickslot,
  itemsById,
  onRadialSelect,
}) {
  const lastKeyRef = useRef({ key: null, time: 0 });
  const pressedKeysRef = useRef(new Set());
  const lastSentVectorRef = useRef({ dx: 0, dy: 0 });

  useEffect(() => {
    // Send the current held-direction intent to the server, which paces the actual
    // stepping. Only sends on change so key auto-repeat is irrelevant. dx,dy = 0 stops.
    const syncMoveIntent = () => {
      if (socketRef.current?.readyState !== WebSocket.OPEN) return;
      const { dx, dy } = getVector(pressedKeysRef.current);
      const last = lastSentVectorRef.current;
      if (dx === last.dx && dy === last.dy) return;
      lastSentVectorRef.current = { dx, dy };
      if (dx === 0 && dy === 0) {
        socketRef.current.send(JSON.stringify({ type: 'MOVE_STOP' }));
      } else {
        isRefocusingRef.current = true;
        isDraggingRef.current = false;
        socketRef.current.send(JSON.stringify({ type: 'MOVE_INTENT', dx, dy }));
      }
    };

    const handleKeyDown = (e) => {
      pressedKeysRef.current.add(e.key);

      if (e.key === 'f') {
        setShowInventory(prev => !prev);
        return;
      }
      if (e.key === 'e') {
        if (onExamineOrReveal) onExamineOrReveal();
        return;
      }
      if (e.key === 'Escape') {
        if (onCancelModes) onCancelModes();
        return;
      }
      if (e.key === ' ' || e.key === 'Spacebar') {
        e.preventDefault();
        if (triggerWait) triggerWait();
        return;
      }
      if (e.key === 'q') {
        if (onRadialSelect) onRadialSelect();
        return;
      }

      if (['1', '2', '3', '4', '5', '6'].includes(e.key)) {
        const index = parseInt(e.key) - 1;
        const slot = quickslot?.slots?.[index];
        const item = slot?.item_id ? (itemsById?.[slot.item_id] || null) : null;
        if (item) {
          const now = Date.now();
          const isDoubleTap = lastKeyRef.current.key === e.key && (now - lastKeyRef.current.time) < 300;

          if (isDoubleTap) {
            handleToolbarDoubleClick(item);
            lastKeyRef.current = { key: null, time: 0 };
          } else {
            handleToolbarClick(item);
            lastKeyRef.current = { key: e.key, time: now };
          }
        }
      }

      if (DIRECTION_KEYS.has(e.key)) {
        // Auto-repeat keydowns don't change the held set, so syncMoveIntent no-ops on
        // them; the server paces repeated stepping while the key stays down.
        syncMoveIntent();
      }
    };

    const handleKeyUp = (e) => {
      pressedKeysRef.current.delete(e.key);
      if (DIRECTION_KEYS.has(e.key)) {
        syncMoveIntent();
      }
    };

    const handleBlur = () => {
      pressedKeysRef.current.clear();
      syncMoveIntent();
    };

    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('keyup', handleKeyUp);
    window.addEventListener('blur', handleBlur);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('keyup', handleKeyUp);
      window.removeEventListener('blur', handleBlur);
    };
  }, [inventory, handleToolbarClick, handleToolbarDoubleClick, socketRef, setShowInventory, onExamineOrReveal, onCancelModes, triggerWait, isRefocusingRef, isDraggingRef, quickslot, itemsById, onRadialSelect]);
}
