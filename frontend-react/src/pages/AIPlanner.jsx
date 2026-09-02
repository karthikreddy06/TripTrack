import { useState } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import {
  Sparkles,
  MapPin,
  Compass,
  CheckCircle2,
  Clock,
  Briefcase,
  Lightbulb,
  ArrowLeft,
  BookmarkPlus
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import { aiAPI, tripsAPI, itineraryAPI, extractErrorMessage } from '../services/api';
import { Alert } from '../components/Alert';

const INTEREST_OPTIONS = [
  'Culture & Heritage',
  'Local Cuisine & Food',
  'Nature & Landscapes',
  'Adventure & Hiking',
  'Beaches & Coastal',
  'Art & Museums',
  'Shopping & Markets',
  'Relaxation & Wellness',
  'Photography',
  'Nightlife & Music'
];

const STYLE_OPTIONS = [
  'Balanced',
  'Backpacker / Budget',
  'Luxury & Comfort',
  'Relaxed & Slow Travel',
  'Fast-paced / Highlights',
  'Family Friendly'
];

export const AIPlanner = () => {
  const { user } = useAuth();
  const { showSuccess, showError } = useToast();
  const navigate = useNavigate();
  const location = useLocation();

  const prefill = location.state?.prefill || {};

  const [formData, setFormData] = useState({
    destination: prefill.destination || '',
    days: 3,
    start_date: new Date().toISOString().split('T')[0],
    travelers: prefill.travelers || 1,
    budget: prefill.budget !== undefined ? String(prefill.budget) : '',
    interests: ['Culture & Heritage', 'Local Cuisine & Food'],
    travel_style: 'Balanced',
  });

  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState(null);
  const [generatedPlan, setGeneratedPlan] = useState(null);
  const [savingTrip, setSavingTrip] = useState(false);
  const [activeDayIndex, setActiveDayIndex] = useState(0);

  const toggleInterest = (interest) => {
    setFormData((prev) => {
      const exists = prev.interests.includes(interest);
      if (exists) {
        return { ...prev, interests: prev.interests.filter((i) => i !== interest) };
      }
      return { ...prev, interests: [...prev.interests, interest] };
    });
  };

  const handleGenerate = async (e) => {
    e.preventDefault();
    if (!formData.destination.trim()) {
      setError('Please enter a destination.');
      return;
    }

    try {
      setGenerating(true);
      setError(null);
      setGeneratedPlan(null);

      const plan = await aiAPI.planTrip({
        destination: formData.destination.trim(),
        days: parseInt(formData.days, 10) || 3,
        start_date: formData.start_date || undefined,
        travelers: parseInt(formData.travelers, 10) || 1,
        budget: formData.budget ? parseFloat(formData.budget) : undefined,
        interests: formData.interests,
        travel_style: formData.travel_style,
      });

      setGeneratedPlan(plan);
      setActiveDayIndex(0);
      showSuccess('AI Itinerary generated successfully!');
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setGenerating(false);
    }
  };

  // Convert AI generated plan into a real MongoDB Trip and activities
  const handleSaveAsTrip = async () => {
    if (!generatedPlan || !user?.user_id) return;

    try {
      setSavingTrip(true);

      const daysCount = generatedPlan.days || 3;
      const startDate = formData.start_date || new Date().toISOString().split('T')[0];
      const startD = new Date(startDate);
      const endD = new Date(startD);
      endD.setDate(startD.getDate() + (daysCount - 1));
      const endDate = endD.toISOString().split('T')[0];

      // 1. Create Trip
      const createdTrip = await tripsAPI.createTrip({
        user_id: user.user_id,
        destination: generatedPlan.destination,
        title: `${generatedPlan.destination} — ${formData.travel_style}`,
        start_date: startDate,
        end_date: endDate,
        status: 'planned',
        budget: parseFloat(formData.budget) || (daysCount * 150),
        travelers: parseInt(formData.travelers, 10) || 1,
        description: generatedPlan.summary,
        notes: `Packing:\n- ${generatedPlan.packing_list?.slice(0, 5).join('\n- ')}\n\nTips:\n- ${generatedPlan.travel_tips?.slice(0, 3).join('\n- ')}`,
      });

      const tripId = createdTrip.trip_id;

      // 2. Insert Activities into Itinerary
      if (generatedPlan.itinerary && Array.isArray(generatedPlan.itinerary)) {
        for (const day of generatedPlan.itinerary) {
          const actDate = day.date || startDate;
          if (day.activities && Array.isArray(day.activities)) {
            for (const act of day.activities) {
              await itineraryAPI.createActivity({
                trip_id: tripId,
                day_number: day.day,
                date: actDate,
                time: act.time || '09:00 AM',
                title: act.title,
                location: act.location || '',
                description: act.description || '',
                cost: parseFloat(act.estimated_cost) || 0,
              });
            }
          }
        }
      }

      showSuccess(`Trip to ${generatedPlan.destination} and all activities saved!`);
      navigate(`/trips/${tripId}`);
    } catch (err) {
      showError(extractErrorMessage(err));
    } finally {
      setSavingTrip(false);
    }
  };

  const formatCurrency = (val) =>
    new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      maximumFractionDigits: 0,
    }).format(val || 0);

  return (
    <div className="main-content">
      <Link
        to="/dashboard"
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '0.45rem',
          marginBottom: '1.5rem',
          color: 'var(--text-secondary)',
          fontWeight: 500,
          fontSize: '0.8rem',
          fontFamily: 'var(--font-mono)',
          textTransform: 'uppercase',
          letterSpacing: '0.04em',
        }}
      >
        <ArrowLeft size={14} />
        <span>Back to dashboard</span>
      </Link>

      <div className="dashboard-header">
        <div className="dashboard-title-group">
          <div className="editorial-mark">
            <i></i> 05 / AI TRAVEL PLANNER
          </div>
          <h1>
            Intelligent journeys, <br />
            <em>curated in seconds.</em>
          </h1>
          <p className="welcome-subtitle">
            Provide your destination, dates, budget, and travel interests. Our AI assistant will construct a full day-by-day itinerary, packing list, and budget breakdown.
          </p>
        </div>
      </div>

      {error && <Alert type="error" message={error} onClose={() => setError(null)} />}

      <div className="ai-planner-grid">
        {/* Left Form Panel */}
        <div className="card ai-form-card">
          <div className="form-header" style={{ marginBottom: '1.5rem' }}>
            <div className="editorial-mark"><i></i> PARAMETERS</div>
            <h3 style={{ fontSize: '1.5rem' }}>Trip Preferences</h3>
          </div>

          <form onSubmit={handleGenerate}>
            <div className="form-group">
              <label className="form-label" htmlFor="ai-destination">
                DESTINATION <span style={{ color: 'var(--accent)' }}>*</span>
              </label>
              <input
                id="ai-destination"
                type="text"
                className="form-input"
                placeholder="e.g. Kyoto, Japan or Amalfi Coast, Italy"
                value={formData.destination}
                onChange={(e) => setFormData({ ...formData, destination: e.target.value })}
                required
              />
            </div>

            <div className="form-grid-two">
              <div className="form-group">
                <label className="form-label" htmlFor="ai-days">
                  DURATION (DAYS)
                </label>
                <input
                  id="ai-days"
                  type="number"
                  min="1"
                  max="30"
                  className="form-input"
                  value={formData.days}
                  onChange={(e) => setFormData({ ...formData, days: e.target.value })}
                  required
                />
              </div>

              <div className="form-group">
                <label className="form-label" htmlFor="ai-start-date">
                  START DATE
                </label>
                <input
                  id="ai-start-date"
                  type="date"
                  className="form-input"
                  value={formData.start_date}
                  onChange={(e) => setFormData({ ...formData, start_date: e.target.value })}
                />
              </div>
            </div>

            <div className="form-grid-two">
              <div className="form-group">
                <label className="form-label" htmlFor="ai-travelers">
                  TRAVELERS
                </label>
                <input
                  id="ai-travelers"
                  type="number"
                  min="1"
                  max="50"
                  className="form-input"
                  value={formData.travelers}
                  onChange={(e) => setFormData({ ...formData, travelers: e.target.value })}
                />
              </div>

              <div className="form-group">
                <label className="form-label" htmlFor="ai-budget">
                  BUDGET CAP (USD)
                </label>
                <input
                  id="ai-budget"
                  type="number"
                  step="any"
                  min="0"
                  className="form-input"
                  placeholder="e.g. 2500"
                  value={formData.budget}
                  onChange={(e) => setFormData({ ...formData, budget: e.target.value })}
                />
              </div>
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="ai-style">
                TRAVEL STYLE
              </label>
              <select
                id="ai-style"
                className="form-select"
                value={formData.travel_style}
                onChange={(e) => setFormData({ ...formData, travel_style: e.target.value })}
              >
                {STYLE_OPTIONS.map((style) => (
                  <option key={style} value={style}>
                    {style}
                  </option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label className="form-label">INTERESTS & ACTIVITIES</label>
              <div className="interest-tags-container">
                {INTEREST_OPTIONS.map((interest) => {
                  const isSelected = formData.interests.includes(interest);
                  return (
                    <button
                      key={interest}
                      type="button"
                      className={`interest-tag-btn ${isSelected ? 'selected' : ''}`}
                      onClick={() => toggleInterest(interest)}
                    >
                      {isSelected && <CheckCircle2 size={12} />}
                      <span>{interest}</span>
                    </button>
                  );
                })}
              </div>
            </div>

            <button
              type="submit"
              className="btn btn-primary"
              style={{ width: '100%', marginTop: '1rem' }}
              disabled={generating}
            >
              {generating ? (
                <>
                  <span className="spinner" />
                  <span>Curating Itinerary...</span>
                </>
              ) : (
                <>
                  <Sparkles size={15} />
                  <span>Generate AI Itinerary</span>
                </>
              )}
            </button>
          </form>
        </div>

        {/* Right Output Panel */}
        <div className="ai-output-panel">
          {generating ? (
            <div className="card" style={{ padding: '4rem 2rem', textAlign: 'center' }}>
              <div className="spinner spinner-lg" style={{ margin: '0 auto 1.5rem' }} />
              <h3>Creating your personalized journey...</h3>
              <p style={{ color: 'var(--text-secondary)', maxWidth: '420px', margin: '0.5rem auto 0' }}>
                Analyzing top attractions, dining hotspots, and optimal daily pacing for {formData.destination || 'your destination'}.
              </p>
            </div>
          ) : generatedPlan ? (
            <div className="ai-plan-results">
              {/* Header Card */}
              <div className="card" style={{ marginBottom: '1.5rem' }}>
                <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem', marginBottom: '1rem' }}>
                  <div>
                    <div className="editorial-mark"><i></i> CURATED ITINERARY</div>
                    <h2 style={{ fontSize: '2rem' }}>{generatedPlan.destination}</h2>
                    <p style={{ color: 'var(--text-secondary)', marginTop: '0.4rem', fontSize: '0.95rem' }}>
                      {generatedPlan.summary}
                    </p>
                  </div>

                  <button
                    type="button"
                    className="btn btn-primary"
                    onClick={handleSaveAsTrip}
                    disabled={savingTrip}
                  >
                    {savingTrip ? (
                      <>
                        <span className="spinner" />
                        <span>Saving Trip...</span>
                      </>
                    ) : (
                      <>
                        <BookmarkPlus size={15} />
                        <span>Save to My Trips</span>
                      </>
                    )}
                  </button>
                </div>

                {/* Estimated Budget Cards */}
                {generatedPlan.budget_breakdown && (
                  <div className="category-breakdown-row" style={{ marginTop: '1rem' }}>
                    {Object.entries(generatedPlan.budget_breakdown).map(([cat, amt]) => (
                      <div key={cat} className="category-pill">
                        <span className="cat-name">{cat}</span>
                        <span className="cat-amount">{formatCurrency(amt)}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Day-by-Day Selector */}
              <div className="ai-day-tabs">
                {generatedPlan.itinerary.map((dayPlan, idx) => (
                  <button
                    key={dayPlan.day}
                    type="button"
                    className={`ai-day-tab ${activeDayIndex === idx ? 'active' : ''}`}
                    onClick={() => setActiveDayIndex(idx)}
                  >
                    DAY {dayPlan.day}
                  </button>
                ))}
              </div>

              {/* Active Day Activities */}
              {generatedPlan.itinerary[activeDayIndex] && (
                <div className="card" style={{ marginBottom: '1.5rem' }}>
                  <div style={{ borderBottom: '1px solid var(--border)', paddingBottom: '0.75rem', marginBottom: '1.25rem' }}>
                    <div className="editorial-mark">
                      <i></i> DAY {generatedPlan.itinerary[activeDayIndex].day}
                    </div>
                    <h3 style={{ fontSize: '1.4rem' }}>
                      {generatedPlan.itinerary[activeDayIndex].theme}
                    </h3>
                  </div>

                  <div className="timeline-activities-list">
                    {generatedPlan.itinerary[activeDayIndex].activities?.map((act, aIdx) => (
                      <div key={aIdx} className="timeline-activity-card">
                        <div className="activity-time-col">
                          <Clock size={13} style={{ color: 'var(--primary-green)' }} />
                          <span>{act.time}</span>
                        </div>
                        <div className="activity-content-col">
                          <div className="activity-header-row">
                            <h4 className="activity-title">{act.title}</h4>
                            {act.estimated_cost > 0 && (
                              <span className="activity-cost-tag">
                                {formatCurrency(act.estimated_cost)}
                              </span>
                            )}
                          </div>
                          {act.location && (
                            <div className="activity-location">
                              <MapPin size={12} />
                              <span>{act.location}</span>
                            </div>
                          )}
                          <p className="activity-desc">{act.description}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Packing List & Travel Tips */}
              <div className="form-grid-two">
                <div className="card">
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
                    <Briefcase size={16} style={{ color: 'var(--primary-green)' }} />
                    <h4 style={{ margin: 0, fontSize: '1.15rem' }}>Packing Checklist</h4>
                  </div>
                  <ul className="advice-tips-list">
                    {generatedPlan.packing_list?.map((item, idx) => (
                      <li key={idx}>
                        <CheckCircle2 size={13} style={{ color: 'var(--primary-green)', flexShrink: 0, marginTop: '3px' }} />
                        <span>{item}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                <div className="card">
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
                    <Lightbulb size={16} style={{ color: 'var(--primary-green)' }} />
                    <h4 style={{ margin: 0, fontSize: '1.15rem' }}>Local Travel Tips</h4>
                  </div>
                  <ul className="advice-tips-list">
                    {generatedPlan.travel_tips?.map((tip, idx) => (
                      <li key={idx}>
                        <Compass size={13} style={{ color: 'var(--primary-green)', flexShrink: 0, marginTop: '3px' }} />
                        <span>{tip}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>
          ) : (
            <div className="card empty-ai-placeholder">
              <div className="empty-icon-wrapper">
                <Sparkles size={24} />
              </div>
              <h3 className="empty-title">Ready to plan your escape?</h3>
              <p className="empty-desc">
                Fill out the preferences on the left and generate a complete travel itinerary with suggested timing, activities, estimated costs, and packing checklist.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
