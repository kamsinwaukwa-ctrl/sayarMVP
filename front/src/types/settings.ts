// Settings domain types for secure configuration management

export type UserRole = 'admin' | 'staff'
export type ConnectionStatus = 'active' | 'inactive' | 'error' | 'webhook_failed' | 'pending'
export type PaymentProvider = 'paystack' | 'korapay'
export type Environment = 'test' | 'live'
export type SyncStatus = 'synced' | 'pending' | 'failed'
export type SettlementSchedule = 'AUTO' | 'WEEKLY' | 'MONTHLY' | 'MANUAL'

export interface ProviderConnection {
  connected: boolean
  environment?: Environment
  maskedIdentifier?: string
  connectedAt?: string
  status: ConnectionStatus
  lastUsed?: string
  // New Paystack-first fields
  subaccountCode?: string
  bankName?: string
  accountName?: string
  percentageCharge?: number
  settlementSchedule?: SettlementSchedule
  syncStatus?: SyncStatus
  lastSyncedAt?: string
  syncError?: string
}

export interface PaymentSettings {
  paystack?: ProviderConnection
  korapay?: ProviderConnection
}

export interface ValidationResult {
  is_valid: boolean
  tested_at: string
  error_message?: string
  error_code?: string
  business_name?: string
  phone_number_display?: string
}

export interface WhatsAppSettings {
  connected: boolean
  app_id_masked?: string // Masked app ID (e.g., "684132••••••5988")
  waba_id_masked?: string // Masked WABA ID (e.g., "1871••••••8542")
  phone_number_id_masked?: string // Masked phone number ID (e.g., "8233••••••6057")
  phoneNumber?: string // WhatsApp phone number in E164 format
  status: ConnectionStatus
  lastVerifiedAt?: string
  token_last_updated?: string // When system user token was last updated
  webhookUrl?: string // Webhook URL for receiving WhatsApp events
  lastWebhookAt?: string // When the last webhook was received
  messagesCount: number // Legacy field, kept for compatibility
  validation_result?: ValidationResult // Latest validation test results
}

export interface MetaCatalogSettings {
  connected: boolean
  catalogId?: string
  productsCount: number
  lastSyncAt?: string
  syncStatus: 'synced' | 'pending' | 'failed' | 'never'
  failedProducts: number
  message?: string // User-friendly error message for invalid status
}

export interface BrandSettings {
  business_name: string
  slug: string
  description?: string
  currency: string
  logo_url?: string
  website_url?: string
  support_email?: string
  support_phone_e164?: string
  address_line1?: string
  address_line2?: string
  city?: string
  state_region?: string
  postal_code?: string
  country_code?: string
}

export interface ProfileSettings {
  id: string
  email: string
  role: UserRole
  created_at: string
  last_login?: string
  primary_contact_name?: string
  primary_contact_email?: string
  contact_phone?: string
  company_website?: string
}

// Form data types for secure credential updates
export interface CredentialUpdateFormData {
  publicKey: string
  secretKey: string
  environment: Environment
}

// Paystack subaccount update form data (new Paystack-first approach)
export interface PaystackSubaccountFormData {
  business_name?: string
  bank_code?: string
  account_number?: string
  percentage_charge?: number
  settlement_schedule?: SettlementSchedule
}

export interface WhatsAppUpdateFormData {
  waba_id: string
  phone_number_id: string
  app_id: string
  whatsapp_phone_e164: string
  system_user_token: string
}

// Separate interfaces for the two different update flows
export interface WhatsAppDetailsUpdateData {
  app_id: string
  waba_id: string
  phone_number_id: string
  whatsapp_phone_e164: string
}

export interface WhatsAppTokenReplaceData {
  system_user_token: string
}

export interface MetaCatalogUpdateFormData {
  catalog_id: string
  app_id: string
  system_user_token: string
}

// API Response types (never expose full credentials)
export interface PaymentProviderSettings {
  provider: PaymentProvider
  environment: Environment
  connected: boolean
  connectedAt?: string
  maskedPublicKey?: string // pk_test_••••••••1234
  maskedAccount?: string   // ••••••••5678
  lastUsed?: string
  status: ConnectionStatus
}

export interface IntegrationSettingsResponse {
  payment_provider?: PaymentProviderSettings
  whatsapp?: WhatsAppSettings
  meta_catalog?: MetaCatalogSettings
}

// Settings tabs
export type SettingsTab = 'brand' | 'catalog' | 'whatsapp' | 'payments' | 'profile'

export interface SettingsTabConfig {
  id: SettingsTab
  label: string
  description: string
  icon: string
  requiresAdmin?: boolean
}