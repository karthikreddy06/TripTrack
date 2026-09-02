import { useState } from 'react';

export const SafeImage = ({
  src,
  alt = 'Place Photo',
  isVerified = false,
  className = '',
  style = {},
}) => {
  const [hasError, setHasError] = useState(false);

  // If unverified, no source, or failed to load, return null (do NOT render empty box or placeholder)
  if (!src || !isVerified || hasError) {
    return null;
  }

  return (
    <img
      src={src}
      alt={alt}
      className={className}
      loading="lazy"
      onError={() => setHasError(true)}
      style={{
        width: '100%',
        height: '100%',
        objectFit: 'cover',
        display: 'block',
        ...style,
      }}
    />
  );
};
