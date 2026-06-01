import { useEffect } from 'react';
import { TILE_SIZE, PLAYER_ATTACK_DURATION, PLAYER_OPERATE_DURATION, HIT_CONNECT_DELAY, FLASH_DURATION } from '../constants';
import { getWsBaseUrl } from '../config/urls';
import AudioManager from '../audio/AudioManager';
import { spawnBlood, spawnHeal } from '../rendering/draw/particles';
import { spawnFloatingText } from '../rendering/draw/floatingText';

// Blood color per mob (default red; Goo bleeds green like its acidic body).
const BLOOD_COLORS = { Goo: '#8eb300' };

export default function useGameSocket({
  enabled,
  gameId,
  selectedClass,
  difficulty,
  playerName,
  socketRef,
  gridRef,
  myPlayerIdRef,
  entitiesRef,
  visionRef,
  openDoorsRef,
  projectilesRef,
  mobAnimRef,
  dyingMobsRef,
  playerAnimRef,
  particlesRef,
  floatingTextRef,
  wasDownedRef,
  setGrid,
  setDepth,
  setMyPlayerId,
  setInventory,
  setEquippedItems,
  setMyStats,
  setMessages,
  setDifficulty,
}) {
  useEffect(() => {
    if (!enabled) return;

    const wsBaseUrl = getWsBaseUrl();
    const nameParam = playerName ? `&name=${encodeURIComponent(playerName)}` : '';
    const urlParams = new URLSearchParams(window.location.search);
    const adminSecret = urlParams.get('admin_secret') || '';
    const adminParam = adminSecret ? `&admin_secret=${encodeURIComponent(adminSecret)}` : '';
    const ws = new WebSocket(`${wsBaseUrl}/ws/game/${gameId}?class_type=${selectedClass}&difficulty=${difficulty}${nameParam}${adminParam}`);
    socketRef.current = ws;
    let hasConnected = false;

    const addConnectionFailedMessage = () => {
      setMessages(prev => (
        prev[prev.length - 1] === "Failed to connect to channel"
          ? prev
          : [...prev, "Failed to connect to channel"]
      ));
    };

    ws.onopen = () => {
      hasConnected = true;
      setMessages(prev => [...prev, "Connected to server"]);
    };
    ws.onerror = () => {
      if (!hasConnected) addConnectionFailedMessage();
    };
    ws.onclose = () => {
      if (!hasConnected) addConnectionFailedMessage();
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'INIT') {
        setGrid(data.grid);
        gridRef.current = data.grid;
        visionRef.current.discovered = new Set();
        if (typeof data.depth === 'number') setDepth(data.depth);
        if (data.player_id) {
          setMyPlayerId(data.player_id);
          myPlayerIdRef.current = data.player_id;
        }
        return;
      }

      if (data.type !== 'STATE_UPDATE') return;

      if (typeof data.depth === 'number') setDepth(data.depth);
      if (data.difficulty) setDifficulty(data.difficulty);

      // Sync players
      const currentServerPlayerIds = new Set(data.players.map(p => p.id));
      Object.keys(entitiesRef.current.players).forEach(id => {
        if (!currentServerPlayerIds.has(id)) {
          delete entitiesRef.current.players[id];
        }
      });

      data.players.forEach(p => {
        if (p.id === myPlayerIdRef.current) {
          setInventory(p.inventory || []);
          setEquippedItems({
            weapon: p.equipped_weapon,
            wearable: p.equipped_wearable,
          });
          const healthBoost = p.equipped_wearable ? p.equipped_wearable.health_boost : 0;
          // Death sound is played for all players (incl. local) by the entity-sync
          // transition below, so it is not duplicated here.
          wasDownedRef.current = p.is_downed;
          setMyStats({
            hp: p.hp,
            maxHp: p.max_hp + healthBoost,
            name: p.name,
            isDowned: p.is_downed,
            isRegen: (p.heal_left || 0) > 0,
          });
        }

        if (!entitiesRef.current.players[p.id]) {
          entitiesRef.current.players[p.id] = {
            ...p,
            renderPos: { x: p.pos.x, y: p.pos.y },
            animStartPos: { x: p.pos.x, y: p.pos.y },
            animStartTime: null,
            facing: 'RIGHT',
            flipX: false,
            deathStart: p.is_downed ? performance.now() : null,
          };
        } else {
          const existing = entitiesRef.current.players[p.id];
          const currentTarget = existing.targetPos || existing.renderPos;
          const dx = p.pos.x - currentTarget.x;
          const dy = p.pos.y - currentTarget.y;

          if (Math.abs(dx) > Math.abs(dy)) {
            if (dx > 0) { existing.facing = 'RIGHT'; existing.flipX = false; }
            else if (dx < 0) { existing.facing = 'LEFT'; existing.flipX = true; }
          } else {
            if (dy > 0) existing.facing = 'DOWN';
            else if (dy < 0) existing.facing = 'UP';
          }

          existing.animStartPos = { x: existing.renderPos.x, y: existing.renderPos.y };
          existing.animStartTime = performance.now();
          existing.targetPos = p.pos;
          existing.name = p.name;
          existing.hp = p.hp;
          existing.max_hp = p.max_hp;
          existing.equipped_wearable = p.equipped_wearable;
          // Start the death animation (and death sound) the instant a player dies.
          if (p.is_downed && !existing.is_downed) {
            existing.deathStart = performance.now();
            AudioManager.play('DEATH');
          }
          existing.is_downed = p.is_downed;
          existing.heal_left = p.heal_left;
          existing.class_type = p.class_type;
        }
      });

      // Sync mobs
      const currentServerMobIds = new Set(data.mobs.map(m => m.id));

      // Snapshot mobs that die this tick before the sync removes them,
      // otherwise the DEATH event handler below finds an empty entity map.
      if (data.events) {
        data.events.forEach(ev => {
          if (ev.type !== 'DEATH') return;
          const id = ev.data.target;
          const mob = entitiesRef.current.mobs[id];
          if (mob && !dyingMobsRef.current[id]) {
            dyingMobsRef.current[id] = {
              ...mob,
              renderPos: { ...mob.renderPos },
              deathStart: performance.now(),
            };
          }
        });
      }

      Object.keys(entitiesRef.current.mobs).forEach(id => {
        if (!currentServerMobIds.has(id)) {
          delete entitiesRef.current.mobs[id];
        }
      });

      data.mobs.forEach(m => {
        if (!entitiesRef.current.mobs[m.id]) {
          entitiesRef.current.mobs[m.id] = {
            ...m,
            renderPos: { x: m.pos.x, y: m.pos.y },
            animStartPos: { x: m.pos.x, y: m.pos.y },
            animStartTime: null,
            facing: 'RIGHT',
          };
        } else {
          const existing = entitiesRef.current.mobs[m.id];
          const currentTarget = existing.targetPos || existing.renderPos;
          if (m.pos.x > currentTarget.x) existing.facing = 'RIGHT';
          else if (m.pos.x < currentTarget.x) existing.facing = 'LEFT';

          existing.animStartPos = { x: existing.renderPos.x, y: existing.renderPos.y };
          existing.animStartTime = performance.now();
          existing.targetPos = m.pos;
          existing.hp = m.hp;
        }
      });

      entitiesRef.current.items = data.items || [];

      if (data.visible_tiles) {
        const newVisible = new Set(data.visible_tiles.map(t => `${t[0]},${t[1]}`));
        visionRef.current.visible = newVisible;
        newVisible.forEach(t => visionRef.current.discovered.add(t));
      }

      const myPlayer = data.players.find(p => p.id === myPlayerIdRef.current);
      if (myPlayer?.is_admin && gridRef.current.length > 0) {
        const allTiles = new Set();
        for (let y = 0; y < gridRef.current.length; y++) {
          for (let x = 0; x < gridRef.current[0].length; x++) {
            allTiles.add(`${x},${y}`);
          }
        }
        visionRef.current.visible = allTiles;
        allTiles.forEach(t => visionRef.current.discovered.add(t));
      }

      if (data.open_doors) {
        openDoorsRef.current = new Set(data.open_doors.map(d => `${d[0]},${d[1]}`));
      }

      if (data.events) {
        data.events.forEach(event => {
          handleEvent(event, {
            myPlayerIdRef, gridRef, setGrid, entitiesRef,
            projectilesRef, mobAnimRef, dyingMobsRef, playerAnimRef, particlesRef,
            floatingTextRef,
          });
        });
      }
    };

    return () => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.close();
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled, gameId]);
}

