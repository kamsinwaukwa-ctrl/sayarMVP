import React from 'react'

export interface IconButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  size?: 'small' | 'medium' | 'large'
  color?: 'primary' | 'secondary' | 'default' | 'inherit'
  edge?: 'start' | 'end' | false
  children: React.ReactNode
}

export const IconButton: React.FC<IconButtonProps> = ({
  size = 'medium',
  color = 'default',
  edge = false,
  disabled = false,
  className = '',
  children,
  ...props
}) => {
  const baseClasses = [
    'inline-flex items-center justify-center rounded-full transition-all duration-standard',
    'focus:outline-none focus:ring-2 focus:ring-offset-2',
    'disabled:cursor-not-allowed disabled:opacity-50',
  ].filter(Boolean).join(' ')

  const sizeClasses = {
    small: 'w-8 h-8 p-1',
    medium: 'w-10 h-10 p-2',
    large: 'w-12 h-12 p-3',
  }

  const getColorClasses = () => {
    const colorMap = {
      default: 'text-grey-600 hover:bg-grey-100 focus:ring-grey-300',
      primary: 'text-primary-main hover:bg-primary-50 focus:ring-primary-300',
      secondary: 'text-secondary-main hover:bg-secondary-50 focus:ring-secondary-300',
      inherit: 'text-current hover:bg-current hover:bg-opacity-10 focus:ring-current',
    }

    return colorMap[color]
  }

  const getEdgeClasses = () => {
    if (edge === 'start') return '-ml-2'
    if (edge === 'end') return '-mr-2'
    return ''
  }

  const classes = [
    baseClasses,
    sizeClasses[size],
    getColorClasses(),
    getEdgeClasses(),
    className,
  ].filter(Boolean).join(' ')

  return (
    <button
      className={classes}
      disabled={disabled}
      {...props}
    >
      {children}
    </button>
  )
}

export default IconButton