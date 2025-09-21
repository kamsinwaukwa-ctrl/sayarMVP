# Sayar UI Components Usage Guide

Complete guide for using the shadcn/ui component library in the Sayar WhatsApp commerce platform.

## Quick Start

```tsx
import { Button, Card, Input } from '@/components/ui'
import { TextField, SelectField } from '@/components/forms'
import { AppShell, PageHeader } from '@/components/layout'
```

## Preferred Components & Variants (Authoritative)

> This section is **canonical** for agents. When public shadcn demos conflict with these rules, **this guide wins**. Anything outside these rules must be called out in PR notes as **GUIDE-EXTENSION**.

| Pattern | Must Use | Defaults | Don’ts |
|---|---|---|---|
| Simple input forms | `TextField`, `SelectField`, `SwitchField`, `CheckboxField` | Labels required; `help` optional | Don’t use raw `Input` in validated forms |
| Actions | `Button` | `variant="secondary"` for toolbar; `size="sm"` in dense tables | Don’t invent custom variants without `buttonVariants` |
| Page header | `PageHeader` | Breadcrumbs required on nested pages | Don’t roll your own header |
| Lists/tables | `DataTable` | Server pagination; row actions via `DropdownMenu` | No inline styles; no ad‑hoc cells |
| Empty state | `EmptyState` | Title + description + primary action | Don’t use plain `<p>` placeholders |
| Feedback | `useToast()` | Use success/destructive variants | Don’t stack toasts for validation errors (show inline) |

---

## Tokens & Spacing (Tailwind)

Use only these tokens unless explicitly approved as a **GUIDE-EXTENSION**.

- **Spacing:** `gap-2`, `gap-3`, `gap-4`, `gap-6`, `gap-8`; `p-4`, `p-6`; `py-6` for sections
- **Radii:** `rounded-md` (default), `rounded-lg` for cards
- **Typography:** `text-sm` (meta), `text-base` (body), `text-lg` (section titles)

> Any value outside this list must be justified in the plan and PR as **GUIDE-EXTENSION**.

---

## Accessibility Defaults

- **Inputs:** Every field has a visible `label`; when `help` is present, include `aria-describedby`.
- **Buttons:** Provide text content or `aria-label` if icon‑only; never rely solely on color.
- **Focus:** Do **not** remove focus outlines; use shadcn focus ring tokens.
- **Keyboard:** Dialogs and menus must trap focus and support ESC/Enter.

---

## Composition Patterns (Canonical Boilerplates)

### Page Template
```tsx
<PageHeader title="Products" description="Manage your product catalog" />
<div className="space-y-6">
  {/* Page content here */}
</div>
```

### Standard Validated Form
```tsx
<FormSection title="Details" description="Basic info">
  <TextField name="name" control={form.control} label="Product Name" required />
  <TextField name="price" control={form.control} label="Price (₦)" type="number" required />
</FormSection>

<FormActions
  submitLabel="Save Product"
  cancelLabel="Cancel"
  onCancel={() => navigate('/products')}
  isSubmitting={form.formState.isSubmitting}
  isDirty={form.formState.isDirty}
/>
```

### Data Table Page
```tsx
<DataTable
  data={products}
  columns={columns}
  pagination={{ page, pageSize: 10, total }}
  onPageChange={setPage}
  sorting={{ key, direction }}
  onSortChange={({ key, direction }) => { setKey(key); setDirection(direction); }}
  rowActions={(row) => (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="sm"><MoreHorizontal className="h-4 w-4" /></Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent>
        <DropdownMenuItem onClick={() => edit(row.id)}>Edit</DropdownMenuItem>
        <DropdownMenuItem className="text-red-600" onClick={() => remove(row.id)}>Delete</DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )}
  emptyState={{
    title: 'No products found',
    description: 'Create your first product to get started',
    action: <Button onClick={() => navigate('/products/new')}>Add Product</Button>
  }}
/>
```

