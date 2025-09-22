/**
 * Onboarding API client - thin wrapper over stateless HTTP client
 * Replaces the inheritance-based OnboardingApiClient to eliminate token drift
 */

import { http } from "@/lib/http";
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
  MetaCatalogOnlyData,
  MetaCredentialsResponse,
  MetaIntegrationStatusResponse,
  MetaSyncDetails,
  MetaSyncTriggerResponse,
  OnboardingProgressData
} from "@/types/onboarding";

export const onboardingApi = {
  // Step 1: Brand Basics
  updateMerchantProfile: (data: BrandBasicsFormData): Promise<Merchant> =>
    http.patch("/api/v1/merchants/me", data),

  uploadMerchantLogo: (file: File): Promise<{ logo_url: string }> => {
    const formData = new FormData();
    formData.append("file", file);
    return http.post("/api/v1/merchants/me/logo", formData);
  },

  // Step 2: Products
  getProducts: (): Promise<Product[]> =>
    http.get("/api/v1/products"),

  createProduct: (data: CreateProductRequest): Promise<Product> =>
    http.post("/api/v1/products", data),

  updateProduct: (id: string, data: Partial<CreateProductRequest>): Promise<Product> =>
    http.put(`/api/v1/products/${id}`, data),

  deleteProduct: (id: string): Promise<{ ok: boolean }> =>
    http.del(`/api/v1/products/${id}`),

  uploadProductImage: (productId: string, file: File): Promise<{ image_url: string }> => {
    const formData = new FormData();
    formData.append("file", file);
    return http.post(`/api/v1/products/${productId}/image`, formData);
  },

  getProductMetaSyncStatus: async (productId: string): Promise<MetaSyncDetails> => {
    const response = await http.get<MetaSyncDetails>(`/api/v1/products/${productId}/meta-sync`);
    return response;
  },

  reSyncProduct: (productId: string): Promise<MetaSyncTriggerResponse> =>
    http.post(`/api/v1/products/${productId}/meta-sync`),

  // Step 3: Delivery Rates
  getDeliveryRates: (): Promise<DeliveryRate[]> =>
    http.get("/api/v1/delivery-rates"),

  createDeliveryRate: (data: CreateDeliveryRateRequest): Promise<DeliveryRate> =>
    http.post("/api/v1/delivery-rates", data),

  updateDeliveryRate: (id: string, data: Partial<CreateDeliveryRateRequest>): Promise<DeliveryRate> =>
    http.put(`/api/v1/delivery-rates/${id}`, data),

  deleteDeliveryRate: (id: string): Promise<{ ok: boolean }> =>
    http.del(`/api/v1/delivery-rates/${id}`),

  // Step 4: Payment Verification
  getPaymentProviders: (): Promise<PaymentProvider[]> =>
    http.get("/api/v1/payments/providers"),

  verifyPaymentProvider: (data: PaymentVerificationData): Promise<{ verified: boolean; message: string; provider: string }> =>
    http.post("/api/v1/payments/verify", data),

  // Integrations: WhatsApp & Meta
  verifyWhatsAppCredentials: (data: WhatsAppVerificationData): Promise<{ verified: boolean; message: string }> =>
    http.post("/api/v1/integrations/whatsapp/verify", data),

  getWhatsAppStatus: (): Promise<{ connected: boolean; phone_number?: string }> =>
    http.get("/api/v1/integrations/whatsapp/status"),

  updateMetaCredentials: (data: MetaCredentialsData): Promise<MetaCredentialsResponse> =>
    http.put("/api/v1/integrations/meta/credentials", data),

  updateMetaCatalogId: (data: MetaCatalogOnlyData): Promise<MetaCredentialsResponse> =>
    http.patch("/api/v1/integrations/meta/catalog", data),

  getMetaIntegrationStatus: (): Promise<MetaIntegrationStatusResponse> =>
    http.get("/api/v1/integrations/meta/status"),

  // Onboarding Progress
  getOnboardingProgress: (): Promise<OnboardingProgressData> =>
    http.get("/api/v1/merchants/me/onboarding"),

  updateOnboardingProgress: (data: Partial<OnboardingProgressData>): Promise<OnboardingProgressData> =>
    http.put("/api/v1/merchants/me/onboarding", data),
};