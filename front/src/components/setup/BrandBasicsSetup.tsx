/**
 * BrandBasicsSetup - Wrapper component for brand basics setup in dashboard
 * Reuses Step1BrandBasics form logic but adapts for setup card context
 */

import { useState, useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { useAuth } from '@/hooks/useAuth'
import { useToast } from '@/hooks/use-toast'
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form'
import { Textarea } from '@/components/ui/textarea'
import { Button } from '@/components/ui/Button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/Select'
import { ImageUpload } from '@/components/setup/ui/ImageUpload'
import { brandBasicsSchema, type BrandBasicsFormData } from '@/lib/form-schemas/brand-basics'
import { onboardingApi } from '@/lib/onboarding-api'
import type { Currency } from '@/types/onboarding'

const currencies: { value: Currency; label: string }[] = [
  { value: 'NGN', label: 'Nigerian Naira (₦)' },
  { value: 'USD', label: 'US Dollar ($)' },
  { value: 'GHS', label: 'Ghanaian Cedi (₵)' },
  { value: 'KES', label: 'Kenyan Shilling (KSh)' },
]

interface BrandBasicsSetupProps {
  onComplete?: () => void
  onCancel?: () => void
}

export function BrandBasicsSetup({ onComplete, onCancel }: BrandBasicsSetupProps) {
  const { merchant, refreshOnboardingProgress } = useAuth()
  const { toast } = useToast()
  const [isSubmitting, setIsSubmitting] = useState(false)

  const form = useForm<BrandBasicsFormData>({
    resolver: zodResolver(brandBasicsSchema),
    mode: 'onSubmit',
    reValidateMode: 'onBlur',
    defaultValues: {
      description: '',
      currency: 'NGN',
      logo_url: '',
    },
  })

  // Load existing merchant data when available
  useEffect(() => {
    if (merchant) {
      const updates: Partial<BrandBasicsFormData> = {}

      if (merchant.description) {
        updates.description = merchant.description
      }

      if (merchant.currency) {
        updates.currency = merchant.currency as any
      }

      if (merchant.logo_url) {
        updates.logo_url = merchant.logo_url
      }

      if (Object.keys(updates).length > 0) {
        form.reset(updates)
      }
    }
  }, [merchant, form])

  const onSubmit = async (data: BrandBasicsFormData) => {
    setIsSubmitting(true)
    try {
      // Save merchant profile data via API
      await onboardingApi.updateMerchantProfile(data as BrandBasicsFormData)

      // Refresh progress in auth context (this will automatically reflect completion)
      await refreshOnboardingProgress()

      // Call completion callback (this will close the dialog and show success toast)
      onComplete?.()
    } catch (error) {
      console.error('Error saving brand basics:', error)
      toast({
        title: "Error saving brand basics",
        description: "Please try again later.",
        variant: "destructive",
      })
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
        {/* Logo Upload */}
        <FormField
          control={form.control}
          name="logo_url"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Business Logo</FormLabel>
              <FormControl>
                <ImageUpload
                  value={field.value ?? ''}
                  onChange={(v) => field.onChange(v ?? '')}
                  onRemove={() => field.onChange('')}
                  placeholder="Upload your business logo"
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        {/* Description */}
        <FormField
          control={form.control}
          name="description"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Business Description *</FormLabel>
              <FormControl>
                <Textarea
                  placeholder="Describe what you sell and what makes your business special... (minimum 10 characters)"
                  className="min-h-[100px]"
                  {...field}
                />
              </FormControl>
              <div className="text-sm text-muted-foreground">
                {field.value?.length || 0}/10 characters minimum
              </div>
              <FormMessage />
            </FormItem>
          )}
        />

        {/* Currency */}
        <FormField
          control={form.control}
          name="currency"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Primary Currency (Choose from the list) *</FormLabel>
              <Select onValueChange={field.onChange} value={field.value}>
                <FormControl>
                  <SelectTrigger>
                    <SelectValue placeholder="Select your currency" />
                  </SelectTrigger>
                </FormControl>
                <SelectContent>
                  {currencies.map((currency) => (
                    <SelectItem key={currency.value} value={currency.value}>
                      {currency.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <FormMessage />
            </FormItem>
          )}
        />

        {/* Action Buttons */}
        <div className="flex justify-end gap-3 pt-4 border-t">
          {onCancel && (
            <Button
              type="button"
              variant="outline"
              onClick={onCancel}
              disabled={isSubmitting}
            >
              Cancel
            </Button>
          )}
          <Button
            type="submit"
            disabled={isSubmitting}
          >
            {isSubmitting ? 'Saving...' : 'Save & Complete'}
          </Button>
        </div>
      </form>
    </Form>
  )
}