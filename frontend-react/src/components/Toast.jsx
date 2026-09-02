import { CheckCircle2, AlertCircle, Info, X } from 'lucide-react';

export const Toast = ({ message, type = 'info', onClose }) => {
  const getIcon = () => {
    switch (type) {
      case 'success':
        return <CheckCircle2 size={16} className="toast-icon" />;
      case 'error':
        return <AlertCircle size={16} className="toast-icon" />;
      default:
        return <Info size={16} className="toast-icon" />;
    }
  };

  return (
    <div className={`toast-item toast-${type}`} role="alert">
      {getIcon()}
      <span className="toast-message">{message}</span>
      <button
        type="button"
        className="toast-close"
        onClick={onClose}
        aria-label="Dismiss notification"
      >
        <X size={14} />
      </button>
    </div>
  );
};
