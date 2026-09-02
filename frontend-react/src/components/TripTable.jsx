import { StatusBadge } from './StatusBadge';

export const TripTable = ({ trips, onEdit, onDelete }) => {
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

  return (
    <div className="table-container">
      <table className="trip-table">
        <thead>
          <tr>
            <th>DESTINATION</th>
            <th>ITINERARY DATES</th>
            <th>STATUS</th>
            <th>BUDGET</th>
            <th style={{ textAlign: 'right' }}>ACTIONS</th>
          </tr>
        </thead>
        <tbody>
          {trips.map((trip) => (
            <tr key={trip._id}>
              <td>
                <Link to={`/trips/${trip._id}`} className="table-destination-link" title={trip.title || trip.destination}>
                  <span className="table-destination-title">
                    {trip.title || trip.destination}
                  </span>
                </Link>
                {trip.title && trip.title !== trip.destination && (
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                    {trip.destination}
                  </div>
                )}
              </td>
              <td>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.775rem', color: 'var(--text-secondary)' }}>
                  {formatDate(trip.start_date)} — {formatDate(trip.end_date)}
                </span>
              </td>
              <td>
                <StatusBadge status={trip.status} />
              </td>
              <td>
                <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, color: 'var(--text-primary)' }}>
                  {formatCurrency(trip.budget)}
                </span>
              </td>
              <td>
                <div className="table-actions" style={{ justifyContent: 'flex-end' }}>
                  <Link
                    to={`/trips/${trip._id}`}
                    className="btn btn-secondary btn-sm"
                    title="View itinerary & budget"
                  >
                    View
                  </Link>
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    onClick={() => onEdit(trip)}
                    title="Edit trip"
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
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};
