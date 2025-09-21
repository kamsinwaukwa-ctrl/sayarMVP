# FE-001 Onboarding Wizard - Comprehensive Implementation Plan


## Overview
Complete 4-step onboarding wizard for merchant setup with integrations tab for WhatsApp credentials. This plan builds on the established shadcn/ui component library from FE-000 and follows Sayar's React patterns.

## 0. Deterministic Build Contracts (for Orchestrator)

> This section pins down concrete routes, env vars, exports, and API contracts so the task orchestrator can build without guessing. If backend paths differ, update **only** `front/src/lib/onboarding-api.ts` to re‑wire.

### 0.1 Environment & Providers
- **Env**: `VITE_API_BASE_URL` (e.g., `http://localhost:3000`)
- **Required Providers in `main.tsx`** (must exist):
  - `<AuthProvider>` from `@/context/AuthProvider`
  - `<QueryClientProvider>` from `@tanstack/react-query`
  - `<BrowserRouter>`

### 0.2 Route Registration & Auth Integration

#### Auth Context & Protected Route
```tsx
// context/AuthProvider.tsx
export interface AuthContextType {
  isAuthenticated: boolean
  user: User | null
  login: (credentials: LoginCredentials) => Promise<void>
  logout: () => Promise<void>
}

export const AuthContext = createContext<AuthContextType>(null!)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  // ... auth implementation ...
  return <AuthContext.Provider value={authValue}>{children}</AuthContext.Provider>
}

// hooks/useAuth.ts
export function useAuth() {
  return useContext(AuthContext)
}

// components/ProtectedRoute.tsx
export default function ProtectedRoute() {
  const { isAuthenticated } = useAuth()
  const location = useLocation()

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  return <Outlet />
}
```

#### Route Registration (React Router v6)
Add to `front/src/App.tsx`:
```tsx
import { Routes, Route, Navigate } from 'react-router-dom'
import ProtectedRoute from '@/components/ProtectedRoute'
import OnboardingWizard from '@/pages/onboarding/OnboardingWizard'
import OnboardingComplete from '@/pages/onboarding/OnboardingComplete'

export default function AppRoutes() {
  return (
    <Routes>
      {/* ...other routes... */}
      <Route element={<ProtectedRoute />}> 
        <Route path="/onboarding" element={<OnboardingWizard />} />
        <Route path="/onboarding/step/:step" element={<OnboardingWizard />} />
        <Route path="/onboarding/integrations" element={<OnboardingWizard initialTab="integrations" />} />
        <Route path="/onboarding/complete" element={<OnboardingComplete />} />
      </Route>
      <Route path="/" element={<Navigate to="/onboarding" replace />} />
    </Routes>
  )
}
```

### 0.3 Storage Keys & Feature Flags
- `LS_ONBOARDING_PROGRESS = 'onboarding.step'`
- `LS_ONBOARDING_DRAFT = 'onboarding.draft'`
- Optional feature flag: `feature.onboarding` (boolean) — if false, redirect `/` → `/dashboard`.

### 0.4 File & Export Contracts

#### Required Utility Functions
```ts
// lib/format.ts
export const formatNaira = (kobo: number): string => {
  const naira = kobo / 100
  return new Intl.NumberFormat('en-NG', {
    style: 'currency',
    currency: 'NGN'
  }).format(naira)
}

export const formatDate = (isoString: string): string => {
  return new Intl.DateTimeFormat('en-NG', {
    dateStyle: 'medium',
    timeStyle: 'short'
  }).format(new Date(isoString))
}
```

### 0.5 File & Export Contracts
Create these named exports exactly:
- `front/src/pages/onboarding/OnboardingWizard.tsx` → `export default OnboardingWizard`
- `front/src/pages/onboarding/OnboardingComplete.tsx` → `export default OnboardingComplete`
- `front/src/components/onboarding/index.ts` must export:
  - `OnboardingShell`, `StepIndicator`, `StepNavigation`
  - `steps/*`: `Step1BrandBasics`, `Step2Products`, `Step3DeliveryRates`, `Step4Payments`, `IntegrationsTab`
- `front/src/components/onboarding/ui/` must export:
  - `ImageUpload`, `StepCard`, `VerificationStatus`, `WizardProgress`

