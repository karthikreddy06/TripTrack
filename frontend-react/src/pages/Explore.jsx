import { useState, useEffect, useCallback, useRef } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import {
  Search,
  Compass,
  MapPin,
  Map,
  Grid,
  ArrowUpRight,
  Hotel,
  Utensils,
  Landmark,
  Layers,
  RotateCcw,
  Coffee,
  Trees,
  Scroll,
  ChevronDown
} from 'lucide-react';
import { exploreAPI, extractErrorMessage } from '../services/api';
import { PlaceCard } from '../components/PlaceCard';
import { MapView } from '../components/MapView';
import { AddToTripModal } from '../components/AddToTripModal';
import { SafeImage } from '../components/SafeImage';
import { Alert } from '../components/Alert';

const CATEGORIES = [
  { id: 'all', label: 'All Places', icon: Layers },
  { id: 'attractions', label: 'Attractions', icon: Landmark },
  { id: 'hotels', label: 'Hotels & Stays', icon: Hotel },
  { id: 'restaurants', label: 'Restaurants', icon: Utensils },
  { id: 'cafes', label: 'Cafes', icon: Coffee },
  { id: 'museums', label: 'Museums', icon: Landmark },
  { id: 'parks', label: 'Parks & Nature', icon: Trees },
  { id: 'historic', label: 'Historic', icon: Scroll },
  { id: 'activities', label: 'Activities', icon: Compass },
];

const FEATURED_SHORTCUTS = [
  { name: 'Hyderabad', label: 'Hyderabad, India', img: 'https://upload.wikimedia.org/wikipedia/commons/thumb/7/71/Charminar_Hyderabad_1.jpg/400px-Charminar_Hyderabad_1.jpg' },
  { name: 'Goa', label: 'Goa, India', img: 'https://upload.wikimedia.org/wikipedia/commons/thumb/7/7b/Baga_Beach_North_Goa.jpg/400px-Baga_Beach_North_Goa.jpg' },
  { name: 'Bengaluru', label: 'Bengaluru, India', img: 'https://upload.wikimedia.org/wikipedia/commons/thumb/8/8f/Lalbagh_Glass_house_Bangalore.jpg/400px-Lalbagh_Glass_house_Bangalore.jpg' },
  { name: 'Delhi', label: 'Delhi, India', img: 'https://upload.wikimedia.org/wikipedia/commons/thumb/0/09/India_Gate_in_New_Delhi_03-2016.jpg/400px-India_Gate_in_New_Delhi_03-2016.jpg' },
  { name: 'Mumbai', label: 'Mumbai, India', img: 'https://upload.wikimedia.org/wikipedia/commons/thumb/d/df/Gateway_of_India_Mumbai_India.jpg/400px-Gateway_of_India_Mumbai_India.jpg' },
  { name: 'Paris', label: 'Paris, France', img: 'https://upload.wikimedia.org/wikipedia/commons/thumb/a/a8/Tour_Eiffel_Wikimedia_Commons.jpg/400px-Tour_Eiffel_Wikimedia_Commons.jpg' },
];

