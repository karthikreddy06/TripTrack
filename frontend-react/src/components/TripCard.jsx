import { Link } from 'react-router-dom';
import { Users, Calendar, ArrowUpRight } from 'lucide-react';
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
  const displayTitle = trip.title || trip.destination;
  const subtitle = trip.title && trip.title !== trip.destination ? trip.destination : null;

  return (
    <div className="trip-card">
      <div className="trip-card-header">
        <div>
          <Link to={`/trips/${trip._id}`} className="trip-destination-link" title={displayTitle}>
            <h3 className="trip-destination">
              {displayTitle}
            </h3>
          </Link>
          {subtitle && (
            <span className="trip-sub-destination">{subtitle}</span>
          )}
        </div>
        <StatusBadge status={trip.status} />
      </div>

      <div className="trip-card-body">
        <div className="trip-dates">
          <Calendar size={13} style={{ opacity: 0.7 }} />
          <span>
            {formatDate(trip.start_date)} — {formatDate(trip.end_date)}
          </span>
        </div>

        {trip.description && (
          <p className="trip-card-description">
            {trip.description}
          </p>
        )}

        <div className="trip-details-row">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <span className="trip-duration">{duration}</span>
            {trip.travelers > 1 && (
              <span className="trip-travelers-tag" title={`${trip.travelers} travelers`}>
                <Users size={11} />
                <span>{trip.travelers}</span>
              </span>
            )}
          </div>
          <div className="trip-budget" title={`Budget: ${formatCurrency(trip.budget)}`}>
            {formatCurrency(trip.budget)}
          </div>
        </div>
      </div>

      <div className="trip-card-footer">
        <Link
          to={`/trips/${trip._id}`}
          className="btn btn-secondary btn-sm"
          title="Open trip itinerary and budget details"
        >
          <span>View Details</span>
          <ArrowUpRight size={12} />
        </Link>

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
