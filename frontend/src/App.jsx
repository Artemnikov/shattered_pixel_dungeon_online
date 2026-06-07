import { useEffect, useRef, useState } from 'react';
import './App.css';

import CharacterSelection from './CharacterSelection';
import MainMenu from './menu/MainMenu';
import cursorMouseUrl from './assets/cursors/cursor_mouse.png';
import cursorControllerUrl from './assets/cursors/cursor_controller.png';

import { TILE_SIZE } from './constants';
import useAudioUnlock from './audio/useAudioUnlock';
import AudioManager from './audio/AudioManager';
import useMusicByDepth from './audio/useMusicByDepth';
import useAssetImages from './rendering/useAssetImages';
import useGameRenderer from './rendering/useGameRenderer';
import useGameSocket from './net/useGameSocket';
import useKeyboardControls from './input/useKeyboardControls';
import useCanvasControls from './input/useCanvasControls';
import { resolveTapAction } from './input/resolveTap';
import { describeCell } from './input/describeCell';
import useDebugApi from './dev/useDebugApi';
import { getApiBaseUrl } from './config/urls';

import StatusPane from './ui/StatusPane';
import BossHealthBar from './ui/BossHealthBar';
import Toolbar from './ui/Toolbar';
import InventoryPane from './ui/InventoryPane';
import WndBag from './ui/WndBag';
import WndQuickBag from './ui/WndQuickBag';
import RadialMenu from './ui/RadialMenu';
import WndUseItem from './ui/WndUseItem';
import RightClickMenu from './ui/RightClickMenu';
import LoadingOverlay from './ui/LoadingOverlay';
import GameOverScreen from './ui/GameOverScreen';
import GameMenu from './ui/GameMenu';
import TalentPane from './ui/TalentPane';
import SubclassChoice from './ui/SubclassChoice';
import ArmorAbilityChoice from './ui/ArmorAbilityChoice';
import AbilityButton from './ui/AbilityButton';
import BerserkButton from './ui/BerserkButton';
import PrepStrikeButton from './ui/PrepStrikeButton';
import WndOptions from './ui/WndOptions';
import ComboDisplay from './ui/ComboDisplay';
import LevelUpBanner from './ui/LevelUpBanner';

// Live viewport position of an inspect-popup anchor (a world tile, or a mob we follow
// by its renderPos). Returns { left, top, below } or null when the popup should hide
// (mob gone/out of view, or the anchor panned off the visible canvas). Pure so it can
// be called from the per-frame rAF loop without reading refs during render.
function inspectScreenPos(canvas, cam, zoom, anchor, mobs, visible) {
  if (!canvas || !anchor) return null;
  let wx, wyTop, wyBottom;
  if (anchor.type === 'mob') {
    const mob = mobs[anchor.id];
    if (!mob) return null;
    const mx = Math.round(mob.renderPos.x), my = Math.round(mob.renderPos.y);
    if (!visible.has(`${mx},${my}`)) return null;
    wx = (mob.renderPos.x + 0.5) * TILE_SIZE;
    wyTop = mob.renderPos.y * TILE_SIZE;
    wyBottom = (mob.renderPos.y + 1) * TILE_SIZE;
  } else {
    wx = (anchor.x + 0.5) * TILE_SIZE;
    wyTop = anchor.y * TILE_SIZE;
    wyBottom = (anchor.y + 1) * TILE_SIZE;
  }
  const rect = canvas.getBoundingClientRect();
  const cw = canvas.width, ch = canvas.height;
  const left = rect.left + (wx - cam.x - cw / 2) * zoom + cw / 2;
  const topY = rect.top + (wyTop - cam.y - ch / 2) * zoom + ch / 2;
  const bottomY = rect.top + (wyBottom - cam.y - ch / 2) * zoom + ch / 2;
  // Hide once the anchor is panned off the visible canvas.
  if (left < rect.left || left > rect.right || bottomY < rect.top || topY > rect.bottom) return null;
  const below = topY < rect.top + 70;
  return { left, top: below ? bottomY + 6 : topY - 6, below };
}

