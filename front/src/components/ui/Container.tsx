import React from 'react'

export interface ContainerProps extends React.HTMLAttributes<HTMLDivElement> {
  maxWidth?: 'xs' | 'sm' | 'md' | 'lg' | 'xl' | false
  fixed?: boolean
  disableGutters?: boolean
  children: React.ReactNode
}

export const Container: React.FC<ContainerProps> = ({
  maxWidth = 'lg',
  fixed = false,
  disableGutters = false,
  className = '',
  children,
  ...props
}) => {
  const baseClasses = 'mx-auto'

  const getMaxWidthClasses = () => {
    if (maxWidth === false) {
      return 'w-full'
    }

    const maxWidthMap = {
      xs: 'max-w-xs',
      sm: 'max-w-2xl',
      md: 'max-w-4xl', 
      lg: 'max-w-6xl',
      xl: 'max-w-7xl',
    }

    return maxWidthMap[maxWidth] || 'max-w-6xl'
  }

  const getPaddingClasses = () => {
    if (disableGutters) {
      return ''
    }
    return 'px-4 sm:px-6 lg:px-8'
  }

  const classes = [
    baseClasses,
    getMaxWidthClasses(),
    getPaddingClasses(),
    fixed && 'relative',
    className,
  ].filter(Boolean).join(' ')

  return (
    <div className={classes} {...props}>
      {children}
    </div>
  )
}

export default Container