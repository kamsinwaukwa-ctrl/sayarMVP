/**
 * Onboarding types and interfaces for the 4-step merchant setup wizard
 */

// Domain Types
export type Currency = 'NGN' | 'USD' | 'GHS' | 'KES'
export type MetaSyncStatus = 'pending' | 'synced' | 'error'
export type OnboardingStep = 1 | 2 | 3 | 4 | 5
export type VerificationStatus = 'idle' | 'verifying' | 'verified' | 'failed'

// Enhanced Meta sync details interface
export interface MetaSyncDetails {
  status: MetaSyncStatus
  reason?: string
  updated_at?: string           // Maps to last_synced_at in frontend
  sync_version?: number
  error_details?: string
  retry_count?: number
}

export interface Product {
  id: string
  title: string
  description?: string
  price_kobo: number
  stock: number
  sku?: string
  brand?: string          // readonly, auto-generated after save
  mpn?: string           // readonly, auto-generated after save
  gtin?: string          // readonly, auto-generated after save
  category_path?: string
  tags: string[]
  image_url?: string
  additional_image_urls?: string[]
  condition?: 'new' | 'used' | 'refurbished'
  meta_sync?: MetaSyncDetails
}

export interface DeliveryRate {
  id: string
  name: string
  areas_text: string
  price_kobo: number
  description?: string
  active: boolean
}

export interface PaymentProvider {
  key: 'paystack' | 'korapay'
  name: string
  verified?: boolean
}

export interface OnboardingState {
  currentStep: OnboardingStep
  completedSteps: OnboardingStep[]
  canNavigateToStep: (step: OnboardingStep) => boolean
  completeStep: (step: OnboardingStep) => void
  goToStep: (step: OnboardingStep) => void
}

// Form Data Types (for react-hook-form)
export interface BrandBasicsFormData {
  description: string
  currency: Currency
  logo_url?: string
}

export interface ProductFormData {
  title: string
  description?: string
  price_kobo: number
  stock: number
  sku?: string
  condition?: 'new' | 'used' | 'refurbished'
  category_path?: string
  tags: string[]
}

export interface DeliveryRateFormData {
  name: string
  areas_text: string
  price_kobo: number
  description?: string
}

export interface PaymentVerificationFormData {
  provider: 'paystack' | 'korapay'
  secret_key: string
  public_key: string
}

export interface WhatsAppVerificationFormData {
  waba_id: string
  phone_number_id: string
  app_id: string
  system_user_token: string
}

// API Request Types (for API client methods)
export interface CreateProductRequest {
  title: string
  description?: string
  price_kobo: number
  stock: number
  sku?: string
  condition?: 'new' | 'used' | 'refurbished'
  category_path?: string
  tags?: string[]
}

export interface CreateDeliveryRateRequest {
  name: string
  areas_text: string
  price_kobo: number
  description?: string
}

export interface PaymentVerificationData {
  provider: 'paystack' | 'korapay'
  secret_key: string
  public_key: string
}

export interface WhatsAppVerificationData {
  waba_id: string
  phone_number_id: string
  app_id: string
  system_user_token: string
}

export interface MetaCredentialsData {
  catalog_id: string
  app_id: string
  system_user_token: string
  waba_id?: string
}

export interface MetaCatalogOnlyData {
  catalog_id: string
}

export interface MetaCredentialsResponse {
  success: boolean
  message: string
  status: 'pending' | 'verified' | 'invalid' | 'expired'
  catalog_name?: string
  verification_timestamp?: string
}

export interface MetaIntegrationStatusResponse {
  status: 'pending' | 'verified' | 'invalid' | 'expired'
  catalog_id?: string
  catalog_name?: string
  app_id?: string
  waba_id?: string
  last_verified_at?: string
  error?: string
  error_code?: string
  last_error_at?: string
  message?: string
}

// Utility Types
export interface VerificationResult {
  verified: boolean
  message: string
  provider?: string
}

export interface MetaSyncResult {
  status: MetaSyncStatus
  reason?: string
  updated_at?: string
}

// FE-001.1 Enhanced Meta Sync Types
export interface MetaSyncTriggerRequest {
  product_id: string
}

export interface MetaSyncTriggerResponse {
  status: "queued" | "in_progress" | "completed" | "failed"
  message: string
  job_id?: string
}

// Onboarding Progress Types
export interface OnboardingProgressData {
  brand_basics: boolean
  meta_catalog: boolean
  products: boolean
  delivery_rates: boolean
  payments: boolean
}