function App() {
  // --- screen flow / session state ---
  const [gameState, setGameState] = useState('WELCOME');
  const [selectedClass, setSelectedClass] = useState('warrior');
  const [playerName, setPlayerName] = useState('');
  const [difficulty, setDifficulty] = useState('normal');
  const [gameId] = useState('default-lobby');
  // Stable per-run identity so a dropped socket can reconnect to the same hero.
  // A fresh id is minted when a new run starts (see startGame); persisted so a
  // page reload mid-run could resume the same session server-side.
  const [sessionId, setSessionId] = useState(
    () => sessionStorage.getItem('opd_session') || ''
  );
  // 'connected' | 'reconnecting' | null — drives the reconnect banner.
  const [connectionStatus, setConnectionStatus] = useState(null);

  // --- game state ---
  const [grid, setGrid] = useState([]);
  const [myPlayerId, setMyPlayerId] = useState(null);
  const [viewport, setViewport] = useState({ width: window.innerWidth, height: window.innerHeight });
  const [showInventory, setShowInventory] = useState(false);
  // Open info+actions popup (item) and right-click context menu ({item,x,y}).
  const [useItemTarget, setUseItemTarget] = useState(null);
  const [ctxMenu, setCtxMenu] = useState(null);
  const [inventory, setInventory] = useState([]);
  const [equippedItems, setEquippedItems] = useState({ weapon: null, wearable: null });
  const [belongings, setBelongings] = useState(null);
  const [quickslot, setQuickslot] = useState(null);
  const [targetingMode, setTargetingMode] = useState(false);
  // Examine mode: 1st search trigger arms it (click a cell to inspect), 2nd trigger
  // performs the reveal. Mirrors the original's btnSearch examine→search two-step.
  const [examineMode, setExamineMode] = useState(false);
  // Inspect popup: { name, sub, left, top, below } positioned over the inspected cell.
  const [inspectInfo, setInspectInfo] = useState(null);
  const [myStats, setMyStats] = useState({ hp: 0, maxHp: 10, name: '' });
  const [bossInfo, setBossInfo] = useState(null);
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
  const [showQuickBag, setShowQuickBag] = useState(false);
  const [radialOpen, setRadialOpen] = useState(false);
  const [swappedQuickslots, setSwappedQuickslots] = useState(false);
  const [gameMenuOpen, setGameMenuOpen] = useState(false);
  const [showTalentPane, setShowTalentPane] = useState(false);
  const [talentDefs, setTalentDefs] = useState(null);
  const [talentDefsLoading, setTalentDefsLoading] = useState(false);
  const [talentDefsError, setTalentDefsError] = useState(null);
  const [talentPoints, setTalentPoints] = useState({});
  const [showSubclassChoice, setShowSubclassChoice] = useState(false);
  const [subclassOptions, setSubclassOptions] = useState([]);
  const [showArmorAbilityChoice, setShowArmorAbilityChoice] = useState(false);
  const [armorAbilityOptions, setArmorAbilityOptions] = useState([]);
  const [showLevelUpBanner, setShowLevelUpBanner] = useState(false);
  const [levelUpData, setLevelUpData] = useState({});
  const [upgradedTalentId, setUpgradedTalentId] = useState(null);
  const [showMetamorphMode, setShowMetamorphMode] = useState(false);
  const [metamorphOldTalent, setMetamorphOldTalent] = useState(null);
  const [metamorphOptions, setMetamorphOptions] = useState(null);

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
  const onOpenTalentsRef = useRef(() => setShowTalentPane(v => !v));
  useEffect(() => { onOpenTalentsRef.current = () => setShowTalentPane(v => !v); }, []);
  // Examine-mode state + tap resolver, shared with the touch handler (same pattern
  // as targeting, since the canvas has touch-action:none so taps don't fire onClick).
  const examineModeRef = useRef(false);
  const onExamineTapRef = useRef(null);
  const inspectPopupRef = useRef(null);
  const inspectSubRef = useRef(null);
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
  const searchEffectsRef = useRef([]);
  // Boss ability telegraphs (e.g. Goo's pumped-up charge): { tiles: [[x,y],...], untilMs }.
  // Cleared by an empty-tiles GOO_CHARGE event when the charge releases or cancels.
  const warnedTilesRef = useRef(null);
  const floatingTextRef = useRef([]);
  const trapsRef = useRef([]);
  const depthRef = useRef(1);
  const gameMenuOpenRef = useRef(false);

  useEffect(() => { targetingModeRef.current = targetingMode; }, [targetingMode]);
  useEffect(() => { examineModeRef.current = examineMode; }, [examineMode]);
  useEffect(() => { depthRef.current = depth; }, [depth]);
  useEffect(() => { gameMenuOpenRef.current = gameMenuOpen; }, [gameMenuOpen]);

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

  // Sync talentPoints from myStats (updated every STATE_UPDATE)
  useEffect(() => {
    if (myStats.talentPoints) setTalentPoints(myStats.talentPoints);
  }, [myStats.talentPoints]);

  // Fetch talent definitions when class or game state changes
  useEffect(() => {
    if (gameState !== 'PLAYING') return;
    const classType = myStats.classType || selectedClass;
    setTalentDefsLoading(true);
    setTalentDefsError(null);
    fetch(`${getApiBaseUrl()}/api/talents/${classType}`)
      .then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then(data => {
        setTalentDefs(data);
        setTalentDefsLoading(false);
      })
      .catch(e => {
        setTalentDefsError(e.message);
        setTalentDefsLoading(false);
      });
  }, [gameState, selectedClass, myStats.classType]);

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
    gameId, sessionId, selectedClass, difficulty, playerName,
    setConnectionStatus,
    socketRef, gridRef, myPlayerIdRef, entitiesRef,
    visionRef, openDoorsRef, projectilesRef,
    trapsRef,
    mobAnimRef, dyingMobsRef, playerAnimRef, particlesRef, searchEffectsRef, floatingTextRef, wasDownedRef, warnedTilesRef,
    setGrid, setDepth, setMyPlayerId, setInventory,
    setEquippedItems, setMyStats, setDifficulty, setBossInfo,
    setGold, setEnergy, setBelongings, setQuickslot,
    onLevelUp: (data) => {
      if (data.talent_points) setTalentPoints(data.talent_points);
      setLevelUpData(data);
      setShowLevelUpBanner(true);
    },
    onSubclassChoiceAvailable: (data) => {
      setSubclassOptions(data.options);
      setShowSubclassChoice(true);
    },
    onArmorAbilityChoiceAvailable: (data) => {
      setArmorAbilityOptions(data.options);
      setShowArmorAbilityChoice(true);
    },
    onMetamorphOpen: () => {
      setShowTalentPane(true);
      setShowMetamorphMode(true);
    },
    onMetamorphOptions: ({ old_talent, options }) => {
      setMetamorphOldTalent(old_talent);
      setMetamorphOptions(options);
    },
    onTalentUpgraded: ({ talent }) => {
      if (!talentDefs) return;
      for (const [tierKey, tierData] of Object.entries(talentDefs.tiers)) {
        if (tierData.talents.some(tt => tt.id === talent)) {
          setTalentPoints(prev => ({
            ...prev,
            [tierKey]: Math.max(0, (prev[tierKey] || 0) - 1),
          }));
          setUpgradedTalentId(talent);
          AudioManager.play('LEVELUP', 1.2);
          return;
        }
      }
    },
  });

  const { hasDraggedRef } = useCanvasControls({
    enabled: gameState === 'PLAYING',
    canvasRef, socketRef,
    panOffsetRef, zoomRef, cameraLerpRef,
    isDraggingRef, isRefocusingRef, isPinchingRef,
    targetingModeRef, onTargetTapRef,
    examineModeRef, onExamineTapRef,
    entitiesRef, myPlayerIdRef,
  });

  useGameRenderer({
    canvasRef, grid, myPlayerId, depth, assetImages,
    entitiesRef, visionRef, openDoorsRef, projectilesRef,
    trapsRef,
    mobAnimRef, dyingMobsRef, playerAnimRef, particlesRef, searchEffectsRef, floatingTextRef, myPlayerIdRef, warnedTilesRef,
    panOffsetRef, cameraLerpRef, zoomRef,
    isRefocusingRef, isDraggingRef,
    setCamera,
  });

  // --- send helpers ---
  // Drop (don't throw) sends while the socket is closed/reconnecting.
  const sendMessage = (msg) => {
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify(msg));
    }
  };
  const equipItem = (itemId) => sendMessage({ type: 'EQUIP_ITEM', item_id: itemId });
  const dropItem = (itemId) => sendMessage({ type: 'DROP_ITEM', item_id: itemId });
  const useItem = (itemId) => sendMessage({ type: 'USE_ITEM', item_id: itemId });

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
    console.log('resolveTargetingTap', { tm, tileX, tileY });
    // Ability targeting
    if (tm && typeof tm === 'object' && tm.ability) {
      send({ type: 'USE_ARMOR_ABILITY', ability: tm.ability, target_x: tileX, target_y: tileY });
      setTargetingMode(false);
      return;
    }
    // Preparation strike targeting
    if (tm && typeof tm === 'object' && tm.prepStrike) {
      send({ type: 'PREPARATION_STRIKE', target_x: tileX, target_y: tileY });
      setTargetingMode(false);
      return;
    }
    // New SPD-style path: an item action awaiting a target cell.
    if (tm && typeof tm === 'object' && tm.action) {
      console.log('Sending EXECUTE_ITEM_ACTION', { item_id: tm.itemId, action: tm.action, target_x: tileX, target_y: tileY });
      send({ type: 'EXECUTE_ITEM_ACTION', item_id: tm.itemId, action: tm.action, target_x: tileX, target_y: tileY });
      setTargetingMode(false);
      return;
    }
    // Legacy path: equipped ranged weapon kept armed for repeat fire.
    const weaponId = typeof tm === 'string' ? tm : equippedItems.weapon?.id;
    if (weaponId) {
      send({ type: 'RANGED_ATTACK', item_id: weaponId, target_x: tileX, target_y: tileY });
      // Keep armed for repeat fire only when already in "always armed" mode (tm===true),
      // not when a single action was selected from toolbar (tm is a string item ID).
      setTargetingMode(typeof tm === 'string' ? false : true);
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

  const TARGETED_ABILITIES = ['heroic_leap', 'smoke_bomb', 'death_mark'];

  const sendUseAbility = (ability) => {
    if (TARGETED_ABILITIES.includes(ability)) {
      setTargetingMode({ ability });
      return;
    }
    send({ type: 'USE_ARMOR_ABILITY', ability });
  };

  const sendTriggerBerserk = () => {
    send({ type: 'TRIGGER_BERSERK' });
  };

  const sendPrepStrike = () => {
    setTargetingMode({ prepStrike: true });
  };
  const handleQuickBag = () => setShowQuickBag(true);
  const handleSwap = () => setSwappedQuickslots(v => !v);
  const handleRadialSelect = () => setRadialOpen(true);

  const assignQuickslot = (itemId) => {
    const slots = quickslot?.slots || [];
    let idx = slots.findIndex(s => !s.item_id);
    if (idx < 0) idx = 0;
    send({ type: 'SET_QUICKSLOT', index: idx, item_id: itemId });
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

  // Magnifying-glass / E / Search button: 1st trigger arms examine mode, 2nd performs
  // the reveal. (In examine mode, tapping a cell inspects it and exits — see
  // resolveExamineTap.) Mirrors the original Toolbar.btnSearch examine→search two-step.
  const clearInspect = () => {
    setInspectInfo(null);
  };

  const handleExamineOrReveal = () => {
    clearInspect();
    if (examineModeRef.current) {
      setExamineMode(false);
      triggerSearch();
    } else {
      setTargetingMode(false);
      setExamineMode(true);
    }
  };

  const sendUpgradeTalent = (talent) => send({ type: 'UPGRADE_TALENT', talent });
  const sendMetamorphChoose = (talent) => send({ type: 'METAMORPH_CHOOSE', talent });
  const sendMetamorphReplace = (oldTalent, newTalent) => send({ type: 'METAMORPH_REPLACE', old_talent: oldTalent, new_talent: newTalent });
  const handleChooseSubclass = (subclass) => {
    send({ type: 'CHOOSE_SUBCLASS', subclass });
    setShowTalentPane(false);
  };
  const handleChooseArmorAbility = (abilityTalentId) => {
    sendUpgradeTalent(abilityTalentId);
    setShowTalentPane(false);
  };

  const handleEscape = () => {
    if (examineModeRef.current || targetingModeRef.current) {
      setExamineMode(false);
      setTargetingMode(false);
      clearInspect();
    } else if (showSubclassChoice) {
      setShowSubclassChoice(false);
    } else if (showArmorAbilityChoice) {
      setShowArmorAbilityChoice(false);
    } else if (showTalentPane) {
      setShowTalentPane(false);
    } else if (!gameMenuOpenRef.current) {
      setGameMenuOpen(true);
    }
  };

  // Examine-mode tap: open a small popup naming whatever is in the cell, anchored to it
  // (the live screen position is recomputed each frame by computeInspectPos so it sticks
  // to the tile/mob as the camera or that mob moves), then leave examine mode.
  const resolveExamineTap = (tileX, tileY) => {
    const info = describeCell({
      tileX, tileY, gridRef, entitiesRef, visionRef,
      myPlayerId: myPlayerIdRef.current,
    });
    setExamineMode(false);
    if (!info) { clearInspect(); return; }
    setInspectInfo({ name: info.name, sub: info.sub, anchor: info.anchor });
  };
  useEffect(() => { onExamineTapRef.current = resolveExamineTap; });

  // While a popup is open, drive it every frame: reposition from the live camera + anchor
  // (so it sticks to its tile/mob), refresh a mob's HP, and handle auto-dismiss. Done in a
  // rAF (not render) so we don't read refs during render. Dismissal is timestamp-based:
  // the popup stays alive for DISMISS_MS after the last "activity" — for a mob that's its
  // last HP change, so you can watch a fight and it fades 3s after the final hit; for a
  // tile it's the inspect itself (fixed 3s). A vanished mob dismisses immediately.
  useEffect(() => {
    if (!inspectInfo) return;
    const anchor = inspectInfo.anchor;
    const DISMISS_MS = 3000;
    let raf;
    let lastSub;
    let lastActive = performance.now();
    const tick = () => {
      const now = performance.now();

      // Resolve the live secondary line (a mob's current HP), and bump the activity
      // timestamp whenever it changes so active combat keeps the popup on screen.
      let sub = inspectInfo.sub;
      if (anchor.type === 'mob') {
        const mob = entitiesRef.current.mobs[anchor.id];
        if (!mob) { setInspectInfo(null); return; } // mob gone (killed/despawned)
        sub = mob.hp != null && mob.max_hp != null ? `HP ${mob.hp}/${mob.max_hp}` : null;
      }
      if (sub !== lastSub) { lastSub = sub; lastActive = now; }
      if (now - lastActive > DISMISS_MS) { setInspectInfo(null); return; }

      const el = inspectPopupRef.current;
      if (el) {
        const pos = inspectScreenPos(
          canvasRef.current, cameraLerpRef.current, zoomRef.current,
          anchor, entitiesRef.current.mobs, visionRef.current.visible,
        );
        if (pos) {
          el.style.display = '';
          el.style.left = `${pos.left}px`;
          el.style.top = `${pos.top}px`;
          el.style.transform = pos.below ? 'translate(-50%, 0)' : 'translate(-50%, -100%)';
          const subEl = inspectSubRef.current;
          if (subEl) {
            subEl.textContent = sub || '';
            subEl.style.display = sub ? '' : 'none';
          }
        } else {
          el.style.display = 'none';
        }
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [inspectInfo]);

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

    if (examineModeRef.current) {
      resolveExamineTap(tileX, tileY);
      return;
    }

    // Any non-examine tap dismisses a lingering inspect popup.
    clearInspect();

    if (targetingModeRef.current) {
      resolveTargetingTap(tileX, tileY);
      return;
    }

    if (socketRef.current?.readyState === WebSocket.OPEN) {
      const myPlayer = entitiesRef.current.players[myPlayerIdRef.current];
      const playerTile = myPlayer ? (myPlayer.targetPos || myPlayer.renderPos) : null;
      const action = resolveTapAction({ tileX, tileY, playerTile });
      if (action.type === 'MOVE_TO' || action.type === 'MOVE') isRefocusingRef.current = true;
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
      if (targetingMode && typeof targetingMode === 'object' && targetingMode.itemId === item.id) {
        setTargetingMode(false);
      } else {
        setTargetingMode({ itemId: item.id, action: 'THROW' });
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
    onExamineOrReveal: handleExamineOrReveal, onCancelModes: handleEscape,
    triggerWait,
    isRefocusingRef, isDraggingRef,
    quickslot, itemsById,
    onRadialSelect: handleRadialSelect,
    gameMenuOpenRef,
    onOpenTalents: () => setShowTalentPane(v => !v),
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
    setBossInfo(null);
    setInventory([]);
    setConnectionStatus(null);
    setShowMetamorphMode(false);
    setMetamorphOptions(null);
    setMetamorphOldTalent(null);
  };

  const handleLeaveGame = () => {
    resetForRestart();
    setGameMenuOpen(false);
    setGameState('WELCOME');
  };

  const isDesktop = interfaceSize > 0;

  // --- screen flow ---
  if (gameState === 'WELCOME') {
    return (
      <>
        <title>SPD Online — Play Shattered Pixel Dungeon in your browser</title>
        <meta name="description" content="Play the roguelike dungeon crawler Shattered Pixel Dungeon online, for free in your browser. Multiplayer real-time, no download required." />
        <div className={isDesktop ? 'desktop-mode' : ''}
             style={isDesktop ? { '--cursor-mouse': `url(${cursorMouseUrl}) 1 1, pointer` } : {}}>
          <MainMenu onStart={() => setGameState('SELECT')} />
        </div>
      </>
    );
  }

  if (gameState === 'SELECT') {
    return (
      <>
        <title>SPD Online — Choose your class</title>
        <meta name="description" content="Select your hero class — Warrior, Mage, Rogue, or Archer — and descend into the dungeon." />
        <div className={isDesktop ? 'desktop-mode' : ''}
             style={isDesktop ? { '--cursor-mouse': `url(${cursorMouseUrl}) 1 1, pointer` } : {}}>
          <CharacterSelection onSelect={(c, d, n) => {
            setSelectedClass(c);
            setDifficulty(d);
            setPlayerName(n);
            // Fresh identity for the new run so we spawn a new hero rather than
            // rebinding to a previous (possibly dead) one.
            const newSession = crypto.randomUUID();
            sessionStorage.setItem('opd_session', newSession);
            setSessionId(newSession);
            setGameState('PLAYING');
          }} />
        </div>
      </>
    );
  }
  const cursorStyle = (targetingMode || examineMode)
    ? isDesktop
      ? `url(${cursorControllerUrl}) 8 8, crosshair`
      : 'crosshair'
    : isDesktop
      ? `url(${cursorMouseUrl}) 1 1, auto`
      : 'default';

  // Toolbar quickslots mirror the real quickslot state (as in the original game),
  // resolving each slot's item id against the flattened belongings.
  const toolbarItems = Array.from({ length: 6 }).map((_, i) => {
    const slot = quickslot?.slots?.[i];
    return slot && slot.item_id ? (itemsById[slot.item_id] || null) : null;
  });

  return (
    <>
      <title>SPD Online — Floor {depth}</title>
      <meta name="description" content={`Playing SPD Online — exploring floor ${depth} of the dungeon.`} />
      <div className={`game-container ${isDesktop ? 'desktop-mode' : ''}`}
           style={isDesktop ? { '--cursor-mouse': `url(${cursorMouseUrl}) 1 1, pointer` } : {}}>
      <LoadingOverlay visible={grid.length === 0} />

      {connectionStatus === 'reconnecting' && (
        <div className="reconnect-banner" role="status">
          Connection lost — reconnecting…
        </div>
      )}

      <BossHealthBar boss={bossInfo} />

      <StatusPane
        myStats={myStats}
        depth={depth}
        isAdmin={myStats.isAdmin}
        onSearch={handleExamineOrReveal}
        hasTalentPoints={Object.values(talentPoints || {}).some(p => p > 0)}
        onOpenTalents={() => setShowTalentPane(v => !v)}
        onTeleport={(floor) => sendMessage({ type: 'ADMIN_TELEPORT', target_floor: floor })}
      />

      <div className="canvas-wrapper" ref={wrapperRef}>
        <canvas
          ref={canvasRef}
          width={viewport.width}
          height={viewport.height}
          className="game-canvas"
          style={{ cursor: cursorStyle }}
          onClick={handleCanvasClick}
        />
      </div>

      {inspectInfo && (
        <div
          ref={inspectPopupRef}
          className="inspect-popup"
          style={{
            position: 'fixed',
            left: 0,
            top: 0,
            display: 'none',
            transform: 'translate(-50%, -100%)',
            background: 'rgba(0, 0, 0, 0.85)',
            border: '1px solid #6a6a6a',
            borderRadius: 3,
            padding: '3px 7px',
            color: '#ffffff',
            font: '11px monospace',
            lineHeight: 1.25,
            whiteSpace: 'nowrap',
            textAlign: 'center',
            pointerEvents: 'none',
            zIndex: 60,
          }}
        >
          <div style={{ fontWeight: 'bold' }}>{inspectInfo.name}</div>
          {/* Uncontrolled (no React child) so the rAF loop can update the live HP text
              without React clobbering it on the next per-frame re-render. */}
          <div ref={inspectSubRef} style={{ color: '#bdbdbd', display: 'none' }} />
        </div>
      )}

      {/* Bottom-right HUD: toolbar, then the inventory pane below it
          (toggled open/closed with 'f' or the bag button). */}
      <div className="hud-bottom">
        <Toolbar
          mode={interfaceSize > 0 ? 'group' : 'split'}
          interfaceSize={interfaceSize}
          flipToolbar={false}
          quickSwapper={!isDesktop}
          canvasWidth={viewport.width}
          items={toolbarItems}
          equippedItems={equippedItems}
          targetingMode={targetingMode}
          swappedQuickslots={swappedQuickslots}
          onWait={triggerWait}
          onSearch={handleExamineOrReveal}
          onInventory={() => setShowInventory(v => !v)}
          onQuickBag={handleQuickBag}
          onSlotClick={handleToolbarClick}
          onSlotDoubleClick={handleToolbarDoubleClick}
          onSwap={handleSwap}
        />
        <AbilityButton
          armorAbility={myStats.armorAbility || null}
          armorCharge={myStats.armorCharge || 0}
          onUseAbility={sendUseAbility}
        />
        <BerserkButton
          berserkPower={myStats.berserkPower || 0}
          onTriggerBerserk={sendTriggerBerserk}
        />
        <PrepStrikeButton
          subclass={myStats.subclass}
          invisible={myStats.invisible || 0}
          prepSeconds={myStats.prepSeconds || 0}
          onPrepStrike={sendPrepStrike}
        />
        <ComboDisplay
          subclass={myStats.subclass}
          comboCount={myStats.comboCount || 0}
        />
        {showInventory && (isDesktop ? (
          <InventoryPane
            belongings={belongings}
            gold={gold}
            energy={energy}
            strength={myStats.strength}
            onOpenItem={setUseItemTarget}
            onContextMenu={(item, x, y) => setCtxMenu({ item, x, y })}
            onDefaultAction={(item) => executeItemAction(item.id, item.default_action)}
          />
        ) : (
          <WndBag
            belongings={belongings}
            gold={gold}
            energy={energy}
            strength={myStats.strength}
            onOpenItem={setUseItemTarget}
            onContextMenu={(item, x, y) => setCtxMenu({ item, x, y })}
            onDefaultAction={(item) => executeItemAction(item.id, item.default_action)}
            onClose={() => setShowInventory(false)}
          />
        ))}
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

      {useItemTarget && (
        <WndUseItem
          item={itemsById[useItemTarget.id] || useItemTarget}
          onAction={executeItemAction}
          onAssignQuickslot={assignQuickslot}
          onClose={() => setUseItemTarget(null)}
        />
      )}

      {ctxMenu && (
        <RightClickMenu
          item={itemsById[ctxMenu.item.id] || ctxMenu.item}
          x={ctxMenu.x}
          y={ctxMenu.y}
          onAction={executeItemAction}
          onAssignQuickslot={assignQuickslot}
          onClose={() => setCtxMenu(null)}
        />
      )}

      {showQuickBag && (
        <WndQuickBag
          belongings={belongings}
          onUse={(itemId, action) => executeItemAction(itemId, action)}
          onClose={() => setShowQuickBag(false)}
        />
      )}

      {radialOpen && (
        <RadialMenu
          items={toolbarItems}
          size={isDesktop ? 200 : 140}
          onSelect={(idx) => { handleToolbarClick(toolbarItems[idx], idx); }}
          onClose={() => setRadialOpen(false)}
        />
      )}

      {showSubclassChoice && (
        <SubclassChoice
          options={subclassOptions}
          onChoose={(sc) => {
            handleChooseSubclass(sc);
            setShowSubclassChoice(false);
          }}
          onSkip={() => setShowSubclassChoice(false)}
        />
      )}

      {showArmorAbilityChoice && (
        <ArmorAbilityChoice
          options={armorAbilityOptions}
          abilitySelectors={talentDefs?.ability_selectors || {}}
          onChoose={(tid) => {
            handleChooseArmorAbility(tid);
            setShowArmorAbilityChoice(false);
          }}
          onSkip={() => setShowArmorAbilityChoice(false)}
        />
      )}

      {showLevelUpBanner && levelUpData && gameState === 'PLAYING' && (
        <LevelUpBanner
          level={levelUpData.level}
          tierUnlocked={levelUpData.tier_unlocked}
          talentPoints={talentPoints}
          canChooseSubclass={levelUpData.can_choose_subclass}
          canChooseArmorAbility={levelUpData.can_choose_armor_ability}
          onOpenTalents={() => {
            setShowTalentPane(true);
            onOpenTalentsRef.current();
          }}
          onDismiss={() => setShowLevelUpBanner(false)}
        />
      )}

      {showTalentPane && (
        <TalentPane
          talentDefs={talentDefs}
          talentLevels={myStats.talentLevels || {}}
          talentPoints={talentPoints}
          bonusTalentPoints={myStats.bonusTalentPoints}
          level={myStats.level || 1}
          subclass={myStats.subclass || null}
          armorAbility={myStats.armorAbility || null}
          abilityTier4={talentDefs?.ability_tier4 || {}}
          upgradedTalentId={upgradedTalentId}
          onAnimationDone={() => setUpgradedTalentId(null)}
          onUpgradeTalent={sendUpgradeTalent}
          onChooseSubclass={handleChooseSubclass}
          onChooseArmorAbility={handleChooseArmorAbility}
          onClose={() => {
            setShowSubclassChoice(false);
            setShowArmorAbilityChoice(false);
            setShowTalentPane(false);
            setShowMetamorphMode(false);
            setMetamorphOptions(null);
            setMetamorphOldTalent(null);
          }}
          loading={talentDefsLoading}
          error={talentDefsError}
          metamorphMode={showMetamorphMode}
          onMetamorphChoose={sendMetamorphChoose}
        />
      )}

      {metamorphOptions && (
        <WndOptions
          icon="§"
          title="Choose replacement talent"
          message="Pick a talent from another class to replace your current one."
          options={metamorphOptions.map(tid => {
            // Look up talent name from talentDefs
            for (const [, tier] of Object.entries(talentDefs?.tiers || {})) {
              const found = tier.talents.find(t => t.id === tid);
              if (found) return found.name || tid;
            }
            return tid;
          })}
          onSelect={(idx) => {
            const tid = metamorphOptions[idx];
            if (metamorphOldTalent && tid) {
              sendMetamorphReplace(metamorphOldTalent, tid);
            }
            setMetamorphOptions(null);
            setMetamorphOldTalent(null);
            setShowMetamorphMode(false);
          }}
          onClose={() => {
            setMetamorphOptions(null);
            setMetamorphOldTalent(null);
            setShowMetamorphMode(false);
          }}
        />
      )}

      {gameMenuOpen && (
        <GameMenu
          onClose={() => setGameMenuOpen(false)}
          onLeaveGame={handleLeaveGame}
        />
      )}

      {!!myStats.isDowned && (
        <GameOverScreen
          playerName={myStats.name}
          classType={myStats.classType || selectedClass}
          level={myStats.level || 1}
          depth={depth}
          gold={gold ?? 0}
          subclass={myStats.subclass}
          armorAbility={myStats.armorAbility}
          talentLevels={myStats.talentLevels}
          talentDefs={talentDefs}
          inventory={inventory}
          onNewGame={() => { resetForRestart(); setGameState('SELECT'); }}
          onMenu={() => { resetForRestart(); setGameState('WELCOME'); }}
        />
      )}
    </div>
    </>
  );
}

export default App;
