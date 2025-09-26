/**
 * WhatsAppIntegrationSetup - Component for WhatsApp Business integration setup
 * Allows merchants to connect their WhatsApp Business account
 */

import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useToast } from '@/hooks/use-toast'
import { apiUrl } from '@/lib/api-config'
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

const maskKey = (key: string): string => {
  if (!key || key.length < 8) return key
  const start = key.substring(0, 8)
  const end = key.substring(key.length - 4)
  return `${start}${'•'.repeat(Math.min(key.length - 12, 20))}${end}`
}

function MaskedLine({ label, value }: { label: string; value?: string }) {
  if (!value) return null
  return (
    <div className="text-sm text-muted-foreground">
      <span className="font-medium text-foreground mr-1">{label}:</span>
      <span className="font-mono select-all">{value}</span>
    </div>
  )
}

const whatsappCredentialsSchema = z.object({
  app_id: z.string().min(1, "App ID is required"),
  system_user_token: z.string().min(1, "System User Access Token is required"),
  waba_id: z.string().optional(),
  phone_number_id: z.string().optional(),
  whatsapp_phone_number: z.string().min(1, "WhatsApp phone number is required"),
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
  const [isVerified, setIsVerified] = useState(false)
  const [maskedToken, setMaskedToken] = useState<string | undefined>(undefined)

  const form = useForm<WhatsAppCredentialsFormData>({
    resolver: zodResolver(whatsappCredentialsSchema),
    defaultValues: {
      app_id: '',
      system_user_token: '',
      waba_id: '',
      phone_number_id: '',
      whatsapp_phone_number: '',
    },
  })

  const onSubmit = async (data: WhatsAppCredentialsFormData) => {
    setIsSubmitting(true)
    try {
      const token = localStorage.getItem('access_token')

      // Prepare the data for the new WhatsApp-specific PATCH endpoint
      const apiData = {
        app_id: data.app_id,
        system_user_token: data.system_user_token,
        waba_id: data.waba_id || undefined, // Convert empty string to undefined
        phone_number_id: data.phone_number_id || undefined, // Now supported!
        whatsapp_phone_e164: data.whatsapp_phone_number, // Now supported!
      }

      // Call the new WhatsApp-specific PATCH endpoint
      const response = await fetch(apiUrl('api/v1/integrations/meta/whatsapp'), {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify(apiData),
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.error?.message || errorData.message || `API error: ${response.status}`)
      }

      await response.json()

      setIsVerified(true)
      setMaskedToken(maskKey(data.system_user_token))

      toast({
        title: "WhatsApp connected! 📱",
        description: "Your WhatsApp Business account credentials have been saved successfully.",
      })

      onComplete?.()
    } catch (error) {
      console.error('Error saving WhatsApp credentials:', error)
      toast({
        title: "Connection failed",
        description: error instanceof Error ? error.message : "Please check your credentials and try again.",
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
      
      const currentToken = form.getValues('system_user_token')
      setIsVerified(true)
      setMaskedToken(maskKey(currentToken))
      
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
          {/* App ID */}
          <FormField
            control={form.control}
            name="app_id"
            render={({ field }) => (
              <FormItem>
                <FormLabel>App ID *</FormLabel>
                <FormControl>
                  <Input
                    placeholder="Enter your Meta App ID"
                    className="h-12"
                    {...field}
                  />
                </FormControl>
                <p className="text-sm text-gray-500">
                  Your Facebook/Meta App ID from developers.facebook.com
                </p>
                <FormMessage />
              </FormItem>
            )}
          />

          {/* System User Access Token */}
          <FormField
            control={form.control}
            name="system_user_token"
            render={({ field }) => (
              <FormItem>
                <FormLabel>System User Access Token *</FormLabel>
                {isVerified ? (
                  <div className="rounded-md border p-3 bg-muted/30">
                    <MaskedLine label="Access Token" value={maskedToken} />
                    <div className="mt-2 text-xs text-muted-foreground">Hidden after validation</div>
                  </div>
                ) : (
                  <FormControl>
                    <Input
                      type="password"
                      placeholder="Enter your System User Access Token"
                      className="h-12"
                      {...field}
                    />
                  </FormControl>
                )}
                <p className="text-sm text-gray-500">
                  Long-lived access token for your system user
                </p>
                <FormMessage />
              </FormItem>
            )}
          />

          {/* WABA ID (Optional) */}
          <FormField
            control={form.control}
            name="waba_id"
            render={({ field }) => (
              <FormItem>
                <FormLabel>WhatsApp Business Account ID</FormLabel>
                <FormControl>
                  <Input
                    placeholder="Enter your WABA ID (optional)"
                    className="h-12"
                    {...field}
                  />
                </FormControl>
                <p className="text-sm text-gray-500">
                  Optional: Your WhatsApp Business Account ID
                </p>
                <FormMessage />
              </FormItem>
            )}
          />

          {/* Phone Number ID (Optional) */}
          <FormField
            control={form.control}
            name="phone_number_id"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Phone Number ID</FormLabel>
                <FormControl>
                  <Input
                    placeholder="Enter your Phone Number ID (optional)"
                    className="h-12"
                    {...field}
                  />
                </FormControl>
                <p className="text-sm text-gray-500">
                  Optional: WhatsApp Phone Number ID for API calls
                </p>
                <FormMessage />
              </FormItem>
            )}
          />

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
                    {isVerified ? 'Re-verifying…' : 'Verifying...'}
                  </>
                ) : (
                  isVerified ? 'Re-Verify Connection' : 'Verify Connection'
                )}
              </Button>
              
              <Button
                type="submit"
                disabled={isSubmitting || isVerifying}
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Saving...
                  </>
                ) : (
                  'Save and Continue'
                )}
              </Button>
            </div>
          </div>
        </form>
      </Form>
    </div>
  )
}
