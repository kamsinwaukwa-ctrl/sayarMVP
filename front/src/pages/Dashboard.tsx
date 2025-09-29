/**
 * Dashboard Page for Sayar WhatsApp Commerce Platform
 * Beautiful, modern merchant dashboard with clean design
 */

import { useEffect, useState } from 'react'
import { Typography } from '@/components/ui/Typography'
import { Button } from '@/components/ui/Button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Alert } from '@/components/ui/Alert'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { Badge } from '@/components/ui/badge'
import { koboToNairaDisplay } from '@/lib/format'
import {
  Store,
  ShoppingCart,
  BarChart4,
  MessageCircle,
  User,
  Building2,
  Package,
  Truck,
  CreditCard,
  Link2,
  Clock,
  ArrowRight,
  TrendingUp,
  Users,
  DollarSign,
} from 'lucide-react'
import { useAuth } from '@/hooks/useAuth'
import { apiClient } from '@/lib/api-client'
import { clearSensitiveOnboardingData } from '@/lib/onboarding'
import {
  SetupCard,
  BrandBasicsSetup,
  MetaCatalogSetup,
  WhatsAppIntegrationSetup,
  DeliveryRatesSetup,
  PaymentsSetup
} from '@/components/setup'
import { useToast } from '@/hooks/use-toast'
import { MerchantSummary } from '@/types/merchant'

