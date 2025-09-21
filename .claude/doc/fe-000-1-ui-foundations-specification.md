# FE-000.1 UI Foundations Technical Specification

## Overview

This document provides comprehensive technical specifications for implementing shadcn/ui component foundations for the Sayar commerce platform. The design follows S-Tier SaaS standards and integrates seamlessly with existing React 18 + Vite + TypeScript architecture.

## 1. ShadCN/UI Setup & Configuration

### Package Dependencies

```json
{
  "dependencies": {
    "@radix-ui/react-accordion": "^1.2.0",
    "@radix-ui/react-alert-dialog": "^1.1.1",
    "@radix-ui/react-avatar": "^1.1.0",
    "@radix-ui/react-checkbox": "^1.1.1",
    "@radix-ui/react-collapsible": "^1.1.0",
    "@radix-ui/react-dialog": "^1.1.1",
    "@radix-ui/react-dropdown-menu": "^2.1.1",
    "@radix-ui/react-hover-card": "^1.1.1",
    "@radix-ui/react-label": "^2.1.0",
    "@radix-ui/react-menubar": "^1.1.1",
    "@radix-ui/react-navigation-menu": "^1.2.0",
    "@radix-ui/react-popover": "^1.1.1",
    "@radix-ui/react-progress": "^1.1.0",
    "@radix-ui/react-radio-group": "^1.2.0",
    "@radix-ui/react-scroll-area": "^1.1.0",
    "@radix-ui/react-select": "^2.1.1",
    "@radix-ui/react-separator": "^1.1.0",
    "@radix-ui/react-sheet": "^1.1.0",
    "@radix-ui/react-slider": "^1.2.0",
    "@radix-ui/react-slot": "^1.1.0",
    "@radix-ui/react-switch": "^1.1.0",
    "@radix-ui/react-tabs": "^1.1.0",
    "@radix-ui/react-toast": "^1.2.1",
    "@radix-ui/react-toggle": "^1.1.0",
    "@radix-ui/react-toggle-group": "^1.1.0",
    "@radix-ui/react-tooltip": "^1.1.2",
    "cmdk": "^1.0.0",
    "embla-carousel-react": "^8.3.0",
    "input-otp": "^1.2.4",
    "recharts": "^2.12.7",
    "sonner": "^1.5.0",
    "vaul": "^0.9.9"
  }
}
```

### CSS Variables Configuration

