/**
 * PaymentSettingsTab - Payment provider configuration with security-first approach
 * Shows connection status and masked credentials only
 */

import { usePaymentSettings } from '@/hooks/settings'
import { PAYMENT_PROVIDERS } from '@/constants/settings'
import { SettingsSection, SettingsGrid } from '@/components/settings/SettingsLayout'
import { ProviderConnectionCard, ConnectionTestButton } from '@/components/settings/ConnectionStatus'
import { PaystackSubaccountUpdate } from '@/components/settings/SecureCredentialUpdate'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { Alert, AlertDescription } from '@/components/ui/Alert'
import {
  CreditCard,
  Shield,
  AlertTriangle,
  CheckCircle,
  Lock,
  Key,
  RefreshCw,
  Clock,
  AlertCircle,
} from 'lucide-react'

interface PaymentSettingsTabProps {
  role: 'admin' | 'staff'
}

export function PaymentSettingsTab({ role }: PaymentSettingsTabProps) {
  // Admin-only access control
  if (role !== 'admin') {
    return (
      <Alert className="border-red-200 bg-red-50">
        <AlertTriangle className="h-4 w-4" />
        <AlertDescription>
          You need admin privileges to access payment settings and integration details.
        </AlertDescription>
      </Alert>
    )
  }

  const {
    data: paymentSettings,
    isLoading,
    error,
    isUpdatingCredentials,
    testConnection,
    isTestingConnection,
    disconnect,
    isDisconnecting,
    syncPaystack,
    isSyncingPaystack,
  } = usePaymentSettings()

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <LoadingSpinner size="lg" />
      </div>
    )
  }

  if (error) {
    return (
      <Alert className="border-red-200 bg-red-50">
        <AlertDescription>
          Failed to load payment settings. Please refresh the page.
        </AlertDescription>
      </Alert>
    )
  }

  return (
    <div className="space-y-6">
      {/* Overview */}
      <SettingsSection
        title="Payment Providers"
        description="Configure payment processing for your business"
      >
        <Alert>
          <Shield className="h-4 w-4" />
          <AlertDescription>
            Your payment credentials are encrypted and stored securely.
            Only masked identifiers are displayed for security.
          </AlertDescription>
        </Alert>

        <SettingsGrid columns={1}>
          {/* Paystack */}
          <PaystackConnectionCard
            settings={paymentSettings?.paystack}
            role={role}
            onUpdate={() => {
              // Will be handled by the mutation
            }}
            onTest={() => testConnection('paystack')}
            onSync={() => syncPaystack()}
            onDisconnect={() => disconnect('paystack')}
            isTestingConnection={isTestingConnection}
            isUpdating={isUpdatingCredentials}
            isSyncing={isSyncingPaystack}
            isDisconnecting={isDisconnecting}
          />

          {/* Korapay 
          <KorapayConnectionCard
            settings={paymentSettings?.korapay}
            role={role}
            onUpdate={() => {
              // Will be handled by the mutation
            }}
            onTest={() => testConnection('korapay')}
            onDisconnect={() => disconnect('korapay')}
            isTestingConnection={isTestingConnection}
            isUpdating={isUpdatingCredentials}
            isDisconnecting={isDisconnecting}
          />
          */}
        </SettingsGrid>
      </SettingsSection>

      {/* Payment Security */}
     
    </div>
  )
}

/**
 * Paystack connection card
 */
interface PaystackConnectionCardProps {
  settings: any
  role: 'admin' | 'staff'
  onUpdate: () => void
  onTest: () => void
  onSync: () => void
  onDisconnect: () => void
  isTestingConnection: boolean
  isUpdating: boolean
  isSyncing: boolean
  isDisconnecting: boolean
}

