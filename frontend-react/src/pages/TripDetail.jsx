import { useState, useEffect, useMemo, useCallback } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import {
  Calendar,
  DollarSign,
  Plus,
  ArrowLeft,
  Clock,
  MapPin,
  Tag,
  Trash2,
  Edit2,
  Sparkles,
  Users,
  Compass,
  CreditCard,
  FileText,
  AlertTriangle,
  Lightbulb,
  Check
} from 'lucide-react';
import { useToast } from '../context/ToastContext';
import { tripsAPI, itineraryAPI, expensesAPI, aiAPI, extractErrorMessage } from '../services/api';
import { StatusBadge } from '../components/StatusBadge';
import { DeleteModal } from '../components/DeleteModal';

export const TripDetail = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { showSuccess, showError } = useToast();

  const [trip, setTrip] = useState(null);
  const [activities, setActivities] = useState([]);
  const [expenses, setExpenses] = useState([]);
  const [budgetSummary, setBudgetSummary] = useState(null);

  const [activeTab, setActiveTab] = useState('itinerary'); // 'itinerary' | 'budget' | 'overview'
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Modals state
  const [isActivityModalOpen, setIsActivityModalOpen] = useState(false);
  const [editingActivity, setEditingActivity] = useState(null);
  const [activityForm, setActivityForm] = useState({
    day_number: 1,
    date: '',
    time: '09:00 AM',
    title: '',
    location: '',
    description: '',
    cost: '',
    notes: '',
  });
  const [activitySaving, setActivitySaving] = useState(false);

  const [isExpenseModalOpen, setIsExpenseModalOpen] = useState(false);
  const [editingExpense, setEditingExpense] = useState(null);
  const [expenseForm, setExpenseForm] = useState({
    category: 'Food',
    amount: '',
    date: '',
    description: '',
  });
  const [expenseSaving, setExpenseSaving] = useState(false);

  // Delete trip state
  const [tripToDelete, setTripToDelete] = useState(null);
  const [isDeletingTrip, setIsDeletingTrip] = useState(false);

  // AI Budget Advice state
  const [aiBudgetAdvice, setAiBudgetAdvice] = useState(null);
  const [loadingAiAdvice, setLoadingAiAdvice] = useState(false);

  const fetchTripData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const [tripData, actData, expData] = await Promise.all([
        tripsAPI.getSingleTrip(id),
        itineraryAPI.getTripActivities(id),
        expensesAPI.getTripExpenses(id),
      ]);

      setTrip(tripData);
      setActivities(actData || []);
      setExpenses(expData.expenses || []);
      setBudgetSummary(expData.summary || null);

      // Default date for new activity/expense
      const tripStart = tripData.start_date || new Date().toISOString().split('T')[0];
      setActivityForm((prev) => ({ ...prev, date: tripStart }));
      setExpenseForm((prev) => ({ ...prev, date: tripStart }));
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchTripData();
  }, [fetchTripData]);

  // Handle Trip Deletion
  const handleConfirmDeleteTrip = async () => {
    try {
      setIsDeletingTrip(true);
      await tripsAPI.deleteTrip(id);
      showSuccess(`Trip to ${trip.destination} was deleted.`);
      navigate('/trips');
    } catch (err) {
      showError(extractErrorMessage(err));
    } finally {
      setIsDeletingTrip(false);
      setTripToDelete(null);
    }
  };

  // Activity Handlers
  const handleOpenAddActivity = (dayNum, dayDate) => {
    setEditingActivity(null);
    setActivityForm({
      day_number: dayNum || 1,
      date: dayDate || trip?.start_date || '',
      time: '09:00 AM',
      title: '',
      location: '',
      description: '',
      cost: '',
      notes: '',
    });
    setIsActivityModalOpen(true);
  };

  const handleOpenEditActivity = (act) => {
    setEditingActivity(act);
    setActivityForm({
      day_number: act.day_number || 1,
      date: act.date || '',
      time: act.time || '',
      title: act.title || '',
      location: act.location || '',
      description: act.description || '',
      cost: act.cost !== undefined ? String(act.cost) : '',
      notes: act.notes || '',
    });
    setIsActivityModalOpen(true);
  };

  const handleSaveActivity = async (e) => {
    e.preventDefault();
    if (!activityForm.title.trim() || !activityForm.date) {
      showError('Please provide a title and date for the activity.');
      return;
    }

    try {
      setActivitySaving(true);
      if (editingActivity) {
        await itineraryAPI.updateActivity(editingActivity._id, activityForm);
        showSuccess('Activity updated.');
      } else {
        await itineraryAPI.createActivity({
          trip_id: id,
          ...activityForm,
        });
        showSuccess('Activity added to itinerary.');
      }
      setIsActivityModalOpen(false);
      const acts = await itineraryAPI.getTripActivities(id);
      setActivities(acts);
    } catch (err) {
      showError(extractErrorMessage(err));
    } finally {
      setActivitySaving(false);
    }
  };

  const handleDeleteActivity = async (activityId) => {
    if (!window.confirm('Delete this activity from your itinerary?')) return;
    try {
      await itineraryAPI.deleteActivity(activityId);
      setActivities((prev) => prev.filter((a) => a._id !== activityId));
      showSuccess('Activity removed.');
    } catch (err) {
      showError(extractErrorMessage(err));
    }
  };

  // Expense Handlers
  const handleOpenAddExpense = () => {
    setEditingExpense(null);
    setExpenseForm({
      category: 'Food',
      amount: '',
      date: trip?.start_date || new Date().toISOString().split('T')[0],
      description: '',
    });
    setIsExpenseModalOpen(true);
  };

  const handleOpenEditExpense = (exp) => {
    setEditingExpense(exp);
    setExpenseForm({
      category: exp.category || 'Food',
      amount: exp.amount !== undefined ? String(exp.amount) : '',
      date: exp.date || '',
      description: exp.description || '',
    });
    setIsExpenseModalOpen(true);
  };

  const handleSaveExpense = async (e) => {
    e.preventDefault();
    const numAmt = parseFloat(expenseForm.amount);
    if (isNaN(numAmt) || numAmt <= 0) {
      showError('Please enter a valid expense amount greater than 0.');
      return;
    }
    if (!expenseForm.description.trim()) {
      showError('Please enter a description for this expense.');
      return;
    }

    try {
      setExpenseSaving(true);
      if (editingExpense) {
        await expensesAPI.updateExpense(editingExpense._id, expenseForm);
        showSuccess('Expense updated.');
      } else {
        await expensesAPI.createExpense({
          trip_id: id,
          ...expenseForm,
        });
        showSuccess('Expense recorded.');
      }
      setIsExpenseModalOpen(false);
      const expData = await expensesAPI.getTripExpenses(id);
      setExpenses(expData.expenses || []);
      setBudgetSummary(expData.summary || null);
    } catch (err) {
      showError(extractErrorMessage(err));
    } finally {
      setExpenseSaving(false);
    }
  };

  const handleDeleteExpense = async (expenseId) => {
    if (!window.confirm('Delete this expense entry?')) return;
    try {
      await expensesAPI.deleteExpense(expenseId);
      const expData = await expensesAPI.getTripExpenses(id);
      setExpenses(expData.expenses || []);
      setBudgetSummary(expData.summary || null);
      showSuccess('Expense deleted.');
    } catch (err) {
      showError(extractErrorMessage(err));
    }
  };

  // AI Budget Advisor
  const fetchAiBudgetAdvice = async () => {
    try {
      setLoadingAiAdvice(true);
      const advice = await aiAPI.getBudgetAdvice(id);
      setAiBudgetAdvice(advice);
    } catch (err) {
      showError(extractErrorMessage(err));
    } finally {
      setLoadingAiAdvice(false);
    }
  };

  // Helpers
  const formatCurrency = (amount) =>
    new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      maximumFractionDigits: 0,
    }).format(amount || 0);

  const formatDate = (dateStr) => {
    if (!dateStr) return '';
    try {
      const [y, m, d] = dateStr.split('-');
      if (!y || !m || !d) return dateStr;
      const date = new Date(y, m - 1, d);
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

  // Group activities by date
  const groupedActivities = useMemo(() => {
    const groups = {};
    activities.forEach((act) => {
      const d = act.date || 'Unscheduled';
      if (!groups[d]) groups[d] = [];
      groups[d].push(act);
    });
    return groups;
  }, [activities]);

  if (loading) {
    return (
      <div className="main-content">
        <div className="loading-container">
          <div className="spinner spinner-lg" />
          <p>Loading journey details...</p>
        </div>
      </div>
    );
  }

  if (error || !trip) {
    return (
      <div className="main-content">
        <div className="card" style={{ textAlign: 'center', padding: '3rem 1.5rem' }}>
          <AlertTriangle size={32} style={{ color: 'var(--accent)', margin: '0 auto 1rem' }} />
          <h2>Journey not found</h2>
          <p style={{ color: 'var(--text-secondary)', margin: '0.5rem 0 1.5rem' }}>
            {error || 'The requested trip could not be loaded.'}
          </p>
          <Link to="/trips" className="btn btn-primary">
            Back to itineraries
          </Link>
        </div>
      </div>
    );
  }

  const displayTitle = trip.title || trip.destination;
  const subtitle = trip.title && trip.title !== trip.destination ? trip.destination : null;

  return (
    <div className="main-content">
      {/* Back Link */}
      <Link
        to="/trips"
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
        <span>All Itineraries</span>
      </Link>

      {/* Trip Hero Header */}
      <div className="trip-detail-header card">
        <div className="trip-detail-hero-content">
          <div className="editorial-mark">
            <i></i> 04 / JOURNEY DETAILS
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
            <h1 className="trip-detail-title">{displayTitle}</h1>
            <StatusBadge status={trip.status} />
          </div>

          {subtitle && (
            <div className="trip-detail-subtitle">
              <MapPin size={15} />
              <span>{subtitle}</span>
            </div>
          )}

          <div className="trip-detail-meta-row">
            <div className="meta-pill">
              <Calendar size={14} />
              <span>
                {formatDate(trip.start_date)} — {formatDate(trip.end_date)}
              </span>
            </div>

            <div className="meta-pill">
              <DollarSign size={14} />
              <span>Budget: {formatCurrency(trip.budget)}</span>
            </div>

            {trip.travelers && (
              <div className="meta-pill">
                <Users size={14} />
                <span>{trip.travelers} {trip.travelers === 1 ? 'Traveler' : 'Travelers'}</span>
              </div>
            )}
          </div>
        </div>

        <div className="trip-detail-actions">
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={() => navigate(`/trips/${id}/edit`, { state: { trip } })}
          >
            <Edit2 size={13} />
            <span>Edit Trip</span>
          </button>
          <button
            type="button"
            className="btn btn-danger btn-sm"
            onClick={() => setTripToDelete(trip)}
          >
            <Trash2 size={13} />
            <span>Delete</span>
          </button>
        </div>
      </div>

      {/* Tabs Bar */}
      <div className="trip-tabs">
        <button
          type="button"
          className={`trip-tab-btn ${activeTab === 'itinerary' ? 'active' : ''}`}
          onClick={() => setActiveTab('itinerary')}
        >
          <Compass size={15} />
          <span>Day-by-Day Itinerary ({activities.length})</span>
        </button>

        <button
          type="button"
          className={`trip-tab-btn ${activeTab === 'budget' ? 'active' : ''}`}
          onClick={() => setActiveTab('budget')}
        >
          <CreditCard size={15} />
          <span>Budget & Expenses ({expenses.length})</span>
        </button>

        <button
          type="button"
          className={`trip-tab-btn ${activeTab === 'overview' ? 'active' : ''}`}
          onClick={() => setActiveTab('overview')}
        >
          <FileText size={15} />
          <span>Overview & Notes</span>
        </button>
      </div>

      {/* ================================================== */}
      {/* TAB 1: DAY-BY-DAY ITINERARY                        */}
      {/* ================================================== */}
      {activeTab === 'itinerary' && (
        <div className="tab-pane">
          <div className="tab-pane-header">
            <div>
              <h2>Itinerary Schedule</h2>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
                Organize activities, sightseeing, dining, and reservations chronologically.
              </p>
            </div>
            <div style={{ display: 'flex', gap: '0.65rem' }}>
              <Link
                to="/ai-planner"
                state={{ prefill: { destination: trip.destination, budget: trip.budget, travelers: trip.travelers } }}
                className="btn btn-secondary btn-sm"
              >
                <Sparkles size={13} style={{ color: 'var(--primary-green)' }} />
                <span>AI Generator</span>
              </Link>
              <button
                type="button"
                className="btn btn-primary btn-sm"
                onClick={() => handleOpenAddActivity()}
              >
                <Plus size={14} />
                <span>Add Activity</span>
              </button>
            </div>
          </div>

          {activities.length === 0 ? (
            <div className="empty-state">
              <div className="empty-icon-wrapper">
                <Compass size={24} />
              </div>
              <h3 className="empty-title">No activities planned yet.</h3>
              <p className="empty-desc">
                Add your visits, bookings, meals, and adventures for each day of this journey.
              </p>
              <button
                type="button"
                className="btn btn-primary"
                onClick={() => handleOpenAddActivity()}
              >
                <Plus size={15} />
                <span>Add First Activity</span>
              </button>
            </div>
          ) : (
            <div className="itinerary-timeline">
              {Object.keys(groupedActivities)
                .sort()
                .map((dateKey, dayIdx) => {
                  const dayActivities = groupedActivities[dateKey];
                  return (
                    <div key={dateKey} className="timeline-day-block">
                      <div className="timeline-day-header">
                        <div className="timeline-day-badge">
                          DAY {dayActivities[0]?.day_number || dayIdx + 1}
                        </div>
                        <div className="timeline-day-date">{formatDate(dateKey)}</div>
                        <button
                          type="button"
                          className="btn btn-secondary btn-sm"
                          style={{ marginLeft: 'auto', padding: '0.2rem 0.5rem', fontSize: '0.75rem' }}
                          onClick={() => handleOpenAddActivity(dayActivities[0]?.day_number || dayIdx + 1, dateKey)}
                        >
                          <Plus size={12} />
                          <span>Add</span>
                        </button>
                      </div>

                      <div className="timeline-activities-list">
                        {dayActivities.map((act) => (
                          <div key={act._id} className="timeline-activity-card">
                            <div className="activity-time-col">
                              <Clock size={13} style={{ color: 'var(--primary-green)' }} />
                              <span>{act.time || 'All Day'}</span>
                            </div>

                            <div className="activity-content-col">
                              <div className="activity-header-row">
                                <h4 className="activity-title">{act.title}</h4>
                                {act.cost > 0 && (
                                  <span className="activity-cost-tag">
                                    {formatCurrency(act.cost)}
                                  </span>
                                )}
                              </div>

                              {act.location && (
                                <div className="activity-location">
                                  <MapPin size={12} />
                                  <span>{act.location}</span>
                                </div>
                              )}

                              {act.description && (
                                <p className="activity-desc">{act.description}</p>
                              )}

                              {act.notes && (
                                <div className="activity-notes-box">
                                  <Lightbulb size={12} style={{ color: 'var(--primary-green)', flexShrink: 0 }} />
                                  <span>{act.notes}</span>
                                </div>
                              )}
                            </div>

                            <div className="activity-actions-col">
                              <button
                                type="button"
                                className="icon-btn"
                                onClick={() => handleOpenEditActivity(act)}
                                title="Edit activity"
                              >
                                <Edit2 size={13} />
                              </button>
                              <button
                                type="button"
                                className="icon-btn icon-btn-danger"
                                onClick={() => handleDeleteActivity(act._id)}
                                title="Delete activity"
                              >
                                <Trash2 size={13} />
                              </button>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  );
                })}
            </div>
          )}
        </div>
      )}

      {/* ================================================== */}
      {/* TAB 2: BUDGET & EXPENSES                           */}
      {/* ================================================== */}
      {activeTab === 'budget' && (
        <div className="tab-pane">
          {/* Budget Overview Cards */}
          <div className="stats-grid" style={{ marginBottom: '2rem' }}>
            <div className="stat-card">
              <div className="stat-card-top">
                <span className="stat-number-label">01</span>
                <span className="stat-label">TOTAL BUDGET</span>
              </div>
              <div className="stat-value" style={{ fontSize: '2rem' }}>
                {formatCurrency(budgetSummary?.budget || trip.budget)}
              </div>
            </div>

            <div className="stat-card">
              <div className="stat-card-top">
                <span className="stat-number-label">02</span>
                <span className="stat-label">TOTAL SPENT</span>
              </div>
              <div className="stat-value" style={{ fontSize: '2rem', color: (budgetSummary?.percentage_spent > 100) ? 'var(--danger-text)' : 'var(--text-primary)' }}>
                {formatCurrency(budgetSummary?.total_spent || 0)}
              </div>
            </div>

            <div className="stat-card">
              <div className="stat-card-top">
                <span className="stat-number-label">03</span>
                <span className="stat-label">REMAINING</span>
              </div>
              <div className="stat-value" style={{ fontSize: '2rem', color: (budgetSummary?.remaining_budget < 0) ? 'var(--danger-text)' : 'var(--primary-green)' }}>
                {formatCurrency(budgetSummary?.remaining_budget || trip.budget)}
              </div>
            </div>

            <div className="stat-card">
              <div className="stat-card-top">
                <span className="stat-number-label">04</span>
                <span className="stat-label">USED</span>
              </div>
              <div className="stat-value" style={{ fontSize: '2rem' }}>
                {budgetSummary?.percentage_spent || 0}%
              </div>
            </div>
          </div>

          {/* Budget Bar Visualizer */}
          <div className="card" style={{ marginBottom: '2rem', padding: '1.5rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.65rem' }}>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', textTransform: 'uppercase', color: 'var(--text-secondary)' }}>
                Budget Allocation Progress
              </span>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', fontWeight: 600 }}>
                {budgetSummary?.percentage_spent || 0}% Spent
              </span>
            </div>
            <div className="progress-bar-track">
              <div
                className={`progress-bar-fill ${budgetSummary?.percentage_spent > 100 ? 'progress-danger' : ''}`}
                style={{ width: `${Math.min(budgetSummary?.percentage_spent || 0, 100)}%` }}
              />
            </div>

            {/* Category Breakdown Badges */}
            {budgetSummary?.by_category && (
              <div className="category-breakdown-row">
                {Object.entries(budgetSummary.by_category).map(([cat, amount]) => (
                  <div key={cat} className="category-pill">
                    <span className="cat-name">{cat}</span>
                    <span className="cat-amount">{formatCurrency(amount)}</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* AI Budget Assistant Section */}
          <div className="card ai-budget-box" style={{ marginBottom: '2.5rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem', flexWrap: 'wrap', gap: '0.75rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Sparkles size={18} style={{ color: 'var(--primary-green)' }} />
                <h3 style={{ margin: 0, fontSize: '1.25rem' }}>AI Budget Assistant</h3>
              </div>
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={fetchAiBudgetAdvice}
                disabled={loadingAiAdvice}
              >
                {loadingAiAdvice ? 'Analyzing...' : 'Run Financial Check'}
              </button>
            </div>

            {aiBudgetAdvice ? (
              <div className="ai-advice-content">
                <div className={`advice-status-badge advice-${aiBudgetAdvice.status}`}>
                  STATUS: {aiBudgetAdvice.status.toUpperCase().replace('_', ' ')}
                </div>
                <p className="advice-summary">{aiBudgetAdvice.summary}</p>
                <p className="advice-analysis">{aiBudgetAdvice.analysis}</p>

                {aiBudgetAdvice.saving_tips?.length > 0 && (
                  <div style={{ marginTop: '1rem' }}>
                    <div className="editorial-mark"><i></i> ACTIONABLE SAVINGS</div>
                    <ul className="advice-tips-list">
                      {aiBudgetAdvice.saving_tips.map((tip, idx) => (
                        <li key={idx}>
                          <Check size={13} style={{ color: 'var(--primary-green)', flexShrink: 0, marginTop: '3px' }} />
                          <span>{tip}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            ) : (
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', margin: 0 }}>
                Click "Run Financial Check" to analyze your current burn rate, category breakdowns, and receive smart cost-saving tips tailored to {trip.destination}.
              </p>
            )}
          </div>

          {/* Expenses Table Header & Add */}
          <div className="tab-pane-header">
            <div>
              <h2>Logged Expenses</h2>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
                All documented transactions for accommodation, dining, transport, and excursions.
              </p>
            </div>
            <button
              type="button"
              className="btn btn-primary btn-sm"
              onClick={handleOpenAddExpense}
            >
              <Plus size={14} />
              <span>Log Expense</span>
            </button>
          </div>

          {expenses.length === 0 ? (
            <div className="empty-state">
              <div className="empty-icon-wrapper">
                <DollarSign size={24} />
              </div>
              <h3 className="empty-title">No expenses logged yet.</h3>
              <p className="empty-desc">
                Record your accommodation, dining, transport, and souvenir costs to track your budget accurately.
              </p>
              <button
                type="button"
                className="btn btn-primary"
                onClick={handleOpenAddExpense}
              >
                <Plus size={15} />
                <span>Log First Expense</span>
              </button>
            </div>
          ) : (
            <div className="table-container">
              <table className="trip-table">
                <thead>
                  <tr>
                    <th>DATE</th>
                    <th>CATEGORY</th>
                    <th>DESCRIPTION</th>
                    <th>AMOUNT</th>
                    <th style={{ textAlign: 'right' }}>ACTIONS</th>
                  </tr>
                </thead>
                <tbody>
                  {expenses.map((exp) => (
                    <tr key={exp._id}>
                      <td>
                        <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.775rem' }}>
                          {formatDate(exp.date)}
                        </span>
                      </td>
                      <td>
                        <span className="category-tag-badge">
                          <Tag size={11} />
                          <span>{exp.category}</span>
                        </span>
                      </td>
                      <td>
                        <span style={{ fontWeight: 500 }}>{exp.description}</span>
                      </td>
                      <td>
                        <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, color: 'var(--text-primary)' }}>
                          {formatCurrency(exp.amount)}
                        </span>
                      </td>
                      <td>
                        <div className="table-actions" style={{ justifyContent: 'flex-end' }}>
                          <button
                            type="button"
                            className="btn btn-secondary btn-sm"
                            onClick={() => handleOpenEditExpense(exp)}
                          >
                            Edit
                          </button>
                          <button
                            type="button"
                            className="btn btn-danger btn-sm"
                            onClick={() => handleDeleteExpense(exp._id)}
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
          )}
        </div>
      )}

      {/* ================================================== */}
      {/* TAB 3: OVERVIEW & NOTES                            */}
      {/* ================================================== */}
      {activeTab === 'overview' && (
        <div className="tab-pane">
          <div className="form-grid-two">
            <div className="card">
              <div className="editorial-mark"><i></i> SUMMARY</div>
              <h3 style={{ marginBottom: '0.75rem' }}>Trip Overview</h3>
              <p style={{ color: 'var(--text-secondary)', lineHeight: 1.7, fontSize: '0.95rem' }}>
                {trip.description || 'No description provided yet for this journey.'}
              </p>
            </div>

            <div className="card">
              <div className="editorial-mark"><i></i> PREPARATION</div>
              <h3 style={{ marginBottom: '0.75rem' }}>Travel & Packing Notes</h3>
              <p style={{ color: 'var(--text-secondary)', lineHeight: 1.7, fontSize: '0.95rem', whiteSpace: 'pre-line' }}>
                {trip.notes || 'No custom notes logged yet. Use the edit button to document flight references, packing lists, and visas.'}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* ================================================== */}
      {/* ACTIVITY MODAL (ADD / EDIT)                        */}
      {/* ================================================== */}
      {isActivityModalOpen && (
        <div className="modal-backdrop">
          <div className="modal-content">
            <h3 style={{ marginBottom: '0.5rem', fontSize: '1.5rem' }}>
              {editingActivity ? 'Modify Activity' : 'Add Itinerary Activity'}
            </h3>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginBottom: '1.5rem' }}>
              Schedule a visit, dining spot, or travel event.
            </p>

            <form onSubmit={handleSaveActivity}>
              <div className="form-group">
                <label className="form-label" htmlFor="act-title">
                  ACTIVITY TITLE <span style={{ color: 'var(--accent)' }}>*</span>
                </label>
                <input
                  id="act-title"
                  type="text"
                  className="form-input"
                  placeholder="e.g. Fushimi Inari Torii Gate Hike"
                  value={activityForm.title}
                  onChange={(e) => setActivityForm({ ...activityForm, title: e.target.value })}
                  required
                />
              </div>

              <div className="form-grid-two">
                <div className="form-group">
                  <label className="form-label" htmlFor="act-date">
                    DATE <span style={{ color: 'var(--accent)' }}>*</span>
                  </label>
                  <input
                    id="act-date"
                    type="date"
                    className="form-input"
                    value={activityForm.date}
                    onChange={(e) => setActivityForm({ ...activityForm, date: e.target.value })}
                    required
                  />
                </div>

                <div className="form-group">
                  <label className="form-label" htmlFor="act-time">
                    TIME / SLOT
                  </label>
                  <input
                    id="act-time"
                    type="text"
                    className="form-input"
                    placeholder="e.g. 09:30 AM"
                    value={activityForm.time}
                    onChange={(e) => setActivityForm({ ...activityForm, time: e.target.value })}
                  />
                </div>
              </div>

              <div className="form-grid-two">
                <div className="form-group">
                  <label className="form-label" htmlFor="act-location">
                    LOCATION / VENUE
                  </label>
                  <input
                    id="act-location"
                    type="text"
                    className="form-input"
                    placeholder="e.g. Fushimi Ward, Kyoto"
                    value={activityForm.location}
                    onChange={(e) => setActivityForm({ ...activityForm, location: e.target.value })}
                  />
                </div>

                <div className="form-group">
                  <label className="form-label" htmlFor="act-cost">
                    ESTIMATED COST (USD)
                  </label>
                  <input
                    id="act-cost"
                    type="number"
                    step="any"
                    min="0"
                    className="form-input"
                    placeholder="0"
                    value={activityForm.cost}
                    onChange={(e) => setActivityForm({ ...activityForm, cost: e.target.value })}
                  />
                </div>
              </div>

              <div className="form-group">
                <label className="form-label" htmlFor="act-desc">
                  DESCRIPTION
                </label>
                <textarea
                  id="act-desc"
                  className="form-input"
                  rows={2}
                  placeholder="Highlights, transport directions, ticket details..."
                  value={activityForm.description}
                  onChange={(e) => setActivityForm({ ...activityForm, description: e.target.value })}
                />
              </div>

              <div className="form-group">
                <label className="form-label" htmlFor="act-notes">
                  TIPS & BOOKING REFS
                </label>
                <input
                  id="act-notes"
                  type="text"
                  className="form-input"
                  placeholder="e.g. Booking #JP4920, arrive 15m early"
                  value={activityForm.notes}
                  onChange={(e) => setActivityForm({ ...activityForm, notes: e.target.value })}
                />
              </div>

              <div className="form-actions" style={{ marginTop: '1.25rem', paddingTop: '1rem' }}>
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setIsActivityModalOpen(false)}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={activitySaving}
                >
                  {activitySaving ? 'Saving...' : editingActivity ? 'Save Changes' : 'Add Activity'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ================================================== */}
      {/* EXPENSE MODAL (ADD / EDIT)                         */}
      {/* ================================================== */}
      {isExpenseModalOpen && (
        <div className="modal-backdrop">
          <div className="modal-content">
            <h3 style={{ marginBottom: '0.5rem', fontSize: '1.5rem' }}>
              {editingExpense ? 'Modify Expense' : 'Log New Expense'}
            </h3>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginBottom: '1.5rem' }}>
              Keep your financial records aligned with your journey budget.
            </p>

            <form onSubmit={handleSaveExpense}>
              <div className="form-group">
                <label className="form-label" htmlFor="exp-category">
                  CATEGORY <span style={{ color: 'var(--accent)' }}>*</span>
                </label>
                <select
                  id="exp-category"
                  className="form-select"
                  value={expenseForm.category}
                  onChange={(e) => setExpenseForm({ ...expenseForm, category: e.target.value })}
                >
                  <option value="Accommodation">Accommodation</option>
                  <option value="Food">Food & Dining</option>
                  <option value="Transport">Transport & Transit</option>
                  <option value="Activities">Activities & Sightseeing</option>
                  <option value="Shopping">Shopping & Souvenirs</option>
                  <option value="Other">Other / Miscellaneous</option>
                </select>
              </div>

              <div className="form-grid-two">
                <div className="form-group">
                  <label className="form-label" htmlFor="exp-amount">
                    AMOUNT (USD) <span style={{ color: 'var(--accent)' }}>*</span>
                  </label>
                  <input
                    id="exp-amount"
                    type="number"
                    step="any"
                    min="0.01"
                    className="form-input"
                    placeholder="e.g. 85.50"
                    value={expenseForm.amount}
                    onChange={(e) => setExpenseForm({ ...expenseForm, amount: e.target.value })}
                    required
                  />
                </div>

                <div className="form-group">
                  <label className="form-label" htmlFor="exp-date">
                    DATE <span style={{ color: 'var(--accent)' }}>*</span>
                  </label>
                  <input
                    id="exp-date"
                    type="date"
                    className="form-input"
                    value={expenseForm.date}
                    onChange={(e) => setExpenseForm({ ...expenseForm, date: e.target.value })}
                    required
                  />
                </div>
              </div>

              <div className="form-group">
                <label className="form-label" htmlFor="exp-desc">
                  DESCRIPTION <span style={{ color: 'var(--accent)' }}>*</span>
                </label>
                <input
                  id="exp-desc"
                  type="text"
                  className="form-input"
                  placeholder="e.g. Traditional tea house tasting"
                  value={expenseForm.description}
                  onChange={(e) => setExpenseForm({ ...expenseForm, description: e.target.value })}
                  required
                />
              </div>

              <div className="form-actions" style={{ marginTop: '1.25rem', paddingTop: '1rem' }}>
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setIsExpenseModalOpen(false)}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={expenseSaving}
                >
                  {expenseSaving ? 'Saving...' : editingExpense ? 'Save Changes' : 'Log Expense'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal for Trip */}
      <DeleteModal
        isOpen={Boolean(tripToDelete)}
        trip={tripToDelete}
        onConfirm={handleConfirmDeleteTrip}
        onCancel={() => setTripToDelete(null)}
        isDeleting={isDeletingTrip}
      />
    </div>
  );
};
