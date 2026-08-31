import { useState, useEffect } from 'react';
import { useParams, useNavigate, useLocation, Link } from 'react-router-dom';
import { ArrowLeft, ArrowUpRight } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { tripsAPI, extractErrorMessage } from '../services/api';
import { Alert } from '../components/Alert';

export const EditTrip = () => {
  const { id } = useParams();
  const location = useLocation();
  const navigate = useNavigate();
  const { user } = useAuth();

  const [formData, setFormData] = useState({
    destination: '',
    start_date: '',
    end_date: '',
    status: 'planned',
    budget: '',
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
          start_date: t.start_date || '',
          end_date: t.end_date || '',
          status: t.status || 'planned',
          budget: t.budget !== undefined ? String(t.budget) : '',
        });
        setFetching(false);
        return;
      }

      // 2. Otherwise, fetch user trips and locate by id
      if (!user?.user_id) return;

      try {
        setFetching(true);
        const trips = await tripsAPI.getTrips(user.user_id);
        const match = trips.find((t) => t._id === id);
        if (!match) {
          setError('Trip not found or you do not have permission to edit it.');
        } else {
          setFormData({
            destination: match.destination || '',
            start_date: match.start_date || '',
            end_date: match.end_date || '',
            status: match.status || 'planned',
            budget: match.budget !== undefined ? String(match.budget) : '',
          });
        }
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
        start_date: formData.start_date,
        end_date: formData.end_date,
        status: formData.status,
        budget: numericBudget,
      });

      navigate('/trips');
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
          to="/trips"
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
          <span>Back to itineraries</span>
        </Link>

        <div className="card">
          <div className="form-header">
            <div className="editorial-mark">
              <i></i> 03 / MODIFY
            </div>
            <h1>Refine your journey.</h1>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.95rem' }}>
              Update dates, destination, budget, or status for this itinerary.
            </p>
          </div>

          {error && <Alert type="error" message={error} onClose={() => setError(null)} />}

          <form onSubmit={handleSubmit}>
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

            <div className="form-grid-two">
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
            </div>

            <div className="form-actions">
              <Link to="/trips" className="btn btn-secondary">
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
