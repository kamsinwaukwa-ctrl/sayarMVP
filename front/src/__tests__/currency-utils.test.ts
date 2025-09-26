/**
 * Currency Utilities Tests
 * Tests precision-first currency conversion functions
 */

import { describe, it, expect } from 'vitest'
import { nairaToKobo, koboToNairaDisplay, koboToNairaNumber } from '@/lib/format'

describe('Currency Utilities', () => {
  describe('nairaToKobo', () => {
    it('should convert integer naira to kobo', () => {
      expect(nairaToKobo('90')).toBe(9000)
      expect(nairaToKobo('1')).toBe(100)
      expect(nairaToKobo('1000')).toBe(100000)
    })

    it('should convert decimal naira to kobo', () => {
      expect(nairaToKobo('90.50')).toBe(9050)
      expect(nairaToKobo('1.99')).toBe(199)
      expect(nairaToKobo('1500.25')).toBe(150025)
    })

    it('should handle string inputs with trailing zeros', () => {
      expect(nairaToKobo('90.00')).toBe(9000)
      expect(nairaToKobo('90.10')).toBe(9010)
      expect(nairaToKobo('90.5')).toBe(9050)
    })

    it('should handle numeric inputs', () => {
      expect(nairaToKobo(90)).toBe(9000)
      expect(nairaToKobo(90.5)).toBe(9050)
      expect(nairaToKobo(1500.25)).toBe(150025)
    })

    it('should handle zero', () => {
      expect(nairaToKobo('0')).toBe(0)
      expect(nairaToKobo('0.00')).toBe(0)
      expect(nairaToKobo(0)).toBe(0)
    })

    it('should strip commas from input', () => {
      expect(nairaToKobo('1,500.50')).toBe(150050)
      expect(nairaToKobo('10,000')).toBe(1000000)
    })

    it('should throw error for invalid input', () => {
      expect(() => nairaToKobo('abc')).toThrow('Enter a valid amount (max 2 decimals)')
      expect(() => nairaToKobo('90.123')).toThrow('Enter a valid amount (max 2 decimals)')
      expect(() => nairaToKobo('90.')).toThrow('Enter a valid amount (max 2 decimals)')
      expect(() => nairaToKobo('.50')).toThrow('Enter a valid amount (max 2 decimals)')
      expect(() => nairaToKobo('-50')).toThrow('Enter a valid amount (max 2 decimals)')
      expect(() => nairaToKobo('')).toThrow('Enter a valid amount (max 2 decimals)')
    })

    it('should throw error for amounts that are too large', () => {
      const veryLarge = '999999999999999'
      expect(() => nairaToKobo(veryLarge)).toThrow('Amount too large')
    })

    it('should handle edge case decimal inputs', () => {
      expect(nairaToKobo('0.1')).toBe(10)
      expect(nairaToKobo('0.01')).toBe(1)
      expect(nairaToKobo('999.99')).toBe(99999)
    })
  })

  describe('koboToNairaDisplay', () => {
    it('should format kobo to currency display', () => {
      expect(koboToNairaDisplay(9000)).toBe('₦90.00')
      expect(koboToNairaDisplay(9050)).toBe('₦90.50')
      expect(koboToNairaDisplay(150025)).toBe('₦1,500.25')
    })

    it('should handle zero', () => {
      expect(koboToNairaDisplay(0)).toBe('₦0.00')
    })

    it('should handle large amounts with proper formatting', () => {
      expect(koboToNairaDisplay(100000000)).toBe('₦1,000,000.00')
      expect(koboToNairaDisplay(123456789)).toBe('₦1,234,567.89')
    })

    it('should handle null and undefined', () => {
      expect(koboToNairaDisplay(null)).toBe('')
      expect(koboToNairaDisplay(undefined)).toBe('')
    })

    it('should maintain exactly 2 decimal places', () => {
      expect(koboToNairaDisplay(100)).toBe('₦1.00')
      expect(koboToNairaDisplay(101)).toBe('₦1.01')
      expect(koboToNairaDisplay(999)).toBe('₦9.99')
    })
  })

  describe('koboToNairaNumber', () => {
    it('should convert kobo to plain naira number', () => {
      expect(koboToNairaNumber(9000)).toBe(90)
      expect(koboToNairaNumber(9050)).toBe(90.5)
      expect(koboToNairaNumber(150025)).toBe(1500.25)
    })

    it('should handle zero', () => {
      expect(koboToNairaNumber(0)).toBe(0)
    })

    it('should handle null and undefined', () => {
      expect(koboToNairaNumber(null)).toBe(0)
      expect(koboToNairaNumber(undefined)).toBe(0)
    })

    it('should handle decimal precision correctly', () => {
      expect(koboToNairaNumber(1)).toBe(0.01)
      expect(koboToNairaNumber(99)).toBe(0.99)
      expect(koboToNairaNumber(100)).toBe(1)
    })
  })

  describe('Round-trip conversion', () => {
    it('should maintain precision in round-trip conversions', () => {
      const testCases = ['90', '90.50', '1500.25', '0.01', '999.99']

      testCases.forEach(original => {
        const kobo = nairaToKobo(original)
        const backToNaira = koboToNairaNumber(kobo)
        expect(backToNaira).toBe(parseFloat(original))
      })
    })

    it('should preserve exact amounts through display conversion', () => {
      const koboAmount = 9050 // ₦90.50
      const displayString = koboToNairaDisplay(koboAmount)
      expect(displayString).toBe('₦90.50')

      // Extract numeric part and convert back
      const numericPart = displayString.replace(/[₦,]/g, '')
      const backToKobo = nairaToKobo(numericPart)
      expect(backToKobo).toBe(koboAmount)
    })
  })

  describe('Edge cases from user requirements', () => {
    it('should handle the specific problem case: user enters 9000 expecting ₦90', () => {
      // The problem: user enters "9000" but means ₦90, not ₦9000
      // Our solution: input field accepts "90" and converts to 9000 kobo
      expect(nairaToKobo('90')).toBe(9000)
      expect(koboToNairaDisplay(9000)).toBe('₦90.00')
    })

    it('should prevent floating-point precision issues', () => {
      // These are exact conversions that avoid float math
      expect(nairaToKobo('1500.99')).toBe(150099)
      expect(nairaToKobo('0.99')).toBe(99)
      expect(nairaToKobo('999999.99')).toBe(99999999)
    })

    it('should handle typical delivery rate scenarios', () => {
      // Common delivery rates in Lagos
      expect(nairaToKobo('1500')).toBe(150000) // Lagos Mainland
      expect(nairaToKobo('2000')).toBe(200000) // Lagos Island
      expect(nairaToKobo('2500.50')).toBe(250050) // Surulere with 50 kobo
    })

    it('should handle typical product price scenarios', () => {
      // Common product prices
      expect(nairaToKobo('15000')).toBe(1500000) // ₦15,000 product
      expect(nairaToKobo('25000.99')).toBe(2500099) // ₦25,000.99 product
      expect(nairaToKobo('500')).toBe(50000) // ₦500 product
    })
  })
})