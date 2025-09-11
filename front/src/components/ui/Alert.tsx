import React from 'react'

export interface AlertProps extends React.HTMLAttributes<HTMLDivElement> {
  severity?: 'error' | 'warning' | 'info' | 'success'
  variant?: 'filled' | 'outlined' | 'standard'
  onClose?: () => void
  icon?: React.ReactNode
  children: React.ReactNode
}

export const Alert: React.FC<AlertProps> = ({
  severity = 'info',
  variant = 'standard',
  onClose,
  icon,
  className = '',
  children,
  ...props
}) => {
  const baseClasses = 'flex items-start px-4 py-2 rounded text-sm'

  const getSeverityClasses = () => {
    const severityMap = {
      error: {
        filled: 'bg-error-main text-white',
        outlined: 'bg-error-50 text-error-800 border border-error-200',
        standard: 'bg-error-50 text-error-800',
      },
      warning: {
        filled: 'bg-warning-main text-white',
        outlined: 'bg-warning-50 text-warning-800 border border-warning-200',
        standard: 'bg-warning-50 text-warning-800',
      },
      info: {
        filled: 'bg-info-main text-white',
        outlined: 'bg-info-50 text-info-800 border border-info-200',
        standard: 'bg-info-50 text-info-800',
      },
      success: {
        filled: 'bg-success-main text-white',
        outlined: 'bg-success-50 text-success-800 border border-success-200',
        standard: 'bg-success-50 text-success-800',
      },
    }

    return severityMap[severity][variant]
  }

  const getDefaultIcon = () => {
    const iconMap = {
      error: (
        <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
        </svg>
      ),
      warning: (
        <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
        </svg>
      ),
      info: (
        <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
        </svg>
      ),
      success: (
        <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
        </svg>
      ),
    }

    return iconMap[severity]
  }

  const classes = [
    baseClasses,
    getSeverityClasses(),
    className,
  ].filter(Boolean).join(' ')

  const CloseIcon = () => (
    <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
      <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
    </svg>
  )

  return (
    <div className={classes} role="alert" {...props}>
      <div className="flex-shrink-0 mr-3">
        {icon || getDefaultIcon()}
      </div>
      
      <div className="flex-1 min-w-0">
        {children}
      </div>
      
      {onClose && (
        <button
          onClick={onClose}
          className="flex-shrink-0 ml-3 p-1 rounded hover:bg-black hover:bg-opacity-10 transition-colors duration-standard focus:outline-none focus:ring-2 focus:ring-current focus:ring-opacity-50"
          aria-label="Close alert"
        >
          <CloseIcon />
        </button>
      )}
    </div>
  )
}

export default Alert