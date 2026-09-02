import { useMemo } from 'react';
import {
  Landmark,
  Scroll,
  Hotel,
  Utensils,
  Coffee,
  Trees,
  Compass,
  MapPin
} from 'lucide-react';

const CATEGORY_THEMES = {
  attraction: {
    gradient: 'linear-gradient(135deg, #1e3a2b 0%, #2d553e 55%, #447456 100%)',
    accent: '#8cd4a4',
    icon: Landmark,
    label: 'ATTRACTION',
    patternOpacity: 0.18,
  },
  historic: {
    gradient: 'linear-gradient(135deg, #282f25 0%, #3e4839 55%, #596653 100%)',
    accent: '#d8cbb5',
    icon: Scroll,
    label: 'HISTORIC',
    patternOpacity: 0.16,
  },
  museum: {
    gradient: 'linear-gradient(135deg, #1c2e2e 0%, #2d4747 55%, #456868 100%)',
    accent: '#a5d8d8',
    icon: Landmark,
    label: 'MUSEUM',
    patternOpacity: 0.16,
  },
  hotel: {
    gradient: 'linear-gradient(135deg, #2d2a24 0%, #474136 55%, #635b4c 100%)',
    accent: '#ebd5b3',
    icon: Hotel,
    label: 'HOTEL',
    patternOpacity: 0.15,
  },
  restaurant: {
    gradient: 'linear-gradient(135deg, #38241c 0%, #54372a 55%, #754f3d 100%)',
    accent: '#f2bda0',
    icon: Utensils,
    label: 'DINING',
    patternOpacity: 0.16,
  },
  cafe: {
    gradient: 'linear-gradient(135deg, #33231d 0%, #4d362d 55%, #6e4e41 100%)',
    accent: '#edd1c2',
    icon: Coffee,
    label: 'CAFE',
    patternOpacity: 0.16,
  },
  park: {
    gradient: 'linear-gradient(135deg, #183827 0%, #25543a 55%, #387853 100%)',
    accent: '#a0e8be',
    icon: Trees,
    label: 'PARK & NATURE',
    patternOpacity: 0.20,
  },
  activity: {
    gradient: 'linear-gradient(135deg, #1b2f38 0%, #2b4957 55%, #3f687a 100%)',
    accent: '#a8dcf0',
    icon: Compass,
    label: 'ACTIVITY',
    patternOpacity: 0.16,
  },
};

export const EditorialCardBanner = ({
  category = 'attraction',
  name = '',
  lat = null,
  lon = null,
  height = '115px',
  className = '',
  children,
}) => {
  const catKey = (category || 'attraction').toLowerCase();
  const theme = CATEGORY_THEMES[catKey] || CATEGORY_THEMES.attraction;
  const CategoryIcon = theme.icon;

  // Extract initials (e.g. "Charminar" -> "CH", "Golconda Fort" -> "GF")
  const initials = useMemo(() => {
    if (!name) return theme.label.slice(0, 2);
    const words = name.trim().split(/\s+/);
    if (words.length === 1) return words[0].slice(0, 2).toUpperCase();
    return (words[0][0] + words[1][0]).toUpperCase();
  }, [name, theme.label]);

  // Format coordinates stamp (e.g. "17.36°N · 78.47°E")
  const coordsStamp = useMemo(() => {
    if (lat === null || lon === null || isNaN(lat) || isNaN(lon)) return null;
    const nLat = typeof lat === 'string' ? parseFloat(lat) : lat;
    const nLon = typeof lon === 'string' ? parseFloat(lon) : lon;
    const latDir = nLat >= 0 ? 'N' : 'S';
    const lonDir = nLon >= 0 ? 'E' : 'W';
    return `${Math.abs(nLat).toFixed(2)}°${latDir} · ${Math.abs(nLon).toFixed(2)}°${lonDir}`;
  }, [lat, lon]);

  return (
    <div
      className={`editorial-card-banner ${className}`}
      style={{
        position: 'relative',
        width: '100%',
        height,
        background: theme.gradient,
        overflow: 'hidden',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        padding: '0.75rem 0.95rem',
        borderTopLeftRadius: 'inherit',
        borderTopRightRadius: 'inherit',
        color: '#FFFFFF',
        userSelect: 'none',
      }}
    >
      {/* Background Topographic / Botanical Vector Pattern */}
      <svg
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: '100%',
          height: '100%',
          opacity: theme.patternOpacity,
          pointerEvents: 'none',
        }}
        viewBox="0 0 300 120"
        preserveAspectRatio="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <path
          d="M-20,60 C40,20 100,100 160,50 C220,0 260,90 320,40"
          fill="none"
          stroke="#FFFFFF"
          strokeWidth="1.2"
          strokeDasharray="4 4"
        />
        <path
          d="M-10,90 C60,40 120,110 180,70 C240,30 280,100 330,60"
          fill="none"
          stroke="#FFFFFF"
          strokeWidth="1.0"
        />
        <path
          d="M-30,30 C30,80 90,30 150,80 C210,130 270,40 320,80"
          fill="none"
          stroke="#FFFFFF"
          strokeWidth="0.8"
        />
        {/* Subtle decorative botanical compass marks */}
        <circle cx="250" cy="30" r="16" fill="none" stroke="#FFFFFF" strokeWidth="0.6" strokeDasharray="2 3" />
        <circle cx="250" cy="30" r="4" fill="none" stroke="#FFFFFF" strokeWidth="0.8" />
        <line x1="250" y1="10" x2="250" y2="50" stroke="#FFFFFF" strokeWidth="0.6" />
        <line x1="230" y1="30" x2="270" y2="30" stroke="#FFFFFF" strokeWidth="0.6" />
      </svg>

      {/* Watermark Monogram Typography in the background */}
      <div
        style={{
          position: 'absolute',
          right: '12px',
          bottom: '-10px',
          fontFamily: 'var(--font-serif, Georgia, serif)',
          fontSize: '4.2rem',
          fontWeight: 800,
          letterSpacing: '-0.04em',
          lineHeight: 1,
          color: '#FFFFFF',
          opacity: 0.11,
          pointerEvents: 'none',
          fontStyle: 'italic',
        }}
      >
        {initials}
      </div>

      {/* Top Banner Row (Category Pill + Wishlist Button via children) */}
      <div
        style={{
          position: 'relative',
          zIndex: 2,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          width: '100%',
        }}
      >
        {children}
      </div>

      {/* Bottom Coordinates & Provenance Mark */}
      <div
        style={{
          position: 'relative',
          zIndex: 2,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          fontSize: '0.68rem',
          fontFamily: 'var(--font-mono, monospace)',
          letterSpacing: '0.05em',
          color: 'rgba(255, 255, 255, 0.75)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
          <CategoryIcon size={12} style={{ color: theme.accent }} />
          <span style={{ textTransform: 'uppercase', fontWeight: 600, color: theme.accent }}>
            {theme.label}
          </span>
        </div>

        {coordsStamp && (
          <span style={{ opacity: 0.85, fontSize: '0.64rem' }}>
            {coordsStamp}
          </span>
        )}
      </div>
    </div>
  );
};