```css
/* /front/src/index.css - Enhanced theme tokens */
@layer base {
  :root {
    /* Base colors */
    --background: 0 0% 100%;
    --foreground: 222.2 84% 4.9%;

    /* Card colors */
    --card: 0 0% 100%;
    --card-foreground: 222.2 84% 4.9%;

    /* Popover colors */
    --popover: 0 0% 100%;
    --popover-foreground: 222.2 84% 4.9%;

    /* Primary brand colors */
    --primary: 221.2 83.2% 53.3%;
    --primary-foreground: 210 40% 98%;

    /* Secondary colors */
    --secondary: 210 40% 96%;
    --secondary-foreground: 222.2 84% 4.9%;

    /* Muted colors */
    --muted: 210 40% 96%;
    --muted-foreground: 215.4 16.3% 46.9%;

    /* Accent colors */
    --accent: 210 40% 96%;
    --accent-foreground: 222.2 84% 4.9%;

    /* Destructive colors */
    --destructive: 0 84.2% 60.2%;
    --destructive-foreground: 210 40% 98%;

    /* Border and input */
    --border: 214.3 31.8% 91.4%;
    --input: 214.3 31.8% 91.4%;
    --ring: 221.2 83.2% 53.3%;

    /* Radius */
    --radius: 0.5rem;

    /* Chart colors */
    --chart-1: 12 76% 61%;
    --chart-2: 173 58% 39%;
    --chart-3: 197 37% 24%;
    --chart-4: 43 74% 66%;
    --chart-5: 27 87% 67%;

    /* Commerce-specific semantic colors */
    --success: 142 71% 45%;
    --success-foreground: 210 40% 98%;
    --warning: 38 92% 50%;
    --warning-foreground: 222.2 84% 4.9%;
    --info: 199 89% 48%;
    --info-foreground: 210 40% 98%;

    /* Status colors for commerce */
    --status-pending: 43 74% 66%;
    --status-processing: 199 89% 48%;
    --status-completed: 142 71% 45%;
    --status-cancelled: 0 84.2% 60.2%;
    --status-refunded: 221.2 83.2% 53.3%;
  }

  .dark {
    --background: 222.2 84% 4.9%;
    --foreground: 210 40% 98%;

    --card: 222.2 84% 4.9%;
    --card-foreground: 210 40% 98%;

    --popover: 222.2 84% 4.9%;
    --popover-foreground: 210 40% 98%;

    --primary: 217.2 91.2% 59.8%;
    --primary-foreground: 222.2 84% 4.9%;

    --secondary: 217.2 32.6% 17.5%;
    --secondary-foreground: 210 40% 98%;

    --muted: 217.2 32.6% 17.5%;
    --muted-foreground: 215 20.2% 65.1%;

    --accent: 217.2 32.6% 17.5%;
    --accent-foreground: 210 40% 98%;

    --destructive: 0 62.8% 30.6%;
    --destructive-foreground: 210 40% 98%;

    --border: 217.2 32.6% 17.5%;
    --input: 217.2 32.6% 17.5%;
    --ring: 224.3 76.3% 94.1%;

    --chart-1: 220 70% 50%;
    --chart-2: 160 60% 45%;
    --chart-3: 30 80% 55%;
    --chart-4: 280 65% 60%;
    --chart-5: 340 75% 55%;
  }
}
```

### components.json Configuration

```json
{
  "$schema": "https://ui.shadcn.com/schema.json",
  "style": "new-york",
  "rsc": false,
  "tsx": true,
  "tailwind": {
    "config": "tailwind.config.js",
    "css": "src/index.css",
    "baseColor": "slate",
    "cssVariables": true,
    "prefix": ""
  },
  "aliases": {
    "components": "@/components",
    "utils": "@/lib/utils",
    "ui": "@/components/ui",
    "lib": "@/lib",
    "hooks": "@/hooks",
    "types": "@/types"
  }
}
```

## 2. Component Architecture & File Structure

### Directory Organization

```
front/src/
├── components/
│   ├── ui/                          # shadcn/ui primitives
│   │   ├── accordion.tsx
│   │   ├── alert-dialog.tsx
│   │   ├── alert.tsx
│   │   ├── avatar.tsx
│   │   ├── badge.tsx
│   │   ├── button.tsx
│   │   ├── calendar.tsx
│   │   ├── card.tsx
│   │   ├── checkbox.tsx
│   │   ├── collapsible.tsx
│   │   ├── command.tsx
│   │   ├── context-menu.tsx
│   │   ├── dialog.tsx
│   │   ├── dropdown-menu.tsx
│   │   ├── form.tsx
│   │   ├── hover-card.tsx
│   │   ├── input.tsx
│   │   ├── label.tsx
│   │   ├── menubar.tsx
│   │   ├── navigation-menu.tsx
│   │   ├── popover.tsx
│   │   ├── progress.tsx
│   │   ├── radio-group.tsx
│   │   ├── scroll-area.tsx
│   │   ├── select.tsx
│   │   ├── separator.tsx
│   │   ├── sheet.tsx
│   │   ├── skeleton.tsx
│   │   ├── slider.tsx
│   │   ├── switch.tsx
│   │   ├── table.tsx
│   │   ├── tabs.tsx
│   │   ├── textarea.tsx
│   │   ├── toast.tsx
│   │   ├── toaster.tsx
│   │   ├── toggle-group.tsx
│   │   ├── toggle.tsx
│   │   └── tooltip.tsx
│   ├── layout/                      # Layout primitives
│   │   ├── app-shell.tsx
│   │   ├── header.tsx
│   │   ├── sidebar.tsx
│   │   ├── page-header.tsx
│   │   ├── content.tsx
│   │   └── main-layout.tsx
│   ├── navigation/                  # Navigation components
│   │   ├── top-nav.tsx
│   │   ├── sidebar-nav.tsx
│   │   ├── breadcrumbs.tsx
│   │   ├── command-palette.tsx
│   │   └── nav-link.tsx
│   ├── data-display/               # Data components
│   │   ├── data-table.tsx
│   │   ├── stat-card.tsx
│   │   ├── description-list.tsx
│   │   ├── empty-state.tsx
│   │   ├── pagination.tsx
│   │   └── filter-bar.tsx
│   ├── forms/                      # Form components
│   │   ├── form-field.tsx
│   │   ├── form-section.tsx
│   │   ├── form-actions.tsx
│   │   ├── text-field.tsx
│   │   ├── textarea-field.tsx
│   │   ├── select-field.tsx
│   │   ├── switch-field.tsx
│   │   └── combobox-field.tsx
│   └── feedback/                   # Feedback components
│       ├── loading-spinner.tsx
│       ├── inline-alert.tsx
│       └── status-badge.tsx
├── hooks/                          # Custom hooks
│   ├── use-toast.ts
│   ├── use-local-storage.ts
│   ├── use-command-palette.ts
│   └── use-sidebar.ts
├── lib/
│   ├── utils.ts                    # cn utility
│   ├── validations.ts              # Zod schemas
│   └── constants.ts                # Design tokens
└── types/
    ├── ui.ts                       # UI component types
    └── commerce.ts                 # Business domain types
```

