/**
 * PaymentsSetup - Component for payment provider configuration
 * Allows merchants to connect Paystack or Korapay for payment processing
 */

import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useToast } from '@/hooks/use-toast'
import { useAuth } from '@/hooks/useAuth'
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
import { paymentsApi, PaystackCredentialsRequest, KorapayCredentialsRequest } from '@/lib/api/payments'

const paymentProviderSchema = z.object({
  provider: z.enum(['paystack', 'korapay'], {
    message: "Please select a payment provider",
  }),
  public_key: z.string().min(1, "Public key is required"),
  secret_key: z.string().min(1, "Secret key is required"),
  environment: z.enum(['test', 'live'], {
    message: "Please select an environment"
  }).default('test'),
})

type PaymentProviderFormData = z.infer<typeof paymentProviderSchema>

interface PaymentsSetupProps {
  onComplete?: () => void
  onCancel?: () => void
}

export function PaymentsSetup({ onComplete, onCancel }: PaymentsSetupProps) {
  const { toast } = useToast()
  const { refreshOnboardingProgress } = useAuth()
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isVerifying, setIsVerifying] = useState(false)
  const [isVerified, setIsVerified] = useState(false)
  const [maskedCredentials, setMaskedCredentials] = useState<{
    publicKey?: string
    secretKey?: string
  }>({})

  const form = useForm<PaymentProviderFormData>({
    resolver: zodResolver(paymentProviderSchema),
    defaultValues: {
      provider: undefined,
      public_key: '',
      secret_key: '',
      environment: 'test' as 'test' | 'live',
    },
  })

  const selectedProvider = form.watch('provider')

  const onSubmit = async (data: PaymentProviderFormData) => {
    setIsSubmitting(true)
    try {
      let result;

      if (data.provider === 'paystack') {
        const paystackData: PaystackCredentialsRequest = {
          secret_key: data.secret_key,
          public_key: data.public_key,
          environment: data.environment
        };
        result = await paymentsApi.verifyPaystackCredentials(paystackData);
      } else {
        const korapayData: KorapayCredentialsRequest = {
          public_key: data.public_key,
          secret_key: data.secret_key,
          environment: data.environment
        };
        result = await paymentsApi.verifyKorapayCredentials(korapayData);
      }

      if (result.success) {
        toast({
          title: "Payment provider connected! 💳",
          description: `Successfully connected ${data.provider === 'paystack' ? 'Paystack' : 'Korapay'} for payment processing.`,
        });

        // Refresh onboarding progress
        try {
          await refreshOnboardingProgress();
        } catch (error) {
          console.warn('Failed to refresh onboarding progress:', error);
        }

        onComplete?.();
      } else {
        toast({
          title: "Connection failed",
          description: result.error_message || "Please check your credentials and try again.",
          variant: "destructive",
        });
      }
    } catch (error: any) {
      console.error('Error connecting payment provider:', error);
      const errorMessage = error?.response?.data?.detail || error?.message || "Please check your credentials and try again.";
      toast({
        title: "Connection failed",
        description: errorMessage,
        variant: "destructive",
      });
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
      let result;

      if (formData.provider === 'paystack') {
        const paystackData: PaystackCredentialsRequest = {
          secret_key: formData.secret_key,
          public_key: formData.public_key,
          environment: formData.environment
        };
        result = await paymentsApi.verifyPaystackCredentials(paystackData);
      } else {
        const korapayData: KorapayCredentialsRequest = {
          public_key: formData.public_key,
          secret_key: formData.secret_key,
          environment: formData.environment
        };
        result = await paymentsApi.verifyKorapayCredentials(korapayData);
      }

      if (result.success) {
        toast({
          title: "Verification successful! ✅",
          description: `Your ${formData.provider === 'paystack' ? 'Paystack' : 'Korapay'} credentials are valid and ready to process payments.`,
        });
      } else {
        toast({
          title: "Verification failed",
          description: result.error_message || "Please check your credentials and try again.",
          variant: "destructive",
        });
      }
    } catch (error: any) {
      console.error('Error verifying credentials:', error);
      const errorMessage = error?.response?.data?.detail || error?.message || "Please check your credentials and try again.";
      toast({
        title: "Verification failed",
        description: errorMessage,
        variant: "destructive",
      });
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

          {/* Environment */}
          <FormField
            control={form.control}
            name="environment"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Environment *</FormLabel>
                <Select onValueChange={field.onChange} value={field.value}>
                  <FormControl>
                    <SelectTrigger>
                      <SelectValue placeholder="Select environment" />
                    </SelectTrigger>
                  </FormControl>
                  <SelectContent>
                    <SelectItem value="test">
                      <div className="flex items-center gap-2">
                        <span className="w-2 h-2 bg-orange-400 rounded-full"></span>
                        Test Environment
                      </div>
                    </SelectItem>
                    <SelectItem value="live">
                      <div className="flex items-center gap-2">
                        <span className="w-2 h-2 bg-green-400 rounded-full"></span>
                        Live Environment
                      </div>
                    </SelectItem>
                  </SelectContent>
                </Select>
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
