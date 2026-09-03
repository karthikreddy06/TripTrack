/**
 * Validates and sanitizes external URLs before rendering them into href attributes or navigating.
 * Prevents DOM-based XSS attacks via javascript:, vbscript:, data:, or other malicious URI schemes.
 *
 * @param {string} url - Target URL to validate
 * @returns {string|null} - Clean URL if strictly http:// or https://, otherwise null
 */
export function getSafeExternalUrl(url) {
  if (!url || typeof url !== 'string') {
    return null;
  }

  const trimmed = url.trim();

  // Strictly permit only http:// and https:// schemes
  if (/^https?:\/\//i.test(trimmed)) {
    try {
      const parsed = new URL(trimmed);
      if (parsed.protocol === 'http:' || parsed.protocol === 'https:') {
        return trimmed;
      }
    } catch {
      return null;
    }
  }

  // Reject all relative, data:, javascript:, vbscript:, or other pseudo-protocols
  return null;
}
