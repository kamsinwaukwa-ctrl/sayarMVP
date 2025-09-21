import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '@/hooks/useAuth'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'

interface ProtectedRouteProps {
  children?: React.ReactNode
}

const ProtectedRoute = ({ children }: ProtectedRouteProps) => {
  const { isAuthenticated, loading, merchant, merchantLoadAttempted, isLoadingMerchant } = useAuth()
  const location = useLocation()

  // Always check auth first
  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <LoadingSpinner size="lg" />
      </div>
    )
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  // Handle onboarding routes differently
  const isOnboarding = location.pathname.startsWith('/onboarding')

  if (isOnboarding) {
    // For onboarding: allow access once we've attempted to load merchant (even if failed)
    if (!merchantLoadAttempted) {
      return (
        <div className="flex min-h-screen items-center justify-center">
          <LoadingSpinner size="lg" />
        </div>
      )
    }
    // Render onboarding even if merchant is null (neutral fallback)
    return children ? <>{children}</> : <Outlet />
  }

  // For non-onboarding routes: wait for merchant to be loaded
  if (!merchant || isLoadingMerchant) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <LoadingSpinner size="lg" />
      </div>
    )
  }

  // Support both children pattern (legacy) and Outlet pattern (new)
  return children ? <>{children}</> : <Outlet />
}

export default ProtectedRoute