> **Do/Don'ts:**
> - **Do** mount `Dialog`/`DropdownMenu` at page level or via portals; **don’t** nest portals in table rows if it causes focus issues.
> - **Do** keep columns typed and memoized; **don’t** compute heavy cell content inline per render.

---

## State Handling Matrix

| Context | Loading | Error | Empty | Success |
|---|---|---|---|---|
| Pages | Skeletons (`<Skeleton />`) | `<ErrorMessage />` with retry | `<EmptyState />` with CTA | Render content |
| Forms | Disable submit + Button `loading` | Inline field errors + toast (destructive for server) | N/A | Toast success + redirect when applicable |
| Tables | Skeleton rows | Inline error banner | `emptyState` prop with CTA | Paginated data |

---

## Naming & File Structure

- New UI atoms/molecules live in `src/components/ui/`.
- Form fields live in `src/components/forms/`.
- Layout primitives live in `src/components/layout/`.
- Barrel exports: prefer `@/components/ui` and `@/components/forms`.
- Tests co-located as `*.test.tsx`; use `data-testid` kebab‑case tokens.

---

## Theming & Dark Mode

- Use `buttonVariants`, `inputVariants`, `statusVariants` for brand variants (e.g., `variant: 'commerce'`).
- Respect system theme; avoid hardcoded colors—prefer CSS variables.
- Document any new variant additions as **GUIDE-EXTENSION** with rationale.

---

## i18n / RTL & Formatting

- Text should be localizable; avoid hardcoded currency formatting—use a util for `₦`/locale formatting.
- Components should not assume LTR; ensure icons/chevrons mirror correctly if RTL is enabled later.

---

## Performance & DX Guardrails

- Memoize expensive table cells and column defs.
- Prefer lazy‑mounted `Dialog` content for heavy forms.
- Avoid inline functions in hot paths (rows, lists) when it causes re‑renders.
- No inline styles; use classes and variant utilities.

---

> **GUIDE-EXTENSION**: If a required pattern is missing, propose it with name, rationale, accessibility notes, and example usage. Mark such items clearly in your plan and PR.

## Component Categories

### 1. Basic UI Components
Core shadcn/ui components for general interface needs.

#### Button
```tsx
import { Button } from '@/components/ui'

// Basic usage
<Button>Click me</Button>

// With variants
<Button variant="secondary" size="sm">Small Button</Button>
<Button variant="destructive">Delete</Button>

// Loading state
<Button loading={isLoading}>
  {isLoading ? 'Saving...' : 'Save Product'}
</Button>
```

#### Card
```tsx
import { Card, CardHeader, CardContent, CardTitle } from '@/components/ui'

<Card>
  <CardHeader>
    <CardTitle>Product Details</CardTitle>
  </CardHeader>
  <CardContent>
    <p>Product information goes here</p>
  </CardContent>
</Card>
```

#### Input & Basic Form Fields
```tsx
import { Input, Label, Textarea } from '@/components/ui'

<div>
  <Label htmlFor="product-name">Product Name</Label>
  <Input
    id="product-name"
    placeholder="Enter product name"
    value={name}
    onChange={(e) => setName(e.target.value)}
  />
</div>
```

### 2. Form Components
Enhanced form fields with validation and consistent styling.

#### TextField (Recommended)
```tsx
import { TextField } from '@/components/forms'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { productSchema } from '@/lib/form-utils'

function ProductForm() {
  const form = useForm({
    resolver: zodResolver(productSchema)
  })

  return (
    <form onSubmit={form.handleSubmit(onSubmit)}>
      <TextField
        name="name"
        control={form.control}
        label="Product Name"
        placeholder="Enter product name"
        required
        help="This will be displayed to customers"
      />

      <TextField
        name="price"
        control={form.control}
        label="Price (₦)"
        type="number"
        required
      />
    </form>
  )
}
```

