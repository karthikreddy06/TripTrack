import { useState } from 'react';
import { Camera, ImageOff, Compass } from 'lucide-react';

export const SafeImage = ({
  src,
  alt = 'Place Photo',
  isVerified = false,
  className = '',
  style = {},
  placeholderClassName = '',
  placeholderText = 'NO VERIFIED PHOTO AVAILABLE',
  icon: CustomIcon = null,
}) => {
  const [hasError, setHasError] = useState(false);

  // If no source, not verified, or image failed to load -> Render professional botanical placeholder
  if (!src || !isVerified || hasError) {
    const FallbackIcon = CustomIcon || Camera;
    return (
      <div
        className={`safe-image-placeholder ${placeholderClassName}`}
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '0.45rem',
          backgroundColor: 'var(--surface, #f8f9f6)',
          border: '1px solid var(--border, #e5e7eb)',
          color: 'var(--text-muted, #8a9a86)',
          width: '100%',
          height: '100%',
          minHeight: '140px',
          userSelect: 'none',
          padding: '1rem',
          textAlign: 'center',
          ...style,
        }}
      >
        <FallbackIcon size={22} style={{ opacity: 0.65, strokeWidth: 1.5 }} />
        <span
          style={{
            fontFamily: 'var(--font-mono, monospace)',
            fontSize: '0.65rem',
            letterSpacing: '0.06em',
            textTransform: 'uppercase',
            fontWeight: 600,
            opacity: 0.8,
            lineHeight: 1.2,
          }}
        >
          {placeholderText}
        </span>
      </div>
    );
  }

  return (
    <img
      src={src}
      alt={alt}
      className={className}
      style={{
        objectFit: 'cover',
        width: '100%',
        height: '100%',
        display: 'block',
        ...style,
      }}
      loading="lazy"
      onError={() => setHasError(true)}
    />
  );
};
