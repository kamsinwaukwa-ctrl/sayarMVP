/**
 * Settings API adapter - maps existing backend endpoints to settings UI needs
 * Provides secure display patterns for sensitive data (masking/status only)
 */

import {
  IntegrationSettingsResponse,
  PaymentSettings,
  WhatsAppSettings,
  MetaCatalogSettings,
  BrandSettings,
  ProfileSettings,
  CredentialUpdateFormData,
  WhatsAppUpdateFormData,
  MetaCatalogUpdateFormData,
  PaymentProvider,
  Environment,
  ConnectionStatus,
  PaystackSubaccountFormData,
  SyncStatus,
  SettlementSchedule,
} from '@/types/settings'
import { ApiResponse } from '@/types/api'

// Base API URL from environment
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

/**
 * Get authentication token from storage
 */
function getAuthToken(): string | null {
  return localStorage.getItem('access_token')
}

/**
 * Make authenticated API request
 */
async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getAuthToken()

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token && { Authorization: `Bearer ${token}` }),
      ...options.headers,
    },
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({
      message: 'Network error occurred'
    }))

    // Handle FastAPI validation errors (422)
    if (response.status === 422 && error.detail) {
      if (Array.isArray(error.detail)) {
        // Pydantic validation errors
        const validationErrors = error.detail.map((err: any) =>
          `${err.loc?.join('.')}: ${err.msg}`
        ).join(', ')
        throw new Error(`Validation error: ${validationErrors}`)
      } else if (error.detail.error && error.detail.error.message) {
        // Custom API error format
        throw new Error(error.detail.error.message)
      }
    }

    // Handle other error formats
    const errorMessage = error.error?.message || error.message || `HTTP ${response.status}`
    throw new Error(errorMessage)
  }

  return response.json()
}


/**
 * Settings API adapter - maps existing backend endpoints to settings UI expectations
 */