function PaystackConnectionCard({
  settings,
  role,
  onUpdate,
  onTest,
  onSync,
  onDisconnect,
  isTestingConnection,
  isUpdating,
  isSyncing,
  isDisconnecting,
}: PaystackConnectionCardProps) {
  const providerInfo = PAYMENT_PROVIDERS.paystack

  return (
    <ProviderConnectionCard
      provider="paystack"
      title={providerInfo.name}
      description={providerInfo.description}
      connected={settings?.connected || false}
      status={settings?.status || 'inactive'}
      maskedIdentifier={settings?.maskedPublicKey}
      connectedAt={settings?.connectedAt}
      lastUsed={settings?.lastUsed}
      role={role}
      icon={<CreditCard className="w-5 h-5 text-green-600" />}
      actions={
        <div className="flex flex-wrap gap-2">
          <ConnectionTestButton
            provider="paystack"
            isLoading={isTestingConnection}
            onTest={onTest}
          />

          {role === 'admin' ? (
            <>
              <PaystackSubaccountUpdate
                onSuccess={onUpdate}
                trigger={
                  <Button variant="outline" size="sm" disabled={isUpdating}>
                    <Key className="w-4 h-4 mr-2" />
                    {isUpdating ? 'Update Subaccount' : 'Update Subaccount'}
                  </Button>
                }
              />

              {/* Sync with Paystack Button */}
              <Button
                variant="outline"
                size="sm"
                onClick={onSync}
                disabled={isUpdating || isSyncing}
              >
                <RefreshCw className={`w-4 h-4 mr-2 ${isSyncing ? 'animate-spin' : ''}`} />
                {isSyncing ? 'Syncing...' : 'Sync with Paystack'}
              </Button>

              {settings?.connected && (
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={onDisconnect}
                  disabled={isDisconnecting}
                >
                  {isDisconnecting ? 'Disconnecting...' : 'Disconnect'}
                </Button>
              )}
            </>
          ) : (
            <Badge variant="secondary" className="text-xs">
              <Lock className="w-3 h-3 mr-1" />
              Admin Only
            </Badge>
          )}
        </div>
      }
    >
      <div className="space-y-3">
        {/* Sync Status and Settlement Info */}
        <div className="flex items-center gap-2 flex-wrap">
          {/* Sync Status Badge */}
          {settings?.syncStatus && (
            <Badge
              variant={settings.syncStatus === 'synced' ? 'default' : settings.syncStatus === 'failed' ? 'destructive' : 'secondary'}
              className={
                settings.syncStatus === 'synced'
                  ? 'bg-green-100 text-green-700'
                  : settings.syncStatus === 'failed'
                  ? 'bg-red-100 text-red-700'
                  : 'bg-yellow-100 text-yellow-700'
              }
            >
              {settings.syncStatus === 'synced' && <CheckCircle className="w-3 h-3 mr-1" />}
              {settings.syncStatus === 'pending' && <Clock className="w-3 h-3 mr-1" />}
              {settings.syncStatus === 'failed' && <AlertCircle className="w-3 h-3 mr-1" />}
              {settings.syncStatus === 'synced' ? 'Synced' : settings.syncStatus === 'failed' ? 'Sync Failed' : 'Sync Pending'}
            </Badge>
          )}

          {/* Settlement Schedule */}
          {settings?.settlementSchedule && (
            <Badge variant="outline" className="text-xs">
              Settlement: {settings.settlementSchedule}
            </Badge>
          )}
        </div>

        {/* Subaccount Details */}
        {settings?.subaccountCode && (
          <div className="text-sm space-y-1">
            {settings.bankName && <div><strong>Bank:</strong> {settings.bankName}</div>}
            {settings.accountName && <div><strong>Account:</strong> {settings.accountName}</div>}
            {settings.percentageCharge && <div><strong>Commission:</strong> {settings.percentageCharge}%</div>}
          </div>
        )}

        {/* Sync Error */}
        {settings?.syncError && (
          <Alert className="border-red-200 bg-red-50">
            <AlertTriangle className="h-4 w-4" />
            <AlertDescription className="text-xs">
              <strong>Sync Error:</strong> {settings.syncError}
            </AlertDescription>
          </Alert>
        )}

        <div className="text-sm text-muted-foreground">
          <strong>Features:</strong> {providerInfo.features.join(', ')}
        </div>
      </div>
    </ProviderConnectionCard>
  )
}


