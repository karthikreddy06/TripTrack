import { useEffect, useRef, useState, useCallback } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { Compass } from 'lucide-react';

const CATEGORY_COLORS = {
  hotel: '#244B7A',
  restaurant: '#A03E1C',
  cafe: '#C05621',
  activity: '#61402B',
  attraction: '#2C3E2D',
  museum: '#4338CA',
  park: '#15803D',
  historic: '#78350F',
  destination: '#1F2B20',
};

const getCategoryColor = (category) => {
  return CATEGORY_COLORS[category?.toLowerCase()] || '#2C3E2D';
};

const getValidCoordinates = (place) => {
  const lat = place?.lat ?? place?.latitude ?? place?.location?.lat;
  const lon = place?.lon ?? place?.longitude ?? place?.lng ?? place?.location?.lon;
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
  const markersLayerRef = useRef(null);
  const markersMapRef = useRef(new Map());

  const [mapError, setMapError] = useState(null);

  // Initialize Leaflet Map Instance
  useEffect(() => {
    if (!mapContainerRef.current) return;

    try {
      const initialLat = Array.isArray(center) ? center[0] : (center?.lat ?? 17.3850);
      const initialLng = Array.isArray(center) ? center[1] : (center?.lng ?? center?.lon ?? 78.4867);

      if (!mapInstanceRef.current) {
        const map = L.map(mapContainerRef.current, {
          center: [initialLat, initialLng],
          zoom: zoom,
          zoomControl: true,
          attributionControl: true,
        });

        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
          maxZoom: 19,
          attribution: '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">OpenStreetMap</a> contributors',
        }).addTo(map);

        const markersLayer = L.layerGroup().addTo(map);
        markersLayerRef.current = markersLayer;
        mapInstanceRef.current = map;
        setMapError(null);
      }

      // ResizeObserver to handle tab switches and container resizes
      const resizeObserver = new ResizeObserver(() => {
        if (mapInstanceRef.current) {
          mapInstanceRef.current.invalidateSize();
        }
      });

      if (mapContainerRef.current) {
        resizeObserver.observe(mapContainerRef.current);
      }

      setTimeout(() => {
        if (mapInstanceRef.current) {
          mapInstanceRef.current.invalidateSize();
        }
      }, 200);

      return () => {
        resizeObserver.disconnect();
      };
    } catch (err) {
      setMapError(err.message || 'Failed to initialize OpenStreetMap');
    }

    return () => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
      }
    };
  }, []);

  // Update Markers when places change
  const updateMarkers = useCallback(() => {
    const map = mapInstanceRef.current;
    const markersLayer = markersLayerRef.current;
    if (!map || !markersLayer) return;

    markersLayer.clearLayers();
    markersMapRef.current.clear();

    const validPlaces = places
      .map((p) => ({ place: p, coords: getValidCoordinates(p) }))
      .filter((item) => item.coords !== null);

    if (validPlaces.length === 0) return;

    const bounds = L.latLngBounds();

    validPlaces.forEach(({ place, coords }, idx) => {
      const pId = place.id || place.place_id || place.provider_id || String(idx);
      const isSelected = selectedPlaceId && (place.id === selectedPlaceId || place.place_id === selectedPlaceId || place.provider_id === selectedPlaceId);
      const catColor = getCategoryColor(place.category);

      const customIcon = L.divIcon({
        className: 'custom-osm-div-icon',
        html: `
          <div style="
            display: flex;
            align-items: center;
            justify-content: center;
            width: ${isSelected ? '32px' : '26px'};
            height: ${isSelected ? '32px' : '26px'};
            background-color: ${isSelected ? '#1f2b20' : catColor};
            color: #ffffff;
            border-radius: 50%;
            border: 2px solid #ffffff;
            box-shadow: 0 3px 8px rgba(0,0,0,0.35);
            font-family: var(--font-mono, monospace);
            font-size: ${isSelected ? '11px' : '9px'};
            font-weight: 700;
            cursor: pointer;
            transition: transform 0.2s cubic-bezier(0.16, 1, 0.3, 1);
          ">
            ${idx + 1}
          </div>
        `,
        iconSize: [isSelected ? 32 : 26, isSelected ? 32 : 26],
        iconAnchor: [isSelected ? 16 : 13, isSelected ? 16 : 13],
        popupAnchor: [0, isSelected ? -16 : -13],
      });

      const marker = L.marker([coords.lat, coords.lon], { icon: customIcon });

      const popupHtml = `
        <div style="font-family: inherit; padding: 2px; max-width: 220px;">
          <span style="font-size: 9px; text-transform: uppercase; font-weight: 700; color: ${catColor}; letter-spacing: 0.05em;">
            ${place.category?.toUpperCase() || 'PLACE'}
          </span>
          <h4 style="margin: 4px 0 2px 0; font-size: 13px; font-weight: 600; color: #1f2b20;">
            ${place.name}
          </h4>
          <p style="margin: 0; font-size: 11px; color: #64748b; line-height: 1.3;">
            ${place.address || place.location || ''}
          </p>
        </div>
      `;

      marker.bindPopup(popupHtml, { closeButton: false, offset: [0, -10] });

      marker.on('click', () => {
        if (onSelectPlace) {
          onSelectPlace(place);
        }
      });

      markersLayer.addLayer(marker);
      markersMapRef.current.set(pId, marker);
      bounds.extend([coords.lat, coords.lon]);

      if (isSelected) {
        marker.openPopup();
      }
    });

    if (bounds.isValid()) {
      map.fitBounds(bounds, {
        padding: [45, 45],
        maxZoom: 15,
        animate: true,
      });
    }
  }, [places, selectedPlaceId, onSelectPlace]);

  useEffect(() => {
    updateMarkers();
  }, [updateMarkers]);

  // Selected Place focus effect
  useEffect(() => {
    if (!selectedPlaceId || !mapInstanceRef.current) return;

    const target = places.find(
      (p) => p.id === selectedPlaceId || p.place_id === selectedPlaceId || p.provider_id === selectedPlaceId
    );
    const coords = getValidCoordinates(target);

    if (coords) {
      mapInstanceRef.current.setView([coords.lat, coords.lon], Math.max(mapInstanceRef.current.getZoom(), 14), {
        animate: true,
        duration: 0.8,
      });

      const pId = target.id || target.place_id || target.provider_id;
      const marker = markersMapRef.current.get(pId);
      if (marker) {
        marker.openPopup();
      }
    }
  }, [selectedPlaceId, places]);

  if (mapError) {
    return (
      <div
        className="map-view-container card map-fallback-container"
        style={{
          height: height,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          textAlign: 'center',
          padding: '2rem',
          background: 'var(--surface)',
        }}
      >
        <Compass size={32} style={{ color: 'var(--accent)', marginBottom: '0.75rem' }} />
        <h4 style={{ fontSize: '1.1rem', margin: '0 0 0.5rem 0' }}>OpenStreetMap Preview</h4>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', maxWidth: '380px', margin: 0 }}>
          {mapError}
        </p>
      </div>
    );
  }

  return (
    <div
      className="map-view-container card"
      style={{
        position: 'relative',
        height: height,
        minHeight: '380px',
        width: '100%',
        borderRadius: 'var(--radius-md)',
        overflow: 'hidden',
        border: '1px solid var(--border-light)',
      }}
    >
      <div
        ref={mapContainerRef}
        style={{
          width: '100%',
          height: '100%',
          minHeight: '380px',
          background: '#f8f9f6',
        }}
      />
    </div>
  );
};
