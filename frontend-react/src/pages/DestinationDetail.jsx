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
        ].filter((p, i, self) => {
          const pId = p.id || p.place_id || p.provider_id;
          return i === self.findIndex((t) => (t.id || t.place_id || t.provider_id) === pId);
        });
    }
  }, [destSummary, activeTab]);

  if (loading) {
    return (
      <div className="main-content">
        <div className="loading-container" style={{ padding: '6rem 1rem', textAlign: 'center' }}>
          <div className="spinner" style={{ margin: '0 auto 1rem' }} />
          <p style={{ color: 'var(--text-secondary)' }}>Loading destination guide for {decodedDestination}...</p>
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
        <div className="card" style={{ textAlign: 'center', padding: '3.5rem 1.5rem' }}>
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

      {/* Destination Hero Header (Rich Editorial Vector Banner) */}
      <div
        className="destination-hero-header card"
        style={{
          marginBottom: '2.5rem',
          padding: 0,
          overflow: 'hidden',
          border: '1px solid var(--border, #e5e3db)',
        }}
      >
        <div
          style={{
            position: 'relative',
            background: 'linear-gradient(135deg, #183324 0%, #264a35 50%, #3a684b 100%)',
            color: '#FFFFFF',
            padding: '2.25rem 2rem',
            overflow: 'hidden',
          }}
        >
          {/* Topographic Vector Pattern */}
          <svg
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              width: '100%',
              height: '100%',
              opacity: 0.16,
              pointerEvents: 'none',
            }}
            viewBox="0 0 600 200"
            preserveAspectRatio="none"
          >
            <path d="M-20,100 C120,20 280,180 440,60 C520,0 580,120 640,80" fill="none" stroke="#FFFFFF" strokeWidth="1.2" strokeDasharray="4 4" />
            <path d="M-20,160 C150,80 300,190 460,110 C530,70 590,160 640,120" fill="none" stroke="#FFFFFF" strokeWidth="0.8" />
            <circle cx="500" cy="50" r="30" fill="none" stroke="#FFFFFF" strokeWidth="0.8" strokeDasharray="3 3" />
            <circle cx="500" cy="50" r="6" fill="none" stroke="#FFFFFF" strokeWidth="1" />
          </svg>

          <div style={{ position: 'relative', zIndex: 2 }}>
            <div className="editorial-mark" style={{ color: 'rgba(255, 255, 255, 0.8)', borderColor: 'rgba(255, 255, 255, 0.3)' }}>
              <i></i> 02 / DESTINATION DOSSIER
            </div>

            <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem', marginTop: '0.45rem' }}>
              <div>
                <h1 style={{ fontSize: '2.5rem', fontFamily: 'var(--font-serif)', margin: '0 0 0.35rem 0', color: '#FFFFFF' }}>
                  {destSummary.destination}
                </h1>

                {destSummary.country && (
                  <p style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: '#a0e8be', fontSize: '0.95rem', margin: 0 }}>
                    <MapPin size={15} />
                    <span>{destSummary.country}</span>
                    {destSummary.lat && destSummary.lon && (
                      <span style={{ color: 'rgba(255, 255, 255, 0.65)', fontFamily: 'var(--font-mono)', fontSize: '0.75rem', marginLeft: '0.5rem' }}>
                        ({Math.abs(destSummary.lat).toFixed(2)}°N, {Math.abs(destSummary.lon).toFixed(2)}°E)
                      </span>
                    )}
                  </p>
                )}
              </div>

              <div style={{ display: 'flex', gap: '0.65rem', alignItems: 'center' }}>
                <Link
                  to="/ai-planner"
                  state={{ prefill: { destination: destSummary.destination } }}
                  className="btn btn-primary"
                  style={{ display: 'inline-flex', alignItems: 'center', gap: '0.4rem', background: 'var(--accent, #d97706)', border: 'none' }}
                >
                  <Sparkles size={14} />
                  <span>Plan Trip with AI</span>
                </Link>
                <Link
                  to="/trips/new"
                  state={{ prefill: { destination: destSummary.destination } }}
                  className="btn btn-secondary"
                  style={{ background: 'rgba(255, 255, 255, 0.15)', color: '#FFFFFF', border: '1px solid rgba(255, 255, 255, 0.25)' }}
                >
                  <span>Manual Itinerary</span>
                </Link>
              </div>
            </div>

            <p style={{ fontSize: '0.95rem', lineHeight: '1.65', color: 'rgba(255, 255, 255, 0.9)', maxWidth: '850px', margin: '1rem 0 1.25rem 0' }}>
              {destSummary.overview || destSummary.description}
            </p>

            <div style={{ display: 'flex', gap: '0.65rem', flexWrap: 'wrap', alignItems: 'center' }}>
              {destSummary.best_time_to_visit && (
                <div
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '0.35rem',
                    background: 'rgba(0, 0, 0, 0.35)',
                    backdropFilter: 'blur(6px)',
                    padding: '4px 10px',
                    borderRadius: '12px',
                    fontSize: '0.75rem',
                    color: 'rgba(255, 255, 255, 0.95)',
                    fontFamily: 'var(--font-mono)',
                  }}
                >
                  <Calendar size={12} style={{ color: '#a0e8be' }} />
                  <span>Best Season: {destSummary.best_time_to_visit}</span>
                </div>
              )}

              {destSummary.currency && (
                <div
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '0.35rem',
                    background: 'rgba(0, 0, 0, 0.35)',
                    backdropFilter: 'blur(6px)',
                    padding: '4px 10px',
                    borderRadius: '12px',
                    fontSize: '0.75rem',
                    color: 'rgba(255, 255, 255, 0.95)',
                    fontFamily: 'var(--font-mono)',
                  }}
                >
                  <DollarSign size={12} style={{ color: '#a0e8be' }} />
                  <span>Currency: {destSummary.currency}</span>
                </div>
              )}

              <div
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '0.35rem',
                  background: 'rgba(255, 255, 255, 0.15)',
                  backdropFilter: 'blur(6px)',
                  padding: '4px 10px',
                  borderRadius: '12px',
                  fontSize: '0.75rem',
                  color: 'rgba(255, 255, 255, 0.95)',
                  fontFamily: 'var(--font-mono)',
                }}
              >
                <span>OpenStreetMap &amp; Overpass Grounding</span>
              </div>
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
            <span>Hotels &amp; Stays ({destSummary.hotels?.length || 0})</span>
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
          <span>{showMap ? 'Hide Map' : 'Interactive Map'}</span>
        </button>
      </div>

      {/* Map View Section */}
      {showMap && (
        <div className="explore-map-section" style={{ marginBottom: '2.5rem' }}>
          <MapView
            places={activePlaces}
            center={
              destSummary.lat && destSummary.lon
                ? [destSummary.lat, destSummary.lon]
                : [17.3850, 78.4867]
            }
            height="440px"
          />
        </div>
      )}

      {/* Places Grid */}
      <div className="explore-results-section">
        <h3 className="section-title" style={{ marginBottom: '1.5rem', textTransform: 'capitalize' }}>
          {activeTab} in {destSummary.destination} ({activePlaces.length})
        </h3>

        {activePlaces.length === 0 ? (
          <div className="card empty-state" style={{ textAlign: 'center', padding: '3.5rem 1.5rem' }}>
            <Compass size={36} style={{ color: 'var(--accent)', margin: '0 auto 1rem' }} />
            <h3>No {activeTab} listed yet</h3>
            <p style={{ color: 'var(--text-secondary)', margin: '0.5rem 0' }}>
              Check back soon as OpenStreetMap contributors catalog more places in this area.
            </p>
          </div>
        ) : (
          <div className="places-grid">
            {activePlaces.map((place) => {
              const pId = place.id || place.place_id || place.provider_id;
              return (
                <PlaceCard
                  key={pId}
                  place={place}
                  onAddToTrip={(p) => setModalPlace(p)}
                />
              );
            })}
          </div>
        )}
      </div>

      {/* Add To Trip Modal */}
      {modalPlace && (
        <AddToTripModal
          place={modalPlace}
          onClose={() => setModalPlace(null)}
          onSuccess={() => {}}
        />
      )}
    </div>
  );
};
