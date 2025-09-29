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
import { Input } from '@/components/ui/Input'
import { Button } from '@/components/ui/Button'
import { Separator } from '@/components/ui/separator'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/Select'
import { ChevronDown, ChevronRight } from 'lucide-react'
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
  mode?: 'onboarding' | 'settings'
  readOnly?: boolean
  showExtended?: boolean
}

export function BrandBasicsSetup({
  onComplete,
  onCancel,
  mode = 'onboarding',
  readOnly = false,
  showExtended = false,
}: BrandBasicsSetupProps) {
  const { merchant, refreshOnboardingProgress } = useAuth()
  const { toast } = useToast()
  const [isSubmitting, setIsSubmitting] = useState(false)

  const [isExtendedOpen, setIsExtendedOpen] = useState(showExtended)

  const form = useForm<BrandBasicsFormData>({
    resolver: zodResolver(brandBasicsSchema),
    mode: 'onSubmit',
    reValidateMode: 'onBlur',
    defaultValues: {
      description: '',
      currency: 'NGN',
      logo_url: '',
      // Extended fields for settings mode
      website_url: '',
      support_email: '',
      support_phone_e164: '',
      address_line1: '',
      address_line2: '',
      city: '',
      state_region: '',
      postal_code: '',
      country_code: '',
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

      // Load extended fields for settings mode
      if (mode === 'settings' || showExtended) {
        if (merchant.website_url) updates.website_url = merchant.website_url
        if (merchant.support_email) updates.support_email = merchant.support_email
        if (merchant.support_phone_e164) updates.support_phone_e164 = merchant.support_phone_e164
        if (merchant.address_line1) updates.address_line1 = merchant.address_line1
        if (merchant.address_line2) updates.address_line2 = merchant.address_line2
        if (merchant.city) updates.city = merchant.city
        if (merchant.state_region) updates.state_region = merchant.state_region
        if (merchant.postal_code) updates.postal_code = merchant.postal_code
        if (merchant.country_code) updates.country_code = merchant.country_code
      }

      if (Object.keys(updates).length > 0) {
        form.reset(updates)
      }
    }
  }, [merchant, form, mode, showExtended])

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
                  disabled={readOnly}
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
                  disabled={readOnly}
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
              <Select onValueChange={field.onChange} value={field.value} disabled={readOnly}>
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

        {/* Extended Fields for Settings Mode */}
        {(mode === 'settings' || showExtended) && (
          <>
            <Separator className="my-6" />

            <Collapsible open={isExtendedOpen} onOpenChange={setIsExtendedOpen}>
              <CollapsibleTrigger asChild>
                <Button variant="ghost" className="w-full justify-between p-0 font-medium">
                  Contact & Location Details
                  {isExtendedOpen ? (
                    <ChevronDown className="h-4 w-4" />
                  ) : (
                    <ChevronRight className="h-4 w-4" />
                  )}
                </Button>
              </CollapsibleTrigger>

              <CollapsibleContent className="space-y-6 mt-4">
                {/* Website URL */}
                <FormField
                  control={form.control}
                  name="website_url"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Website URL</FormLabel>
                      <FormControl>
                        <Input
                          type="url"
                          placeholder="https://your-website.com"
                          disabled={readOnly}
                          {...field}
                          value={field.value || ''}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                {/* Support Email */}
                <FormField
                  control={form.control}
                  name="support_email"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Support Email</FormLabel>
                      <FormControl>
                        <Input
                          type="email"
                          placeholder="support@your-business.com"
                          disabled={readOnly}
                          {...field}
                          value={field.value || ''}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                {/* Support Phone */}
                <FormField
                  control={form.control}
                  name="support_phone_e164"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Support Phone</FormLabel>
                      <FormControl>
                        <Input
                          type="tel"
                          placeholder="+234 801 234 5678"
                          disabled={readOnly}
                          {...field}
                          value={field.value || ''}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                {/* Address Fields */}
                <div className="space-y-4">
                  <h4 className="font-medium text-sm">Business Address</h4>

                  <FormField
                    control={form.control}
                    name="address_line1"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Address Line 1</FormLabel>
                        <FormControl>
                          <Input
                            placeholder="Street address"
                            disabled={readOnly}
                            {...field}
                            value={field.value || ''}
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={form.control}
                    name="address_line2"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Address Line 2 (Optional)</FormLabel>
                        <FormControl>
                          <Input
                            placeholder="Apartment, suite, etc."
                            disabled={readOnly}
                            {...field}
                            value={field.value || ''}
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <FormField
                      control={form.control}
                      name="city"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>City</FormLabel>
                          <FormControl>
                            <Input
                              placeholder="City"
                              disabled={readOnly}
                              {...field}
                              value={field.value || ''}
                            />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />

                    <FormField
                      control={form.control}
                      name="state_region"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>State/Region</FormLabel>
                          <FormControl>
                            <Input
                              placeholder="State or Region"
                              disabled={readOnly}
                              {...field}
                              value={field.value || ''}
                            />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <FormField
                      control={form.control}
                      name="postal_code"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Postal Code</FormLabel>
                          <FormControl>
                            <Input
                              placeholder="Postal code"
                              disabled={readOnly}
                              {...field}
                              value={field.value || ''}
                            />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />

                    <FormField
                      control={form.control}
                      name="country_code"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Country</FormLabel>
                          <FormControl>
                            <Input
                              placeholder="Nigeria"
                              disabled={readOnly}
                              {...field}
                              value={field.value || ''}
                            />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                  </div>
                </div>
              </CollapsibleContent>
            </Collapsible>
          </>
        )}

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