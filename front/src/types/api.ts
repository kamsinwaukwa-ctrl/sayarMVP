// API Types for Sayar Frontend
// Generated from OpenAPI contracts

export interface ApiResponse<T = any> {
  ok: boolean;
  id?: string;
  data?: T;
  message?: string;
  timestamp: string;
}

export interface ApiErrorDetails {
  field?: string;
  reason: string;
  value?: unknown;
  service?: string;
  retry_after?: number;
  request_id?: string;
}

export interface ApiError {
  code: string;
  message: string;
  details?: ApiErrorDetails;
  trace_id?: string;
}

export type Envelope<T> = ApiResponse<T> | { ok: false; error: ApiError; timestamp: string };

// Auth Types
export interface AuthRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  name: string;
  email: string;
  password: string;
  business_name: string;
  whatsapp_phone_e164?: string; // Optional WhatsApp phone
}

export interface AuthResponse {
  token: string;
  user: {
    id: string;
    email: string;
    name: string;
    role: 'admin' | 'staff'; // Updated to match backend enum
    merchant_id: string;
  };
}

export interface RegisterResponse {
  token: string;
  user: {
    id: string;
    email: string;
    name: string;
    role: 'admin' | 'staff';
    merchant_id: string;
  };
  merchant: {
    id: string;
    name: string;
    whatsapp_phone_e164?: string; // Optional WhatsApp phone
  };
}

// Merchant Types
import type { MerchantSummary, CreateMerchantRequest } from './merchant'

export type { CreateMerchantRequest }
export type MerchantResponse = MerchantSummary

// Product Types
export interface CreateProductRequest {
  title: string;
  description?: string;
  price_kobo: number;
  stock: number;
  sku: string;
  category_path?: string;
  tags?: string[];
}

export interface ProductResponse {
  id: string;
  merchant_id: string;
  title: string;
  description?: string;
  price_kobo: number;
  stock: number;
  reserved_qty: number;
  available_qty: number;
  image_url?: string;
  sku: string;
  status: 'active' | 'inactive';
  retailer_id: string;
  category_path?: string;
  tags: string[];
  created_at: string;
  updated_at: string;
}

// Delivery Rate Types
export interface CreateDeliveryRateRequest {
  name: string;
  areas_text: string;
  price_kobo: number;
  description?: string;
}

export interface DeliveryRateResponse {
  id: string;
  merchant_id: string;
  name: string;
  areas_text: string;
  price_kobo: number;
  description?: string;
  active: boolean;
  created_at: string;
  updated_at: string;
}

// Discount Types
export interface ValidateDiscountRequest {
  code: string;
  subtotal_kobo: number;
  customer_id?: string;
}

export interface DiscountValidationResponse {
  valid: boolean;
  discount_kobo?: number;
  reason?: string;
}

// Pagination Types
export interface PaginationParams {
  page?: number;
  page_size?: number;
  sort?: string;
}

export interface PaginatedResponse<T> {
  ok: boolean;
  data: T[];
  pagination: {
    page: number;
    page_size: number;
    total_items: number;
    total_pages: number;
    has_next: boolean;
    has_prev: boolean;
  };
  timestamp: string;
}

// Error Codes
export type ErrorCode =
  | 'VALIDATION_ERROR'
  | 'AUTHENTICATION_ERROR'
  | 'AUTHORIZATION_ERROR'
  | 'NOT_FOUND'
  | 'CONFLICT'
  | 'RATE_LIMITED'
  | 'EXTERNAL_SERVICE_ERROR'
  | 'WHATSAPP_ERROR'
  | 'PAYSTACK_ERROR'
  | 'KORAPAY_ERROR'
  | 'INTERNAL_ERROR'
  | 'DATABASE_ERROR'
  | 'SERVICE_UNAVAILABLE';

// HTTP Status Codes
export const HTTP_STATUS = {
  OK: 200,
  CREATED: 201,
  BAD_REQUEST: 400,
  UNAUTHORIZED: 401,
  FORBIDDEN: 403,
  NOT_FOUND: 404,
  CONFLICT: 409,
  TOO_MANY_REQUESTS: 429,
  INTERNAL_SERVER_ERROR: 500,
  BAD_GATEWAY: 502,
  SERVICE_UNAVAILABLE: 503,
  GATEWAY_TIMEOUT: 504,
} as const;