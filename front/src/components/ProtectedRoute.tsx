import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '@/hooks/useAuth'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { AppShell } from '@/components/layout/app-shell'
import {
  Home,
  Settings,
  Store,
  MessageCircle,
  BarChart3,
  Package,
  Users,
  HelpCircle,
} from 'lucide-react'

interface ProtectedRouteProps {
  children?: React.ReactNode
}

const ProtectedRoute = ({ children }: ProtectedRouteProps) => {
  const { isAuthenticated, loading, merchant, merchantLoadAttempted, isLoadingMerchant, logout } = useAuth()
  const location = useLocation()

  // Sidebar configuration
  const sidebarSections = [
    {
      items: [
        {
          icon: Home,
          label: 'Dashboard',
          href: '/dashboard',
          active: location.pathname === '/dashboard' || location.pathname === '/',
        },
        {
          icon: Store,
          label: 'Products',
          href: '/products',
          active: location.pathname.startsWith('/products'),
        },
        {
          icon: Package,
          label: 'Orders',
          href: '/orders',
          active: location.pathname.startsWith('/orders'),
        },
        {
          icon: MessageCircle,
          label: 'Messages',
          href: '/messages',
          active: location.pathname.startsWith('/messages'),
        },
        {
          icon: BarChart3,
          label: 'Analytics',
          href: '/analytics',
          active: location.pathname.startsWith('/analytics'),
        },
        {
          icon: Users,
          label: 'Customers',
          href: '/customers',
          active: location.pathname.startsWith('/customers'),
        },
      ],
    },
    {
      title: 'Settings',
      items: [
        {
          icon: Settings,
          label: 'Settings',
          href: '/settings',
          active: location.pathname.startsWith('/settings'),
        },
        {
          icon: HelpCircle,
          label: 'Help & Support',
          href: '/help',
          active: location.pathname.startsWith('/help'),
        },
      ],
    },
  ]

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

  // Wrap all authenticated pages with AppShell layout (except onboarding)
  return (
    <AppShell sidebarSections={sidebarSections} onLogout={logout}>
      {children ? <>{children}</> : <Outlet />}
    </AppShell>
  )
}

export default ProtectedRoute