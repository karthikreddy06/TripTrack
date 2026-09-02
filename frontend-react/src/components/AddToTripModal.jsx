import { useState, useEffect, useMemo } from 'react';
import { Link } from 'react-router-dom';
import {
  Plus,
  CheckCircle2,
  X,
  MapPin,
  ArrowUpRight,
  Luggage,
  Clock,
  Calendar,
  DollarSign,
  CameraOff
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import { tripsAPI, itineraryAPI, extractErrorMessage } from '../services/api';

const calculateIsoDateForDay = (startDateStr, dayNum) => {
  if (!startDateStr) return new Date().toISOString().split('T')[0];
  try {
    const parts = startDateStr.split('-').map(Number);
    if (parts.length !== 3 || parts.some(isNaN)) return startDateStr;
    const [y, m, d] = parts;
    const target = new Date(y, m - 1, d + (dayNum - 1));
    const targetY = target.getFullYear();
    const targetM = String(target.getMonth() + 1).padStart(2, '0');
    const targetD = String(target.getDate()).padStart(2, '0');
    return `${targetY}-${targetM}-${targetD}`;
  } catch {
    return startDateStr;
  }
};

const formatReadableDate = (dateStr) => {
  if (!dateStr) return '';
  try {
    const [y, m, d] = dateStr.split('-').map(Number);
    const dt = new Date(y, m - 1, d);
    return dt.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  } catch {
    return dateStr;
  }
};

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

        if (list.length > 0) {
          const matching = place?.location
            ? list.find(
                (t) =>
                  place.location.toLowerCase().includes(t.destination.toLowerCase()) ||
                  t.destination.toLowerCase().includes(place.location.toLowerCase())
              )
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
  }, [isOpen, user?.user_id, place?.location, showError]);

  const selectedTrip = trips.find((t) => t._id === selectedTripId);

  // Compute available days for the selected trip
  const tripDayOptions = useMemo(() => {
    if (!selectedTrip?.start_date || !selectedTrip?.end_date) {
      return [{ dayNum: 1, dateStr: new Date().toISOString().split('T')[0] }];
    }
    try {
      const [y1, m1, d1] = selectedTrip.start_date.split('-').map(Number);
      const [y2, m2, d2] = selectedTrip.end_date.split('-').map(Number);
      const start = new Date(y1, m1 - 1, d1);
      const end = new Date(y2, m2 - 1, d2);
      const diffTime = Math.max(0, end - start);
      const totalDays = Math.min(Math.ceil(diffTime / (1000 * 60 * 60 * 24)) + 1, 30);

      const options = [];
      for (let i = 1; i <= totalDays; i++) {
        options.push({
          dayNum: i,
          dateStr: calculateIsoDateForDay(selectedTrip.start_date, i),
        });
      }
      return options;
    } catch {
      return [{ dayNum: 1, dateStr: selectedTrip.start_date }];
    }
  }, [selectedTrip]);

  if (!isOpen || !place) return null;

  const handleAdd = async (e) => {
    e.preventDefault();
    if (!selectedTripId) {
      showError('Please select a trip or create a new one first.');
      return;
    }

    try {
      setSubmitting(true);

      const chosenDayNum = parseInt(dayNumber, 10) || 1;
      const activityDate = calculateIsoDateForDay(selectedTrip?.start_date, chosenDayNum);

      const res = await itineraryAPI.createActivity({
        trip_id: selectedTripId,
        day_number: chosenDayNum,
        date: activityDate,
        time: timeSlot || '10:00 AM',
        title: place.name ? place.name.trim().slice(0, 150) : 'Discovered Place',
        location: (place.address || place.location || '').slice(0, 250),
        description: (place.description || `${place.category?.toUpperCase() || 'PLACE'} in ${place.location || ''}`).slice(0, 900),
        cost: estimatedCost ? parseFloat(estimatedCost) : 0,
        notes: place.category ? `Discovered on TravelTrack Explore (${place.category})` : '',
        place_id: place.place_id || place.provider_place_id || null,
        category: place.category || null,
        image_url: place.image_url || (place.photos && place.photos[0]) || null,
      });

      if (res.already_exists) {
        showSuccess(`"${place.name}" is already scheduled for Day ${chosenDayNum} in ${selectedTrip.title || selectedTrip.destination}.`);
      } else {
        showSuccess(`Added "${place.name}" to ${selectedTrip.title || selectedTrip.destination}!`);
      }

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

  const placeImg = place.image_url || (place.photos && place.photos.length > 0 ? place.photos[0] : null);

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
              {placeImg ? (
                <img
                  src={placeImg}
                  alt={place.name}
                  className="modal-place-thumb"
                  loading="lazy"
                />
              ) : (
                <div className="modal-place-thumb" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--surface)', border: '1px solid var(--border)' }}>
                  <CameraOff size={18} style={{ color: 'var(--text-muted)' }} />
                </div>
              )}
              <div>
                <span className="category-tag-badge" style={{ marginBottom: '0.2rem' }}>
                  {place.category}
                </span>
                <h4 style={{ margin: 0, fontSize: '1.1rem' }}>{place.name}</h4>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.3rem', fontSize: '0.775rem', color: 'var(--text-secondary)', marginTop: '0.2rem' }}>
                  <MapPin size={11} />
                  <span>{place.address || place.location}</span>
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
                    onChange={(e) => {
                      setSelectedTripId(e.target.value);
                      setDayNumber(1);
                    }}
                    required
                  >
                    {trips.map((t) => (
                      <option key={t._id} value={t._id}>
                        {t.title || t.destination} ({t.start_date} — {t.end_date}) [{t.status?.toUpperCase()}]
                      </option>
                    ))}
                  </select>
                </div>

                <div className="form-grid-two">
                  <div className="form-group">
                    <label className="form-label" htmlFor="day-num">
                      <Calendar size={12} style={{ display: 'inline', marginRight: '4px' }} />
                      SCHEDULE DAY
                    </label>
                    <select
                      id="day-num"
                      className="form-select"
                      value={dayNumber}
                      onChange={(e) => setDayNumber(parseInt(e.target.value, 10))}
                    >
                      {tripDayOptions.map((opt) => (
                        <option key={opt.dayNum} value={opt.dayNum}>
                          Day {opt.dayNum} ({formatReadableDate(opt.dateStr)})
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="form-group">
                    <label className="form-label" htmlFor="time-slot">
                      <Clock size={12} style={{ display: 'inline', marginRight: '4px' }} />
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
                    <DollarSign size={12} style={{ display: 'inline', marginRight: '4px' }} />
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
                    {submitting ? 'Persisting to Trip...' : 'Add to Trip'}
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
