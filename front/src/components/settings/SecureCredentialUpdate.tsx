/**
 * SecureCredentialUpdate - Secure credential update forms
 * Never pre-populates existing credentials, always clears after success
 */

import { useState, useEffect } from 'react'
import { z } from 'zod'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { useToast } from '@/hooks/use-toast'
import { useSecureForm } from '@/hooks/useSecureForm'
import { useAuth } from '@/hooks/useAuth'
import { PaymentProvider } from '@/types/settings'
import { settingsApi } from '@/lib/settings-api'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/Select'
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from '@/components/ui/command'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import { Shield, Loader2, Key, AlertTriangle, Building2, CheckCircle, ChevronsUpDown, Check } from 'lucide-react'
import { cn } from '@/lib/utils'
import { apiUrl, getAuthHeaders } from '@/lib/api-config'

interface Bank {
  id: number;
  name: string;
  code: string;
  slug: string;
  country: string;
  currency: string;
  type: string;
  active: boolean;
}

interface AccountResolution {
  account_number: string;
  account_name: string;
}

// Payment credential schema
const paymentCredentialSchema = z.object({
  environment: z.enum(['test', 'live']),
})

type PaymentCredentialFormData = z.infer<typeof paymentCredentialSchema>

// Paystack subaccount schema (new Paystack-first approach)
const paystackSubaccountSchema = z.object({
  business_name: z.string().min(1, 'Business name is required'),
  bank_code: z.string().min(1, 'Bank code is required'),
  account_number: z.string().regex(/^\d{10}$/, 'Account number must be exactly 10 digits'),
  // Admin-controlled defaults: 2% commission, AUTO settlement
  percentage_charge: z.number().default(2.0),
  settlement_schedule: z.enum(['AUTO', 'WEEKLY', 'MONTHLY', 'MANUAL']).default('AUTO'),
})

type PaystackSubaccountFormData = z.infer<typeof paystackSubaccountSchema>

// WhatsApp credential schema
const whatsappCredentialSchema = z.object({
  waba_id: z.string().min(1, 'WhatsApp Business Account ID is required'),
  phone_number_id: z.string().min(1, 'Phone Number ID is required'),
  app_id: z.string().min(1, 'App ID is required'),
  system_user_token: z.string().min(1, 'System User Token is required'),
})

type WhatsAppCredentialFormData = z.infer<typeof whatsappCredentialSchema>

// Meta Catalog credential schema


/**
 * Payment credential update form
 */
interface PaymentCredentialUpdateProps {
  provider: PaymentProvider
  onSuccess: () => void
  trigger?: React.ReactNode
}

export function PaymentCredentialUpdate({
  provider,
  onSuccess,
  trigger,
}: PaymentCredentialUpdateProps) {
  const [open, setOpen] = useState(false)
  const { toast } = useToast()

  const { form, secureSubmit, clearForm } = useSecureForm(
    paymentCredentialSchema,
    {
      provider,
      onSuccess: () => {
        setOpen(false)
        onSuccess()
      },
    }
  )

  const onSubmit = async (data: PaymentCredentialFormData) => {
    // This would call your actual API
    console.log(`Updating ${provider} credentials`, {
      ...data,
    })

    // Mock API call
    await new Promise(resolve => setTimeout(resolve, 2000))

    toast({
      title: 'Credentials updated',
      description: `${provider} credentials have been updated and verified successfully.`,
    })
  }

  const handleCancel = () => {
    clearForm()
    setOpen(false)
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        {trigger || (
          <Button variant="outline" size="sm">
            <Key className="w-4 h-4 mr-2" />
            Update Credentials
          </Button>
        )}
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Shield className="w-5 h-5" />
            Update {provider} Credentials
          </DialogTitle>
          <DialogDescription>
            Enter your new {provider} credentials. Existing credentials will be replaced.
          </DialogDescription>
        </DialogHeader>

        <Alert>
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>
            This action will replace your current {provider} configuration.
            Your credentials are encrypted and never displayed in the browser.
          </AlertDescription>
        </Alert>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(data => secureSubmit(() => onSubmit(data)))}>
            <div className="space-y-4">
              <FormField
                control={form.control}
                name="environment"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Environment</FormLabel>
                    <Select onValueChange={field.onChange} value={field.value}>
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue placeholder="Select environment" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        <SelectItem value="test">Test Environment</SelectItem>
                        <SelectItem value="live">Live Environment</SelectItem>
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )}
              />


              <div className="flex justify-end gap-2 pt-4">
                <Button
                  type="button"
                  variant="outline"
                  onClick={handleCancel}
                  disabled={form.formState.isSubmitting}
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  disabled={form.formState.isSubmitting}
                >
                  {form.formState.isSubmitting ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Updating...
                    </>
                  ) : (
                    'Update Credentials'
                  )}
                </Button>
              </div>
            </div>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  )
}

