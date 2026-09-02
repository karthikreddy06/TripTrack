import { useState, useEffect, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  MapPin,
  Star,
  Heart,
  Plus,
  ArrowLeft,
  Globe,
  Clock,
  Phone,
  CameraOff,
  Navigation
} from 'lucide-react';
import { exploreAPI, wishlistAPI, extractErrorMessage } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import { PlaceCard } from '../components/PlaceCard';
import { MapView } from '../components/MapView';
import { AddToTripModal } from '../components/AddToTripModal';

export const PlaceDetail = () => {
  const { placeId } = useParams();
  const decodedPlaceId = decodeURIComponent(placeId || '');
  const { isAuthenticated } = useAuth();
  const { showSuccess, showError } = useToast();

  const [placeData, setPlaceData] = useState(null);
  const [nearbyPlaces, setNearbyPlaces] = useState([]);
  const [activePhotoIndex, setActivePhotoIndex] = useState(0);
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
      setActivePhotoIndex(0);

      // Check wishlist status if authenticated
      if (isAuthenticated) {
        const check = await wishlistAPI.checkSaved(decodedPlaceId);
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

    try {
      setSavingWishlist(true);
      if (isSaved) {
        const check = await wishlistAPI.checkSaved(placeData.place_id);
        if (check.is_saved && check.wishlist_id) {
          await wishlistAPI.removeFromWishlist(check.wishlist_id);
          setIsSaved(false);
          showSuccess(`Removed "${placeData.name}" from wishlist.`);
        }
      } else {
        await wishlistAPI.addToWishlist({
          place_id: placeData.place_id,
          name: placeData.name,
          category: placeData.category,
          location: placeData.location,
          image_url: placeData.image_url || (placeData.photos && placeData.photos[0]) || null,
          rating: placeData.rating,
          description: placeData.description,
          metadata: {
            lat: placeData.lat,
            lon: placeData.lon,
            address: placeData.address,
            price_level: placeData.price_level,
            tags: placeData.tags,
            review_count: placeData.review_count,
            provider_place_id: placeData.provider_place_id || placeData.place_id
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

  if (loading) {
    return (
      <div className="main-content">
        <div className="loading-container" style={{ padding: '6rem 1rem' }}>
          <div className="spinner spinner-lg" />
          <p style={{ marginTop: '1rem' }}>Loading verified place details...</p>
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
        <div className="card" style={{ textAlign: 'center', padding: '3rem 1.5rem' }}>
          <h2>Place Information Unavailable</h2>
          <p style={{ color: 'var(--text-secondary)', margin: '0.5rem 0 1.5rem' }}>
            {error || 'Unable to load place details.'}
          </p>
          <Link to="/explore" className="btn btn-primary">
            Explore Places
          </Link>
        </div>
      </div>
    );
  }

  const photosList = placeData.photos && placeData.photos.length > 0
    ? placeData.photos
    : placeData.image_url
    ? [placeData.image_url]
    : [];

  const currentPhoto = photosList[activePhotoIndex] || null;

  return (
    <div className="main-content">
      {/* Back Link */}
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
      <div className="card place-detail-hero" style={{ marginBottom: '2.5rem' }}>
        <div className="place-detail-hero-grid">
          {/* Photo Gallery Column */}
          <div className="place-detail-gallery-col">
            <div className="place-detail-hero-img-wrapper">
              {currentPhoto ? (
                <img
                  src={currentPhoto}
                  alt={placeData.name}
                  className="place-detail-hero-img"
                  loading="lazy"
                />
              ) : (
                <div className="no-photo-placeholder" style={{ height: '380px', borderRadius: 'var(--radius-lg)' }}>
                  <CameraOff size={36} className="no-photo-icon" />
                  <span className="no-photo-text">No verified photo available from provider</span>
                </div>
              )}
            </div>

            {/* Thumbnail Strip */}
            {photosList.length > 1 && (
              <div className="place-detail-thumb-strip">
                {photosList.map((photoUrl, idx) => (
                  <button
                    key={idx}
                    type="button"
                    className={`place-gallery-thumb-btn ${idx === activePhotoIndex ? 'active' : ''}`}
                    onClick={() => setActivePhotoIndex(idx)}
                  >
                    <img
                      src={photoUrl}
                      alt={`${placeData.name} ${idx + 1}`}
                      className="place-gallery-thumb-img"
                    />
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Place Content */}
          <div className="place-detail-info-col">
            <div className="editorial-mark">
              <i></i> 03 / PLACE DETAILS
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem', flexWrap: 'wrap', marginBottom: '0.5rem' }}>
              <span className={`place-category-badge cat-${placeData.category?.toLowerCase()}`}>
                <span>{placeData.category?.toUpperCase()}</span>
              </span>

              {placeData.rating > 0 && (
                <span className="place-rating-badge">
                  <Star size={11} fill="currentColor" />
                  <span>{placeData.rating.toFixed(1)}</span>
                  {placeData.review_count > 0 && (
                    <span style={{ opacity: 0.8, fontSize: '0.65rem' }}>({placeData.review_count} reviews)</span>
                  )}
                </span>
              )}

              {placeData.price_level && (
                <span className="place-tag price-tag">{placeData.price_level}</span>
              )}
            </div>

            <h1 className="place-detail-title">{placeData.name}</h1>

            <div className="place-detail-location-row">
              <MapPin size={14} />
              <span>{placeData.address || placeData.location}</span>
            </div>

            {placeData.description && (
              <p className="place-detail-desc">{placeData.description}</p>
            )}

            {/* Metadata Grid */}
            <div className="place-detail-meta-box">
              {placeData.opening_hours && (
                <div className="meta-item">
                  <Clock size={13} />
                  <span><strong>Hours:</strong> {placeData.opening_hours}</span>
                </div>
              )}

              {placeData.phone && (
                <div className="meta-item">
                  <Phone size={13} />
                  <span><strong>Phone:</strong> {placeData.phone}</span>
                </div>
              )}

              {placeData.website && (
                <div className="meta-item">
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

              {placeData.google_maps_uri && (
                <div className="meta-item">
                  <Navigation size={13} />
                  <a
                    href={placeData.google_maps_uri}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{ color: 'var(--primary-green)', textDecoration: 'underline' }}
                  >
                    View on Google Maps
                  </a>
                </div>
              )}
            </div>

            {/* Action Buttons */}
            <div className="place-detail-actions-row">
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
            </div>
          </div>
        </div>
      </div>

      {/* Map & Location Section */}
      {placeData.lat && placeData.lon && (
        <div className="card" style={{ marginBottom: '2.5rem', padding: '1.75rem' }}>
          <div className="section-header" style={{ marginBottom: '1.25rem' }}>
            <h3 style={{ fontSize: '1.35rem', margin: 0 }}>Professional Map Location</h3>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
              {placeData.lat.toFixed(4)}, {placeData.lon.toFixed(4)}
            </span>
          </div>
          <MapView
            places={[placeData, ...nearbyPlaces]}
            center={{ lat: placeData.lat, lng: placeData.lon }}
            zoom={14}
            height="380px"
            selectedPlaceId={placeData.place_id}
          />
        </div>
      )}

      {/* Nearby Places Section */}
      {nearbyPlaces.length > 0 && (
        <div className="nearby-places-section" style={{ marginTop: '3rem' }}>
          <div className="section-header">
            <div>
              <h2 className="section-title">Verified Nearby Places</h2>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
                Other notable sights, restaurants, and stays in this area.
              </p>
            </div>
          </div>

          <div className="explore-places-grid">
            {nearbyPlaces.map((nearby) => (
              <PlaceCard
                key={nearby.place_id}
                place={nearby}
                onAddToTrip={(p) => setModalPlace(p)}
              />
            ))}
          </div>
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