### Naming Conventions

- **File Naming**: kebab-case (e.g., `data-table.tsx`, `form-field.tsx`)
- **Component Names**: PascalCase (e.g., `DataTable`, `FormField`)
- **Props Interfaces**: ComponentNameProps (e.g., `DataTableProps`, `FormFieldProps`)
- **Variant Types**: ComponentNameVariant (e.g., `ButtonVariant`, `AlertVariant`)

## 3. AppShell System Architecture

### Core Layout Primitives

#### AppShell Component

```typescript
// components/layout/app-shell.tsx
import { ReactNode } from 'react'
import { cn } from '@/lib/utils'

interface AppShellProps {
  children: ReactNode
  sidebar?: ReactNode
  header?: ReactNode
  className?: string
}

export function AppShell({ children, sidebar, header, className }: AppShellProps) {
  return (
    <div className={cn("min-h-screen bg-background font-sans antialiased", className)}>
      {header}
      <div className="flex">
        {sidebar}
        <main className="flex-1">{children}</main>
      </div>
    </div>
  )
}
```

#### Sidebar Component

```typescript
// components/layout/sidebar.tsx
import { ReactNode, createContext, useContext, useState } from 'react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import { ChevronLeft, ChevronRight } from 'lucide-react'

interface SidebarContextValue {
  collapsed: boolean
  toggle: () => void
}

const SidebarContext = createContext<SidebarContextValue | null>(null)

export function useSidebar() {
  const context = useContext(SidebarContext)
  if (!context) {
    throw new Error('useSidebar must be used within SidebarProvider')
  }
  return context
}

interface SidebarProps {
  children: ReactNode
  defaultCollapsed?: boolean
  className?: string
}

export function Sidebar({ children, defaultCollapsed = false, className }: SidebarProps) {
  const [collapsed, setCollapsed] = useState(defaultCollapsed)

  const toggle = () => setCollapsed(!collapsed)

  return (
    <SidebarContext.Provider value={{ collapsed, toggle }}>
      <aside
        className={cn(
          "relative flex h-screen flex-col border-r bg-background transition-all duration-300",
          collapsed ? "w-16" : "w-64",
          className
        )}
      >
        <div className="flex h-14 items-center justify-between px-4">
          {!collapsed && (
            <div className="flex items-center space-x-2">
              <div className="h-6 w-6 rounded bg-primary" />
              <span className="text-sm font-semibold">Sayar</span>
            </div>
          )}
          <Button
            variant="ghost"
            size="icon"
            onClick={toggle}
            className="h-8 w-8"
          >
            {collapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
          </Button>
        </div>
        <Separator />
        <ScrollArea className="flex-1">
          <div className="p-2">{children}</div>
        </ScrollArea>
      </aside>
    </SidebarContext.Provider>
  )
}

interface SidebarSectionProps {
  title?: string
  children: ReactNode
  className?: string
}

export function SidebarSection({ title, children, className }: SidebarSectionProps) {
  const { collapsed } = useSidebar()

  return (
    <div className={cn("py-2", className)}>
      {title && !collapsed && (
        <h4 className="mb-2 px-2 text-xs font-medium text-muted-foreground uppercase tracking-wider">
          {title}
        </h4>
      )}
      <div className="space-y-1">{children}</div>
    </div>
  )
}
```

