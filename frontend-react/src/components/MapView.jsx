import { useEffect, useRef, useState } from 'react';
import { Loader } from '@googlemaps/js-api-loader';
import { MarkerClusterer } from '@googlemaps/markerclusterer';
import { AlertCircle, Compass } from 'lucide-react';

const TRAVELTRACK_MAP_STYLES = [
  { elementType: 'geometry', stylers: [{ color: '#f7f8f4' }] },
  { elementType: 'labels.text.stroke', stylers: [{ color: '#ffffff' }] },
  { elementType: 'labels.text.fill', stylers: [{ color: '#384639' }] },
  { featureType: 'administrative.locality', elementType: 'labels.text.fill', stylers: [{ color: '#1f2b20' }] },
  { featureType: 'poi', elementType: 'labels.text.fill', stylers: [{ color: '#4a5d4c' }] },
  { featureType: 'poi.park', elementType: 'geometry', stylers: [{ color: '#e6ede0' }] },
  { featureType: 'poi.park', elementType: 'labels.text.fill', stylers: [{ color: '#2d4730' }] },
  { featureType: 'road', elementType: 'geometry', stylers: [{ color: '#ffffff' }] },
  { featureType: 'road', elementType: 'geometry.stroke', stylers: [{ color: '#e2e7dc' }] },
  { featureType: 'road.highway', elementType: 'geometry', stylers: [{ color: '#ebece4' }] },
  { featureType: 'road.highway', elementType: 'geometry.stroke', stylers: [{ color: '#dadfd4' }] },
  { featureType: 'transit', elementType: 'geometry', stylers: [{ color: '#edf2e7' }] },
  { featureType: 'water', elementType: 'geometry', stylers: [{ color: '#d3e2db' }] },
  { featureType: 'water', elementType: 'labels.text.fill', stylers: [{ color: '#577970' }] }
];

const getCategoryColor = (category) => {
  switch (category?.toLowerCase()) {
    case 'hotel':
      return '#244B7A';
    case 'restaurant':
      return '#A03E1C';
    case 'activity':
      return '#61402B';
    case 'attraction':
    default:
      return '#2C3E2D';
  }
};

