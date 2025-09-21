import * as React from "react"
import { cn } from "@/lib/utils"

interface ContentProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode
  size?: "sm" | "md" | "lg" | "xl" | "full"
  padding?: "none" | "sm" | "md" | "lg"
}

/**
 * Content component for consistent page content wrapper
 * Provides standard container widths and padding for page bodies
 */
const Content = React.forwardRef<HTMLDivElement, ContentProps>(
  ({
    className,
    children,
    size = "lg",
    padding = "md",
    ...props
  }, ref) => {
    const sizeClasses = {
      sm: "max-w-screen-sm",
      md: "max-w-screen-md",
      lg: "max-w-screen-lg",
      xl: "max-w-screen-xl",
      full: "max-w-full",
    }

    const paddingClasses = {
      none: "",
      sm: "px-4 py-4",
      md: "px-6 py-6",
      lg: "px-8 py-8",
    }

    return (
      <main
        ref={ref}
        className={cn(
          "mx-auto w-full",
          sizeClasses[size],
          paddingClasses[padding],
          className
        )}
        {...props}
      >
        {children}
      </main>
    )
  }
)
Content.displayName = "Content"

export { Content, type ContentProps }