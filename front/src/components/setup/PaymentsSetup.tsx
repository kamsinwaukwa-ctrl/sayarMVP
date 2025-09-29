/**
 * PaymentsSetup - Component for payment provider configuration
 * Allows merchants to connect Paystack for payment processing with subaccount creation
 */

import { useState, useEffect } from 'react'
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
import { Loader2, CreditCard, CheckCircle, Building2, Check, ChevronsUpDown } from 'lucide-react'
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

const paymentProviderSchema = z.object({
  bank_code: z.string().min(1, "Please select a bank"),
  account_number: z.string().length(10, "Account number must be exactly 10 digits").regex(/^\d{10}$/, "Account number must contain only digits"),
})

type PaymentProviderFormData = z.infer<typeof paymentProviderSchema>

interface PaymentsSetupProps {
  onComplete?: () => void
  onCancel?: () => void
}

export function PaymentsSetup({ onComplete, onCancel }: PaymentsSetupProps) {
  const { toast } = useToast()
  const { refreshOnboardingProgress, merchant } = useAuth()
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isLoadingBanks, setIsLoadingBanks] = useState(false)
  const [isResolvingAccount, setIsResolvingAccount] = useState(false)
  const [banks, setBanks] = useState<Bank[]>([])
  const [accountResolution, setAccountResolution] = useState<AccountResolution | null>(null)
  const [selectedBank, setSelectedBank] = useState<Bank | null>(null)
  const [bankComboOpen, setBankComboOpen] = useState(false)

  const form = useForm<PaymentProviderFormData>({
    resolver: zodResolver(paymentProviderSchema),
    defaultValues: {
      bank_code: '',
      account_number: '',
    },
    mode: 'onBlur',
  })

  const watchedAccountNumber = form.watch('account_number')
  const watchedBankCode = form.watch('bank_code')

  // Load banks on component mount
  useEffect(() => {
    loadBanks()
  }, [])

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

  const onSubmit = async (data: PaymentProviderFormData) => {
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
      const subaccountData = {
        business_name: merchant?.name || 'Business Name',
        bank_code: data.bank_code,
        account_number: data.account_number,
        percentage_charge: 2.0,
        settlement_schedule: 'AUTO',
      }

      const response = await fetch(apiUrl('api/v1/payments/create-subaccount'), {
        method: 'POST',
        headers: {
          ...getAuthHeaders(),
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(subaccountData)
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }

      const result = await response.json()

      if (result.ok && result.data?.success) {
        toast({
          title: "Payment provider connected! 💳",
          description: "Successfully connected Paystack for payment processing.",
        })

        // Refresh onboarding progress
        try {
          await refreshOnboardingProgress()
        } catch (error) {
          console.warn('Failed to refresh onboarding progress:', error)
        }

        onComplete?.()
      } else {
        const errorMsg = result.data?.error_message || result.message || "Failed to create payment account"
        toast({
          title: "Connection failed",
          description: errorMsg,
          variant: "destructive",
        })
      }
    } catch (error: any) {
      console.error('Error creating subaccount:', error)
      const errorMessage = error?.response?.data?.detail || error?.message || "Failed to create payment account. Please try again."
      toast({
        title: "Connection failed",
        description: errorMessage,
        variant: "destructive",
      })
    } finally {
      setIsSubmitting(false)
    }
  }

  const isFormValid = () => {
    const formData = form.getValues()
    return formData.bank_code &&
           formData.account_number?.length === 10 &&
           accountResolution !== null
  }

  const handleBankSelect = (bankCode: string) => {
    const bank = banks.find(b => b.code === bankCode)
    setSelectedBank(bank || null)
    form.setValue('bank_code', bankCode)
    setBankComboOpen(false)
    // Reset account resolution when bank changes
    setAccountResolution(null)
  }

  return (
    <div className="space-y-6">
    

      {/* Paystack Info */}
      <div className="p-4 rounded-lg border bg-green-50 border-green-200 text-green-800">
            <h4 className="font-medium mb-2">Paystack</h4>
            <p className="text-sm mb-3"> Connect Paystack to start accepting payments from customers. You'll need to provide your bank details to receive payments.
            </p>
            <div className="flex flex-wrap gap-2">
              {['Card payments', 'Bank transfers', 'USSD', 'Mobile money'].map((feature, index) => (
                <span key={index} className="text-xs px-2 py-1 bg-white/50 rounded">
                  {feature}
                </span>
              ))}
            </div>
          </div>


      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
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

          {/* Commission Info */}
          <div className="space-y-2">
            <FormLabel>Commission</FormLabel>
            <div className="flex items-center gap-3 p-3 bg-muted/30 rounded-md border">
              <CreditCard className="w-4 h-4 text-muted-foreground" />
              <span className="font-medium">2% per transaction</span>
            </div>
            <p className="text-xs text-muted-foreground">Fixed commission rate for all transactions</p>
          </div>

          {/* Security Note */}
          <Alert>
            <CheckCircle className="h-4 w-4" />
            <AlertDescription>
              Your bank details are securely stored and used only for payment processing through Paystack.
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
                  disabled={isSubmitting}
                >
                  Cancel
                </Button>
              )}
            </div>

            <div className="flex gap-3">
              <Button
                type="submit"
                disabled={isSubmitting || !isFormValid()}
                className="min-w-[140px]"
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Creating Account...
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
