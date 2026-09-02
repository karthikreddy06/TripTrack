import { useEffect, useRef, useState, useCallback } from 'react';
import mapboxgl from 'mapbox-gl';
import 'mapbox-gl/dist/mapbox-gl.css';
import { MapPin, Navigation, Compass, AlertCircle } from 'lucide-react';

const CATEGORY_COLORS = {
  hotel: '#244B7A',
  restaurant: '#A03E1C',
  activity: '#61402B',
  attraction: '#2C3E2D',
  destination: '#1F2B20',
};

const getCategoryColor = (category) => {
  return CATEGORY_COLORS[category?.toLowerCase()] || '#2C3E2D';
};

const getValidCoordinates = (place) => {
  const lat = place?.lat ?? place?.latitude;
  const lon = place?.lon ?? place?.longitude ?? place?.lng;
  if (typeof lat === 'number' && typeof lon === 'number' && !isNaN(lat) && !isNaN(lon)) {
    return { lat, lon };
  }
  return null;
};

export const MapView = ({
  places = [],
  center = { lat: 17.3850, lng: 78.4867 },
  zoom = 12,
  height = '480px',
  selectedPlaceId = null,
  onSelectPlace = null,
}) => {
  const mapContainerRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const markersRef = useRef([]);
  const popupRef = useRef(null);

  const [mapError, setMapError] = useState(null);
  const [tokenMissing, setTokenMissing] = useState(false);

  const mapboxToken = (import.meta.env.VITE_MAPBOX_ACCESS_TOKEN || '').trim();

  // Initialize Mapbox instance
  useEffect(() => {
    if (!mapboxToken) {
      setTokenMissing(true);
      return;
    }

    setTokenMissing(false);
    mapboxgl.accessToken = mapboxToken;

    const initialCenter = Array.isArray(center)
      ? [center[1], center[0]]
      : [center.lng ?? center.lon ?? 78.4867, center.lat ?? 17.3850];

    try {
      const map = new mapboxgl.Map({
        container: mapContainerRef.current,
        style: 'mapbox://styles/mapbox/light-v11',
        center: initialCenter,
        zoom: zoom,
        attributionControl: false,
      });

      // Add navigation controls
      map.addControl(new mapboxgl.NavigationControl({ showCompass: true }), 'top-right');
      map.addControl(new mapboxgl.AttributionControl({ compact: true }), 'bottom-right');

      mapInstanceRef.current = map;
      setMapError(null);

      map.on('error', (e) => {
        if (e && e.error && e.error.status === 401) {
          setMapError('Invalid Mapbox access token. Please check VITE_MAPBOX_ACCESS_TOKEN.');
        }
      });
    } catch (err) {
      setMapError(err.message || 'Failed to initialize Mapbox');
    }

    return () => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
      }
    };
  }, [mapboxToken, zoom]);

  // Update Markers & Bounds whenever places change
  const updateMarkers = useCallback(() => {
    const map = mapInstanceRef.current;
    if (!map) return;

    // Clear previous markers
    markersRef.current.forEach((m) => m.remove());
    markersRef.current = [];

    if (popupRef.current) {
      popupRef.current.remove();
      popupRef.current = null;
    }

    const validPlaces = places
      .map((p) => ({ place: p, coords: getValidCoordinates(p) }))
      .filter((item) => item.coords !== null);

    if (validPlaces.length === 0) return;

    const bounds = new mapboxgl.LngLatBounds();

    validPlaces.forEach(({ place, coords }, idx) => {
      const isSelected = selectedPlaceId && (place.place_id === selectedPlaceId || place.provider_place_id === selectedPlaceId);
      const catColor = getCategoryColor(place.category);

      // Create Custom DOM Element for Marker
      const el = document.createElement('div');
      el.className = `mapbox-custom-marker ${isSelected ? 'selected' : ''}`;
      el.style.cssText = `
        display: flex;
        align-items: center;
        justify-content: center;
        width: ${isSelected ? '36px' : '28px'};
        height: ${isSelected ? '36px' : '28px'};
        background-color: ${isSelected ? 'var(--primary-green, #2C3E2D)' : catColor};
        color: #ffffff;
        border-radius: 50%;
        border: 2px solid #ffffff;
        box-shadow: 0 4px 12px rgba(0,0,0,0.22);
        cursor: pointer;
        font-family: var(--font-mono, monospace);
        font-size: ${isSelected ? '12px' : '10px'};
        font-weight: 700;
        transition: transform 0.2s cubic-bezier(0.16, 1, 0.3, 1), box-shadow 0.2s ease;
      `;
      el.innerText = `${idx + 1}`;

      // Create Popup
      const popupHtml = `
        <div style="font-family: inherit; padding: 4px; max-width: 220px;">
          <span style="font-size: 9px; text-transform: uppercase; font-weight: 700; color: ${catColor}; letter-spacing: 0.05em;">
            ${place.category?.toUpperCase() || 'PLACE'}
          </span>
          <h4 style="margin: 4px 0 2px 0; font-size: 13px; font-weight: 600; color: #1f2b20;">
            ${place.name}
          </h4>
          <p style="margin: 0; font-size: 11px; color: #64748b; line-height: 1.3;">
            ${place.address || place.location || ''}
          </p>
          ${place.rating ? `<div style="margin-top: 4px; font-size: 11px; font-weight: 600; color: #d97706;">★ ${Number(place.rating).toFixed(1)}</div>` : ''}
        </div>
      `;

      const popup = new mapboxgl.Popup({ offset: 25, closeButton: false }).setHTML(popupHtml);

      const marker = new mapboxgl.Marker(el)
        .setLngLat([coords.lon, coords.lat])
        .setPopup(popup)
        .addTo(map);

      el.addEventListener('click', (e) => {
        e.stopPropagation();
        if (onSelectPlace) {
          onSelectPlace(place);
        }
      });

      markersRef.current.push(marker);
      bounds.extend([coords.lon, coords.lat]);

      if (isSelected) {
        popupRef.current = popup;
        marker.togglePopup();
      }
    });

    // Fit map to markers bounds
    if (!bounds.isEmpty()) {
      map.fitBounds(bounds, {
        padding: { top: 60, bottom: 60, left: 60, right: 60 },
        maxZoom: 15,
        duration: 1000,
      });
    }
  }, [places, selectedPlaceId, onSelectPlace]);

  useEffect(() => {
    updateMarkers();
  }, [updateMarkers]);

  // Focus selected place when selectedPlaceId changes
  useEffect(() => {
    if (!selectedPlaceId || !mapInstanceRef.current) return;

    const target = places.find(
      (p) => p.place_id === selectedPlaceId || p.provider_place_id === selectedPlaceId
    );
    const coords = getValidCoordinates(target);

    if (coords) {
      mapInstanceRef.current.flyTo({
        center: [coords.lon, coords.lat],
        zoom: Math.max(mapInstanceRef.current.getZoom(), 14),
        essential: true,
        duration: 1200,
      });
    }
  }, [selectedPlaceId, places]);

  if (tokenMissing || mapError) {
    return (
      <div
        className="map-view-container card map-fallback-container"
        style={{
          height: height,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '2rem',
          textAlign: 'center',
          background: 'linear-gradient(135deg, #f5f6f2 0%, #ebeee7 100%)',
          border: '1px solid var(--border)',
          borderRadius: 'var(--radius-lg)',
        }}
      >
        <div
          style={{
            width: '48px',
            height: '48px',
            borderRadius: '50%',
            backgroundColor: '#ffffff',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 4px 12px rgba(0,0,0,0.06)',
            marginBottom: '1rem',
            color: 'var(--primary-green)',
          }}
        >
          <Compass size={24} />
        </div>
        <h4 style={{ fontSize: '1.15rem', marginBottom: '0.4rem', color: 'var(--text-main)' }}>
          Interactive Map
        </h4>
        <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', maxWidth: '360px', margin: 0 }}>
          {mapError ? mapError : 'Map temporarily unavailable. To enable live map exploration, configure VITE_MAPBOX_ACCESS_TOKEN.'}
        </p>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: '1rem', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
          <MapPin size={12} />
          <span>{places.length} verified coordinate markers ready</span>
        </div>
      </div>
    );
  }

  return (
    <div
      className="map-view-wrapper"
      style={{
        height: height,
        width: '100%',
        position: 'relative',
        borderRadius: 'var(--radius-lg)',
        overflow: 'hidden',
        border: '1px solid var(--border)',
      }}
    >
      <div
        ref={mapContainerRef}
        style={{ width: '100%', height: '100%' }}
        className="mapbox-gl-map-container"
      />
    </div>
  );
};
