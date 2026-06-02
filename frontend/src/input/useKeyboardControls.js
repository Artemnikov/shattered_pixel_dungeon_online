import { useEffect, useRef } from 'react';

export default function useKeyboardControls({
  socketRef,
  inventory,
  setShowInventory,
  handleToolbarClick,
  handleToolbarDoubleClick,
  triggerSearch,
  triggerWait,
  isRefocusingRef,
  isDraggingRef,
  quickslot,
  itemsById,
}) {
  const lastKeyRef = useRef({ key: null, time: 0 });
  const holdSkipRef = useRef(false);

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'f') {
        setShowInventory(prev => !prev);
        return;
      }
      if (e.key === 'e') {
        // Mirror the original: search is the second of a double-press (1st E enters
        // examine mode, 2nd searches). The remake has no examine mode, so a single
        // press is inert and only a double-tap within 300ms triggers the search.
        const now = Date.now();
        const isDoubleTap = lastKeyRef.current.key === 'e' && (now - lastKeyRef.current.time) < 300;
        if (isDoubleTap) {
          triggerSearch();
          lastKeyRef.current = { key: null, time: 0 };
        } else {
          lastKeyRef.current = { key: 'e', time: now };
        }
        return;
      }
      if (e.key === ' ' || e.key === 'Spacebar') {
        e.preventDefault();
        if (triggerWait) triggerWait();
        return;
      }

      let direction = null;
      if (e.key === 'ArrowUp' || e.key === 'w') direction = 'UP';
      if (e.key === 'ArrowDown' || e.key === 's') direction = 'DOWN';
      if (e.key === 'ArrowLeft' || e.key === 'a') direction = 'LEFT';
      if (e.key === 'ArrowRight' || e.key === 'd') direction = 'RIGHT';

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

      if (direction && socketRef.current?.readyState === WebSocket.OPEN) {
        if (e.repeat) {
          holdSkipRef.current = !holdSkipRef.current;
          if (holdSkipRef.current) return;
        } else {
          holdSkipRef.current = false;
        }
        isRefocusingRef.current = true;
        isDraggingRef.current = false;
        socketRef.current.send(JSON.stringify({ type: 'MOVE', direction }));
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [inventory, handleToolbarClick, handleToolbarDoubleClick, socketRef, setShowInventory, triggerSearch, triggerWait, isRefocusingRef, isDraggingRef, quickslot, itemsById]);
}
