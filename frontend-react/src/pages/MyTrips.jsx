import { useState, useEffect, useMemo } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { 
  Search, 
  LayoutGrid, 
  List, 
  Compass,
  ArrowUpRight
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { tripsAPI, extractErrorMessage } from '../services/api';
import { TripCard } from '../components/TripCard';
import { TripTable } from '../components/TripTable';
import { DeleteModal } from '../components/DeleteModal';
import { Alert } from '../components/Alert';

export const MyTrips = () => {
  const { user } = useAuth();
  const navigate = useNavigate();

  const [trips, setTrips] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);

  // Filters & display state
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [sortBy, setSortBy] = useState('date-desc');
  const [viewMode, setViewMode] = useState('grid'); // 'grid' | 'table'

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

  // Filter and sort computation
  const filteredTrips = useMemo(() => {
    return trips
      .filter((trip) => {
        const matchesSearch = trip.destination
          ?.toLowerCase()
          .includes(searchQuery.toLowerCase().trim());
        const matchesStatus =
          statusFilter === 'all' ? true : trip.status === statusFilter;
        return matchesSearch && matchesStatus;
      })
      .sort((a, b) => {
        if (sortBy === 'date-desc') {
          return new Date(b.start_date || 0) - new Date(a.start_date || 0);
        }
        if (sortBy === 'date-asc') {
          return new Date(a.start_date || 0) - new Date(b.start_date || 0);
        }
        if (sortBy === 'budget-desc') {
          return (parseFloat(b.budget) || 0) - (parseFloat(a.budget) || 0);
        }
        if (sortBy === 'budget-asc') {
          return (parseFloat(a.budget) || 0) - (parseFloat(b.budget) || 0);
        }
        return 0;
      });
  }, [trips, searchQuery, statusFilter, sortBy]);

  return (
    <div className="main-content">
      {/* Top Botanical Header */}
      <div className="dashboard-header">
        <div className="dashboard-title-group">
          <div className="editorial-mark">
            <i></i> 02 / ITINERARIES
          </div>
          <h1>My trips</h1>
          <p className="welcome-subtitle">
            Every destination, date and detail in one place.
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

      {/* Toolbar: Search, Filters, Sorting, View mode */}
      <div className="trips-toolbar">
        <div className="search-box">
          <Search className="search-icon" size={16} />
          <input
            type="text"
            className="form-input"
            placeholder="Search destination..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>

        <div className="filter-group">
          <select
            className="form-select"
            style={{ width: 'auto', minWidth: '140px' }}
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            aria-label="Filter by status"
          >
            <option value="all">All Statuses ({trips.length})</option>
            <option value="planned">Planned</option>
            <option value="ongoing">Ongoing</option>
            <option value="completed">Completed</option>
            <option value="cancelled">Cancelled</option>
          </select>

          <select
            className="form-select"
            style={{ width: 'auto', minWidth: '150px' }}
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
            aria-label="Sort trips"
          >
            <option value="date-desc">Newest First</option>
            <option value="date-asc">Oldest First</option>
            <option value="budget-desc">Budget: High to Low</option>
            <option value="budget-asc">Budget: Low to High</option>
          </select>

          <div className="view-toggle">
            <button
              type="button"
              className={`view-toggle-btn ${viewMode === 'grid' ? 'active' : ''}`}
              onClick={() => setViewMode('grid')}
              title="Grid view"
              aria-label="Grid view"
            >
              <LayoutGrid size={15} />
            </button>
            <button
              type="button"
              className={`view-toggle-btn ${viewMode === 'table' ? 'active' : ''}`}
              onClick={() => setViewMode('table')}
              title="Table view"
              aria-label="Table view"
            >
              <List size={15} />
            </button>
          </div>
        </div>
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
            Your next adventure starts here.
          </p>
          <Link to="/trips/new" className="btn btn-primary">
            <span>Create your first trip</span>
            <ArrowUpRight size={15} />
          </Link>
        </div>
      ) : filteredTrips.length === 0 ? (
        <div className="empty-state">
          <div className="empty-icon-wrapper">
            <Search size={24} />
          </div>
          <h3 className="empty-title">No matching trips found</h3>
          <p className="empty-desc">
            No itineraries matched "{searchQuery}".
          </p>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => {
              setSearchQuery('');
              setStatusFilter('all');
            }}
          >
            Clear Filters
          </button>
        </div>
      ) : viewMode === 'grid' ? (
        <div className="trips-grid">
          {filteredTrips.map((trip) => (
            <TripCard
              key={trip._id}
              trip={trip}
              onEdit={handleEdit}
              onDelete={handleDeletePrompt}
            />
          ))}
        </div>
      ) : (
        <TripTable
          trips={filteredTrips}
          onEdit={handleEdit}
          onDelete={handleDeletePrompt}
        />
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
