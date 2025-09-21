/**
 * Generated TypeScript models from OpenAPI specification v0.1.1
 * Sayar WhatsApp Commerce Platform API
 */

export interface RegisterRequest {
  name: string;
  email: string;
  password: string;
  business_name: string;
  whatsapp_phone_e164?: string; // Optional WhatsApp phone number
}

export interface AuthRequest {
  email: string;
  password: string;
}

export interface ApiResponse<T = any> {
  ok: boolean;
  id?: string;
  data?: T;
  message?: string;
  timestamp: string;
}

export interface ApiErrorDetails {
  field?: string;
  reason?: string;
  value?: unknown;
  service?: string;
  retry_after?: number;
  request_id?: string;
}

export interface APIError {
  code: string;
  message: string;
  details?: ApiErrorDetails;
  trace_id?: string;
}

export interface ApiErrorResponse {
  ok: false;
  error: APIError;
  timestamp: string;
}

export type ApiEnvelope<T> = ApiResponse<T> | ApiErrorResponse;

// Auth specific responses
export interface UserResponse {
  id: string;
  name: string;
  email: string;
  role: 'admin' | 'staff';
  merchant_id: string;
}

export interface AuthResponse {
  token: string;
  user: UserResponse;
}

export interface MerchantResponse {
  id: string;
  name: string;
  whatsapp_phone_e164?: string;
}

export interface RegisterResponse {
  token: string;
  user: UserResponse;
  merchant: MerchantResponse;
}

// Configuration for API client
export interface ApiClientConfiguration {
  basePath?: string;
  accessToken?: string;
}

// HTTP methods
export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH';

// Request configuration
export interface RequestConfig {
  method: HttpMethod;
  headers?: Record<string, string>;
  body?: any;
}