### 0.5 API Endpoints (default mapping)
These are the default REST paths used by `onboarding-api.ts`. If your backend differs, change only the path strings in that file.

**Merchants (Step 1)**
- `PATCH   /api/merchants/me` — update profile `{ business_name, description, currency, logo_url? }`
- `POST    /api/merchants/me/logo` — multipart form `file` → `{ logo_url }`

**Products (Step 2)**
- `GET     /api/products` → `Product[]`
- `POST    /api/products` → `Product`
- `PATCH   /api/products/:id` → `Product`
- `DELETE  /api/products/:id` → `{ ok: true }`
- `POST    /api/products/:id/image` — multipart `file` → `{ image_url }`
  - Call multiple times for additional images (BE stores in additional_image_urls)
  - Order preserved based on upload sequence
  - To remove an image, PATCH product with filtered additional_image_urls array
- `GET     /api/products/:id/meta-sync` → `{ status: 'pending' | 'synced' | 'error', reason?: string, updated_at: string }`
- `POST    /api/products/:id/meta-sync` → `{ ok: true }` (trigger re-sync)

**Delivery Rates (Step 3)**
- `GET     /api/delivery-rates` → `DeliveryRate[]`
- `POST    /api/delivery-rates` → `DeliveryRate`
- `PATCH   /api/delivery-rates/:id` → `DeliveryRate`
- `DELETE  /api/delivery-rates/:id` → `{ ok: true }`

**Payments Verify (Step 4)**
- `GET     /api/payments/providers` → `PaymentProvider[]` (e.g., `paystack`, `korapay`)
- `POST    /api/payments/verify` → `{ verified: boolean, message: string, provider: string }`

**WhatsApp Integrations Tab**
- `GET     /api/integrations/whatsapp/status` → `{ connected: boolean, phone_number?: string }`
- `POST    /api/integrations/whatsapp/verify` → `{ verified: boolean, message: string }`

### 0.6 Types (ts) expected by UI
```ts
// front/src/types/onboarding.ts
export type Currency = 'NGN' | 'USD' | 'GHS' | 'KES'
export type MetaSyncStatus = 'pending' | 'synced' | 'error'

export interface Merchant {
  id: string
  business_name: string
  description?: string
  currency: Currency
  logo_url?: string
}

export interface Product {
  id: string
  title: string
  description?: string
  price_kobo: number
  stock: number
  sku?: string            // Optional, auto-generated if blank
  brand?: string          // Optional, readonly (auto-generated)
  mpn?: string           // Optional, readonly (auto-generated)
  category_path?: string
  tags: string[]
  image_url?: string
  additional_image_urls?: string[]  // Optional additional product images
  condition?: 'new' | 'used' | 'refurbished'  // Optional quality signal
  meta_sync?: {
    status: MetaSyncStatus
    reason?: string       // Human-readable sync status reason
    updated_at?: string
  }
}

export interface DeliveryRate {
  id: string
  name: string
  areas_text: string
  price_kobo: number
  description?: string
  active: boolean
}

export interface PaymentProvider { key: 'paystack' | 'korapay'; name: string }
```

### 0.7 DataTable Column Contracts (Step 2 & 3)
```ts
// ProductsTable columns
[
  { key: 'title', header: 'Product' },
  { key: 'sku', header: 'SKU' },
  { key: 'price_kobo', header: 'Price', render: (v:number)=>formatNaira(v) },
  { key: 'stock', header: 'Stock' },
  { 
    key: 'meta_sync.status', 
    header: 'Meta', 
    render: (status: MetaSyncStatus, row: Product) => (
      <HoverCard>
        <HoverCardTrigger>
          <MetaSyncBadge status={status} />
        </HoverCardTrigger>
        <HoverCardContent>
          <div className="flex flex-col gap-2">
            <div>Status: {status}</div>
            {row.meta_sync?.reason && <div>Reason: {row.meta_sync.reason}</div>}
            {row.meta_sync?.updated_at && (
              <div>Updated: {formatDate(row.meta_sync.updated_at)}</div>
            )}
          </div>
        </HoverCardContent>
      </HoverCard>
    )
  },
  { 
    key: 'actions', 
    header: '', 
    width: 100,
    render: (_, row: Product) => (
      <DropdownMenu>
        <DropdownMenuItem onClick={() => onEdit(row)}>Edit</DropdownMenuItem>
        <DropdownMenuItem 
          onClick={() => onResync(row.id)}
          disabled={row.meta_sync?.status === 'pending'}
        >
          Re-sync
        </DropdownMenuItem>
        <DropdownMenuItem 
          onClick={() => onDelete(row.id)}
          className="text-destructive"
        >
          Delete
        </DropdownMenuItem>
      </DropdownMenu>
    )
  }
]

// DeliveryRatesTable columns
[
  { key: 'name', header: 'Rate' },
  { key: 'areas_text', header: 'Areas' },
  { key: 'price_kobo', header: 'Price', render: (v:number)=>formatNaira(v) },
  { key: 'active', header: 'Active', render: (b:boolean)=> <Switch checked={b} /> },
  { key: 'actions', header: '', width: 48 }
]
```

