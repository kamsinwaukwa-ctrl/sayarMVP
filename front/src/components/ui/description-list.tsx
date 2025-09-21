import * as React from "react"
import { cn } from "@/lib/utils"

interface DescriptionListProps extends React.HTMLAttributes<HTMLDListElement> {
  items: Array<{
    term: string
    description: React.ReactNode
    className?: string
  }>
  orientation?: "horizontal" | "vertical"
  variant?: "default" | "bordered" | "striped"
}

/**
 * DescriptionList component for displaying read-only entity details
 * Provides consistent formatting for key-value data display
 */
const DescriptionList = React.forwardRef<HTMLDListElement, DescriptionListProps>(
  ({
    className,
    items,
    orientation = "horizontal",
    variant = "default",
    ...props
  }, ref) => {
    const listClasses = cn(
      "space-y-3",
      {
        // Variant styles
        "divide-y divide-border": variant === "bordered",
        "[&>div:nth-child(even)]:bg-muted/30 [&>div]:px-3 [&>div]:py-2 [&>div]:rounded-md":
          variant === "striped",
      },
      className
    )

    const itemClasses = cn({
      // Orientation styles
      "flex items-start justify-between gap-4": orientation === "horizontal",
      "space-y-1": orientation === "vertical",
      // Variant spacing adjustments
      "py-3 first:pt-0 last:pb-0": variant === "bordered",
    })

    const termClasses = cn(
      "text-sm font-medium text-foreground",
      {
        "min-w-0 flex-shrink-0 basis-1/3": orientation === "horizontal",
        "": orientation === "vertical",
      }
    )

    const descriptionClasses = cn(
      "text-sm text-muted-foreground",
      {
        "min-w-0 flex-1 text-right": orientation === "horizontal",
        "": orientation === "vertical",
      }
    )

    return (
      <dl ref={ref} className={listClasses} {...props}>
        {items.map((item, index) => (
          <div key={index} className={cn(itemClasses, item.className)}>
            <dt className={termClasses}>{item.term}</dt>
            <dd className={descriptionClasses}>{item.description}</dd>
          </div>
        ))}
      </dl>
    )
  }
)
DescriptionList.displayName = "DescriptionList"

export { DescriptionList, type DescriptionListProps }