import * as React from "react"
import { cn } from "../../lib/utils"
import { Sidebar, type SidebarSection } from "./sidebar"
import { Header, type User } from "./header"

interface AppShellProps extends React.HTMLAttributes<HTMLDivElement> {
  user?: User
  sidebarSections: SidebarSection[]
  children: React.ReactNode
  sidebarCollapsed?: boolean
  onSidebarToggle?: () => void
  searchEnabled?: boolean
  onSearch?: (query: string) => void
  quickActions?: React.ReactNode
  notifications?: number
  onProfileClick?: () => void
  onSettingsClick?: () => void
  onLogout?: () => void
}

/**
 * AppShell component for complete application layout
 * Combines sidebar, header, and content area with responsive behavior
 */
const AppShell = React.forwardRef<HTMLDivElement, AppShellProps>(
  ({
    className,
    user,
    sidebarSections,
    children,
    sidebarCollapsed,
    onSidebarToggle,
    searchEnabled,
    onSearch,
    quickActions,
    notifications,
    onProfileClick,
    onSettingsClick,
    onLogout,
    ...props
  }, ref) => {
    return (
      <div
        ref={ref}
        className={cn("flex h-screen bg-background", className)}
        {...props}
      >
        {/* Sidebar */}
        <Sidebar
          sections={sidebarSections}
          collapsed={sidebarCollapsed}
          onToggle={onSidebarToggle}
        />

        {/* Main Content Area */}
        <div className="flex flex-1 flex-col overflow-hidden">
          {/* Header */}
          <Header
            user={user}
            searchEnabled={searchEnabled}
            onSearch={onSearch}
            quickActions={quickActions}
            notifications={notifications}
            onProfileClick={onProfileClick}
            onSettingsClick={onSettingsClick}
            onLogout={onLogout}
          />

          {/* Page Content */}
          <div className="flex-1 overflow-y-auto">
            {children}
          </div>
        </div>
      </div>
    )
  }
)
AppShell.displayName = "AppShell"

export { AppShell, type AppShellProps }