import { useState } from 'react';
import { useNavigate, Link, useLocation } from 'react-router-dom';
import { ArrowLeft, ArrowUpRight, Sparkles } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import { tripsAPI, extractErrorMessage } from '../services/api';
import { Alert } from '../components/Alert';

export const CreateTrip = () => {
  const { user } = useAuth();
  const { showSuccess } = useToast();
  const navigate = useNavigate();
  const location = useLocation();

  // Prefill state if coming from AI Trip Planner
  const initialData = location.state?.prefill || {};

  const today = new Date().toISOString().split('T')[0];

  const [formData, setFormData] = useState({
    destination: initialData.destination || '',
    title: initialData.title || '',
    start_date: initialData.start_date || today,
    end_date: initialData.end_date || today,
    status: initialData.status || 'planned',
    budget: initialData.budget !== undefined ? String(initialData.budget) : '',
    travelers: initialData.travelers || 1,
    description: initialData.description || '',
    notes: initialData.notes || '',
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    if (error) setError(null);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    // Client validations matching backend constraints
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

    if (!user?.user_id) {
      setError('User session not found. Please log in again.');
      return;
    }

    setLoading(true);

    try {
      const created = await tripsAPI.createTrip({
        user_id: user.user_id,
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

      showSuccess(`Trip to ${formData.destination} created successfully!`);
      navigate(`/trips/${created.trip_id}`);
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="main-content">
      <div className="form-page-container">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.75rem' }}>
          <Link
            to="/trips"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.45rem',
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

          <Link
            to="/ai-planner"
            className="btn btn-secondary btn-sm"
            style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}
          >
            <Sparkles size={13} style={{ color: 'var(--primary-green)' }} />
            <span>Try AI Planner</span>
          </Link>
        </div>

        <div className="card">
          <div className="form-header">
            <div className="editorial-mark">
              <i></i> 03 / NEW ITINERARY
            </div>
            <h1>Plan a new journey.</h1>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.95rem' }}>
              Define destination, dates, budget cap, travelers, and personal notes.
            </p>
          </div>

          {error && <Alert type="error" message={error} onClose={() => setError(null)} />}

          <form onSubmit={handleSubmit}>
            <div className="form-grid-two">
              <div className="form-group">
                <label className="form-label" htmlFor="destination">
                  DESTINATION <span style={{ color: 'var(--accent)' }}>*</span>
                </label>
                <input
                  id="destination"
                  type="text"
                  name="destination"
                  className="form-input"
                  placeholder="e.g. Kyoto, Japan or Amalfi Coast, Italy"
                  value={formData.destination}
                  onChange={handleChange}
                  required
                />
              </div>

              <div className="form-group">
                <label className="form-label" htmlFor="title">
                  TRIP TITLE (OPTIONAL)
                </label>
                <input
                  id="title"
                  type="text"
                  name="title"
                  className="form-input"
                  placeholder="e.g. Autumn Blossoms Tour"
                  value={formData.title}
                  onChange={handleChange}
                />
              </div>
            </div>

            <div className="form-grid-two">
              <div className="form-group">
                <label className="form-label" htmlFor="start_date">
                  START DATE <span style={{ color: 'var(--accent)' }}>*</span>
                </label>
                <input
                  id="start_date"
                  type="date"
                  name="start_date"
                  className="form-input"
                  value={formData.start_date}
                  onChange={handleChange}
                  required
                />
              </div>

              <div className="form-group">
                <label className="form-label" htmlFor="end_date">
                  END DATE <span style={{ color: 'var(--accent)' }}>*</span>
                </label>
                <input
                  id="end_date"
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
                <label className="form-label" htmlFor="status">
                  STATUS
                </label>
                <select
                  id="status"
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
                <label className="form-label" htmlFor="budget">
                  BUDGET (USD) <span style={{ color: 'var(--accent)' }}>*</span>
                </label>
                <input
                  id="budget"
                  type="number"
                  step="any"
                  min="0"
                  name="budget"
                  className="form-input"
                  placeholder="e.g. 2400"
                  value={formData.budget}
                  onChange={handleChange}
                  required
                />
              </div>

              <div className="form-group">
                <label className="form-label" htmlFor="travelers">
                  TRAVELERS
                </label>
                <input
                  id="travelers"
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
              <label className="form-label" htmlFor="description">
                TRIP OVERVIEW / SUMMARY (OPTIONAL)
              </label>
              <textarea
                id="description"
                name="description"
                className="form-input"
                rows={2}
                placeholder="Brief summary of highlights, purpose of travel, or companion notes..."
                value={formData.description}
                onChange={handleChange}
              />
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="notes">
                PACKING & PREPARATION NOTES (OPTIONAL)
              </label>
              <textarea
                id="notes"
                name="notes"
                className="form-input"
                rows={3}
                placeholder="Flight codes, booking refs, visa notes, emergency contacts..."
                value={formData.notes}
                onChange={handleChange}
              />
            </div>

            <div className="form-actions">
              <Link to="/trips" className="btn btn-secondary">
                Cancel
              </Link>
              <button
                type="submit"
                className="btn btn-primary"
                disabled={loading}
              >
                {loading ? (
                  <>
                    <span className="spinner" />
                    <span>Creating...</span>
                  </>
                ) : (
                  <>
                    <span>Create trip</span>
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
