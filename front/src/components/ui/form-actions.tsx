import * as React from "react"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/Button"

interface FormActionsProps extends React.HTMLAttributes<HTMLDivElement> {
  children?: React.ReactNode
  submitLabel?: string
  cancelLabel?: string
  onCancel?: () => void
  isSubmitting?: boolean
  submitDisabled?: boolean
}

/**
 * FormActions component for consistent form action layouts
 * Provides right-aligned Save/Cancel buttons with proper spacing and states
 */
const FormActions = React.forwardRef<HTMLDivElement, FormActionsProps>(
  ({
    className,
    children,
    submitLabel = "Save",
    cancelLabel = "Cancel",
    onCancel,
    isSubmitting = false,
    submitDisabled = false,
    ...props
  }, ref) => {
    return (
      <div
        ref={ref}
        className={cn(
          "flex items-center justify-end gap-3 pt-6 border-t border-border",
          className
        )}
        {...props}
      >
        {children || (
          <>
            {onCancel && (
              <Button
                type="button"
                variant="outline"
                onClick={onCancel}
                disabled={isSubmitting}
              >
                {cancelLabel}
              </Button>
            )}
            <Button
              type="submit"
              disabled={submitDisabled || isSubmitting}
              className="min-w-[100px]"
            >
              {isSubmitting ? "Saving..." : submitLabel}
            </Button>
          </>
        )}
      </div>
    )
  }
)
FormActions.displayName = "FormActions"

export { FormActions }