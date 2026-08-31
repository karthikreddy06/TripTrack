import { StatusBadge } from './StatusBadge';

export const TripCard = ({ trip, onEdit, onDelete }) => {
  const calculateDuration = (start, end) => {
    if (!start || !end) return '';
    try {
      const startDate = new Date(start);
      const endDate = new Date(end);
      const diffTime = endDate - startDate;
      const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24)) + 1;
      return diffDays > 0 ? `${diffDays} ${diffDays === 1 ? 'DAY' : 'DAYS'}` : '1 DAY';
    } catch {
      return '';
    }
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      maximumFractionDigits: 0,
    }).format(amount || 0);
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '';
    try {
      const [year, month, day] = dateStr.split('-');
      if (!year || !month || !day) return dateStr;
      const date = new Date(year, month - 1, day);
      return date
        .toLocaleDateString('en-US', {
          month: 'short',
          day: 'numeric',
          year: 'numeric',
        })
        .toUpperCase();
    } catch {
      return dateStr;
    }
  };

  const duration = calculateDuration(trip.start_date, trip.end_date);

  return (
    <div className="trip-card">
      <div className="trip-card-header">
        <h3 className="trip-destination" title={trip.destination}>
          {trip.destination}
        </h3>
        <StatusBadge status={trip.status} />
      </div>

      <div className="trip-card-body">
        <div className="trip-dates">
          <span>
            {formatDate(trip.start_date)} — {formatDate(trip.end_date)}
          </span>
        </div>

        <div className="trip-details-row">
          <div>
            <span className="trip-duration">{duration}</span>
          </div>
          <div className="trip-budget" title={`Budget: ${formatCurrency(trip.budget)}`}>
            {formatCurrency(trip.budget)}
          </div>
        </div>
      </div>

      <div className="trip-card-footer">
        <button
          type="button"
          className="btn btn-secondary btn-sm"
          onClick={() => onEdit(trip)}
          title="Edit trip details"
        >
          Edit
        </button>

        <button
          type="button"
          className="btn btn-danger btn-sm"
          onClick={() => onDelete(trip)}
          title="Delete trip"
        >
          Delete
        </button>
      </div>
    </div>
  );
};
