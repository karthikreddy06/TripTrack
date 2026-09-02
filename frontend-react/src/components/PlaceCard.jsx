import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  MapPin,
  Star,
  Heart,
  Plus,
  ArrowUpRight,
  Utensils,
  Hotel,
  Landmark,
  Compass,
  Coffee,
  Trees,
  Scroll,
  Sparkles,
  Navigation
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import { wishlistAPI, resolveImageUrl } from '../services/api';
import { SafeImage } from './SafeImage';
import { formatDistance } from '../utils/geo';

const getCategoryIcon = (category) => {
  switch (category?.toLowerCase()) {
    case 'hotel':
      return <Hotel size={12} />;
    case 'restaurant':
      return <Utensils size={12} />;
    case 'cafe':
      return <Coffee size={12} />;
    case 'museum':
    case 'attraction':
      return <Landmark size={12} />;
    case 'park':
      return <Trees size={12} />;
    case 'historic':
      return <Scroll size={12} />;
    case 'activity':
      return <Compass size={12} />;
    default:
      return <MapPin size={12} />;
  }
};

export const PlaceCard = ({
  place,
  onAddToTrip,
  isWishlisted = false,
  onWishlistToggled,
  showRemoveButton = false,
  onRemoveFromWishlist,
  isActive = false,
  onCardClick = null,
  anchorDistanceKm = null,
}) => {
  const { isAuthenticated } = useAuth();
  const { showSuccess, showError } = useToast();
  const navigate = useNavigate();
  const [saved, setSaved] = useState(isWishlisted);
  const [saving, setSaving] = useState(false);
  const [imgError, setImgError] = useState(false);

  const placeId = place?.id || place?.place_id || place?.provider_id || '';

  const handleToggleWishlist = async (e) => {
    e.preventDefault();
    e.stopPropagation();

    if (!isAuthenticated) {
      showError('Please sign in to save places to your wishlist.');
      return;
    }

    try {
      setSaving(true);
      if (saved) {
        const check = await wishlistAPI.checkSaved(placeId);
        if (check.is_saved && check.wishlist_id) {
          await wishlistAPI.removeFromWishlist(check.wishlist_id);
          setSaved(false);
          showSuccess(`Removed "${place.name}" from wishlist.`);
          if (onWishlistToggled) onWishlistToggled(placeId, false);
        }
      } else {
        await wishlistAPI.addToWishlist({
          place_id: placeId,
          name: place.name,
          category: place.category,
          location: place.location || place.address,
          image_url: place.image_verified ? place.image_url : null,
          rating: place.rating || null,
          description: place.description,
          metadata: {
            lat: place.lat,
            lon: place.lon,
            address: place.address,
            tags: place.tags,
            provider_id: place.provider_id || placeId
          },
        });
        setSaved(true);
        showSuccess(`Saved "${place.name}" to wishlist!`);
        if (onWishlistToggled) onWishlistToggled(placeId, true);
      }
    } catch {
      showError('Failed to update wishlist. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  const handleAddClick = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (onAddToTrip) {
      onAddToTrip(place);
    }
  };

  const handlePlanWithAI = (e) => {
    e.preventDefault();
    e.stopPropagation();
    const dest = place.location || place.address || place.name;
    const cleanDest = dest.split(',')[0].trim();
    navigate('/ai-planner', {
      state: {
        prefill: {
          destination: cleanDest,
          anchor_place_id: placeId,
          anchor_place_name: place.name,
        },
      },
    });
  };

  const detailUrl = place.category === 'destination'
    ? `/explore/${encodeURIComponent(place.name.toLowerCase())}`
    : `/explore/place/${encodeURIComponent(placeId)}`;

  const photoUrl = resolveImageUrl(place.image_url || (place.photos && place.photos.length > 0 ? place.photos[0] : null));
  const hasVerifiedPhoto = Boolean(
    !imgError &&
    place.image_verified &&
    photoUrl &&
    typeof photoUrl === 'string' &&
    photoUrl.trim() !== '' &&
    !photoUrl.includes('undefined') &&
    !photoUrl.includes('null')
  );
  const displayDist = anchorDistanceKm ?? place.distance_km;

  return (
    <div
      id={`place-card-${placeId}`}
      className={`place-card card ${isActive ? 'active-map-card' : ''} ${!hasVerifiedPhoto ? 'no-photo-card' : ''}`}
      onClick={() => onCardClick && onCardClick(place)}
      style={{
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        transition: 'transform 0.2s, box-shadow 0.2s',
      }}
    >
      <div>
        {/* Render Image ONLY IF verified real photo exists and hasn't errored */}
        {hasVerifiedPhoto ? (
          <div className="place-card-image-wrapper">
            <SafeImage
              src={photoUrl}
              alt={place.name}
              isVerified={true}
              className="place-card-image"
              onError={() => setImgError(true)}
            />

            <div className="place-card-badge-row">
              <span className={`place-category-badge cat-${place.category?.toLowerCase()}`}>
                {getCategoryIcon(place.category)}
                <span>{place.category?.toUpperCase()}</span>
              </span>

              {typeof place.rating === 'number' && place.rating > 0 && (
                <span className="place-rating-badge">
                  <Star size={11} fill="currentColor" />
                  <span>{place.rating.toFixed(1)}</span>
                  {place.review_count > 0 && (
                    <span style={{ opacity: 0.8, fontSize: '0.65rem' }}>({place.review_count})</span>
                  )}
                </span>
              )}
            </div>

            {/* Wishlist toggle heart button */}
            {!showRemoveButton && (
              <button
                type="button"
                className={`place-wishlist-btn ${saved ? 'saved' : ''}`}
                onClick={handleToggleWishlist}
                disabled={saving}
                title={saved ? 'Remove from Wishlist' : 'Save to Wishlist'}
                aria-label="Wishlist"
              >
                <Heart size={16} fill={saved ? 'var(--accent)' : 'none'} />
              </button>
            )}
          </div>
        ) : (
          /* Clean info card header when NO verified photo is available — no image box, no empty area */
          <div
            className="place-card-no-photo-header"
            style={{
              padding: '1.15rem 1.25rem 0.25rem 1.25rem',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span className={`place-category-badge cat-${place.category?.toLowerCase()}`}>
                {getCategoryIcon(place.category)}
                <span>{place.category?.toUpperCase()}</span>
              </span>

              {typeof place.rating === 'number' && place.rating > 0 && (
                <span className="place-rating-badge">
                  <Star size={11} fill="currentColor" />
                  <span>{place.rating.toFixed(1)}</span>
                </span>
              )}
            </div>

            {!showRemoveButton && (
              <button
                type="button"
                className={`place-wishlist-btn-inline ${saved ? 'saved' : ''}`}
                onClick={handleToggleWishlist}
                disabled={saving}
                title={saved ? 'Remove from Wishlist' : 'Save to Wishlist'}
                aria-label="Wishlist"
                style={{
                  background: saved ? 'var(--accent-light, #f4e8dc)' : 'none',
                  border: 'none',
                  cursor: 'pointer',
                  padding: '4px',
                  borderRadius: '50%',
                  display: 'flex',
                  alignItems: 'center',
                  color: saved ? 'var(--accent)' : 'var(--text-secondary)',
                }}
              >
                <Heart size={16} fill={saved ? 'var(--accent)' : 'none'} />
              </button>
            )}
          </div>
        )}

        {/* Card Body */}
        <div className="place-card-body" style={{ padding: '0.85rem 1.25rem 1rem 1.25rem' }}>
          <Link to={detailUrl} className="place-card-title-link">
            <h3 className="place-card-title" style={{ fontSize: '1.15rem', marginBottom: '0.35rem' }}>
              {place.name}
            </h3>
          </Link>

          <div
            className="place-card-location"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.35rem',
              fontSize: '0.8rem',
              color: 'var(--text-secondary)',
              marginBottom: '0.5rem',
            }}
          >
            <MapPin size={13} style={{ flexShrink: 0 }} />
            <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {place.address || (typeof place.location === 'string' ? place.location : '')}
            </span>
          </div>

          {/* Distance Indicator if available */}
          {displayDist !== null && displayDist !== undefined && (
            <div
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.3rem',
                fontFamily: 'var(--font-mono, monospace)',
                fontSize: '0.75rem',
                color: 'var(--primary-green)',
                background: 'rgba(95, 155, 104, 0.1)',
                padding: '2px 7px',
                borderRadius: '4px',
                marginBottom: '0.65rem',
                fontWeight: 600,
              }}
            >
              <Navigation size={11} />
              <span>{formatDistance(displayDist)} away</span>
            </div>
          )}

          {place.description && (
            <p
              className="place-card-description"
              style={{
                fontSize: '0.85rem',
                lineHeight: 1.45,
                color: 'var(--text-secondary)',
                marginBottom: '0.75rem',
                display: '-webkit-box',
                WebkitLineClamp: 3,
                WebkitBoxOrient: 'vertical',
                overflow: 'hidden',
              }}
            >
              {place.description}
            </p>
          )}

          {/* Tags */}
          {place.tags && place.tags.length > 0 && (
            <div className="place-card-tags" style={{ display: 'flex', gap: '0.35rem', flexWrap: 'wrap' }}>
              {place.tags.slice(0, 3).map((t, idx) => (
                <span key={idx} className="place-tag" style={{ fontSize: '0.7rem', padding: '2px 7px' }}>
                  {t}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Footer Actions */}
      <div
        className="place-card-footer"
        style={{
          padding: '0.75rem 1.25rem 1.1rem 1.25rem',
          borderTop: '1px solid var(--border-light, #f0f0f0)',
          display: 'flex',
          gap: '0.5rem',
          alignItems: 'center',
        }}
      >
        {showRemoveButton ? (
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={() => onRemoveFromWishlist && onRemoveFromWishlist(place)}
            style={{ width: '100%' }}
          >
            Remove from Wishlist
          </button>
        ) : (
          <>
            <Link to={detailUrl} className="btn btn-secondary btn-sm" style={{ flex: '1', justifyContent: 'center' }}>
              <span>Details</span>
              <ArrowUpRight size={12} />
            </Link>

            <button
              type="button"
              className="btn btn-primary btn-sm"
              onClick={handleAddClick}
              title="Add to Trip Itinerary"
              style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}
            >
              <Plus size={13} />
              <span>Add</span>
            </button>

            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={handlePlanWithAI}
              title="Plan itinerary with AI around this place"
              style={{ padding: '0.45rem 0.6rem', color: 'var(--primary-green)' }}
            >
              <Sparkles size={13} />
            </button>
          </>
        )}
      </div>
    </div>
  );
};