export const MapView = ({
  places = [],
  center = { lat: 17.3850, lng: 78.4867 },
  zoom = 12,
  height = '480px',
  selectedPlaceId = null,
  onSelectPlace = null,
}) => {
  const mapRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const markersRef = useRef([]);
  const clustererRef = useRef(null);
  const infoWindowRef = useRef(null);
  const isLoadedRef = useRef(false);

  const [mapError, setMapError] = useState(null);
  const [apiKeyMissing, setApiKeyMissing] = useState(false);

  const apiKey = (import.meta.env.VITE_GOOGLE_MAPS_API_KEY || '').trim();

  // Initialize Google Maps instance
  useEffect(() => {
    if (!apiKey) {
      setApiKeyMissing(true);
      return;
    }

    let isMounted = true;

    const initMap = async () => {
      try {
        const loader = new Loader({
          apiKey: apiKey,
          version: 'weekly',
          libraries: ['maps', 'marker']
        });

        const [mapsLib, markerLib] = await Promise.all([
          loader.importLibrary('maps'),
          loader.importLibrary('marker')
        ]);

        if (!isMounted || !mapRef.current) return;

        const defaultCenter = Array.isArray(center)
          ? { lat: center[0], lng: center[1] }
          : center;

        const map = new mapsLib.Map(mapRef.current, {
          center: defaultCenter,
          zoom: zoom,
          styles: TRAVELTRACK_MAP_STYLES,
          mapTypeControl: false,
          streetViewControl: false,
          fullscreenControl: true,
          zoomControl: true,
          mapId: 'TRAVELTRACK_BOTANICAL_MAP'
        });

        infoWindowRef.current = new mapsLib.InfoWindow();
        mapInstanceRef.current = map;
        isLoadedRef.current = true;
        setMapError(null);
      } catch (err) {
        if (isMounted) {
          setMapError(err.message || 'Failed to load Google Maps');
        }
      }
    };

    initMap();

    return () => {
      isMounted = false;
    };
  }, [apiKey]);

  // Update Markers & Bounds whenever places change
  useEffect(() => {
    if (!mapInstanceRef.current || !window.google?.maps) return;

    const map = mapInstanceRef.current;
    const infoWindow = infoWindowRef.current;

    // Clear previous markers & clusterer
    if (clustererRef.current) {
      clustererRef.current.clearMarkers();
    }
    markersRef.current.forEach((m) => {
      if (m.map) m.map = null;
    });
    markersRef.current = [];

    const validPlaces = places.filter((p) => p.lat && p.lon);
    if (validPlaces.length === 0) return;

    const bounds = new window.google.maps.LatLngBounds();
    const newMarkers = [];

    validPlaces.forEach((p) => {
      const pos = { lat: p.lat, lng: p.lon };
      bounds.extend(pos);

      // Create Custom Pin Element
      const pinColor = getCategoryColor(p.category);
      const pinContainer = document.createElement('div');
      pinContainer.className = `custom-google-pin ${selectedPlaceId === p.place_id ? 'active' : ''}`;
      pinContainer.style.cssText = `
        background-color: ${pinColor};
        width: 30px;
        height: 30px;
        border-radius: 50% 50% 50% 0;
        transform: rotate(-45deg);
        display: flex;
        align-items: center;
        justify-content: center;
        border: 2px solid #FFFFFF;
        box-shadow: 0 3px 8px rgba(0,0,0,0.28);
        cursor: pointer;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
      `;

      const innerDot = document.createElement('div');
      innerDot.style.cssText = `
        width: 8px;
        height: 8px;
        background-color: #FFFFFF;
        border-radius: 50%;
        transform: rotate(45deg);
      `;
      pinContainer.appendChild(innerDot);

      let marker;
      if (window.google.maps.marker && window.google.maps.marker.AdvancedMarkerElement) {
        marker = new window.google.maps.marker.AdvancedMarkerElement({
          map: map,
          position: pos,
          title: p.name,
          content: pinContainer
        });
      } else {
        marker = new window.google.maps.Marker({
          map: map,
          position: pos,
          title: p.name
        });
      }

      marker.placeData = p;

      // Click listener on marker
      marker.addListener('click', () => {
        const contentStr = `
          <div style="font-family: var(--font-sans, system-ui); max-width: 220px; padding: 4px;">
            <div style="font-size: 10px; text-transform: uppercase; font-weight: 700; color: ${pinColor}; letter-spacing: 0.05em; margin-bottom: 3px;">
              ${p.category || 'Place'}
            </div>
            <div style="font-weight: 600; font-size: 14px; color: #1B241C; line-height: 1.25; margin-bottom: 4px;">
              ${p.name}
            </div>
            <div style="font-size: 11px; color: #5C6E5E; margin-bottom: 6px;">
              ${p.address || p.location || ''}
            </div>
            ${p.rating ? `<div style="font-size: 11px; font-weight: 700; color: #8A624A; margin-bottom: 8px;">★ ${p.rating.toFixed(1)} ${p.review_count ? `(${p.review_count})` : ''}</div>` : ''}
            <a href="/explore/place/${encodeURIComponent(p.place_id)}" style="display: inline-block; font-size: 11px; font-weight: 600; background: #2C3E2D; color: #FFFFFF; padding: 4px 10px; border-radius: 4px; text-decoration: none;">
              View Details →
            </a>
          </div>
        `;
        infoWindow.setContent(contentStr);
        infoWindow.open({
          anchor: marker,
          map: map
        });

        if (onSelectPlace) {
          onSelectPlace(p);
        }
      });

      newMarkers.push(marker);
    });

    markersRef.current = newMarkers;

    // Initialize marker clusterer
    try {
      clustererRef.current = new MarkerClusterer({
        map: map,
        markers: newMarkers
      });
    } catch {
      // Fallback
    }

    // Auto-fit bounds
    if (validPlaces.length > 1) {
      map.fitBounds(bounds, { top: 40, right: 40, bottom: 40, left: 40 });
    } else if (validPlaces.length === 1) {
      map.setCenter({ lat: validPlaces[0].lat, lng: validPlaces[0].lon });
      map.setZoom(14);
    }
  }, [places, selectedPlaceId, onSelectPlace]);

  if (apiKeyMissing) {
    return (
      <div
        className="map-fallback-banner"
        style={{
          height: height,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          background: 'linear-gradient(135deg, #FAFBF7 0%, #F1F5EA 100%)',
          border: '1px solid var(--border)',
          borderRadius: 'var(--radius-lg, 12px)',
          padding: '2rem',
          textAlign: 'center'
        }}
      >
        <Compass size={36} style={{ color: 'var(--primary-green)', marginBottom: '0.75rem' }} />
        <h4 style={{ margin: '0 0 0.4rem', fontSize: '1.2rem', color: 'var(--text-primary)' }}>
          Professional Google Maps
        </h4>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', maxWidth: '480px', margin: '0 0 1rem', lineHeight: '1.5' }}>
          Interactive maps with Advanced Markers are ready. To enable live map rendering, set <code>VITE_GOOGLE_MAPS_API_KEY</code> in your environment.
        </p>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
          Showing {places.filter((p) => p.lat && p.lon).length} mapped coordinates ready for display
        </span>
      </div>
    );
  }

  if (mapError) {
    return (
      <div
        className="map-fallback-banner"
        style={{
          height: height,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          background: 'var(--surface-cream)',
          border: '1px solid var(--border)',
          borderRadius: 'var(--radius-lg)',
          padding: '2rem',
          textAlign: 'center'
        }}
      >
        <AlertCircle size={32} style={{ color: 'var(--accent)', marginBottom: '0.5rem' }} />
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>{mapError}</p>
      </div>
    );
  }

  return (
    <div
      className="map-view-wrapper"
      style={{
        width: '100%',
        height: height,
        borderRadius: 'var(--radius-lg, 12px)',
        overflow: 'hidden',
        border: '1px solid var(--border)',
        position: 'relative',
        zIndex: 1
      }}
    >
      <div ref={mapRef} style={{ width: '100%', height: '100%' }} />
    </div>
  );
};
