import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowUpRight, Compass } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { tripsAPI, extractErrorMessage } from '../services/api';
import { TripCard } from '../components/TripCard';
import { DeleteModal } from '../components/DeleteModal';
import { Alert } from '../components/Alert';

export const Dashboard = () => {
  const { user } = useAuth();
  const navigate = useNavigate();

  const [trips, setTrips] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);

  // Delete modal state
  const [tripToDelete, setTripToDelete] = useState(null);
  const [isDeleting, setIsDeleting] = useState(false);

  const fetchTrips = async () => {
    if (!user?.user_id) return;
    try {
      setLoading(true);
      setError(null);
      const data = await tripsAPI.getTrips(user.user_id);
      setTrips(Array.isArray(data) ? data : []);
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTrips();
  }, [user?.user_id]);

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
      setSuccessMessage(`Trip to ${trip.destination} was deleted successfully.`);
      setTimeout(() => setSuccessMessage(null), 4000);
    } catch (err) {
      setError(extractErrorMessage(err));
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

  // Metrics computation for 5 cards
  const totalTrips = trips.length;
  const plannedTrips = trips.filter((t) => t.status === 'planned').length;
  const ongoingTrips = trips.filter((t) => t.status === 'ongoing').length;
  const completedTrips = trips.filter((t) => t.status === 'completed').length;
  const totalBudget = trips.reduce((sum, t) => sum + (parseFloat(t.budget) || 0), 0);

  const formatCurrency = (val) =>
    new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      maximumFractionDigits: 0,
    }).format(val);

  const firstName = user?.name ? user.name.split(' ')[0] : 'Traveler';

  return (
    <div className="main-content">
      {/* Top Botanical Header */}
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
            Plan, track, and manage every itinerary from one calm, considered space.
          </p>
        </div>
        <div>
          <Link to="/trips/new" className="btn btn-primary">
            <span>Create Trip</span>
            <ArrowUpRight size={15} />
          </Link>
        </div>
      </div>

      {error && <Alert type="error" message={error} onClose={() => setError(null)} />}
      {successMessage && (
        <Alert type="success" message={successMessage} onClose={() => setSuccessMessage(null)} />
      )}

      {/* 5 Minimal Botanical Metric Blocks */}
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

        {/* 04 COMPLETED */}
        <div className="stat-card">
          <div className="stat-card-top">
            <span className="stat-number-label">04</span>
            <span className="stat-label">COMPLETED</span>
          </div>
          <div className="stat-value">
            {String(completedTrips).padStart(2, '0')}
          </div>
        </div>

        {/* 05 TOTAL BUDGET */}
        <div className="stat-card">
          <div className="stat-card-top">
            <span className="stat-number-label">05</span>
            <span className="stat-label">TOTAL BUDGET</span>
          </div>
          <div className="stat-value" style={{ fontSize: '2.1rem' }}>
            {formatCurrency(totalBudget)}
          </div>
        </div>
      </div>

      {/* Recent Trips Section */}
      <div className="section-header">
        <div>
          <h2 className="section-title">Recent itineraries</h2>
        </div>
        {trips.length > 0 && (
          <Link to="/trips" className="btn btn-secondary btn-sm">
            <span>View all trips</span>
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
            Your next adventure starts here. Add your upcoming destination, dates, and budget.
          </p>
          <Link to="/trips/new" className="btn btn-primary">
            <span>Create your first trip</span>
            <ArrowUpRight size={15} />
          </Link>
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
