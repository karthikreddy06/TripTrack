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
  CameraOff
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import { wishlistAPI } from '../services/api';

const getCategoryIcon = (category) => {
  switch (category?.toLowerCase()) {
    case 'hotel':
      return <Hotel size={12} />;
    case 'restaurant':
      return <Utensils size={12} />;
    case 'attraction':
      return <Landmark size={12} />;
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
  const [imgError, setImgError] = useState(false);

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
        const check = await wishlistAPI.checkSaved(place.place_id);
        if (check.is_saved && check.wishlist_id) {
          await wishlistAPI.removeFromWishlist(check.wishlist_id);
          setSaved(false);
          showSuccess(`Removed "${place.name}" from wishlist.`);
          if (onWishlistToggled) onWishlistToggled(place.place_id, false);
        }
      } else {
        await wishlistAPI.addToWishlist({
          place_id: place.place_id,
          name: place.name,
          category: place.category,
          location: place.location,
          image_url: place.image_url || (place.photos && place.photos[0]) || null,
          rating: place.rating,
          description: place.description,
          metadata: {
            lat: place.lat,
            lon: place.lon,
            address: place.address,
            price_level: place.price_level,
            tags: place.tags,
            review_count: place.review_count,
            provider_place_id: place.provider_place_id || place.place_id
          },
        });
        setSaved(true);
        showSuccess(`Saved "${place.name}" to wishlist!`);
        if (onWishlistToggled) onWishlistToggled(place.place_id, true);
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
    : `/explore/place/${encodeURIComponent(place.place_id)}`;

  const photoUrl = (!imgError && (place.image_url || (place.photos && place.photos.length > 0 ? place.photos[0] : null))) || null;

  return (
    <div
      className={`place-card card ${isActive ? 'active-map-card' : ''}`}
      onClick={() => onCardClick && onCardClick(place)}
    >
      {/* Image Banner / Genuine Photo or Clean No-Photo Placeholder */}
      <div className="place-card-image-wrapper">
        {photoUrl ? (
          <img
            src={photoUrl}
            alt={place.name}
            className="place-card-image"
            loading="lazy"
            onError={() => setImgError(true)}
          />
        ) : (
          <div className="no-photo-placeholder">
            <CameraOff size={24} className="no-photo-icon" />
            <span className="no-photo-text">No verified photo available</span>
          </div>
        )}

        <div className="place-card-badge-row">
          <span className={`place-category-badge cat-${place.category?.toLowerCase()}`}>
            {getCategoryIcon(place.category)}
            <span>{place.category?.toUpperCase()}</span>
          </span>

          {place.rating > 0 && (
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
          <span>{place.address || place.location}</span>
        </div>

        {place.description && (
          <p className="place-card-description">{place.description}</p>
        )}

        {/* Tags / Details */}
        {(place.tags?.length > 0 || place.price_level || place.cuisine) && (
          <div className="place-card-tags">
            {place.price_level && (
              <span className="place-tag price-tag">{place.price_level}</span>
            )}
            {place.cuisine && (
              <span className="place-tag">{place.cuisine}</span>
            )}
            {place.tags?.slice(0, 2).map((t, idx) => (
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
