export const DeleteModal = ({ isOpen, trip, onConfirm, onCancel, isDeleting }) => {
  if (!isOpen || !trip) return null;

  return (
    <div className="modal-backdrop" onClick={onCancel}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div style={{ marginBottom: '1.25rem' }}>
          <div className="editorial-mark" style={{ color: 'var(--danger-text)', marginBottom: '0.4rem' }}>
            <i style={{ background: 'var(--danger-text)' }}></i> CONFIRMATION
          </div>
          <h2 style={{ fontSize: '1.65rem', fontWeight: 500, letterSpacing: '-0.03em' }}>
            Delete this trip?
          </h2>
        </div>

        <p style={{ color: 'var(--text-secondary)', marginBottom: '0.5rem', fontSize: '0.925rem' }}>
          Are you sure you want to remove your itinerary to <strong style={{ color: 'var(--text-primary)' }}>{trip.destination}</strong>?
        </p>
        <p style={{ color: 'var(--text-muted)', marginBottom: '1.75rem', fontSize: '0.78rem', fontFamily: 'var(--font-mono)' }}>
          This action cannot be undone.
        </p>

        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem' }}>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={onCancel}
            disabled={isDeleting}
          >
            Cancel
          </button>
          <button
            type="button"
            className="btn btn-danger"
            onClick={() => onConfirm(trip)}
            disabled={isDeleting}
          >
            {isDeleting ? (
              <>
                <span className="spinner" />
                <span>Deleting...</span>
              </>
            ) : (
              'Delete trip'
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
