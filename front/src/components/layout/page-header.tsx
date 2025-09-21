import * as React from "react"
import { cn } from "../../lib/utils"
import { Button } from "../ui/Button"
import { Breadcrumb, BreadcrumbItem, BreadcrumbLink, BreadcrumbList, BreadcrumbPage, BreadcrumbSeparator } from "../ui/breadcrumb"

interface BreadcrumbItem {
  label: string
  href?: string
}

interface PageHeaderProps extends React.HTMLAttributes<HTMLDivElement> {
  title: string
  description?: string
  breadcrumbs?: BreadcrumbItem[]
  primaryAction?: {
    label: string
    onClick: () => void
    variant?: "default" | "outline" | "secondary"
    icon?: React.ComponentType<{ className?: string }>
  }
  secondaryActions?: Array<{
    label: string
    onClick: () => void
    variant?: "default" | "outline" | "secondary" | "ghost"
    icon?: React.ComponentType<{ className?: string }>
  }>
  children?: React.ReactNode
}

/**
 * PageHeader component for consistent page layouts
 * Provides title, breadcrumbs, description, and action buttons
 */
const PageHeader = React.forwardRef<HTMLDivElement, PageHeaderProps>(
  ({
    className,
    title,
    description,
    breadcrumbs,
    primaryAction,
    secondaryActions,
    children,
    ...props
  }, ref) => {
    return (
      <div
        ref={ref}
        className={cn("space-y-4 pb-6 border-b border-border", className)}
        {...props}
      >
        {/* Breadcrumbs */}
        {breadcrumbs && breadcrumbs.length > 0 && (
          <Breadcrumb>
            <BreadcrumbList>
              {breadcrumbs.map((crumb, index) => (
                <React.Fragment key={index}>
                  <BreadcrumbItem>
                    {crumb.href ? (
                      <BreadcrumbLink href={crumb.href}>
                        {crumb.label}
                      </BreadcrumbLink>
                    ) : (
                      <BreadcrumbPage>{crumb.label}</BreadcrumbPage>
                    )}
                  </BreadcrumbItem>
                  {index < breadcrumbs.length - 1 && <BreadcrumbSeparator />}
                </React.Fragment>
              ))}
            </BreadcrumbList>
          </Breadcrumb>
        )}

        {/* Header Content */}
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          {/* Title and Description */}
          <div className="space-y-2 flex-1">
            <h1 className="text-3xl font-bold tracking-tight text-foreground">
              {title}
            </h1>
            {description && (
              <p className="text-muted-foreground max-w-2xl">
                {description}
              </p>
            )}
          </div>

          {/* Actions */}
          <div className="flex items-center gap-2 flex-wrap">
            {/* Secondary Actions */}
            {secondaryActions?.map((action, index) => (
              <Button
                key={index}
                variant={action.variant || "outline"}
                onClick={action.onClick}
                className="gap-2"
              >
                {action.icon && <action.icon className="h-4 w-4" />}
                {action.label}
              </Button>
            ))}

            {/* Primary Action */}
            {primaryAction && (
              <Button
                variant={primaryAction.variant || "default"}
                onClick={primaryAction.onClick}
                className="gap-2"
              >
                {primaryAction.icon && <primaryAction.icon className="h-4 w-4" />}
                {primaryAction.label}
              </Button>
            )}
          </div>
        </div>

        {/* Custom Content */}
        {children}
      </div>
    )
  }
)
PageHeader.displayName = "PageHeader"

export { PageHeader, type PageHeaderProps, type BreadcrumbItem }