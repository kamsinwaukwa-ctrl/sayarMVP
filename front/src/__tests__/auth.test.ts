/**
 * Authentication Tests for Sayar Frontend
 * Tests authentication hooks and API integration
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { ReactNode } from 'react'
import { useAuth, AuthProvider } from '../hooks/useAuth'
import { apiClient } from '../lib/api-client'

// Mock the API client
vi.mock('../lib/api-client', () => ({
  apiClient: {
    login: vi.fn(),
    register: vi.fn(),
    getCurrentUser: vi.fn(),
    logout: vi.fn(),
    setAuthToken: vi.fn(),
    isAuthenticated: vi.fn(),
  },
}))

const mockApiClient = vi.mocked(apiClient)

// Test wrapper component
const wrapper = ({ children }: { children: ReactNode }) => (
  <AuthProvider>{children}</AuthProvider>
)

describe('useAuth', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Mock localStorage
    Object.defineProperty(window, 'localStorage', {
      value: {
        getItem: vi.fn(),
        setItem: vi.fn(),
        removeItem: vi.fn(),
        clear: vi.fn(),
      },
      writable: true,
    })
  })

  it('should initialize with loading state', () => {
    mockApiClient.isAuthenticated.mockReturnValue(false)
    
    const { result } = renderHook(() => useAuth(), { wrapper })
    
    expect(result.current.loading).toBe(true)
    expect(result.current.user).toBe(null)
    expect(result.current.isAuthenticated).toBe(false)
  })

  it('should handle successful login', async () => {
    const mockUser = {
      id: '123',
      name: 'Test User',
      email: 'test@example.com',
      role: 'admin' as const,
      merchant_id: '456',
    }

    const mockAuthResponse = {
      token: 'mock-token',
      user: mockUser,
    }

    mockApiClient.login.mockResolvedValue(mockAuthResponse)
    mockApiClient.isAuthenticated.mockReturnValue(false)

    const { result } = renderHook(() => useAuth(), { wrapper })

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    const loginCredentials = {
      email: 'test@example.com',
      password: 'password123',
    }

    await result.current.login(loginCredentials)

    expect(mockApiClient.login).toHaveBeenCalledWith(loginCredentials)
    expect(result.current.user).toEqual(mockUser)
    expect(result.current.isAuthenticated).toBe(true)
    expect(result.current.error).toBe(null)
  })

  it('should handle login failure', async () => {
    const mockError = new Error('Invalid credentials')
    mockApiClient.login.mockRejectedValue(mockError)
    mockApiClient.isAuthenticated.mockReturnValue(false)

    const { result } = renderHook(() => useAuth(), { wrapper })

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    const loginCredentials = {
      email: 'test@example.com',
      password: 'wrongpassword',
    }

    await expect(result.current.login(loginCredentials)).rejects.toThrow('Invalid credentials')
    
    expect(result.current.user).toBe(null)
    expect(result.current.isAuthenticated).toBe(false)
    expect(result.current.error).toBe('Invalid credentials')
  })

  it('should handle successful registration', async () => {
    const mockUser = {
      id: '123',
      name: 'Test User',
      email: 'test@example.com',
      role: 'admin' as const,
      merchant_id: '456',
    }

    const mockRegisterResponse = {
      token: 'mock-token',
      user: mockUser,
      merchant: {
        id: '456',
        name: 'Test Business',
        whatsapp_phone_e164: '+1234567890',
      },
    }

    mockApiClient.register.mockResolvedValue(mockRegisterResponse)
    mockApiClient.isAuthenticated.mockReturnValue(false)

    const { result } = renderHook(() => useAuth(), { wrapper })

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    const registerData = {
      name: 'Test User',
      email: 'test@example.com',
      password: 'password123',
      business_name: 'Test Business',
      whatsapp_phone_e164: '+1234567890',
    }

    await result.current.register(registerData)

    expect(mockApiClient.register).toHaveBeenCalledWith(registerData)
    expect(result.current.user).toEqual(mockUser)
    expect(result.current.isAuthenticated).toBe(true)
    expect(result.current.error).toBe(null)
  })

  it('should handle logout', async () => {
    // Setup authenticated state first
    const mockUser = {
      id: '123',
      name: 'Test User',
      email: 'test@example.com',
      role: 'admin' as const,
      merchant_id: '456',
    }

    mockApiClient.isAuthenticated.mockReturnValue(true)
    mockApiClient.getCurrentUser.mockResolvedValue(mockUser)

    const { result } = renderHook(() => useAuth(), { wrapper })

    await waitFor(() => {
      expect(result.current.user).toEqual(mockUser)
      expect(result.current.isAuthenticated).toBe(true)
    })

    // Test logout
    result.current.logout()

    expect(mockApiClient.logout).toHaveBeenCalled()
    expect(result.current.user).toBe(null)
    expect(result.current.isAuthenticated).toBe(false)
  })

  it('should restore user from stored token on initialization', async () => {
    const mockUser = {
      id: '123',
      name: 'Test User',
      email: 'test@example.com',
      role: 'admin' as const,
      merchant_id: '456',
    }

    mockApiClient.isAuthenticated.mockReturnValue(true)
    mockApiClient.getCurrentUser.mockResolvedValue(mockUser)

    const { result } = renderHook(() => useAuth(), { wrapper })

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
      expect(result.current.user).toEqual(mockUser)
      expect(result.current.isAuthenticated).toBe(true)
    })

    expect(mockApiClient.getCurrentUser).toHaveBeenCalled()
  })

  it('should clear error when calling clearError', async () => {
    mockApiClient.login.mockRejectedValue(new Error('Test error'))
    mockApiClient.isAuthenticated.mockReturnValue(false)

    const { result } = renderHook(() => useAuth(), { wrapper })

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    // Trigger an error
    try {
      await result.current.login({
        email: 'test@example.com',
        password: 'wrong',
      })
    } catch {
      // Expected to fail
    }

    expect(result.current.error).toBe('Test error')

    // Clear the error
    result.current.clearError()

    expect(result.current.error).toBe(null)
  })
})