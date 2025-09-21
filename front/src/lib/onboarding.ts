/**
 * Onboarding utility functions
 */

import React from 'react'
import { STORAGE_KEYS, ONBOARDING_EVENTS } from '@/constants/onboarding'
import type { OnboardingStep } from '@/types/onboarding'

// Event tracking utility
export function trackOnboardingEvent(
  event: string,
  properties: { step?: number; provider?: string; error?: string }
) {
  console.log(`[ONBOARDING] ${event}`, properties)
  // TODO: Integration with analytics service (PostHog, Mixpanel, etc.)
}

// Step navigation utilities
export function canNavigateToStep(
  targetStep: OnboardingStep,
  currentStep: OnboardingStep,
  completedSteps: OnboardingStep[]
): boolean {
  // Always allow backward navigation to completed steps
  if (targetStep <= currentStep && completedSteps.includes(targetStep)) {
    return true
  }

  // Allow forward navigation only to next incomplete step
  const maxCompletedStep = Math.max(0, ...completedSteps)
  if (targetStep === maxCompletedStep + 1 && targetStep <= 5) {
    return true
  }

  return false
}

// LocalStorage helpers
export function saveOnboardingProgress(step: OnboardingStep, completedSteps: OnboardingStep[]) {
  try {
    localStorage.setItem(STORAGE_KEYS.ONBOARDING_PROGRESS, step.toString())
    localStorage.setItem(STORAGE_KEYS.ONBOARDING_DRAFT, JSON.stringify(completedSteps))
  } catch (error) {
    console.warn('Failed to save onboarding progress:', error)
  }
}

export function getOnboardingProgress(): { currentStep: OnboardingStep; completedSteps: OnboardingStep[] } {
  try {
    const currentStep = parseInt(
      localStorage.getItem(STORAGE_KEYS.ONBOARDING_PROGRESS) || '1'
    ) as OnboardingStep
    const completedSteps = JSON.parse(
      localStorage.getItem(STORAGE_KEYS.ONBOARDING_DRAFT) || '[]'
    )
    return { currentStep, completedSteps }
  } catch (error) {
    console.warn('Failed to get onboarding progress:', error)
    return { currentStep: 1, completedSteps: [] }
  }
}

export function clearOnboardingProgress() {
  try {
    localStorage.removeItem(STORAGE_KEYS.ONBOARDING_PROGRESS)
    localStorage.removeItem(STORAGE_KEYS.ONBOARDING_DRAFT)
    localStorage.removeItem(STORAGE_KEYS.ONBOARDING_FORM_DATA)
  } catch (error) {
    console.warn('Failed to clear onboarding progress:', error)
  }
}

export function isOnboardingCompleted(): boolean {
  try {
    const { completedSteps } = getOnboardingProgress()
    // Onboarding is completed when all 5 steps are completed
    return completedSteps.length === 5
  } catch (error) {
    console.warn('Failed to check onboarding completion:', error)
    return false
  }
}

// Auto-save helpers
export function saveFormData(stepId: OnboardingStep, data: Record<string, unknown>) {
  try {
    const existingData = JSON.parse(
      localStorage.getItem(STORAGE_KEYS.ONBOARDING_FORM_DATA) || '{}'
    )
    existingData[stepId] = data
    localStorage.setItem(STORAGE_KEYS.ONBOARDING_FORM_DATA, JSON.stringify(existingData))

    trackOnboardingEvent(ONBOARDING_EVENTS.FORM_AUTO_SAVED, { step: stepId })
  } catch (error) {
    console.warn('Failed to save form data:', error)
  }
}

export function getFormData(stepId: OnboardingStep): Record<string, unknown> {
  try {
    const data = JSON.parse(
      localStorage.getItem(STORAGE_KEYS.ONBOARDING_FORM_DATA) || '{}'
    )
    return data[stepId] || {}
  } catch (error) {
    console.warn('Failed to get form data:', error)
    return {}
  }
}

// Formatting utilities
export function formatNaira(kobo: number): string {
  const naira = kobo / 100
  return new Intl.NumberFormat('en-NG', {
    style: 'currency',
    currency: 'NGN'
  }).format(naira)
}

export function formatDate(isoString: string): string {
  return new Intl.DateTimeFormat('en-NG', {
    dateStyle: 'medium',
    timeStyle: 'short'
  }).format(new Date(isoString))
}

// Validation helpers
export function validateImageFile(file: File): { valid: boolean; error?: string } {
  const maxSize = 5 * 1024 * 1024 // 5MB
  const supportedTypes = ['image/png', 'image/jpeg', 'image/jpg', 'image/webp']

  if (file.size > maxSize) {
    return { valid: false, error: 'File size must be less than 5MB' }
  }

  if (!supportedTypes.includes(file.type)) {
    return { valid: false, error: 'Only PNG, JPG, and WebP images are supported' }
  }

  return { valid: true }
}

// Performance monitoring
export function withPerformanceTracking<P extends Record<string, any>>(
  Component: React.ComponentType<P>,
  componentName: string
) {
  const WrappedComponent = React.memo((props: P) => {
    const startTime = performance.now()

    React.useEffect(() => {
      const endTime = performance.now()
      const renderTime = endTime - startTime

      if (renderTime > 100) { // Log slow renders
        console.warn(`[PERFORMANCE] ${componentName} render took ${renderTime.toFixed(2)}ms`)
      }
    })

    return React.createElement(Component, props)
  })

  WrappedComponent.displayName = `withPerformanceTracking(${componentName})`
  return WrappedComponent as unknown as React.ComponentType<P>
}