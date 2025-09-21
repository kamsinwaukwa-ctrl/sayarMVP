import * as React from "react"
import { cn } from "../../lib/utils"
import { Card, CardContent, CardHeader } from "./Card"

interface StatCardProps extends React.HTMLAttributes<HTMLDivElement> {
  title: string
  value: string | number
  description?: string
  icon?: React.ComponentType<{ className?: string }>
  trend?: {
    value: number
    label?: string
    direction: "up" | "down" | "neutral"
  }
  loading?: boolean
  variant?: "default" | "success" | "warning" | "error"
}

/**
 * StatCard component for displaying KPI metrics and dashboard statistics
 * Provides consistent metric visualization with optional trends and icons
 */
const StatCard = React.forwardRef<HTMLDivElement, StatCardProps>(
  ({
    className,
    title,
    value,
    description,
    icon: Icon,
    trend,
    loading = false,
    variant = "default",
    ...props
  }, ref) => {
    const trendIcon = trend?.direction === "up" ? "↗" : trend?.direction === "down" ? "↘" : "→"
    const trendColor = trend?.direction === "up" ? "text-green-600" :
                      trend?.direction === "down" ? "text-red-600" : "text-gray-600"

    const cardVariant = {
      default: "",
      success: "border-green-200 bg-green-50/50",
      warning: "border-yellow-200 bg-yellow-50/50",
      error: "border-red-200 bg-red-50/50",
    }[variant]

    if (loading) {
      return (
        <Card ref={ref} className={cn("animate-pulse", cardVariant, className)} {...props}>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <div className="h-4 w-24 bg-muted rounded"></div>
            {Icon && <div className="h-5 w-5 bg-muted rounded"></div>}
          </CardHeader>
          <CardContent>
            <div className="h-8 w-16 bg-muted rounded mb-2"></div>
            <div className="h-3 w-32 bg-muted rounded"></div>
          </CardContent>
        </Card>
      )
    }

    return (
      <Card ref={ref} className={cn(cardVariant, className)} {...props}>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <h3 className="text-sm font-medium text-muted-foreground">
            {title}
          </h3>
          {Icon && (
            <Icon className="h-5 w-5 text-muted-foreground" />
          )}
        </CardHeader>
        <CardContent>
          <div className="space-y-1">
            <div className="text-2xl font-bold text-foreground">
              {typeof value === "number" ? value.toLocaleString() : value}
            </div>

            <div className="flex items-center gap-2 text-xs">
              {trend && (
                <span className={cn("flex items-center gap-1 font-medium", trendColor)}>
                  <span>{trendIcon}</span>
                  <span>{Math.abs(trend.value)}%</span>
                  {trend.label && <span className="text-muted-foreground">({trend.label})</span>}
                </span>
              )}
              {description && (
                <span className="text-muted-foreground">
                  {description}
                </span>
              )}
            </div>
          </div>
        </CardContent>
      </Card>
    )
  }
)
StatCard.displayName = "StatCard"

export { StatCard, type StatCardProps }