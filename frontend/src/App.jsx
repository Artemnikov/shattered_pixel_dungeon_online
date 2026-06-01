import { useEffect, useRef, useState } from 'react';
import './App.css';

import CharacterSelection from './CharacterSelection';
import WelcomeScreen from './WelcomeScreen';

import { TILE_SIZE } from './constants';
import useAudioUnlock from './audio/useAudioUnlock';
import useMusicByDepth from './audio/useMusicByDepth';
import useAssetImages from './rendering/useAssetImages';
import useGameRenderer from './rendering/useGameRenderer';
import useGameSocket from './net/useGameSocket';
import useKeyboardControls from './input/useKeyboardControls';
import useCanvasControls from './input/useCanvasControls';
import useDebugApi from './dev/useDebugApi';

import HUD from './ui/HUD';
import Toolbar from './ui/Toolbar';
import InventoryModal from './ui/InventoryModal';
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
  const [viewport] = useState({ width: 800, height: 600 });
  const [showInventory, setShowInventory] = useState(false);
  const [inventory, setInventory] = useState([]);
  const [equippedItems, setEquippedItems] = useState({ weapon: null, wearable: null });
  const [targetingMode, setTargetingMode] = useState(false);
  const [myStats, setMyStats] = useState({ hp: 0, maxHp: 10, name: '' });
  const [depth, setDepth] = useState(1);
  const [, setCamera] = useState({ x: 0, y: 0 });

  // --- shared refs ---
  const canvasRef = useRef(null);
  const socketRef = useRef(null);
  const gridRef = useRef([]);
  const entitiesRef = useRef({ players: {}, mobs: {} });
  const myPlayerIdRef = useRef(null);
  const targetingModeRef = useRef(false);
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
  });

  const { hasDraggedRef } = useCanvasControls({
    enabled: gameState === 'PLAYING',
    canvasRef, socketRef,
    panOffsetRef, zoomRef, cameraLerpRef,
    isDraggingRef, isRefocusingRef, isPinchingRef,
    targetingModeRef,
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
  const triggerSearch = () => {
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({ type: 'SEARCH' }));
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
      const weaponId = typeof targetingModeRef.current === 'string' ? targetingModeRef.current : equippedItems.weapon?.id;
      if (weaponId) {
        socketRef.current.send(JSON.stringify({
          type: 'RANGED_ATTACK',
          item_id: weaponId,
          target_x: tileX,
          target_y: tileY,
        }));
        setTargetingMode(true);
      }
      return;
    }

    if (socketRef.current?.readyState === WebSocket.OPEN) {
      isRefocusingRef.current = true;
      socketRef.current.send(JSON.stringify({ type: 'MOVE_TO', x: tileX, y: tileY }));
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
      socketRef.current.send(JSON.stringify({
        type: 'RANGED_ATTACK',
        item_id: item.id,
        target_x: Math.round(nearestMob.renderPos.x),
        target_y: Math.round(nearestMob.renderPos.y),
      }));
    }
  };

  useKeyboardControls({
    socketRef, inventory, setShowInventory,
    handleToolbarClick, handleToolbarDoubleClick, triggerSearch,
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
    return <WelcomeScreen onStart={() => setGameState('SELECT')} />;
  }

  if (gameState === 'SELECT') {
    return <CharacterSelection onSelect={(c, d, n) => {
      setSelectedClass(c);
      setDifficulty(d);
      setPlayerName(n);
      setGameState('PLAYING');
    }} />;
  }

  const toolbarItems = Array.from({ length: 5 }).map((_, i) => inventory[i] || null);

  return (
    <div className="game-container">
      <LoadingOverlay visible={grid.length === 0} />

      <HUD myStats={myStats} depth={depth} onSearch={triggerSearch} />

      <div className="canvas-wrapper">
        <canvas
          ref={canvasRef}
          width={viewport.width}
          height={viewport.height}
          className={`game-canvas ${targetingMode ? 'cursor-crosshair' : ''}`}
          onClick={handleCanvasClick}
        />
      </div>

      <InventoryModal
        open={showInventory}
        inventory={inventory}
        onClose={() => setShowInventory(false)}
        onEquip={equipItem}
        onUse={useItem}
        onDrop={dropItem}
      />

      <div className="game-hud-bottom">
        <Toolbar
          items={toolbarItems}
          targetingMode={targetingMode}
          equippedItems={equippedItems}
          onSlotClick={handleToolbarClick}
          onSlotDoubleClick={handleToolbarDoubleClick}
          onOpenInventory={() => setShowInventory(true)}
        />
        <MessageLog messages={messages} />
      </div>

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
