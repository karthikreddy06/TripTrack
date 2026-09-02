import { useState, useEffect } from 'react';
import { useParams, useNavigate, useLocation, Link } from 'react-router-dom';
import { ArrowLeft, ArrowUpRight } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import { tripsAPI, extractErrorMessage } from '../services/api';
import { Alert } from '../components/Alert';

export const EditTrip = () => {
  const { id } = useParams();
  const location = useLocation();
  const navigate = useNavigate();
  const { user } = useAuth();
  const { showSuccess } = useToast();

  const [formData, setFormData] = useState({
    destination: '',
    title: '',
    start_date: '',
    end_date: '',
    status: 'planned',
    budget: '',
    travelers: 1,
    description: '',
    notes: '',
  });

  const [fetching, setFetching] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    const loadTripData = async () => {
      // 1. If passed via router state, use immediately
      if (location.state?.trip) {
        const t = location.state.trip;
        setFormData({
          destination: t.destination || '',
          title: t.title || '',
          start_date: t.start_date || '',
          end_date: t.end_date || '',
          status: t.status || 'planned',
          budget: t.budget !== undefined ? String(t.budget) : '',
          travelers: t.travelers || 1,
          description: t.description || '',
          notes: t.notes || '',
        });
        setFetching(false);
        return;
      }

      // 2. Otherwise fetch via single trip endpoint or user trips
      try {
        setFetching(true);
        const trip = await tripsAPI.getSingleTrip(id);
        setFormData({
          destination: trip.destination || '',
          title: trip.title || '',
          start_date: trip.start_date || '',
          end_date: trip.end_date || '',
          status: trip.status || 'planned',
          budget: trip.budget !== undefined ? String(trip.budget) : '',
          travelers: trip.travelers || 1,
          description: trip.description || '',
          notes: trip.notes || '',
        });
      } catch (err) {
        setError(extractErrorMessage(err));
      } finally {
        setFetching(false);
      }
    };

    loadTripData();
  }, [id, location.state, user?.user_id]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    if (error) setError(null);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    if (!formData.destination.trim()) {
      setError('Please enter a destination.');
      return;
    }

    if (!formData.start_date || !formData.end_date) {
      setError('Please select both start and end dates.');
      return;
    }

    if (formData.end_date < formData.start_date) {
      setError('End date cannot be earlier than start date.');
      return;
    }

    const numericBudget = parseFloat(formData.budget);
    if (isNaN(numericBudget) || numericBudget < 0) {
      setError('Budget must be a valid non-negative number.');
      return;
    }

    setSubmitting(true);

    try {
      await tripsAPI.updateTrip(id, {
        destination: formData.destination.trim(),
        title: formData.title.trim() || undefined,
        start_date: formData.start_date,
        end_date: formData.end_date,
        status: formData.status,
        budget: numericBudget,
        travelers: parseInt(formData.travelers, 10) || 1,
        description: formData.description.trim(),
        notes: formData.notes.trim(),
      });

      showSuccess(`Trip updated successfully!`);
      navigate(`/trips/${id}`);
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  if (fetching) {
    return (
      <div className="loading-container">
        <div className="spinner spinner-lg" />
        <p>Loading itinerary details...</p>
      </div>
    );
  }

  return (
    <div className="main-content">
      <div className="form-page-container">
        <Link
          to={`/trips/${id}`}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '0.45rem',
            marginBottom: '1.75rem',
            color: 'var(--text-secondary)',
            fontWeight: 500,
            fontSize: '0.8rem',
            fontFamily: 'var(--font-mono)',
            textTransform: 'uppercase',
            letterSpacing: '0.04em',
          }}
        >
          <ArrowLeft size={14} />
          <span>Back to trip details</span>
        </Link>

        <div className="card">
          <div className="form-header">
            <div className="editorial-mark">
              <i></i> 03 / MODIFY
            </div>
            <h1>Refine your journey.</h1>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.95rem' }}>
              Update dates, destination, budget, travelers, or notes for this itinerary.
            </p>
          </div>

          {error && <Alert type="error" message={error} onClose={() => setError(null)} />}

          <form onSubmit={handleSubmit}>
            <div className="form-grid-two">
              <div className="form-group">
                <label className="form-label" htmlFor="edit-destination">
                  DESTINATION <span style={{ color: 'var(--accent)' }}>*</span>
                </label>
                <input
                  id="edit-destination"
                  type="text"
                  name="destination"
                  className="form-input"
                  value={formData.destination}
                  onChange={handleChange}
                  required
                />
              </div>

              <div className="form-group">
                <label className="form-label" htmlFor="edit-title">
                  TRIP TITLE (OPTIONAL)
                </label>
                <input
                  id="edit-title"
                  type="text"
                  name="title"
                  className="form-input"
                  placeholder="e.g. Kyoto Autumn Tour"
                  value={formData.title}
                  onChange={handleChange}
                />
              </div>
            </div>

            <div className="form-grid-two">
              <div className="form-group">
                <label className="form-label" htmlFor="edit-start_date">
                  START DATE <span style={{ color: 'var(--accent)' }}>*</span>
                </label>
                <input
                  id="edit-start_date"
                  type="date"
                  name="start_date"
                  className="form-input"
                  value={formData.start_date}
                  onChange={handleChange}
                  required
                />
              </div>

              <div className="form-group">
                <label className="form-label" htmlFor="edit-end_date">
                  END DATE <span style={{ color: 'var(--accent)' }}>*</span>
                </label>
                <input
                  id="edit-end_date"
                  type="date"
                  name="end_date"
                  className="form-input"
                  value={formData.end_date}
                  min={formData.start_date}
                  onChange={handleChange}
                  required
                />
              </div>
            </div>

            <div className="form-grid-three">
              <div className="form-group">
                <label className="form-label" htmlFor="edit-status">
                  STATUS
                </label>
                <select
                  id="edit-status"
                  name="status"
                  className="form-select"
                  value={formData.status}
                  onChange={handleChange}
                >
                  <option value="planned">Planned</option>
                  <option value="ongoing">Ongoing</option>
                  <option value="completed">Completed</option>
                  <option value="cancelled">Cancelled</option>
                </select>
              </div>

              <div className="form-group">
                <label className="form-label" htmlFor="edit-budget">
                  BUDGET (USD) <span style={{ color: 'var(--accent)' }}>*</span>
                </label>
                <input
                  id="edit-budget"
                  type="number"
                  step="any"
                  min="0"
                  name="budget"
                  className="form-input"
                  value={formData.budget}
                  onChange={handleChange}
                  required
                />
              </div>

              <div className="form-group">
                <label className="form-label" htmlFor="edit-travelers">
                  TRAVELERS
                </label>
                <input
                  id="edit-travelers"
                  type="number"
                  min="1"
                  max="100"
                  name="travelers"
                  className="form-input"
                  value={formData.travelers}
                  onChange={handleChange}
                />
              </div>
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="edit-description">
                TRIP OVERVIEW / SUMMARY (OPTIONAL)
              </label>
              <textarea
                id="edit-description"
                name="description"
                className="form-input"
                rows={2}
                placeholder="Brief summary of highlights or companion notes..."
                value={formData.description}
                onChange={handleChange}
              />
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="edit-notes">
                PACKING & PREPARATION NOTES (OPTIONAL)
              </label>
              <textarea
                id="edit-notes"
                name="notes"
                className="form-input"
                rows={3}
                placeholder="Flight codes, booking refs, visa notes, emergency contacts..."
                value={formData.notes}
                onChange={handleChange}
              />
            </div>

            <div className="form-actions">
              <Link to={`/trips/${id}`} className="btn btn-secondary">
                Cancel
              </Link>
              <button
                type="submit"
                className="btn btn-primary"
                disabled={submitting}
              >
                {submitting ? (
                  <>
                    <span className="spinner" />
                    <span>Updating...</span>
                  </>
                ) : (
                  <>
                    <span>Update trip</span>
                    <ArrowUpRight size={15} />
                  </>
                )}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};
