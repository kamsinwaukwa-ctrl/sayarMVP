// Database types for Sayar WhatsApp Commerce Platform
import type { Merchant } from './merchant'

export interface User {
  id: string
  email: string
  merchant_id?: string
  role: 'owner' | 'staff'
  created_at: string
  updated_at: string
}

export type { Merchant }

export interface Product {
  id: string
  merchant_id: string
  title: string
  description?: string
  price_kobo: number
  stock: number
  reserved_qty: number
  available_qty: number
  image_url?: string
  sku?: string
  status: 'active' | 'inactive'
  catalog_id?: string
  retailer_id: string
  category_path?: string
  tags?: string[]
  created_at: string
  updated_at: string
}

export interface Customer {
  id: string
  merchant_id: string
  phone_e164: string
  name?: string
  created_at: string
  updated_at: string
}

export interface Order {
  id: string
  merchant_id: string
  customer_id: string
  subtotal_kobo: number
  shipping_kobo: number
  discount_kobo: number
  total_kobo: number
  status: 'pending' | 'paid' | 'failed' | 'cancelled'
  payment_provider?: string
  provider_reference?: string
  order_code: string
  paid_at?: string
  created_at: string
  updated_at: string
}

export interface OrderItem {
  id: string
  order_id: string
  product_id: string
  qty: number
  unit_price_kobo: number
  total_kobo: number
  created_at: string
  updated_at: string
}

export interface DeliveryRate {
  id: string
  merchant_id: string
  name: string
  areas_text: string
  price_kobo: number
  description?: string
  active: boolean
  created_at: string
  updated_at: string
}