/**
 * WhatsApp credential update form (system tokens never displayed)
 */
interface WhatsAppCredentialUpdateProps {
  onSuccess: () => void
  trigger?: React.ReactNode
}

export function WhatsAppCredentialUpdate({
  onSuccess,
  trigger,
}: WhatsAppCredentialUpdateProps) {
  const [open, setOpen] = useState(false)
  const { toast } = useToast()

  const { form, secureSubmit, clearForm } = useSecureForm(
    whatsappCredentialSchema,
    {
      provider: 'whatsapp',
      onSuccess: () => {
        setOpen(false)
        onSuccess()
      },
    }
  )

  const onSubmit = async (data: WhatsAppCredentialFormData) => {
    // This would call your actual API
    console.log('Updating WhatsApp credentials', {
      ...data,
      system_user_token: '[MASKED]',
    })

    // Mock API call
    await new Promise(resolve => setTimeout(resolve, 2000))

    toast({
      title: 'WhatsApp credentials updated',
      description: 'WhatsApp configuration has been updated successfully.',
    })
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        {trigger || (
          <Button variant="outline" size="sm">
            Update Configuration
          </Button>
        )}
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Update WhatsApp Configuration</DialogTitle>
          <DialogDescription>
            Update your WhatsApp Business API configuration.
          </DialogDescription>
        </DialogHeader>

        <Alert>
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>
            System user tokens are never displayed or stored in the browser.
            This configuration will replace your existing WhatsApp setup.
          </AlertDescription>
        </Alert>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(data => secureSubmit(() => onSubmit(data)))}>
            <div className="space-y-4">
              <FormField
                control={form.control}
                name="waba_id"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>WhatsApp Business Account ID</FormLabel>
                    <FormControl>
                      <Input {...field} placeholder="Enter WABA ID" className="h-12" />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="phone_number_id"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Phone Number ID</FormLabel>
                    <FormControl>
                      <Input {...field} placeholder="Enter Phone Number ID" className="h-12" />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="app_id"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>App ID</FormLabel>
                    <FormControl>
                      <Input {...field} placeholder="Enter App ID" className="h-12" />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="system_user_token"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>System User Access Token</FormLabel>
                    <FormControl>
                      <Input
                        {...field}
                        type="password"
                        placeholder="Enter system user token"
                        autoComplete="off"
                        className="h-12"
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <div className="flex justify-end gap-2 pt-4">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => {
                    clearForm()
                    setOpen(false)
                  }}
                  disabled={form.formState.isSubmitting}
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  disabled={form.formState.isSubmitting}
                >
                  {form.formState.isSubmitting ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Updating...
                    </>
                  ) : (
                    'Update Configuration'
                  )}
                </Button>
              </div>
            </div>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  )
}

/**
 * Token rotation form for WhatsApp (admin only)
 */
interface TokenRotationProps {
  onSuccess: () => void
  trigger?: React.ReactNode
}

