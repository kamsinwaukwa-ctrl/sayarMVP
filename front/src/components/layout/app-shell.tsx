import * as React from "react"
import { cn } from "@/lib/utils"
import { Sidebar, type SidebarSection } from "@/components/layout/sidebar"

interface AppShellProps extends React.HTMLAttributes<HTMLDivElement> {
  sidebarSections: SidebarSection[]
  children: React.ReactNode
  sidebarCollapsed?: boolean
  onSidebarToggle?: () => void
  onLogout?: () => void
}

/**
 * AppShell component for application layout
 * Provides sidebar navigation and content area
 */
const AppShell = React.forwardRef<HTMLDivElement, AppShellProps>(
  ({
    className,
    sidebarSections,
    children,
    sidebarCollapsed,
    onSidebarToggle,
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
          onLogout={onLogout}
        />

        {/* Main Content Area */}
        <div className="flex-1 overflow-y-auto">
          {children}
        </div>
      </div>
    )
  }
)
AppShell.displayName = "AppShell"

export { AppShell, type AppShellProps }