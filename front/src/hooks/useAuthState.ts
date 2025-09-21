import { useState, useEffect } from 'react'
import { apiClient, ApiClientError } from '@/lib/api-client'
import { onboardingApi } from '@/lib/api/onboarding'
import { AuthRequest, RegisterRequest } from '@/types/api'
import { User, AuthContextType } from '@/hooks/useAuth'
import { Merchant } from '@/types/merchant'
import { OnboardingProgressData } from '@/types/onboarding'

export function useAuthState(): AuthContextType {
  const [user, setUser] = useState<User | null>(null)
  const [merchant, setMerchant] = useState<Merchant | null>(null)
  const [onboardingProgress, setOnboardingProgress] = useState<OnboardingProgressData | null>(null)
  const [loading, setLoading] = useState(true)
  const [isLoadingMerchant, setIsLoadingMerchant] = useState(false)
  const [isLoadingOnboarding, setIsLoadingOnboarding] = useState(false)
  const [merchantLoadAttempted, setMerchantLoadAttempted] = useState(false)
  const [onboardingLoadAttempted, setOnboardingLoadAttempted] = useState(false)
  const [authReady, setAuthReady] = useState(false)
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
        // Mark auth as ready after successful user fetch
        setAuthReady(true)
        // Also attempt to fetch merchant and onboarding progress in background
        fetchMerchantWithBackoff()
        fetchOnboardingProgressWithBackoff()
      } else {
        // No token, mark auth ready (for unauthenticated state)
        setAuthReady(true)
      }
    } catch (error) {
      console.warn('Auth initialization failed:', error)
      // Clear invalid token
      apiClient.setAuthToken(null)
      // Mark auth ready even on failure
      setAuthReady(true)
    } finally {
      setLoading(false)
    }
  }

  const fetchMerchantWithBackoff = async (retryCount = 0) => {
    const maxRetries = 3
    const baseDelay = 1000 // 1 second

    setIsLoadingMerchant(true)

    try {
      const merchantData = await apiClient.getCurrentMerchant()
      setMerchant(merchantData)
    } catch (error) {
      console.warn('Merchant fetch failed:', error)

      // Silent retry with exponential backoff
      if (retryCount < maxRetries) {
        const delay = baseDelay * Math.pow(2, retryCount)
        setTimeout(() => {
          fetchMerchantWithBackoff(retryCount + 1)
        }, delay)
        return // Don't set loading states yet
      }

      // Max retries reached - silently fail (no UI error)
      console.warn('Max merchant fetch retries reached')
    } finally {
      setIsLoadingMerchant(false)
      setMerchantLoadAttempted(true)
    }
  }

  const fetchOnboardingProgressWithBackoff = async (retryCount = 0) => {
    const maxRetries = 3
    const baseDelay = 1000 // 1 second

    setIsLoadingOnboarding(true)

    try {
      const progressData = await onboardingApi.getOnboardingProgress()
      setOnboardingProgress(progressData)
    } catch (error) {
      console.warn('Onboarding progress fetch failed:', error)

      // Silent retry with exponential backoff
      if (retryCount < maxRetries) {
        const delay = baseDelay * Math.pow(2, retryCount)
        setTimeout(() => {
          fetchOnboardingProgressWithBackoff(retryCount + 1)
        }, delay)
        return // Don't set loading states yet
      }

      // Max retries reached - silently fail (no UI error)
      console.warn('Max onboarding progress fetch retries reached')
    } finally {
      setIsLoadingOnboarding(false)
      setOnboardingLoadAttempted(true)
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

      // Mark auth as ready after successful login
      setAuthReady(true)

      // Now fetch merchant and onboarding progress sequentially
      // No setTimeout needed - the unified token management eliminates race conditions
      await fetchMerchantWithBackoff()
      await fetchOnboardingProgressWithBackoff()
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

      // Mark auth as ready after successful registration
      setAuthReady(true)

      // Now fetch merchant and onboarding progress sequentially
      // No setTimeout needed - the unified token management eliminates race conditions
      await fetchMerchantWithBackoff()
      await fetchOnboardingProgressWithBackoff()
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
      setMerchant(null)
      setOnboardingProgress(null)
      setMerchantLoadAttempted(false)
      setOnboardingLoadAttempted(false)
      setAuthReady(false)
      setError(null)
    } catch (error) {
      console.warn('Logout error (ignored):', error)
    } finally {
      setLoading(false)
      setIsLoadingMerchant(false)
      setIsLoadingOnboarding(false)
      // Mark auth ready after logout cleanup
      setAuthReady(true)
    }
  }

  const refreshOnboardingProgress = async () => {
    try {
      const progressData = await onboardingApi.getOnboardingProgress()
      setOnboardingProgress(progressData)
      setError(null)
    } catch (error) {
      console.error('Failed to refresh onboarding progress:', error)
      throw error
    }
  }

  const clearError = () => {
    setError(null)
  }

  return {
    user,
    merchant,
    onboardingProgress,
    loading,
    isLoadingMerchant,
    isLoadingOnboarding,
    merchantLoadAttempted,
    onboardingLoadAttempted,
    authReady,
    error,
    isAuthenticated: !!user,
    login,
    register,
    logout,
    refreshUser,
    refreshOnboardingProgress,
    clearError,
  }
}



