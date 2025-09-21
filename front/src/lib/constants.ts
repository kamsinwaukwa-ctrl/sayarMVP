/**
 * Design tokens and application constants
 * Centralized configuration for consistent theming and behavior
 */

// Design system tokens
export const DESIGN_TOKENS = {
  // Spacing scale (Tailwind-based)
  spacing: {
    xs: '0.25rem', // 1
    sm: '0.5rem',  // 2
    md: '1rem',    // 4
    lg: '1.5rem',  // 6
    xl: '2rem',    // 8
    '2xl': '3rem', // 12
    '3xl': '4rem', // 16
  },

  // Border radius scale
  radius: {
    none: '0',
    sm: '0.25rem',
    md: '0.5rem',
    lg: '0.75rem',
    xl: '1rem',
    full: '9999px',
  },

  // Typography scale
  fontSize: {
    xs: '0.75rem',
    sm: '0.875rem',
    base: '1rem',
    lg: '1.125rem',
    xl: '1.25rem',
    '2xl': '1.5rem',
    '3xl': '1.875rem',
    '4xl': '2.25rem',
  },

  // Animation durations
  animation: {
    fast: '150ms',
    normal: '300ms',
    slow: '500ms',
  },

  // Breakpoints
  breakpoints: {
    mobile: '375px',
    tablet: '768px',
    desktop: '1440px',
  },
} as const

// Application configuration
export const APP_CONFIG = {
  name: 'Sayar Dashboard',
  description: 'WhatsApp Commerce Platform for SMEs',
  version: '1.0.0',

  // Pagination defaults
  pagination: {
    defaultPageSize: 10,
    pageSizeOptions: [5, 10, 20, 50],
    maxPageSize: 100,
  },

  // Form defaults
  form: {
    debounceMs: 300,
    autoSaveMs: 2000,
  },

  // File upload constraints
  upload: {
    maxFileSize: 5 * 1024 * 1024, // 5MB
    allowedImageTypes: ['image/jpeg', 'image/png', 'image/webp'],
    maxImageDimension: 2048,
  },

  // Commerce defaults
  commerce: {
    defaultCurrency: 'NGN',
    currencySymbol: '₦',
    decimalPlaces: 2,
    minPrice: 0.01,
    maxPrice: 10000000,
  },
} as const

// Status definitions for commerce entities
export const ORDER_STATUSES = {
  PENDING: 'pending',
  PROCESSING: 'processing',
  COMPLETED: 'completed',
  CANCELLED: 'cancelled',
  REFUNDED: 'refunded',
} as const

export const PAYMENT_STATUSES = {
  PAID: 'paid',
  UNPAID: 'unpaid',
  FAILED: 'failed',
  REFUNDED: 'refunded',
} as const

export const STOCK_STATUSES = {
  IN_STOCK: 'in-stock',
  LOW_STOCK: 'low-stock',
  OUT_OF_STOCK: 'out-of-stock',
} as const

export const USER_ROLES = {
  ADMIN: 'admin',
  STAFF: 'staff',
} as const

// Navigation structure
export const NAVIGATION_ITEMS = [
  {
    label: 'Dashboard',
    href: '/dashboard',
    icon: 'LayoutDashboard',
    active: false,
  },
  {
    label: 'Products',
    href: '/products',
    icon: 'Package',
    active: false,
    children: [
      { label: 'All Products', href: '/products' },
      { label: 'Add Product', href: '/products/new' },
      { label: 'Categories', href: '/products/categories' },
    ],
  },
  {
    label: 'Orders',
    href: '/orders',
    icon: 'ShoppingCart',
    active: false,
    badge: 12,
  },
  {
    label: 'Customers',
    href: '/customers',
    icon: 'Users',
    active: false,
  },
  {
    label: 'Analytics',
    href: '/analytics',
    icon: 'BarChart3',
    active: false,
  },
  {
    label: 'Settings',
    href: '/settings',
    icon: 'Settings',
    active: false,
    children: [
      { label: 'Business Profile', href: '/settings/business' },
      { label: 'WhatsApp Setup', href: '/settings/whatsapp' },
      { label: 'Payment Methods', href: '/settings/payments' },
      { label: 'Team & Users', href: '/settings/team' },
    ],
  },
] as const

// Theme configuration
export const THEME_CONFIG = {
  defaultTheme: 'light',
  themes: ['light', 'dark'],

  // CSS custom properties for theming
  cssVars: {
    light: {
      // Commerce-specific semantic colors
      '--success': '142 71% 45%',
      '--success-foreground': '210 40% 98%',
      '--warning': '38 92% 50%',
      '--warning-foreground': '222.2 84% 4.9%',
      '--info': '199 89% 48%',
      '--info-foreground': '210 40% 98%',

      // Status colors for commerce
      '--status-pending': '43 74% 66%',
      '--status-processing': '199 89% 48%',
      '--status-completed': '142 71% 45%',
      '--status-cancelled': '0 84.2% 60.2%',
      '--status-refunded': '221.2 83.2% 53.3%',
    },
    dark: {
      // Dark theme overrides
      '--success': '142 71% 45%',
      '--success-foreground': '210 40% 98%',
      '--warning': '38 92% 50%',
      '--warning-foreground': '222.2 84% 4.9%',
      '--info': '199 89% 48%',
      '--info-foreground': '210 40% 98%',
    },
  },
} as const

// Keyboard shortcuts
export const KEYBOARD_SHORTCUTS = {
  COMMAND_PALETTE: ['cmd+k', 'ctrl+k'],
  SEARCH: ['cmd+/', 'ctrl+/'],
  NEW_PRODUCT: ['cmd+shift+p', 'ctrl+shift+p'],
  NEW_ORDER: ['cmd+shift+o', 'ctrl+shift+o'],
  SETTINGS: ['cmd+,', 'ctrl+,'],
} as const

// API configuration
export const API_CONFIG = {
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  timeout: 30000,
  retryAttempts: 3,
  retryDelay: 1000,

  endpoints: {
    auth: {
      login: '/api/v1/auth/login',
      register: '/api/v1/auth/register',
      logout: '/api/v1/auth/logout',
      me: '/api/v1/auth/me',
    },
    products: {
      list: '/api/v1/products',
      create: '/api/v1/products',
      detail: '/api/v1/products',
      update: '/api/v1/products',
      delete: '/api/v1/products',
    },
    orders: {
      list: '/api/v1/orders',
      create: '/api/v1/orders',
      detail: '/api/v1/orders',
      update: '/api/v1/orders',
    },
    merchants: {
      me: '/api/v1/merchants/me',
      update: '/api/v1/merchants/me',
    },
  },
} as const

// Development flags
export const DEV_FLAGS = {
  UI_SHOWCASE: import.meta.env.VITE_UI_SHOWCASE === 'true',
  DEBUG_MODE: import.meta.env.DEV,
  MOCK_API: import.meta.env.VITE_MOCK_API === 'true',
} as const