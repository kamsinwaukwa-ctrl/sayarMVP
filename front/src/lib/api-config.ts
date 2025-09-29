/**
 * Centralized API configuration
 */

export const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

/**
 * Construct full API URL from endpoint path
 */
export function apiUrl(endpoint: string): string {
  // Remove leading slash if present to avoid double slashes
  const cleanEndpoint = endpoint.startsWith('/') ? endpoint.slice(1) : endpoint
  return `${API_BASE}/${cleanEndpoint}`
}

/**
 * Get auth token from localStorage
 */
export function getAuthToken(): string | null {
  return localStorage.getItem('access_token')
}

/**
 * Standard headers for authenticated requests
 */
export function getAuthHeaders(): Record<string, string> {
  const token = getAuthToken()
  return token ? { 'Authorization': `Bearer ${token}` } : {}
}