function handleEvent(event, {
  myPlayerIdRef, gridRef, setGrid, entitiesRef,
  projectilesRef, mobAnimRef, dyingMobsRef, playerAnimRef, particlesRef,
  floatingTextRef,
}) {
  if (event.type === 'PLAY_SOUND') {
    AudioManager.play(event.data.sound);
    return;
  }

  if (event.type === 'DRINK') {
    AudioManager.play('DRINK');
    // Play the "operate" gesture (raise item) on the drinker, mirroring
    // Potion.drink() -> hero.sprite.operate() in the original game.
    const pid = event.data.player;
    if (playerAnimRef && entitiesRef.current.players[pid]) {
      if (!playerAnimRef.current[pid]) playerAnimRef.current[pid] = {};
      playerAnimRef.current[pid].operateUntil = performance.now() + PLAYER_OPERATE_DURATION;
    }
    return;
  }

  if (event.type === 'HEAL') {
    // Green "+N" rising number plus upward sparkles, mirroring the original's
    // FloatingText.HEALING and Speck.HEALING when the Healing buff ticks.
    const cx = event.data.x * TILE_SIZE + TILE_SIZE / 2;
    const cy = event.data.y * TILE_SIZE; // above the sprite's feet
    if (floatingTextRef) {
      spawnFloatingText(floatingTextRef, cx, cy, `+${event.data.amount}`, '#2ecc71');
    }
    if (particlesRef) {
      spawnHeal(particlesRef, cx, cy + TILE_SIZE / 2, 4);
    }
    return;
  }

  if (event.type === 'MAP_PATCH' && event.data?.tiles) {
    setGrid(prev => {
      if (!prev || prev.length === 0) return prev;
      const next = prev.map(row => row.slice());
      event.data.tiles.forEach(tilePatch => {
        const { x, y, tile } = tilePatch;
        if (y >= 0 && y < next.length && x >= 0 && x < next[y].length) {
          next[y][x] = tile;
        }
      });
      gridRef.current = next;
      return next;
    });
    return;
  }

  if (event.type === 'MOVE') {
    const tileX = event.data.x;
    const tileY = event.data.y;
    const tileType = gridRef.current[tileY]?.[tileX];
    const isDoor = tileType === 3;

    if (event.data.entity === myPlayerIdRef.current) {
      if (isDoor) {
        AudioManager.play('DOOR_OPEN');
      } else if (tileType) {
        AudioManager.playStep(tileType);
      } else {
        AudioManager.play('MOVE');
      }
    } else {
      if (isDoor) {
        AudioManager.play('DOOR_OPEN');
      } else {
        AudioManager.play(event.type);
      }
    }
    return;
  }

  if (event.type === 'RANGED_ATTACK') {
    const startX = event.data.x * TILE_SIZE + TILE_SIZE / 2;
    const startY = event.data.y * TILE_SIZE + TILE_SIZE / 2;
    const targetX = event.data.target_x * TILE_SIZE + TILE_SIZE / 2;
    const targetY = event.data.target_y * TILE_SIZE + TILE_SIZE / 2;

    projectilesRef.current.push({
      x: startX,
      y: startY,
      startX,
      startY,
      targetX,
      targetY,
      type: event.data.projectile || 'arrow',
      progress: 0,
      finished: false,
    });

    if (event.data.projectile === 'magic_bolt') {
      AudioManager.play('ATTACK_MAGIC');
    } else {
      AudioManager.play('ATTACK_BOW');
    }
    return;
  }

  if (event.type === 'PICKUP' && event.data.player === myPlayerIdRef.current) {
    AudioManager.play('PICKUP');
    return;
  }

  if (event.type === 'STAIRS_DOWN' && event.data.player === myPlayerIdRef.current) {
    AudioManager.play('STAIRS_DOWN');
    return;
  }

  if (event.type === 'ATTACK') {
    const src = event.data.source;
    const tgt = event.data.target;
    const damage = event.data.damage || 0;
    const now = performance.now();

    const srcMob = entitiesRef.current.mobs[src];
    const srcPlayer = entitiesRef.current.players[src];
    const srcEntity = srcMob || srcPlayer;
    const tgtEntity = entitiesRef.current.mobs[tgt] || entitiesRef.current.players[tgt];

    // 1) Play the attacker's swing.
    if (srcMob) {
      if (!mobAnimRef.current[src]) mobAnimRef.current[src] = {};
      const attackDuration = srcMob.name === 'Goo' ? 300 : srcMob.name === 'Scorpio' ? 200 : srcMob.name === 'Rat' ? 333 : 250;
      mobAnimRef.current[src].attackUntil = now + attackDuration;
    } else if (srcPlayer && playerAnimRef) {
      if (!playerAnimRef.current[src]) playerAnimRef.current[src] = {};
      playerAnimRef.current[src].attackUntil = now + PLAYER_ATTACK_DURATION;
    }

    // 2) Turn the attacker to face the target (mirrors CharSprite.turnTo).
    if (srcEntity && tgtEntity) {
      const dx = tgtEntity.renderPos.x - srcEntity.renderPos.x;
      if (dx > 0) { srcEntity.facing = 'RIGHT'; srcEntity.flipX = false; }
      else if (dx < 0) { srcEntity.facing = 'LEFT'; srcEntity.flipX = true; }
    }

    // 3) Hit reaction (flash + blood) when the swing connects.
    if (damage > 0 && tgtEntity) {
      const sc = srcEntity ? {
        x: srcEntity.renderPos.x * TILE_SIZE + TILE_SIZE / 2,
        y: srcEntity.renderPos.y * TILE_SIZE + TILE_SIZE / 2,
      } : null;
      const tc = {
        x: tgtEntity.renderPos.x * TILE_SIZE + TILE_SIZE / 2,
        y: tgtEntity.renderPos.y * TILE_SIZE + TILE_SIZE / 2,
      };
      const isMobTarget = !!entitiesRef.current.mobs[tgt];
      const maxHp = tgtEntity.max_hp || 1;
      const color = BLOOD_COLORS[tgtEntity.name] || '#bb0000';

      setTimeout(() => {
        const flashUntil = performance.now() + FLASH_DURATION;
        if (isMobTarget) {
          if (!mobAnimRef.current[tgt]) mobAnimRef.current[tgt] = {};
          mobAnimRef.current[tgt].flashUntil = flashUntil;
          // Blood only on mobs (heroes suppress blood, like HeroSprite.bloodBurstA).
          if (particlesRef) {
            const awayAngle = sc ? Math.atan2(tc.y - sc.y, tc.x - sc.x) : -Math.PI / 2;
            const count = Math.min(Math.round(9 * Math.sqrt(damage / maxHp)), 9);
            spawnBlood(particlesRef, tc.x, tc.y, awayAngle, count, color);
          }
        } else if (playerAnimRef) {
          if (!playerAnimRef.current[tgt]) playerAnimRef.current[tgt] = {};
          playerAnimRef.current[tgt].flashUntil = flashUntil;
        }
      }, HIT_CONNECT_DELAY);
    }
    return;
  }

  if (event.type === 'DEATH') {
    const id = event.data.target;
    const mob = entitiesRef.current.mobs[id];
    if (mob) {
      dyingMobsRef.current[id] = { ...mob, renderPos: { ...mob.renderPos }, deathStart: performance.now() };
    }
  }
}
