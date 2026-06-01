import { useEffect, useState } from 'react';

// "You Died" overlay shown on permanent death. It is semi-transparent so the
// dimmed world (the player's death spot) stays visible for spectating, mirroring
// Shattered Pixel Dungeon's game-over banner + restart/menu buttons.
export default function GameOverScreen({ onNewGame, onMenu }) {
  const [shown, setShown] = useState(false);

  useEffect(() => {
    // Fade in over ~2s on mount, like SPD's GAME_OVER banner. The setState runs
    // asynchronously inside requestAnimationFrame, not synchronously in the effect.
    const id = requestAnimationFrame(() => setShown(true));
    return () => cancelAnimationFrame(id);
  }, []);

  return (
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

      <div style={{ display: 'flex', gap: '16px', pointerEvents: 'auto' }}>
        <button onClick={onNewGame} style={btnStyle}>New Game</button>
        <button onClick={onMenu} style={btnStyle}>Menu</button>
      </div>
    </div>
  );
}

const btnStyle = {
  fontFamily: 'monospace',
  fontSize: '18px',
  padding: '10px 22px',
  color: '#fff',
  background: '#3a3a3a',
  border: '2px solid #6a6a6a',
  borderRadius: '4px',
  cursor: 'pointer',
};
