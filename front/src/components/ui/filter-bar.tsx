import * as React from "react"
import { X } from "lucide-react"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/Button"
import { Badge } from "@/components/ui/Badge"

interface Filter {
  id: string
  label: string
  value: string
}

interface FilterBarProps extends React.HTMLAttributes<HTMLDivElement> {
  filters: Filter[]
  onRemoveFilter: (filterId: string) => void
  onClearAll: () => void
  showClearAll?: boolean
  emptyMessage?: string
}

/**
 * FilterBar component for displaying active filters with removal options
 * Provides consistent filter chip UI for table and list filtering
 */
const FilterBar = React.forwardRef<HTMLDivElement, FilterBarProps>(
  ({
    className,
    filters,
    onRemoveFilter,
    onClearAll,
    showClearAll = true,
    emptyMessage = "No filters applied",
    ...props
  }, ref) => {
    const hasFilters = filters.length > 0

    if (!hasFilters) {
      return (
        <div
          ref={ref}
          className={cn("text-sm text-muted-foreground py-2", className)}
          {...props}
        >
          {emptyMessage}
        </div>
      )
    }

    return (
      <div
        ref={ref}
        className={cn(
          "flex items-center gap-2 py-2 flex-wrap",
          className
        )}
        {...props}
      >
        <span className="text-sm font-medium text-foreground">
          Filters:
        </span>

        <div className="flex items-center gap-2 flex-wrap">
          {filters.map((filter) => (
            <Badge
              key={filter.id}
              variant="secondary"
              className="gap-1 pr-1"
            >
              <span className="text-xs">
                {filter.label}: {filter.value}
              </span>
              <Button
                variant="ghost"
                size="icon"
                className="h-4 w-4 p-0 hover:bg-destructive hover:text-destructive-foreground"
                onClick={() => onRemoveFilter(filter.id)}
                aria-label={`Remove ${filter.label} filter`}
              >
                <X className="h-3 w-3" />
              </Button>
            </Badge>
          ))}
        </div>

        {showClearAll && filters.length > 1 && (
          <Button
            variant="ghost"
            size="sm"
            onClick={onClearAll}
            className="h-6 px-2 text-xs"
          >
            Clear all
          </Button>
        )}
      </div>
    )
  }
)
FilterBar.displayName = "FilterBar"

export { FilterBar, type FilterBarProps, type Filter }