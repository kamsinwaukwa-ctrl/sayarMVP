// Tailwind UI Component Library
// Export all components for easy importing

export { Button } from './Button'
export type { ButtonProps } from './Button'

export { Input } from './Input'
export type { InputProps } from './Input'

export { Card, CardContent } from './Card'
export type { CardProps, CardContentProps } from './Card'

export { Alert } from './Alert'
export type { AlertProps } from './Alert'

export { Typography } from './Typography'
export type { TypographyProps } from './Typography'

export { Container } from './Container'
export type { ContainerProps } from './Container'

export { IconButton } from './IconButton'
export type { IconButtonProps } from './IconButton'

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

// Re-export all components as default exports for compatibility
export { default as ButtonDefault } from './Button'
export { default as InputDefault } from './Input'
export { default as CardDefault } from './Card'
export { default as AlertDefault } from './Alert'
export { default as TypographyDefault } from './Typography'
export { default as ContainerDefault } from './Container'
export { default as IconButtonDefault } from './IconButton'