#### Header Component

```typescript
// components/layout/header.tsx
import { ReactNode } from 'react'
import { cn } from '@/lib/utils'

interface HeaderProps {
  children?: ReactNode
  className?: string
}

export function Header({ children, className }: HeaderProps) {
  return (
    <header
      className={cn(
        "sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60",
        className
      )}
    >
      <div className="container flex h-14 items-center">
        {children}
      </div>
    </header>
  )
}

interface HeaderSectionProps {
  children: ReactNode
  className?: string
}

export function HeaderSection({ children, className }: HeaderSectionProps) {
  return <div className={cn("flex items-center space-x-4", className)}>{children}</div>
}

export function HeaderStart({ children, className }: HeaderSectionProps) {
  return <div className={cn("flex items-center space-x-4", className)}>{children}</div>
}

export function HeaderCenter({ children, className }: HeaderSectionProps) {
  return <div className={cn("flex flex-1 items-center justify-center", className)}>{children}</div>
}

export function HeaderEnd({ children, className }: HeaderSectionProps) {
  return <div className={cn("flex items-center justify-end space-x-4", className)}>{children}</div>
}
```

#### PageHeader Component

```typescript
// components/layout/page-header.tsx
import { ReactNode } from 'react'
import { cn } from '@/lib/utils'
import { Separator } from '@/components/ui/separator'

interface PageHeaderProps {
  title: string
  description?: string
  breadcrumbs?: ReactNode
  actions?: ReactNode
  className?: string
}

export function PageHeader({ title, description, breadcrumbs, actions, className }: PageHeaderProps) {
  return (
    <div className={cn("space-y-4 pb-4", className)}>
      {breadcrumbs}
      <div className="flex items-center justify-between space-y-2">
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
          {description && <p className="text-sm text-muted-foreground">{description}</p>}
        </div>
        {actions && <div className="flex items-center space-x-2">{actions}</div>}
      </div>
      <Separator />
    </div>
  )
}
```

## 4. Form Integration Strategy

### react-hook-form + Zod Integration

#### Form Context & Utilities

```typescript
// lib/validations.ts
import { z } from 'zod'

// Common validation schemas
export const commonValidations = {
  email: z.string().email('Invalid email address'),
  password: z.string().min(8, 'Password must be at least 8 characters'),
  phone: z.string().regex(/^\+?[\d\s-()]+$/, 'Invalid phone number'),
  currency: z.number().positive('Amount must be positive'),
  sku: z.string().min(1, 'SKU is required').max(50, 'SKU too long'),
  name: z.string().min(1, 'Name is required').max(100, 'Name too long'),
  description: z.string().max(1000, 'Description too long').optional(),
}

// Commerce-specific schemas
export const productSchema = z.object({
  name: commonValidations.name,
  description: commonValidations.description,
  sku: commonValidations.sku,
  price: commonValidations.currency,
  category: z.string().min(1, 'Category is required'),
  active: z.boolean().default(true),
  trackInventory: z.boolean().default(false),
  stockQuantity: z.number().int().min(0).optional(),
})

export type ProductFormData = z.infer<typeof productSchema>
```

