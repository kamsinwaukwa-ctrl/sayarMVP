/**
 * Formatting utilities for currency, dates, and other display values
 */

export const formatNaira = (kobo: number): string => {
  const naira = kobo / 100
  return new Intl.NumberFormat('en-NG', {
    style: 'currency',
    currency: 'NGN'
  }).format(naira)
}

export const formatDate = (isoString: string): string => {
  return new Intl.DateTimeFormat('en-NG', {
    dateStyle: 'medium',
    timeStyle: 'short'
  }).format(new Date(isoString))
}

export const formatCurrency = (amount: number, currency: string = 'NGN'): string => {
  return new Intl.NumberFormat('en-NG', {
    style: 'currency',
    currency: currency
  }).format(amount)
}

export const formatNumber = (number: number): string => {
  return new Intl.NumberFormat('en-NG').format(number)
}