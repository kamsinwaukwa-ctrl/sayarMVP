import React from 'react'

export interface TypographyProps extends React.HTMLAttributes<HTMLElement> {
  variant?: 'h1' | 'h2' | 'h3' | 'h4' | 'h5' | 'h6' | 'subtitle1' | 'subtitle2' | 'body1' | 'body2' | 'button' | 'caption' | 'overline'
  component?: keyof JSX.IntrinsicElements
  color?: 'primary' | 'secondary' | 'muted' | 'destructive' | 'accent' | 'foreground'
  align?: 'left' | 'center' | 'right' | 'justify'
  gutterBottom?: boolean
  noWrap?: boolean
  children: React.ReactNode
}

export const Typography: React.FC<TypographyProps> = ({
  variant = 'body1',
  component,
  color = 'foreground',
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
      h1: 'text-4xl font-extrabold tracking-tight lg:text-5xl',
      h2: 'text-3xl font-semibold tracking-tight',
      h3: 'text-2xl font-semibold tracking-tight',
      h4: 'text-xl font-semibold tracking-tight',
      h5: 'text-lg font-semibold',
      h6: 'text-base font-semibold',
      subtitle1: 'text-lg text-muted-foreground',
      subtitle2: 'text-base text-muted-foreground',
      body1: 'text-base leading-7',
      body2: 'text-sm text-muted-foreground',
      button: 'text-sm font-medium uppercase tracking-wider',
      caption: 'text-xs text-muted-foreground',
      overline: 'text-xs font-medium uppercase tracking-wider',
    }

    return variantMap[variant]
  }

  const getColorClasses = () => {
    const colorMap = {
      primary: 'text-primary',
      secondary: 'text-secondary-foreground',
      muted: 'text-muted-foreground',
      destructive: 'text-destructive',
      accent: 'text-accent-foreground',
      foreground: 'text-foreground',
    }

    return colorMap[color] || 'text-foreground'
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
    <Component className={classes} {...(props as any)}>
      {children}
    </Component>
  )
}

export default Typography