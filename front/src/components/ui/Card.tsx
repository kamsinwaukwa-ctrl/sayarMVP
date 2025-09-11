import React from 'react'

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  elevation?: 0 | 1 | 2 | 3 | 4 | 6 | 8 | 12 | 16 | 24
  variant?: 'outlined' | 'elevation'
  children: React.ReactNode
}

export const Card: React.FC<CardProps> = ({
  elevation = 1,
  variant = 'elevation',
  className = '',
  children,
  ...props
}) => {
  const baseClasses = 'bg-white rounded overflow-hidden'

  const getElevationClass = () => {
    if (variant === 'outlined') {
      return 'border border-grey-200'
    }
    
    const elevationMap = {
      0: 'shadow-none',
      1: 'shadow-elevation-1',
      2: 'shadow-elevation-2', 
      3: 'shadow-elevation-3',
      4: 'shadow-elevation-4',
      6: 'shadow-elevation-6',
      8: 'shadow-elevation-8',
      12: 'shadow-elevation-12',
      16: 'shadow-elevation-16',
      24: 'shadow-elevation-24',
    }
    
    return elevationMap[elevation] || 'shadow-elevation-1'
  }

  const classes = [
    baseClasses,
    getElevationClass(),
    className,
  ].filter(Boolean).join(' ')

  return (
    <div className={classes} {...props}>
      {children}
    </div>
  )
}

export interface CardContentProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode
}

export const CardContent: React.FC<CardContentProps> = ({
  className = '',
  children,
  ...props
}) => {
  const classes = [
    'p-4',
    className,
  ].filter(Boolean).join(' ')

  return (
    <div className={classes} {...props}>
      {children}
    </div>
  )
}

export default Card