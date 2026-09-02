import { useState, useEffect, useCallback } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import {
  Search,
  Compass,
  MapPin,
  Map,
  Grid,
  Sparkles,
  ArrowUpRight,
  Hotel,
  Utensils,
  Landmark,
  Layers,
  RotateCcw
} from 'lucide-react';
import { exploreAPI, extractErrorMessage } from '../services/api';
import { PlaceCard } from '../components/PlaceCard';
import { MapView } from '../components/MapView';
import { AddToTripModal } from '../components/AddToTripModal';
import { Alert } from '../components/Alert';

const CATEGORIES = [
  { id: 'all', label: 'All Places', icon: Layers },
  { id: 'destinations', label: 'Destinations', icon: MapPin },
  { id: 'hotels', label: 'Hotels & Stays', icon: Hotel },
  { id: 'restaurants', label: 'Dining & Cafes', icon: Utensils },
  { id: 'attractions', label: 'Attractions', icon: Landmark },
  { id: 'activities', label: 'Activities', icon: Compass },
];

const FEATURED_SHORTCUTS = [
  { name: 'Goa', label: 'Goa, India', img: 'https://images.unsplash.com/photo-1512343879784-a960bf40e7f2?auto=format&fit=crop&w=400&q=80' },
  { name: 'Hyderabad', label: 'Hyderabad, India', img: 'https://images.unsplash.com/photo-1605649487212-47bdab064df7?auto=format&fit=crop&w=400&q=80' },
  { name: 'Dubai', label: 'Dubai, UAE', img: 'https://images.unsplash.com/photo-1512453979798-5ea266f8880c?auto=format&fit=crop&w=400&q=80' },
  { name: 'Paris', label: 'Paris, France', img: 'https://images.unsplash.com/photo-1502602898657-3e91760cbb34?auto=format&fit=crop&w=400&q=80' },
];

