/**
 * Security utilities for credential masking and secure form handling
 * Never expose sensitive credentials in the UI
 */

import { SETTINGS_EVENTS } from '@/constants/settings'

// Re-export for convenience
export { SETTINGS_EVENTS }

/**
 * Mask API keys and credentials for display
 * Never use this for system user tokens (WhatsApp/Meta)
 */
export function maskKey(key: string): string {
  if (!key || key.length < 8) return key

  // Never mask system user tokens at all (WhatsApp/Meta)
  if (key.startsWith('EAA') || key.includes('system_user')) {
    throw new Error('System user tokens should never be displayed')
  }

  const start = key.substring(0, 8)
  const end = key.substring(key.length - 4)
  const middleLength = Math.min(key.length - 12, 20)

  return `${start}${'•'.repeat(middleLength)}${end}`
}

/**
 * Mask account identifiers for display
 */
export function maskIdentifier(identifier: string): string {
  if (!identifier || identifier.length < 8) return identifier

  const start = identifier.substring(0, 4)
  const end = identifier.substring(identifier.length - 4)
  const middleLength = Math.min(identifier.length - 8, 12)

  return `${start}${'•'.repeat(middleLength)}${end}`
}

/**
 * Generate masked display for payment provider keys
 */
export function maskPaymentKey(key: string): string {
  if (!key) return ''

  // Preserve provider prefix for context
  if (key.startsWith('pk_test_') || key.startsWith('pk_live_')) {
    const prefix = key.substring(0, 8)
    const end = key.substring(key.length - 4)
    return `${prefix}${'•'.repeat(12)}${end}`
  }

  if (key.startsWith('sk_test_') || key.startsWith('sk_live_')) {
    const prefix = key.substring(0, 8)
    const end = key.substring(key.length - 4)
    return `${prefix}${'•'.repeat(12)}${end}`
  }

  // Fallback masking for other key formats
  return maskKey(key)
}

/**
 * Validate that no credentials are being logged or exposed
 */
export function sanitizeForLogging(data: Record<string, any>): Record<string, any> {
  const sanitized = { ...data }

  // Remove or mask sensitive fields
  const sensitiveFields = [
    'secret_key',
    'public_key',
    'access_token',
    'system_user_token',
    'password',
    'token',
    'api_key',
  ]

  sensitiveFields.forEach((field) => {
    if (sanitized[field]) {
      sanitized[field] = '[MASKED]'
    }
  })

  return sanitized
}

/**
 * Track settings events with sanitized properties
 */
export function trackSettingsEvent(
  event: string,
  properties: Record<string, any> = {}
) {
  const sanitizedProperties = sanitizeForLogging(properties)

  console.log(`[SETTINGS] ${event}`, sanitizedProperties)

  // Add analytics integration here (e.g., PostHog, Mixpanel)
  // analytics.track(event, sanitizedProperties)
}

/**
 * Validate credential format without exposing the actual value
 */
export function validateCredentialFormat(
  key: string,
  provider: 'paystack' | 'korapay',
  keyType: 'public' | 'secret'
): { valid: boolean; reason?: string } {
  if (!key || key.length < 10) {
    return { valid: false, reason: 'Key too short' }
  }

  // Basic format validation without exposing the key
  if (provider === 'paystack') {
    const expectedPrefix = keyType === 'public' ? 'pk_' : 'sk_'
    if (!key.startsWith(expectedPrefix)) {
      return {
        valid: false,
        reason: `Expected ${keyType} key to start with ${expectedPrefix}`
      }
    }
  }

  // Additional validation can be added here
  return { valid: true }
}

/**
 * Generate a secure identifier for UI display
 * Used for connection status without exposing credentials
 */
export function generateSecureDisplayId(
  provider: string,
  environment: string,
  lastFourChars?: string
): string {
  const timestamp = Date.now().toString().slice(-4)
  const base = `${provider}_${environment}_${timestamp}`

  if (lastFourChars) {
    return `${base}_${lastFourChars}`
  }

  return base
}

/**
 * Check if a string contains potential credentials
 * Used for validation before logging or displaying
 */
export function containsCredentials(text: string): boolean {
  const credentialPatterns = [
    /pk_[a-z]+_[a-zA-Z0-9]+/i,    // Paystack public keys
    /sk_[a-z]+_[a-zA-Z0-9]+/i,    // Paystack secret keys
    /EAA[a-zA-Z0-9]+/,             // Meta access tokens
    /[a-zA-Z0-9]{32,}/,            // Generic long tokens
  ]

  return credentialPatterns.some(pattern => pattern.test(text))
}

/**
 * Clean sensitive data from error messages
 */
export function sanitizeErrorMessage(error: any): string {
  let message = typeof error === 'string' ? error : error?.message || 'Unknown error'

  // Remove any potential credentials from error messages
  if (containsCredentials(message)) {
    return 'An error occurred with your credentials. Please verify they are correct.'
  }

  return message
}