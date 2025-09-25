/**
 * DeliveryRatesSetup - Component for delivery rates configuration
 * Allows merchants to set up shipping zones and delivery pricing
 *
 * IMPORTANT: Backend requires ADMIN role for creating delivery rates.
 * Users with STAFF role will get 403 Forbidden errors.
 */

import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useToast } from '@/hooks/use-toast'
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form'
import { Input } from '@/components/ui/Input'
import { Textarea } from '@/components/ui/textarea'
import { Button } from '@/components/ui/Button'
import { Alert, AlertDescription } from '@/components/ui/Alert'
import { Loader2, Plus, Trash2 } from 'lucide-react'
import { nairaToKobo, koboToNairaDisplay } from '@/lib/format'
import { onboardingApi } from '@/lib/api/onboarding'
import type { CreateDeliveryRateRequest } from '@/types/onboarding'

const deliveryRateSchema = z.object({
  name: z.string().min(1, "Delivery zone name is required"),
  areas_text: z.string().min(1, "Please specify delivery areas"),
  price_naira: z.union([z.string(), z.number()])
    .transform(v => String(v))
    .refine(v => /^\d+(\.\d{0,2})?$/.test(v.replace(/,/g, "")), "Enter a valid amount (max 2 decimals)")
    .refine(v => parseFloat(v.replace(/,/g, "")) >= 0, "Price must be positive"),
})

type DeliveryRateFormData = z.infer<typeof deliveryRateSchema>

interface DeliveryRatesSetupProps {
  onComplete?: () => void
  onCancel?: () => void
}

export function DeliveryRatesSetup({ onComplete, onCancel }: DeliveryRatesSetupProps) {
  const { toast } = useToast()
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [deliveryRates, setDeliveryRates] = useState<DeliveryRateFormData[]>([])

  const form = useForm<DeliveryRateFormData>({
    resolver: zodResolver(deliveryRateSchema),
    defaultValues: {
      name: '',
      areas_text: '',
      price_naira: '',
    },
  })

  const addDeliveryRate = (data: DeliveryRateFormData) => {
    setDeliveryRates([...deliveryRates, data])
    form.reset()
    toast({
      title: "Delivery rate added",
      description: `Added ${data.name} delivery zone.`,
    })
  }

  const removeDeliveryRate = (index: number) => {
    setDeliveryRates(deliveryRates.filter((_, i) => i !== index))
  }

  const onSubmit = async (data: DeliveryRateFormData) => {
    addDeliveryRate(data)
  }

  const handleComplete = async () => {
    if (deliveryRates.length === 0) {
      toast({
        title: "Add delivery rates first",
        description: "Please add at least one delivery rate before completing setup.",
        variant: "destructive",
      })
      return
    }

    setIsSubmitting(true)
    const createdRates: string[] = []
    let failedCount = 0

    try {
      // Convert Naira prices to kobo for API submission and create each rate
      for (let i = 0; i < deliveryRates.length; i++) {
        const rate = deliveryRates[i]
        try {
          const apiPayload: CreateDeliveryRateRequest = {
            name: rate.name,
            areas_text: rate.areas_text,
            price_kobo: nairaToKobo(rate.price_naira),
            description: undefined // Optional field
          }

          const createdRate = await onboardingApi.createDeliveryRate(apiPayload)
          createdRates.push(createdRate.name)

          // Show progress for multiple rates
          if (deliveryRates.length > 1) {
            toast({
              title: `Created ${rate.name}`,
              description: `${i + 1} of ${deliveryRates.length} delivery zones created.`,
            })
          }
        } catch (error) {
          console.error(`Failed to create delivery rate "${rate.name}":`, error)
          failedCount++

          // Show specific error for this rate
          toast({
            title: `Failed to create ${rate.name}`,
            description: error instanceof Error ? error.message : "Unknown error occurred.",
            variant: "destructive",
          })
        }
      }

      // Final summary
      if (createdRates.length > 0) {
        toast({
          title: "Delivery rates configured! 🚚",
          description: `Successfully created ${createdRates.length} delivery zone(s).${failedCount > 0 ? ` ${failedCount} failed.` : ''}`,
          variant: failedCount > 0 ? "destructive" : "default",
        })

        // Only call onComplete if at least one rate was created successfully
        if (createdRates.length === deliveryRates.length) {
          onComplete?.()
        }
      } else {
        // All rates failed
        toast({
          title: "All delivery rates failed",
          description: "No delivery rates were created. Please check your connection and try again.",
          variant: "destructive",
        })
      }
    } catch (error) {
      console.error('Unexpected error during delivery rates creation:', error)
      toast({
        title: "Setup failed",
        description: "An unexpected error occurred. Please try again later.",
        variant: "destructive",
      })
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="space-y-6">
      <Alert>
        <AlertDescription>
          Set up delivery zones and pricing for your store. Customers will see these options during checkout.
        </AlertDescription>
      </Alert>

      {/* Add New Delivery Rate Form */}
      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4 p-4 border rounded-lg bg-gray-50">
          <h4 className="font-medium text-gray-900">Add Delivery Zone</h4>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <FormField
              control={form.control}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Zone Name *</FormLabel>
                  <FormControl>
                    <Input
                      placeholder="e.g., Lagos Mainland"
                      className="h-12"
                      {...field}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="price_naira"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Price (₦) *</FormLabel>
                  <FormControl>
                    <Input
                      type="text"
                      placeholder="1500.00"
                      className="h-12"
                      {...field}
                      onChange={(e) => {
                        let value = e.target.value.replace(/[^0-9.]/g, '');
                        // Prevent multiple decimal points
                        const decimalCount = (value.match(/\./g) || []).length;
                        if (decimalCount > 1) {
                          value = value.slice(0, value.lastIndexOf('.'));
                        }
                        // Limit to 2 decimal places
                        const parts = value.split('.');
                        if (parts[1] && parts[1].length > 2) {
                          parts[1] = parts[1].slice(0, 2);
                          value = parts.join('.');
                        }
                        field.onChange(value);
                      }}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="areas_text"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Delivery Areas *</FormLabel>
                  <FormControl>
                    <Textarea
                      placeholder="Victoria Island, Ikoyi, Lagos Island"
                      className="min-h-[40px]"
                      {...field}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
          </div>

          <Button type="submit" className="w-full">
            <Plus className="w-4 h-4 mr-2" />
            Add Delivery Zone
          </Button>
        </form>
      </Form>

      {/* Existing Delivery Rates */}
      {deliveryRates.length > 0 && (
        <div className="space-y-3">
          <h4 className="font-medium text-gray-900">Configured Delivery Zones</h4>
          {deliveryRates.map((rate, index) => (
            <div key={index} className="flex items-center justify-between p-3 border rounded-lg bg-white">
              <div>
                <div className="font-medium text-gray-900">{rate.name}</div>
                <div className="text-sm text-gray-600">{koboToNairaDisplay(nairaToKobo(rate.price_naira))}</div>
                <div className="text-sm text-gray-500">{rate.areas_text}</div>
              </div>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => removeDeliveryRate(index)}
              >
                <Trash2 className="w-4 h-4" />
              </Button>
            </div>
          ))}
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex justify-between gap-3 pt-4 border-t">
        <div>
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
        </div>
        
        <Button
          onClick={handleComplete}
          disabled={isSubmitting || deliveryRates.length === 0}
        >
          {isSubmitting ? (
            <>
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              Creating delivery zones...
            </>
          ) : (
            `Complete Setup (${deliveryRates.length} zones)`
          )}
        </Button>
      </div>
    </div>
  )
}
