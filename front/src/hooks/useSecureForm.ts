/**
 * Secure form handling hooks for credential management
 * Ensures forms never pre-populate with existing credentials
 */

import { useState, useCallback, useRef, useEffect } from 'react'
import { useForm, FieldValues, UseFormHandleSubmit, UseFormGetValues, UseFormReset, UseFormSetValue, UseFormWatch, FormState, Control, UseFormGetFieldState, UseFormSetError, UseFormClearErrors, UseFormTrigger, UseFormUnregister, UseFormRegister, UseFormResetField, UseFormSetFocus, UseFormSubscribe } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { trackSettingsEvent, SETTINGS_EVENTS } from '@/lib/security'
import { useAuth } from '@/hooks/useAuth'

/**
 * Explicitly typed form interface for security
 */
interface SecureFormReturn<TFormData extends FieldValues> {
  handleSubmit: UseFormHandleSubmit<TFormData, TFormData>
  getValues: UseFormGetValues<TFormData>
  reset: UseFormReset<TFormData>
  setValue: UseFormSetValue<TFormData>
  watch: UseFormWatch<TFormData>
  formState: FormState<TFormData>
  control: Control<TFormData>
  getFieldState: UseFormGetFieldState<TFormData>
  setError: UseFormSetError<TFormData>
  clearErrors: UseFormClearErrors<TFormData>
  trigger: UseFormTrigger<TFormData>
  unregister: UseFormUnregister<TFormData>
  register: UseFormRegister<TFormData>
  resetField: UseFormResetField<TFormData>
  setFocus: UseFormSetFocus<TFormData>
  subscribe: UseFormSubscribe<TFormData>
}

/**
 * Secure form hook that never pre-populates sensitive fields
 */
export function useSecureForm<T extends FieldValues>(
  schema: z.ZodSchema<T>,
  options: {
    onSuccess?: () => void
    onError?: (error: Error) => void
    provider?: string
  } = {}
): {
  form: SecureFormReturn<T>
  secureSubmit: (
    onSubmit: (data: T) => Promise<void>
  ) => Promise<void>
  clearForm: () => void
} {
  const form = useForm<T>({
    resolver: zodResolver(schema),
    defaultValues: undefined, // Never pre-populate with existing credentials
    mode: 'onChange',
  })

  const clearForm = () => {
    form.reset()
  }

  const secureSubmit = async (
    onSubmit: (data: T) => Promise<void>
  ) => {
    try {
      const data = form.getValues()

      // Track credential update start
      trackSettingsEvent(SETTINGS_EVENTS.CREDENTIAL_UPDATE_STARTED, {
        provider: options.provider,
        hasPublicKey: !!(data as any).publicKey || !!(data as any).public_key,
        hasSecretKey: !!(data as any).secretKey || !!(data as any).secret_key,
      })

      await onSubmit(data)

      // Clear all sensitive form data immediately after success
      clearForm()

      // Track success
      trackSettingsEvent(SETTINGS_EVENTS.CREDENTIAL_UPDATE_SUCCESS, {
        provider: options.provider,
      })

      options.onSuccess?.()
    } catch (error) {
      // Track failure
      trackSettingsEvent(SETTINGS_EVENTS.CREDENTIAL_UPDATE_FAILED, {
        provider: options.provider,
        error: error instanceof Error ? error.message : 'Unknown error',
      })

      options.onError?.(error instanceof Error ? error : new Error('Unknown error'))
      throw error
    }
  }

  return {
    form: {
      handleSubmit: form.handleSubmit,
      getValues: form.getValues,
      reset: form.reset,
      setValue: form.setValue,
      watch: form.watch,
      formState: form.formState,
      control: form.control,
      getFieldState: form.getFieldState,
      setError: form.setError,
      clearErrors: form.clearErrors,
      trigger: form.trigger,
      unregister: form.unregister,
      register: form.register,
      resetField: form.resetField,
      setFocus: form.setFocus,
      subscribe: form.subscribe
    },
    secureSubmit,
    clearForm
  }
}

/**
 * Hook for role-based access control
 */
export function useRole() {
  const { user } = useAuth()
  const role = user?.role || 'staff'

  return {
    role,
    canUpdateCredentials: role === 'admin',
    canManageTeam: role === 'admin',
    canAccessAdvancedSettings: role === 'admin',
    canRotateTokens: role === 'admin',
    canViewLogs: role === 'admin',
  }
}

/**
 * Hook for connection testing
 */
export function useConnectionTest(provider: string) {
  const [isTestingConnection, setIsTestingConnection] = useState(false)

  const testConnection = useCallback(async () => {
    setIsTestingConnection(true)

    try {
      trackSettingsEvent(SETTINGS_EVENTS.CONNECTION_TEST_STARTED, {
        provider,
      })

      // This would call your actual API
      // const result = await api.testConnection(provider)

      // Mock for now
      const result = { success: true, message: 'Connection successful' }

      trackSettingsEvent(
        result.success
          ? SETTINGS_EVENTS.CONNECTION_TEST_SUCCESS
          : SETTINGS_EVENTS.CONNECTION_TEST_FAILED,
        { provider, success: result.success }
      )

      return result
    } finally {
      setIsTestingConnection(false)
    }
  }, [provider])

  return { testConnection, isTestingConnection }
}

/**
 * Hook for performance monitoring of settings operations
 */
export function useSettingsPerformance() {
  const startTime = useRef(performance.now())

  useEffect(() => {
    const loadTime = performance.now() - startTime.current

    if (loadTime > 500) { // Log slow settings loads
      console.warn(`[PERFORMANCE] Settings load took ${loadTime.toFixed(2)}ms`)
    }

    trackSettingsEvent(SETTINGS_EVENTS.SETTINGS_OPENED, {
      loadTime: Math.round(loadTime)
    })
  }, [])
}