### 0.8 Test IDs (for integration tests)
- Wizard shell: `data-testid="onboarding-wizard"`
- Step containers: `data-testid="step-1"`, `step-2`, `step-3`, `step-4`
- Save/Next buttons: `data-testid="next-btn"`, `back-btn` 
- Verify buttons: `data-testid="verify-payments"`, `verify-whatsapp`
- Tables: `data-testid="products-table"`, `delivery-rates-table"`

### 0.9 Image Upload Constraints
- Max file size: **5MB**; allowed: `image/*`
- Enforce client-side size/type; show `VerificationStatus` while uploading
- Endpoint mapping: Step 1 → `/api/merchants/me/logo`, Step 2 → `/api/products/:id/image`

### 0.10 Error Message Canonicals
- Validation: use field `FormMessage`
- Network: toast destructive "Connection error. Please try again."
- External service (payments/WA): toast destructive "Verification failed. Check credentials."

---

## 1. File Structure & Organization

### New Files to Create
```
front/src/
├── pages/
│   └── onboarding/
│       ├── OnboardingWizard.tsx           # Main wizard shell
│       └── OnboardingComplete.tsx         # Success page
├── components/
│   └── onboarding/
│       ├── index.ts                       # Export barrel
│       ├── OnboardingShell.tsx            # Wizard layout wrapper
│       ├── StepIndicator.tsx              # Progress indicator
│       ├── StepNavigation.tsx             # Step navigation controls
│       ├── steps/
│       │   ├── index.ts                   # Step exports
│       │   ├── Step1BrandBasics.tsx       # Brand setup form
│       │   ├── Step2Products.tsx          # Product management
│       │   ├── Step3DeliveryRates.tsx     # Delivery configuration
│       │   ├── Step4Payments.tsx          # Payment verification
│       │   └── IntegrationsTab.tsx        # WhatsApp credentials
│       ├── forms/
│       │   ├── BrandBasicsForm.tsx        # Step 1 form
│       │   ├── ProductForm.tsx            # Product creation form
│       │   ├── ProductsTable.tsx          # Products display table
│       │   ├── DeliveryRateForm.tsx       # Delivery rate form
│       │   ├── DeliveryRatesTable.tsx     # Delivery rates table
│       │   ├── PaymentVerificationForm.tsx # Payment setup
│       │   └── WhatsAppVerificationForm.tsx # WhatsApp setup
│       └── ui/
│           ├── ImageUpload.tsx            # Logo/product image upload
│           ├── StepCard.tsx               # Step content wrapper
│           ├── VerificationStatus.tsx     # API verification status
│           └── WizardProgress.tsx         # Progress visualization
├── hooks/
│   ├── useOnboarding.ts                   # Main onboarding state
│   ├── useOnboardingStep.ts               # Step management
│   ├── useImageUpload.ts                  # Image upload handling
│   └── useVerification.ts                 # API verification hooks
├── lib/
│   ├── onboarding.ts                      # Onboarding utilities
│   ├── form-schemas/
│   │   ├── index.ts                       # Schema exports
│   │   ├── brand-basics.ts                # Step 1 validation
│   │   ├── products.ts                    # Product validation
│   │   ├── delivery-rates.ts              # Delivery validation
│   │   ├── payments.ts                    # Payment validation
│   │   └── whatsapp.ts                    # WhatsApp validation
│   └── onboarding-api.ts                  # API client extensions
├── types/
│   └── onboarding.ts                      # Onboarding type definitions
└── constants/
    └── onboarding.ts                      # Onboarding constants
```

