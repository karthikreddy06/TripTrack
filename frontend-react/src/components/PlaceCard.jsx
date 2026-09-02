import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  MapPin,
  Star,
  Heart,
  Plus,
  ArrowUpRight,
  Sparkles,
  Navigation
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import { wishlistAPI } from '../services/api';
import { EditorialCardBanner } from './EditorialCardBanner';
import { formatDistance } from '../utils/geo';

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
          image_url: null,
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

  const displayDist = anchorDistanceKm ?? place.distance_km;

  return (
    <div
      id={`place-card-${placeId}`}
      className={`place-card card ${isActive ? 'active-map-card' : ''}`}
      onClick={() => onCardClick && onCardClick(place)}
      style={{
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        transition: 'transform 0.2s ease, box-shadow 0.2s ease',
        overflow: 'hidden',
        padding: 0,
      }}
    >
      <div>
        {/* Editorial Visual Header (Botanical / Topographic vector illustration) */}
        <EditorialCardBanner
          category={place.category}
          name={place.name}
          lat={place.lat}
          lon={place.lon}
          height="112px"
        >
          {/* Top Row Badges within Banner */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem' }}>
            {typeof place.rating === 'number' && place.rating > 0 ? (
              <span
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '3px',
                  background: 'rgba(0, 0, 0, 0.45)',
                  backdropFilter: 'blur(6px)',
                  padding: '2px 7px',
                  borderRadius: '12px',
                  fontSize: '0.72rem',
                  color: '#fbbf24',
                  fontWeight: 600,
                  fontFamily: 'var(--font-mono, monospace)',
                }}
              >
                <Star size={10} fill="currentColor" />
                <span>{place.rating.toFixed(1)}</span>
              </span>
            ) : (
              <span
                style={{
                  background: 'rgba(255, 255, 255, 0.15)',
                  backdropFilter: 'blur(6px)',
                  padding: '2px 7px',
                  borderRadius: '12px',
                  fontSize: '0.62rem',
                  letterSpacing: '0.05em',
                  fontFamily: 'var(--font-mono, monospace)',
                  color: 'rgba(255, 255, 255, 0.9)',
                }}
              >
                OSM VERIFIED
              </span>
            )}
          </div>

          {!showRemoveButton && (
            <button
              type="button"
              className={`place-wishlist-btn-header ${saved ? 'saved' : ''}`}
              onClick={handleToggleWishlist}
              disabled={saving}
              title={saved ? 'Remove from Wishlist' : 'Save to Wishlist'}
              aria-label="Wishlist"
              style={{
                background: saved ? 'var(--accent, #d97706)' : 'rgba(0, 0, 0, 0.35)',
                backdropFilter: 'blur(6px)',
                border: 'none',
                cursor: 'pointer',
                padding: '6px',
                borderRadius: '50%',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: saved ? '#FFFFFF' : 'rgba(255, 255, 255, 0.85)',
                transition: 'transform 0.15s ease, background 0.15s ease',
              }}
            >
              <Heart size={14} fill={saved ? '#FFFFFF' : 'none'} />
            </button>
          )}
        </EditorialCardBanner>

        {/* Card Body */}
        <div className="place-card-body" style={{ padding: '0.95rem 1.25rem 0.85rem 1.25rem' }}>
          <Link to={detailUrl} className="place-card-title-link">
            <h3
              className="place-card-title"
              style={{
                fontSize: '1.18rem',
                marginBottom: '0.3rem',
                fontFamily: 'var(--font-serif, Georgia, serif)',
                fontWeight: 600,
                lineHeight: 1.25,
              }}
            >
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
              color: 'var(--text-secondary, #6b7280)',
              marginBottom: '0.45rem',
            }}
          >
            <MapPin size={13} style={{ flexShrink: 0, color: 'var(--primary-green, #2f523b)' }} />
            <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {place.address || (typeof place.location === 'string' ? place.location : '')}
            </span>
          </div>

          {/* Distance Tag */}
          {displayDist !== null && displayDist !== undefined && (
            <div
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.3rem',
                fontFamily: 'var(--font-mono, monospace)',
                fontSize: '0.74rem',
                color: 'var(--primary-green, #2f523b)',
                background: 'rgba(47, 82, 59, 0.08)',
                padding: '2px 7px',
                borderRadius: '4px',
                marginBottom: '0.55rem',
                fontWeight: 600,
              }}
            >
              <Navigation size={10} />
              <span>{formatDistance(displayDist)} away</span>
            </div>
          )}

          {place.description && (
            <p
              className="place-card-description"
              style={{
                fontSize: '0.84rem',
                lineHeight: 1.45,
                color: 'var(--text-secondary, #4b5563)',
                marginBottom: '0.65rem',
                display: '-webkit-box',
                WebkitLineClamp: 2,
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
                <span
                  key={idx}
                  className="place-tag"
                  style={{
                    fontSize: '0.68rem',
                    padding: '2px 7px',
                    borderRadius: '4px',
                    background: 'var(--surface-cream, #f5f4ef)',
                    color: 'var(--text-secondary, #555)',
                    fontFamily: 'var(--font-mono, monospace)',
                  }}
                >
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
          padding: '0.75rem 1.25rem 1rem 1.25rem',
          borderTop: '1px solid var(--border-light, #eae8e1)',
          display: 'flex',
          gap: '0.45rem',
          alignItems: 'center',
          background: '#FFFFFF',
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
