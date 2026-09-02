/**
 * Calculate Great-Circle distance between two coordinates in kilometers using Haversine formula.
 */
export const calculateDistanceKm = (lat1, lon1, lat2, lon2) => {
  if (
    lat1 === undefined || lat1 === null ||
    lon1 === undefined || lon1 === null ||
    lat2 === undefined || lat2 === null ||
    lon2 === undefined || lon2 === null
  ) {
    return null;
  }

  const nLat1 = typeof lat1 === 'string' ? parseFloat(lat1) : lat1;
  const nLon1 = typeof lon1 === 'string' ? parseFloat(lon1) : lon1;
  const nLat2 = typeof lat2 === 'string' ? parseFloat(lat2) : lat2;
  const nLon2 = typeof lon2 === 'string' ? parseFloat(lon2) : lon2;

  if (isNaN(nLat1) || isNaN(nLon1) || isNaN(nLat2) || isNaN(nLon2)) {
    return null;
  }

  const R = 6371; // Earth's radius in km
  const dLat = (nLat2 - nLat1) * (Math.PI / 180);
  const dLon = (nLon2 - nLon1) * (Math.PI / 180);

  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(nLat1 * (Math.PI / 180)) *
      Math.cos(nLat2 * (Math.PI / 180)) *
      Math.sin(dLon / 2) *
      Math.sin(dLon / 2);

  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
};

/**
 * Format distance in a human-friendly string.
 * Example: 0.4 -> "400 m", 1.83 -> "1.8 km"
 */
export const formatDistance = (km) => {
  if (km === null || km === undefined || isNaN(km)) return '';
  if (km < 1) {
    return `${Math.round(km * 1000)} m`;
  }
  return `${km.toFixed(1)} km`;
};
