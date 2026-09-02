import { useState, useEffect, useMemo, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  MapPin,
  Calendar,
  DollarSign,
  Compass,
  ArrowLeft,
  Sparkles,
  Hotel,
  Utensils,
  Landmark,
  Layers,
  Map,
  Grid
} from 'lucide-react';
import { exploreAPI, extractErrorMessage } from '../services/api';
import { PlaceCard } from '../components/PlaceCard';
import { MapView } from '../components/MapView';
import { AddToTripModal } from '../components/AddToTripModal';

export const DestinationDetail = () => {
  const { destination } = useParams();
  const decodedDestination = decodeURIComponent(destination || '');

  const [destSummary, setDestSummary] = useState(null);
  const [activeTab, setActiveTab] = useState('highlights'); // 'highlights' | 'attractions' | 'hotels' | 'restaurants' | 'activities'
  const [showMap, setShowMap] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [modalPlace, setModalPlace] = useState(null);

  const fetchDetails = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await exploreAPI.getDestination(decodedDestination);
      setDestSummary(data);
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, [decodedDestination]);

  useEffect(() => {
    fetchDetails();
  }, [fetchDetails]);

  const activePlaces = useMemo(() => {
    if (!destSummary) return [];
    switch (activeTab) {
      case 'hotels':
        return destSummary.hotels || [];
      case 'restaurants':
        return destSummary.restaurants || [];
      case 'attractions':
        return destSummary.attractions || [];
      case 'activities':
        return destSummary.activities || [];
      case 'highlights':
      default:
        return [
          ...(destSummary.highlights || []),
          ...(destSummary.attractions || []),
          ...(destSummary.hotels || []),
          ...(destSummary.restaurants || []),
        ].filter((p, i, self) => i === self.findIndex((t) => t.place_id === p.place_id));
    }
  }, [destSummary, activeTab]);

  if (loading) {
    return (
      <div className="main-content">
        <div className="loading-container" style={{ padding: '6rem 1rem' }}>
          <div className="spinner spinner-lg" />
          <p style={{ marginTop: '1rem' }}>Loading destination guide for {decodedDestination}...</p>
        </div>
      </div>
    );
  }

  if (error || !destSummary) {
    return (
      <div className="main-content">
        <Link
          to="/explore"
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '0.45rem',
            marginBottom: '1.5rem',
            color: 'var(--text-secondary)',
            fontFamily: 'var(--font-mono)',
            fontSize: '0.8rem',
            textTransform: 'uppercase',
          }}
        >
          <ArrowLeft size={14} />
          <span>Back to Explore</span>
        </Link>
        <div className="card" style={{ textAlign: 'center', padding: '3rem 1.5rem' }}>
          <Compass size={36} style={{ color: 'var(--accent)', margin: '0 auto 1rem' }} />
          <h2>Destination Guide Unavailable</h2>
          <p style={{ color: 'var(--text-secondary)', margin: '0.5rem 0 1.5rem' }}>
            {error || `We couldn't retrieve details for "${decodedDestination}".`}
          </p>
          <Link to="/explore" className="btn btn-primary">
            Explore Other Destinations
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="main-content">
      {/* Back to Explore */}
      <Link
        to="/explore"
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '0.45rem',
          marginBottom: '1.5rem',
          color: 'var(--text-secondary)',
          fontFamily: 'var(--font-mono)',
          fontSize: '0.8rem',
          textTransform: 'uppercase',
          letterSpacing: '0.04em',
        }}
      >
        <ArrowLeft size={14} />
        <span>All Destinations</span>
      </Link>

      {/* Destination Hero Header */}
      <div className="destination-hero-header card">
        <div className="dest-hero-grid">
          {destSummary.image_url && (
            <img
              src={destSummary.image_url}
              alt={destSummary.destination}
              className="dest-hero-image"
              loading="lazy"
            />
          )}

          <div className="dest-hero-content">
            <div className="editorial-mark">
              <i></i> 02 / DESTINATION GUIDE
            </div>
            <h1 className="dest-hero-title">{destSummary.destination}</h1>

            {destSummary.country && (
              <p className="dest-hero-location">
                <MapPin size={15} />
                <span>{destSummary.country}</span>
              </p>
            )}

            <p className="dest-hero-overview">
              {destSummary.overview || destSummary.description}
            </p>

            <div className="dest-meta-row" style={{ marginTop: '1.25rem' }}>
              {destSummary.best_time_to_visit && (
                <div className="meta-pill">
                  <Calendar size={13} />
                  <span>Best Season: {destSummary.best_time_to_visit}</span>
                </div>
              )}
              {destSummary.currency && (
                <div className="meta-pill">
                  <DollarSign size={13} />
                  <span>Currency: {destSummary.currency}</span>
                </div>
              )}
            </div>

            <div className="dest-hero-actions" style={{ marginTop: '1.5rem', display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
              <Link
                to="/ai-planner"
                state={{ prefill: { destination: destSummary.destination } }}
                className="btn btn-primary btn-sm"
              >
                <Sparkles size={13} />
                <span>Plan Trip to {destSummary.destination}</span>
              </Link>
              <Link
                to={`/trips/new`}
                state={{ prefill: { destination: destSummary.destination } }}
                className="btn btn-secondary btn-sm"
              >
                <span>Create Manual Itinerary</span>
              </Link>
            </div>
          </div>
        </div>
      </div>

      {/* Tabs & Map Toggle */}
      <div className="explore-toolbar" style={{ marginTop: '2.5rem' }}>
        <div className="explore-category-tabs">
          <button
            type="button"
            className={`explore-cat-tab ${activeTab === 'highlights' ? 'active' : ''}`}
            onClick={() => setActiveTab('highlights')}
          >
            <Layers size={14} />
            <span>All Highlights</span>
          </button>

          <button
            type="button"
            className={`explore-cat-tab ${activeTab === 'attractions' ? 'active' : ''}`}
            onClick={() => setActiveTab('attractions')}
          >
            <Landmark size={14} />
            <span>Attractions ({destSummary.attractions?.length || 0})</span>
          </button>

          <button
            type="button"
            className={`explore-cat-tab ${activeTab === 'hotels' ? 'active' : ''}`}
            onClick={() => setActiveTab('hotels')}
          >
            <Hotel size={14} />
            <span>Hotels & Stays ({destSummary.hotels?.length || 0})</span>
          </button>

          <button
            type="button"
            className={`explore-cat-tab ${activeTab === 'restaurants' ? 'active' : ''}`}
            onClick={() => setActiveTab('restaurants')}
          >
            <Utensils size={14} />
            <span>Dining ({destSummary.restaurants?.length || 0})</span>
          </button>

          <button
            type="button"
            className={`explore-cat-tab ${activeTab === 'activities' ? 'active' : ''}`}
            onClick={() => setActiveTab('activities')}
          >
            <Compass size={14} />
            <span>Activities ({destSummary.activities?.length || 0})</span>
          </button>
        </div>

        <button
          type="button"
          className={`btn btn-secondary btn-sm map-toggle-btn ${showMap ? 'active' : ''}`}
          onClick={() => setShowMap(!showMap)}
        >
          {showMap ? <Grid size={13} /> : <Map size={13} />}
          <span>{showMap ? 'Hide Map' : 'View on Map'}</span>
        </button>
      </div>

      {/* Map View Section */}
      {showMap && (
        <div className="explore-map-section" style={{ marginBottom: '2.5rem' }}>
          <MapView
            places={activePlaces}
            center={
              destSummary.lat && destSummary.lon
                ? { lat: destSummary.lat, lng: destSummary.lon }
                : { lat: 17.3850, lng: 78.4867 }
            }
            height="440px"
          />
        </div>
      )}

      {/* Places Grid */}
      {activePlaces.length === 0 ? (
        <div className="empty-state">
          <Compass size={24} style={{ color: 'var(--text-muted)' }} />
          <h3>No places listed in this category yet.</h3>
          <p className="empty-desc">
            Explore other tabs or use the AI planner to suggest activities in {destSummary.destination}.
          </p>
        </div>
      ) : (
        <div className="explore-places-grid">
          {activePlaces.map((place) => (
            <PlaceCard
              key={place.place_id}
              place={place}
              onAddToTrip={(p) => setModalPlace(p)}
            />
          ))}
        </div>
      )}

      {/* Add to Trip Modal */}
      <AddToTripModal
        isOpen={Boolean(modalPlace)}
        onClose={() => setModalPlace(null)}
        place={modalPlace}
      />
    </div>
  );
};
