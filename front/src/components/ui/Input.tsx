import React, { forwardRef } from 'react'

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string
  helperText?: string
  error?: boolean
  fullWidth?: boolean
  variant?: 'outlined' | 'filled'
  size?: 'small' | 'medium'
  startAdornment?: React.ReactNode
  endAdornment?: React.ReactNode
}

export const Input = forwardRef<HTMLInputElement, InputProps>(({
  label,
  helperText,
  error = false,
  fullWidth = false,
  variant = 'outlined',
  size = 'medium',
  startAdornment,
  endAdornment,
  className = '',
  id,
  ...props
}, ref) => {
  const inputId = id || `input-${Math.random().toString(36).substr(2, 9)}`

  const containerClasses = [
    fullWidth && 'w-full',
  ].filter(Boolean).join(' ')

  const labelClasses = [
    'block text-sm font-medium mb-1',
    error ? 'text-error-main' : 'text-grey-700',
  ].filter(Boolean).join(' ')

  const inputWrapperClasses = [
    'relative',
    fullWidth && 'w-full',
  ].filter(Boolean).join(' ')

  const baseInputClasses = [
    'block transition-colors duration-standard focus:outline-none',
    size === 'small' ? 'px-3 py-1.5 text-sm' : 'px-3 py-2 text-base',
    fullWidth && 'w-full',
  ].filter(Boolean).join(' ')

  const getVariantClasses = () => {
    if (variant === 'filled') {
      return [
        'bg-grey-100 border-0 border-b-2 rounded-t',
        error 
          ? 'border-error-main focus:border-error-main bg-error-50' 
          : 'border-grey-300 focus:border-primary-main hover:bg-grey-200',
      ].join(' ')
    }
    
    // outlined variant (default)
    return [
      'bg-white border rounded',
      error 
        ? 'border-error-main focus:ring-2 focus:ring-error-main focus:border-error-main' 
        : 'border-grey-300 focus:ring-2 focus:ring-primary-main focus:border-primary-main hover:border-grey-400',
    ].join(' ')
  }

  const inputClasses = [
    baseInputClasses,
    getVariantClasses(),
    startAdornment && 'pl-10',
    endAdornment && 'pr-10',
    props.disabled && 'bg-grey-100 text-grey-500 cursor-not-allowed',
    className,
  ].filter(Boolean).join(' ')

  const helperTextClasses = [
    'mt-1 text-xs',
    error ? 'text-error-main' : 'text-grey-600',
  ].filter(Boolean).join(' ')

  const adornmentClasses = [
    'absolute top-1/2 transform -translate-y-1/2 flex items-center',
    size === 'small' ? 'text-sm' : 'text-base',
    error ? 'text-error-main' : 'text-grey-500',
  ].filter(Boolean).join(' ')

  return (
    <div className={containerClasses}>
      {label && (
        <label htmlFor={inputId} className={labelClasses}>
          {label}
        </label>
      )}
      
      <div className={inputWrapperClasses}>
        {startAdornment && (
          <div className={`${adornmentClasses} left-3`}>
            {startAdornment}
          </div>
        )}
        
        <input
          ref={ref}
          id={inputId}
          className={inputClasses}
          {...props}
        />
        
        {endAdornment && (
          <div className={`${adornmentClasses} right-3`}>
            {endAdornment}
          </div>
        )}
      </div>
      
      {helperText && (
        <p className={helperTextClasses}>
          {helperText}
        </p>
      )}
    </div>
  )
})

Input.displayName = 'Input'

export default Input