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
  ChevronDown,
  Sparkles,
  Calendar,
  DollarSign,
  Building2,
  Navigation
} from 'lucide-react';
import { exploreAPI, extractErrorMessage } from '../services/api';
import { PlaceCard } from '../components/PlaceCard';
import { MapView } from '../components/MapView';
import { AddToTripModal } from '../components/AddToTripModal';
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
  { name: 'Hyderabad', label: 'Hyderabad, India', code: 'HYD' },
  { name: 'Kolkata', label: 'Kolkata, India', code: 'CCU' },
  { name: 'Bengaluru', label: 'Bengaluru, India', code: 'BLR' },
  { name: 'Goa', label: 'Goa, India', code: 'GOA' },
  { name: 'Delhi', label: 'Delhi, India', code: 'DEL' },
  { name: 'Mumbai', label: 'Mumbai, India', code: 'BOM' },
  { name: 'Paris', label: 'Paris, France', code: 'PAR' },
  { name: 'Tokyo', label: 'Tokyo, Japan', code: 'TYO' },
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

  // Autocomplete Suggestions State
  const [suggestions, setSuggestions] = useState([]);
  const [suggestionsLoading, setSuggestionsLoading] = useState(false);
  const [showDropdown, setShowDropdown] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(-1);

  const [modalPlace, setModalPlace] = useState(null);
  const debounceTimerRef = useRef(null);
  const searchWrapperRef = useRef(null);

  const performSearch = useCallback(async (q, cat, page = 1, append = false, lat = null, lon = null) => {
    if (!q.trim()) return;
    try {
      if (append) {
        setLoadingMore(true);
      } else {
        setLoading(true);
        setError(null);
        // Clear stale destination and places when switching to a new search query
        if (page === 1) {
          setSearchResults([]);
          setDestinationInfo(null);
        }
      }

      const data = await exploreAPI.search(q.trim(), cat, page, 24, lat, lon);
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
        setDestinationInfo(null);
      }
    } finally {
      setLoading(false);
      setLoadingMore(false);
    }
  }, []);

  // Fetch initial search query on mount or URL change
  useEffect(() => {
    performSearch(initialQuery, initialCategory, 1, false);
  }, [initialQuery, initialCategory, performSearch]);

  // Click outside to close autocomplete dropdown
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (searchWrapperRef.current && !searchWrapperRef.current.contains(e.target)) {
        setShowDropdown(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, []);

  // Fetch dynamic suggestions on input change with 250ms debounce
  const handleInputChange = (e) => {
    const val = e.target.value;
    setSearchQuery(val);
    setSelectedIndex(-1);

    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }

    if (val.trim().length >= 2) {
      setSuggestionsLoading(true);
      setShowDropdown(true);

      debounceTimerRef.current = setTimeout(async () => {
        try {
          const sugs = await exploreAPI.getSuggestions(val.trim(), 6);
          setSuggestions(sugs || []);
        } catch {
          setSuggestions([]);
        } finally {
          setSuggestionsLoading(false);
        }
      }, 250);
    } else {
      setSuggestions([]);
      setShowDropdown(false);
      setSuggestionsLoading(false);
    }
  };

  // Keyboard navigation within suggestions dropdown
  const handleKeyDown = (e) => {
    if (!showDropdown || suggestions.length === 0) return;

    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex((prev) => (prev < suggestions.length - 1 ? prev + 1 : 0));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex((prev) => (prev > 0 ? prev - 1 : suggestions.length - 1));
    } else if (e.key === 'Enter') {
      if (selectedIndex >= 0 && selectedIndex < suggestions.length) {
        e.preventDefault();
        handleSelectSuggestion(suggestions[selectedIndex]);
      }
    } else if (e.key === 'Escape') {
      setShowDropdown(false);
    }
  };

  // Handle suggestion click / selection
  const handleSelectSuggestion = (sug) => {
    if (!sug) return;
    const targetName = sug.name;
    setSearchQuery(targetName);
    setShowDropdown(false);
    setSuggestions([]);
    setSearchParams({ q: targetName, category: activeCategory });
    performSearch(targetName, activeCategory, 1, false, sug.lat, sug.lon);
  };

  // Submit search form
  const handleSearchSubmit = (e) => {
    e.preventDefault();
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }
    setShowDropdown(false);
    if (!searchQuery.trim()) return;

    // If an item is selected by keyboard, use it
    if (selectedIndex >= 0 && selectedIndex < suggestions.length) {
      handleSelectSuggestion(suggestions[selectedIndex]);
      return;
    }

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
    setShowDropdown(false);
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
          Search authentic attractions, historic sights, local dining, cafes, and verified stays worldwide powered dynamically by OpenStreetMap &amp; Overpass.
        </p>

        {/* Autocomplete Search Bar */}
        <div className="explore-search-wrapper" ref={searchWrapperRef}>
          <form onSubmit={handleSearchSubmit} className="explore-search-bar">
            <Search size={18} className="search-bar-icon" />
            <input
              type="text"
              className="explore-search-input"
              placeholder="Search any destination worldwide... (e.g. Kolkata, Hyderabad, Paris, Tokyo, Eiffel Tower)"
              value={searchQuery}
              onChange={handleInputChange}
              onKeyDown={handleKeyDown}
              onFocus={() => {
                if (suggestions.length > 0) setShowDropdown(true);
              }}
              autoComplete="off"
            />
            {suggestionsLoading && (
              <div className="spinner-sm" style={{ marginRight: '0.5rem', width: '14px', height: '14px' }} />
            )}
            <button type="submit" className="btn btn-primary explore-search-btn">
              <span>Explore</span>
              <ArrowUpRight size={14} />
            </button>
          </form>

          {/* Autocomplete Suggestions Dropdown */}
          {showDropdown && suggestions.length > 0 && (
            <div className="explore-suggestions-dropdown" role="listbox">
              {suggestions.map((sug, idx) => {
                const isSelected = idx === selectedIndex;
                const isDest = sug.is_destination;
                const IconComponent = isDest ? Building2 : (sug.category === 'hotel' ? Hotel : (sug.category === 'restaurant' || sug.category === 'cafe' ? Utensils : Landmark));

                return (
                  <div
                    key={`${sug.id || sug.name}-${idx}`}
                    className={`explore-suggestion-item ${isSelected ? 'active' : ''}`}
                    onClick={() => handleSelectSuggestion(sug)}
                    onMouseEnter={() => setSelectedIndex(idx)}
                    role="option"
                    aria-selected={isSelected}
                  >
                    <div className="explore-suggestion-left">
                      <div className="explore-suggestion-icon">
                        <IconComponent size={16} />
                      </div>
                      <div style={{ minWidth: 0 }}>
                        <div className="explore-suggestion-name">{sug.name}</div>
                        {sug.subtitle && (
                          <div className="explore-suggestion-sub">{sug.subtitle}</div>
                        )}
                      </div>
                    </div>
                    <span className="explore-suggestion-badge">
                      {isDest ? 'Destination' : (sug.category || 'Place')}
                    </span>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Clean Editorial Destination Shortcut Chips */}
        <div className="featured-shortcuts-row">
          <span className="shortcuts-label">
            POPULAR DESTINATIONS:
          </span>
          {FEATURED_SHORTCUTS.map((sc) => {
            const isSelected = searchQuery.toLowerCase() === sc.name.toLowerCase();
            return (
              <button
                key={sc.name}
                type="button"
                className={`shortcut-pill ${isSelected ? 'active' : ''}`}
                onClick={() => handleShortcutClick(sc.name)}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '0.4rem',
                  padding: '0.35rem 0.75rem',
                  borderRadius: '20px',
                  background: isSelected ? 'var(--primary-green, #2f523b)' : 'var(--surface-cream, #f5f4ef)',
                  color: isSelected ? '#FFFFFF' : 'var(--text-primary, #1a2e22)',
                  border: isSelected ? '1px solid var(--primary-green)' : '1px solid var(--border-light, #e5e3db)',
                  cursor: 'pointer',
                  fontSize: '0.8rem',
                  fontWeight: 500,
                  transition: 'all 0.15s ease',
                }}
              >
                <span
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    width: '18px',
                    height: '18px',
                    borderRadius: '50%',
                    background: isSelected ? 'rgba(255, 255, 255, 0.25)' : 'rgba(47, 82, 59, 0.1)',
                    color: isSelected ? '#FFFFFF' : 'var(--primary-green, #2f523b)',
                    fontSize: '0.62rem',
                    fontFamily: 'var(--font-mono)',
                    fontWeight: 700,
                  }}
                >
                  {sc.code.slice(0, 1)}
                </span>
                <span>{sc.name}</span>
              </button>
            );
          })}
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

      {/* Destination Editorial Overview Banner */}
      {destinationInfo && (
        <div
          className="card destination-overview-banner"
          style={{
            marginBottom: '2rem',
            padding: 0,
            overflow: 'hidden',
            background: 'var(--surface-card, #FFFFFF)',
            border: '1px solid var(--border, #e5e3db)',
          }}
        >
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'minmax(240px, 300px) 1fr',
              gap: '0',
            }}
            className="dest-overview-grid"
          >
            {/* Left Decorative Botanical Graphic Block */}
            <div
              style={{
                position: 'relative',
                background: 'linear-gradient(135deg, #1b3627 0%, #294d38 55%, #3d6e50 100%)',
                color: '#FFFFFF',
                padding: '1.75rem 1.5rem',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
                minHeight: '190px',
                overflow: 'hidden',
              }}
            >
              <svg
                style={{
                  position: 'absolute',
                  top: 0,
                  left: 0,
                  width: '100%',
                  height: '100%',
                  opacity: 0.18,
                  pointerEvents: 'none',
                }}
                viewBox="0 0 200 160"
                preserveAspectRatio="none"
              >
                <path d="M-10,40 Q50,120 120,60 T220,90" fill="none" stroke="#FFFFFF" strokeWidth="1.2" strokeDasharray="4 4" />
                <path d="M-10,90 Q70,20 150,100 T220,40" fill="none" stroke="#FFFFFF" strokeWidth="0.8" />
                <circle cx="160" cy="40" r="24" fill="none" stroke="#FFFFFF" strokeWidth="0.8" strokeDasharray="3 3" />
                <circle cx="160" cy="40" r="5" fill="none" stroke="#FFFFFF" strokeWidth="1" />
              </svg>

              <div>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.68rem', letterSpacing: '0.1em', opacity: 0.75, textTransform: 'uppercase' }}>
                  DESTINATION DOSSIER
                </div>
                <h3 style={{ fontSize: '1.75rem', fontFamily: 'var(--font-serif)', margin: '0.25rem 0', color: '#FFFFFF' }}>
                  {destinationInfo.destination}
                </h3>
                {destinationInfo.country && (
                  <p style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.85rem', color: '#a0e8be', margin: 0 }}>
                    <MapPin size={13} />
                    <span>{destinationInfo.country}</span>
                  </p>
                )}
              </div>

              <div style={{ fontSize: '0.7rem', fontFamily: 'var(--font-mono)', color: 'rgba(255, 255, 255, 0.7)' }}>
                {destinationInfo.lat && destinationInfo.lon
                  ? `${Math.abs(destinationInfo.lat).toFixed(2)}°N · ${Math.abs(destinationInfo.lon).toFixed(2)}°E`
                  : 'OpenStreetMap Cartography'}
              </div>
            </div>

            {/* Right Editorial Info Content */}
            <div style={{ padding: '1.5rem 1.75rem', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.75rem', marginBottom: '0.5rem' }}>
                  <div className="editorial-mark" style={{ margin: 0 }}>
                    <i></i> VERIFIED TRAVEL GUIDE
                  </div>

                  <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                    <Link
                      to="/ai-planner"
                      state={{ prefill: { destination: destinationInfo.destination } }}
                      className="btn btn-primary btn-sm"
                      style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}
                    >
                      <Sparkles size={13} />
                      <span>Plan with AI</span>
                    </Link>
                    <Link
                      to={`/explore/${encodeURIComponent(destinationInfo.destination.toLowerCase())}`}
                      className="btn btn-secondary btn-sm"
                    >
                      <span>Explore Guide</span>
                      <ArrowUpRight size={13} />
                    </Link>
                  </div>
                </div>

                <p style={{ fontSize: '0.9rem', lineHeight: '1.55', color: 'var(--text-secondary)', margin: '0.5rem 0 1rem 0' }}>
                  {destinationInfo.description}
                </p>
              </div>

              {/* Metadata Pills */}
              <div style={{ display: 'flex', gap: '0.65rem', flexWrap: 'wrap', alignItems: 'center' }}>
                {destinationInfo.best_time_to_visit && (
                  <div
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '0.35rem',
                      background: 'var(--surface-cream, #f5f4ef)',
                      padding: '3px 9px',
                      borderRadius: '4px',
                      fontSize: '0.75rem',
                      color: 'var(--text-primary)',
                      fontFamily: 'var(--font-mono)',
                    }}
                  >
                    <Calendar size={11} style={{ color: 'var(--primary-green)' }} />
                    <span>Season: {destinationInfo.best_time_to_visit}</span>
                  </div>
                )}
                {destinationInfo.currency && (
                  <div
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '0.35rem',
                      background: 'var(--surface-cream, #f5f4ef)',
                      padding: '3px 9px',
                      borderRadius: '4px',
                      fontSize: '0.75rem',
                      color: 'var(--text-primary)',
                      fontFamily: 'var(--font-mono)',
                    }}
                  >
                    <DollarSign size={11} style={{ color: 'var(--primary-green)' }} />
                    <span>Currency: {destinationInfo.currency}</span>
                  </div>
                )}
                <div
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '0.35rem',
                    background: 'rgba(47, 82, 59, 0.08)',
                    padding: '3px 9px',
                    borderRadius: '4px',
                    fontSize: '0.75rem',
                    color: 'var(--primary-green)',
                    fontFamily: 'var(--font-mono)',
                  }}
                >
                  <Navigation size={11} />
                  <span>OSM Verified</span>
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
            center={
              destinationInfo?.lat && destinationInfo?.lon
                ? [destinationInfo.lat, destinationInfo.lon]
                : [17.3850, 78.4867]
            }
            zoom={12}
            height="440px"
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
            <p style={{ color: 'var(--text-secondary)' }}>Discovering real places with OpenStreetMap &amp; Overpass...</p>
          </div>
        ) : searchResults.length === 0 ? (
          <div className="empty-state card" style={{ padding: '3.5rem 1.5rem', textAlign: 'center' }}>
            <Compass size={36} style={{ color: 'var(--primary-green)', margin: '0 auto 1rem', opacity: 0.8 }} />
            <h3 style={{ fontFamily: 'var(--font-serif)', fontSize: '1.35rem', margin: '0 0 0.5rem 0' }}>
              No matching places found for &ldquo;{searchQuery}&rdquo;
            </h3>
            <p style={{ color: 'var(--text-secondary)', maxWidth: '480px', margin: '0 auto 1.5rem auto', fontSize: '0.9rem', lineHeight: '1.5' }}>
              We could not find places for this specific query or category. Try searching another city, town, landmark, or select from popular destinations above.
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