#### Enhanced Form Components

```typescript
// components/forms/form-field.tsx
import { ReactNode } from 'react'
import { FieldPath, FieldValues, useController, UseControllerProps } from 'react-hook-form'
import { cn } from '@/lib/utils'
import { Label } from '@/components/ui/label'

interface FormFieldProps<TFieldValues extends FieldValues, TName extends FieldPath<TFieldValues>>
  extends UseControllerProps<TFieldValues, TName> {
  label?: string
  description?: string
  required?: boolean
  children: (field: any) => ReactNode
  className?: string
}

export function FormField<TFieldValues extends FieldValues, TName extends FieldPath<TFieldValues>>({
  label,
  description,
  required,
  children,
  className,
  ...props
}: FormFieldProps<TFieldValues, TName>) {
  const { field, fieldState } = useController(props)
  const hasError = !!fieldState.error

  return (
    <div className={cn("space-y-2", className)}>
      {label && (
        <Label htmlFor={field.name} className={cn(hasError && "text-destructive")}>
          {label}
          {required && <span className="text-destructive ml-1">*</span>}
        </Label>
      )}
      {children(field)}
      {description && !hasError && (
        <p className="text-sm text-muted-foreground">{description}</p>
      )}
      {hasError && (
        <p className="text-sm text-destructive">{fieldState.error?.message}</p>
      )}
    </div>
  )
}
```

#### Specific Field Components

```typescript
// components/forms/text-field.tsx
import { forwardRef } from 'react'
import { FieldPath, FieldValues, UseControllerProps } from 'react-hook-form'
import { Input, InputProps } from '@/components/ui/input'
import { FormField } from './form-field'

interface TextFieldProps<TFieldValues extends FieldValues, TName extends FieldPath<TFieldValues>>
  extends UseControllerProps<TFieldValues, TName>,
    Omit<InputProps, 'name' | 'value' | 'onChange'> {
  label?: string
  description?: string
  required?: boolean
}

export function TextField<TFieldValues extends FieldValues, TName extends FieldPath<TFieldValues>>({
  label,
  description,
  required,
  ...props
}: TextFieldProps<TFieldValues, TName>) {
  return (
    <FormField
      {...props}
      label={label}
      description={description}
      required={required}
    >
      {(field) => (
        <Input
          {...field}
          {...props}
          id={field.name}
        />
      )}
    </FormField>
  )
}
```

## 5. Theme System & Design Tokens

### Design Token Structure

```typescript
// lib/constants.ts
export const designTokens = {
  spacing: {
    xs: '0.25rem',    // 4px
    sm: '0.5rem',     // 8px
    md: '1rem',       // 16px
    lg: '1.5rem',     // 24px
    xl: '2rem',       // 32px
    '2xl': '3rem',    // 48px
    '3xl': '4rem',    // 64px
  },
  borderRadius: {
    none: '0',
    sm: '0.125rem',   // 2px
    base: '0.25rem',  // 4px
    md: '0.375rem',   // 6px
    lg: '0.5rem',     // 8px
    xl: '0.75rem',    // 12px
    '2xl': '1rem',    // 16px
    full: '9999px',
  },
  shadows: {
    sm: '0 1px 2px 0 rgb(0 0 0 / 0.05)',
    base: '0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1)',
    md: '0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)',
    lg: '0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)',
    xl: '0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1)',
  },
  typography: {
    fontFamily: {
      sans: ['Inter', 'ui-sans-serif', 'system-ui'],
      mono: ['JetBrains Mono', 'ui-monospace', 'monospace'],
    },
    fontSize: {
      xs: ['0.75rem', { lineHeight: '1rem' }],
      sm: ['0.875rem', { lineHeight: '1.25rem' }],
      base: ['1rem', { lineHeight: '1.5rem' }],
      lg: ['1.125rem', { lineHeight: '1.75rem' }],
      xl: ['1.25rem', { lineHeight: '1.75rem' }],
      '2xl': ['1.5rem', { lineHeight: '2rem' }],
      '3xl': ['1.875rem', { lineHeight: '2.25rem' }],
    },
  },
  animation: {
    duration: {
      fast: '150ms',
      normal: '250ms',
      slow: '350ms',
    },
    easing: {
      ease: 'cubic-bezier(0.25, 0.46, 0.45, 0.94)',
      easeIn: 'cubic-bezier(0.4, 0, 1, 1)',
      easeOut: 'cubic-bezier(0, 0, 0.2, 1)',
      easeInOut: 'cubic-bezier(0.4, 0, 0.2, 1)',
    },
  },
} as const

export const commerceStatusColors = {
  pending: 'hsl(var(--status-pending))',
  processing: 'hsl(var(--status-processing))',
  completed: 'hsl(var(--status-completed))',
  cancelled: 'hsl(var(--status-cancelled))',
  refunded: 'hsl(var(--status-refunded))',
} as const

export type CommerceStatus = keyof typeof commerceStatusColors
```