const Dashboard = () => {
  const {
    user,
    merchant,
    onboardingProgress,
    loading: authLoading,
    isLoadingOnboarding,
    refreshOnboardingProgress,
  } = useAuth()
  const { toast } = useToast()
  const [merchantInfo, setMerchantInfo] = useState<MerchantSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (user && !authLoading) {
      loadMerchantInfo()
    }
  }, [user, authLoading])

  const loadMerchantInfo = async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await apiClient.getCurrentMerchant()
      setMerchantInfo(response)
    } catch (error) {
      console.error('Failed to load merchant info:', error)
      setError('Failed to load merchant information')
    } finally {
      setLoading(false)
    }
  }

  // Sign out controlled in AppHeader

  const getRoleDisplayName = (role: string) => {
    return role === 'admin' ? 'Owner' : 'Staff'
  }

  const getSetupProgress = () => {
    if (!onboardingProgress) return 0
    const completed = Object.values(onboardingProgress).filter(Boolean).length
    const total = Object.keys(onboardingProgress).length
    return Math.round((completed / total) * 100)
  }

  const isSetupComplete = onboardingProgress && Object.values(onboardingProgress).every(Boolean)

  // Clear sensitive data when onboarding completes
  useEffect(() => {
    if (isSetupComplete && !authLoading && !loading) {
      // Only clear sensitive data once per session to avoid repeated cleanup
      const hasCleared = sessionStorage.getItem('sensitive_data_cleared')
      if (!hasCleared) {
        clearSensitiveOnboardingData()
        sessionStorage.setItem('sensitive_data_cleared', 'true')
      }
    }
  }, [isSetupComplete, authLoading, loading])

  if (authLoading || loading) {
    return (
      <div className="flex justify-center items-center min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
        <div className="text-center">
        <LoadingSpinner size="lg" />
          <Typography variant="body1" className="mt-4 text-muted-foreground">
            Loading your dashboard...
          </Typography>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-slate-100">
      <div className="px-4 sm:px-6 lg:px-8 py-8 max-w-7xl mx-auto w-full">
        {error && (
          <Alert variant="destructive" className="mb-8">
            {error}
          </Alert>
        )}

        {/* Welcome Hero Section */}
        <div className="mb-12">
          <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-blue-600 via-purple-600 to-indigo-700 p-8 text-white">
            <div className="absolute inset-0 bg-black/10" />
            <div className="relative">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center space-x-3 mb-4">
                    <div className="w-12 h-12 bg-white/20 rounded-xl flex items-center justify-center">
                      <Building2 className="w-7 h-7" />
                    </div>
                    <div>
                      <Typography variant="h3" className="text-white font-bold">
                        Welcome back, {user?.name?.split(' ')[0]}! 👋
                      </Typography>
                      <Typography variant="body1" className="text-white">
                        {merchant?.name || merchantInfo?.name || 'Your Business'}
                      </Typography>
                    </div>
                  </div>

                  <Typography variant="body1" className="text-white mb-6 max-w-2xl">
                    {isSetupComplete
                      ? "Your WhatsApp commerce store is fully set up and ready to go! Start selling and growing your business."
                      : "Complete your store setup to unlock all features and start selling on WhatsApp."}
                  </Typography>

                  <div className="flex flex-wrap gap-3">
                    {merchantInfo?.whatsapp_phone_e164 && (
                      <Badge className="bg-white/20 text-white border-white/30 hover:bg-white/30">
                        <MessageCircle className="w-4 h-4 mr-2" />
                        WhatsApp: {merchantInfo.whatsapp_phone_e164}
                      </Badge>
                    )}
                    <Badge className="bg-white/20 text-white border-white/30 hover:bg-white/30">
                      <DollarSign className="w-4 h-4 mr-2" />
                      {merchant?.currency || merchantInfo?.currency || 'NGN'}
                    </Badge>
                    <Badge className="bg-white/20 text-white border-white/30 hover:bg-white/30">
                      <Users className="w-4 h-4 mr-2" />
                      {getRoleDisplayName(user?.role || 'staff')}
                    </Badge>
                  </div>
                </div>

                {/* Setup Progress */}
                {!isSetupComplete && onboardingProgress && (
                  <div className="text-right">
                    <div className="bg-white/20 rounded-xl p-4 backdrop-blur-sm">
                      <Typography variant="body2" className="text-white mb-2">
                        Setup Progress
                      </Typography>
                      <div className="flex items-center space-x-2 mb-2">
                        <div className="w-24 h-2 bg-white/30 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-white rounded-full transition-all duration-500"
                            style={{ width: `${getSetupProgress()}%` }}
                          />
                        </div>
                        <Typography variant="caption" className="text-white font-medium">
                          {getSetupProgress()}%
                        </Typography>
                      </div>
                      <Typography variant="caption" className="text-white">
                        {Object.values(onboardingProgress).filter(Boolean).length} of {Object.keys(onboardingProgress).length} steps complete
                      </Typography>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

          {/* Setup Cards Section */}
        {!isSetupComplete && onboardingProgress && !isLoadingOnboarding && (
          <div className="mb-12">
            <div className="flex items-center justify-between mb-8">
              <div>
                <Typography variant="h4" className="font-bold text-slate-900 mb-2">
                  Complete Your Store Setup
                </Typography>
                <Typography variant="body1" className="text-slate-600">
                  Finish these steps to unlock all platform features and start selling
                </Typography>
              </div>
              <div className="flex items-center space-x-2 text-sm text-slate-500">
                <Clock className="w-4 h-4" />
                <span>~10 minutes to complete</span>
              </div>
              </div>

            <div className="grid gap-6 md:grid-cols-2">
                {/* Brand Basics Setup */}
                <SetupCard
                  title="Brand Basics"
                  description="Set up your business information, logo, and primary currency"
                  icon={<Building2 className="w-5 h-5" />}
                  completed={onboardingProgress.brand_basics}
                  onAction={() => {}}
                  actionLabel="Configure"
                  onComplete={() => {
                    // Refresh merchant info and onboarding progress to update the UI
                    loadMerchantInfo()
                    refreshOnboardingProgress()
                    toast({
                      title: "Brand basics completed! 🎉",
                      description: "Your business information has been saved successfully.",
                    })
                  }}
                >
                  {({ onComplete }) => <BrandBasicsSetup onComplete={onComplete} />}
                </SetupCard>

                {/* Meta Catalog Setup */}
                <SetupCard
                  title="Meta Catalog"
                  description="Connect your product catalog to Meta for WhatsApp commerce"
                  icon={<Link2 className="w-5 h-5" />}
                  completed={onboardingProgress.meta_catalog}
                  disabled={!onboardingProgress.brand_basics}
                  disabledReason="Complete brand basics first"
                  onAction={() => {}}
                  actionLabel="Connect"
                  onComplete={() => {
                    loadMerchantInfo()
                    refreshOnboardingProgress()
                    toast({
                      title: "Meta Catalog connected! 🔗",
                      description: "Your catalog is now synced with Meta for WhatsApp commerce.",
                    })
                  }}
                >
                  {({ onComplete }) => <MetaCatalogSetup onComplete={onComplete} />}
                </SetupCard>

                {/* WhatsApp Integration Setup */}
                <SetupCard
                  title="WhatsApp Integration"
                  description="Connect your WhatsApp Business account for customer orders"
                  icon={<MessageCircle className="w-5 h-5" />}
                  completed={onboardingProgress.whatsapp}
                  disabled={!onboardingProgress.brand_basics}
                  disabledReason="Complete brand basics first"
                  onAction={() => {}}
                  actionLabel="Connect WhatsApp"
                  onComplete={() => {
                    loadMerchantInfo()
                    refreshOnboardingProgress()
                    toast({
                      title: "WhatsApp connected! 📱",
                      description: "Your WhatsApp Business account is now ready to receive orders.",
                    })
                  }}
                >
                  {({ onComplete }) => <WhatsAppIntegrationSetup onComplete={onComplete} />}
                </SetupCard>

                {/* Delivery Rates Setup */}
                <SetupCard
                  title="Delivery Rates"
                  description="Configure shipping zones and delivery pricing"
                  icon={<Truck className="w-5 h-5" />}
                  completed={onboardingProgress.delivery_rates}
                  onAction={() => {}}
                  actionLabel="Set Rates"
                  onComplete={() => {
                    loadMerchantInfo()
                    refreshOnboardingProgress()
                    toast({
                      title: "Delivery rates configured! 🚚",
                      description: "Your delivery zones and pricing are now set up.",
                    })
                  }}
                >
                  {({ onComplete }) => <DeliveryRatesSetup onComplete={onComplete} />}
                </SetupCard>

                {/* Payment Setup */}
                <SetupCard
                  title="Payments"
                  description="Connect Paystack or Korapay for payment processing"
                  icon={<CreditCard className="w-5 h-5" />}
                  completed={onboardingProgress.payments}
                  disabled={!onboardingProgress.whatsapp}
                  disabledReason="Complete WhatsApp integration first"
                  onAction={() => {}}
                  actionLabel="Configure"
                  onComplete={() => {
                    loadMerchantInfo()
                    refreshOnboardingProgress()
                    toast({
                      title: "Payments configured! 💳",
                      description: "Your payment provider is now connected and ready to process payments.",
                    })
                  }}
                >
                  {({ onComplete }) => <PaymentsSetup onComplete={onComplete} />}
                </SetupCard>
              </div>
            </div>
          )}

        {/* Quick Stats - Show when setup is complete */}
        {isSetupComplete && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-12">
            <Card className="p-6 hover:shadow-lg transition-shadow">
              <div className="flex items-center justify-between">
                <div>
                  <Typography variant="body2" className="text-slate-600 mb-1">
                    Total Products
                  </Typography>
                  <Typography variant="h3" className="font-bold text-slate-900">
                    0
                  </Typography>
                </div>
                <div className="w-12 h-12 bg-blue-100 rounded-xl flex items-center justify-center">
                  <Package className="w-6 h-6 text-blue-600" />
                </div>
              </div>
              <div className="flex items-center mt-4 text-sm text-green-600">
                <TrendingUp className="w-4 h-4 mr-1" />
                <span>+0% from last month</span>
              </div>
            </Card>

            <Card className="p-6 hover:shadow-lg transition-shadow">
              <div className="flex items-center justify-between">
                <div>
                  <Typography variant="body2" className="text-slate-600 mb-1">
                    Orders Today
                  </Typography>
                  <Typography variant="h3" className="font-bold text-slate-900">
                    0
                  </Typography>
                </div>
                <div className="w-12 h-12 bg-green-100 rounded-xl flex items-center justify-center">
                  <ShoppingCart className="w-6 h-6 text-green-600" />
                </div>
              </div>
              <div className="flex items-center mt-4 text-sm text-green-600">
                <TrendingUp className="w-4 h-4 mr-1" />
                <span>+0% from yesterday</span>
              </div>
            </Card>

            <Card className="p-6 hover:shadow-lg transition-shadow">
              <div className="flex items-center justify-between">
                <div>
                  <Typography variant="body2" className="text-slate-600 mb-1">
                    Revenue
                  </Typography>
                  <Typography variant="h3" className="font-bold text-slate-900">
                    {koboToNairaDisplay(0)}
                  </Typography>
                </div>
                <div className="w-12 h-12 bg-purple-100 rounded-xl flex items-center justify-center">
                  <DollarSign className="w-6 h-6 text-purple-600" />
                </div>
              </div>
              <div className="flex items-center mt-4 text-sm text-green-600">
                <TrendingUp className="w-4 h-4 mr-1" />
                <span>+0% from last month</span>
        </div>
            </Card>

            <Card className="p-6 hover:shadow-lg transition-shadow">
              <div className="flex items-center justify-between">
                <div>
                  <Typography variant="body2" className="text-slate-600 mb-1">
                    Customers
                  </Typography>
                  <Typography variant="h3" className="font-bold text-slate-900">
                    0
                  </Typography>
                </div>
                <div className="w-12 h-12 bg-orange-100 rounded-xl flex items-center justify-center">
                  <Users className="w-6 h-6 text-orange-600" />
                </div>
              </div>
              <div className="flex items-center mt-4 text-sm text-green-600">
                <TrendingUp className="w-4 h-4 mr-1" />
                <span>+0% from last month</span>
              </div>
            </Card>
          </div>
        )}
          {/* Feature Cards - Show when setup is complete */}
        {isSetupComplete && (
          <div className="mb-12">
            <div className="flex items-center justify-between mb-8">
              <div>
                <Typography variant="h4" className="font-bold text-slate-900 mb-2">
                  Quick Actions
                </Typography>
                <Typography variant="body1" className="text-slate-600">
                  Manage your store and track performance
                </Typography>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              <Card className="group hover:shadow-xl transition-all duration-300 border-0 bg-gradient-to-br from-blue-50 to-blue-100">
                <CardContent className="p-8">
                  <div className="flex items-center justify-between mb-6">
                    <div className="w-14 h-14 bg-blue-600 rounded-2xl flex items-center justify-center group-hover:scale-110 transition-transform">
                      <Store className="w-8 h-8 text-white" />
                    </div>
                    <ArrowRight className="w-5 h-5 text-blue-600 group-hover:translate-x-1 transition-transform" />
                  </div>
                  <Typography variant="h5" className="font-bold text-slate-900 mb-3">
                    Products
                  </Typography>
                  <Typography variant="body2" className="text-slate-600 mb-6">
                    Manage your product catalog and sync with WhatsApp Business
                  </Typography>
                  <Button className="w-full bg-blue-600 hover:bg-blue-700">
                  Manage Products
                </Button>
                </CardContent>
              </Card>

              <Card className="group hover:shadow-xl transition-all duration-300 border-0 bg-gradient-to-br from-green-50 to-green-100">
                <CardContent className="p-8">
                  <div className="flex items-center justify-between mb-6">
                    <div className="w-14 h-14 bg-green-600 rounded-2xl flex items-center justify-center group-hover:scale-110 transition-transform">
                      <ShoppingCart className="w-8 h-8 text-white" />
                    </div>
                    <ArrowRight className="w-5 h-5 text-green-600 group-hover:translate-x-1 transition-transform" />
                  </div>
                  <Typography variant="h5" className="font-bold text-slate-900 mb-3">
                  Orders
                </Typography>
                  <Typography variant="body2" className="text-slate-600 mb-6">
                  Track and manage WhatsApp orders and customer interactions
                </Typography>
                  <Button className="w-full bg-green-600 hover:bg-green-700">
                  View Orders
                </Button>
                </CardContent>
              </Card>

              <Card className="group hover:shadow-xl transition-all duration-300 border-0 bg-gradient-to-br from-purple-50 to-purple-100">
                <CardContent className="p-8">
                  <div className="flex items-center justify-between mb-6">
                    <div className="w-14 h-14 bg-purple-600 rounded-2xl flex items-center justify-center group-hover:scale-110 transition-transform">
                      <BarChart4 className="w-8 h-8 text-white" />
                    </div>
                    <ArrowRight className="w-5 h-5 text-purple-600 group-hover:translate-x-1 transition-transform" />
                  </div>
                  <Typography variant="h5" className="font-bold text-slate-900 mb-3">
                  Analytics
                </Typography>
                  <Typography variant="body2" className="text-slate-600 mb-6">
                  View performance metrics and customer insights
                </Typography>
                  <Button className="w-full bg-purple-600 hover:bg-purple-700">
                  View Analytics
                </Button>
                </CardContent>
              </Card>
            </div>
            </div>
          )}

        {/* Account Information */}
        <Card className="border-0 shadow-lg">
          <CardHeader className="pb-4">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-slate-100 rounded-xl flex items-center justify-center">
                <User className="w-5 h-5 text-slate-600" />
            </div>
              <div>
                <CardTitle className="text-slate-900">Account Information</CardTitle>
                <Typography variant="body2" className="text-slate-600">
                  Your account details and merchant information
                </Typography>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
              <div className="space-y-2">
                <Typography variant="body2" className="text-slate-500 font-medium">
                  Email Address
                </Typography>
                <Typography variant="body1" className="text-slate-900 font-medium">
                  {user?.email}
                </Typography>
              </div>
              
              <div className="space-y-2">
                <Typography variant="body2" className="text-slate-500 font-medium">
                  Account Role
                </Typography>
                <Badge variant="secondary" className="bg-blue-100 text-blue-700">
                  {getRoleDisplayName(user?.role || 'staff')}
                </Badge>
              </div>
              
              <div className="space-y-2">
                <Typography variant="body2" className="text-slate-500 font-medium">
                  Merchant ID
                </Typography>
                <Typography variant="body1" className="font-mono text-sm text-slate-600 bg-slate-50 px-2 py-1 rounded">
                  {user?.merchant_id}
                </Typography>
              </div>
              
              {merchantInfo && (
                <div className="space-y-2">
                  <Typography variant="body2" className="text-slate-500 font-medium">
                    Member Since
                  </Typography>
                  <Typography variant="body1" className="text-slate-900">
                    {new Date(merchantInfo.created_at).toLocaleDateString('en-US', {
                      year: 'numeric',
                      month: 'long',
                      day: 'numeric'
                    })}
                  </Typography>
                </div>
              )}
            </div>
          </CardContent>
          </Card>
        </div>
    </div>
  )
}

export default Dashboard