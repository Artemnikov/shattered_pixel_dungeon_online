export default function WndOptions({
  icon,
  title,
  message,
  options,
  onSelect,
  onClose,
}) {
  return (
    <div className="wnd-overlay" onClick={onClose}>
      <div className="wnd-options" onClick={(e) => e.stopPropagation()}>
        {icon && <div className="wnd-options-icon">{icon}</div>}
        {title && <div className="wnd-options-title">{title}</div>}
        {message && <div className="wnd-options-msg">{message}</div>}
        <div className="wnd-options-buttons">
          {options.map((opt, i) => (
            <button
              key={i}
              className={`wnd-opt-btn ${i === 0 ? 'yes' : i === options.length - 1 ? 'no' : ''}`}
              onClick={() => { onSelect?.(i); onClose?.(); }}
            >
              {opt}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
