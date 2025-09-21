/**
 * API Client Tests for Sayar Frontend
 * Tests API client functionality and error handling
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { ApiClient, ApiClientError } from '@/lib/api-client'

// Mock fetch
global.fetch = vi.fn()
const mockFetch = vi.mocked(fetch)

// Mock localStorage
const mockLocalStorage = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
}

Object.defineProperty(window, 'localStorage', {
  value: mockLocalStorage,
  writable: true,
})

describe('ApiClient', () => {
  let apiClient: ApiClient
  const baseUrl = 'http://localhost:8000'

  beforeEach(() => {
    vi.clearAllMocks()
    apiClient = new ApiClient(baseUrl)
    mockLocalStorage.getItem.mockReturnValue(null)
  })

  describe('constructor', () => {
    it('should initialize with base URL', () => {
      const client = new ApiClient('http://test.com/')
      expect(client['baseUrl']).toBe('http://test.com')
    })

    it('should try to restore token from localStorage', () => {
      mockLocalStorage.getItem.mockReturnValue('stored-token')
      const client = new ApiClient(baseUrl)
      expect(mockLocalStorage.getItem).toHaveBeenCalledWith('auth_token')
      expect(client.getAuthToken()).toBe('stored-token')
    })
  })

  describe('token management', () => {
    it('should store and retrieve auth token', () => {
      const token = 'test-token'
      apiClient.setAuthToken(token)
      
      expect(mockLocalStorage.setItem).toHaveBeenCalledWith('auth_token', token)
      expect(apiClient.getAuthToken()).toBe(token)
      expect(apiClient.isAuthenticated()).toBe(true)
    })

    it('should clear auth token', () => {
      apiClient.setAuthToken('test-token')
      apiClient.setAuthToken(null)
      
      expect(mockLocalStorage.removeItem).toHaveBeenCalledWith('auth_token')
      expect(apiClient.getAuthToken()).toBe(null)
      expect(apiClient.isAuthenticated()).toBe(false)
    })

    it('should handle localStorage errors gracefully', () => {
      mockLocalStorage.setItem.mockImplementation(() => {
        throw new Error('Storage quota exceeded')
      })
      
      // Should not throw
      expect(() => apiClient.setAuthToken('test-token')).not.toThrow()
    })
  })

  describe('login', () => {
    it('should make login request and store token', async () => {
      const credentials = { email: 'test@example.com', password: 'password123' }
      const mockResponse = {
        token: 'auth-token',
        user: {
          id: '123',
          name: 'Test User',
          email: 'test@example.com',
          role: 'admin',
          merchant_id: '456',
        },
      }

      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ ok: true, data: mockResponse }),
      } as Response)

      const result = await apiClient.login(credentials)

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/auth/login',
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(credentials),
        }
      )

      expect(result).toEqual(mockResponse)
      expect(apiClient.getAuthToken()).toBe('auth-token')
    })

    it('should handle login errors', async () => {
      const credentials = { email: 'test@example.com', password: 'wrong' }
      
      mockFetch.mockResolvedValue({
        ok: false,
        status: 401,
        statusText: 'Unauthorized',
        json: () => Promise.resolve({
          ok: false,
          error: {
            code: 'AUTHENTICATION_ERROR',
            message: 'Invalid credentials',
            request_id: 'req-123',
          },
        }),
      } as Response)

      await expect(apiClient.login(credentials)).rejects.toThrow(ApiClientError)
      
      try {
        await apiClient.login(credentials)
      } catch (error) {
        expect(error).toBeInstanceOf(ApiClientError)
        expect((error as ApiClientError).code).toBe('AUTHENTICATION_ERROR')
        expect((error as ApiClientError).message).toBe('Invalid credentials')
        expect((error as ApiClientError).status).toBe(401)
        expect((error as ApiClientError).requestId).toBe('req-123')
      }
    })
  })

  describe('register', () => {
    it('should make register request and store token', async () => {
      const userData = {
        name: 'Test User',
        email: 'test@example.com',
        password: 'password123',
        business_name: 'Test Business',
        whatsapp_phone_e164: '+1234567890',
      }

      const mockResponse = {
        token: 'auth-token',
        user: {
          id: '123',
          name: 'Test User',
          email: 'test@example.com',
          role: 'admin',
          merchant_id: '456',
        },
        merchant: {
          id: '456',
          name: 'Test Business',
          whatsapp_phone_e164: '+1234567890',
        },
      }

      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ ok: true, data: mockResponse }),
      } as Response)

      const result = await apiClient.register(userData)

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/auth/register',
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(userData),
        }
      )

      expect(result).toEqual(mockResponse)
      expect(apiClient.getAuthToken()).toBe('auth-token')
    })
  })

  describe('authenticated requests', () => {
    beforeEach(() => {
      apiClient.setAuthToken('test-token')
    })

    it('should include authorization header in authenticated requests', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ ok: true, data: { id: '123' } }),
      } as Response)

      await apiClient.getCurrentUser()

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/auth/me',
        expect.objectContaining({
          method: 'GET',
          headers: expect.objectContaining({
            'Authorization': 'Bearer test-token',
            'Content-Type': 'application/json',
          }),
        })
      )
    })

    it('should handle 401 errors by not clearing token automatically', async () => {
      mockFetch.mockResolvedValue({
        ok: false,
        status: 401,
        statusText: 'Unauthorized',
        json: () => Promise.resolve({
          ok: false,
          error: {
            code: 'AUTHENTICATION_ERROR',
            message: 'Token expired',
          },
        }),
      } as Response)

      await expect(apiClient.getCurrentUser()).rejects.toThrow(ApiClientError)
      
      // Token should still be present (let auth context handle clearing)
      expect(apiClient.getAuthToken()).toBe('test-token')
    })
  })

  describe('logout', () => {
    it('should clear token and optionally call backend', async () => {
      apiClient.setAuthToken('test-token')
      
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ ok: true }),
      } as Response)

      await apiClient.logout()

      expect(apiClient.getAuthToken()).toBe(null)
      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/auth/logout',
        expect.objectContaining({
          method: 'POST',
        })
      )
    })

    it('should clear token even if backend call fails', async () => {
      apiClient.setAuthToken('test-token')
      
      mockFetch.mockRejectedValue(new Error('Network error'))

      await apiClient.logout()

      expect(apiClient.getAuthToken()).toBe(null)
    })
  })

  describe('error handling', () => {
    it('should handle network errors', async () => {
      mockFetch.mockRejectedValue(new Error('Network error'))

      await expect(apiClient.login({
        email: 'test@example.com',
        password: 'password123',
      })).rejects.toThrow(ApiClientError)

      try {
        await apiClient.login({
          email: 'test@example.com',
          password: 'password123',
        })
      } catch (error) {
        expect(error).toBeInstanceOf(ApiClientError)
        expect((error as ApiClientError).code).toBe('NETWORK_ERROR')
        expect((error as ApiClientError).status).toBe(0)
      }
    })

    it('should handle invalid JSON responses', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.reject(new Error('Invalid JSON')),
      } as Response)

      await expect(apiClient.login({
        email: 'test@example.com',
        password: 'password123',
      })).rejects.toThrow(ApiClientError)

      try {
        await apiClient.login({
          email: 'test@example.com',
          password: 'password123',
        })
      } catch (error) {
        expect(error).toBeInstanceOf(ApiClientError)
        expect((error as ApiClientError).code).toBe('INVALID_RESPONSE')
      }
    })
  })

  describe('health check', () => {
    it('should make health check request', async () => {
      const mockResponse = { status: 'healthy', timestamp: '2025-01-27T10:00:00Z' }
      
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ ok: true, data: mockResponse }),
      } as Response)

      const result = await apiClient.healthCheck()

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/healthz',
        expect.objectContaining({
          method: 'GET',
        })
      )

      expect(result).toEqual(mockResponse)
    })
  })
})