/**
 * Settings - Main settings page with secure credential management
 * Implements security-first approach with no credential exposure
 * Enhanced with modern, aesthetic design elements
 */

import { useEffect } from 'react'
import { useParams, Navigate } from 'react-router-dom'
import { useAuth } from '@/hooks/useAuth'
import { useRole, useSettingsPerformance } from '@/hooks/useSecureForm'
// Settings hooks are used in individual tab components
import { trackSettingsEvent, SETTINGS_EVENTS } from '@/lib/security'
import { SETTINGS_TABS } from '@/constants/settings'
import { SettingsTab } from '@/types/settings'
import { SettingsLayout } from '@/components/settings/SettingsLayout'
import { BrandSettingsTab } from '@/components/settings/tabs/BrandSettingsTab'
import { PaymentSettingsTab } from '@/components/settings/tabs/PaymentSettingsTab'
import { WhatsAppSettingsTab } from '@/components/settings/tabs/WhatsAppSettingsTab'
import { MetaCatalogSettingsTab } from '@/components/settings/tabs/MetaCatalogSettingsTab'
import { ProfileSettingsTab } from '@/components/settings/tabs/ProfileSettingsTab'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { AlertTriangle, Shield } from 'lucide-react'

export default function Settings() {
  const { tab = 'brand' } = useParams<{ tab: SettingsTab }>()
  const { user, loading: authLoading } = useAuth()
  const { role, canAccessAdvancedSettings } = useRole()

  // Performance monitoring
  useSettingsPerformance()

  // Redirect to brand tab if invalid tab
  const validTabs = SETTINGS_TABS.map(t => t.id)
  const activeTab = validTabs.includes(tab as SettingsTab) ? (tab as SettingsTab) : 'brand'

  // Check if user can access admin-only tabs
  const tabConfig = SETTINGS_TABS.find(t => t.id === activeTab)
  if (tabConfig?.requiresAdmin && !canAccessAdvancedSettings) {
    trackSettingsEvent(SETTINGS_EVENTS.UNAUTHORIZED_ACCESS_ATTEMPT, {
      tab: activeTab,
      role,
    })
    return <Navigate to="/settings/brand" replace />
  }

  // Track tab changes
  useEffect(() => {
    trackSettingsEvent(SETTINGS_EVENTS.TAB_CHANGED, {
      tab: activeTab,
      role,
    })
  }, [activeTab, role])

  if (authLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-slate-100 flex items-center justify-center">
        <div className="text-center space-y-4">
          <div className="w-16 h-16 bg-gradient-to-br from-blue-500 to-purple-600 rounded-2xl flex items-center justify-center mx-auto">
            <Shield className="w-8 h-8 text-white" />
          </div>
          <div className="space-y-2">
            <LoadingSpinner size="lg" />
            <p className="text-slate-600 font-medium">Loading your settings...</p>
          </div>
        </div>
      </div>
    )
  }

  if (!user) {
    return <Navigate to="/login" replace />
  }

  return (
    <SettingsLayout activeTab={activeTab}>
      <SettingsTabContent tab={activeTab} role={role} />
    </SettingsLayout>
  )
}

/**
 * Settings tab content renderer
 */
interface SettingsTabContentProps {
  tab: SettingsTab
  role: 'admin' | 'staff'
}

function SettingsTabContent({ tab, role }: SettingsTabContentProps) {
  switch (tab) {
    case 'brand':
      return <BrandSettingsTab role={role} />

    case 'payments':
      return <PaymentSettingsTab role={role} />

    case 'whatsapp':
      return <WhatsAppSettingsTab role={role} />

    case 'catalog':
      return <MetaCatalogSettingsTab role={role} />

    case 'profile':
      if (role !== 'admin') {
        return (
          <div className="text-center py-12">
            <div className="w-20 h-20 bg-red-100 rounded-2xl flex items-center justify-center mx-auto mb-6">
              <AlertTriangle className="w-10 h-10 text-red-600" />
            </div>
            <h3 className="text-xl font-semibold text-slate-900 mb-2">Access Restricted</h3>
            <p className="text-slate-600 max-w-md mx-auto">
              You need admin privileges to access profile settings. Contact your administrator for access.
            </p>
          </div>
        )
      }
      return <ProfileSettingsTab />

    default:
      return (
        <div className="text-center py-12">
          <div className="w-20 h-20 bg-orange-100 rounded-2xl flex items-center justify-center mx-auto mb-6">
            <AlertTriangle className="w-10 h-10 text-orange-600" />
          </div>
          <h3 className="text-xl font-semibold text-slate-900 mb-2">Settings Not Found</h3>
          <p className="text-slate-600 max-w-md mx-auto">
            The requested settings tab could not be found. Please select a valid tab from the navigation above.
          </p>
        </div>
      )
  }
}