#### SelectField
```tsx
import { SelectField } from '@/components/forms'

const categories = [
  { value: 'skincare', label: 'Skincare' },
  { value: 'makeup', label: 'Makeup' },
  { value: 'fragrance', label: 'Fragrance' }
]

<SelectField
  name="category"
  control={form.control}
  label="Category"
  options={categories}
  placeholder="Select category"
  required
/>
```

#### SwitchField & CheckboxField
```tsx
import { SwitchField, CheckboxField } from '@/components/forms'

<SwitchField
  name="active"
  control={form.control}
  label="Active Product"
  description="Product will be visible to customers"
/>

<CheckboxField
  name="trackInventory"
  control={form.control}
  label="Track Inventory"
/>
```

### 3. Layout Components
Complete app shell and page layout system.

#### AppShell
```tsx
import { AppShell } from '@/components/layout'
import { NAVIGATION_ITEMS } from '@/lib/constants'

function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <AppShell
      user={currentUser}
      sidebarSections={NAVIGATION_ITEMS}
      searchEnabled={true}
      onSearch={handleGlobalSearch}
      notifications={notificationCount}
      onLogout={handleLogout}
    >
      {children}
    </AppShell>
  )
}
```

#### PageHeader
```tsx
import { PageHeader } from '@/components/layout'

<PageHeader
  title="Products"
  description="Manage your product catalog"
  breadcrumbs={[
    { label: 'Dashboard', href: '/dashboard' },
    { label: 'Products', href: '/products' }
  ]}
  actions={
    <Button onClick={() => navigate('/products/new')}>
      Add Product
    </Button>
  }
/>
```

#### Sidebar (Custom Navigation)
```tsx
import { Sidebar } from '@/components/layout'

const navigationSections = [
  {
    title: 'Commerce',
    items: [
      {
        label: 'Products',
        href: '/products',
        icon: 'Package',
        badge: productCount
      },
      {
        label: 'Orders',
        href: '/orders',
        icon: 'ShoppingCart',
        badge: pendingOrders > 0 ? pendingOrders : undefined
      }
    ]
  }
]

<Sidebar
  sections={navigationSections}
  collapsed={sidebarCollapsed}
  onToggle={setSidebarCollapsed}
/>
```

### 4. Data Display Components
Specialized components for showing data and status.

#### DataTable
```tsx
import { DataTable } from '@/components/ui'

function ProductsTable() {
  const columns = [
    {
      key: 'name',
      header: 'Product',
      sortable: true
    },
    {
      key: 'price',
      header: 'Price',
      render: (value: number) => `₦${value.toLocaleString()}`
    },
    {
      key: 'status',
      header: 'Status',
      render: (value: string) => (
        <Badge variant={value === 'active' ? 'success' : 'secondary'}>
          {value}
        </Badge>
      )
    }
  ]

  return (
    <DataTable
      data={products}
      columns={columns}
      pagination={{
        page: currentPage,
        pageSize: 10,
        total: totalProducts
      }}
      onPageChange={setCurrentPage}
      sorting={{
        key: sortKey,
        direction: sortDirection
      }}
      onSortChange={({ key, direction }) => {
        setSortKey(key)
        setSortDirection(direction)
      }}
      rowActions={(product) => (
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="sm">
              <MoreHorizontal className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent>
            <DropdownMenuItem onClick={() => editProduct(product.id)}>
              Edit
            </DropdownMenuItem>
            <DropdownMenuItem
              onClick={() => deleteProduct(product.id)}
              className="text-red-600"
            >
              Delete
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      )}
      emptyState={{
        title: "No products found",
        description: "Create your first product to get started",
        action: (
          <Button onClick={() => navigate('/products/new')}>
            Add Product
          </Button>
        )
      }}
    />
  )
}
```

#### Badge (Status Display)
```tsx
import { Badge } from '@/components/ui'
import { statusVariants } from '@/lib/variants'

// Using predefined status variants
<Badge className={statusVariants({ status: 'completed' })}>
  Completed
</Badge>

// Basic usage
<Badge variant="success">In Stock</Badge>
<Badge variant="warning">Low Stock</Badge>
<Badge variant="destructive">Out of Stock</Badge>
```

