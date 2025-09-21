import * as React from "react"
import { ChevronUp, ChevronDown } from "lucide-react"
import { cn } from "@/lib/utils"
//import { Button } from "@/components/ui/Button"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { EmptyState } from "@/components/ui/empty-state"
import { Pagination } from "@/components/ui/pagination"
import { LoadingSpinner } from "@/components/ui/LoadingSpinner"

interface TableColumn<T> {
  key: keyof T | string
  header: string
  width?: string
  sortable?: boolean
  render?: (value: any, row: T, index: number) => React.ReactNode
  className?: string
  headerClassName?: string
}

interface SortConfig {
  key: string
  direction: "asc" | "desc"
}

interface PaginationConfig {
  page: number
  pageSize: number
  total: number
}

interface DataTableProps<T> {
  data: T[]
  columns: TableColumn<T>[]
  loading?: boolean
  emptyState?: {
    title: string
    description?: string
    action?: {
      label: string
      onClick: () => void
    }
  }
  pagination?: PaginationConfig
  onPageChange?: (page: number) => void
  onPageSizeChange?: (pageSize: number) => void
  sorting?: SortConfig
  onSortChange?: (sort: SortConfig) => void
  onRowClick?: (row: T, index: number) => void
  rowActions?: (row: T, index: number) => React.ReactNode
  selection?: {
    selectedRows: Set<string | number>
    onSelectionChange: (selectedRows: Set<string | number>) => void
    getRowId: (row: T) => string | number
  }
  className?: string
  variant?: "default" | "striped" | "bordered"
}

/**
 * DataTable component with sorting, pagination, and row actions
 * Provides enhanced table functionality for data display
 */
export function DataTable<T extends Record<string, any>>({
  data,
  columns,
  loading = false,
  emptyState,
  pagination,
  onPageChange,
  onPageSizeChange,
  sorting,
  onSortChange,
  onRowClick,
  rowActions,
  selection,
  className,
  variant = "default",
}: DataTableProps<T>) {
  const getCellValue = (row: T, column: TableColumn<T>): any => {
    if (typeof column.key === "string" && column.key.includes(".")) {
      return column.key.split(".").reduce((obj, key) => obj?.[key], row)
    }
    return row[column.key as keyof T]
  }

  const handleSort = (column: TableColumn<T>) => {
    if (!column.sortable || !onSortChange) return

    const key = column.key as string
    const newDirection =
      sorting?.key === key && sorting.direction === "asc" ? "desc" : "asc"

    onSortChange({ key, direction: newDirection })
  }

  const getSortIcon = (column: TableColumn<T>) => {
    if (!column.sortable) return null

    const key = column.key as string
    if (sorting?.key !== key) {
      return <div className="w-4 h-4" />
    }

    return sorting.direction === "asc" ? (
      <ChevronUp className="w-4 h-4" />
    ) : (
      <ChevronDown className="w-4 h-4" />
    )
  }

  const handleSelectAll = (checked: boolean) => {
    if (!selection) return

    if (checked) {
      const allIds = new Set(data.map(selection.getRowId))
      selection.onSelectionChange(allIds)
    } else {
      selection.onSelectionChange(new Set())
    }
  }

  const handleRowSelect = (rowId: string | number, checked: boolean) => {
    if (!selection) return

    const newSelection = new Set(selection.selectedRows)
    if (checked) {
      newSelection.add(rowId)
    } else {
      newSelection.delete(rowId)
    }
    selection.onSelectionChange(newSelection)
  }

  const isAllSelected = selection ?
    data.length > 0 && data.every(row => selection.selectedRows.has(selection.getRowId(row))) :
    false

  const isSomeSelected = selection ?
    data.some(row => selection.selectedRows.has(selection.getRowId(row))) :
    false

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <LoadingSpinner size="lg" />
      </div>
    )
  }

  if (!loading && data.length === 0) {
    return (
      <EmptyState
        title={emptyState?.title || "No data available"}
        description={emptyState?.description}
        action={emptyState?.action}
      />
    )
  }

  return (
    <div className={cn("space-y-4", className)}>
      <div className="rounded-md border">
        <Table className={cn(
          "w-full",
          variant === "striped" && "[&_tr:nth-child(even)]:bg-muted/50",
          variant === "bordered" && "border-collapse border border-border"
        )}>
          <TableHeader>
            <TableRow>
              {selection && (
                <TableHead className="w-12">
                  <input
                    type="checkbox"
                    checked={isAllSelected}
                    ref={(input) => {
                      if (input) input.indeterminate = isSomeSelected && !isAllSelected
                    }}
                    onChange={(e) => handleSelectAll(e.target.checked)}
                    className="rounded border-gray-300"
                  />
                </TableHead>
              )}

              {columns.map((column, index) => (
                <TableHead
                  key={index}
                  className={cn(
                    column.headerClassName,
                    column.sortable && "cursor-pointer select-none hover:bg-muted/50"
                  )}
                  style={{ width: column.width }}
                  onClick={() => handleSort(column)}
                >
                  <div className="flex items-center gap-2">
                    <span>{column.header}</span>
                    {getSortIcon(column)}
                  </div>
                </TableHead>
              ))}

              {rowActions && <TableHead className="w-12"></TableHead>}
            </TableRow>
          </TableHeader>

          <TableBody>
            {data.map((row, rowIndex) => {
              const rowId = selection?.getRowId(row)
              const isSelected = selection ? selection.selectedRows.has(rowId!) : false

              return (
                <TableRow
                  key={rowIndex}
                  className={cn(
                    onRowClick && "cursor-pointer hover:bg-muted/50",
                    isSelected && "bg-muted/50"
                  )}
                  onClick={() => onRowClick?.(row, rowIndex)}
                >
                  {selection && (
                    <TableCell>
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={(e) => handleRowSelect(rowId!, e.target.checked)}
                        onClick={(e) => e.stopPropagation()}
                        className="rounded border-gray-300"
                      />
                    </TableCell>
                  )}

                  {columns.map((column, colIndex) => {
                    const value = getCellValue(row, column)
                    const content = column.render ?
                      column.render(value, row, rowIndex) :
                      String(value ?? "")

                    return (
                      <TableCell
                        key={colIndex}
                        className={column.className}
                      >
                        {content}
                      </TableCell>
                    )
                  })}

                  {rowActions && (
                    <TableCell>
                      <div onClick={(e) => e.stopPropagation()}>
                        {rowActions(row, rowIndex)}
                      </div>
                    </TableCell>
                  )}
                </TableRow>
              )
            })}
          </TableBody>
        </Table>
      </div>

      {pagination && (
        <Pagination
          currentPage={pagination.page}
          totalPages={Math.ceil(pagination.total / pagination.pageSize)}
          pageSize={pagination.pageSize}
          totalItems={pagination.total}
          onPageChange={onPageChange || (() => {})}
          onPageSizeChange={onPageSizeChange}
          showPageSize={!!onPageSizeChange}
        />
      )}
    </div>
  )
}

export type { DataTableProps, TableColumn, SortConfig, PaginationConfig }