### Existing Files to Modify
```
front/src/
├── App.tsx                                # Add onboarding routes
├── components/ui/form.tsx                 # Extend for wizard forms
├── lib/api-client.ts                      # Add onboarding endpoints
├── types/api.ts                          # Add onboarding API types
└── pages/Dashboard.tsx                    # Add onboarding redirect logic
```

## 2. Component Mapping Strategy

### Step 1: Brand Basics (Logo/Description/Currency)
**ShadCN Components Used:**
- `Form` + `FormField` + `FormItem` + `FormLabel` + `FormControl` + `FormMessage`
- `Input` (business name, description)
- `Select` (currency selection)
- `Button` (upload logo, save & continue)
- `Card` + `CardHeader` + `CardContent`
- `Badge` (currency display)
- `AlertCircle` icon for validation errors
- Custom `ImageUpload` component (built on `Button` + `Input[type=file]`)

### Step 2: Products (Create/Edit, Image Upload)
**ShadCN Components Used:**
- `Dialog` + `DialogContent` + `DialogHeader` + `DialogTitle` + `DialogTrigger`
- `Table` + `TableHeader` + `TableBody` + `TableRow` + `TableCell`
- `Form` fields:
  - `Input` (name, price)
  - `Input` (SKU - optional with helper "Leave blank to auto-generate")
  - `Textarea` (description)
  - `Select` (category, condition)
  - `ImageUpload` (primary + additional images)
- `Card` (Auto-generated Fields):
  ```tsx
  {product.brand && (
    <Card className="mt-4 bg-muted/50">
      <CardHeader>
        <CardTitle className="text-sm">Auto-generated Fields</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        <div className="grid gap-1">
          <Label>Brand</Label>
          <Input value={product.brand} readOnly />
          <p className="text-xs text-muted-foreground">
            Auto-generated from merchant name
          </p>
        </div>
        <div className="grid gap-1">
          <Label>MPN</Label>
          <Input value={product.mpn} readOnly />
          <p className="text-xs text-muted-foreground">
            Auto-generated from merchant slug + SKU
          </p>
        </div>
      </CardContent>
    </Card>
  )}
  ```
- `Button` variants: primary (Add Product), secondary (Edit), destructive (Delete)
- `Badge` (Meta sync status with hover details)
- `Popover` (Meta sync details: status, reason, updated_at)
- `EmptyState` (no products yet)
- `Skeleton` (loading states)
- `Toast` (product saved/error notifications)

### Step 3: Delivery Rates (CRUD)
**ShadCN Components Used:**
- `Table` with CRUD actions
- `Form` with `Input` (rate name, price), `Textarea` (areas, description)
- `Switch` (active/inactive toggle)
- `AlertDialog` (delete confirmation)
- `DropdownMenu` (row actions)
- `FormSection` (organize form fields)

### Step 4: Payments Verification
**ShadCN Components Used:**
- `Tabs` + `TabsList` + `TabsTrigger` + `TabsContent` (Paystack vs Korapay)
- `Form` with `Input` (API keys - password type)
- `Button` with loading spinner (Verify Connection)
- `Alert` (verification results)
- `Badge` (verification status)
- `Collapsible` (advanced settings)

### Integrations Tab: WhatsApp Credentials
**ShadCN Components Used:**
- `Form` with multiple `Input` fields (WABA ID, Phone Number ID, App ID, Token)
- `Button` (Verify WhatsApp Connection)
- `Alert` (connection status, error messages)
- `Accordion` (help section with setup instructions)
- `ExternalLink` icon for Meta Business docs

### Shared Components
**ShadCN Components Used:**
- `Progress` (wizard progress bar)
- `Breadcrumb` (step navigation)
- `Separator` (visual dividers)
- `ScrollArea` (step content scrolling)
- `Tooltip` (help icons and guidance)

## 3. Form Schemas & Validation

