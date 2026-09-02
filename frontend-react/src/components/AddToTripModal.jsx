import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  Plus,
  CheckCircle2,
  X,
  MapPin,
  ArrowUpRight,
  Luggage
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import { tripsAPI, itineraryAPI, extractErrorMessage } from '../services/api';

export const AddToTripModal = ({ isOpen, onClose, place }) => {
  const { user } = useAuth();
  const { showSuccess, showError } = useToast();

  const [trips, setTrips] = useState([]);
  const [loadingTrips, setLoadingTrips] = useState(true);
  const [selectedTripId, setSelectedTripId] = useState('');
  const [dayNumber, setDayNumber] = useState(1);
  const [timeSlot, setTimeSlot] = useState('10:00 AM');
  const [estimatedCost, setEstimatedCost] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [addedSuccessTrip, setAddedSuccessTrip] = useState(null);

  useEffect(() => {
    const fetchUserTrips = async () => {
      if (!isOpen || !user?.user_id) return;
      try {
        setLoadingTrips(true);
        const data = await tripsAPI.getTrips(user.user_id);
        const list = Array.isArray(data) ? data : [];
        setTrips(list);

        // Pre-select trip matching destination if available
        if (list.length > 0) {
          const matching = place?.location
            ? list.find((t) => place.location.toLowerCase().includes(t.destination.toLowerCase()) || t.destination.toLowerCase().includes(place.location.toLowerCase()))
            : null;
          setSelectedTripId(matching ? matching._id : list[0]._id);
        }
      } catch (err) {
        showError(extractErrorMessage(err));
      } finally {
        setLoadingTrips(false);
      }
    };

    fetchUserTrips();
  }, [isOpen, user?.user_id, place?.location]);

  if (!isOpen || !place) return null;

  const selectedTrip = trips.find((t) => t._id === selectedTripId);

  const handleAdd = async (e) => {
    e.preventDefault();
    if (!selectedTripId) {
      showError('Please select an existing trip or create a new one first.');
      return;
    }

    try {
      setSubmitting(true);

      // Determine date from trip start date + day number
      let activityDate = selectedTrip?.start_date || new Date().toISOString().split('T')[0];
      if (selectedTrip?.start_date && dayNumber > 1) {
        const start = new Date(selectedTrip.start_date);
        start.setDate(start.getDate() + (dayNumber - 1));
        activityDate = start.toISOString().split('T')[0];
      }

      await itineraryAPI.createActivity({
        trip_id: selectedTripId,
        day_number: parseInt(dayNumber, 10) || 1,
        date: activityDate,
        time: timeSlot || '10:00 AM',
        title: place.name,
        location: place.address || place.location,
        description: place.description || `${place.category.toUpperCase()} in ${place.location}`,
        cost: estimatedCost ? parseFloat(estimatedCost) : 0,
        notes: `Discovered on TravelTrack Explore (${place.category})`,
      });

      showSuccess(`Added "${place.name}" to ${selectedTrip.title || selectedTrip.destination}!`);
      setAddedSuccessTrip(selectedTrip);
    } catch (err) {
      showError(extractErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  const handleClose = () => {
    setAddedSuccessTrip(null);
    onClose();
  };

  return (
    <div className="modal-backdrop" onClick={handleClose}>
      <div className="modal-content add-to-trip-modal" onClick={(e) => e.stopPropagation()}>
        <button type="button" className="modal-close-icon-btn" onClick={handleClose} aria-label="Close">
          <X size={18} />
        </button>

        {addedSuccessTrip ? (
          <div style={{ textAlign: 'center', padding: '1.5rem 0.5rem' }}>
            <div className="success-icon-circle">
              <CheckCircle2 size={36} style={{ color: 'var(--primary-green)' }} />
            </div>
            <h3 style={{ fontSize: '1.6rem', marginTop: '1rem', marginBottom: '0.4rem' }}>
              Added to Itinerary!
            </h3>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.95rem', marginBottom: '1.75rem' }}>
              <strong>{place.name}</strong> is now scheduled for Day {dayNumber} of your journey to{' '}
              <strong>{addedSuccessTrip.destination}</strong>.
            </p>

            <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'center' }}>
              <button type="button" className="btn btn-secondary" onClick={handleClose}>
                Continue Exploring
              </button>
              <Link
                to={`/trips/${addedSuccessTrip._id}`}
                className="btn btn-primary"
                onClick={handleClose}
              >
                <span>View Trip Itinerary</span>
                <ArrowUpRight size={14} />
              </Link>
            </div>
          </div>
        ) : (
          <>
            <div className="editorial-mark"><i></i> 01 / ADD TO TRIP</div>
            <h3 style={{ fontSize: '1.6rem', marginBottom: '0.35rem' }}>
              Add to Existing Journey
            </h3>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', marginBottom: '1.5rem' }}>
              Select one of your planned trips to append <strong>{place.name}</strong> into its day-by-day itinerary.
            </p>

            {/* Place summary banner */}
            <div className="modal-place-banner">
              {place.image_url && (
                <img
                  src={place.image_url}
                  alt={place.name}
                  className="modal-place-thumb"
                  loading="lazy"
                />
              )}
              <div>
                <span className="category-tag-badge" style={{ marginBottom: '0.2rem' }}>
                  {place.category}
                </span>
                <h4 style={{ margin: 0, fontSize: '1.1rem' }}>{place.name}</h4>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.3rem', fontSize: '0.775rem', color: 'var(--text-secondary)', marginTop: '0.2rem' }}>
                  <MapPin size={11} />
                  <span>{place.location}</span>
                </div>
              </div>
            </div>

            {loadingTrips ? (
              <div style={{ padding: '2rem', textAlign: 'center' }}>
                <div className="spinner spinner-sm" style={{ margin: '0 auto 0.5rem' }} />
                <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Loading your journeys...</p>
              </div>
            ) : trips.length === 0 ? (
              <div className="empty-state" style={{ padding: '2rem 1rem' }}>
                <Luggage size={28} style={{ color: 'var(--text-muted)', marginBottom: '0.5rem' }} />
                <h4>No planned trips found</h4>
                <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', margin: '0.25rem 0 1rem' }}>
                  Create your first trip to organize your discovered sights.
                </p>
                <Link to="/trips/new" className="btn btn-primary btn-sm" onClick={handleClose}>
                  <Plus size={13} />
                  <span>Create Trip Now</span>
                </Link>
              </div>
            ) : (
              <form onSubmit={handleAdd}>
                <div className="form-group">
                  <label className="form-label" htmlFor="select-trip">
                    SELECT DESTINATION TRIP <span style={{ color: 'var(--accent)' }}>*</span>
                  </label>
                  <select
                    id="select-trip"
                    className="form-select"
                    value={selectedTripId}
                    onChange={(e) => setSelectedTripId(e.target.value)}
                    required
                  >
                    {trips.map((t) => (
                      <option key={t._id} value={t._id}>
                        {t.title || t.destination} ({t.start_date} — {t.end_date}) [{t.status}]
                      </option>
                    ))}
                  </select>
                </div>

                <div className="form-grid-two">
                  <div className="form-group">
                    <label className="form-label" htmlFor="day-num">
                      ITINERARY DAY
                    </label>
                    <input
                      id="day-num"
                      type="number"
                      min="1"
                      max="30"
                      className="form-input"
                      value={dayNumber}
                      onChange={(e) => setDayNumber(e.target.value)}
                    />
                  </div>

                  <div className="form-group">
                    <label className="form-label" htmlFor="time-slot">
                      TIME / SCHEDULE
                    </label>
                    <input
                      id="time-slot"
                      type="text"
                      className="form-input"
                      placeholder="e.g. 10:00 AM"
                      value={timeSlot}
                      onChange={(e) => setTimeSlot(e.target.value)}
                    />
                  </div>
                </div>

                <div className="form-group">
                  <label className="form-label" htmlFor="est-cost">
                    ESTIMATED EXPENSE (USD)
                  </label>
                  <input
                    id="est-cost"
                    type="number"
                    step="any"
                    min="0"
                    className="form-input"
                    placeholder="0"
                    value={estimatedCost}
                    onChange={(e) => setEstimatedCost(e.target.value)}
                  />
                </div>

                <div className="form-actions" style={{ marginTop: '1.25rem', paddingTop: '1rem' }}>
                  <button type="button" className="btn btn-secondary" onClick={handleClose}>
                    Cancel
                  </button>
                  <button type="submit" className="btn btn-primary" disabled={submitting}>
                    {submitting ? 'Adding...' : 'Add to Trip'}
                  </button>
                </div>
              </form>
            )}
          </>
        )}
      </div>
    </div>
  );
};
