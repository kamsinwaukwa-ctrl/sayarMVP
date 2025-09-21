/**
 * WhatsAppIntegrationSetup - Component for WhatsApp Business integration setup
 * Allows merchants to connect their WhatsApp Business account
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
import { Loader2, ExternalLink, MessageCircle } from 'lucide-react'

const whatsappCredentialsSchema = z.object({
  whatsapp_phone_number: z.string().min(1, "WhatsApp phone number is required"),
  whatsapp_business_account_id: z.string().min(1, "Business Account ID is required"),
  whatsapp_access_token: z.string().min(1, "Access Token is required"),
})

type WhatsAppCredentialsFormData = z.infer<typeof whatsappCredentialsSchema>

interface WhatsAppIntegrationSetupProps {
  onComplete?: () => void
  onCancel?: () => void
}

export function WhatsAppIntegrationSetup({ onComplete, onCancel }: WhatsAppIntegrationSetupProps) {
  const { toast } = useToast()
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isVerifying, setIsVerifying] = useState(false)

  const form = useForm<WhatsAppCredentialsFormData>({
    resolver: zodResolver(whatsappCredentialsSchema),
    defaultValues: {
      whatsapp_phone_number: '',
      whatsapp_business_account_id: '',
      whatsapp_access_token: '',
    },
  })

  const onSubmit = async (_data: WhatsAppCredentialsFormData) => {
    setIsSubmitting(true)
    try {
      // TODO: Implement WhatsApp credentials API call
      // await onboardingApi.updateWhatsAppCredentials(data)
      
      // Simulate API call for now
      await new Promise(resolve => setTimeout(resolve, 1000))
      
      toast({
        title: "WhatsApp connected! 📱",
        description: "Your WhatsApp Business account is now connected and ready to receive orders.",
      })

      onComplete?.()
    } catch (error) {
      console.error('Error connecting WhatsApp:', error)
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
    setIsVerifying(true)
    try {
      // TODO: Implement verification API call
      await new Promise(resolve => setTimeout(resolve, 2000))
      
      toast({
        title: "Verification successful! ✅",
        description: "Your WhatsApp credentials are valid and the phone number is verified.",
      })
    } catch (error) {
      toast({
        title: "Verification failed",
        description: "Please check your credentials and phone number.",
        variant: "destructive",
      })
    } finally {
      setIsVerifying(false)
    }
  }

  return (
    <div className="space-y-6">
      <Alert>
        <AlertDescription>
          Connect your WhatsApp Business account to enable customers to place orders directly through WhatsApp messages.
        </AlertDescription>
      </Alert>

      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
          {/* WhatsApp Phone Number */}
          <FormField
            control={form.control}
            name="whatsapp_phone_number"
            render={({ field }) => (
              <FormItem>
                <FormLabel>WhatsApp Business Phone Number *</FormLabel>
                <FormControl>
                  <Input
                    placeholder="+2348123456789"
                    className="h-12"
                    {...field}
                  />
                </FormControl>
                <p className="text-sm text-gray-500">
                  Include country code (e.g., +234 for Nigeria)
                </p>
                <FormMessage />
              </FormItem>
            )}
          />

          {/* Business Account ID */}
          <FormField
            control={form.control}
            name="whatsapp_business_account_id"
            render={({ field }) => (
              <FormItem>
                <FormLabel>WhatsApp Business Account ID *</FormLabel>
                <FormControl>
                  <Input
                    placeholder="Enter your Business Account ID"
                    className="h-12"
                    {...field}
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          {/* Access Token */}
          <FormField
            control={form.control}
            name="whatsapp_access_token"
            render={({ field }) => (
              <FormItem>
                <FormLabel>WhatsApp Access Token *</FormLabel>
                <FormControl>
                  <Input
                    type="password"
                    placeholder="Enter your WhatsApp Access Token"
                    className="h-12"
                    {...field}
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          {/* Features Preview */}
          <div className="p-4 bg-green-50 rounded-lg border border-green-200">
            <div className="flex items-center gap-2 mb-3">
              <MessageCircle className="w-5 h-5 text-green-600" />
              <h4 className="font-medium text-green-800">WhatsApp Commerce Features</h4>
            </div>
            <ul className="text-sm text-green-700 space-y-1">
              <li>• Customers can browse products via WhatsApp</li>
              <li>• Direct order placement through chat</li>
              <li>• Automated order confirmations</li>
              <li>• Real-time order status updates</li>
            </ul>
          </div>

          {/* Help Link */}
          <div className="p-4 bg-blue-50 rounded-lg">
            <p className="text-sm text-blue-800 mb-2">
              Need help setting up WhatsApp Business API?
            </p>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => window.open('https://developers.facebook.com/docs/whatsapp', '_blank')}
            >
              <ExternalLink className="w-4 h-4 mr-2" />
              WhatsApp Business API Docs
            </Button>
          </div>

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
                  'Verify Connection'
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
                  'Connect WhatsApp'
                )}
              </Button>
            </div>
          </div>
        </form>
      </Form>
    </div>
  )
}
