/**
 * DeliveryRatesSetup - Component for delivery rates configuration
 * Allows merchants to set up shipping zones and delivery pricing
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

const deliveryRateSchema = z.object({
  name: z.string().min(1, "Delivery zone name is required"),
  areas_text: z.string().min(1, "Please specify delivery areas"),
  price_kobo: z.number().min(0, "Price must be positive"),
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
      price_kobo: 0,
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
    try {
      // TODO: Implement delivery rates API call
      // await onboardingApi.createDeliveryRates(deliveryRates)
      
      // Simulate API call for now
      await new Promise(resolve => setTimeout(resolve, 1000))
      
      toast({
        title: "Delivery rates configured! 🚚",
        description: `Successfully configured ${deliveryRates.length} delivery zones.`,
      })

      onComplete?.()
    } catch (error) {
      console.error('Error saving delivery rates:', error)
      toast({
        title: "Save failed",
        description: "Please try again later.",
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
              name="price_kobo"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Price (Kobo) *</FormLabel>
                  <FormControl>
                    <Input
                      type="number"
                      placeholder="150000"
                      className="h-12"
                      {...field}
                      onChange={(e) => field.onChange(parseInt(e.target.value) || 0)}
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
                <div className="text-sm text-gray-600">₦{(rate.price_kobo / 100).toLocaleString()}</div>
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
              Saving...
            </>
          ) : (
            `Complete Setup (${deliveryRates.length} zones)`
          )}
        </Button>
      </div>
    </div>
  )
}
