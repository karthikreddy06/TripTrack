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
  CameraOff,
  Sparkles,
  Users
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import { tripsAPI, itineraryAPI, resolveImageUrl, extractErrorMessage } from '../services/api';

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

const getFutureDateString = (daysAhead = 0) => {
  const dt = new Date();
  dt.setDate(dt.getDate() + daysAhead);
  const y = dt.getFullYear();
  const m = String(dt.getMonth() + 1).padStart(2, '0');
  const d = String(dt.getDate()).padStart(2, '0');
  return `${y}-${m}-${d}`;
};

export const AddToTripModal = ({ isOpen, onClose, place }) => {
  const { user, isAuthenticated } = useAuth();
  const { showSuccess, showError } = useToast();

  const [mode, setMode] = useState('existing'); // 'existing' | 'create'
  const [trips, setTrips] = useState([]);
  const [loadingTrips, setLoadingTrips] = useState(true);
  const [selectedTripId, setSelectedTripId] = useState('');
  const [dayNumber, setDayNumber] = useState(1);
  const [timeSlot, setTimeSlot] = useState('10:00 AM');
  const [estimatedCost, setEstimatedCost] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [addedSuccessTrip, setAddedSuccessTrip] = useState(null);

  // New Trip Form State
  const [newTripTitle, setNewTripTitle] = useState('');
  const [newTripDestination, setNewTripDestination] = useState('');
  const [newTripStartDate, setNewTripStartDate] = useState(getFutureDateString(7));
  const [newTripEndDate, setNewTripEndDate] = useState(getFutureDateString(11));
  const [newTripBudget, setNewTripBudget] = useState('2000');
  const [newTripTravelers, setNewTripTravelers] = useState('2');

  useEffect(() => {
    if (place) {
      const dest = place.location || place.address || place.name || '';
      setNewTripDestination(dest.split(',')[0].trim());
      setNewTripTitle(`Journey to ${dest.split(',')[0].trim() || 'New Destination'}`);
    }
  }, [place]);

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
          setMode('existing');
        } else {
          setMode('create');
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

  // Handle adding to EXISTING trip
  const handleAddToExistingTrip = async (e) => {
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

  // Handle CREATING A NEW TRIP & adding the place directly from Explore
  const handleCreateNewTripAndAdd = async (e) => {
    e.preventDefault();
    if (!newTripDestination.trim()) {
      showError('Please enter a trip destination.');
      return;
    }

    try {
      setSubmitting(true);

      // 1. Create Trip in MongoDB
      const tripRes = await tripsAPI.createTrip({
        user_id: user.user_id,
        destination: newTripDestination.trim(),
        title: newTripTitle.trim() || `Journey to ${newTripDestination.trim()}`,
        start_date: newTripStartDate,
        end_date: newTripEndDate,
        budget: parseFloat(newTripBudget) || 0,
        travelers: parseInt(newTripTravelers, 10) || 1,
        description: `Created directly from TravelTrack Explore while discovering ${place.name}.`,
      });

      const newTripId = tripRes.trip_id;

      // 2. Add Place to Day 1 of the new trip
      await itineraryAPI.createActivity({
        trip_id: newTripId,
        day_number: 1,
        date: newTripStartDate,
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

      const newlyCreatedTripObj = {
        _id: newTripId,
        destination: newTripDestination.trim(),
        title: newTripTitle.trim() || `Journey to ${newTripDestination.trim()}`,
        start_date: newTripStartDate,
        end_date: newTripEndDate,
      };

      showSuccess(`Created "${newlyCreatedTripObj.title}" and added "${place.name}"!`);
      setAddedSuccessTrip(newlyCreatedTripObj);
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

  const rawPhoto = place.image_url || (place.photos && place.photos.length > 0 ? place.photos[0] : null);
  const placeImg = resolveImageUrl(rawPhoto);

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
              Added to Journey!
            </h3>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.95rem', marginBottom: '1.75rem' }}>
              <strong>{place.name}</strong> is now saved in your itinerary for{' '}
              <strong>{addedSuccessTrip.title || addedSuccessTrip.destination}</strong>.
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
        ) : !isAuthenticated ? (
          <div style={{ textAlign: 'center', padding: '1.5rem 0.5rem' }}>
            <div className="empty-icon-wrapper" style={{ margin: '0 auto 1rem' }}>
              <Luggage size={28} />
            </div>
            <h3 style={{ fontSize: '1.5rem', marginBottom: '0.5rem' }}>Sign In to Plan Trips</h3>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: '1.5rem' }}>
              Create an account or sign in to save <strong>{place.name}</strong> into your custom journeys and day-by-day itineraries.
            </p>
            <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'center' }}>
              <Link to="/login" className="btn btn-secondary" onClick={handleClose}>
                Sign In
              </Link>
              <Link to="/register" className="btn btn-primary" onClick={handleClose}>
                <span>Register Account</span>
                <ArrowUpRight size={14} />
              </Link>
            </div>
          </div>
        ) : (
          <>
            <div className="editorial-mark"><i></i> 01 / ADD TO TRIP</div>
            <h3 style={{ fontSize: '1.6rem', marginBottom: '0.35rem' }}>
              Add to Journey
            </h3>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', marginBottom: '1.25rem' }}>
              Schedule <strong>{place.name}</strong> into an existing itinerary or create a new trip immediately.
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

            {/* Mode Switcher Tabs */}
            <div className="explore-category-tabs" style={{ marginBottom: '1.25rem' }}>
              <button
                type="button"
                className={`explore-cat-tab ${mode === 'existing' ? 'active' : ''}`}
                onClick={() => setMode('existing')}
                disabled={trips.length === 0}
              >
                <Luggage size={13} />
                <span>Existing Trips ({trips.length})</span>
              </button>
              <button
                type="button"
                className={`explore-cat-tab ${mode === 'create' ? 'active' : ''}`}
                onClick={() => setMode('create')}
              >
                <Plus size={13} />
                <span>+ Create New Trip</span>
              </button>
            </div>

            {/* ================================================== */}
            {/* MODE 1: EXISTING TRIP SELECTION                    */}
            {/* ================================================== */}
            {mode === 'existing' && (
              <>
                {loadingTrips ? (
                  <div style={{ padding: '2rem', textAlign: 'center' }}>
                    <div className="spinner spinner-sm" style={{ margin: '0 auto 0.5rem' }} />
                    <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Loading your journeys...</p>
                  </div>
                ) : trips.length === 0 ? (
                  <div className="empty-state" style={{ padding: '1.5rem 1rem' }}>
                    <Luggage size={24} style={{ color: 'var(--text-muted)', marginBottom: '0.5rem' }} />
                    <h4>No planned trips yet</h4>
                    <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', margin: '0.25rem 0 1rem' }}>
                      Create a new trip to begin scheduling places.
                    </p>
                    <button type="button" className="btn btn-primary btn-sm" onClick={() => setMode('create')}>
                      <Plus size={13} />
                      <span>Create Trip Now</span>
                    </button>
                  </div>
                ) : (
                  <form onSubmit={handleAddToExistingTrip}>
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

            {/* ================================================== */}
            {/* MODE 2: CREATE NEW TRIP DIRECTLY FROM EXPLORE     */}
            {/* ================================================== */}
            {mode === 'create' && (
              <form onSubmit={handleCreateNewTripAndAdd}>
                <div className="form-group">
                  <label className="form-label" htmlFor="new-trip-title">
                    JOURNEY TITLE <span style={{ color: 'var(--accent)' }}>*</span>
                  </label>
                  <input
                    id="new-trip-title"
                    type="text"
                    className="form-input"
                    placeholder="e.g. Goa Coastal Escape 2026"
                    value={newTripTitle}
                    onChange={(e) => setNewTripTitle(e.target.value)}
                    required
                  />
                </div>

                <div className="form-group">
                  <label className="form-label" htmlFor="new-trip-dest">
                    DESTINATION / CITY <span style={{ color: 'var(--accent)' }}>*</span>
                  </label>
                  <input
                    id="new-trip-dest"
                    type="text"
                    className="form-input"
                    placeholder="e.g. Goa, India"
                    value={newTripDestination}
                    onChange={(e) => setNewTripDestination(e.target.value)}
                    required
                  />
                </div>

                <div className="form-grid-two">
                  <div className="form-group">
                    <label className="form-label" htmlFor="new-trip-start">
                      <Calendar size={12} style={{ display: 'inline', marginRight: '4px' }} />
                      START DATE
                    </label>
                    <input
                      id="new-trip-start"
                      type="date"
                      className="form-input"
                      value={newTripStartDate}
                      onChange={(e) => setNewTripStartDate(e.target.value)}
                      required
                    />
                  </div>

                  <div className="form-group">
                    <label className="form-label" htmlFor="new-trip-end">
                      <Calendar size={12} style={{ display: 'inline', marginRight: '4px' }} />
                      END DATE
                    </label>
                    <input
                      id="new-trip-end"
                      type="date"
                      className="form-input"
                      value={newTripEndDate}
                      onChange={(e) => setNewTripEndDate(e.target.value)}
                      required
                    />
                  </div>
                </div>

                <div className="form-grid-two">
                  <div className="form-group">
                    <label className="form-label" htmlFor="new-trip-budget">
                      <DollarSign size={12} style={{ display: 'inline', marginRight: '4px' }} />
                      BUDGET (USD)
                    </label>
                    <input
                      id="new-trip-budget"
                      type="number"
                      min="0"
                      className="form-input"
                      value={newTripBudget}
                      onChange={(e) => setNewTripBudget(e.target.value)}
                    />
                  </div>

                  <div className="form-group">
                    <label className="form-label" htmlFor="new-trip-travelers">
                      <Users size={12} style={{ display: 'inline', marginRight: '4px' }} />
                      TRAVELERS
                    </label>
                    <input
                      id="new-trip-travelers"
                      type="number"
                      min="1"
                      max="50"
                      className="form-input"
                      value={newTripTravelers}
                      onChange={(e) => setNewTripTravelers(e.target.value)}
                    />
                  </div>
                </div>

                <div className="form-actions" style={{ marginTop: '1.25rem', paddingTop: '1rem' }}>
                  <button type="button" className="btn btn-secondary" onClick={handleClose}>
                    Cancel
                  </button>
                  <button type="submit" className="btn btn-primary" disabled={submitting}>
                    <Sparkles size={13} />
                    <span>{submitting ? 'Creating Journey & Saving...' : 'Create Trip & Add Place'}</span>
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
