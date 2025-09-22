/**
 * MetaCatalogSetup - Feed URL First approach for Meta Catalog integration
 * Shows feed URL immediately, then collects only catalog_id
 */

import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useAuth } from '@/hooks/useAuth'
import { useToast } from '@/hooks/use-toast'
import { API_BASE } from '@/lib/api-config'
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
  FormDescription,
} from '@/components/ui/form'
import { Input } from '@/components/ui/Input'
import { Button } from '@/components/ui/Button'
import { Alert, AlertDescription } from '@/components/ui/Alert'
import { Loader2, ExternalLink, Copy, CheckCircle } from 'lucide-react'

const metaCatalogSchema = z.object({
  catalog_id: z.string().min(1, "Catalog ID is required"),
})

type MetaCatalogFormData = z.infer<typeof metaCatalogSchema>

interface MetaCatalogSetupProps {
  onComplete?: () => void
  onCancel?: () => void
}

// Feed URL Display Component
function FeedUrlDisplay() {
  const { merchant, isLoadingMerchant, merchantLoadAttempted } = useAuth()
  const { toast } = useToast()
  const [copied, setCopied] = useState(false)

  // Show loading state while merchant data is being fetched
  if (isLoadingMerchant || !merchantLoadAttempted) {
    return (
      <div className="p-4 bg-gray-50 rounded-lg border border-gray-200">
        <h3 className="font-semibold text-gray-700 mb-2">Loading Feed URL...</h3>
        <div className="bg-white p-3 rounded border">
          <div className="animate-pulse bg-gray-200 h-4 rounded"></div>
        </div>
        <p className="text-sm text-gray-600 mt-2">
          Getting your business information...
        </p>
      </div>
    )
  }

  // Generate feed URL from merchant data
  const feedUrl = merchant?.slug
    ? `${API_BASE}/api/v1/meta/feeds/${merchant.slug}/products.csv`
    : `${API_BASE}/api/v1/meta/feeds/[your-business-slug]/products.csv`

  const handleCopyUrl = async () => {
    try {
      await navigator.clipboard.writeText(feedUrl)
      setCopied(true)
      toast({
        title: "URL copied! 📋",
        description: "Feed URL copied to clipboard",
      })
      setTimeout(() => setCopied(false), 2000)
    } catch (error) {
      toast({
        title: "Copy failed",
        description: "Please copy the URL manually",
        variant: "destructive",
      })
    }
  }

  const handleTestFeed = () => {
    window.open(feedUrl, '_blank')
  }

  // Debug: This should rarely happen if slug is always generated at signup
  if (!merchant?.slug || merchant.slug.length === 0) {
    return (
      <div className="p-4 bg-red-50 rounded-lg border border-red-200">
        <h3 className="font-semibold text-red-900 mb-2">⚠️ Missing Business Slug</h3>
        <p className="text-sm text-red-800 mb-3">
          Your business slug is missing from your profile. This should not happen normally.
        </p>
        <div className="bg-white p-3 rounded border font-mono text-sm break-all text-gray-400">
          {feedUrl}
        </div>
        <p className="text-xs text-red-700 mt-2">
          Debug info: merchant.name="{merchant?.name}", merchant.slug="{merchant?.slug}"
        </p>
        <p className="text-xs text-red-700">
          Please contact support if this issue persists.
        </p>
      </div>
    )
  }

  return (
    <div className="p-4 bg-blue-50 rounded-lg border border-blue-200">
      <h3 className="font-semibold text-blue-900 mb-2">Your Product Feed URL</h3>
      <div className="bg-white p-3 rounded border font-mono text-sm break-all">
        {feedUrl}
      </div>
      <div className="flex gap-2 mt-3">
        <Button variant="outline" size="sm" onClick={handleCopyUrl}>
          {copied ? (
            <>
              <CheckCircle className="w-4 h-4 mr-2 text-green-600" />
              Copied!
            </>
          ) : (
            <>
              <Copy className="w-4 h-4 mr-2" />
              Copy URL
            </>
          )}
        </Button>
        <Button variant="outline" size="sm" onClick={handleTestFeed}>
          <ExternalLink className="w-4 h-4 mr-2" />
          Test Feed
        </Button>
      </div>
      <p className="text-sm text-blue-700 mt-2">
        ✅ This URL is ready to use in Meta Commerce Manager
      </p>
    </div>
  )
}

// Setup Instructions Component
function SetupInstructions() {
  return (
    <Alert>
      <AlertDescription>
        <strong>Don't have a catalog yet?</strong>
        <ol className="mt-2 space-y-1 text-sm list-decimal list-inside">
          <li>Copy the feed URL above</li>
          <li>
            <a
              href="https://www.facebook.com/commerce_manager/catalogs"
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-600 underline hover:text-blue-800"
            >
              Create a catalog in Meta Commerce Manager
            </a>
          </li>
          <li>When prompted for "Data Feed URL", paste your feed URL</li>
          <li>Return here and enter your Catalog ID below</li>
        </ol>
      </AlertDescription>
    </Alert>
  )
}

export function MetaCatalogSetup({ onComplete, onCancel }: MetaCatalogSetupProps) {
  const { toast } = useToast()
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isVerifying, setIsVerifying] = useState(false)

  const form = useForm<MetaCatalogFormData>({
    resolver: zodResolver(metaCatalogSchema),
    defaultValues: {
      catalog_id: '',
    },
  })

  const onSubmit = async (_data: MetaCatalogFormData) => {
    setIsSubmitting(true)
    try {
      // TODO: Implement Meta catalog credentials API call
      // await metaApi.saveCatalogId(data.catalog_id)

      // Simulate API call for now
      await new Promise(resolve => setTimeout(resolve, 1000))

      toast({
        title: "Meta Catalog connected! 🎉",
        description: "Your catalog is now synced with Meta for WhatsApp commerce.",
      })

      onComplete?.()
    } catch (error) {
      console.error('Error saving catalog ID:', error)
      toast({
        title: "Connection failed",
        description: "Please check your catalog ID and try again.",
        variant: "destructive",
      })
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleVerify = async () => {
    const catalogId = form.getValues('catalog_id')
    if (!catalogId) {
      toast({
        title: "Catalog ID required",
        description: "Please enter your catalog ID first.",
        variant: "destructive",
      })
      return
    }

    setIsVerifying(true)
    try {
      // TODO: Implement verification API call
      // await metaApi.verifyCatalog(catalogId)

      // Simulate API call for now
      await new Promise(resolve => setTimeout(resolve, 2000))

      toast({
        title: "Verification successful! ✅",
        description: "Your catalog connection is working.",
      })
    } catch (error) {
      toast({
        title: "Verification failed",
        description: "Please check your catalog ID.",
        variant: "destructive",
      })
    } finally {
      setIsVerifying(false)
    }
  }

  return (
    <div className="space-y-6">
      {/* Step 1: Show Feed URL Immediately */}
      <FeedUrlDisplay />

      {/* Step 2: Setup Instructions */}
      <SetupInstructions />

      {/* Step 3: Catalog ID Collection */}
      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
          <FormField
            control={form.control}
            name="catalog_id"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Catalog ID *</FormLabel>
                <FormControl>
                  <Input
                    placeholder="Enter your Catalog ID from Meta Commerce Manager"
                    className="h-12"
                    {...field}
                  />
                </FormControl>
                <FormDescription>
                  Find this in Commerce Manager after creating your catalog using the feed URL above
                </FormDescription>
                <FormMessage />
              </FormItem>
            )}
          />

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
                  'Save & Connect'
                )}
              </Button>
            </div>
          </div>
        </form>
      </Form>
    </div>
  )
}
