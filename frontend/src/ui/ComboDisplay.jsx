const COMBO_MOVE_NAMES = {
  2: 'Clobber',
  4: 'Slam',
  6: 'Parry',
  8: 'Crush',
  10: 'Fury',
};

export default function ComboDisplay({
  subclass,
  comboCount,
  comboMax = 10,
}) {
  if (subclass !== 'gladiator' || !comboCount) return null;

  const unlockedMoves = Object.entries(COMBO_MOVE_NAMES)
    .filter(([threshold]) => comboCount >= Number(threshold))
    .map(([, name]) => name);

  return (
    <div className="combo-container">
      <div className="combo-label">
        Combo <span className="combo-count">{comboCount}</span>
        <span className="combo-max">/{comboMax}</span>
      </div>
      <div className="combo-bar-track">
        <div className="combo-bar-fill" style={{
          width: `${(comboCount / comboMax) * 100}%`
        }} />
      </div>
      {unlockedMoves.length > 0 && (
        <div className="combo-moves">
          {unlockedMoves.map(m => (
            <span key={m} className="combo-move">{m}</span>
          ))}
        </div>
      )}
    </div>
  );
}
