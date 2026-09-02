import { useState, useEffect, useMemo, useCallback } from 'react';
import { Link } from 'react-router-dom';
import {
  Heart,
  Compass,
  ArrowUpRight,
  ArrowLeft,
  MapPin,
  Hotel,
  Utensils,
  Landmark,
  Layers,
  Trash2
} from 'lucide-react';
import { wishlistAPI, extractErrorMessage } from '../services/api';
import { useToast } from '../context/ToastContext';
import { PlaceCard } from '../components/PlaceCard';
import { AddToTripModal } from '../components/AddToTripModal';
import { Alert } from '../components/Alert';

const CATEGORIES = [
  { id: 'all', label: 'All Saved', icon: Layers },
  { id: 'destination', label: 'Destinations', icon: MapPin },
  { id: 'hotel', label: 'Hotels', icon: Hotel },
  { id: 'restaurant', label: 'Dining', icon: Utensils },
  { id: 'attraction', label: 'Attractions', icon: Landmark },
  { id: 'activity', label: 'Activities', icon: Compass },
];

export const Wishlist = () => {
  const { showSuccess, showError } = useToast();
  const [wishlistItems, setWishlistItems] = useState([]);
  const [activeCategory, setActiveCategory] = useState('all');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [modalPlace, setModalPlace] = useState(null);

  const fetchWishlist = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await wishlistAPI.getWishlist();
      setWishlistItems(Array.isArray(data) ? data : []);
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchWishlist();
  }, [fetchWishlist]);

  const handleRemove = async (item) => {
    try {
      await wishlistAPI.removeFromWishlist(item._id || item.id);
      setWishlistItems((prev) => prev.filter((i) => (i._id || i.id) !== (item._id || item.id)));
      showSuccess(`Removed "${item.name}" from your wishlist.`);
    } catch (err) {
      showError(extractErrorMessage(err));
    }
  };

  const filteredItems = useMemo(() => {
    if (activeCategory === 'all') return wishlistItems;
    return wishlistItems.filter((i) => i.category?.toLowerCase() === activeCategory.toLowerCase());
  }, [wishlistItems, activeCategory]);

  return (
    <div className="main-content">
      {/* Editorial Header */}
      <div className="dashboard-header">
        <div className="dashboard-title-group">
          <div className="editorial-mark">
            <i></i> 04 / WISHLIST
          </div>
          <h1>
            Curated inspirations, <br />
            <em>saved for future journeys.</em>
          </h1>
          <p className="welcome-subtitle">
            All your favorited destinations, boutique hotels, gourmet restaurants, and bucket-list attractions in one place.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '0.65rem' }}>
          <Link to="/explore" className="btn btn-primary">
            <Compass size={14} />
            <span>Discover More Places</span>
          </Link>
        </div>
      </div>

      {error && <Alert type="error" message={error} onClose={() => setError(null)} />}

      {/* Category Tabs */}
      <div className="explore-toolbar" style={{ marginBottom: '2rem' }}>
        <div className="explore-category-tabs">
          {CATEGORIES.map((cat) => {
            const Icon = cat.icon;
            const count = cat.id === 'all'
              ? wishlistItems.length
              : wishlistItems.filter((i) => i.category?.toLowerCase() === cat.id).length;

            return (
              <button
                key={cat.id}
                type="button"
                className={`explore-cat-tab ${activeCategory === cat.id ? 'active' : ''}`}
                onClick={() => setActiveCategory(cat.id)}
              >
                <Icon size={14} />
                <span>
                  {cat.label} ({count})
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Grid */}
      {loading ? (
        <div className="loading-container" style={{ padding: '5rem 1rem' }}>
          <div className="spinner spinner-lg" />
          <p style={{ marginTop: '1rem' }}>Loading your saved places...</p>
        </div>
      ) : wishlistItems.length === 0 ? (
        <div className="empty-state">
          <div className="empty-icon-wrapper">
            <Heart size={28} />
          </div>
          <h3 className="empty-title">Your wishlist is empty.</h3>
          <p className="empty-desc">
            Explore destinations worldwide, discover luxury stays and culinary hotspots, and click the heart icon to save them here.
          </p>
          <Link to="/explore" className="btn btn-primary">
            <span>Explore Destinations</span>
            <ArrowUpRight size={14} />
          </Link>
        </div>
      ) : filteredItems.length === 0 ? (
        <div className="empty-state">
          <div className="empty-icon-wrapper">
            <Compass size={24} />
          </div>
          <h3 className="empty-title">No saved items in this category</h3>
          <p className="empty-desc">
            You haven't saved any {activeCategory}s yet.
          </p>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => setActiveCategory('all')}
          >
            View All Saved ({wishlistItems.length})
          </button>
        </div>
      ) : (
        <div className="explore-places-grid">
          {filteredItems.map((item) => (
            <div key={item._id || item.id} className="wishlist-item-wrapper">
              <PlaceCard
                place={{
                  place_id: item.place_id,
                  name: item.name,
                  category: item.category,
                  location: item.location,
                  image_url: item.image_url,
                  rating: item.rating,
                  description: item.description,
                  lat: item.metadata?.lat,
                  lon: item.metadata?.lon,
                  address: item.metadata?.address,
                  price_level: item.metadata?.price_level,
                  tags: item.metadata?.tags,
                }}
                isWishlisted={true}
                onAddToTrip={(p) => setModalPlace(p)}
              />
              <button
                type="button"
                className="wishlist-remove-btn"
                onClick={() => handleRemove(item)}
                title="Remove from Wishlist"
              >
                <Trash2 size={13} />
                <span>Remove</span>
              </button>
            </div>
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
