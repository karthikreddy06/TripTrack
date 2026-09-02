import { useEffect, useRef } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

// Fix Leaflet's default marker icon paths in Vite bundling
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
});

// Custom botanical pin icon creator
const createCustomPin = (category) => {
  let color = '#2C3E2D'; // Forest green
  if (category === 'hotel') color = '#3B5998';
  if (category === 'restaurant') color = '#D95D39';
  if (category === 'activity') color = '#8A624A';

  return L.divIcon({
    className: 'custom-leaflet-marker',
    html: `<div style="
      background-color: ${color};
      width: 28px;
      height: 28px;
      border-radius: 50% 50% 50% 0;
      transform: rotate(-45deg);
      display: flex;
      align-items: center;
      justify-content: center;
      border: 2px solid #FFFFFF;
      box-shadow: 0 2px 6px rgba(0,0,0,0.3);
    ">
      <div style="
        width: 8px;
        height: 8px;
        background-color: #FFFFFF;
        border-radius: 50%;
        transform: rotate(45deg);
      "></div>
    </div>`,
    iconSize: [28, 28],
    iconAnchor: [14, 28],
    popupAnchor: [0, -28],
  });
};

export const MapView = ({
  places = [],
  center = [15.2993, 74.1240],
  zoom = 11,
  height = '420px',
  onSelectPlace
}) => {
  const mapContainerRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const markersLayerRef = useRef(null);

  useEffect(() => {
    if (!mapContainerRef.current) return;

    // Initialize Map if not already created
    if (!mapInstanceRef.current) {
      const map = L.map(mapContainerRef.current, {
        center: center,
        zoom: zoom,
        zoomControl: true,
        scrollWheelZoom: false,
      });

      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution:
          '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        maxZoom: 19,
      }).addTo(map);

      markersLayerRef.current = L.featureGroup().addTo(map);
      mapInstanceRef.current = map;
    }

    const map = mapInstanceRef.current;
    const markersLayer = markersLayerRef.current;

    // Clear previous markers
    markersLayer.clearLayers();

    const validPlaces = places.filter((p) => p.lat && p.lon);

    if (validPlaces.length > 0) {
      validPlaces.forEach((p) => {
        const marker = L.marker([p.lat, p.lon], {
          icon: createCustomPin(p.category),
        });

        const popupContent = `
          <div style="font-family: var(--font-sans, system-ui); min-width: 180px; padding: 4px;">
            <div style="font-size: 10px; text-transform: uppercase; font-weight: 700; color: #8A624A; letter-spacing: 0.05em; margin-bottom: 2px;">
              ${p.category || 'Place'}
            </div>
            <div style="font-weight: 600; font-size: 13px; color: #1B241C; margin-bottom: 4px;">
              ${p.name}
            </div>
            <div style="font-size: 11px; color: #5C6E5E; margin-bottom: 6px;">
              ${p.location || ''}
            </div>
            ${p.price_level ? `<span style="display:inline-block; font-size: 10px; font-weight: 700; background: #F1F5EA; padding: 2px 6px; border-radius: 4px; color: #2C3E2D; margin-bottom: 6px;">${p.price_level}</span>` : ''}
          </div>
        `;

        marker.bindPopup(popupContent);
        marker.on('click', () => {
          if (onSelectPlace) onSelectPlace(p);
        });

        markersLayer.addLayer(marker);
      });

      // Fit map bounds to encompass all markers if multiple
      if (validPlaces.length > 1) {
        map.fitBounds(markersLayer.getBounds(), { padding: [40, 40], maxZoom: 14 });
      } else if (validPlaces.length === 1) {
        map.setView([validPlaces[0].lat, validPlaces[0].lon], 13);
      }
    } else {
      map.setView(center, zoom);
    }

    // Leaflet resize invalidation
    setTimeout(() => {
      map.invalidateSize();
    }, 200);

    return () => {
      // Cleanup on unmount
    };
  }, [places, center, zoom, onSelectPlace]);

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
        zIndex: 1,
      }}
    >
      <div ref={mapContainerRef} style={{ width: '100%', height: '100%' }} />
    </div>
  );
};
