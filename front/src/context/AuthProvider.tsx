import { ReactNode } from 'react'
import { AuthContext } from '@/hooks/useAuth'
import { useAuthState } from '@/hooks/useAuthState'

interface AuthProviderProps {
  children: ReactNode
}

export function AuthProvider({ children }: AuthProviderProps) {
  const value = useAuthState()

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}