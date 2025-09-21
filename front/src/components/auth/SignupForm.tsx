/**
 * Two-Step Signup Form Component for Sayar WhatsApp Commerce Platform
 * Professional multi-step form with progress indication and micro-UX optimizations
 */

import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { yupResolver } from '@hookform/resolvers/yup'
import * as yup from 'yup'
import { Eye, EyeOff } from 'lucide-react'
import { useAuth } from '../../hooks/useAuth'
import { RegisterRequest } from '../../types/api'
import { ApiClientError } from '../../lib/api-client'
import { Button } from '../ui/Button'
import { Input } from '../ui/Input'
import { Label } from '../ui/label'
import { Alert, AlertDescription } from '../ui/Alert'

// Type definitions for each step
interface Step1Data {
  name: string
  email: string
  password: string
  confirmPassword: string
}

interface Step2Data {
  business_name: string
  termsAccepted: boolean
}

interface SignupFormData extends RegisterRequest {
  confirmPassword: string
  termsAccepted: boolean
}

// Step 1 validation schema
const step1Schema = yup.object({
  name: yup
    .string()
    .min(2, 'Name must be at least 2 characters')
    .max(50, 'Name must be less than 50 characters')
    .required('Full name is required'),
  email: yup
    .string()
    .email('Please enter a valid email address')
    .required('Email is required'),
  password: yup
    .string()
    .min(8, 'Password must be at least 8 characters')
    .matches(
      /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/,
      'Password must contain at least one uppercase letter, one lowercase letter, and one number'
    )
    .required('Password is required'),
  confirmPassword: yup
    .string()
    .oneOf([yup.ref('password')], 'Passwords must match')
    .required('Please confirm your password'),
}) as yup.ObjectSchema<Step1Data>

// Step 2 validation schema
const step2Schema = yup.object({
  business_name: yup
    .string()
    .min(2, 'Business name must be at least 2 characters')
    .max(100, 'Business name must be less than 100 characters')
    .required('Business name is required'),
  termsAccepted: yup
    .boolean()
    .oneOf([true], 'You must accept the terms and conditions')
    .required('You must accept the terms and conditions'),
}) as yup.ObjectSchema<Step2Data>

interface SignupFormProps {
  onError?: (error: string) => void
}

