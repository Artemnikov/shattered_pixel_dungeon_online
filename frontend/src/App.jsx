import { useEffect, useRef, useState } from 'react';
import './App.css';

import CharacterSelection from './CharacterSelection';
import MainMenu from './menu/MainMenu';

import { TILE_SIZE } from './constants';
import useAudioUnlock from './audio/useAudioUnlock';
import useMusicByDepth from './audio/useMusicByDepth';
import useAssetImages from './rendering/useAssetImages';
import useGameRenderer from './rendering/useGameRenderer';
import useGameSocket from './net/useGameSocket';
import useKeyboardControls from './input/useKeyboardControls';
import useCanvasControls from './input/useCanvasControls';
import { resolveTapAction } from './input/resolveTap';
import useDebugApi from './dev/useDebugApi';

import StatusPane from './ui/StatusPane';
import Toolbar from './ui/Toolbar';
import WndBag from './ui/WndBag';
import MessageLog from './ui/MessageLog';
import LoadingOverlay from './ui/LoadingOverlay';
import GameOverScreen from './ui/GameOverScreen';

function App() {
  // --- screen flow / session state ---
  const [gameState, setGameState] = useState('WELCOME');
  const [selectedClass, setSelectedClass] = useState('warrior');
  const [playerName, setPlayerName] = useState('');
  const [difficulty, setDifficulty] = useState('normal');
  const [gameId] = useState('default-lobby');

  // --- game state ---
  const [grid, setGrid] = useState([]);
  const [messages, setMessages] = useState([]);
  const [myPlayerId, setMyPlayerId] = useState(null);
  const [viewport, setViewport] = useState({ width: window.innerWidth, height: window.innerHeight });
  const [showInventory, setShowInventory] = useState(false);
  const [inventory, setInventory] = useState([]);
  const [equippedItems, setEquippedItems] = useState({ weapon: null, wearable: null });
  const [belongings, setBelongings] = useState(null);
  const [quickslot, setQuickslot] = useState(null);
  const [targetingMode, setTargetingMode] = useState(false);
  const [myStats, setMyStats] = useState({ hp: 0, maxHp: 10, name: '' });
  const [depth, setDepth] = useState(1);
  const [, setCamera] = useState({ x: 0, y: 0 });
  const getInitialInterfaceSize = () => {
    const w = window.innerWidth;
    const h = window.innerHeight;
    return (w > h && Math.min(w / 360, h / 200) >= 2) ? 2 : 0;
  };
  const [interfaceSize, setInterfaceSize] = useState(getInitialInterfaceSize());
  const [gold, setGold] = useState(0);
  const [energy, setEnergy] = useState(0);

  // --- shared refs ---
  const canvasRef = useRef(null);
  const socketRef = useRef(null);
  const gridRef = useRef([]);
  const entitiesRef = useRef({ players: {}, mobs: {} });
  const myPlayerIdRef = useRef(null);
  const targetingModeRef = useRef(false);
  // Latest targeting-tap resolver, shared with the touch handler (canvas has
  // touch-action:none, so taps don't fire onClick — see resolveTargetingTap).
  const onTargetTapRef = useRef(null);
  const projectilesRef = useRef([]);
  const visionRef = useRef({ visible: new Set(), discovered: new Set() });
  const openDoorsRef = useRef(new Set());
  const musicRef = useRef(null);
  const panOffsetRef = useRef({ x: 0, y: 0 });
  const cameraLerpRef = useRef({ x: 0, y: 0 });
  const zoomRef = useRef(1.0);
  const isDraggingRef = useRef(false);
  const isRefocusingRef = useRef(false);
  const isPinchingRef = useRef(false);
  const wasDownedRef = useRef(false);
  const mobAnimRef = useRef({});
  const dyingMobsRef = useRef({});
  const playerAnimRef = useRef({});
  const particlesRef = useRef([]);
  const floatingTextRef = useRef([]);
  const depthRef = useRef(1);

  useEffect(() => { targetingModeRef.current = targetingMode; }, [targetingMode]);
  useEffect(() => { depthRef.current = depth; }, [depth]);

  const wrapperRef = useRef(null);

  useEffect(() => {
    const wrapper = wrapperRef.current;
    if (!wrapper) return;
    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width, height } = entry.contentRect;
        setViewport({ width: Math.round(width), height: Math.round(height) });
      }
    });
    observer.observe(wrapper);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    const canFitFullUI = Math.min(viewport.width / 360, viewport.height / 200) >= 2;
    const detected = (viewport.width > viewport.height && canFitFullUI) ? 2 : 0;
    setInterfaceSize(detected);
  }, [viewport]);

  const [isFullscreen, setIsFullscreen] = useState(false);

  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen().catch(() => {});
    } else {
      document.exitFullscreen().catch(() => {});
    }
  };

  useEffect(() => {
    const handler = () => setIsFullscreen(!!document.fullscreenElement);
    document.addEventListener('fullscreenchange', handler);
    return () => document.removeEventListener('fullscreenchange', handler);
  }, []);

  useDebugApi({
    gridRef, entitiesRef, visionRef, openDoorsRef,
    myPlayerIdRef, panOffsetRef, cameraLerpRef, zoomRef, depthRef,
  });

  // --- infra hooks ---
  useAudioUnlock();
  const assetImages = useAssetImages();
  useMusicByDepth({ enabled: gameState === 'PLAYING', depth, musicRef });

  useGameSocket({
    enabled: gameState === 'PLAYING',
    gameId, selectedClass, difficulty, playerName,
    socketRef, gridRef, myPlayerIdRef, entitiesRef,
    visionRef, openDoorsRef, projectilesRef,
    mobAnimRef, dyingMobsRef, playerAnimRef, particlesRef, floatingTextRef, wasDownedRef,
    setGrid, setDepth, setMyPlayerId, setInventory,
    setEquippedItems, setMyStats, setMessages, setDifficulty,
    setGold, setEnergy, setBelongings, setQuickslot,
  });

  const { hasDraggedRef } = useCanvasControls({
    enabled: gameState === 'PLAYING',
    canvasRef, socketRef,
    panOffsetRef, zoomRef, cameraLerpRef,
    isDraggingRef, isRefocusingRef, isPinchingRef,
    targetingModeRef, onTargetTapRef,
    entitiesRef, myPlayerIdRef,
  });

  useGameRenderer({
    canvasRef, grid, myPlayerId, depth, assetImages,
    entitiesRef, visionRef, openDoorsRef, projectilesRef,
    mobAnimRef, dyingMobsRef, playerAnimRef, particlesRef, floatingTextRef, myPlayerIdRef,
    panOffsetRef, cameraLerpRef, zoomRef,
    isRefocusingRef, isDraggingRef,
    setCamera,
  });

  // --- send helpers ---
  const equipItem = (itemId) => {
    socketRef.current.send(JSON.stringify({ type: 'EQUIP_ITEM', item_id: itemId }));
  };
  const dropItem = (itemId) => {
    socketRef.current.send(JSON.stringify({ type: 'DROP_ITEM', item_id: itemId }));
  };
  const useItem = (itemId) => {
    socketRef.current.send(JSON.stringify({ type: 'USE_ITEM', item_id: itemId }));
  };

  // --- SPD-style generic item-action dispatch ---
  const TARGETED_ACTIONS = ['THROW', 'ZAP'];
  const send = (msg) => {
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify(msg));
    }
  };
  // Resolve a targeting-mode tap (THROW/ZAP aim, or a kept-armed ranged weapon)
  // against the tapped cell. Shared by the mouse onClick path and the touch path.
  const resolveTargetingTap = (tileX, tileY) => {
    const tm = targetingModeRef.current;
    // New SPD-style path: an item action awaiting a target cell.
    if (tm && typeof tm === 'object' && tm.action) {
      send({ type: 'EXECUTE_ITEM_ACTION', item_id: tm.itemId, action: tm.action, target_x: tileX, target_y: tileY });
      return;
    }
    // Legacy path: equipped ranged weapon kept armed for repeat fire.
    const weaponId = typeof tm === 'string' ? tm : equippedItems.weapon?.id;
    if (weaponId) {
      send({ type: 'RANGED_ATTACK', item_id: weaponId, target_x: tileX, target_y: tileY });
      setTargetingMode(true);
    }
  };
  useEffect(() => { onTargetTapRef.current = resolveTargetingTap; });

  const executeItemAction = (itemId, action, tx, ty) => {
    if (TARGETED_ACTIONS.includes(action) && tx === undefined) {
      // Needs a target cell: enter targeting, resolve on the next canvas click.
      setTargetingMode({ itemId, action });
      setShowInventory(false);
      return;
    }
    send({ type: 'EXECUTE_ITEM_ACTION', item_id: itemId, action, target_x: tx, target_y: ty });
  };
  const assignQuickslot = (itemId) => {
    const slots = quickslot?.slots || [];
    let idx = slots.findIndex(s => !s.item_id);
    if (idx < 0) idx = 0;
    send({ type: 'SET_QUICKSLOT', index: idx, item_id: itemId });
  };
  const useQuickslotSlot = (index, item) => {
    const action = item?.default_action;
    if (action && TARGETED_ACTIONS.includes(action)) {
      setTargetingMode({ itemId: item.id, action });
      return;
    }
    send({ type: 'USE_QUICKSLOT', index });
  };

  // Flatten belongings into an id->item map for quickslot resolution.
  const itemsById = {};
  if (belongings) {
    ['weapon', 'armor', 'artifact', 'misc', 'ring'].forEach(k => {
      if (belongings[k]) itemsById[belongings[k].id] = belongings[k];
    });
    const walk = (bag) => {
      (bag?.items || []).forEach(it => {
        itemsById[it.id] = it;
        if (it.items) walk(it);
      });
    };
    walk(belongings.backpack);
  }
  const triggerSearch = () => {
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({ type: 'SEARCH' }));
    }
  };

  const triggerWait = () => {
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({ type: 'WAIT' }));
    }
  };

  // --- interaction handlers (touch multiple states → keep here) ---
  const handleCanvasClick = (e) => {
    if (hasDraggedRef.current) return;
    if (!canvasRef.current) return;

    const rect = canvasRef.current.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const clickY = e.clientY - rect.top;

    const cw = canvasRef.current.width, ch = canvasRef.current.height;
    const z = zoomRef.current;
    const worldX = (clickX - cw / 2) / z + cameraLerpRef.current.x + cw / 2;
    const worldY = (clickY - ch / 2) / z + cameraLerpRef.current.y + ch / 2;

    const tileX = Math.floor(worldX / TILE_SIZE);
    const tileY = Math.floor(worldY / TILE_SIZE);

    if (targetingModeRef.current) {
      resolveTargetingTap(tileX, tileY);
      return;
    }

    if (socketRef.current?.readyState === WebSocket.OPEN) {
      const myPlayer = entitiesRef.current.players[myPlayerIdRef.current];
      const playerTile = myPlayer ? (myPlayer.targetPos || myPlayer.renderPos) : null;
      const action = resolveTapAction({ tileX, tileY, playerTile });
      if (action.type === 'MOVE_TO') isRefocusingRef.current = true;
      socketRef.current.send(JSON.stringify(action));
    }
  };

  const handleToolbarClick = (item) => {
    if (!item) {
      setShowInventory(true);
      return;
    }
    if (item.type === 'potion') {
      useItem(item.id);
      return;
    }
    if (item.type === 'weapon') {
      const isEquipped = equippedItems.weapon && equippedItems.weapon.id === item.id;

      if (!isEquipped) {
        equipItem(item.id);
        if (item.range && item.range > 1) {
          setTargetingMode(item.id);
        } else {
          setTargetingMode(false);
        }
      } else if (item.range && item.range > 1) {
        setTargetingMode(prev => !prev);
      }
    } else if (item.type === 'wearable') {
      equipItem(item.id);
    } else if (item.type === 'throwable') {
      if (targetingMode === item.id) {
        setTargetingMode(false);
      } else {
        setTargetingMode(item.id);
      }
    }
  };

  const handleToolbarDoubleClick = (item) => {
    const isRangedWeapon = item && item.type === 'weapon' && item.range && item.range > 1;
    const isThrowable = item && item.type === 'throwable';
    if (!isRangedWeapon && !isThrowable) return;

    const myPlayer = entitiesRef.current.players[myPlayerIdRef.current];
    if (!myPlayer) return;

    let nearestMob = null;
    let minDist = item.range + 1;

    Object.values(entitiesRef.current.mobs).forEach(mob => {
      if (!visionRef.current.visible.has(`${Math.round(mob.renderPos.x)},${Math.round(mob.renderPos.y)}`)) return;
      const dx = mob.renderPos.x - myPlayer.renderPos.x;
      const dy = mob.renderPos.y - myPlayer.renderPos.y;
      const dist = Math.sqrt(dx * dx + dy * dy);
      if (dist <= item.range && dist < minDist) {
        minDist = dist;
        nearestMob = mob;
      }
    });

    if (nearestMob) {
      const tx = Math.round(nearestMob.renderPos.x);
      const ty = Math.round(nearestMob.renderPos.y);
      // Throwables fire via the generic THROW action; equipped ranged weapons use RANGED_ATTACK.
      if (isThrowable) {
        send({ type: 'EXECUTE_ITEM_ACTION', item_id: item.id, action: 'THROW', target_x: tx, target_y: ty });
      } else {
        send({ type: 'RANGED_ATTACK', item_id: item.id, target_x: tx, target_y: ty });
      }
    }
  };

  useKeyboardControls({
    socketRef, inventory, setShowInventory,
    handleToolbarClick, handleToolbarDoubleClick,
    triggerSearch, triggerWait,
    isRefocusingRef, isDraggingRef,
  });

  // Reset transient game state on death so a fresh run starts clean (no stale
  // corpse, dim overlay, or game-over flag carried over from the previous run).
  const resetForRestart = () => {
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.close();
    }
    entitiesRef.current = { players: {}, mobs: {} };
    visionRef.current = { visible: new Set(), discovered: new Set() };
    myPlayerIdRef.current = null;
    wasDownedRef.current = false;
    setMyPlayerId(null);
    setGrid([]);
    setMyStats({ hp: 0, maxHp: 10, name: '' });
    setInventory([]);
  };

  // --- screen flow ---
  if (gameState === 'WELCOME') {
    return <MainMenu onStart={() => setGameState('SELECT')} />;
  }

  if (gameState === 'SELECT') {
    return <CharacterSelection onSelect={(c, d, n) => {
      setSelectedClass(c);
      setDifficulty(d);
      setPlayerName(n);
      setGameState('PLAYING');
    }} />;
  }

  // Toolbar quickslots mirror the real quickslot state (as in the original game),
  // resolving each slot's item id against the flattened belongings.
  const toolbarItems = Array.from({ length: 6 }).map((_, i) => {
    const slot = quickslot?.slots?.[i];
    return slot && slot.item_id ? (itemsById[slot.item_id] || null) : null;
  });

  return (
    <div className="game-container">
      <LoadingOverlay visible={grid.length === 0} />

      <StatusPane myStats={myStats} depth={depth} onSearch={triggerSearch} />

      <div className="canvas-wrapper" ref={wrapperRef}>
        <canvas
          ref={canvasRef}
          width={viewport.width}
          height={viewport.height}
          className={`game-canvas ${targetingMode ? 'cursor-crosshair' : ''}`}
          onClick={handleCanvasClick}
        />
      </div>

      {/* Bottom-centered HUD: message log, then toolbar, then the inventory
          pane below it (toggled open/closed with 'f' or the bag button). */}
      <div className="hud-bottom">
        <MessageLog messages={messages} />
        <Toolbar
          mode={interfaceSize > 0 ? 'group' : 'split'}
          interfaceSize={interfaceSize}
          flipToolbar={false}
          quickSwapper={false}
          canvasWidth={viewport.width}
          items={toolbarItems}
          equippedItems={equippedItems}
          targetingMode={targetingMode}
          onWait={triggerWait}
          onSearch={triggerSearch}
          onInventory={() => setShowInventory(v => !v)}
          onSlotClick={handleToolbarClick}
          onSlotDoubleClick={handleToolbarDoubleClick}
        />
        {showInventory && (
          <WndBag
            belongings={belongings}
            onAction={executeItemAction}
            onAssignQuickslot={assignQuickslot}
          />
        )}
      </div>

      <button className="fullscreen-btn" onClick={toggleFullscreen} title={isFullscreen ? 'Exit fullscreen' : 'Fullscreen'}>
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          {isFullscreen ? (
            <path d="M8 3v3a2 2 0 0 1-2 2H3m18 0h-3a2 2 0 0 1-2-2V3m0 18v-3a2 2 0 0 1 2-2h3M3 16h3a2 2 0 0 1 2 2v3" />
          ) : (
            <path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3" />
          )}
        </svg>
      </button>

      {!!myStats.isDowned && (
        <GameOverScreen
          onNewGame={() => { resetForRestart(); setGameState('SELECT'); }}
          onMenu={() => { resetForRestart(); setGameState('WELCOME'); }}
        />
      )}
    </div>
  );
}

export default App;
