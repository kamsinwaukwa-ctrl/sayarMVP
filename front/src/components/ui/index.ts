/**
 * UI Components - Complete shadcn/ui + custom component library
 * Export all components for easy importing across the Sayar platform
 */

// Legacy components (existing)
export { Button, buttonVariants } from './Button'

export { Input } from './Input'

export { Card, CardHeader, CardContent, CardTitle, CardDescription, CardFooter } from './Card'

export { Alert } from './Alert'

export { Typography } from './Typography'

export { Container } from './Container'

export { IconButton } from './IconButton'

export { LoadingSpinner } from './LoadingSpinner'

export { Select } from './Select'

// Icons
export {
  VisibilityIcon,
  VisibilityOffIcon,
  EmailIcon,
  LockIcon,
  PersonIcon,
  BusinessIcon,
  PhoneIcon,
  ExitToAppIcon,
  WhatsAppIcon,
  CheckCircleIcon,
} from './icons'
export type { IconProps } from './icons'

// Enhanced shadcn/ui components
export * from './skeleton'
export * from './separator'
export * from './toast'
export * from './toaster'
export * from './dialog'
export * from './alert-dialog'
export * from './sheet'
export * from './tooltip'
export * from './popover'
export * from './Badge'
export * from './avatar'
export * from './progress'
export * from './table'
export * from './tabs'
export * from './breadcrumb'
export * from './dropdown-menu'
export * from './context-menu'
export * from './command'
export * from './checkbox'
export * from './radio-group'
export * from './switch'
export * from './textarea'
export * from './accordion'
export * from './collapsible'

// Form system
export * from './form'
export * from './form-section'
export * from './form-actions'
export * from './label'

// Specialized components
export * from './empty-state'
export * from './stat-card'
export * from './filter-bar'
export * from './pagination'
export * from './description-list'
export * from './data-table'
export * from './command-palette'

// Hooks
export * from '@/hooks/use-toast'

// Export types for TypeScript support
export type { ButtonProps } from './Button'