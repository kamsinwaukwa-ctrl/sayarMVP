/**
 * Stateless HTTP client that reads auth token on every request
 * Eliminates token drift between different API client instances
 */

import type { ApiResponse } from '@/types/api'

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

/**
 * Get the current auth token from localStorage
 * Returns undefined if no token is found
 */
const getToken = (): string | undefined => {
  try {
    return localStorage.getItem("access_token") || undefined;
  } catch {
    return undefined;
  }
};

/**
 * Make an HTTP request with automatic token injection
 * Reads token fresh on every request to avoid token drift
 */
async function request<T = unknown>(path: string, init: RequestInit = {}): Promise<T> {
  const token = getToken();
  const isFormData = init.body instanceof FormData;

  const headers: HeadersInit = {
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    // Let the browser set multipart boundary for FormData
    ...(isFormData ? {} : { "Content-Type": "application/json" }),
    ...(init.headers || {}),
  };

  const url = `${API_BASE}${path}`;
  const config: RequestInit = {
    ...init,
    headers,
    credentials: init.credentials ?? "same-origin",
  };

  try {
    const response = await fetch(url, config);

    if (!response.ok) {
      // Try to get error details from response
      let errorMessage = `${response.status} ${response.statusText}`;
      try {
        const errorData = await response.json();
        if (errorData.error?.message) {
          errorMessage = errorData.error.message;
        } else if (errorData.detail) {
          errorMessage = errorData.detail;
        } else if (errorData.message) {
          errorMessage = errorData.message;
        }

        // Handle specific error codes
        if (response.status === 403 && errorData.error?.code === 'AUTHORIZATION_FAILED') {
          errorMessage = 'Authentication required. Please log in again.';
        }
      } catch (parseError) {
        // If response isn't JSON, use status text
        console.warn('Failed to parse error response:', parseError);
      }

      const error = new Error(errorMessage) as Error & { status: number; statusText: string };
      error.status = response.status;
      error.statusText = response.statusText;
      throw error;
    }

    // Check if response has JSON content
    const contentType = response.headers.get("content-type") || "";
    if (contentType.includes("application/json")) {
      const data: ApiResponse<T> | T = await response.json();
      // Handle envelope format (with data property) or direct response
      if (data && typeof data === 'object' && 'data' in data) {
        return (data as ApiResponse<T>).data as T;
      }
      return data as T;
    }

    return response.text() as T;
  } catch (error) {
    // Re-throw with status code if available
    if (error instanceof Error && !('status' in error)) {
      (error as Error & { status: number }).status = 0; // Network error
    }
    throw error;
  }
}

/**
 * HTTP client with common REST methods
 * All methods read token fresh from localStorage on every request
 */
export const http = {
  get: <T = unknown>(path: string, init?: RequestInit): Promise<T> =>
    request<T>(path, { ...init, method: "GET" }),

  post: <T = unknown>(path: string, body?: unknown, init?: RequestInit): Promise<T> =>
    request<T>(path, {
      ...init,
      method: "POST",
      body: body instanceof FormData ? body : JSON.stringify(body)
    }),

  put: <T = unknown>(path: string, body?: unknown, init?: RequestInit): Promise<T> =>
    request<T>(path, {
      ...init,
      method: "PUT",
      body: body instanceof FormData ? body : JSON.stringify(body)
    }),

  patch: <T = unknown>(path: string, body?: unknown, init?: RequestInit): Promise<T> =>
    request<T>(path, {
      ...init,
      method: "PATCH",
      body: body instanceof FormData ? body : JSON.stringify(body)
    }),

  del: <T = unknown>(path: string, init?: RequestInit): Promise<T> =>
    request<T>(path, { ...init, method: "DELETE" }),
};