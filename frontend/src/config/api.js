/**
 * Central API Client Configuration for Smart Payment Advisor
 * Provides base URL management and host fallback (127.0.0.1 <-> localhost)
 * with robust network failure handling.
 */

export const API_BASE_URL = 'http://127.0.0.1:8080';

/**
 * Robust fetch wrapper with hostname fallback and standard header handling.
 * Throws clean human-readable Error if backend server is unreachable.
 */
export async function fetchApi(endpoint, options = {}) {
  const primaryUrl = `${API_BASE_URL}${endpoint}`;
  
  const defaultHeaders = {
    'Content-Type': 'application/json',
    ...options.headers
  };

  const config = {
    ...options,
    headers: defaultHeaders
  };

  try {
    const res = await fetch(primaryUrl, config);
    return res;
  } catch (err) {
    console.warn(`Primary API call to ${primaryUrl} failed. Retrying with localhost fallback...`, err);
    try {
      const fallbackUrl = primaryUrl.replace('127.0.0.1', 'localhost');
      const fallbackRes = await fetch(fallbackUrl, config);
      return fallbackRes;
    } catch (fallbackErr) {
      console.error(`API fetch failed on both 127.0.0.1 and localhost for ${endpoint}:`, fallbackErr);
      throw new Error('⚠️ Cannot reach server — please check backend is running');
    }
  }
}
