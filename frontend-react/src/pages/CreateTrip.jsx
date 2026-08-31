import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { ArrowLeft, ArrowUpRight } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { tripsAPI, extractErrorMessage } from '../services/api';
import { Alert } from '../components/Alert';

export const CreateTrip = () => {
  const { user } = useAuth();
  const navigate = useNavigate();

  const today = new Date().toISOString().split('T')[0];

  const [formData, setFormData] = useState({
    destination: '',
    start_date: today,
    end_date: today,
    status: 'planned',
    budget: '',
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
      await tripsAPI.createTrip({
        user_id: user.user_id,
        destination: formData.destination.trim(),
        start_date: formData.start_date,
        end_date: formData.end_date,
        status: formData.status,
        budget: numericBudget,
      });

      // Redirect to trips page
      navigate('/trips');
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

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
              <i></i> 03 / NEW ITINERARY
            </div>
            <h1>Plan a new journey.</h1>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.95rem' }}>
              Define destination, dates, budget cap, and tracking status.
            </p>
          </div>

          {error && <Alert type="error" message={error} onClose={() => setError(null)} />}

          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label className="form-label" htmlFor="destination">
                DESTINATION <span style={{ color: 'var(--accent)' }}>*</span>
              </label>
              <input
                id="destination"
                type="text"
                name="destination"
                className="form-input"
                placeholder="e.g. Kyoto, Japan or Paris, France"
                value={formData.destination}
                onChange={handleChange}
                required
              />
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

            <div className="form-grid-two">
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
                <span className="helper-text">Initial status for this itinerary.</span>
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
                <span className="helper-text">Estimated expense cap.</span>
              </div>
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
