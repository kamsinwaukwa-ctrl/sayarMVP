/**
 * Constants and enums for the onboarding wizard
 */

// LocalStorage keys
export const STORAGE_KEYS = {
  ONBOARDING_PROGRESS: 'onboarding.step',
  ONBOARDING_DRAFT: 'onboarding.draft',
  ONBOARDING_FORM_DATA: 'onboarding.form_data'
} as const

// Event tracking constants
export const ONBOARDING_EVENTS = {
  WIZARD_STARTED: 'onboarding.wizard_started',
  STEP_COMPLETED: 'onboarding.step_completed',
  STEP_FAILED: 'onboarding.step_failed',
  WIZARD_COMPLETED: 'onboarding.wizard_completed',
  VERIFICATION_STARTED: 'onboarding.verification_started',
  VERIFICATION_SUCCESS: 'onboarding.verification_success',
  VERIFICATION_FAILED: 'onboarding.verification_failed',
  IMAGE_UPLOAD_SUCCESS: 'onboarding.image_upload_success',
  IMAGE_UPLOAD_FAILED: 'onboarding.image_upload_failed',
  FORM_AUTO_SAVED: 'onboarding.form_auto_saved'
} as const

// Wizard configuration
export const WIZARD_CONFIG = {
  TOTAL_STEPS: 5,
  AUTO_SAVE_INTERVAL: 30000, // 30 seconds
  MAX_IMAGE_SIZE: 5 * 1024 * 1024, // 5MB
  SUPPORTED_IMAGE_FORMATS: ['image/png', 'image/jpeg', 'image/jpg', 'image/webp'],
  MAX_ADDITIONAL_IMAGES: 10
} as const

// Step information - normalized to 5 steps to match router and StepIndicator
export const WIZARD_STEPS = [
  {
    id: 1,
    title: 'Brand Basics',
    description: 'Set up your business information',
    icon: 'Building'
  },
  {
    id: 2,
    title: 'Meta Catalog',
    description: 'Connect your catalog',
    icon: 'Link'
  },
  {
    id: 3,
    title: 'Products',
    description: 'Add your product catalog',
    icon: 'Package'
  },
  {
    id: 4,
    title: 'Delivery',
    description: 'Configure delivery rates',
    icon: 'Truck'
  },
  {
    id: 5,
    title: 'Payments',
    description: 'Verify payment providers',
    icon: 'CreditCard'
  }
] as const

// Currency options
export const CURRENCY_OPTIONS = [
  { value: 'NGN', label: 'Nigerian Naira (₦)', symbol: '₦' },
  { value: 'USD', label: 'US Dollar ($)', symbol: '$' },
  { value: 'GHS', label: 'Ghanaian Cedi (₵)', symbol: '₵' },
  { value: 'KES', label: 'Kenyan Shilling (KSh)', symbol: 'KSh' }
] as const

// Product condition options
export const PRODUCT_CONDITIONS = [
  { value: 'new', label: 'New' },
  { value: 'used', label: 'Used' },
  { value: 'refurbished', label: 'Refurbished' }
] as const

// Payment provider options
export const PAYMENT_PROVIDERS = [
  {
    key: 'paystack',
    name: 'Paystack',
    description: 'Accept payments via cards, bank transfers, and mobile money',
    logo: '/icons/paystack.svg'
  },
  {
    key: 'korapay',
    name: 'Korapay',
    description: 'Nigerian payment gateway with multiple payment options',
    logo: '/icons/korapay.svg'
  }
] as const

// Test IDs for automated testing
export const TEST_IDS = {
  WIZARD_SHELL: 'onboarding-wizard',
  STEP_1: 'step-1',
  STEP_2: 'step-2',
  STEP_3: 'step-3',
  STEP_4: 'step-4',
  NEXT_BTN: 'next-btn',
  BACK_BTN: 'back-btn',
  VERIFY_PAYMENTS: 'verify-payments',
  VERIFY_WHATSAPP: 'verify-whatsapp',
  PRODUCTS_TABLE: 'products-table',
  DELIVERY_RATES_TABLE: 'delivery-rates-table',
  ADD_PRODUCT_BTN: 'add-product-btn',
  BUSINESS_NAME: 'business-name',
  DESCRIPTION: 'description',
  PRODUCT_TITLE: 'product-title',
  PRODUCT_PRICE: 'product-price',
  PRODUCT_STOCK: 'product-stock',
  SAVE_PRODUCT_BTN: 'save-product-btn',
  ONBOARDING_COMPLETE: 'onboarding-complete'
} as const