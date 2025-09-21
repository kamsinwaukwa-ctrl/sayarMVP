/**
 * Extended API client for onboarding endpoints
 * Extends the base ApiClient with onboarding-specific methods
 */

import { ApiClient } from '@/lib/api-client'
import { Merchant } from '@/types/merchant';
import {
  Product,
  DeliveryRate,
  PaymentProvider,
  BrandBasicsFormData,
  CreateProductRequest,
  CreateDeliveryRateRequest,
  PaymentVerificationData,
  WhatsAppVerificationData,
  MetaCredentialsData,
  MetaSyncDetails,
  MetaSyncTriggerResponse,
  OnboardingProgressData
} from '@/types/onboarding'

export class OnboardingApiClient extends ApiClient {
  // Step 1: Brand Basics
  async updateMerchantProfile(data: BrandBasicsFormData): Promise<Merchant> {
    return this.patch('/api/v1/merchants/me', data)
  }

  async uploadMerchantLogo(file: File): Promise<{ logo_url: string }> {
    const formData = new FormData()
    formData.append('file', file)
    return this.post('/api/v1/merchants/me/logo', formData)
  }

  // Step 2: Products
  async getProducts(): Promise<Product[]> {
    return this.get<Product[]>('/api/v1/products')
  }

  async createProduct(data: CreateProductRequest): Promise<Product> {
    return this.post<Product>('/api/v1/products', data)
  }

  async updateProduct(id: string, data: Partial<CreateProductRequest>): Promise<Product> {
    return this.put<Product>(`/api/v1/products/${id}`, data)
  }

  async deleteProduct(id: string): Promise<{ ok: boolean }> {
    return this.delete(`/api/v1/products/${id}`)
  }

  async uploadProductImage(productId: string, file: File): Promise<{ image_url: string }> {
    const formData = new FormData()
    formData.append('file', file)
    // Note: POST /products/{id}/image can be called multiple times to add extras;
    // BE returns all images via additional_image_urls array
    // After upload, call getProducts() or invalidate React Query cache to refresh UI
    return this.post(`/api/v1/products/${productId}/image`, formData)
  }

  // Alias for clarity when uploading additional images
  uploadAdditionalProductImage = this.uploadProductImage

  async getProductMetaSyncStatus(productId: string): Promise<MetaSyncDetails> {
    const response = await this.get(`/api/v1/products/${productId}/meta-sync`) as MetaSyncDetails
    return response
  }

  async reSyncProduct(productId: string): Promise<MetaSyncTriggerResponse> {
    return this.post(`/api/v1/products/${productId}/meta-sync`)
  }

  // Step 3: Delivery Rates
  async getDeliveryRates(): Promise<DeliveryRate[]> {
    return this.get('/api/v1/delivery-rates')
  }

  async createDeliveryRate(data: CreateDeliveryRateRequest): Promise<DeliveryRate> {
    return this.post('/api/v1/delivery-rates', data)
  }

  async updateDeliveryRate(id: string, data: Partial<CreateDeliveryRateRequest>): Promise<DeliveryRate> {
    return this.put(`/api/v1/delivery-rates/${id}`, data)
  }

  async deleteDeliveryRate(id: string): Promise<{ ok: boolean }> {
    return this.delete(`/api/v1/delivery-rates/${id}`)
  }

  // Step 4: Payment Verification
  async getPaymentProviders(): Promise<PaymentProvider[]> {
    return this.get('/api/v1/payments/providers')
  }

  async verifyPaymentProvider(data: PaymentVerificationData): Promise<{ verified: boolean; message: string; provider: string }> {
    return this.post('/api/v1/payments/verify', data)
  }

  // Integrations: WhatsApp & Meta
  async verifyWhatsAppCredentials(data: WhatsAppVerificationData): Promise<{ verified: boolean; message: string }> {
    return this.post('/api/v1/integrations/whatsapp/verify', data)
  }

  async getWhatsAppStatus(): Promise<{ connected: boolean; phone_number?: string }> {
    return this.get('/api/v1/integrations/whatsapp/status')
  }

  async updateMetaCredentials(data: MetaCredentialsData): Promise<{ ok: boolean }> {
    return this.put('/api/v1/integrations/meta/credentials', data)
  }

  // Onboarding Progress
  async getOnboardingProgress(): Promise<OnboardingProgressData> {
    return this.get('/api/v1/merchants/me/onboarding')
  }

  async updateOnboardingProgress(data: Partial<OnboardingProgressData>): Promise<OnboardingProgressData> {
    return this.put('/api/v1/merchants/me/onboarding', data)
  }
}

// Create a singleton instance
const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
export const onboardingApi = new OnboardingApiClient(baseUrl)