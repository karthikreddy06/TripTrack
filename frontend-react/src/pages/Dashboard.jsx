import { useState, useEffect, useCallback } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  ArrowUpRight,
  Compass,
  Plus,
  Sparkles,
  User
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import { tripsAPI, expensesAPI, extractErrorMessage } from '../services/api';
import { TripCard } from '../components/TripCard';
import { DeleteModal } from '../components/DeleteModal';
import { Alert } from '../components/Alert';

export const Dashboard = () => {
  const { user } = useAuth();
  const { showSuccess, showError } = useToast();
  const navigate = useNavigate();

  const [trips, setTrips] = useState([]);
  const [expenseSummary, setExpenseSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Delete modal state
  const [tripToDelete, setTripToDelete] = useState(null);
  const [isDeleting, setIsDeleting] = useState(false);

  const fetchDashboardData = useCallback(async () => {
    if (!user?.user_id) return;
    try {
      setLoading(true);
      setError(null);

      const [tripsData, expSummary] = await Promise.all([
        tripsAPI.getTrips(user.user_id),
        expensesAPI.getUserExpenseSummary(user.user_id).catch(() => ({ total_spent: 0, by_category: {} })),
      ]);

      setTrips(Array.isArray(tripsData) ? tripsData : []);
      setExpenseSummary(expSummary);
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, [user?.user_id]);

  useEffect(() => {
    fetchDashboardData();
  }, [fetchDashboardData]);

  const handleEdit = (trip) => {
    navigate(`/trips/${trip._id}/edit`, { state: { trip } });
  };

  const handleDeletePrompt = (trip) => {
    setTripToDelete(trip);
  };

  const handleConfirmDelete = async (trip) => {
    try {
      setIsDeleting(true);
      await tripsAPI.deleteTrip(trip._id);
      setTrips((prev) => prev.filter((t) => t._id !== trip._id));
      setTripToDelete(null);
      showSuccess(`Trip to ${trip.destination} was deleted successfully.`);
      fetchDashboardData();
    } catch (err) {
      showError(extractErrorMessage(err));
    } finally {
      setIsDeleting(false);
    }
  };

  // Time of day greeting
  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return 'Good morning';
    if (hour < 18) return 'Good afternoon';
    return 'Good evening';
  };

  // Metrics computation from real MongoDB data
  const totalTrips = trips.length;
  const plannedTrips = trips.filter((t) => t.status === 'planned').length;
  const ongoingTrips = trips.filter((t) => t.status === 'ongoing').length;
  const completedTrips = trips.filter((t) => t.status === 'completed').length;
  const totalBudget = trips.reduce((sum, t) => sum + (parseFloat(t.budget) || 0), 0);
  const totalExpenses = expenseSummary?.total_spent || 0;

  const formatCurrency = (val) =>
    new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      maximumFractionDigits: 0,
    }).format(val);

  const firstName = user?.name ? user.name.split(' ')[0] : 'Traveler';

  return (
    <div className="main-content">
      {/* Top Editorial Header */}
      <div className="dashboard-header">
        <div className="dashboard-title-group">
          <div className="editorial-mark">
            <i></i> 01 / OVERVIEW
          </div>
          <div className="user-greeting">
            {getGreeting()}, {firstName}.
          </div>
          <h1>
            Your journeys, <br />
            <em>beautifully planned.</em>
          </h1>
          <p className="welcome-subtitle">
            Curate day-by-day itineraries, track expenses against target budgets, and explore intelligent AI travel suggestions.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '0.65rem', flexWrap: 'wrap' }}>
          <Link to="/ai-planner" className="btn btn-secondary">
            <Sparkles size={14} style={{ color: 'var(--primary-green)' }} />
            <span>AI Planner</span>
          </Link>
          <Link to="/trips/new" className="btn btn-primary">
            <span>Create Trip</span>
            <ArrowUpRight size={15} />
          </Link>
        </div>
      </div>

      {error && <Alert type="error" message={error} onClose={() => setError(null)} />}

      {/* 5 Real MongoDB Metric Cards */}
      <div className="stats-grid">
        {/* 01 TOTAL TRIPS */}
        <div className="stat-card">
          <div className="stat-card-top">
            <span className="stat-number-label">01</span>
            <span className="stat-label">TOTAL TRIPS</span>
          </div>
          <div className="stat-value">
            {String(totalTrips).padStart(2, '0')}
          </div>
        </div>

        {/* 02 PLANNED */}
        <div className="stat-card">
          <div className="stat-card-top">
            <span className="stat-number-label">02</span>
            <span className="stat-label">PLANNED</span>
          </div>
          <div className="stat-value">
            {String(plannedTrips).padStart(2, '0')}
          </div>
        </div>

        {/* 03 ONGOING */}
        <div className="stat-card">
          <div className="stat-card-top">
            <span className="stat-number-label">03</span>
            <span className="stat-label">ONGOING</span>
          </div>
          <div className="stat-value" style={{ color: 'var(--primary-green)' }}>
            {String(ongoingTrips).padStart(2, '0')}
          </div>
        </div>

        {/* 04 TOTAL BUDGET */}
        <div className="stat-card">
          <div className="stat-card-top">
            <span className="stat-number-label">04</span>
            <span className="stat-label">PLANNED BUDGET</span>
          </div>
          <div className="stat-value" style={{ fontSize: '1.95rem' }}>
            {formatCurrency(totalBudget)}
          </div>
        </div>

        {/* 05 TOTAL EXPENSES */}
        <div className="stat-card">
          <div className="stat-card-top">
            <span className="stat-number-label">05</span>
            <span className="stat-label">TOTAL SPENT</span>
          </div>
          <div className="stat-value" style={{ fontSize: '1.95rem', color: totalExpenses > totalBudget && totalBudget > 0 ? 'var(--danger-text)' : 'var(--text-primary)' }}>
            {formatCurrency(totalExpenses)}
          </div>
        </div>
      </div>

      {/* Quick Action Navigation Cards */}
      <div className="quick-actions-grid" style={{ marginBottom: '3.5rem' }}>
        <Link to="/trips/new" className="quick-action-card">
          <div className="qa-icon-wrapper">
            <Plus size={18} />
          </div>
          <div className="qa-text">
            <h4>Create New Trip</h4>
            <p>Define destination, duration, budget cap, and companions.</p>
          </div>
          <ArrowUpRight size={15} className="qa-arrow" />
        </Link>

        <Link to="/ai-planner" className="quick-action-card">
          <div className="qa-icon-wrapper" style={{ background: 'var(--surface-cream)' }}>
            <Sparkles size={18} style={{ color: 'var(--primary-green)' }} />
          </div>
          <div className="qa-text">
            <h4>AI Trip Planner</h4>
            <p>Generate structured day-by-day itineraries and packing checklists.</p>
          </div>
          <ArrowUpRight size={15} className="qa-arrow" />
        </Link>

        <Link to="/trips" className="quick-action-card">
          <div className="qa-icon-wrapper">
            <Compass size={18} />
          </div>
          <div className="qa-text">
            <h4>View All Itineraries</h4>
            <p>Search, filter, and review active journeys and archives.</p>
          </div>
          <ArrowUpRight size={15} className="qa-arrow" />
        </Link>

        <Link to="/profile" className="quick-action-card">
          <div className="qa-icon-wrapper">
            <User size={18} />
          </div>
          <div className="qa-text">
            <h4>Profile & Preferences</h4>
            <p>Update travel styles, biography, and security settings.</p>
          </div>
          <ArrowUpRight size={15} className="qa-arrow" />
        </Link>
      </div>

      {/* Recent Trips Section */}
      <div className="section-header">
        <div>
          <h2 className="section-title">Recent itineraries</h2>
        </div>
        {trips.length > 0 && (
          <Link to="/trips" className="btn btn-secondary btn-sm">
            <span>View all ({trips.length})</span>
            <ArrowUpRight size={13} />
          </Link>
        )}
      </div>

      {loading ? (
        <div className="loading-container">
          <div className="spinner spinner-lg" />
          <p>Loading your itineraries...</p>
        </div>
      ) : trips.length === 0 ? (
        <div className="empty-state">
          <div className="empty-icon-wrapper">
            <Compass size={24} />
          </div>
          <h3 className="empty-title">No journeys yet.</h3>
          <p className="empty-desc">
            Your next adventure starts here. Add your upcoming destination, dates, and budget or generate an itinerary with AI.
          </p>
          <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'center' }}>
            <Link to="/trips/new" className="btn btn-primary">
              <span>Create your first trip</span>
              <ArrowUpRight size={15} />
            </Link>
            <Link to="/ai-planner" className="btn btn-secondary">
              <Sparkles size={14} style={{ color: 'var(--primary-green)' }} />
              <span>Generate with AI</span>
            </Link>
          </div>
        </div>
      ) : (
        <div className="trips-grid">
          {trips.slice(0, 3).map((trip) => (
            <TripCard
              key={trip._id}
              trip={trip}
              onEdit={handleEdit}
              onDelete={handleDeletePrompt}
            />
          ))}
        </div>
      )}

      {/* Delete Confirmation Modal */}
      <DeleteModal
        isOpen={Boolean(tripToDelete)}
        trip={tripToDelete}
        onConfirm={handleConfirmDelete}
        onCancel={() => setTripToDelete(null)}
        isDeleting={isDeleting}
      />
    </div>
  );
};
