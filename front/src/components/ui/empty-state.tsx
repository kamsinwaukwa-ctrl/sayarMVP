import * as React from "react"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/Button"

interface EmptyStateProps extends React.HTMLAttributes<HTMLDivElement> {
  icon?: React.ComponentType<{ className?: string }>
  title: string
  description?: string
  action?: {
    label: string
    onClick: () => void
    variant?: "default" | "outline" | "secondary"
  }
  children?: React.ReactNode
}

/**
 * EmptyState component for displaying empty collections with call-to-action
 * Provides consistent empty state UI across the application
 */
const EmptyState = React.forwardRef<HTMLDivElement, EmptyStateProps>(
  ({
    className,
    icon: Icon,
    title,
    description,
    action,
    children,
    ...props
  }, ref) => {
    return (
      <div
        ref={ref}
        className={cn(
          "flex flex-col items-center justify-center py-12 px-4 text-center",
          className
        )}
        {...props}
      >
        {Icon && (
          <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-muted">
            <Icon className="h-8 w-8 text-muted-foreground" />
          </div>
        )}

        <div className="space-y-2 mb-6">
          <h3 className="text-lg font-semibold text-foreground">
            {title}
          </h3>
          {description && (
            <p className="text-sm text-muted-foreground max-w-md">
              {description}
            </p>
          )}
        </div>

        {action && (
          <Button
            onClick={action.onClick}
            variant={action.variant || "default"}
            className="min-w-[120px]"
          >
            {action.label}
          </Button>
        )}

        {children}
      </div>
    )
  }
)
EmptyState.displayName = "EmptyState"

export { EmptyState, type EmptyStateProps }