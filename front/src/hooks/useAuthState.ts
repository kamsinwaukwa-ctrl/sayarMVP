import { useState, useEffect } from 'react'
import { apiClient, ApiClientError } from '../lib/api-client'
import { AuthRequest, RegisterRequest } from '../types/api'
import { User, AuthContextType } from './useAuth'

export function useAuthState(): AuthContextType {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Initialize auth state on mount
  useEffect(() => {
    initializeAuth()
  }, [])

  const initializeAuth = async () => {
    setLoading(true)
    setError(null)

    try {
      // Check if we have a stored token
      if (apiClient.isAuthenticated()) {
        // Try to get current user
        await refreshUser()
      }
    } catch (error) {
      console.warn('Auth initialization failed:', error)
      // Clear invalid token
      apiClient.setAuthToken(null)
    } finally {
      setLoading(false)
    }
  }

  const refreshUser = async () => {
    try {
      const userData = await apiClient.getCurrentUser()
      setUser(userData)
      setError(null)
    } catch (error) {
      console.error('Failed to refresh user:', error)
      
      if (error instanceof ApiClientError && error.status === 401) {
        // Token is invalid, clear auth state
        apiClient.setAuthToken(null)
        setUser(null)
      }
      
      throw error
    }
  }

  const login = async (credentials: AuthRequest) => {
    setLoading(true)
    setError(null)

    try {
      const response = await apiClient.login(credentials)
      
      // Set user from response
      if (response.user) {
        setUser(response.user)
      }
    } catch (error) {
      if (error instanceof ApiClientError) {
        setError(error.message)
      } else {
        setError('Login failed. Please try again.')
      }
      throw error
    } finally {
      setLoading(false)
    }
  }

  const register = async (userData: RegisterRequest) => {
    setLoading(true)
    setError(null)

    try {
      const response = await apiClient.register(userData)
      
      // Set user from response
      if (response.user) {
        setUser(response.user)
      }
    } catch (error) {
      if (error instanceof ApiClientError) {
        setError(error.message)
      } else {
        setError('Registration failed. Please try again.')
      }
      throw error
    } finally {
      setLoading(false)
    }
  }

  const logout = () => {
    setLoading(true)
    
    try {
      // Clear auth state
      apiClient.logout()
      setUser(null)
      setError(null)
    } catch (error) {
      console.warn('Logout error (ignored):', error)
    } finally {
      setLoading(false)
    }
  }

  const clearError = () => {
    setError(null)
  }

  return {
    user,
    loading,
    error,
    isAuthenticated: !!user,
    login,
    register,
    logout,
    refreshUser,
    clearError,
  }
}