export const Explore = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const initialQuery = searchParams.get('q') || 'Goa';
  const initialCategory = searchParams.get('category') || 'all';

  const [searchQuery, setSearchQuery] = useState(initialQuery);
  const [activeCategory, setActiveCategory] = useState(initialCategory);
  const [searchResults, setSearchResults] = useState([]);
  const [destinationInfo, setDestinationInfo] = useState(null);
  const [featuredDestinations, setFeaturedDestinations] = useState([]);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showMap, setShowMap] = useState(false);

  // Add to trip modal state
  const [modalPlace, setModalPlace] = useState(null);

  const performSearch = useCallback(async (q, cat) => {
    if (!q.trim()) return;
    try {
      setLoading(true);
      setError(null);
      const data = await exploreAPI.search(q.trim(), cat);
      setSearchResults(data.results || []);
      setDestinationInfo(data.destination_info || null);
    } catch (err) {
      setError(extractErrorMessage(err));
      setSearchResults([]);
    } finally {
      setLoading(false);
    }
  }, []);

  // Fetch initial featured list and perform search
  useEffect(() => {
    const loadFeatured = async () => {
      try {
        const feat = await exploreAPI.getFeatured();
        setFeaturedDestinations(Array.isArray(feat) ? feat : []);
      } catch {
        // Non-critical
      }
    };
    loadFeatured();
    performSearch(initialQuery, initialCategory);
  }, [initialQuery, initialCategory, performSearch]);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;
    setSearchParams({ q: searchQuery.trim(), category: activeCategory });
    performSearch(searchQuery.trim(), activeCategory);
  };

  const handleCategoryChange = (catId) => {
    setActiveCategory(catId);
    setSearchParams({ q: searchQuery.trim(), category: catId });
    performSearch(searchQuery.trim(), catId);
  };

  const handleShortcutClick = (destName) => {
    setSearchQuery(destName);
    setSearchParams({ q: destName, category: 'all' });
    setActiveCategory('all');
    performSearch(destName, 'all');
  };

  return (
    <div className="main-content explore-page-container">
      {/* Editorial Header & Hero Search */}
      <div className="explore-hero-card card">
        <div className="editorial-mark">
          <i></i> 01 / DESTINATION DISCOVERY
        </div>
        <h1 className="explore-hero-title">
          Where do you <br />
          <em>want to wander?</em>
        </h1>
        <p className="explore-hero-subtitle">
          Search destinations, luxury hotels, authentic local dining, and iconic attractions worldwide.
        </p>

        {/* Search Bar */}
        <form onSubmit={handleSearchSubmit} className="explore-search-bar">
          <Search size={18} className="search-bar-icon" />
          <input
            type="text"
            className="explore-search-input"
            placeholder="Search destinations, hotels, restaurants, attractions... (e.g. Goa, Paris, Dubai)"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
          <button type="submit" className="btn btn-primary explore-search-btn">
            <span>Explore</span>
            <ArrowUpRight size={14} />
          </button>
        </form>

        {/* Featured Destination Shortcuts */}
        <div className="featured-shortcuts-row">
          <span className="shortcuts-label">TRENDING DESTINATIONS:</span>
          {FEATURED_SHORTCUTS.map((sc) => (
            <button
              key={sc.name}
              type="button"
              className={`shortcut-pill ${searchQuery.toLowerCase() === sc.name.toLowerCase() ? 'active' : ''}`}
              onClick={() => handleShortcutClick(sc.name)}
            >
              <img src={sc.img} alt={sc.name} className="shortcut-thumb" />
              <span>{sc.name}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Category Tabs & View Controls */}
      <div className="explore-toolbar">
        <div className="explore-category-tabs">
          {CATEGORIES.map((cat) => {
            const Icon = cat.icon;
            const isActive = activeCategory === cat.id;
            return (
              <button
                key={cat.id}
                type="button"
                className={`explore-cat-tab ${isActive ? 'active' : ''}`}
                onClick={() => handleCategoryChange(cat.id)}
              >
                <Icon size={14} />
                <span>{cat.label}</span>
              </button>
            );
          })}
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

      {error && <Alert type="error" message={error} onClose={() => setError(null)} />}

      {/* Destination Overview Box (When searching a destination) */}
      {destinationInfo && (
        <div className="card destination-overview-banner" style={{ marginBottom: '2rem' }}>
          <div className="dest-banner-grid">
            {destinationInfo.image_url && (
              <img
                src={destinationInfo.image_url}
                alt={destinationInfo.destination}
                className="dest-banner-image"
                loading="lazy"
              />
            )}
            <div className="dest-banner-content">
              <div className="editorial-mark">
                <i></i> DESTINATION OVERVIEW
              </div>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.75rem' }}>
                <h2 style={{ fontSize: '1.9rem', margin: 0 }}>{destinationInfo.destination}</h2>
                <Link
                  to={`/explore/${encodeURIComponent(destinationInfo.destination.toLowerCase())}`}
                  className="btn btn-secondary btn-sm"
                >
                  <span>Explore Destination Guide</span>
                  <ArrowUpRight size={13} />
                </Link>
              </div>

              {destinationInfo.country && (
                <p className="dest-banner-location">
                  <MapPin size={13} />
                  <span>{destinationInfo.country}</span>
                </p>
              )}

              <p className="dest-banner-desc">{destinationInfo.description}</p>

              <div className="dest-meta-row">
                {destinationInfo.best_time_to_visit && (
                  <div className="meta-pill">
                    <span>Best Time: {destinationInfo.best_time_to_visit}</span>
                  </div>
                )}
                {destinationInfo.currency && (
                  <div className="meta-pill">
                    <span>Currency: {destinationInfo.currency}</span>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Map Section (Collapsible) */}
      {showMap && (
        <div className="explore-map-section" style={{ marginBottom: '2.5rem' }}>
          <div className="section-header" style={{ marginBottom: '1rem' }}>
            <h3 style={{ fontSize: '1.25rem', margin: 0 }}>
              Mapped Places in {searchQuery}
            </h3>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
              Showing {searchResults.filter((p) => p.lat && p.lon).length} mapped locations
            </span>
          </div>
          <MapView
            places={searchResults}
            center={
              destinationInfo?.lat && destinationInfo?.lon
                ? [destinationInfo.lat, destinationInfo.lon]
                : searchResults[0]?.lat
                ? [searchResults[0].lat, searchResults[0].lon]
                : [15.2993, 74.1240]
            }
            height="440px"
          />
        </div>
      )}

      {/* Results Header */}
      <div className="section-header">
        <div>
          <h2 className="section-title">
            {activeCategory === 'all'
              ? `Discovered in "${searchQuery}"`
              : `${CATEGORIES.find((c) => c.id === activeCategory)?.label} in "${searchQuery}"`}
          </h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
            Found {searchResults.length} {searchResults.length === 1 ? 'place' : 'places'} ready to explore and add to your itinerary.
          </p>
        </div>
      </div>

      {/* Results Grid */}
      {loading ? (
        <div className="loading-container" style={{ padding: '4rem 1rem' }}>
          <div className="spinner spinner-lg" />
          <p style={{ marginTop: '1rem' }}>Searching places, hotels, and attractions for {searchQuery}...</p>
        </div>
      ) : searchResults.length === 0 ? (
        <div className="empty-state">
          <div className="empty-icon-wrapper">
            <Compass size={28} />
          </div>
          <h3 className="empty-title">No places found for "{searchQuery}".</h3>
          <p className="empty-desc">
            We couldn't find matching places under the selected category. Try searching for a major city, coastal region, or landmark.
          </p>
          <div style={{ display: 'flex', gap: '0.65rem', justifyContent: 'center' }}>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => handleShortcutClick('Goa')}
            >
              <RotateCcw size={13} />
              <span>Explore Goa</span>
            </button>
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => handleShortcutClick('Dubai')}
            >
              <span>Explore Dubai</span>
            </button>
          </div>
        </div>
      ) : (
        <div className="explore-places-grid">
          {searchResults.map((place) => (
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
