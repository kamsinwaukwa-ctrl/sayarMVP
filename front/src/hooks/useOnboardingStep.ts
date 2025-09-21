/**
 * Hook for managing individual step state and validation
 */

import { useState, useCallback } from 'react'
import { useOnboarding } from './useOnboarding'
import { trackOnboardingEvent } from '../lib/onboarding'
import { ONBOARDING_EVENTS } from '../constants/onboarding'
import type { OnboardingStep } from '../types/onboarding'

interface UseOnboardingStepOptions {
  stepNumber: OnboardingStep
  requiredFields?: string[]
}

export function useOnboardingStep({ stepNumber, requiredFields = [] }: UseOnboardingStepOptions) {
  const { currentStep, completedSteps, completeStep, goToStep, canNavigateToStep } = useOnboarding()
  const [isValidated, setIsValidated] = useState(false)
  const [validationErrors, setValidationErrors] = useState<Record<string, string>>({})

  const isCurrentStep = currentStep === stepNumber
  const isCompleted = completedSteps.includes(stepNumber)
  const canProceed = isValidated && Object.keys(validationErrors).length === 0

  const validateStep = useCallback((data: any) => {
    const errors: Record<string, string> = {}

    // Check required fields
    requiredFields.forEach(field => {
      if (!data[field] || (typeof data[field] === 'string' && data[field].trim() === '')) {
        errors[field] = `${field} is required`
      }
    })

    setValidationErrors(errors)
    const isValid = Object.keys(errors).length === 0
    setIsValidated(isValid)

    if (!isValid) {
      trackOnboardingEvent(ONBOARDING_EVENTS.STEP_FAILED, {
        step: stepNumber,
        error: 'Validation failed'
      })
    }

    return isValid
  }, [stepNumber, requiredFields])

  const handleNext = useCallback(() => {
    if (canProceed) {
      completeStep(stepNumber)

      if (stepNumber < 4) {
        goToStep((stepNumber + 1) as OnboardingStep)
      }
    }
  }, [canProceed, completeStep, stepNumber, goToStep])

  const handleBack = useCallback(() => {
    if (stepNumber > 1) {
      goToStep((stepNumber - 1) as OnboardingStep)
    }
  }, [stepNumber, goToStep])

  const markAsCompleted = useCallback(() => {
    completeStep(stepNumber)
  }, [completeStep, stepNumber])

  return {
    isCurrentStep,
    isCompleted,
    canProceed,
    isValidated,
    validationErrors,
    validateStep,
    handleNext,
    handleBack,
    markAsCompleted,
    canNavigateToStep
  }
}