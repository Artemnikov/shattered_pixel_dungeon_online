import { useEffect } from 'react';
import { TILE_SIZE, MOVE_DURATION, CAMERA_LERP, easeOutQuad } from '../constants';
import { DEST_TILE_SIZE } from './sewers/constants';
import { buildWaterClipPath, drawWaterBackground, getWaterTextureForDepth } from './sewers/draw';
import { drawGrid, drawGridCaps } from './draw/grid';
import { drawItems } from './draw/items';
import { drawMobs } from './draw/mobs';
import { drawPlayers } from './draw/players';
import { advanceAndDrawProjectiles } from './draw/projectiles';
import { advanceAndDrawParticles } from './draw/particles';
import { advanceAndDrawFloatingText } from './draw/floatingText';

export default function useGameRenderer({
  canvasRef,
  grid,
  myPlayerId,
  depth,
  assetImages,
  entitiesRef,
  visionRef,
  openDoorsRef,
  projectilesRef,
  mobAnimRef,
  dyingMobsRef,
  playerAnimRef,
  particlesRef,
  floatingTextRef,
  myPlayerIdRef,
  panOffsetRef,
  cameraLerpRef,
  zoomRef,
  isRefocusingRef,
  isDraggingRef,
  setCamera,
}) {
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    let animationFrameId;

    const waterClipPath = buildWaterClipPath(grid);
    const waterTex = getWaterTextureForDepth(depth, assetImages.waterFrames);
    const gridBounds = {
      x: 0,
      y: 0,
      w: (grid[0]?.length ?? 0) * DEST_TILE_SIZE,
      h: grid.length * DEST_TILE_SIZE,
    };

    const updateAnimations = () => {
      const now = performance.now();
      const allEntities = [
        ...Object.values(entitiesRef.current.players),
        ...Object.values(entitiesRef.current.mobs),
      ];
      allEntities.forEach(entity => {
        if (entity.targetPos && entity.animStartTime != null && entity.animStartPos) {
          const t = Math.min((now - entity.animStartTime) / MOVE_DURATION, 1.0);
          const eased = easeOutQuad(t);
          entity.renderPos.x = entity.animStartPos.x + (entity.targetPos.x - entity.animStartPos.x) * eased;
          entity.renderPos.y = entity.animStartPos.y + (entity.targetPos.y - entity.animStartPos.y) * eased;
        }
      });
    };

    const render = () => {
      if (grid.length === 0) return;
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      updateAnimations();

      if (isRefocusingRef.current) {
        panOffsetRef.current.x += (0 - panOffsetRef.current.x) * CAMERA_LERP;
        panOffsetRef.current.y += (0 - panOffsetRef.current.y) * CAMERA_LERP;
        if (Math.abs(panOffsetRef.current.x) < 0.5 && Math.abs(panOffsetRef.current.y) < 0.5) {
          panOffsetRef.current = { x: 0, y: 0 };
          isRefocusingRef.current = false;
        }
      }

      let cameraX = 0;
      let cameraY = 0;
      const myPlayer = entitiesRef.current.players[myPlayerIdRef.current];

      if (myPlayer) {
        cameraX = myPlayer.renderPos.x * TILE_SIZE - canvas.width / 2 + TILE_SIZE / 2 + panOffsetRef.current.x;
        cameraY = myPlayer.renderPos.y * TILE_SIZE - canvas.height / 2 + TILE_SIZE / 2 + panOffsetRef.current.y;

        const gridCols = grid[0]?.length ?? 0;
        const gridRows = grid.length;
        const z = zoomRef.current;
        const halfW = (canvas.width / 2 - TILE_SIZE / 2) / z;
        const halfH = (canvas.height / 2 - TILE_SIZE / 2) / z;
        cameraX = Math.max(-halfW, Math.min(cameraX, gridCols * TILE_SIZE - canvas.width / z + halfW));
        cameraY = Math.max(-halfH, Math.min(cameraY, gridRows * TILE_SIZE - canvas.height / z + halfH));

        panOffsetRef.current.x = cameraX - (myPlayer.renderPos.x * TILE_SIZE - canvas.width / 2 + TILE_SIZE / 2);
        panOffsetRef.current.y = cameraY - (myPlayer.renderPos.y * TILE_SIZE - canvas.height / 2 + TILE_SIZE / 2);

        if (isDraggingRef.current) {
          cameraLerpRef.current.x = cameraX;
          cameraLerpRef.current.y = cameraY;
        } else {
          cameraLerpRef.current.x += (cameraX - cameraLerpRef.current.x) * CAMERA_LERP;
          cameraLerpRef.current.y += (cameraY - cameraLerpRef.current.y) * CAMERA_LERP;
        }
      }

      setCamera({ x: cameraLerpRef.current.x, y: cameraLerpRef.current.y });

      ctx.save();
      const z = zoomRef.current;
      ctx.translate(canvas.width / 2, canvas.height / 2);
      ctx.scale(z, z);
      ctx.translate(-canvas.width / 2, -canvas.height / 2);
      ctx.translate(-cameraLerpRef.current.x, -cameraLerpRef.current.y);

      drawWaterBackground(ctx, waterTex, waterClipPath, gridBounds, performance.now());
      drawGrid(ctx, { grid, depth, assetImages, visionRef, openDoorsRef });
      drawItems(ctx, { entitiesRef, visionRef, assetImages });
      drawMobs(ctx, { entitiesRef, visionRef, assetImages, mobAnimRef, dyingMobsRef });
      drawPlayers(ctx, { entitiesRef, visionRef, assetImages, playerAnimRef, myPlayerId });
      drawGridCaps(ctx, { grid, depth, assetImages, visionRef });
      advanceAndDrawParticles(ctx, { particlesRef });
      advanceAndDrawFloatingText(ctx, { floatingTextRef });
      advanceAndDrawProjectiles(ctx, { projectilesRef });

      ctx.restore();

      // Vision loss: when the local player is dead, dim the screen but keep the
      // world visible so they can still spectate (alpha ramps 0 -> 0.55 over 2s).
      const me = entitiesRef.current.players[myPlayerIdRef.current];
      if (me && me.is_downed) {
        const elapsed = performance.now() - (me.deathStart || performance.now());
        const alpha = Math.min(elapsed / 2000, 1) * 0.55;
        ctx.fillStyle = `rgba(0, 0, 0, ${alpha})`;
        ctx.fillRect(0, 0, canvas.width, canvas.height);
      }

      animationFrameId = requestAnimationFrame(render);
    };

    render();
    return () => cancelAnimationFrame(animationFrameId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [grid, myPlayerId, assetImages, depth]);
}
