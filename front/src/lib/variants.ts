import { cva } from 'class-variance-authority'

/**
 * Common variant patterns for consistent component styling
 * Uses class-variance-authority for type-safe variant definitions
 */

// Base component variants
export const cardVariants = cva(
  'rounded-xl border bg-card text-card-foreground shadow',
  {
    variants: {
      variant: {
        default: '',
        elevated: 'shadow-md',
        outlined: 'border-2',
        ghost: 'border-transparent shadow-none bg-transparent',
      },
      padding: {
        none: '',
        sm: 'p-4',
        md: 'p-6',
        lg: 'p-8',
      },
    },
    defaultVariants: {
      variant: 'default',
      padding: 'md',
    },
  }
)

// Status-based variants for commerce
export const statusVariants = cva(
  'inline-flex items-center rounded-md px-2 py-1 text-xs font-medium',
  {
    variants: {
      status: {
        // Order statuses
        pending: 'bg-yellow-50 text-yellow-700 border border-yellow-200',
        processing: 'bg-blue-50 text-blue-700 border border-blue-200',
        completed: 'bg-green-50 text-green-700 border border-green-200',
        cancelled: 'bg-red-50 text-red-700 border border-red-200',
        refunded: 'bg-purple-50 text-purple-700 border border-purple-200',

        // Payment statuses
        paid: 'bg-green-50 text-green-700 border border-green-200',
        unpaid: 'bg-gray-50 text-gray-700 border border-gray-200',
        failed: 'bg-red-50 text-red-700 border border-red-200',

        // Stock statuses
        'in-stock': 'bg-green-50 text-green-700 border border-green-200',
        'low-stock': 'bg-yellow-50 text-yellow-700 border border-yellow-200',
        'out-of-stock': 'bg-red-50 text-red-700 border border-red-200',

        // General statuses
        active: 'bg-green-50 text-green-700 border border-green-200',
        inactive: 'bg-gray-50 text-gray-700 border border-gray-200',
        draft: 'bg-gray-50 text-gray-700 border border-gray-200',
      },
    },
    defaultVariants: {
      status: 'pending',
    },
  }
)

// Button action variants
export const actionButtonVariants = cva(
  'inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-lg text-sm font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50',
  {
    variants: {
      intent: {
        primary: 'bg-primary text-primary-foreground hover:bg-primary/90',
        secondary: 'bg-secondary text-secondary-foreground hover:bg-secondary/80',
        success: 'bg-green-600 text-white hover:bg-green-700',
        warning: 'bg-yellow-600 text-white hover:bg-yellow-700',
        danger: 'bg-red-600 text-white hover:bg-red-700',
        ghost: 'hover:bg-accent hover:text-accent-foreground',
        outline: 'border border-input bg-background hover:bg-accent hover:text-accent-foreground',
      },
      size: {
        sm: 'h-8 px-3 text-xs',
        md: 'h-10 px-4',
        lg: 'h-12 px-6 text-base',
        icon: 'h-10 w-10',
      },
    },
    defaultVariants: {
      intent: 'primary',
      size: 'md',
    },
  }
)

// Input field variants
export const inputVariants = cva(
  'flex w-full rounded-lg border bg-background px-3 py-2 text-base ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50 md:text-sm',
  {
    variants: {
      variant: {
        default: 'border-input',
        error: 'border-destructive focus-visible:ring-destructive',
        success: 'border-green-500 focus-visible:ring-green-500',
      },
      size: {
        sm: 'h-8 px-2 text-sm',
        md: 'h-10 px-3',
        lg: 'h-12 px-4 text-base',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'md',
    },
  }
)

// Navigation item variants
export const navItemVariants = cva(
  'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
  {
    variants: {
      variant: {
        default: 'hover:bg-accent hover:text-accent-foreground',
        active: 'bg-accent text-accent-foreground',
        ghost: 'hover:bg-muted/50',
      },
      size: {
        sm: 'px-2 py-1.5 text-xs',
        md: 'px-3 py-2 text-sm',
        lg: 'px-4 py-3 text-base',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'md',
    },
  }
)

// Data table variants
export const tableVariants = cva('w-full', {
  variants: {
    variant: {
      default: '',
      striped: '[&_tr:nth-child(even)]:bg-muted/50',
      bordered: 'border border-border',
    },
    size: {
      sm: 'text-xs [&_td]:px-2 [&_td]:py-1.5 [&_th]:px-2 [&_th]:py-1.5',
      md: 'text-sm [&_td]:px-4 [&_td]:py-2 [&_th]:px-4 [&_th]:py-2',
      lg: 'text-base [&_td]:px-6 [&_td]:py-3 [&_th]:px-6 [&_th]:py-3',
    },
  },
  defaultVariants: {
    variant: 'default',
    size: 'md',
  },
})

// Layout container variants
export const containerVariants = cva('mx-auto w-full', {
  variants: {
    size: {
      sm: 'max-w-screen-sm',
      md: 'max-w-screen-md',
      lg: 'max-w-screen-lg',
      xl: 'max-w-screen-xl',
      '2xl': 'max-w-screen-2xl',
      full: 'max-w-full',
    },
    padding: {
      none: '',
      sm: 'px-4',
      md: 'px-6',
      lg: 'px-8',
    },
  },
  defaultVariants: {
    size: 'lg',
    padding: 'md',
  },
})