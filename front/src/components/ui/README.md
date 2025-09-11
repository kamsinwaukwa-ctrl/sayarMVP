# Tailwind UI Component Library

This directory contains our Tailwind CSS component library that replaces Material-UI components.

## Migration Strategy

### Phase-by-Phase Component Replacement

1. **Basic Components** (Button, Input, Card, Alert)
2. **Form Components** (TextField, FormControl, FormHelperText)
3. **Layout Components** (Container, Grid, Box, Stack)
4. **Navigation Components** (AppBar, Toolbar, Navigation)
5. **Data Display** (Typography, Chip, Avatar, Divider)

### Component Mapping

| Material-UI Component | Tailwind Replacement | Notes |
|----------------------|---------------------|-------|
| `Button` | `ui/Button.tsx` | variants: contained, outlined, text |
| `TextField` | `ui/Input.tsx` | includes label, helper text, error states |
| `Card` + `CardContent` | `ui/Card.tsx` | with content wrapper |
| `Alert` | `ui/Alert.tsx` | severity variants: error, warning, info, success |
| `Typography` | `ui/Typography.tsx` | variant prop for h1-h6, body1-2, etc. |
| `Container` | `ui/Container.tsx` | maxWidth variants |
| `Grid` | `ui/Grid.tsx` | responsive grid system |
| `AppBar` + `Toolbar` | `ui/AppBar.tsx` | navigation header |
| `Chip` | `ui/Chip.tsx` | size and color variants |
| `Avatar` | `ui/Avatar.tsx` | size variants |
| `CircularProgress` | `ui/LoadingSpinner.tsx` | loading indicator |

### Migration Process

1. **Create Tailwind component** with same API as MUI component
2. **Import both components** in the file being migrated
3. **Replace MUI component** with Tailwind component
4. **Test functionality** to ensure no regressions
5. **Remove MUI import** once replacement is confirmed working
6. **Update props** if needed to match new component API

### Design Tokens

All components use consistent design tokens defined in `tailwind.config.js`:

- **Colors**: Primary, secondary, error, warning, info, success, grey scales
- **Typography**: Font sizes and line heights matching MUI variants
- **Spacing**: 8px base unit system (0.5, 1, 1.5, 2, 2.5, 3, 4, 5, 6, 7, 8)
- **Shadows**: Elevation system from 1-24
- **Transitions**: Standard durations (150ms, 200ms, 250ms, 300ms, 375ms)

### Component Props Pattern

Each component follows this pattern:

```tsx
interface ComponentProps {
  variant?: 'primary' | 'secondary' | 'outlined'
  size?: 'small' | 'medium' | 'large'
  disabled?: boolean
  className?: string
  children?: React.ReactNode
}

export const Component: React.FC<ComponentProps> = ({
  variant = 'primary',
  size = 'medium',
  disabled = false,
  className = '',
  children,
  ...props
}) => {
  const baseClasses = 'base-component-classes'
  const variantClasses = {
    primary: 'variant-specific-classes',
    secondary: 'variant-specific-classes',
    outlined: 'variant-specific-classes',
  }
  const sizeClasses = {
    small: 'size-specific-classes',
    medium: 'size-specific-classes', 
    large: 'size-specific-classes',
  }
  
  const classes = [
    baseClasses,
    variantClasses[variant],
    sizeClasses[size],
    disabled && 'disabled-classes',
    className,
  ].filter(Boolean).join(' ')

  return (
    <element className={classes} disabled={disabled} {...props}>
      {children}
    </element>
  )
}
```

### Testing Strategy

- **Visual testing**: Compare before/after screenshots
- **Functional testing**: Ensure all interactive behaviors work
- **Accessibility testing**: Verify ARIA attributes and keyboard navigation
- **Responsive testing**: Check mobile and desktop layouts