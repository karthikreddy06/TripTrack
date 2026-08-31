import { X } from 'lucide-react';

export const Alert = ({ type = 'error', message, onClose }) => {
  if (!message) return null;

  return (
    <div className={`alert alert-${type}`} role="alert">
      <div style={{ flex: 1, fontSize: '0.85rem' }}>{message}</div>
      {onClose && (
        <button
          type="button"
          onClick={onClose}
          className="alert-close"
          aria-label="Dismiss alert"
        >
          <X size={14} />
        </button>
      )}
    </div>
  );
};
