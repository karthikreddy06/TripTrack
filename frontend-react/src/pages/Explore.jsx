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
  { name: 'Hyderabad', label: 'Hyderabad, India', img: 'https://upload.wikimedia.org/wikipedia/commons/thumb/7/71/Charminar_Hyderabad_1.jpg/400px-Charminar_Hyderabad_1.jpg' },
  { name: 'Goa', label: 'Goa, India', img: 'https://upload.wikimedia.org/wikipedia/commons/thumb/7/7b/Baga_Beach_North_Goa.jpg/400px-Baga_Beach_North_Goa.jpg' },
  { name: 'Bengaluru', label: 'Bengaluru, India', img: 'https://upload.wikimedia.org/wikipedia/commons/thumb/8/8f/Lalbagh_Glass_house_Bangalore.jpg/400px-Lalbagh_Glass_house_Bangalore.jpg' },
  { name: 'Delhi', label: 'Delhi, India', img: 'https://upload.wikimedia.org/wikipedia/commons/thumb/0/09/India_Gate_in_New_Delhi_03-2016.jpg/400px-India_Gate_in_New_Delhi_03-2016.jpg' },
  { name: 'Mumbai', label: 'Mumbai, India', img: 'https://upload.wikimedia.org/wikipedia/commons/thumb/3/3a/Mumbai_03-2016_30_Gateway_of_India.jpg/400px-Mumbai_03-2016_30_Gateway_of_India.jpg' },
  { name: 'Paris', label: 'Paris, France', img: 'https://upload.wikimedia.org/wikipedia/commons/thumb/8/85/Tour_Eiffel_Wikimedia_Commons_%28cropped%29.jpg/400px-Tour_Eiffel_Wikimedia_Commons_%28cropped%29.jpg' },
  { name: 'Dubai', label: 'Dubai, UAE', img: 'https://upload.wikimedia.org/wikipedia/commons/thumb/9/93/Burj_Khalifa.jpg/400px-Burj_Khalifa.jpg' },
  { name: 'Tokyo', label: 'Tokyo, Japan', img: 'https://upload.wikimedia.org/wikipedia/commons/thumb/c/ca/Senso-ji_Main_Hall_Tokyo.jpg/400px-Senso-ji_Main_Hall_Tokyo.jpg' },
];

export const Explore = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const initialQuery = searchParams.get('q') || 'Hyderabad';
  const initialCategory = searchParams.get('category') || 'all';

  const [searchQuery, setSearchQuery] = useState(initialQuery);
  const [activeCategory, setActiveCategory] = useState(initialCategory);
  const [searchResults, setSearchResults] = useState([]);
  const [destinationInfo, setDestinationInfo] = useState(null);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showMap, setShowMap] = useState(false);
  const [selectedPlaceId, setSelectedPlaceId] = useState(null);

  const [modalPlace, setModalPlace] = useState(null);
  const debounceTimerRef = useRef(null);

  const performSearch = useCallback(async (q, cat) => {
    if (!q.trim()) return;
    try {
      setLoading(true);
      setError(null);
      const data = await exploreAPI.search(q.trim(), cat);
      setSearchResults(data.results || []);
      setDestinationInfo(data.destination_info || null);
      if (data.results && data.results.length > 0) {
        setSelectedPlaceId(data.results[0].place_id);
      }
    } catch (err) {
      setError(extractErrorMessage(err));
      setSearchResults([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    performSearch(initialQuery, initialCategory);
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
        performSearch(val.trim(), activeCategory);
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

  const handleSelectMapPlace = (place) => {
    setSelectedPlaceId(place.place_id);
    const el = document.getElementById(`place-card-${place.place_id}`);
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
          Search destinations, luxury hotels, authentic local dining, and verified attractions with Google Places.
        </p>

        {/* Search Bar */}
        <form onSubmit={handleSearchSubmit} className="explore-search-bar">
          <Search size={18} className="search-bar-icon" />
          <input
            type="text"
            className="explore-search-input"
            placeholder="Search destinations, hotels, restaurants, attractions... (e.g. Hyderabad, Goa, Paris, Delhi)"
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
          <span>{showMap ? 'Hide Map' : 'View on Google Map'}</span>
        </button>
      </div>

      {error && <Alert type="error" message={error} onClose={() => setError(null)} />}

      {/* Destination Overview Box */}
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

      {/* Interactive Google Map View Section */}
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
                ? { lat: destinationInfo.lat, lng: destinationInfo.lon }
                : searchResults[0]?.lat
                ? { lat: searchResults[0].lat, lng: searchResults[0].lon }
                : { lat: 17.3850, lng: 78.4867 }
            }
            height="460px"
            selectedPlaceId={selectedPlaceId}
            onSelectPlace={handleSelectMapPlace}
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
              onClick={() => handleShortcutClick('Hyderabad')}
            >
              <RotateCcw size={13} />
              <span>Explore Hyderabad</span>
            </button>
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => handleShortcutClick('Goa')}
            >
              <span>Explore Goa</span>
            </button>
          </div>
        </div>
      ) : (
        <div className="explore-places-grid">
          {searchResults.map((place) => (
            <div key={place.place_id} id={`place-card-${place.place_id}`}>
              <PlaceCard
                place={place}
                isActive={selectedPlaceId === place.place_id}
                onCardClick={(p) => setSelectedPlaceId(p.place_id)}
                onAddToTrip={(p) => setModalPlace(p)}
              />
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