### Variant System with CVA

```typescript
// components/ui/button.tsx (Enhanced)
import * as React from "react"
import { Slot } from "@radix-ui/react-slot"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground hover:bg-primary/90",
        destructive: "bg-destructive text-destructive-foreground hover:bg-destructive/90",
        outline: "border border-input bg-background hover:bg-accent hover:text-accent-foreground",
        secondary: "bg-secondary text-secondary-foreground hover:bg-secondary/80",
        ghost: "hover:bg-accent hover:text-accent-foreground",
        link: "text-primary underline-offset-4 hover:underline",
        success: "bg-success text-success-foreground hover:bg-success/90",
        warning: "bg-warning text-warning-foreground hover:bg-warning/90",
      },
      size: {
        default: "h-10 px-4 py-2",
        sm: "h-9 rounded-md px-3",
        lg: "h-11 rounded-md px-8",
        icon: "h-10 w-10",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean
  loading?: boolean
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, loading = false, disabled, children, ...props }, ref) => {
    const Comp = asChild ? Slot : "button"

    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        disabled={disabled || loading}
        {...props}
      >
        {loading && <div className="mr-2 h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />}
        {children}
      </Comp>
    )
  }
)
Button.displayName = "Button"

export { Button, buttonVariants }
```

## 6. Dev Showcase Implementation

### UI Showcase Page Structure

```typescript
// pages/_dev/ui/index.tsx (Dev-only showcase)
import { lazy, Suspense } from 'react'
import { Navigate } from 'react-router-dom'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

// Dev environment check
const isDev = import.meta.env.DEV && import.meta.env.VITE_UI_SHOWCASE === 'true'

if (!isDev) {
  // Redirect to 404 or home in production
  export default function UIShowcase() {
    return <Navigate to="/" replace />
  }
}

// Lazy load showcase sections
const ButtonShowcase = lazy(() => import('./sections/button-showcase'))
const FormShowcase = lazy(() => import('./sections/form-showcase'))
const LayoutShowcase = lazy(() => import('./sections/layout-showcase'))
const DataShowcase = lazy(() => import('./sections/data-showcase'))
const FeedbackShowcase = lazy(() => import('./sections/feedback-showcase'))

export default function UIShowcase() {
  return (
    <div className="container mx-auto p-6">
      <div className="mb-8">
        <h1 className="text-3xl font-bold">UI Component Showcase</h1>
        <p className="text-muted-foreground">
          Development environment for testing and documenting UI components
        </p>
      </div>

      <Tabs defaultValue="buttons" className="space-y-6">
        <TabsList className="grid w-full grid-cols-5">
          <TabsTrigger value="buttons">Buttons</TabsTrigger>
          <TabsTrigger value="forms">Forms</TabsTrigger>
          <TabsTrigger value="layout">Layout</TabsTrigger>
          <TabsTrigger value="data">Data</TabsTrigger>
          <TabsTrigger value="feedback">Feedback</TabsTrigger>
        </TabsList>

        <ScrollArea className="h-[calc(100vh-200px)]">
          <div className="space-y-6">
            <TabsContent value="buttons">
              <Suspense fallback={<ShowcaseSkeleton />}>
                <ButtonShowcase />
              </Suspense>
            </TabsContent>

            <TabsContent value="forms">
              <Suspense fallback={<ShowcaseSkeleton />}>
                <FormShowcase />
              </Suspense>
            </TabsContent>

            <TabsContent value="layout">
              <Suspense fallback={<ShowcaseSkeleton />}>
                <LayoutShowcase />
              </Suspense>
            </TabsContent>

            <TabsContent value="data">
              <Suspense fallback={<ShowcaseSkeleton />}>
                <DataShowcase />
              </Suspense>
            </TabsContent>

            <TabsContent value="feedback">
              <Suspense fallback={<ShowcaseSkeleton />}>
                <FeedbackShowcase />
              </Suspense>
            </TabsContent>
          </div>
        </ScrollArea>
      </Tabs>
    </div>
  )
}

function ShowcaseSkeleton() {
  return (
    <div className="space-y-4">
      {Array.from({ length: 3 }).map((_, i) => (
        <Card key={i}>
          <CardHeader>
            <div className="h-6 w-32 bg-muted animate-pulse rounded" />
            <div className="h-4 w-48 bg-muted animate-pulse rounded" />
          </CardHeader>
          <CardContent>
            <div className="h-20 bg-muted animate-pulse rounded" />
          </CardContent>
        </Card>
      ))}
    </div>
  )
}
```

