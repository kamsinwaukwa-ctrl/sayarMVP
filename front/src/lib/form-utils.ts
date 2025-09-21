import { z } from 'zod'

/**
 * Form integration utilities for react-hook-form + zod
 * Provides common validation schemas and form helpers
 */

// Form error types
export interface FormError {
  message: string
}

export interface FormErrors {
  [key: string]: FormError | FormErrors | undefined
}

export interface ValidationError {
  message: string
  path?: string[]
}

export interface ApiError {
  message: string
  code?: string
  details?: Record<string, unknown>
}

// Common field validation patterns
export const emailSchema = z
  .string()
  .min(1, 'Email is required')
  .email('Enter a valid email address')

export const passwordSchema = z
  .string()
  .min(8, 'Password must be at least 8 characters')
  .regex(/[A-Z]/, 'Password must contain an uppercase letter')
  .regex(/[a-z]/, 'Password must contain a lowercase letter')
  .regex(/\d/, 'Password must contain a number')

export const phoneE164Schema = z
  .string()
  .regex(/^\+[1-9]\d{1,14}$/, 'Enter a valid international phone number (e.g., +1234567890)')
  .optional()

export const requiredStringSchema = (fieldName: string) =>
  z.string().min(1, `${fieldName} is required`)

export const optionalStringSchema = z.string().optional()

export const positiveNumberSchema = (fieldName: string) =>
  z.number().positive(`${fieldName} must be positive`)

export const nonNegativeNumberSchema = (fieldName: string) =>
  z.number().min(0, `${fieldName} cannot be negative`)

// Commerce-specific validation schemas
export const productSchema = z.object({
  name: requiredStringSchema('Product name').max(100, 'Name too long'),
  description: z.string().max(1000, 'Description too long').optional(),
  sku: requiredStringSchema('SKU').max(50, 'SKU too long'),
  price: positiveNumberSchema('Price'),
  category: requiredStringSchema('Category'),
  active: z.boolean().default(true),
  trackInventory: z.boolean().default(false),
  stockQuantity: z.number().int().min(0).optional(),
})

export const businessSchema = z.object({
  name: requiredStringSchema('Business name').max(100, 'Name too long'),
  description: z.string().max(500, 'Description too long').optional(),
  whatsappPhoneE164: phoneE164Schema,
  website: z.string().url('Enter a valid website URL').optional().or(z.literal('')),
  address: z.string().max(200, 'Address too long').optional(),
})

export const userProfileSchema = z.object({
  name: requiredStringSchema('Name').max(50, 'Name too long'),
  email: emailSchema,
  role: z.enum(['admin', 'staff']).default('staff'),
})

// Form field utilities
export const getFieldError = (errors: FormErrors, fieldName: string): FormError | undefined => {
  const error = fieldName.split('.').reduce((obj: FormErrors | FormError | undefined, key: string) => {
    if (obj && typeof obj === 'object' && key in obj) {
      const value = (obj as FormErrors)[key]
      return value
    }
    return undefined
  }, errors)
  
  if (error && 'message' in error) {
    return error as FormError
  }
  return undefined
}

export const formatFormError = (error: string | ValidationError | ApiError | Error): string => {
  if (typeof error === 'string') return error
  if ('message' in error) return error.message
  return 'An error occurred'
}

// Common form default values
export const defaultProductValues = {
  name: '',
  description: '',
  sku: '',
  price: 0,
  category: '',
  active: true,
  trackInventory: false,
  stockQuantity: 0,
}

export const defaultBusinessValues = {
  name: '',
  description: '',
  whatsappPhoneE164: '',
  website: '',
  address: '',
}

export const defaultUserValues = {
  name: '',
  email: '',
  role: 'staff' as const,
}