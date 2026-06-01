import { useEffect, useRef } from 'react';
import { TILE_SIZE, MIN_ZOOM, MAX_ZOOM } from '../constants';
import { resolveTapAction } from './resolveTap';

export default function useCanvasControls({
  enabled,
  canvasRef,
  socketRef,
  panOffsetRef,
  zoomRef,
  cameraLerpRef,
  isDraggingRef,
  isRefocusingRef,
  isPinchingRef,
  targetingModeRef,
  onTargetTapRef,
  entitiesRef,
  myPlayerIdRef,
}) {
  const dragStartRef = useRef({ x: 0, y: 0 });
  const dragStartPanRef = useRef({ x: 0, y: 0 });
  const hasDraggedRef = useRef(false);
  const pinchStartDistRef = useRef(0);
  const pinchStartZoomRef = useRef(1);
  const pinchMidStartRef = useRef({ x: 0, y: 0 });
  const pinchPanStartRef = useRef({ x: 0, y: 0 });

  useEffect(() => {
    if (!enabled) return;
    const canvas = canvasRef.current;
    if (!canvas) return;

    const onMouseDown = (e) => {
      dragStartRef.current = { x: e.clientX, y: e.clientY };
      dragStartPanRef.current = { ...panOffsetRef.current };
      isDraggingRef.current = true;
      hasDraggedRef.current = false;
      isRefocusingRef.current = false;
    };

    const onMouseMove = (e) => {
      if (!isDraggingRef.current) return;
      const dx = e.clientX - dragStartRef.current.x;
      const dy = e.clientY - dragStartRef.current.y;
      if (Math.sqrt(dx * dx + dy * dy) > 4) hasDraggedRef.current = true;
      const z = zoomRef.current;
      panOffsetRef.current = {
        x: dragStartPanRef.current.x - dx / z,
        y: dragStartPanRef.current.y - dy / z,
      };
    };

    const onMouseUp = () => { isDraggingRef.current = false; };

    const onWheel = (e) => {
      e.preventDefault();
      const rect = canvas.getBoundingClientRect();
      const cursorX = e.clientX - rect.left;
      const cursorY = e.clientY - rect.top;
      const cw = canvas.width, ch = canvas.height;
      const oldZoom = zoomRef.current;
      const factor = e.deltaY < 0 ? 1.1 : 0.9;
      const newZoom = Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, oldZoom * factor));
      panOffsetRef.current.x += (cursorX - cw / 2) * (1 / oldZoom - 1 / newZoom);
      panOffsetRef.current.y += (cursorY - ch / 2) * (1 / oldZoom - 1 / newZoom);
      zoomRef.current = newZoom;
    };

    const onTouchStart = (e) => {
      if (e.touches.length === 2) {
        isPinchingRef.current = true;
        const t1 = e.touches[0], t2 = e.touches[1];
        const rect = canvas.getBoundingClientRect();
        pinchStartDistRef.current = Math.hypot(t2.clientX - t1.clientX, t2.clientY - t1.clientY);
        pinchStartZoomRef.current = zoomRef.current;
        pinchMidStartRef.current = {
          x: (t1.clientX + t2.clientX) / 2 - rect.left,
          y: (t1.clientY + t2.clientY) / 2 - rect.top,
        };
        pinchPanStartRef.current = { ...panOffsetRef.current };
        isDraggingRef.current = false;
        hasDraggedRef.current = true;
      } else {
        isPinchingRef.current = false;
        const t = e.touches[0];
        dragStartRef.current = { x: t.clientX, y: t.clientY };
        dragStartPanRef.current = { ...panOffsetRef.current };
        isDraggingRef.current = true;
        hasDraggedRef.current = false;
        isRefocusingRef.current = false;
      }
    };

    const onTouchMove = (e) => {
      e.preventDefault();
      if (e.touches.length === 2 && isPinchingRef.current) {
        const t1 = e.touches[0], t2 = e.touches[1];
        const rect = canvas.getBoundingClientRect();
        const dist = Math.hypot(t2.clientX - t1.clientX, t2.clientY - t1.clientY);
        const newZoom = Math.max(MIN_ZOOM, Math.min(MAX_ZOOM,
          pinchStartZoomRef.current * (dist / pinchStartDistRef.current)));
        const midX = (t1.clientX + t2.clientX) / 2 - rect.left;
        const midY = (t1.clientY + t2.clientY) / 2 - rect.top;
        const cw = canvas.width, ch = canvas.height;
        const z0 = pinchStartZoomRef.current;
        const mx0 = pinchMidStartRef.current.x, my0 = pinchMidStartRef.current.y;
        panOffsetRef.current = {
          x: pinchPanStartRef.current.x + (mx0 - cw / 2) / z0 - (midX - cw / 2) / newZoom,
          y: pinchPanStartRef.current.y + (my0 - ch / 2) / z0 - (midY - ch / 2) / newZoom,
        };
        zoomRef.current = newZoom;
        hasDraggedRef.current = true;
        return;
      }
      if (!isDraggingRef.current) return;
      const t = e.touches[0];
      const dx = t.clientX - dragStartRef.current.x;
      const dy = t.clientY - dragStartRef.current.y;
      // Touch is less precise than a mouse; a higher threshold keeps a deliberate
      // combat tap from being swallowed as an accidental pan.
      if (Math.sqrt(dx * dx + dy * dy) > 10) hasDraggedRef.current = true;
      const z = zoomRef.current;
      panOffsetRef.current = {
        x: dragStartPanRef.current.x - dx / z,
        y: dragStartPanRef.current.y - dy / z,
      };
    };

    const onTouchEnd = (e) => {
      isDraggingRef.current = false;
      isPinchingRef.current = false;
      if (hasDraggedRef.current || e.changedTouches.length === 0) return;
      if (socketRef.current?.readyState !== WebSocket.OPEN) return;

      const t = e.changedTouches[0];
      const rect = canvas.getBoundingClientRect();
      const clickX = t.clientX - rect.left;
      const clickY = t.clientY - rect.top;
      const cw = canvas.width, ch = canvas.height;
      const z = zoomRef.current;
      const worldX = (clickX - cw / 2) / z + cameraLerpRef.current.x + cw / 2;
      const worldY = (clickY - ch / 2) / z + cameraLerpRef.current.y + ch / 2;
      const tileX = Math.floor(worldX / TILE_SIZE);
      const tileY = Math.floor(worldY / TILE_SIZE);

      // The canvas has touch-action:none so taps don't synthesize a click; resolve
      // targeting (THROW/ZAP aim) here instead of relying on the onClick handler.
      if (targetingModeRef.current) {
        onTargetTapRef?.current?.(tileX, tileY);
        return;
      }

      const myPlayer = entitiesRef?.current?.players?.[myPlayerIdRef?.current];
      const playerTile = myPlayer ? (myPlayer.targetPos || myPlayer.renderPos) : null;
      const action = resolveTapAction({ tileX, tileY, playerTile });
      if (action.type === 'MOVE_TO') isRefocusingRef.current = true;
      socketRef.current.send(JSON.stringify(action));
    };

    canvas.addEventListener('mousedown', onMouseDown);
    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('mouseup', onMouseUp);
    canvas.addEventListener('wheel', onWheel, { passive: false });
    canvas.addEventListener('touchstart', onTouchStart);
    canvas.addEventListener('touchmove', onTouchMove, { passive: false });
    canvas.addEventListener('touchend', onTouchEnd);

    return () => {
      canvas.removeEventListener('mousedown', onMouseDown);
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('mouseup', onMouseUp);
      canvas.removeEventListener('wheel', onWheel);
      canvas.removeEventListener('touchstart', onTouchStart);
      canvas.removeEventListener('touchmove', onTouchMove);
      canvas.removeEventListener('touchend', onTouchEnd);
    };
  }, [enabled, canvasRef, socketRef, panOffsetRef, zoomRef, cameraLerpRef, isDraggingRef, isRefocusingRef, isPinchingRef, targetingModeRef, onTargetTapRef, entitiesRef, myPlayerIdRef]);

  return { hasDraggedRef };
}