### Showcase Section Example

```typescript
// pages/_dev/ui/sections/button-showcase.tsx
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Download, Plus, Settings, Trash2 } from 'lucide-react'

export default function ButtonShowcase() {
  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Button Variants</CardTitle>
          <CardDescription>
            Different button styles for various use cases
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-2">
            <Button variant="default">Default</Button>
            <Button variant="secondary">Secondary</Button>
            <Button variant="outline">Outline</Button>
            <Button variant="ghost">Ghost</Button>
            <Button variant="destructive">Destructive</Button>
            <Button variant="success">Success</Button>
            <Button variant="warning">Warning</Button>
            <Button variant="link">Link</Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Button Sizes</CardTitle>
          <CardDescription>
            Different button sizes for various contexts
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center gap-2">
            <Button size="sm">Small</Button>
            <Button size="default">Default</Button>
            <Button size="lg">Large</Button>
            <Button size="icon">
              <Settings className="h-4 w-4" />
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Button States</CardTitle>
          <CardDescription>
            Loading and disabled states
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-2">
            <Button loading>Loading</Button>
            <Button disabled>Disabled</Button>
            <Button loading disabled>Loading + Disabled</Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Button with Icons</CardTitle>
          <CardDescription>
            Buttons with icons for better visual communication
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-2">
            <Button>
              <Plus className="mr-2 h-4 w-4" />
              Add Product
            </Button>
            <Button variant="outline">
              <Download className="mr-2 h-4 w-4" />
              Export
            </Button>
            <Button variant="destructive">
              <Trash2 className="mr-2 h-4 w-4" />
              Delete
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
```

## 7. Performance & Accessibility Standards

### Performance Optimizations

1. **Component Lazy Loading**: Use React.lazy for showcase sections
2. **Tree Shaking**: Import only needed icons from lucide-react
3. **Bundle Splitting**: Separate dev showcase from production bundles
4. **Memoization**: Use React.memo for expensive components

### Accessibility Requirements

1. **WCAG 2.1 AA Compliance**
   - Proper color contrast ratios
   - Keyboard navigation support
   - Screen reader compatibility
   - Focus management

2. **ARIA Patterns**
   - Proper labeling with `aria-label` and `aria-describedby`
   - Role definitions for complex components
   - State announcements with `aria-live` regions

3. **Semantic HTML**
   - Use proper heading hierarchy
   - Form controls with associated labels
   - Interactive elements with proper roles

## 8. Integration Guidelines

### TypeScript Configuration