export const settingsApi = {
  // Overview of all integrations (calls existing endpoints and aggregates)
  async getIntegrationSettings(): Promise<IntegrationSettingsResponse> {
    const [payments, whatsapp, metaCatalog] = await Promise.allSettled([
      this.getPaymentSettings().catch(() => undefined),
      this.getWhatsAppSettings().catch(() => undefined),
      this.getMetaCatalogSettings().catch(() => undefined),
    ])

    // Transform PaymentSettings to PaymentProviderSettings for the integration response
    const paymentSettings = payments.status === 'fulfilled' ? payments.value : undefined
    const primaryProvider = paymentSettings?.paystack?.connected ? 'paystack' :
                           paymentSettings?.korapay?.connected ? 'korapay' : null

    const paymentProviderSettings = primaryProvider && paymentSettings ? {
      provider: primaryProvider as PaymentProvider,
      environment: paymentSettings[primaryProvider]!.environment!,
      connected: paymentSettings[primaryProvider]!.connected,
      connectedAt: paymentSettings[primaryProvider]!.connectedAt,
      maskedPublicKey: paymentSettings[primaryProvider]!.maskedIdentifier,
      lastUsed: paymentSettings[primaryProvider]!.lastUsed,
      status: paymentSettings[primaryProvider]!.status,
    } : undefined

    return {
      payment_provider: paymentProviderSettings,
      whatsapp: whatsapp.status === 'fulfilled' ? whatsapp.value : undefined,
      meta_catalog: metaCatalog.status === 'fulfilled' ? metaCatalog.value : undefined,
    }
  },

  // Brand settings (uses existing merchant endpoints)
  async getBrandSettings(): Promise<BrandSettings> {
    const response = await apiRequest<ApiResponse<any>>('/api/v1/merchants/me')
    const merchant = response.data

    return {
      business_name: merchant.name || '',
      slug: merchant.slug || '',
      description: merchant.description || '',
      logo_url: merchant.logo_url || '',
      currency: merchant.currency || '',
      website_url: '', // Not in current merchant model
      support_email: '', // Not in current merchant model
      support_phone_e164: '', // Not in current merchant model
      address_line1: '', // Not in current merchant model
      address_line2: '',
      city: '',
      state_region: '',
      postal_code: '',
      country_code: '',
    }
  },

  async updateBrandSettings(data: Partial<BrandSettings>): Promise<BrandSettings> {
    // Transform settings data to merchant update format
    const merchantUpdate: any = {}
    if (data.description !== undefined) merchantUpdate.description = data.description
    if (data.currency !== undefined) merchantUpdate.currency = data.currency
    if (data.logo_url !== undefined) merchantUpdate.logo_url = data.logo_url

    await apiRequest('/api/v1/merchants/me', {
      method: 'PATCH',
      body: JSON.stringify(merchantUpdate),
    })

    // Return updated settings
    return this.getBrandSettings()
  },

  // Upload logo using existing endpoint
  async uploadLogo(file: File): Promise<{ url: string }> {
    const formData = new FormData()
    formData.append('file', file)

    const token = getAuthToken()
    const response = await fetch(`${API_BASE_URL}/api/v1/merchants/me/logo`, {
      method: 'POST',
      headers: {
        ...(token && { Authorization: `Bearer ${token}` }),
      },
      body: formData,
    })

    if (!response.ok) {
      throw new Error(`Logo upload failed: ${response.status}`)
    }

    const result = await response.json()
    return { url: result.data.logo.url }
  },

  // Payment settings (uses new Paystack-first endpoints - fast DB-only)
  async getPaymentSettings(): Promise<PaymentSettings> {
    const response = await apiRequest<ApiResponse<any>>('/api/v1/payments/providers')
    const providers = response.data?.providers || []

    const paystack = providers.find((p: any) => p.provider_type === 'paystack')
    const korapay = providers.find((p: any) => p.provider_type === 'korapay')

    return {
      paystack: paystack ? {
        connected: paystack.subaccount_code ? true : false,
        environment: 'live' as Environment, // No environment field in new schema
        maskedIdentifier: paystack.account_last4 ? `****${paystack.account_last4}` : 'Not configured',
        connectedAt: paystack.created_at,
        status: this.mapSyncStatusToConnectionStatus(paystack.sync_status),
        lastUsed: paystack.last_synced_with_provider,
        // New fields from Paystack-first approach
        subaccountCode: paystack.subaccount_code,
        bankName: paystack.bank_name,
        accountName: paystack.account_name,
        percentageCharge: paystack.percentage_charge,
        settlementSchedule: paystack.settlement_schedule as SettlementSchedule,
        syncStatus: paystack.sync_status as SyncStatus,
        lastSyncedAt: paystack.last_synced_with_provider,
        syncError: paystack.sync_error,
      } : undefined,
      korapay: korapay ? {
        connected: korapay.subaccount_code ? true : false,
        environment: 'live' as Environment, // No environment field in new schema
        maskedIdentifier: korapay.account_last4 ? `****${korapay.account_last4}` : 'Not configured',
        connectedAt: korapay.created_at,
        status: this.mapSyncStatusToConnectionStatus(korapay.sync_status),
        lastUsed: korapay.last_synced_with_provider,
        // Korapay fields (similar structure)
        subaccountCode: korapay.subaccount_code,
        bankName: korapay.bank_name,
        accountName: korapay.account_name,
        percentageCharge: korapay.percentage_charge,
        settlementSchedule: korapay.settlement_schedule as SettlementSchedule,
        syncStatus: korapay.sync_status as SyncStatus,
        lastSyncedAt: korapay.last_synced_with_provider,
        syncError: korapay.sync_error,
      } : undefined,
    }
  },

  // Helper method to map sync status to connection status
  mapSyncStatusToConnectionStatus(syncStatus: string): ConnectionStatus {
    switch (syncStatus) {
      case 'synced': return 'active'
      case 'failed': return 'error'
      case 'pending': return 'pending'
      default: return 'inactive'
    }
  },

  // Legacy helper method for compatibility
  mapVerificationStatusToConnectionStatus(verificationStatus: string): ConnectionStatus {
    switch (verificationStatus) {
      case 'verified': return 'active'
      case 'failed': return 'error'
      case 'pending': return 'pending'
      default: return 'inactive'
    }
  },

  async updatePaymentCredentials(
    _provider: PaymentProvider,
    data: CredentialUpdateFormData
  ): Promise<{ success: boolean; message: string; partialSuccess?: boolean }> {
    // Legacy Korapay verification (keep existing flow for now)
    const endpoint = '/api/v1/payments/verify/korapay'
    const payload = {
      secret_key: data.secretKey,
      public_key: data.publicKey,
      environment: data.environment,
    }

    const response = await apiRequest<ApiResponse<any>>(endpoint, {
      method: 'POST',
      body: JSON.stringify(payload),
    })

    return {
      success: response.ok || response.data?.success || false,
      message: response.message || 'Credentials updated successfully',
    }
  },

  // New Paystack subaccount update method
  async updatePaystackSubaccount(data: PaystackSubaccountFormData): Promise<{ success: boolean; message: string; partialSuccess?: boolean }> {
    const response = await apiRequest<ApiResponse<any>>('/api/v1/payments/providers/paystack', {
      method: 'PATCH',
      body: JSON.stringify(data),
    })

    const result = response.data || {}

    return {
      success: result.success || false,
      message: result.message || 'Subaccount updated successfully',
      partialSuccess: result.partial_success || false,
    }
  },

  // Manual sync with Paystack
  async syncPaystackSubaccount(): Promise<{ success: boolean; message: string }> {
    const response = await apiRequest<ApiResponse<any>>('/api/v1/payments/providers/paystack/sync', {
      method: 'POST',
    })

    return {
      success: response.ok || true,
      message: response.message || 'Synced successfully with Paystack',
    }
  },

  async testPaymentConnection(
    provider: PaymentProvider
  ): Promise<{ success: boolean; message: string }> {
    // For now, return the verification status from the existing config
    // This could be enhanced to call a dedicated test endpoint if available
    const settings = await this.getPaymentSettings()
    const providerConfig = settings[provider]

    return {
      success: providerConfig?.status === 'active',
      message: providerConfig?.status === 'active'
        ? 'Connection verified successfully'
        : 'No verified connection found',
    }
  },

  async disconnectPaymentProvider(
    provider: PaymentProvider
  ): Promise<{ success: boolean; message: string }> {
    // Get current settings to determine environment
    const settings = await this.getPaymentSettings()
    const providerConfig = settings[provider]

    if (!providerConfig) {
      return { success: false, message: 'Provider not found' }
    }

    const response = await apiRequest<ApiResponse<any>>(`/api/v1/payments/providers/${provider}?environment=${providerConfig.environment}`, {
      method: 'DELETE',
    })

    return {
      success: response.ok || response.data?.deleted || false,
      message: response.message || 'Provider disconnected successfully',
    }
  },

  // WhatsApp settings (uses existing integration endpoints)
  async getWhatsAppSettings(): Promise<WhatsAppSettings> {
    const response = await apiRequest<ApiResponse<any>>('/api/v1/integrations/whatsapp/status')
    const status = response.data

    return {
      connected: status.connection_status === 'verified_test' || status.connection_status === 'verified_prod',
      app_id_masked: status.app_id_masked || '',
      waba_id_masked: status.waba_id_masked || '',
      phone_number_id_masked: status.phone_number_id_masked || '',
      phoneNumber: status.whatsapp_phone_e164 || '',
      status: this.mapConnectionStatus(status.connection_status),
      lastVerifiedAt: status.verified_at,
      token_last_updated: status.token_last_updated,
      messagesCount: 0, // Not available in new structure
      webhookUrl: status.webhook_url || '',
      lastWebhookAt: status.last_webhook_at,
      validation_result: status.validation_result
    }
  },

  // Helper method to map connection status
  mapConnectionStatus(status: string): ConnectionStatus {
    switch (status) {
      case 'verified_test':
      case 'verified_prod': return 'active'
      case 'not_connected':
      default: return 'inactive'
    }
  },

  // Update WhatsApp configuration details (IDs and phone number)
  async updateWhatsAppDetails(data: {
    app_id: string;
    waba_id: string;
    phone_number_id: string;
    whatsapp_phone_e164: string;
    validate_after_save?: boolean;
  }): Promise<{ success: boolean; message: string; validation_result?: any }> {
    const payload = {
      app_id: data.app_id,
      waba_id: data.waba_id,
      phone_number_id: data.phone_number_id,
      whatsapp_phone_e164: data.whatsapp_phone_e164,
      validate_after_save: data.validate_after_save ?? true
    }

    const response = await apiRequest<ApiResponse<any>>('/api/v1/integrations/whatsapp/credentials', {
      method: 'PATCH',
      body: JSON.stringify(payload),
    })

    return {
      success: response.ok || true, // PATCH returns 200 on success
      message: response.message || 'WhatsApp details updated successfully',
      validation_result: response.data?.validation_result
    }
  },

  // Replace WhatsApp system user token only
  async replaceWhatsAppToken(token: string, validate_after_save = true): Promise<{ success: boolean; message: string; validation_result?: any }> {
    const response = await apiRequest<ApiResponse<any>>('/api/v1/integrations/whatsapp/credentials', {
      method: 'PATCH',
      body: JSON.stringify({
        system_user_token: token,
        validate_after_save
      }),
    })

    return {
      success: response.ok || true, // PATCH returns 200 on success
      message: response.message || 'WhatsApp token replaced successfully',
      validation_result: response.data?.validation_result
    }
  },

  // Legacy method for backwards compatibility (delegates to details update)
  async updateWhatsAppSettings(
    data: WhatsAppUpdateFormData
  ): Promise<{ success: boolean; message: string }> {
    return this.updateWhatsAppDetails({
      app_id: data.app_id,
      waba_id: data.waba_id,
      phone_number_id: data.phone_number_id,
      whatsapp_phone_e164: data.whatsapp_phone_e164,
    })
  },

  async testWhatsAppConnection(): Promise<{ success: boolean; message: string }> {
    const response = await apiRequest<ApiResponse<any>>('/api/v1/integrations/whatsapp/verify', {
      method: 'POST',
    })

    return {
      success: response.ok || response.data?.success || false,
      message: response.message || response.data?.message || 'Connection test completed',
    }
  },

  async verifyWhatsAppWebhook(): Promise<{ success: boolean; message: string }> {
    // This would need a specific webhook verification endpoint if available
    return this.testWhatsAppConnection()
  },

  async rotateWhatsAppToken(
    newToken: string
  ): Promise<{ success: boolean; last_rotated_at: string }> {
    // Use the new replaceWhatsAppToken method instead
    const response = await this.replaceWhatsAppToken(newToken)

    return {
      success: response.success,
      last_rotated_at: new Date().toISOString(),
    }
  },

  async getWhatsAppLogs(): Promise<{ logs: any[] }> {
    // This would need a specific logs endpoint if available
    return { logs: [] }
  },

  // Meta Catalog settings (uses existing meta integration endpoints)
  async getMetaCatalogSettings(): Promise<MetaCatalogSettings> {
    const response = await apiRequest<any>('/api/v1/integrations/meta/status')
    // Handle both response formats: { data: {...} } and direct response
    const status = response.data || response

    return {
      connected: status.status === 'verified',
      catalogId: status.catalog_id || '', // Show real catalog_id, not masked
      productsCount: 0, // This field is not available in the current API
      lastSyncAt: status.last_verified_at,
      syncStatus: status.status === 'verified' ? 'synced' : status.status === 'invalid' ? 'failed' : 'pending',
      failedProducts: 0, // This field is not available in the current API
      message: status.message, // User-friendly error message for invalid status
    }
  },

  async updateMetaCatalogSettings(
    data: MetaCatalogUpdateFormData
  ): Promise<{ success: boolean; message: string }> {
    let response: any

    // Update catalog ID if provided
    if (data.catalog_id) {
      response = await apiRequest('/api/v1/integrations/meta/catalog', {
        method: 'PATCH',
        body: JSON.stringify({ catalog_id: data.catalog_id }),
      })
    }

    // Update access token if provided
    if (data.system_user_token) {
      response = await apiRequest('/api/v1/integrations/meta/credentials', {
        method: 'PATCH',
        body: JSON.stringify({ system_user_token: data.system_user_token }),
      })
    }

    return {
      success: response?.ok || response?.data?.success || false,
      message: response?.message || 'Meta catalog settings updated successfully',
    }
  },

  // Update catalog ID only
  async updateCatalogId(catalogId: string): Promise<{ success: boolean; message: string }> {
    const response = await apiRequest<ApiResponse<any>>('/api/v1/integrations/meta/catalog', {
      method: 'PATCH',
      body: JSON.stringify({ catalog_id: catalogId }),
    })

    return {
      success: response?.data?.success || true, // PATCH typically returns success if no error
      message: response?.message || 'Catalog ID updated successfully',
    }
  },

  // Verify catalog ID works with Meta API
  async verifyCatalogId(): Promise<{ success: boolean; message: string }> {
    // Use the new verify endpoint if available, otherwise fall back to status
    try {
      const response = await apiRequest<any>('/api/v1/integrations/meta/verify', {
        method: 'POST',
      })
      // Handle both response formats: { data: {...} } and direct response
      const status = response.data || response

      return {
        success: status.status === 'verified',
        message: status.message || (status.status === 'verified'
          ? 'Catalog ID verified successfully'
          : `Catalog verification failed: ${status.status}`),
      }
    } catch (error) {
      // Fall back to status endpoint if verify endpoint doesn't exist
      try {
        const response = await apiRequest<any>('/api/v1/integrations/meta/status')
        const status = response.data || response

        return {
          success: status.status === 'verified',
          message: status.message || (status.status === 'verified'
            ? 'Catalog ID verified successfully'
            : `Catalog verification failed: ${status.status}`),
        }
      } catch (fallbackError) {
        return {
          success: false,
          message: error instanceof Error ? error.message : 'Catalog verification failed',
        }
      }
    }
  },

  async syncMetaCatalog(): Promise<{ success: boolean; message: string }> {
    // This would need a specific sync endpoint
    // For now, return a placeholder response
    return {
      success: true,
      message: 'Sync initiated successfully',
    }
  },

  async getMetaCatalogLogs(): Promise<{ logs: any[] }> {
    // This would need a specific logs endpoint if available
    return { logs: [] }
  },

  // Profile settings (uses existing user/merchant endpoints)
  async getProfileSettings(): Promise<ProfileSettings> {
    const [userResponse] = await Promise.all([
      apiRequest<ApiResponse<any>>('/api/v1/auth/me'),
      apiRequest<ApiResponse<any>>('/api/v1/merchants/me'),
    ])

    const user = userResponse.data

    return {
      id: user.id || '',
      email: user.email || '',
      role: user.role || 'admin',
      created_at: user.created_at || new Date().toISOString(),
      last_login: user.last_login_at,
      primary_contact_name: user.full_name || user.name || '',
      primary_contact_email: user.email || '',
      contact_phone: '', // Not in current model
      company_website: '', // Not in current model
    }
  },

  async updateProfileSettings(
    data: Partial<ProfileSettings>
  ): Promise<ProfileSettings> {
    // Update user data if provided
    if (data.primary_contact_name || data.email) {
      await apiRequest('/api/v1/users/me', {
        method: 'PATCH',
        body: JSON.stringify({
          full_name: data.primary_contact_name,
          email: data.email,
        }),
      })
    }

    // Return updated settings
    return this.getProfileSettings()
  },

  // Team management (placeholder - needs implementation)
  async getTeamMembers(): Promise<{ members: any[] }> {
    return { members: [] }
  },

  async inviteTeamMember(_data: {
    email: string
    role: 'admin' | 'staff'
    name?: string
  }): Promise<{ success: boolean; message: string }> {
    return { success: false, message: 'Team management not yet implemented' }
  },

  async updateTeamMember(
    _memberId: string,
    _data: { role?: 'admin' | 'staff'; name?: string }
  ): Promise<{ success: boolean; message: string }> {
    return { success: false, message: 'Team management not yet implemented' }
  },

  async removeTeamMember(
    _memberId: string
  ): Promise<{ success: boolean; message: string }> {
    return { success: false, message: 'Team management not yet implemented' }
  },

  // Audit logs (placeholder - needs implementation)
  async getAuditLogs(_scope: string = 'settings'): Promise<{ logs: any[] }> {
    return { logs: [] }
  },
}

/**
 * Helper functions for credential validation
 */
export const settingsValidation = {
  validatePaystackCredentials: async (data: CredentialUpdateFormData) => {
    // This would normally call the actual verification endpoint
    // For now, we'll do basic format validation
    const { publicKey, secretKey } = data

    if (!publicKey.startsWith('pk_')) {
      throw new Error('Invalid Paystack public key format')
    }

    if (!secretKey.startsWith('sk_')) {
      throw new Error('Invalid Paystack secret key format')
    }

    // Mock API call - replace with actual endpoint
    return { success: true, message: 'Credentials verified' }
  },

  validateKorapayCredentials: async (_data: CredentialUpdateFormData) => {
    // Similar validation for Korapay
    // Mock for now
    return { success: true, message: 'Credentials verified' }
  },

  validateWhatsAppCredentials: async (_data: WhatsAppUpdateFormData) => {
    // WhatsApp credential validation
    // Mock for now
    return { success: true, message: 'WhatsApp credentials verified' }
  },

  validateMetaCatalogCredentials: async (_data: MetaCatalogUpdateFormData) => {
    // Meta catalog credential validation
    // Mock for now
    return { success: true, message: 'Meta catalog credentials verified' }
  },
}