const SignupForm: React.FC<SignupFormProps> = ({ onError }) => {
  const { register: registerUser, loading, error, clearError } = useAuth()
  const navigate = useNavigate()
  const [currentStep, setCurrentStep] = useState(1)
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)
  const [formData, setFormData] = useState<Partial<SignupFormData>>({})

  // Create separate form instances for each step
  const step1Form = useForm<Step1Data>({
    resolver: yupResolver(step1Schema),
    mode: 'onBlur',
    defaultValues: {
      name: formData.name || '',
      email: formData.email || '',
      password: formData.password || '',
      confirmPassword: formData.confirmPassword || '',
    },
  })

  const step2Form = useForm<Step2Data>({
    resolver: yupResolver(step2Schema),
    mode: 'onBlur',
    defaultValues: {
      business_name: formData.business_name || '',
      termsAccepted: formData.termsAccepted || false,
    },
  })

  // Use the appropriate form based on current step
  const password = step1Form.watch('password', '')
  const termsAccepted = step2Form.watch('termsAccepted', false)

  // Password strength calculation
  const getPasswordStrength = (password: string) => {
    let strength = 0
    if (password.length >= 8) strength++
    if (/[a-z]/.test(password)) strength++
    if (/[A-Z]/.test(password)) strength++
    if (/\d/.test(password)) strength++
    if (/[^A-Za-z0-9]/.test(password)) strength++
    return strength
  }

  const passwordStrength = getPasswordStrength(password)
  const strengthColors = ['bg-red-500', 'bg-orange-500', 'bg-yellow-500', 'bg-blue-500', 'bg-green-500']
  const strengthLabels = ['Very Weak', 'Weak', 'Fair', 'Good', 'Strong']

  const onSubmit = async (data: SignupFormData) => {
    clearError()

    try {
      const { confirmPassword: _confirmPassword, termsAccepted: _termsAccepted, ...registerData } = data
      await registerUser(registerData)
      step1Form.reset()
      step2Form.reset()

      // Navigate directly to onboarding (no logout, keep session)
      navigate('/onboarding/step/1', { replace: true })
    } catch (error) {
      let errorMessage = 'Registration failed'

      if (error instanceof Error) {
        if (error instanceof ApiClientError && error.status === 409) {
          errorMessage = 'A user with this email already exists'
        } else {
          errorMessage = error.message
        }
      }

      onError?.(errorMessage)
    }
  }

  const handleStep1Submit = (data: Step1Data) => {
    setFormData(prev => ({ ...prev, ...data }))
    setCurrentStep(2)
  }

  const handleStep2Submit = (data: Step2Data) => {
    const finalData = { ...formData, ...data } as SignupFormData
    onSubmit(finalData)
  }

  const goBack = () => {
    setCurrentStep(1)
  }

  const togglePasswordVisibility = () => {
    setShowPassword(!showPassword)
  }

  const toggleConfirmPasswordVisibility = () => {
    setShowConfirmPassword(!showConfirmPassword)
  }

  return (
    <div className="w-full max-w-md mx-auto">
      {/* Progress Indicator */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-gray-600">Step {currentStep} of 2</span>
          <span className="text-sm text-gray-500">{currentStep === 1 ? 'Account' : 'Business'}</span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-1">
          <div 
            className="bg-blue-600 h-1 rounded-full transition-all duration-300"
            style={{ width: `${(currentStep / 2) * 100}%` }}
          />
        </div>
      </div>

      {/* Error Alert */}
      {error && (
        <Alert variant="destructive" className="mb-6">
          <AlertDescription className="flex items-center justify-between">
            <span>{error}</span>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={clearError}
              className="h-auto p-1 hover:bg-destructive/20"
            >
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </Button>
          </AlertDescription>
        </Alert>
      )}

      {/* Step 1: Account Details */}
      {currentStep === 1 && (
        <form onSubmit={step1Form.handleSubmit(handleStep1Submit)} className="space-y-4">
          <div className="space-y-3">
            <h2 className="text-base font-semibold text-gray-900">Account Details</h2>
            
            {/* Full Name */}
            <div className="space-y-1">
              <Label htmlFor="name" className="text-sm">Full Name</Label>
              <Input
                {...step1Form.register('name')}
                id="name"
                type="text"
                autoComplete="name"
                placeholder="Enter your full name"
                className={`h-10 ${step1Form.formState.errors.name ? 'border-red-500 focus-visible:ring-red-500' : ''}`}
              />
              {step1Form.formState.errors.name && (
                <p className="text-xs text-red-600">{step1Form.formState.errors.name.message}</p>
              )}
            </div>

            {/* Email */}
            <div className="space-y-1">
              <Label htmlFor="email" className="text-sm">Email Address</Label>
              <Input
                {...step1Form.register('email')}
                id="email"
                type="email"
                autoComplete="email"
                placeholder="Enter your email"
                className={`h-10 ${step1Form.formState.errors.email ? 'border-red-500 focus-visible:ring-red-500' : ''}`}
              />
              {step1Form.formState.errors.email && (
                <p className="text-xs text-red-600">{step1Form.formState.errors.email.message}</p>
              )}
            </div>

            {/* Password */}
            <div className="space-y-1">
              <Label htmlFor="password" className="text-sm">Password</Label>
              <div className="relative">
                <Input
                  {...step1Form.register('password')}
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  autoComplete="new-password"
                  placeholder="Create a password"
                  className={`h-10 pr-10 ${step1Form.formState.errors.password ? 'border-red-500 focus-visible:ring-red-500' : ''}`}
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="absolute right-0 top-0 h-full px-2 hover:bg-transparent"
                  onClick={togglePasswordVisibility}
                >
                  {showPassword ? (
                    <EyeOff className="h-3 w-3 text-gray-500" />
                  ) : (
                    <Eye className="h-3 w-3 text-gray-500" />
                  )}
                </Button>
              </div>

              {/* Password Strength Meter */}
              {password && (
                <div className="space-y-1">
                  <div className="flex space-x-1">
                    {[1, 2, 3, 4, 5].map((level) => (
                      <div
                        key={level}
                        className={`h-0.5 flex-1 rounded-full ${
                          level <= passwordStrength
                            ? strengthColors[passwordStrength - 1]
                            : 'bg-gray-200'
                        }`}
                      />
                    ))}
                  </div>
                  <p className="text-xs text-gray-600">
                    {strengthLabels[passwordStrength - 1] || 'Very Weak'}
                  </p>
                </div>
              )}

              {step1Form.formState.errors.password && (
                <p className="text-xs text-red-600">{step1Form.formState.errors.password.message}</p>
              )}
            </div>

            {/* Confirm Password */}
            <div className="space-y-1">
              <Label htmlFor="confirmPassword" className="text-sm">Confirm Password</Label>
              <div className="relative">
                <Input
                  {...step1Form.register('confirmPassword')}
                  id="confirmPassword"
                  type={showConfirmPassword ? 'text' : 'password'}
                  autoComplete="new-password"
                  placeholder="Confirm your password"
                  className={`h-10 pr-10 ${step1Form.formState.errors.confirmPassword ? 'border-red-500 focus-visible:ring-red-500' : ''}`}
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="absolute right-0 top-0 h-full px-2 hover:bg-transparent"
                  onClick={toggleConfirmPasswordVisibility}
                >
                  {showConfirmPassword ? (
                    <EyeOff className="h-3 w-3 text-gray-500" />
                  ) : (
                    <Eye className="h-3 w-3 text-gray-500" />
                  )}
                </Button>
              </div>
              {step1Form.formState.errors.confirmPassword && (
                <p className="text-xs text-red-600">{step1Form.formState.errors.confirmPassword.message}</p>
              )}
            </div>
          </div>

          {/* Step 1 Actions */}
          <div className="space-y-3">
            <Button
              type="submit"
              className="w-full h-10"
            >
              Continue
            </Button>
            
            <p className="text-center text-xs text-gray-600">
              Already have an account?{' '}
              <Link to="/login" className="text-blue-600 hover:text-blue-500 font-medium">
                Log in
              </Link>
            </p>
          </div>
        </form>
      )}

      {/* Step 2: Business Details */}
      {currentStep === 2 && (
        <form onSubmit={step2Form.handleSubmit(handleStep2Submit)} className="space-y-4">
          <div className="space-y-3">
            <h2 className="text-base font-semibold text-gray-900">Business Details</h2>

            {/* Business Name */}
            <div className="space-y-1">
              <Label htmlFor="business_name" className="text-sm">Business Name</Label>
              <Input
                {...step2Form.register('business_name')}
                id="business_name"
                type="text"
                autoComplete="organization"
                placeholder="Enter your business name"
                className={`h-10 ${step2Form.formState.errors.business_name ? 'border-red-500 focus-visible:ring-red-500' : ''}`}
              />
              {step2Form.formState.errors.business_name && (
                <p className="text-xs text-red-600">{step2Form.formState.errors.business_name.message}</p>
              )}
            </div>

            {/* Terms and Privacy */}
            <div className="space-y-2">
              <div className="flex items-start space-x-2">
                <div className="flex items-center h-4">
                  <input
                    {...step2Form.register('termsAccepted')}
                    id="termsAccepted"
                    type="checkbox"
                    className="w-3 h-3 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500 focus:ring-1"
                  />
                </div>
                <div className="text-xs">
                  <label htmlFor="termsAccepted" className="text-gray-700 cursor-pointer">
                    I agree to the{' '}
                    <Link to="/terms" className="text-blue-600 hover:text-blue-500 underline">
                      Terms of Service
                    </Link>{' '}
                    and{' '}
                    <Link to="/privacy" className="text-blue-600 hover:text-blue-500 underline">
                      Privacy Policy
                    </Link>
                  </label>
                  {step2Form.formState.errors.termsAccepted && (
                    <p className="text-xs text-red-600 mt-1">{step2Form.formState.errors.termsAccepted.message}</p>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Step 2 Actions */}
          <div className="space-y-3">
            <div className="flex space-x-2">
              <Button
                type="button"
                variant="outline"
                onClick={goBack}
                className="flex-1 h-10 text-sm"
              >
                Back
              </Button>
              <Button
                type="submit"
                className="flex-1 h-10 text-sm"
                disabled={step2Form.formState.isSubmitting || loading || !termsAccepted}
              >
                {step2Form.formState.isSubmitting || loading ? (
                  <div className="flex items-center space-x-1">
                    <svg className="animate-spin h-3 w-3" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="m4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    <span>Creating...</span>
                  </div>
                ) : (
                  'Create Account'
                )}
              </Button>
            </div>

            {!termsAccepted && (
              <p className="text-xs text-gray-500 text-center">
                Please accept the terms and conditions to continue
              </p>
            )}
          </div>
        </form>
      )}
    </div>
  )
}

export default SignupForm