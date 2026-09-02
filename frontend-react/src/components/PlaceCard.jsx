import { useState } from 'react';
import { Link } from 'react-router-dom';
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
  Scroll
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import { wishlistAPI, resolveImageUrl } from '../services/api';
import { SafeImage } from './SafeImage';

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
}) => {
  const { isAuthenticated } = useAuth();
  const { showSuccess, showError } = useToast();
  const [saved, setSaved] = useState(isWishlisted);
  const [saving, setSaving] = useState(false);

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

  const detailUrl = place.category === 'destination'
    ? `/explore/${encodeURIComponent(place.name.toLowerCase())}`
    : `/explore/place/${encodeURIComponent(placeId)}`;

  const photoUrl = resolveImageUrl(place.image_url || (place.photos && place.photos.length > 0 ? place.photos[0] : null));
  const isVerified = Boolean(place.image_verified || (place.image_url && !place.image_url.includes('undefined')));

  return (
    <div
      id={`place-card-${placeId}`}
      className={`place-card card ${isActive ? 'active-map-card' : ''}`}
      onClick={() => onCardClick && onCardClick(place)}
    >
      {/* Verified Photo or Tasteful No-Photo Botanical Placeholder */}
      <div className="place-card-image-wrapper">
        <SafeImage
          src={photoUrl}
          alt={place.name}
          isVerified={isVerified}
          className="place-card-image"
          placeholderText="NO VERIFIED PHOTO AVAILABLE"
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

      {/* Body */}
      <div className="place-card-body">
        <Link to={detailUrl} className="place-card-title-link">
          <h3 className="place-card-title">{place.name}</h3>
        </Link>

        <div className="place-card-location">
          <MapPin size={13} />
          <span>{place.address || (typeof place.location === 'string' ? place.location : '')}</span>
        </div>

        {place.description && (
          <p className="place-card-description">{place.description}</p>
        )}

        {/* Tags */}
        {place.tags && place.tags.length > 0 && (
          <div className="place-card-tags">
            {place.tags.slice(0, 3).map((t, idx) => (
              <span key={idx} className="place-tag">
                {t}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Footer Actions */}
      <div className="place-card-footer">
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
            <Link to={detailUrl} className="btn btn-secondary btn-sm">
              <span>Details</span>
              <ArrowUpRight size={13} />
            </Link>

            <button
              type="button"
              className="btn btn-primary btn-sm"
              onClick={handleAddClick}
              style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}
            >
              <Plus size={13} />
              <span>Add to Trip</span>
            </button>
          </>
        )}
      </div>
    </div>
  );
};