export function TokenRotation({ onSuccess, trigger }: TokenRotationProps) {
  const [open, setOpen] = useState(false)
  const [token, setToken] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const { toast } = useToast()

  const handleRotate = async () => {
    if (!token.trim()) {
      toast({
        title: 'Token required',
        description: 'Please enter a new system user token.',
        variant: 'destructive',
      })
      return
    }

    setIsLoading(true)
    try {
      // Mock API call for token rotation
      await new Promise(resolve => setTimeout(resolve, 2000))

      // Clear token immediately
      setToken('')
      setOpen(false)
      onSuccess()

      toast({
        title: 'Token rotated successfully',
        description: 'Your WhatsApp access token has been rotated and is now active.',
      })
    } catch (error) {
      toast({
        title: 'Token rotation failed',
        description: 'Failed to rotate token. Please try again.',
        variant: 'destructive',
      })
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        {trigger || (
          <Button variant="outline" size="sm">
            Rotate Token
          </Button>
        )}
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Rotate WhatsApp Token</DialogTitle>
          <DialogDescription>
            Replace your current system user token with a new one.
          </DialogDescription>
        </DialogHeader>

        <Alert>
          <Shield className="h-4 w-4" />
          <AlertDescription>
            Token rotation will immediately replace your current access token.
            Ensure the new token has proper permissions.
          </AlertDescription>
        </Alert>

        <div className="space-y-4">
          <div>
            <label className="text-sm font-medium">New System User Token</label>
            <Input
              type="password"
              value={token}
              onChange={(e) => setToken(e.target.value)}
              placeholder="Enter new system user token"
              className="mt-1 h-12"
              autoComplete="off"
            />
          </div>

          <div className="flex justify-end gap-2">
            <Button
              variant="outline"
              onClick={() => {
                setToken('')
                setOpen(false)
              }}
              disabled={isLoading}
            >
              Cancel
            </Button>
            <Button onClick={handleRotate} disabled={isLoading}>
              {isLoading ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Rotating...
                </>
              ) : (
                'Rotate Token'
              )}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}

/**
 * Paystack subaccount update form (new Paystack-first approach)
 */
interface PaystackSubaccountUpdateProps {
  onSuccess: () => void
  trigger?: React.ReactNode
}

export function PaystackSubaccountUpdate({
  onSuccess,
  trigger,
}: PaystackSubaccountUpdateProps) {
  const [open, setOpen] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isLoadingBanks, setIsLoadingBanks] = useState(false)
  const [isResolvingAccount, setIsResolvingAccount] = useState(false)
  const [banks, setBanks] = useState<Bank[]>([])
  const [accountResolution, setAccountResolution] = useState<AccountResolution | null>(null)
  const [selectedBank, setSelectedBank] = useState<Bank | null>(null)
  const [bankComboOpen, setBankComboOpen] = useState(false)
  const { toast } = useToast()
  const { merchant } = useAuth()

  const form = useForm<PaystackSubaccountFormData>({
    resolver: zodResolver(paystackSubaccountSchema),
    defaultValues: {
      business_name: merchant?.name || '',
      bank_code: '',
      account_number: '',
      percentage_charge: 2.0,
      settlement_schedule: 'AUTO',
    },
    mode: 'onSubmit',
  })

  const watchedAccountNumber = form.watch('account_number')
  const watchedBankCode = form.watch('bank_code')

  // Load banks on component mount and set business name
  useEffect(() => {
    if (open) {
      loadBanks()
      // Update business_name when merchant data is available
      if (merchant?.name) {
        form.setValue('business_name', merchant.name)
      }
    }
  }, [open, merchant])

  // Auto-resolve account when 10 digits entered
  useEffect(() => {
    if (watchedAccountNumber?.length === 10 && watchedBankCode && selectedBank) {
      resolveAccount(watchedAccountNumber, watchedBankCode)
    } else {
      setAccountResolution(null)
    }
  }, [watchedAccountNumber, watchedBankCode, selectedBank])

  const loadBanks = async () => {
    setIsLoadingBanks(true)
    try {
      const response = await fetch(apiUrl('api/v1/payments/banks'), {
        headers: {
          ...getAuthHeaders(),
          'Content-Type': 'application/json',
        },
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }

      const result = await response.json()
      if (result.ok && result.data) {
        setBanks(result.data.banks || [])
      } else {
        throw new Error(result.message || 'Failed to load banks')
      }
    } catch (error) {
      console.error('Error loading banks:', error)
      toast({
        title: "Failed to load banks",
        description: "Please refresh the page to try again.",
        variant: "destructive",
      })
    } finally {
      setIsLoadingBanks(false)
    }
  }

  const resolveAccount = async (accountNumber: string, bankCode: string) => {
    setIsResolvingAccount(true)
    try {
      const response = await fetch(
        apiUrl(`api/v1/payments/resolve-account?account_number=${accountNumber}&bank_code=${bankCode}`),
        {
          headers: {
            ...getAuthHeaders(),
            'Content-Type': 'application/json',
          },
        }
      )

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }

      const result = await response.json()

      if (result.ok && result.data?.success) {
        setAccountResolution({
          account_number: result.data.data.account_number,
          account_name: result.data.data.account_name
        })
      } else {
        setAccountResolution(null)
        const errorMsg = result.data?.error_message || result.message || 'Could not verify this account number'
        toast({
          title: "Account verification failed",
          description: errorMsg,
          variant: "destructive",
        })
      }
    } catch (error) {
      console.error('Error resolving account:', error)
      setAccountResolution(null)
      toast({
        title: "Account verification failed",
        description: "Network error. Please try again.",
        variant: "destructive",
      })
    } finally {
      setIsResolvingAccount(false)
    }
  }

  const handleBankSelect = (bankCode: string) => {
    const bank = banks.find(b => b.code === bankCode)
    setSelectedBank(bank || null)
    form.setValue('bank_code', bankCode)
    setBankComboOpen(false)
    // Reset account resolution when bank changes
    setAccountResolution(null)
  }

  const onSubmit = async (data: PaystackSubaccountFormData) => {
    // Ensure account is verified before submitting
    if (!accountResolution) {
      toast({
        title: "Account verification required",
        description: "Please wait for account verification to complete before saving.",
        variant: "destructive",
      })
      return
    }

    setIsSubmitting(true)
    try {
      // Ensure business_name is included from merchant data
      const submitData = {
        ...data,
        business_name: merchant?.name || data.business_name,
        percentage_charge: 2.0,
        settlement_schedule: 'AUTO' as const,
      }

      const result = await settingsApi.updatePaystackSubaccount(submitData)

      if (result.success) {
        toast({
          title: 'Subaccount updated',
          description: result.message,
        })
        setOpen(false)
        form.reset()
        onSuccess()
      } else if (result.partialSuccess) {
        toast({
          title: 'Partial success',
          description: result.message,
          variant: 'default',
        })
        setOpen(false)
        form.reset()
        onSuccess()
      } else {
        toast({
          title: 'Update failed',
          description: result.message,
          variant: 'destructive',
        })
      }
    } catch (error) {
      toast({
        title: 'Update failed',
        description: error instanceof Error ? error.message : 'An unexpected error occurred',
        variant: 'destructive',
      })
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleCancel = () => {
    form.reset()
    setOpen(false)
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        {trigger || (
          <Button variant="outline" size="sm">
            <Key className="w-4 h-4 mr-2" />
            Update Subaccount
          </Button>
        )}
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Shield className="w-5 h-5" />
            Update Paystack Subaccount
          </DialogTitle>
        </DialogHeader>

        <Alert>
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>
            This will update your Paystack subaccount configuration directly.
            All changes are synced with Paystack in real-time.
          </AlertDescription>
        </Alert>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)}>
            <div className="space-y-4">
              {/* Business Name Display */}
              <div className="space-y-2">
                <FormLabel>Business Name</FormLabel>
                <div className="flex items-center gap-3 p-3 bg-muted/30 rounded-md border">
                  <Building2 className="w-4 h-4 text-muted-foreground" />
                  <span className="font-medium">{merchant?.name || 'Loading...'}</span>
                </div>
                <p className="text-xs text-muted-foreground">This will be used for your Paystack subaccount</p>
              </div>

              {/* Bank Selection */}
              <FormField
                control={form.control}
                name="bank_code"
                render={({ field }) => (
                  <FormItem className="flex flex-col">
                    <FormLabel>Bank *</FormLabel>
                    <Popover open={bankComboOpen} onOpenChange={setBankComboOpen}>
                      <PopoverTrigger asChild>
                        <FormControl>
                          <Button
                            variant="outline"
                            role="combobox"
                            aria-expanded={bankComboOpen}
                            className={cn(
                              "w-full justify-between h-12",
                              !field.value && "text-muted-foreground"
                            )}
                            disabled={isLoadingBanks}
                          >
                            {isLoadingBanks ? (
                              <>
                                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                Loading banks...
                              </>
                            ) : field.value ? (
                              selectedBank?.name || "Select your bank"
                            ) : (
                              "Select your bank"
                            )}
                            <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                          </Button>
                        </FormControl>
                      </PopoverTrigger>
                      <PopoverContent className="w-[--radix-popover-trigger-width] p-0" align="start">
                        <Command>
                          <CommandInput placeholder="Search banks..." className="h-9" />
                          <CommandList>
                            <CommandEmpty>No bank found.</CommandEmpty>
                            <CommandGroup>
                              {banks
                                .filter((bank, index, self) =>
                                  index === self.findIndex(b => b.code === bank.code)
                                )
                                .map((bank) => (
                                  <CommandItem
                                    key={bank.code}
                                    value={bank.name}
                                    onSelect={() => handleBankSelect(bank.code)}
                                  >
                                    {bank.name}
                                    <Check
                                      className={cn(
                                        "ml-auto h-4 w-4",
                                        field.value === bank.code ? "opacity-100" : "opacity-0"
                                      )}
                                    />
                                  </CommandItem>
                                ))}
                            </CommandGroup>
                          </CommandList>
                        </Command>
                      </PopoverContent>
                    </Popover>
                    <FormMessage />
                  </FormItem>
                )}
              />

              {/* Account Number */}
              <FormField
                control={form.control}
                name="account_number"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Account Number *</FormLabel>
                    <FormControl>
                      <Input
                        placeholder="Enter your 10-digit account number"
                        className="h-12"
                        maxLength={10}
                        {...field}
                        onChange={(e) => {
                          const value = e.target.value.replace(/\D/g, '').slice(0, 10)
                          field.onChange(value)
                        }}
                      />
                    </FormControl>
                    {watchedAccountNumber && (
                      <p className="text-xs text-muted-foreground">
                        {watchedAccountNumber.length}/10 digits
                        {watchedAccountNumber.length === 10 && selectedBank && (
                          <span className="ml-2 text-green-600">✓</span>
                        )}
                      </p>
                    )}
                    <FormMessage />
                  </FormItem>
                )}
              />

              {/* Account Resolution Display */}
              {watchedAccountNumber?.length === 10 && selectedBank && (
                <div className="space-y-2">
                  <FormLabel>Account Verification</FormLabel>
                  {isResolvingAccount ? (
                    <div className="flex items-center gap-3 p-3 bg-blue-50 rounded-md border border-blue-200">
                      <Loader2 className="w-4 h-4 animate-spin text-blue-600" />
                      <span className="text-blue-700">Verifying account details...</span>
                    </div>
                  ) : accountResolution ? (
                    <div className="flex items-center gap-3 p-3 bg-green-50 rounded-md border border-green-200">
                      <CheckCircle className="w-4 h-4 text-green-600" />
                      <div>
                        <p className="font-medium text-green-800">{accountResolution.account_name}</p>
                        <p className="text-xs text-green-600">{selectedBank.name} • {accountResolution.account_number}</p>
                      </div>
                    </div>
                  ) : (
                    <div className="flex items-center gap-3 p-3 bg-red-50 rounded-md border border-red-200">
                      <div className="w-4 h-4 rounded-full bg-red-500" />
                      <span className="text-red-700">Could not verify account details</span>
                    </div>
                  )}
                </div>
              )}


              <div className="flex justify-end gap-2 pt-4">
                <Button
                  type="button"
                  variant="outline"
                  onClick={handleCancel}
                  disabled={isSubmitting}
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  disabled={isSubmitting}
                >
                  {isSubmitting ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Updating...
                    </>
                  ) : (
                    'Update Subaccount'
                  )}
                </Button>
              </div>
            </div>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  )
}