export const Explore = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const initialQuery = searchParams.get('q') || 'Hyderabad';
  const initialCategory = searchParams.get('category') || 'all';

  const [searchQuery, setSearchQuery] = useState(initialQuery);
  const [activeCategory, setActiveCategory] = useState(initialCategory);
  const [searchResults, setSearchResults] = useState([]);
  const [destinationInfo, setDestinationInfo] = useState(null);

  const [currentPage, setCurrentPage] = useState(1);
  const [hasMore, setHasMore] = useState(false);
  const [totalCount, setTotalCount] = useState(0);

  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState(null);
  const [showMap, setShowMap] = useState(false);
  const [selectedPlaceId, setSelectedPlaceId] = useState(null);

  const [modalPlace, setModalPlace] = useState(null);
  const debounceTimerRef = useRef(null);

  const performSearch = useCallback(async (q, cat, page = 1, append = false) => {
    if (!q.trim()) return;
    try {
      if (append) {
        setLoadingMore(true);
      } else {
        setLoading(true);
        setError(null);
      }

      const data = await exploreAPI.search(q.trim(), cat, page, 24);
      const incoming = data.places || data.results || [];

      if (append) {
        setSearchResults((prev) => {
          const existingIds = new Set(prev.map((p) => p.id || p.place_id || p.provider_id));
          const newItems = incoming.filter((p) => !existingIds.has(p.id || p.place_id || p.provider_id));
          return [...prev, ...newItems];
        });
      } else {
        setSearchResults(incoming);
        setDestinationInfo(data.destination_info || null);
        if (incoming.length > 0) {
          const first = incoming[0];
          setSelectedPlaceId(first.id || first.place_id || first.provider_id);
        }
      }

      setCurrentPage(data.page || page);
      setHasMore(Boolean(data.has_more));
      setTotalCount(data.total_results || incoming.length);
    } catch (err) {
      if (!append) {
        setError(extractErrorMessage(err));
        setSearchResults([]);
      }
    } finally {
      setLoading(false);
      setLoadingMore(false);
    }
  }, []);

  useEffect(() => {
    performSearch(initialQuery, initialCategory, 1, false);
  }, [initialQuery, initialCategory, performSearch]);

  useEffect(() => {
    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, []);

  const handleInputChange = (e) => {
    const val = e.target.value;
    setSearchQuery(val);
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }
    if (val.trim().length >= 2) {
      debounceTimerRef.current = setTimeout(() => {
        setSearchParams({ q: val.trim(), category: activeCategory });
        performSearch(val.trim(), activeCategory, 1, false);
      }, 500);
    }
  };

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }
    if (!searchQuery.trim()) return;
    setSearchParams({ q: searchQuery.trim(), category: activeCategory });
    performSearch(searchQuery.trim(), activeCategory, 1, false);
  };

  const handleCategoryChange = (catId) => {
    setActiveCategory(catId);
    setSearchParams({ q: searchQuery.trim(), category: catId });
    performSearch(searchQuery.trim(), catId, 1, false);
  };

  const handleShortcutClick = (destName) => {
    setSearchQuery(destName);
    setSearchParams({ q: destName, category: 'all' });
    setActiveCategory('all');
    performSearch(destName, 'all', 1, false);
  };

  const handleLoadMore = () => {
    if (loadingMore || !hasMore) return;
    performSearch(searchQuery, activeCategory, currentPage + 1, true);
  };

  const handleSelectMapPlace = (place) => {
    const pId = place.id || place.place_id || place.provider_id;
    setSelectedPlaceId(pId);
    const el = document.getElementById(`place-card-${pId}`);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
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
          Search destinations, heritage sights, local dining, cafes, and verified stays powered by OpenStreetMap &amp; Wikimedia.
        </p>

        {/* Search Bar */}
        <form onSubmit={handleSearchSubmit} className="explore-search-bar">
          <Search size={18} className="search-bar-icon" />
          <input
            type="text"
            className="explore-search-input"
            placeholder="Search any destination worldwide... (e.g. Hyderabad, Goa, Paris, Bengaluru, Mumbai, London)"
            value={searchQuery}
            onChange={handleInputChange}
          />
          <button type="submit" className="btn btn-primary explore-search-btn">
            <span>Explore</span>
            <ArrowUpRight size={14} />
          </button>
        </form>

        {/* Featured Destination Shortcuts */}
        <div className="featured-shortcuts-row">
          <span className="shortcuts-label">POPULAR DESTINATIONS:</span>
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
          <span>{showMap ? 'Hide Map' : 'Interactive Map'}</span>
        </button>
      </div>

      {error && <Alert type="error" message={error} onClose={() => setError(null)} />}

      {/* Destination Overview Box */}
      {destinationInfo && (
        <div className="card destination-overview-banner" style={{ marginBottom: '2rem' }}>
          <div className="dest-banner-grid">
            <div style={{ maxWidth: '320px', width: '100%', height: '200px', borderRadius: 'var(--radius-md)', overflow: 'hidden' }}>
              <SafeImage
                src={destinationInfo.image_url}
                alt={destinationInfo.destination}
                isVerified={Boolean(destinationInfo.image_url)}
                placeholderText="DESTINATION GUIDE"
                icon={Compass}
                style={{ height: '100%' }}
              />
            </div>

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
                  <span>Explore Guide</span>
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
                <div className="meta-pill">
                  <span>Source: OpenStreetMap &amp; Wikimedia</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Interactive Map View Section */}
      {showMap && (
        <div className="explore-map-container" style={{ marginBottom: '2.5rem' }}>
          <MapView
            places={searchResults}
            center={destinationInfo ? [destinationInfo.lat, destinationInfo.lon] : [17.3850, 78.4867]}
            zoom={12}
            height="460px"
            selectedPlaceId={selectedPlaceId}
            onSelectPlace={handleSelectMapPlace}
          />
        </div>
      )}

      {/* Main Results Grid */}
      <div className="explore-results-section">
        <div className="results-header-row" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.25rem' }}>
          <h3 className="section-title" style={{ margin: 0 }}>
            {activeCategory === 'all'
              ? `Places & Highlights in ${searchQuery}`
              : `${CATEGORIES.find((c) => c.id === activeCategory)?.label || 'Places'} in ${searchQuery}`}
          </h3>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
            Showing {searchResults.length} of {totalCount} verified places
          </span>
        </div>

        {loading ? (
          <div className="loading-state card" style={{ padding: '3.5rem 1.5rem', textAlign: 'center' }}>
            <div className="spinner" style={{ margin: '0 auto 1rem' }} />
            <p style={{ color: 'var(--text-secondary)' }}>Discovering real places with OpenStreetMap...</p>
          </div>
        ) : searchResults.length === 0 ? (
          <div className="empty-state card" style={{ padding: '3.5rem 1.5rem', textAlign: 'center' }}>
            <Compass size={36} style={{ color: 'var(--accent)', margin: '0 auto 1rem' }} />
            <h3>No Places Found in {searchQuery}</h3>
            <p style={{ color: 'var(--text-secondary)', margin: '0.5rem 0 1.5rem' }}>
              We could not find places matching the selected category. Try searching for a different city or category.
            </p>
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={() => handleCategoryChange('all')}
            >
              <RotateCcw size={13} />
              <span>Show All Places</span>
            </button>
          </div>
        ) : (
          <>
            <div className="places-grid">
              {searchResults.map((place) => {
                const pId = place.id || place.place_id || place.provider_id;
                return (
                  <PlaceCard
                    key={pId}
                    place={place}
                    isActive={selectedPlaceId === pId}
                    onCardClick={() => setSelectedPlaceId(pId)}
                    onAddToTrip={(p) => setModalPlace(p)}
                  />
                );
              })}
            </div>

            {/* Load More Button for Pagination */}
            {hasMore && (
              <div style={{ display: 'flex', justifyContent: 'center', marginTop: '2.5rem', marginBottom: '1.5rem' }}>
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={handleLoadMore}
                  disabled={loadingMore}
                  style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem', padding: '0.65rem 1.75rem' }}
                >
                  {loadingMore ? (
                    <>
                      <div className="spinner-sm" />
                      <span>Loading More Places...</span>
                    </>
                  ) : (
                    <>
                      <ChevronDown size={14} />
                      <span>Load More Places</span>
                    </>
                  )}
                </button>
              </div>
            )}
          </>
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
