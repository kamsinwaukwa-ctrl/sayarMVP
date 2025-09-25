/**
 * Payment Provider API client
 * Handles payment provider verification and configuration
 */

import { http } from "@/lib/http";

export interface PaymentEnvironment {
  TEST: 'test';
  LIVE: 'live';
}

export interface PaymentProviderType {
  PAYSTACK: 'paystack';
  KORAPAY: 'korapay';
}

export interface PaystackCredentialsRequest {
  secret_key: string;
  public_key?: string;
  environment: 'test' | 'live';
}

export interface KorapayCredentialsRequest {
  public_key: string;
  secret_key: string;
  webhook_secret?: string;
  environment: 'test' | 'live';
}

export interface VerificationResult {
  success: boolean;
  provider_type: 'paystack' | 'korapay';
  environment: 'test' | 'live';
  verification_status: 'pending' | 'verifying' | 'verified' | 'failed';
  error_message?: string;
  verified_at?: string;
  config_id?: string;
}

export interface PaymentProviderConfig {
  id: string;
  provider_type: 'paystack' | 'korapay';
  environment: 'test' | 'live';
  verification_status: 'pending' | 'verifying' | 'verified' | 'failed';
  last_verified_at?: string;
  verification_error?: string;
  active: boolean;
  created_at: string;
  updated_at: string;
}

export interface PaymentProviderListResponse {
  providers: PaymentProviderConfig[];
  total_count: number;
}

export const paymentsApi = {
  // Verify Paystack credentials
  verifyPaystackCredentials: (data: PaystackCredentialsRequest): Promise<VerificationResult> =>
    http.post("/api/v1/payments/verify/paystack", data),

  // Verify Korapay credentials
  verifyKorapayCredentials: (data: KorapayCredentialsRequest): Promise<VerificationResult> =>
    http.post("/api/v1/payments/verify/korapay", data),

  // List payment provider configurations
  listPaymentProviders: (): Promise<PaymentProviderListResponse> =>
    http.get("/api/v1/payments/providers"),

  // Delete payment provider configuration
  deletePaymentProvider: (provider_type: 'paystack' | 'korapay', environment: 'test' | 'live'): Promise<{ deleted: boolean }> =>
    http.del(`/api/v1/payments/providers/${provider_type}?environment=${environment}`),
};