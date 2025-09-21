/**
 * SINGLE SOURCE OF TRUTH for Merchant types
 * Do not redefine Merchant interface elsewhere - import from here
 */

export interface Merchant {
  id: string
  name: string
  slug: string
  whatsapp_phone_e164?: string
  logo_url?: string
  description?: string
  currency: string
  waba_id?: string
  phone_number_id?: string
  meta_app_id?: string
  provider_default?: 'paystack' | 'korapay'
  payments_verified_at?: string
  created_at: string
  updated_at: string
}

// Narrow API shapes extend/pick from the base
export type MerchantSummary = Pick<
  Merchant,
  'id' | 'name' | 'slug' | 'whatsapp_phone_e164' | 'currency' | 'created_at' | 'updated_at'
>

export type CreateMerchantRequest = Pick<Merchant, 'name' | 'whatsapp_phone_e164'>

// API mapper to handle backend field name differences
export const toMerchant = (r: any): Merchant => ({
  id: r.id,
  name: r.name ?? r.business_name, // tolerate legacy business_name
  slug: r.slug ?? '',
  whatsapp_phone_e164: r.whatsapp_phone_e164,
  logo_url: r.logo_url,
  description: r.description,
  currency: r.currency,
  waba_id: r.waba_id,
  phone_number_id: r.phone_number_id,
  meta_app_id: r.meta_app_id,
  provider_default: r.provider_default,
  payments_verified_at: r.payments_verified_at,
  created_at: r.created_at,
  updated_at: r.updated_at,
})