### Zod Schema Structure
```typescript
// lib/form-schemas/brand-basics.ts
export const brandBasicsSchema = z.object({
  business_name: z.string().min(2, "Business name must be at least 2 characters"),
  description: z.string().min(10, "Description must be at least 10 characters"),
  logo_url: z.string().url().optional(),
  currency: z.enum(['NGN', 'USD', 'GHS', 'KES']).default('NGN')
})

// lib/form-schemas/products.ts
export const productSchema = z.object({
  title: z.string().min(2, "Product name required"),
  description: z.string().optional(),
  price_kobo: z.number().min(100, "Minimum price ₦1.00"),
  stock: z.number().min(0, "Stock cannot be negative"),
  sku: z.string().regex(/^[A-Za-z0-9-_]{1,64}$/).optional()
    .describe("Leave blank to auto-generate"),
  condition: z.enum(['new', 'used', 'refurbished'])
    .optional()
    .describe("Product condition (improves Meta acceptance)"),
  category_path: z.string().optional(),
  tags: z.array(z.string()).default([]),
  image_url: z.string().url().optional(),
  additional_image_urls: z.array(z.string().url())
    .optional()
    .describe("Additional product images")
})

// lib/form-schemas/delivery-rates.ts
export const deliveryRateSchema = z.object({
  name: z.string().min(2, "Rate name required"),
  areas_text: z.string().min(5, "Delivery areas required"),
  price_kobo: z.number().min(0, "Price cannot be negative"),
  description: z.string().optional()
})

// lib/form-schemas/payments.ts
export const paymentVerificationSchema = z.object({
  provider: z.enum(['paystack', 'korapay']),
  secret_key: z.string().min(10, "Secret key required"),
  public_key: z.string().min(10, "Public key required"),
  set_as_default: z.boolean().default(true)
})

// lib/form-schemas/whatsapp.ts
export const whatsappVerificationSchema = z.object({
  waba_id: z.string().min(10, "WhatsApp Business Account ID required"),
  phone_number_id: z.string().min(10, "Phone Number ID required"),
  app_id: z.string().min(10, "App ID required"),
  system_user_token: z.string().min(20, "System User Token required")
})
```

### Error States & Loading States
- **Field-level validation**: Real-time validation with debounced API calls
- **Form-level validation**: Comprehensive validation before API submission
- **Network errors**: Retry mechanisms with exponential backoff
- **Loading indicators**: Form-level and field-level spinners
- **Empty states**: Guidance for empty product/delivery rate lists

## 4. Routing Strategy

### Wizard Shell Navigation
```typescript
// Routing structure
/onboarding                    # Main wizard entry
/onboarding/step/1            # Brand basics
/onboarding/step/2            # Products
/onboarding/step/3            # Delivery rates
/onboarding/step/4            # Payments
/onboarding/integrations      # WhatsApp (accessible from any step)
/onboarding/complete          # Success page

// URL state management
- Step validation before navigation
- Browser back/forward support
- Resume capability (return to last completed step)
- Deep linking with proper step validation
```

### Navigation Logic
```typescript
// Step progression rules
const canNavigateToStep = (targetStep: number, currentStep: number, completedSteps: number[]) => {
  // Always allow backward navigation to completed steps
  if (targetStep <= currentStep && completedSteps.includes(targetStep)) return true

  // Allow forward navigation only to next incomplete step
  if (targetStep === Math.max(...completedSteps) + 1) return true

  return false
}
```

## 5. API Integration Mapping

