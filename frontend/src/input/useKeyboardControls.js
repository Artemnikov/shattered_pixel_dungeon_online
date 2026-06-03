import { useEffect, useRef } from 'react';

const DIRECTION_KEYS = new Set(['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'w', 'a', 's', 'd']);

function isUp(key) { return key === 'ArrowUp' || key === 'w'; }
function isDown(key) { return key === 'ArrowDown' || key === 's'; }
function isLeft(key) { return key === 'ArrowLeft' || key === 'a'; }
function isRight(key) { return key === 'ArrowRight' || key === 'd'; }

function getDirectionFromKeys(pressed) {
  let dx = 0, dy = 0;
  for (const key of pressed) {
    if (isUp(key)) dy = -1;
    if (isDown(key)) dy = 1;
    if (isLeft(key)) dx = -1;
    if (isRight(key)) dx = 1;
  }
  if (dx === 0 && dy === 0) return null;
  if (dx === 0 && dy === -1) return 'UP';
  if (dx === 0 && dy === 1) return 'DOWN';
  if (dx === -1 && dy === 0) return 'LEFT';
  if (dx === 1 && dy === 0) return 'RIGHT';
  if (dx === -1 && dy === -1) return 'UP_LEFT';
  if (dx === 1 && dy === -1) return 'UP_RIGHT';
  if (dx === -1 && dy === 1) return 'DOWN_LEFT';
  if (dx === 1 && dy === 1) return 'DOWN_RIGHT';
  return null;
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
  const holdSkipRef = useRef(false);
  const pressedKeysRef = useRef(new Set());

  const sendMove = (direction) => {
    if (direction && socketRef.current?.readyState === WebSocket.OPEN) {
      isRefocusingRef.current = true;
      isDraggingRef.current = false;
      socketRef.current.send(JSON.stringify({ type: 'MOVE', direction }));
    }
  };

  useEffect(() => {
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

      const currentPressed = pressedKeysRef.current;
      if (DIRECTION_KEYS.has(e.key) && socketRef.current?.readyState === WebSocket.OPEN) {
        if (e.repeat) {
          holdSkipRef.current = !holdSkipRef.current;
          if (holdSkipRef.current) return;
        } else {
          holdSkipRef.current = false;
        }
        sendMove(getDirectionFromKeys(currentPressed));
      }
    };

    const handleKeyUp = (e) => {
      pressedKeysRef.current.delete(e.key);
      const direction = getDirectionFromKeys(pressedKeysRef.current);
      if (direction) {
        sendMove(direction);
      }
    };

    const handleBlur = () => {
      pressedKeysRef.current.clear();
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
