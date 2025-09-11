import React from 'react'

export interface TypographyProps extends React.HTMLAttributes<HTMLElement> {
  variant?: 'h1' | 'h2' | 'h3' | 'h4' | 'h5' | 'h6' | 'subtitle1' | 'subtitle2' | 'body1' | 'body2' | 'button' | 'caption' | 'overline'
  component?: keyof JSX.IntrinsicElements
  color?: 'primary' | 'secondary' | 'text.primary' | 'text.secondary' | 'text.disabled' | 'error' | 'warning' | 'info' | 'success'
  align?: 'left' | 'center' | 'right' | 'justify'
  gutterBottom?: boolean
  noWrap?: boolean
  children: React.ReactNode
}

export const Typography: React.FC<TypographyProps> = ({
  variant = 'body1',
  component,
  color = 'text.primary',
  align = 'left',
  gutterBottom = false,
  noWrap = false,
  className = '',
  children,
  ...props
}) => {
  // Default component mapping for each variant
  const defaultComponent = {
    h1: 'h1',
    h2: 'h2', 
    h3: 'h3',
    h4: 'h4',
    h5: 'h5',
    h6: 'h6',
    subtitle1: 'h6',
    subtitle2: 'h6',
    body1: 'p',
    body2: 'p',
    button: 'span',
    caption: 'span',
    overline: 'span',
  } as const

  const Component = component || defaultComponent[variant]

  const getVariantClasses = () => {
    const variantMap = {
      h1: 'text-h1',
      h2: 'text-h2',
      h3: 'text-h3',
      h4: 'text-h4',
      h5: 'text-h5',
      h6: 'text-h6',
      subtitle1: 'text-subtitle1',
      subtitle2: 'text-subtitle2',
      body1: 'text-body1',
      body2: 'text-body2',
      button: 'text-button uppercase tracking-wider',
      caption: 'text-caption',
      overline: 'text-overline uppercase tracking-wider',
    }

    return variantMap[variant]
  }

  const getColorClasses = () => {
    const colorMap = {
      primary: 'text-primary-main',
      secondary: 'text-secondary-main', 
      'text.primary': 'text-text-primary',
      'text.secondary': 'text-text-secondary',
      'text.disabled': 'text-text-disabled',
      error: 'text-error-main',
      warning: 'text-warning-main',
      info: 'text-info-main',
      success: 'text-success-main',
    }

    return colorMap[color] || 'text-text-primary'
  }

  const getAlignClasses = () => {
    const alignMap = {
      left: 'text-left',
      center: 'text-center',
      right: 'text-right',
      justify: 'text-justify',
    }

    return alignMap[align]
  }

  const classes = [
    getVariantClasses(),
    getColorClasses(),
    getAlignClasses(),
    gutterBottom && 'mb-2',
    noWrap && 'whitespace-nowrap overflow-hidden text-ellipsis',
    className,
  ].filter(Boolean).join(' ')

  return (
    <Component className={classes} {...props}>
      {children}
    </Component>
  )
}

export default Typography