### TypeScript Client Extensions
```typescript
// lib/onboarding-api.ts - Extended API client methods

class OnboardingApiClient extends ApiClient {
  // Step 1: Brand basics
  async updateMerchantProfile(data: UpdateMerchantRequest): Promise<MerchantResponse>
  async uploadMerchantLogo(file: File): Promise<{ logo_url: string }>

  // Step 2: Products
  async createProduct(data: CreateProductRequest): Promise<ProductResponse>
  async updateProduct(id: string, data: Partial<CreateProductRequest>): Promise<ProductResponse>
  async deleteProduct(id: string): Promise<void>
  async uploadProductImage(productId: string, file: File): Promise<{ image_url: string }>
  async getProductMetaSyncStatus(productId: string): Promise<{ status: 'pending' | 'synced' | 'error', reason?: string, updated_at: string }>
  async reSyncProduct(productId: string): Promise<{ ok: boolean }>

  // Step 3: Delivery rates
  async createDeliveryRate(data: CreateDeliveryRateRequest): Promise<DeliveryRateResponse>
  async updateDeliveryRate(id: string, data: Partial<CreateDeliveryRateRequest>): Promise<DeliveryRateResponse>
  async deleteDeliveryRate(id: string): Promise<void>
  async getDeliveryRates(): Promise<DeliveryRateResponse[]>

  // Step 4: Payment verification
  async verifyPaymentProvider(data: VerifyPaymentRequest): Promise<{ verified: boolean; message: string }>
  async getPaymentProviders(): Promise<PaymentProviderResponse[]>

  // Integrations: WhatsApp
  async verifyWhatsAppCredentials(data: VerifyWhatsAppRequest): Promise<{ verified: boolean; message: string }>
  async getWhatsAppStatus(): Promise<{ connected: boolean; phone_number?: string }>
}

// React Query Hooks
export function useProducts() {
  return useQuery({
    queryKey: ['products'],
    queryFn: () => onboardingApi.getProducts()
  })
}

export function useProductMetaSync(productId: string) {
  return useQuery({
    queryKey: ['product', productId, 'meta-sync'],
    queryFn: () => onboardingApi.getProductMetaSyncStatus(productId),
    refetchInterval: (data) => data?.status === 'pending' ? 5000 : false
  })
}

export function useReSyncProduct() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: onboardingApi.reSyncProduct,
    onSuccess: (_, productId) => {
      queryClient.invalidateQueries(['product', productId, 'meta-sync'])
    }
  })
}
```

### API Error Handling Strategy
```typescript
// Specific error handling per API call
const handleApiError = (error: ApiClientError, operation: string) => {
  switch (error.code) {
    case 'VALIDATION_ERROR':
      // Show field-specific errors
      return { type: 'validation', message: error.message, details: error.details }
    case 'EXTERNAL_SERVICE_ERROR':
      // Payment/WhatsApp verification failures
      return { type: 'service', message: 'Verification failed. Please check your credentials.' }
    case 'NETWORK_ERROR':
      // Network connectivity issues
      return { type: 'network', message: 'Connection error. Please try again.', retry: true }
    default:
      return { type: 'unknown', message: error.message }
  }
}
```

## 6. Edge Cases & Error Handling

### Data Persistence Strategy
- **Local Storage**: Auto-save form data every 30 seconds
- **Session Recovery**: Restore partially completed wizard on page refresh
- **Cross-tab Sync**: Prevent concurrent wizard sessions

### Validation Edge Cases
- **Duplicate SKUs**: Real-time SKU availability checking
- **Image Upload Failures**: Retry mechanism with fallback to URL input
- **Payment Verification Timeouts**: 30-second timeout with retry option
- **WhatsApp API Rate Limits**: Exponential backoff with user feedback

### Network Resilience
```typescript
// Retry configuration
const retryConfig = {
  attempts: 3,
  delay: 1000, // Base delay in ms
  backoff: 2,  // Exponential backoff multiplier
  retryableErrors: ['NETWORK_ERROR', 'SERVICE_UNAVAILABLE']
}
```

### Validation Error Recovery
- **Step Validation**: Each step validates independently
- **Cross-step Dependencies**: Products require business setup
- **Required vs Optional**: Clear indication of mandatory fields
- **Progressive Disclosure**: Show advanced options only when needed

## 7. Guide Alignment

### Components > Form Integration
- **Referenced Sections**: Form Components, FormSection, FormActions, TextField, SelectField, SwitchField
- **Applied Patterns**: react-hook-form + zod resolver integration, consistent field validation, FormActions for step navigation

### Components > Data Display
- **Referenced Sections**: DataTable, Badge, EmptyState, StatCard
- **Applied Patterns**: Products and delivery rates tables with proper empty states, status badges for API verification

### Components > Feedback & Overlays
- **Referenced Sections**: Toast, Dialog, Alert, Command Palette
- **Applied Patterns**: Success/error toasts for API operations, confirmation dialogs for destructive actions

### Components > Layout
- **Referenced Sections**: AppShell, PageHeader, FormSection
- **Applied Patterns**: Consistent wizard shell layout, proper form sectioning, step navigation

