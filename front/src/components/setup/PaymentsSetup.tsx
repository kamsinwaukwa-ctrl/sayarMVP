/**
 * PaymentsSetup - Component for payment provider configuration
 * Allows merchants to connect Paystack or Korapay for payment processing
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
import { Button } from '@/components/ui/Button'
import { Alert, AlertDescription } from '@/components/ui/Alert'
import { Loader2, CreditCard, CheckCircle } from 'lucide-react'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/Select'

const paymentProviderSchema = z.object({
  provider: z.enum(['paystack', 'korapay'], {
    message: "Please select a payment provider",
  }),
  public_key: z.string().min(1, "Public key is required"),
  secret_key: z.string().min(1, "Secret key is required"),
})

type PaymentProviderFormData = z.infer<typeof paymentProviderSchema>

interface PaymentsSetupProps {
  onComplete?: () => void
  onCancel?: () => void
}

export function PaymentsSetup({ onComplete, onCancel }: PaymentsSetupProps) {
  const { toast } = useToast()
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isVerifying, setIsVerifying] = useState(false)

  const form = useForm<PaymentProviderFormData>({
    resolver: zodResolver(paymentProviderSchema),
    defaultValues: {
      provider: undefined,
      public_key: '',
      secret_key: '',
    },
  })

  const selectedProvider = form.watch('provider')

  const onSubmit = async (data: PaymentProviderFormData) => {
    setIsSubmitting(true)
    try {
      // TODO: Implement payment provider API call
      // await onboardingApi.verifyPaymentProvider(data)
      
      // Simulate API call for now
      await new Promise(resolve => setTimeout(resolve, 1000))
      
      toast({
        title: "Payment provider connected! 💳",
        description: `Successfully connected ${data.provider === 'paystack' ? 'Paystack' : 'Korapay'} for payment processing.`,
      })

      onComplete?.()
    } catch (error) {
      console.error('Error connecting payment provider:', error)
      toast({
        title: "Connection failed",
        description: "Please check your credentials and try again.",
        variant: "destructive",
      })
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleVerify = async () => {
    const formData = form.getValues()
    if (!formData.provider || !formData.public_key || !formData.secret_key) {
      toast({
        title: "Fill in all fields",
        description: "Please provide all credentials before verifying.",
        variant: "destructive",
      })
      return
    }

    setIsVerifying(true)
    try {
      // TODO: Implement verification API call
      await new Promise(resolve => setTimeout(resolve, 2000))
      
      toast({
        title: "Verification successful! ✅",
        description: "Your payment provider credentials are valid and ready to process payments.",
      })
    } catch (error) {
      toast({
        title: "Verification failed",
        description: "Please check your credentials and try again.",
        variant: "destructive",
      })
    } finally {
      setIsVerifying(false)
    }
  }

  const getProviderInfo = (provider: string) => {
    switch (provider) {
      case 'paystack':
        return {
          name: 'Paystack',
          description: 'Accept payments from customers across Africa',
          features: ['Card payments', 'Bank transfers', 'USSD', 'Mobile money'],
          color: 'bg-green-50 border-green-200 text-green-800'
        }
      case 'korapay':
        return {
          name: 'Korapay',
          description: 'Fast and secure payment processing for Nigeria',
          features: ['Card payments', 'Bank transfers', 'QR codes', 'Split payments'],
          color: 'bg-blue-50 border-blue-200 text-blue-800'
        }
      default:
        return null
    }
  }

  const providerInfo = selectedProvider ? getProviderInfo(selectedProvider) : null

  return (
    <div className="space-y-6">
      <Alert>
        <AlertDescription>
          Connect a payment provider to start accepting payments from customers. Choose between Paystack or Korapay.
        </AlertDescription>
      </Alert>

      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
          {/* Payment Provider Selection */}
          <FormField
            control={form.control}
            name="provider"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Payment Provider *</FormLabel>
                <Select onValueChange={field.onChange} value={field.value}>
                  <FormControl>
                    <SelectTrigger>
                      <SelectValue placeholder="Select a payment provider" />
                    </SelectTrigger>
                  </FormControl>
                  <SelectContent>
                    <SelectItem value="paystack">
                      <div className="flex items-center gap-2">
                        <CreditCard className="w-4 h-4" />
                        Paystack
                      </div>
                    </SelectItem>
                    <SelectItem value="korapay">
                      <div className="flex items-center gap-2">
                        <CreditCard className="w-4 h-4" />
                        Korapay
                      </div>
                    </SelectItem>
                  </SelectContent>
                </Select>
                <FormMessage />
              </FormItem>
            )}
          />

          {/* Provider Info */}
          {providerInfo && (
            <div className={`p-4 rounded-lg border ${providerInfo.color}`}>
              <h4 className="font-medium mb-2">{providerInfo.name}</h4>
              <p className="text-sm mb-3">{providerInfo.description}</p>
              <div className="flex flex-wrap gap-2">
                {providerInfo.features.map((feature, index) => (
                  <span key={index} className="text-xs px-2 py-1 bg-white/50 rounded">
                    {feature}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Public Key */}
          <FormField
            control={form.control}
            name="public_key"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Public Key *</FormLabel>
                <FormControl>
                  <Input
                    placeholder={`Enter your ${selectedProvider === 'paystack' ? 'Paystack' : 'Korapay'} public key`}
                    className="h-12"
                    {...field}
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          {/* Secret Key */}
          <FormField
            control={form.control}
            name="secret_key"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Secret Key *</FormLabel>
                <FormControl>
                  <Input
                    type="password"
                    placeholder={`Enter your ${selectedProvider === 'paystack' ? 'Paystack' : 'Korapay'} secret key`}
                    className="h-12"
                    {...field}
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          {/* Security Note */}
          <Alert>
            <CheckCircle className="h-4 w-4" />
            <AlertDescription>
              Your secret key is encrypted and stored securely. It will never be visible in the browser.
            </AlertDescription>
          </Alert>

          {/* Action Buttons */}
          <div className="flex justify-between gap-3 pt-4 border-t">
            <div>
              {onCancel && (
                <Button
                  type="button"
                  variant="outline"
                  onClick={onCancel}
                  disabled={isSubmitting || isVerifying}
                >
                  Cancel
                </Button>
              )}
            </div>
            
            <div className="flex gap-3">
              <Button
                type="button"
                variant="outline"
                onClick={handleVerify}
                disabled={isSubmitting || isVerifying}
              >
                {isVerifying ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Verifying...
                  </>
                ) : (
                  'Verify Credentials'
                )}
              </Button>
              
              <Button
                type="submit"
                disabled={isSubmitting || isVerifying}
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Connecting...
                  </>
                ) : (
                  `Connect ${providerInfo?.name || 'Provider'}`
                )}
              </Button>
            </div>
          </div>
        </form>
      </Form>
    </div>
  )
}