#### StatCard (KPI Display)
```tsx
import { StatCard } from '@/components/ui'

<div className="grid grid-cols-1 md:grid-cols-4 gap-4">
  <StatCard
    title="Total Revenue"
    value="₦1,234,567"
    change="+12.5%"
    changeType="increase"
    description="vs last month"
  />

  <StatCard
    title="Active Products"
    value="156"
    change="+8"
    changeType="increase"
    description="products added this week"
  />
</div>
```

#### EmptyState
```tsx
import { EmptyState } from '@/components/ui'

<EmptyState
  icon="Package"
  title="No products yet"
  description="Create your first product to start selling"
  action={
    <Button onClick={() => navigate('/products/new')}>
      Add Product
    </Button>
  }
/>
```

### 5. Feedback & Overlay Components
User feedback and interactive overlays.

#### Toast Notifications
```tsx
import { useToast } from '@/hooks/use-toast'

function ProductActions() {
  const { toast } = useToast()

  const saveProduct = async () => {
    try {
      await api.saveProduct(productData)
      toast({
        title: "Product saved",
        description: "Your product has been successfully saved",
      })
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Save failed",
        description: "Failed to save product. Please try again.",
      })
    }
  }
}
```

#### Dialog
```tsx
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui'

<Dialog>
  <DialogTrigger asChild>
    <Button>Edit Product</Button>
  </DialogTrigger>
  <DialogContent>
    <DialogHeader>
      <DialogTitle>Edit Product</DialogTitle>
    </DialogHeader>
    {/* Form content */}
  </DialogContent>
</Dialog>
```

#### Command Palette
```tsx
import { CommandPalette, useCommandPalette } from '@/components/ui'

function App() {
  const commands = [
    {
      id: 'new-product',
      label: 'Add New Product',
      section: 'Products',
      shortcut: ['Cmd', 'N'],
      onSelect: () => navigate('/products/new')
    },
    {
      id: 'view-orders',
      label: 'View Orders',
      section: 'Orders',
      shortcut: ['Cmd', 'O'],
      onSelect: () => navigate('/orders')
    }
  ]

  const { open, setOpen } = useCommandPalette(commands)

  return (
    <div>
      <CommandPalette
        actions={commands}
        open={open}
        onOpenChange={setOpen}
      />
      {/* Rest of app */}
    </div>
  )
}

// Cmd/Ctrl+K opens the palette automatically
```

### 6. Form Layout Components
Consistent form structure and actions.

#### FormSection
```tsx
import { FormSection } from '@/components/ui'

<FormSection
  title="Product Details"
  description="Basic information about your product"
>
  <TextField
    name="name"
    control={form.control}
    label="Product Name"
    required
  />

  <TextField
    name="description"
    control={form.control}
    label="Description"
  />
</FormSection>

<FormSection
  title="Pricing & Inventory"
  description="Set pricing and manage stock levels"
>
  <TextField
    name="price"
    control={form.control}
    label="Price (₦)"
    type="number"
    required
  />

  <SwitchField
    name="trackInventory"
    control={form.control}
    label="Track Inventory"
  />
</FormSection>
```

#### FormActions
```tsx
import { FormActions } from '@/components/ui'

<FormActions
  submitLabel="Save Product"
  cancelLabel="Cancel"
  onCancel={() => navigate('/products')}
  isSubmitting={form.formState.isSubmitting}
  isDirty={form.formState.isDirty}
/>

// For update forms
<FormActions
  submitLabel="Update Product"
  onCancel={handleCancel}
  isSubmitting={isLoading}
  destructiveAction={{
    label: "Delete Product",
    onClick: handleDelete,
    confirmMessage: "Are you sure? This cannot be undone."
  }}
/>
```

## Pre-built Form Schemas

