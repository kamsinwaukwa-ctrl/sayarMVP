//import React from 'react'
import { Typography } from '@/components/ui/Typography'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/badge'
import { useAuth } from '@/hooks/useAuth'
import { Bell, LogOut, MessageCircle, Search } from 'lucide-react'

export interface AppHeaderProps {
  className?: string
}

export function AppHeader({ className = '' }: AppHeaderProps) {
  const { user, logout } = useAuth()

  const handleSignOut = () => logout()

  const getRoleDisplayName = (role: string) => (role === 'admin' ? 'Owner' : 'Staff')

  return (
    <header className={`sticky top-0 z-50 bg-white/80 backdrop-blur-md border-b border-slate-200/60 ${className}`}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo & Brand */}
          <div className="flex items-center space-x-3">
            <div className="flex items-center justify-center w-10 h-10 bg-gradient-to-br from-blue-600 to-purple-600 rounded-xl">
              <MessageCircle className="w-6 h-6 text-white" />
            </div>
            <div>
              <Typography variant="h6" className="font-bold text-slate-900">
                Sayar
              </Typography>
              <Typography variant="caption" className="text-slate-500">
                WhatsApp Commerce
              </Typography>
            </div>
          </div>

          {/* Search Bar */}
          <div className="hidden md:flex flex-1 max-w-md mx-8">
            <div className="relative w-full">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-slate-400" />
              <input
                type="text"
                placeholder="Search products, orders, customers..."
                className="w-full pl-10 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
          </div>

          {/* User Menu */}
          {user && (
            <div className="flex items-center space-x-4">
              <Button variant="ghost" size="icon" className="relative">
                <Bell className="w-5 h-5" />
                <span className="absolute -top-1 -right-1 w-3 h-3 bg-red-500 rounded-full"></span>
              </Button>

              <div className="flex items-center space-x-3">
                <div className="text-right">
                  <Typography variant="body2" className="font-medium text-slate-900">
                    {user.name}
                  </Typography>
                  <Badge variant="secondary" className="text-xs">
                    {getRoleDisplayName(user.role)}
                  </Badge>
                </div>

                <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-500 rounded-full flex items-center justify-center text-white font-semibold text-sm">
                  {user.name.charAt(0).toUpperCase()}
                </div>

                <Button 
                  variant="ghost"
                  size="sm"
                  onClick={handleSignOut}
                  className="text-slate-600 hover:text-slate-900"
                >
                  <LogOut className="w-4 h-4 mr-2" />
                  Sign Out
                </Button>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}

// Compat exports for existing imports
export type User = {
  id: string
  name: string
  email: string
  role: string
}

export type HeaderProps = AppHeaderProps

export { AppHeader as Header }

export default AppHeader


