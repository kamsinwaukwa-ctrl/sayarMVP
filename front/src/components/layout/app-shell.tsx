import * as React from "react"
import { cn } from "@/lib/utils"
import { Sidebar, type SidebarSection } from "@/components/layout/sidebar"
import { Header } from "@/components/layout/header"

interface AppShellProps extends React.HTMLAttributes<HTMLDivElement> {
  sidebarSections: SidebarSection[]
  children: React.ReactNode
  sidebarCollapsed?: boolean
  onSidebarToggle?: () => void
}

/**
 * AppShell component for complete application layout
 * Combines sidebar, header, and content area with responsive behavior
 */
const AppShell = React.forwardRef<HTMLDivElement, AppShellProps>(
  ({
    className,
    sidebarSections,
    children,
    sidebarCollapsed,
    onSidebarToggle,
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
          <Header />

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