import * as React from "react"
import { ChevronLeft, ChevronRight } from "lucide-react"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/Button"
import { Badge } from "@/components/ui/badge"

interface NavItem {
  label: string
  href: string
  icon?: React.ComponentType<{ className?: string }>
  active?: boolean
  badge?: string | number
  children?: Omit<NavItem, 'children'>[]
}

interface SidebarSection {
  title?: string
  items: NavItem[]
}

interface SidebarProps extends React.HTMLAttributes<HTMLDivElement> {
  sections: SidebarSection[]
  collapsed?: boolean
  onToggle?: () => void
  defaultCollapsed?: boolean
  onLogout?: () => void
}

/**
 * Sidebar component for main navigation
 * Provides collapsible navigation with sections, icons, and badges
 */
const Sidebar = React.forwardRef<HTMLDivElement, SidebarProps>(
  ({
    className,
    sections,
    collapsed: controlledCollapsed,
    onToggle,
    defaultCollapsed = false,
    onLogout,
    ...props
  }, ref) => {
    const [internalCollapsed, setInternalCollapsed] = React.useState(defaultCollapsed)

    const collapsed = controlledCollapsed !== undefined ? controlledCollapsed : internalCollapsed

    const handleToggle = () => {
      if (onToggle) {
        onToggle()
      } else {
        setInternalCollapsed(!internalCollapsed)
      }
    }

    return (
      <div
        ref={ref}
        className={cn(
          "sticky top-0 z-40 flex h-screen flex-col border-r border-border bg-background transition-all duration-300",
          collapsed ? "w-16" : "w-64",
          className
        )}
        {...props}
      >
        {/* Toggle Button */}
        <div className="flex h-14 items-center justify-between px-3 border-b border-border">
          <div className="flex items-center gap-2">
            <img 
              src="/logo.png" 
              alt="Sayar" 
              className="h-8 w-8 object-contain"
            />
            {!collapsed && (
              <span className="font-semibold text-foreground">Sayar</span>
            )}
          </div>
          <Button
            variant="ghost"
            size="icon"
            onClick={handleToggle}
            className="h-8 w-8"
          >
            {collapsed ? (
              <ChevronRight className="h-4 w-4" />
            ) : (
              <ChevronLeft className="h-4 w-4" />
            )}
          </Button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 overflow-y-auto py-4">
          <div className="space-y-6">
            {sections.map((section, sectionIndex) => (
              <div key={sectionIndex} className="px-3">
                {section.title && !collapsed && (
                  <h4 className="mb-2 px-2 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                    {section.title}
                  </h4>
                )}

                <div className="space-y-1">
                  {section.items.map((item, itemIndex) => (
                    <NavItemComponent
                      key={itemIndex}
                      item={item}
                      collapsed={collapsed}
                    />
                  ))}
                </div>
              </div>
            ))}
          </div>
        </nav>

        {/* Logout Button */}
        {onLogout && (
          <div className="border-t border-border p-3">
            <Button
              variant="ghost"
              onClick={onLogout}
              className={cn(
                "w-full justify-start text-muted-foreground hover:text-foreground hover:bg-accent",
                collapsed && "justify-center px-2"
              )}
            >
              <svg
                className="h-5 w-5 flex-shrink-0"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"
                />
              </svg>
              {!collapsed && <span className="ml-3">Sign Out</span>}
            </Button>
          </div>
        )}
      </div>
    )
  }
)
Sidebar.displayName = "Sidebar"

interface NavItemComponentProps {
  item: NavItem
  collapsed: boolean
  level?: number
}

const NavItemComponent: React.FC<NavItemComponentProps> = ({
  item,
  collapsed,
  level = 0
}) => {
  const [expanded, setExpanded] = React.useState(false)
  const hasChildren = item.children && item.children.length > 0

  const ItemContent = () => (
    <>
      {item.icon && (
        <item.icon className="h-5 w-5 flex-shrink-0" />
      )}
      {!collapsed && (
        <>
          <span className="flex-1 truncate">{item.label}</span>
          {item.badge && (
            <Badge variant="secondary" className="h-5 px-1.5 text-xs">
              {item.badge}
            </Badge>
          )}
          {hasChildren && (
            <ChevronRight
              className={cn(
                "h-4 w-4 transition-transform",
                expanded && "rotate-90"
              )}
            />
          )}
        </>
      )}
    </>
  )

  if (hasChildren) {
    return (
      <div>
        <button
          onClick={() => setExpanded(!expanded)}
          className={cn(
            "flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors hover:bg-accent hover:text-accent-foreground",
            item.active && "bg-accent text-accent-foreground",
            collapsed && "justify-center"
          )}
          style={{ paddingLeft: collapsed ? undefined : `${12 + level * 16}px` }}
        >
          <ItemContent />
        </button>

        {expanded && !collapsed && (
          <div className="mt-1 space-y-1">
            {item.children?.map((child, childIndex) => (
              <NavItemComponent
                key={childIndex}
                item={child}
                collapsed={collapsed}
                level={level + 1}
              />
            ))}
          </div>
        )}
      </div>
    )
  }

  return (
    <a
      href={item.href}
      className={cn(
        "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors hover:bg-accent hover:text-accent-foreground",
        item.active && "bg-accent text-accent-foreground",
        collapsed && "justify-center"
      )}
      style={{ paddingLeft: collapsed ? undefined : `${12 + level * 16}px` }}
    >
      <ItemContent />
    </a>
  )
}

export { Sidebar, type SidebarProps, type SidebarSection, type NavItem }