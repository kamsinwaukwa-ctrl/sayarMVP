/**
 * SettingsLayout - Main layout component for settings page
 * Provides navigation and content structure
 */

import { ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import { cn } from '@/lib/utils'
import { useAuth } from '@/hooks/useAuth'
import { SETTINGS_TABS } from '@/constants/settings'
import { SettingsTab } from '@/types/settings'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { Card, CardContent } from '@/components/ui/Card'
import {
  Building,
  Store,
  MessageCircle,
  CreditCard,
  Users,
  Shield,
  LucideIcon,
  Sparkles,
} from 'lucide-react'

// Icon mapping
const ICON_MAP: Record<string, LucideIcon> = {
  Building,
  Store,
  MessageCircle,
  CreditCard,
  Users,
}

interface SettingsLayoutProps {
  children: ReactNode
  activeTab: SettingsTab
}

export function SettingsLayout({ children, activeTab }: SettingsLayoutProps) {
  const navigate = useNavigate()
  const { user } = useAuth()

  const handleTabChange = (value: string) => {
    navigate(`/settings/${value}`)
  }

  // Filter tabs based on user role
  const availableTabs = SETTINGS_TABS.filter((tab) => {
    if (tab.requiresAdmin && user?.role !== 'admin') {
      return false
    }
    return true
  })

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-slate-100">
      <div className="container mx-auto max-w-6xl px-4 py-8 space-y-8">
        {/* Enhanced Header */}
        <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-blue-600 via-purple-600 to-indigo-700 p-8 text-white">
          <div className="absolute inset-0 bg-black/10" />
          <div className="absolute top-0 right-0 w-64 h-64 bg-white/10 rounded-full -translate-y-32 translate-x-32" />
          <div className="absolute bottom-0 left-0 w-48 h-48 bg-white/5 rounded-full translate-y-24 -translate-x-24" />
          
          <div className="relative">
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-4 mb-4">
                  <div className="w-14 h-14 bg-white/20 rounded-2xl flex items-center justify-center backdrop-blur-sm">
                    <Shield className="w-8 h-8 text-white" />
                  </div>
                  <div>
                    <h1 className="text-4xl font-bold tracking-tight mb-2">
                      Settings
                    </h1>
                    <div className="flex items-center gap-2">
                      <Sparkles className="w-4 h-4 text-yellow-300" />
                      <span className="text-blue-100">Manage your business configuration</span>
                    </div>
                  </div>
                </div>
                
                <p className="text-blue-100 text-lg max-w-5xl leading-relaxed">
                  Configure your business settings, integrations, and team access with our intuitive dashboard.
                </p>
              </div>
              
             
            </div>
          </div>
        </div>

        {/* Enhanced Settings Tabs */}
        <Tabs value={activeTab} onValueChange={handleTabChange} className="space-y-8">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-2">
            <TabsList className={cn(
              "grid w-full h-auto p-1 bg-slate-50/50 rounded-xl",
              availableTabs.length === 1 && "grid-cols-1",
              availableTabs.length === 2 && "grid-cols-2",
              availableTabs.length === 3 && "grid-cols-3",
              availableTabs.length === 4 && "grid-cols-2 md:grid-cols-4",
              availableTabs.length === 5 && "grid-cols-2 md:grid-cols-5"
            )}>
              {availableTabs.map((tab) => {
                const Icon = ICON_MAP[tab.icon] || Building
                const isActive = activeTab === tab.id

                return (
                  <TabsTrigger
                    key={tab.id}
                    value={tab.id}
                    className={cn(
                      'group relative flex flex-col gap-3 p-4 h-auto text-sm rounded-lg transition-all duration-200',
                      'hover:bg-white/80 hover:shadow-sm',
                      'data-[state=active]:bg-white data-[state=active]:shadow-md data-[state=active]:border data-[state=active]:border-blue-100',
                      'data-[state=active]:ring-2 data-[state=active]:ring-blue-500/20'
                    )}
                  >
                    <div className="flex items-center justify-center w-10 h-10 rounded-xl bg-slate-100 group-data-[state=active]:bg-blue-100 transition-colors">
                      <Icon className={cn(
                        "w-5 h-5 transition-colors",
                        isActive ? "text-blue-600" : "text-slate-600"
                      )} />
                    </div>
                    
                    <div className="text-center">
                      <span className={cn(
                        "font-medium transition-colors",
                        isActive ? "text-blue-900" : "text-slate-700"
                      )}>
                        {tab.label}
                      </span>
                    </div>
                    
                    {isActive && (
                      <div className="absolute -top-1 -right-1 w-3 h-3 bg-blue-500 rounded-full animate-pulse" />
                    )}
                  </TabsTrigger>
                )
              })}
            </TabsList>
          </div>

          {/* Tab Content */}
          <div className="space-y-6">
            {availableTabs.map((tab) => (
              <TabsContent key={tab.id} value={tab.id} className="space-y-0">
                <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-8">
                  {children}
                </div>
              </TabsContent>
            ))}
          </div>
        </Tabs>
      </div>
    </div>
  )
}

/**
 * SettingsSection - Reusable section component for settings content
 */
interface SettingsSectionProps {
  title: string
  description: string
  children: ReactNode
  className?: string
}

export function SettingsSection({
  title,
  description,
  children,
  className,
}: SettingsSectionProps) {
  return (
    <div className={cn('space-y-6', className)}>
      <div className="flex items-start gap-4">
        <div className="w-1 h-8 bg-gradient-to-b from-blue-500 to-purple-500 rounded-full flex-shrink-0" />
        <div className="space-y-2 flex-1">
          <h2 className="text-xl font-bold text-slate-900">{title}</h2>
          <p className="text-slate-600 leading-relaxed">{description}</p>
        </div>
      </div>
      <div className="space-y-6">
        {children}
      </div>
    </div>
  )
}

/**
 * SettingsGrid - Grid layout for settings cards
 */
interface SettingsGridProps {
  children: ReactNode
  columns?: 1 | 2 | 3
}

export function SettingsGrid({ children, columns = 2 }: SettingsGridProps) {
  return (
    <div
      className={cn(
        'grid gap-6',
        columns === 1 && 'grid-cols-1',
        columns === 2 && 'grid-cols-1 md:grid-cols-2',
        columns === 3 && 'grid-cols-1 md:grid-cols-2 lg:grid-cols-3'
      )}
    >
      {children}
    </div>
  )
}

/**
 * SettingsCard - Individual settings card component
 */
interface SettingsCardProps {
  title: string
  description: string
  children: ReactNode
  className?: string
}

export function SettingsCard({
  title,
  description,
  children,
  className,
}: SettingsCardProps) {
  return (
    <Card className={cn(
      'group hover:shadow-lg transition-all duration-200 border-slate-200/60 hover:border-slate-300/60',
      className
    )}>
      <CardContent className="p-6 space-y-4">
        <div className="space-y-2">
          <h3 className="font-semibold text-slate-900 text-lg">{title}</h3>
          <p className="text-slate-600 leading-relaxed">{description}</p>
        </div>
        <div className="space-y-4">
          {children}
        </div>
      </CardContent>
    </Card>
  )
}