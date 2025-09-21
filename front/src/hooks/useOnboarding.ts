/**
 * Main onboarding state management hook
 * Handles wizard navigation, step completion, and localStorage persistence
 */

import { useState, useCallback, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  canNavigateToStep,
  saveOnboardingProgress,
  getOnboardingProgress,
  trackOnboardingEvent
} from '@/lib/onboarding'
import { ONBOARDING_EVENTS } from '@/constants/onboarding'
import type { OnboardingStep, OnboardingState } from '@/types/onboarding'

export function useOnboarding(): OnboardingState {
  const navigate = useNavigate()

  // Initialize state from localStorage
  const [currentStep, setCurrentStep] = useState<OnboardingStep>(() => {
    const { currentStep } = getOnboardingProgress()
    return currentStep
  })

  const [completedSteps, setCompletedSteps] = useState<OnboardingStep[]>(() => {
    const { completedSteps } = getOnboardingProgress()
    return completedSteps
  })

  // Track wizard started event on first load
  useEffect(() => {
    if (currentStep === 1 && completedSteps.length === 0) {
      trackOnboardingEvent(ONBOARDING_EVENTS.WIZARD_STARTED, { step: 1 })
    }
  }, [])

  const completeStep = useCallback((step: OnboardingStep) => {
    const updated = [...new Set([...completedSteps, step])].sort() as OnboardingStep[]
    setCompletedSteps(updated)

    // Save to localStorage
    saveOnboardingProgress(currentStep, updated)

    // Track completion event
    trackOnboardingEvent(ONBOARDING_EVENTS.STEP_COMPLETED, { step })

    // Check if all steps are completed
    if (updated.length === 5) {
      trackOnboardingEvent(ONBOARDING_EVENTS.WIZARD_COMPLETED, {})
      navigate('/onboarding/complete')
    }
  }, [completedSteps, currentStep, navigate])

  const goToStep = useCallback((step: OnboardingStep) => {
    if (canNavigateToStep(step, currentStep, completedSteps)) {
      setCurrentStep(step)
      saveOnboardingProgress(step, completedSteps)

      // Navigate to the step route
      if (step <= 5) {
        navigate(`/onboarding/step/${step}`)
      }
    }
  }, [currentStep, completedSteps, navigate])

  const canNavigateToStepCallback = useCallback((step: OnboardingStep): boolean => {
    return canNavigateToStep(step, currentStep, completedSteps)
  }, [currentStep, completedSteps])

  return {
    currentStep,
    completedSteps,
    canNavigateToStep: canNavigateToStepCallback,
    completeStep,
    goToStep
  }
}