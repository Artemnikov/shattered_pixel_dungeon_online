import { useEffect, useState } from 'react';
import RankingsPane from './RankingsPane';

export default function GameOverScreen({
  playerName,
  classType,
  level,
  depth,
  gold,
  subclass,
  armorAbility,
  talentLevels,
  talentDefs,
  inventory,
  onNewGame,
  onMenu,
}) {
  const [shown, setShown] = useState(false);
  const [showRankings, setShowRankings] = useState(false);

  useEffect(() => {
    const id = requestAnimationFrame(() => setShown(true));
    return () => cancelAnimationFrame(id);
  }, []);

  useEffect(() => {
    if (shown) {
      const id = setTimeout(() => setShowRankings(true), 1500);
      return () => clearTimeout(id);
    }
  }, [shown]);

  return (
    <>
      <div
        style={{
          position: 'absolute',
          inset: 0,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '20px',
          zIndex: 50,
          pointerEvents: 'none',
          opacity: shown ? 1 : 0,
          transition: 'opacity 2s ease-in',
        }}
      >
        <div
          style={{
            fontFamily: 'monospace',
            fontSize: '48px',
            fontWeight: 'bold',
            color: '#e74c3c',
            textShadow: '0 2px 6px #000',
            letterSpacing: '2px',
          }}
        >
          You Died
        </div>
      </div>

      {showRankings && (
        <RankingsPane
          playerName={playerName}
          classType={classType}
          level={level}
          depth={depth}
          gold={gold}
          subclass={subclass}
          armorAbility={armorAbility}
          talentLevels={talentLevels}
          talentDefs={talentDefs}
          inventory={inventory}
          onNewGame={onNewGame}
          onMenu={onMenu}
        />
      )}
    </>
  );
}
