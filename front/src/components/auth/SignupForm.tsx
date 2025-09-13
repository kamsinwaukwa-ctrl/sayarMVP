/**
 * Signup Form Component for Sayar WhatsApp Commerce Platform
 * Professional ShadCN/UI implementation with proper spacing and modern design
 */

import React, { useState } from 'react'
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

const signupSchema = yup.object({
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
  business_name: yup
    .string()
    .min(2, 'Business name must be at least 2 characters')
    .max(100, 'Business name must be less than 100 characters')
    .required('Business name is required'),
  whatsapp_phone_e164: yup
    .string()
    .matches(
      /^\+[1-9]\d{1,14}$/,
      'Please enter a valid WhatsApp phone number in international format (e.g., +234801234567)'
    )
    .optional(),
})

interface SignupFormData extends RegisterRequest {
  confirmPassword: string
}

interface SignupFormProps {
  onSuccess?: () => void
  onError?: (error: string) => void
}

const SignupForm: React.FC<SignupFormProps> = ({ onSuccess, onError }) => {
  const { register: registerUser, loading, error, clearError } = useAuth()
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
    reset,
  } = useForm<SignupFormData>({
    resolver: yupResolver(signupSchema),
    mode: 'onBlur',
  })

  const onSubmit = async (data: SignupFormData) => {
    clearError()
    
    try {
      const { confirmPassword, ...registerData } = data
      await registerUser(registerData)
      reset()
      onSuccess?.()
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

  const togglePasswordVisibility = () => {
    setShowPassword(!showPassword)
  }

  const toggleConfirmPasswordVisibility = () => {
    setShowConfirmPassword(!showConfirmPassword)
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
      {/* Error Alert */}
      {error && (
        <Alert variant="destructive">
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

      {/* Personal Information Section */}
      <div className="space-y-4">
        {/* Full Name */}
        <div className="space-y-2">
          <Label htmlFor="name">Full Name</Label>
          <Input
            {...register('name')}
            id="name"
            type="text"
            autoComplete="name"
            placeholder="Enter your full name"
            className={errors.name ? 'border-red-500 focus-visible:ring-red-500' : ''}
          />
          {errors.name && (
            <p className="text-sm text-red-600">{errors.name.message}</p>
          )}
        </div>

        {/* Email */}
        <div className="space-y-2">
          <Label htmlFor="email">Email Address</Label>
          <Input
            {...register('email')}
            id="email"
            type="email"
            autoComplete="email"
            placeholder="Enter your email"
            className={errors.email ? 'border-red-500 focus-visible:ring-red-500' : ''}
          />
          {errors.email && (
            <p className="text-sm text-red-600">{errors.email.message}</p>
          )}
        </div>
      </div>

      {/* Business Information Section */}
      <div className="space-y-4">
        {/* Business Name */}
        <div className="space-y-2">
          <Label htmlFor="business_name">Business Name</Label>
          <Input
            {...register('business_name')}
            id="business_name"
            type="text"
            autoComplete="organization"
            placeholder="Enter your business name"
            className={errors.business_name ? 'border-red-500 focus-visible:ring-red-500' : ''}
          />
          {errors.business_name && (
            <p className="text-sm text-red-600">{errors.business_name.message}</p>
          )}
        </div>

        {/* WhatsApp Phone (Optional) */}
        <div className="space-y-2">
          <Label htmlFor="whatsapp_phone_e164">
            WhatsApp Number <span className="text-gray-400">(optional)</span>
          </Label>
          <Input
            {...register('whatsapp_phone_e164')}
            id="whatsapp_phone_e164"
            type="tel"
            autoComplete="tel"
            placeholder="e.g., +234801234567"
            className={errors.whatsapp_phone_e164 ? 'border-red-500 focus-visible:ring-red-500' : ''}
          />
          {errors.whatsapp_phone_e164 && (
            <p className="text-sm text-red-600">{errors.whatsapp_phone_e164.message}</p>
          )}
        </div>
      </div>

      {/* Security Section */}
      <div className="space-y-4">
        {/* Password */}
        <div className="space-y-2">
          <Label htmlFor="password">Password</Label>
          <div className="relative">
            <Input
              {...register('password')}
              id="password"
              type={showPassword ? 'text' : 'password'}
              autoComplete="new-password"
              placeholder="Create a password"
              className={`pr-12 ${errors.password ? 'border-red-500 focus-visible:ring-red-500' : ''}`}
            />
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="absolute right-0 top-0 h-full px-3 hover:bg-transparent"
              onClick={togglePasswordVisibility}
            >
              {showPassword ? (
                <EyeOff className="h-4 w-4 text-gray-500" />
              ) : (
                <Eye className="h-4 w-4 text-gray-500" />
              )}
            </Button>
          </div>
          {errors.password && (
            <p className="text-sm text-red-600">{errors.password.message}</p>
          )}
        </div>

        {/* Confirm Password */}
        <div className="space-y-2">
          <Label htmlFor="confirmPassword">Confirm Password</Label>
          <div className="relative">
            <Input
              {...register('confirmPassword')}
              id="confirmPassword"
              type={showConfirmPassword ? 'text' : 'password'}
              autoComplete="new-password"
              placeholder="Confirm your password"
              className={`pr-12 ${errors.confirmPassword ? 'border-red-500 focus-visible:ring-red-500' : ''}`}
            />
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="absolute right-0 top-0 h-full px-3 hover:bg-transparent"
              onClick={toggleConfirmPasswordVisibility}
            >
              {showConfirmPassword ? (
                <EyeOff className="h-4 w-4 text-gray-500" />
              ) : (
                <Eye className="h-4 w-4 text-gray-500" />
              )}
            </Button>
          </div>
          {errors.confirmPassword && (
            <p className="text-sm text-red-600">{errors.confirmPassword.message}</p>
          )}
        </div>
      </div>

      {/* Submit Button */}
      <Button
        type="submit"
        className="w-full h-11"
        disabled={isSubmitting || loading}
      >
        {isSubmitting || loading ? (
          <div className="flex items-center space-x-2">
            <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="m4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            <span>Creating Account...</span>
          </div>
        ) : (
          'Create Account'
        )}
      </Button>

      {/* Terms */}
      <p className="text-center text-xs text-gray-500">
        By creating an account, you agree to our{' '}
        <span className="text-blue-600 hover:text-blue-500 cursor-pointer">Terms of Service</span>{' '}
        and{' '}
        <span className="text-blue-600 hover:text-blue-500 cursor-pointer">Privacy Policy</span>.
      </p>
    </form>
  )
}

export default SignupForm