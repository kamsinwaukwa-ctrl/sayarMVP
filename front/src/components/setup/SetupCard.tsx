/**
 * SetupCard - Reusable card component for dashboard setup tasks
 * Shows progress, description, and CTA for each setup step
 */

import { useState } from 'react'
import { Check, ChevronRight, AlertCircle } from 'lucide-react'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/badge'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog'
import { cn } from '@/lib/utils'

export interface SetupCardProps {
  title: string
  description: string
  icon: React.ReactNode
  completed: boolean
  disabled?: boolean
  disabledReason?: string
  onAction: () => void | Promise<void>
  actionLabel?: string
  children?: React.ReactNode | ((props: { onComplete: () => void }) => React.ReactNode) // For embedding form content in dialog
  onComplete?: () => void // Callback when setup is completed
}

export function SetupCard({
  title,
  description,
  icon,
  completed,
  disabled = false,
  disabledReason,
  onAction,
  actionLabel,
  children,
  onComplete
}: SetupCardProps) {
  const [isDialogOpen, setIsDialogOpen] = useState(false)
  const [isLoading, setIsLoading] = useState(false)

  const handleComplete = () => {
    setIsDialogOpen(false)
    onComplete?.()
  }

  const handleAction = async () => {
    if (disabled) return

    if (children) {
      // If children provided, open dialog with embedded content
      setIsDialogOpen(true)
    } else {
      // Otherwise, execute action directly
      setIsLoading(true)
      try {
        await onAction()
      } finally {
        setIsLoading(false)
      }
    }
  }

  const getStatusBadge = () => {
    if (completed) {
      return (
        <Badge variant="secondary" className="bg-green-100 text-green-700 border-green-200">
          <Check className="w-3 h-3 mr-1" />
          Completed
        </Badge>
      )
    }

    if (disabled) {
      return (
        <Badge variant="outline" className="bg-gray-50 text-gray-500 border-gray-200">
          <AlertCircle className="w-3 h-3 mr-1" />
          Requires setup
        </Badge>
      )
    }

    return (
      <Badge variant="outline" className="bg-blue-50 text-blue-600 border-blue-200">
        Setup needed
      </Badge>
    )
  }

  const getActionButton = () => {
    if (completed) {
      // Hide edit button for completed cards - users should go to settings to edit
      return null
    }

    if (disabled) {
      return (
        <Button
          variant="outline"
          size="sm"
          disabled
          className="cursor-not-allowed"
        >
          {disabledReason || 'Requires other setup'}
        </Button>
      )
    }

    return (
      <Button
        onClick={handleAction}
        disabled={isLoading}
        size="sm"
      >
        {isLoading ? 'Loading...' : actionLabel || 'Set up'}
        <ChevronRight className="w-4 h-4 ml-1" />
      </Button>
    )
  }

  return (
    <>
      <Card className={cn(
        "transition-all duration-200 hover:shadow-md",
        completed && "bg-green-50 border-green-200",
        disabled && "opacity-75"
      )}>
        <div className="p-6">
          <div className="flex items-start justify-between">
            <div className="flex items-start space-x-4 flex-1">
              {/* Icon */}
              <div className={cn(
                "flex items-center justify-center w-10 h-10 rounded-lg",
                completed ? "bg-green-100 text-green-600" : "bg-blue-100 text-blue-600"
              )}>
                {completed ? <Check className="w-5 h-5" /> : icon}
              </div>

              {/* Content */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-3 mb-2">
                  <h3 className="text-lg font-semibold text-gray-900">
                    {title}
                  </h3>
                  {getStatusBadge()}
                </div>
                <p className="text-gray-600 text-sm leading-relaxed">
                  {description}
                </p>
              </div>
            </div>

            {/* Action Button */}
            <div className="ml-4 flex-shrink-0">
              {getActionButton()}
            </div>
          </div>
        </div>
      </Card>

      {/* Dialog for embedded content */}
      {children && (
        <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
          <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                {icon}
                {title}
              </DialogTitle>
              <DialogDescription>
                {description}
              </DialogDescription>
            </DialogHeader>
            <div className="mt-4">
              {children && typeof children === 'function' 
                ? children({ onComplete: handleComplete })
                : children
              }
            </div>
          </DialogContent>
        </Dialog>
      )}
    </>
  )
}

export default SetupCard