### **GUIDE-EXTENSION** Proposals

#### 1. Wizard Progress Component
**Name**: `WizardProgress`
**Rationale**: Multi-step workflow visualization not covered in current guide
**Accessibility**: ARIA labels for progress, keyboard navigation support
**API**:
```tsx
<WizardProgress
  steps={['Brand', 'Products', 'Delivery', 'Payments']}
  currentStep={2}
  completedSteps={[0, 1]}
  onStepClick={handleStepNavigation}
/>
```

#### 2. Verification Status Indicator
**Name**: `VerificationStatus`
**Rationale**: API verification states need consistent visual treatment
**Accessibility**: Screen reader announcements for status changes
**API**:
```tsx
<VerificationStatus
  status="verifying" | "verified" | "failed"
  message="Verifying payment credentials..."
  onRetry={handleRetry}
/>
```

#### 3. Image Upload Component
**Name**: `ImageUpload`
**Rationale**: File upload with preview not in current component set
**Accessibility**: Drag-and-drop with keyboard alternatives, alt text requirements
**API**:
```tsx
<ImageUpload
  value={imageUrl}
  onUpload={handleUpload}
  onRemove={handleRemove}
  accept="image/*"
  maxSize={5 * 1024 * 1024} // 5MB
  placeholder="Drop logo here or click to upload"
/>
```

## 8. Testing Strategy

### Unit Tests
- Form validation schemas
- Utility functions
- Custom hooks (useOnboarding, useVerification)

### Integration Tests
- Complete wizard flow
- API integration with mock responses
- Form submission and error handling
- Step navigation logic

### Accessibility Tests
- Keyboard navigation through wizard
- Screen reader compatibility
- Focus management between steps
- ARIA labeling for progress indicators

### Visual Tests
- Responsive design across breakpoints
- Loading states and error states
- Empty states for all data tables
- Cross-browser compatibility

## 9. Performance Considerations

### Code Splitting
- Lazy load step components
- Dynamic imports for verification APIs
- Separate bundles for image upload functionality

### State Management
- Minimize re-renders with React.memo
- Optimize form field watchers
- Debounce real-time validation

### Asset Optimization
- Image compression for uploads
- Progressive image loading
- Optimized bundle sizes

## 10. Implementation Phases

### Phase 1: Core Infrastructure (Days 1-2)
- Onboarding types and constants
- Form schemas and validation
- Main wizard shell and routing
- Step indicator component

### Phase 2: Step Components (Days 3-5)
- Step 1: Brand basics form
- Step 2: Products management
- Step 3: Delivery rates CRUD
- Step 4: Payment verification

### Phase 3: Integrations & Polish (Days 6-7)
- WhatsApp verification tab
- Image upload components
- Error handling and edge cases
- Visual polish and animations

### Phase 4: Testing & Optimization (Day 8)
- Integration tests
- Accessibility testing
- Performance optimization
- Final QA and bug fixes

## 11. Acceptance Criteria Validation

### Functional Requirements ✅
- [ ] 4-step wizard with clear progression
- [ ] Brand basics form with logo upload
- [ ] Product CRUD with image upload and Meta sync status
- [ ] Delivery rates management
- [ ] Payment provider verification
- [ ] WhatsApp credentials verification
- [ ] Data persistence across steps
- [ ] Responsive design on all devices

### Technical Requirements ✅
- [ ] Built with established shadcn/ui components
- [ ] Form validation with Zod schemas
- [ ] React Query for API integration
- [ ] TypeScript strict mode compliance
- [ ] Accessibility WCAG 2.1 AA standards
- [ ] Error boundaries and loading states
- [ ] Unit and integration test coverage

### UX Requirements ✅
- [ ] Intuitive step navigation
- [ ] Clear progress indication
- [ ] Helpful error messages
- [ ] Loading states for all async operations
- [ ] Success confirmation on completion
- [ ] Ability to resume partial progress

This comprehensive implementation plan provides the exact file structure, component mappings, API integrations, and technical specifications needed to build the FE-001 Onboarding Wizard. The plan leverages the established shadcn/ui component library and follows Sayar's architectural patterns while addressing all edge cases and accessibility requirements.