```typescript
// types/ui.ts
export interface BaseComponentProps {
  className?: string
  children?: React.ReactNode
}

export interface InteractiveComponentProps extends BaseComponentProps {
  disabled?: boolean
  loading?: boolean
}

export interface FormComponentProps extends InteractiveComponentProps {
  required?: boolean
  error?: string
  description?: string
}

// Commerce-specific types
export interface Product {
  id: string
  name: string
  description?: string
  sku: string
  price: number
  category: string
  active: boolean
  trackInventory: boolean
  stockQuantity?: number
  createdAt: string
  updatedAt: string
}

export interface Order {
  id: string
  status: 'pending' | 'processing' | 'completed' | 'cancelled' | 'refunded'
  total: number
  customerName: string
  items: OrderItem[]
  createdAt: string
}

export interface OrderItem {
  id: string
  productId: string
  productName: string
  quantity: number
  price: number
}
```

### Testing Strategy

```typescript
// __tests__/components/ui/button.test.tsx
import { render, screen, fireEvent } from '@testing-library/react'
import { Button } from '@/components/ui/button'

describe('Button Component', () => {
  it('renders with default variant', () => {
    render(<Button>Click me</Button>)
    const button = screen.getByRole('button', { name: /click me/i })
    expect(button).toHaveClass('bg-primary')
  })

  it('shows loading state', () => {
    render(<Button loading>Click me</Button>)
    const button = screen.getByRole('button')
    expect(button).toBeDisabled()
    expect(button).toHaveTextContent('Click me')
  })

  it('handles click events', () => {
    const handleClick = jest.fn()
    render(<Button onClick={handleClick}>Click me</Button>)

    fireEvent.click(screen.getByRole('button'))
    expect(handleClick).toHaveBeenCalledTimes(1)
  })

  it('supports keyboard navigation', () => {
    render(<Button>Click me</Button>)
    const button = screen.getByRole('button')

    button.focus()
    expect(button).toHaveFocus()

    fireEvent.keyDown(button, { key: 'Enter' })
    // Add assertions for keyboard interaction
  })
})
```

## 9. Implementation Checklist

### Phase 1: Foundation Setup
- [ ] Install shadcn/ui dependencies
- [ ] Configure components.json
- [ ] Set up CSS variables and theme tokens
- [ ] Implement core utilities (cn, cva patterns)
- [ ] Create base component structure

### Phase 2: Layout System
- [ ] Implement AppShell primitives
- [ ] Create Sidebar with collapse functionality
- [ ] Build Header with composition patterns
- [ ] Develop PageHeader component
- [ ] Test responsive behavior

### Phase 3: Form Integration
- [ ] Set up react-hook-form + zod integration
- [ ] Create FormField wrapper component
- [ ] Implement field-specific components
- [ ] Add form validation patterns
- [ ] Test accessibility compliance

### Phase 4: UI Components
- [ ] Install and configure shadcn/ui components
- [ ] Customize components for commerce use cases
- [ ] Create commerce-specific variants
- [ ] Implement status badge system
- [ ] Add loading and error states

### Phase 5: Dev Showcase
- [ ] Create gated dev environment check
- [ ] Build showcase page structure
- [ ] Implement component documentation
- [ ] Add interactive examples
- [ ] Test in development environment

### Phase 6: Testing & Documentation
- [ ] Write component unit tests
- [ ] Test accessibility compliance
- [ ] Create usage documentation
- [ ] Performance optimization
- [ ] Final integration testing

## Implementation Notes

1. **Gradual Migration**: Components can be implemented incrementally alongside existing Material-UI components
2. **Type Safety**: All components must have proper TypeScript interfaces
3. **Performance**: Use React.memo sparingly, only for expensive components
4. **Accessibility**: Every interactive component must support keyboard navigation
5. **Testing**: Focus on user behavior testing rather than implementation details
6. **Documentation**: Each component should have usage examples in the dev showcase

This specification provides a comprehensive foundation for implementing the shadcn/ui component system while maintaining high standards for performance, accessibility, and developer experience.