Use validated schemas for common commerce entities:

```tsx
import {
  productSchema,
  businessProfileSchema,
  deliveryRateSchema,
  discountSchema
} from '@/lib/form-utils'

// Product form
const productForm = useForm({
  resolver: zodResolver(productSchema),
  defaultValues: {
    name: '',
    description: '',
    price: 0,
    category: '',
    active: true,
    trackInventory: false
  }
})

// Business profile form
const businessForm = useForm({
  resolver: zodResolver(businessProfileSchema),
  defaultValues: {
    businessName: '',
    description: '',
    email: '',
    phone: '',
    currency: 'NGN'
  }
})
```

## Component Variants

Use type-safe variants for consistent styling:

```tsx
import { statusVariants, buttonVariants, inputVariants } from '@/lib/variants'

// Status badges
<span className={statusVariants({ status: 'pending' })}>
  Pending
</span>

// Custom button variants
<button className={buttonVariants({ variant: 'commerce', size: 'lg' })}>
  Add to Cart
</button>

// Input variants
<input className={inputVariants({ variant: 'search', size: 'sm' })} />
```

## Best Practices

### 1. Form Handling
```tsx
// ✅ Good - Use form components with validation
<TextField
  name="email"
  control={form.control}
  label="Email"
  type="email"
  required
/>

// ❌ Avoid - Direct input without validation
<Input
  placeholder="Email"
  onChange={(e) => setEmail(e.target.value)}
/>
```

### 2. Loading States
```tsx
// ✅ Good - Show loading states
<Button loading={isSubmitting}>
  {isSubmitting ? 'Saving...' : 'Save Product'}
</Button>

// ✅ Good - Use skeletons for data loading
{isLoading ? (
  <div className="space-y-2">
    <Skeleton className="h-4 w-full" />
    <Skeleton className="h-4 w-3/4" />
  </div>
) : (
  <ProductList products={products} />
)}
```

### 3. Error Handling
```tsx
// ✅ Good - Handle all states
function ProductList() {
  const { data, isLoading, error } = useProducts()

  if (isLoading) return <ProductSkeleton />
  if (error) return <ErrorMessage error={error} />
  if (!data?.length) return <EmptyProductState />

  return <ProductGrid products={data} />
}
```

### 4. Accessibility
```tsx
// ✅ Good - Proper labeling and descriptions
<TextField
  name="price"
  control={form.control}
  label="Product Price"
  help="Price in Nigerian Naira"
  aria-describedby="price-help"
  required
/>

// ✅ Good - Keyboard navigation
<Button onKeyDown={(e) => e.key === 'Enter' && handleAction()}>
  Action
</Button>
```

## Development Tools

### UI Showcase
Access the interactive component showcase in development:

```bash
# Enable in .env.local
VITE_UI_SHOWCASE=true

# Visit in browser
http://localhost:5173/_dev/ui
```

### Adding New Components
```bash
# Add shadcn/ui components via CLI
npx shadcn@latest add calendar
npx shadcn@latest add date-picker

# Components are automatically added to src/components/ui/
```

### Component Testing
```tsx
// Test components in isolation
import { render, screen, fireEvent } from '@testing-library/react'
import { TextField } from '@/components/forms'
import { useForm } from 'react-hook-form'

function TestTextField() {
  const form = useForm()

  return (
    <TextField
      name="test"
      control={form.control}
      label="Test Field"
      data-testid="test-field"
    />
  )
}

test('renders field with label', () => {
  render(<TestTextField />)
  expect(screen.getByLabelText('Test Field')).toBeInTheDocument()
})
```

## Migration from Legacy Components

If upgrading from older UI components:

```tsx
// Old way
import { Button } from '../old-ui/Button'

// New way
import { Button } from '@/components/ui'

// The API remains mostly compatible
<Button variant="primary" size="large">
  Click me
</Button>
```

For questions or new component requests, check the interactive showcase or create an issue in the project repository.