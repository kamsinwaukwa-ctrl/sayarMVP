import { SettingsTabConfig } from '@/types/settings'

// Settings tabs configuration
export const SETTINGS_TABS: SettingsTabConfig[] = [
  {
    id: 'brand',
    label: 'Brand',
    description: 'Business identity and branding',
    icon: 'Building',
  },
  {
    id: 'catalog',
    label: 'Meta Catalog',
    description: 'Product catalog synchronization',
    icon: 'Store',
    requiresAdmin: true,
  },
  {
    id: 'whatsapp',
    label: 'WhatsApp',
    description: 'WhatsApp Business integration',
    icon: 'MessageCircle',
    requiresAdmin: true,
  },
  {
    id: 'payments',
    label: 'Payments',
    description: 'Payment provider configuration',
    icon: 'CreditCard',
    requiresAdmin: true,
  },
  {
    id: 'profile',
    label: 'Profile',
    description: 'Account and team management',
    icon: 'Users',
    requiresAdmin: true,
  },
]

// Settings events for tracking
export const SETTINGS_EVENTS = {
  SETTINGS_OPENED: 'settings.opened',
  TAB_CHANGED: 'settings.tab_changed',
  CREDENTIAL_UPDATE_STARTED: 'settings.credential_update_started',
  CREDENTIAL_UPDATE_SUCCESS: 'settings.credential_update_success',
  CREDENTIAL_UPDATE_FAILED: 'settings.credential_update_failed',
  CONNECTION_TEST_STARTED: 'settings.connection_test_started',
  CONNECTION_TEST_SUCCESS: 'settings.connection_test_success',
  CONNECTION_TEST_FAILED: 'settings.connection_test_failed',
  UNAUTHORIZED_ACCESS_ATTEMPT: 'settings.unauthorized_access_attempt',
} as const

// Status colors and badges
export const STATUS_VARIANTS = {
  active: { color: 'green', label: 'Active' },
  inactive: { color: 'red', label: 'Inactive' },
  error: { color: 'red', label: 'Error' },
  webhook_failed: { color: 'orange', label: 'Webhook Failed' },
  pending: { color: 'yellow', label: 'Pending' },
} as const

// Provider configurations
export const PAYMENT_PROVIDERS = {
  paystack: {
    name: 'Paystack',
    description: 'Accept payments from customers across Africa',
    features: ['Card payments', 'Bank transfers', 'USSD', 'Mobile money'],
    color: 'green',
  },
  korapay: {
    name: 'Korapay',
    description: 'Fast and secure payment processing for Nigeria',
    features: ['Card payments', 'Bank transfers', 'QR codes', 'Split payments'],
    color: 'blue',
  },
} as const

// Sync status configurations
export const SYNC_STATUS = {
  synced: { color: 'green', label: 'Synced' },
  pending: { color: 'yellow', label: 'Syncing' },
  failed: { color: 'red', label: 'Failed' },
  never: { color: 'gray', label: 'Never synced' },
} as const

// Form validation constants
export const VALIDATION = {
  MAX_DESCRIPTION_LENGTH: 280,
  MIN_SLUG_LENGTH: 3,
  MAX_LOGO_SIZE_MB: 2,
  MIN_LOGO_DIMENSIONS: 256,
} as const