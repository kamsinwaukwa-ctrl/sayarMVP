import * as React from "react"
import { ChevronLeft, ChevronRight, MoreHorizontal } from "lucide-react"
import { cn } from "../../lib/utils"
import { Button } from "./Button"

interface PaginationProps extends React.HTMLAttributes<HTMLDivElement> {
  currentPage: number
  totalPages: number
  onPageChange: (page: number) => void
  pageSize?: number
  totalItems?: number
  pageSizeOptions?: number[]
  onPageSizeChange?: (pageSize: number) => void
  showPageSize?: boolean
  showInfo?: boolean
  disabled?: boolean
}

/**
 * Pagination component for table and list navigation
 * Provides page navigation with optional page size controls and info display
 */
const Pagination = React.forwardRef<HTMLDivElement, PaginationProps>(
  ({
    className,
    currentPage,
    totalPages,
    onPageChange,
    pageSize = 10,
    totalItems,
    pageSizeOptions = [5, 10, 20, 50],
    onPageSizeChange,
    showPageSize = false,
    showInfo = true,
    disabled = false,
    ...props
  }, ref) => {
    const getVisiblePages = (): (number | "ellipsis")[] => {
      const delta = 2
      const range: (number | "ellipsis")[] = []
      const rangeWithDots: (number | "ellipsis")[] = []

      for (
        let i = Math.max(2, currentPage - delta);
        i <= Math.min(totalPages - 1, currentPage + delta);
        i++
      ) {
        range.push(i)
      }

      if (currentPage - delta > 2) {
        rangeWithDots.push(1, "ellipsis")
      } else {
        rangeWithDots.push(1)
      }

      rangeWithDots.push(...range)

      if (currentPage + delta < totalPages - 1) {
        rangeWithDots.push("ellipsis", totalPages)
      } else {
        if (totalPages > 1) {
          rangeWithDots.push(totalPages)
        }
      }

      return rangeWithDots
    }

    const canPreviousPage = currentPage > 1
    const canNextPage = currentPage < totalPages

    const startItem = totalItems ? (currentPage - 1) * pageSize + 1 : 0
    const endItem = totalItems ? Math.min(currentPage * pageSize, totalItems) : 0

    return (
      <div
        ref={ref}
        className={cn(
          "flex items-center justify-between gap-4 py-4",
          className
        )}
        {...props}
      >
        {/* Left side - Info and page size */}
        <div className="flex items-center gap-4">
          {showInfo && totalItems !== undefined && (
            <div className="text-sm text-muted-foreground">
              Showing {startItem} to {endItem} of {totalItems} results
            </div>
          )}

          {showPageSize && onPageSizeChange && (
            <div className="flex items-center gap-2">
              <span className="text-sm text-muted-foreground">Show</span>
              <select
                value={pageSize}
                onChange={(e) => onPageSizeChange(Number(e.target.value))}
                disabled={disabled}
                className="text-sm border border-input bg-background px-2 py-1 rounded-md"
              >
                {pageSizeOptions.map((size) => (
                  <option key={size} value={size}>
                    {size}
                  </option>
                ))}
              </select>
              <span className="text-sm text-muted-foreground">per page</span>
            </div>
          )}
        </div>

        {/* Right side - Pagination controls */}
        <div className="flex items-center gap-1">
          <Button
            variant="outline"
            size="sm"
            onClick={() => onPageChange(currentPage - 1)}
            disabled={!canPreviousPage || disabled}
            className="gap-1"
          >
            <ChevronLeft className="h-4 w-4" />
            Previous
          </Button>

          <div className="flex items-center gap-1">
            {getVisiblePages().map((page, index) => (
              <React.Fragment key={index}>
                {page === "ellipsis" ? (
                  <div className="flex h-8 w-8 items-center justify-center">
                    <MoreHorizontal className="h-4 w-4" />
                  </div>
                ) : (
                  <Button
                    variant={page === currentPage ? "default" : "outline"}
                    size="sm"
                    onClick={() => onPageChange(page)}
                    disabled={disabled}
                    className="h-8 w-8 p-0"
                  >
                    {page}
                  </Button>
                )}
              </React.Fragment>
            ))}
          </div>

          <Button
            variant="outline"
            size="sm"
            onClick={() => onPageChange(currentPage + 1)}
            disabled={!canNextPage || disabled}
            className="gap-1"
          >
            Next
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      </div>
    )
  }
)
Pagination.displayName = "Pagination"

export { Pagination, type PaginationProps }