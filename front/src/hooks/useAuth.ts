import { createContext, useContext } from 'react'
import { AuthRequest, RegisterRequest } from '../types/api'
import { OnboardingProgressData } from '../types/onboarding'
import { Merchant } from '../types/merchant'

export interface User {
  id: string
  name: string
  email: string
  role: 'admin' | 'staff'
  merchant_id: string
}

export interface AuthContextType {
  user: User | null
  merchant: Merchant | null
  onboardingProgress: OnboardingProgressData | null
  loading: boolean
  isLoadingMerchant: boolean
  isLoadingOnboarding: boolean
  merchantLoadAttempted: boolean
  onboardingLoadAttempted: boolean
  authReady: boolean
  error: string | null
  isAuthenticated: boolean
  login: (credentials: AuthRequest) => Promise<void>
  register: (userData: RegisterRequest) => Promise<void>
  logout: () => void
  refreshUser: () => Promise<void>
  refreshOnboardingProgress: () => Promise<void>
  clearError: () => void
}

export const AuthContext = createContext<AuthContextType | undefined>(undefined)

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}