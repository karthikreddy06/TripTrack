import { useState, useEffect, useCallback, useMemo } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import {
  MapPin,
  Star,
  Heart,
  Plus,
  ArrowLeft,
  Globe,
  Clock,
  Phone,
  Compass,
  Scroll,
  ExternalLink,
  Sparkles
} from 'lucide-react';
import { exploreAPI, wishlistAPI, resolveImageUrl, extractErrorMessage } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import { PlaceCard } from '../components/PlaceCard';
import { MapView } from '../components/MapView';
import { AddToTripModal } from '../components/AddToTripModal';
import { SafeImage } from '../components/SafeImage';
import { calculateDistanceKm } from '../utils/geo';

export const PlaceDetail = () => {
  const { placeId } = useParams();
  const decodedPlaceId = decodeURIComponent(placeId || '');
  const { isAuthenticated } = useAuth();
  const { showSuccess, showError } = useToast();
  const navigate = useNavigate();

  const [placeData, setPlaceData] = useState(null);
  const [nearbyPlaces, setNearbyPlaces] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [isSaved, setIsSaved] = useState(false);
  const [savingWishlist, setSavingWishlist] = useState(false);
  const [modalPlace, setModalPlace] = useState(null);

  const fetchPlace = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await exploreAPI.getPlaceDetails(decodedPlaceId);
      setPlaceData(data.place);
      setNearbyPlaces(data.nearby_places || []);

      const pId = data.place?.id || data.place?.place_id || decodedPlaceId;
      if (isAuthenticated) {
        const check = await wishlistAPI.checkSaved(pId);
        setIsSaved(check.is_saved);
      }
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, [decodedPlaceId, isAuthenticated]);

  useEffect(() => {
    fetchPlace();
  }, [fetchPlace]);

  const handleToggleWishlist = async () => {
    if (!isAuthenticated) {
      showError('Please sign in to save places to your wishlist.');
      return;
    }

    const pId = placeData.id || placeData.place_id || decodedPlaceId;

    try {
      setSavingWishlist(true);
      if (isSaved) {
        const check = await wishlistAPI.checkSaved(pId);
        if (check.is_saved && check.wishlist_id) {
          await wishlistAPI.removeFromWishlist(check.wishlist_id);
          setIsSaved(false);
          showSuccess(`Removed "${placeData.name}" from wishlist.`);
        }
      } else {
        await wishlistAPI.addToWishlist({
          place_id: pId,
          name: placeData.name,
          category: placeData.category,
          location: placeData.location || placeData.address,
          image_url: placeData.image_verified ? placeData.image_url : null,
          rating: placeData.rating || null,
          description: placeData.description,
          metadata: {
            lat: placeData.lat,
            lon: placeData.lon,
            address: placeData.address,
            tags: placeData.tags,
            provider_id: placeData.provider_id || pId
          },
        });
        setIsSaved(true);
        showSuccess(`Saved "${placeData.name}" to wishlist!`);
      }
    } catch {
      showError('Failed to update wishlist. Please try again.');
    } finally {
      setSavingWishlist(false);
    }
  };

  const handlePlanAroundPlace = () => {
    if (!placeData) return;
    const loc = placeData.location || placeData.address || placeData.name;
    const dest = loc.split(',')[0].trim();
    navigate('/ai-planner', {
      state: {
        prefill: {
          destination: dest,
          anchor_place_id: placeData.id || placeData.place_id || decodedPlaceId,
          anchor_place_name: placeData.name,
        },
      },
    });
  };

  const nearbyWithDistances = useMemo(() => {
    if (!placeData || !nearbyPlaces) return [];
    return nearbyPlaces.map((np) => {
      const dist = calculateDistanceKm(placeData.lat, placeData.lon, np.lat, np.lon);
      return { ...np, distance_km: dist };
    }).sort((a, b) => (a.distance_km || 999) - (b.distance_km || 999));
  }, [placeData, nearbyPlaces]);

  if (loading) {
    return (
      <div className="main-content">
        <div className="card" style={{ textAlign: 'center', padding: '4rem 1.5rem' }}>
          <div className="spinner" style={{ margin: '0 auto 1rem' }} />
          <p style={{ color: 'var(--text-secondary)' }}>Loading place details from OpenStreetMap...</p>
        </div>
      </div>
    );
  }

  if (error || !placeData) {
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
          <h2>Place Details Unavailable</h2>
          <p style={{ color: 'var(--text-secondary)', margin: '0.5rem 0 1.5rem' }}>
            {error || 'The requested place could not be located.'}
          </p>
          <Link to="/explore" className="btn btn-primary">
            Explore Other Destinations
          </Link>
        </div>
      </div>
    );
  }

  const pId = placeData.id || placeData.place_id || decodedPlaceId;
  const photoUrl = resolveImageUrl(placeData.image_url);
  const hasVerifiedPhoto = Boolean(placeData.image_verified && photoUrl);

  return (
    <div className="main-content">
      {/* Back button */}
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
        <span>Back to Explore</span>
      </Link>

      {/* Place Hero Card */}
      <div className="place-detail-hero card" style={{ marginBottom: '2.5rem' }}>
        <div className={hasVerifiedPhoto ? 'place-detail-grid' : 'place-detail-grid-no-photo'} style={{ display: 'grid', gridTemplateColumns: hasVerifiedPhoto ? '1.1fr 1fr' : '1fr', gap: '2rem' }}>
          {/* Main Photo ONLY IF verified */}
          {hasVerifiedPhoto && (
            <div className="place-detail-photo-gallery" style={{ height: '360px', borderRadius: 'var(--radius-md)', overflow: 'hidden' }}>
              <SafeImage
                src={photoUrl}
                alt={placeData.name}
                isVerified={true}
                style={{ height: '100%' }}
              />
            </div>
          )}

          {/* Place Details Content */}
          <div className="place-detail-info">
            <div className="editorial-mark">
              <i></i> {placeData.category?.toUpperCase() || 'PLACE'}
            </div>

            <h1 className="place-detail-title" style={{ fontSize: '2.1rem', margin: '0.35rem 0 0.5rem 0' }}>
              {placeData.name}
            </h1>

            <div className="place-detail-address" style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: '0.75rem' }}>
              <MapPin size={14} />
              <span>{placeData.address || placeData.location || 'Location details available'}</span>
            </div>

            {/* Rating if available */}
            {typeof placeData.rating === 'number' && placeData.rating > 0 && (
              <div className="place-detail-rating-row" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '3px', color: '#d97706', fontWeight: 600, fontSize: '0.9rem' }}>
                  <Star size={14} fill="currentColor" />
                  <span>{placeData.rating.toFixed(1)}</span>
                </div>
                {placeData.review_count > 0 && (
                  <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                    ({placeData.review_count} reviews)
                  </span>
                )}
              </div>
            )}

            <p className="place-detail-desc" style={{ lineHeight: '1.65', color: 'var(--text-primary)', fontSize: '0.95rem' }}>
              {placeData.description}
            </p>

            {/* Tags */}
            {placeData.tags && placeData.tags.length > 0 && (
              <div className="place-detail-tags" style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap', marginTop: '1rem' }}>
                {placeData.tags.map((tag, idx) => (
                  <span key={idx} className="place-tag">
                    {tag}
                  </span>
                ))}
              </div>
            )}

            {/* Useful Contact & Provenance Metadata */}
            <div className="place-detail-meta-box" style={{ marginTop: '1.25rem', display: 'flex', flexDirection: 'column', gap: '0.45rem' }}>
              {placeData.opening_hours && (
                <div className="meta-item" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.85rem' }}>
                  <Clock size={13} />
                  <span><strong>Hours:</strong> {placeData.opening_hours}</span>
                </div>
              )}

              {placeData.phone && (
                <div className="meta-item" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.85rem' }}>
                  <Phone size={13} />
                  <span><strong>Phone:</strong> {placeData.phone}</span>
                </div>
              )}

              {placeData.website && (
                <div className="meta-item" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.85rem' }}>
                  <Globe size={13} />
                  <a
                    href={placeData.website}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{ color: 'var(--primary-green)', textDecoration: 'underline' }}
                  >
                    Official Website
                  </a>
                </div>
              )}

              {placeData.wikipedia_url && (
                <div className="meta-item" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.85rem' }}>
                  <Scroll size={13} />
                  <a
                    href={placeData.wikipedia_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{ color: 'var(--primary-green)', textDecoration: 'underline' }}
                  >
                    Wikipedia Article
                  </a>
                </div>
              )}

              {placeData.source?.source_url && (
                <div className="meta-item" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.85rem' }}>
                  <ExternalLink size={13} />
                  <a
                    href={placeData.source.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{ color: 'var(--text-secondary)', textDecoration: 'underline' }}
                  >
                    OpenStreetMap Provenance
                  </a>
                </div>
              )}
            </div>

            {/* Action Buttons */}
            <div className="place-detail-actions-row" style={{ marginTop: '1.75rem', display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={handleToggleWishlist}
                disabled={savingWishlist}
                style={{ display: 'inline-flex', alignItems: 'center', gap: '0.45rem' }}
              >
                <Heart size={14} fill={isSaved ? 'var(--accent)' : 'none'} color={isSaved ? 'var(--accent)' : 'currentColor'} />
                <span>{isSaved ? 'Saved in Wishlist' : 'Save to Wishlist'}</span>
              </button>

              <button
                type="button"
                className="btn btn-primary"
                onClick={() => setModalPlace(placeData)}
                style={{ display: 'inline-flex', alignItems: 'center', gap: '0.45rem' }}
              >
                <Plus size={14} />
                <span>Add to Trip</span>
              </button>

              <button
                type="button"
                className="btn btn-secondary"
                onClick={handlePlanAroundPlace}
                style={{ display: 'inline-flex', alignItems: 'center', gap: '0.45rem', color: 'var(--primary-green)' }}
              >
                <Sparkles size={14} />
                <span>Plan Around This Place</span>
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Map & Location Section */}
      {placeData.lat && placeData.lon && (
        <div className="card" style={{ marginBottom: '2.5rem', padding: '1.75rem' }}>
          <div className="section-header" style={{ marginBottom: '1.25rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <h3 style={{ fontSize: '1.35rem', margin: 0 }}>OpenStreetMap Location</h3>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.8rem', margin: '0.2rem 0 0 0' }}>
                Interactive map displaying {placeData.name} and neighboring sights.
              </p>
            </div>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
              {placeData.lat.toFixed(4)}, {placeData.lon.toFixed(4)}
            </span>
          </div>
          <MapView
            places={[placeData, ...nearbyPlaces]}
            center={{ lat: placeData.lat, lng: placeData.lon }}
            zoom={14}
            height="380px"
            selectedPlaceId={pId}
          />
        </div>
      )}

      {/* Nearby Places Section with Distance */}
      {nearbyWithDistances.length > 0 && (
        <div className="nearby-places-section" style={{ marginTop: '3rem' }}>
          <div className="section-header" style={{ marginBottom: '1.25rem' }}>
            <div>
              <h2 className="section-title">Nearby Places &amp; Distances</h2>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
                Other notable sights, restaurants, and stays with approximate distance from {placeData.name}.
              </p>
            </div>
          </div>

          <div className="places-grid">
            {nearbyWithDistances.map((nearby) => {
              const nId = nearby.id || nearby.place_id || nearby.provider_id;
              return (
                <PlaceCard
                  key={nId}
                  place={nearby}
                  anchorDistanceKm={nearby.distance_km}
                  onAddToTrip={(p) => setModalPlace(p)}
                />
              );
            })}
          </div>
        </div>
      )}

      {/* Add to Trip Modal */}
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
