import React from 'react'

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'contained' | 'outlined' | 'text'
  size?: 'small' | 'medium' | 'large'
  color?: 'primary' | 'secondary' | 'error' | 'warning' | 'info' | 'success'
  fullWidth?: boolean
  startIcon?: React.ReactNode
  endIcon?: React.ReactNode
  loading?: boolean
  children: React.ReactNode
}

export const Button: React.FC<ButtonProps> = ({
  variant = 'contained',
  size = 'medium',
  color = 'primary',
  fullWidth = false,
  startIcon,
  endIcon,
  loading = false,
  disabled = false,
  className = '',
  children,
  ...props
}) => {
  const baseClasses = [
    'inline-flex items-center justify-center font-medium transition-all duration-standard',
    'focus:outline-none focus:ring-2 focus:ring-offset-2',
    'disabled:cursor-not-allowed',
    fullWidth && 'w-full',
  ].filter(Boolean).join(' ')

  const sizeClasses = {
    small: 'px-2 py-1 text-sm min-h-8',
    medium: 'px-4 py-2 text-sm min-h-9', 
    large: 'px-6 py-3 text-base min-h-11',
  }

  const getVariantClasses = () => {
    const colorMap = {
      primary: {
        contained: `bg-primary-main text-white hover:bg-primary-dark focus:ring-primary-main 
                   disabled:bg-grey-300 disabled:text-grey-500`,
        outlined: `border border-primary-main text-primary-main bg-transparent hover:bg-primary-50 
                  focus:ring-primary-main disabled:border-grey-300 disabled:text-grey-500`,
        text: `text-primary-main bg-transparent hover:bg-primary-50 focus:ring-primary-main 
              disabled:text-grey-500`,
      },
      secondary: {
        contained: `bg-secondary-main text-white hover:bg-secondary-dark focus:ring-secondary-main 
                   disabled:bg-grey-300 disabled:text-grey-500`,
        outlined: `border border-secondary-main text-secondary-main bg-transparent hover:bg-secondary-50 
                  focus:ring-secondary-main disabled:border-grey-300 disabled:text-grey-500`,
        text: `text-secondary-main bg-transparent hover:bg-secondary-50 focus:ring-secondary-main 
              disabled:text-grey-500`,
      },
      error: {
        contained: `bg-error-main text-white hover:bg-error-dark focus:ring-error-main 
                   disabled:bg-grey-300 disabled:text-grey-500`,
        outlined: `border border-error-main text-error-main bg-transparent hover:bg-error-50 
                  focus:ring-error-main disabled:border-grey-300 disabled:text-grey-500`,
        text: `text-error-main bg-transparent hover:bg-error-50 focus:ring-error-main 
              disabled:text-grey-500`,
      },
      warning: {
        contained: `bg-warning-main text-white hover:bg-warning-dark focus:ring-warning-main 
                   disabled:bg-grey-300 disabled:text-grey-500`,
        outlined: `border border-warning-main text-warning-main bg-transparent hover:bg-warning-50 
                  focus:ring-warning-main disabled:border-grey-300 disabled:text-grey-500`,
        text: `text-warning-main bg-transparent hover:bg-warning-50 focus:ring-warning-main 
              disabled:text-grey-500`,
      },
      info: {
        contained: `bg-info-main text-white hover:bg-info-dark focus:ring-info-main 
                   disabled:bg-grey-300 disabled:text-grey-500`,
        outlined: `border border-info-main text-info-main bg-transparent hover:bg-info-50 
                  focus:ring-info-main disabled:border-grey-300 disabled:text-grey-500`,
        text: `text-info-main bg-transparent hover:bg-info-50 focus:ring-info-main 
              disabled:text-grey-500`,
      },
      success: {
        contained: `bg-success-main text-white hover:bg-success-dark focus:ring-success-main 
                   disabled:bg-grey-300 disabled:text-grey-500`,
        outlined: `border border-success-main text-success-main bg-transparent hover:bg-success-50 
                  focus:ring-success-main disabled:border-grey-300 disabled:text-grey-500`,
        text: `text-success-main bg-transparent hover:bg-success-50 focus:ring-success-main 
              disabled:text-grey-500`,
      },
    }

    return colorMap[color][variant]
  }

  const borderRadiusClass = variant === 'text' ? 'rounded' : 'rounded'

  const classes = [
    baseClasses,
    sizeClasses[size],
    getVariantClasses(),
    borderRadiusClass,
    className,
  ].filter(Boolean).join(' ')

  const iconClasses = size === 'small' ? 'w-4 h-4' : size === 'large' ? 'w-6 h-6' : 'w-5 h-5'

  const LoadingSpinner = () => (
    <svg
      className={`animate-spin ${iconClasses}`}
      fill="none"
      viewBox="0 0 24 24"
    >
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
      />
      <path
        className="opacity-75"
        fill="currentColor"
        d="m4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
      />
    </svg>
  )

  return (
    <button
      className={classes}
      disabled={disabled || loading}
      {...props}
    >
      {loading ? (
        <>
          <LoadingSpinner />
          {children && <span className="ml-2">{children}</span>}
        </>
      ) : (
        <>
          {startIcon && (
            <span className={`${iconClasses} ${children ? 'mr-2' : ''}`}>
              {startIcon}
            </span>
          )}
          {children}
          {endIcon && (
            <span className={`${iconClasses} ${children ? 'ml-2' : ''}`}>
              {endIcon}
            </span>
          )}
        </>
      )}
    </button>
  )
}

export default Button