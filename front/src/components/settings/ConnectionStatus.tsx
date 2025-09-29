/**
 * ConnectionStatus - Secure connection status display components
 * Shows connection status without exposing sensitive credentials
 */

import { ReactNode } from 'react'
import { cn } from '@/lib/utils'
import { ConnectionStatus as StatusType, UserRole } from '@/types/settings'
import { STATUS_VARIANTS } from '@/constants/settings'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Card, CardContent, CardHeader } from '@/components/ui/Card'
import { Alert, AlertDescription } from '@/components/ui/Alert'
import {
  CheckCircle,
  XCircle,
  AlertTriangle,
  Clock,
  Loader2,
  LucideIcon,
} from 'lucide-react'

// Status icons mapping
const STATUS_ICONS: Record<StatusType, LucideIcon> = {
  active: CheckCircle,
  inactive: XCircle,
  error: XCircle,
  webhook_failed: AlertTriangle,
  pending: Clock,
}

// Status colors
const STATUS_COLORS: Record<StatusType, string> = {
  active: 'text-green-600 bg-green-50 border-green-200',
  inactive: 'text-red-600 bg-red-50 border-red-200',
  error: 'text-red-600 bg-red-50 border-red-200',
  webhook_failed: 'text-orange-600 bg-orange-50 border-orange-200',
  pending: 'text-yellow-600 bg-yellow-50 border-yellow-200',
}

/**
 * Connection status badge
 */
interface ConnectionStatusBadgeProps {
  status: StatusType
  label?: string
}

export function ConnectionStatusBadge({ status, label }: ConnectionStatusBadgeProps) {
  const Icon = STATUS_ICONS[status]
  const statusInfo = STATUS_VARIANTS[status]

  return (
    <Badge variant="secondary" className={cn('flex items-center gap-1', STATUS_COLORS[status])}>
      <Icon className="w-3 h-3" />
      {label || statusInfo.label}
    </Badge>
  )
}

/**
 * Provider connection card
 */
interface ProviderConnectionCardProps {
  provider: 'paystack' | 'korapay' | 'whatsapp' | 'meta'
  title: string
  description: string
  connected: boolean
  status: StatusType
  maskedIdentifier?: string
  connectedAt?: string
  lastUsed?: string
  role: UserRole
  icon: ReactNode
  children?: ReactNode
  actions?: ReactNode
}

export function ProviderConnectionCard({
  title,
  description,
  connected,
  status,
  maskedIdentifier,
  connectedAt,
  lastUsed,
  icon,
  children,
  actions,
}: ProviderConnectionCardProps) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            {icon}
            <div>
              <h3 className="font-medium">{title}</h3>
              <p className="text-sm text-muted-foreground">{description}</p>
            </div>
          </div>
          <ConnectionStatusBadge status={status} />
        </div>
      </CardHeader>

      {connected && (
        <CardContent>
          <div className="space-y-4">
            {/* Connection Details */}
            <div className="grid grid-cols-2 gap-4 text-sm">
              {maskedIdentifier && (
                <div>
                  <span className="text-muted-foreground">Identifier</span>
                  <code className="block bg-muted px-2 py-1 rounded mt-1 font-mono text-xs">
                    {maskedIdentifier}
                  </code>
                </div>
              )}
              {connectedAt && (
                <div>
                  <span className="text-muted-foreground">Connected</span>
                  <p className="mt-1">{new Date(connectedAt).toLocaleDateString()}</p>
                </div>
              )}
              {lastUsed && (
                <div>
                  <span className="text-muted-foreground">Last Used</span>
                  <p className="mt-1">{new Date(lastUsed).toLocaleDateString()}</p>
                </div>
              )}
            </div>

            {/* Status Messages */}
            {status === 'webhook_failed' && (
              <Alert className="border-orange-200 bg-orange-50">
                <AlertTriangle className="h-4 w-4" />
                <AlertDescription>
                  Webhook verification failed. Please check your webhook configuration.
                </AlertDescription>
              </Alert>
            )}

            {status === 'error' && (
              <Alert className="border-red-200 bg-red-50">
                <XCircle className="h-4 w-4" />
                <AlertDescription>
                  Connection error detected. Please test your connection or update credentials.
                </AlertDescription>
              </Alert>
            )}

            {/* Additional Content */}
            {children}

            {/* Actions */}
            {actions && <div className="flex gap-2 pt-2 border-t">{actions}</div>}
          </div>
        </CardContent>
      )}

      {!connected && (
        <CardContent>
          <div className="text-center py-6">
            <XCircle className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
            <h4 className="font-medium mb-2">Not Connected</h4>
            <p className="text-sm text-muted-foreground mb-4">
              Connect {title} to start using this integration.
            </p>
            {actions}
          </div>
        </CardContent>
      )}
    </Card>
  )
}

/**
 * Connection test button
 */
interface ConnectionTestButtonProps {
  provider: string
  isLoading?: boolean
  onTest: () => void
  disabled?: boolean
}

export function ConnectionTestButton({
  isLoading = false,
  onTest,
  disabled = false,
}: ConnectionTestButtonProps) {
  return (
    <Button
      variant="outline"
      size="sm"
      onClick={onTest}
      disabled={disabled || isLoading}
    >
      {isLoading ? (
        <>
          <Loader2 className="w-4 h-4 mr-2 animate-spin" />
          Testing...
        </>
      ) : (
        'Test Connection'
      )}
    </Button>
  )
}

/**
 * Sync status badge for Meta Catalog
 */
interface SyncStatusBadgeProps {
  status: 'synced' | 'pending' | 'failed' | 'never'
}

export function SyncStatusBadge({ status }: SyncStatusBadgeProps) {
  const statusConfig = {
    synced: { color: 'text-green-600 bg-green-50', label: 'Synced', icon: CheckCircle },
    pending: { color: 'text-yellow-600 bg-yellow-50', label: 'Syncing', icon: Loader2 },
    failed: { color: 'text-red-600 bg-red-50', label: 'Failed', icon: XCircle },
    never: { color: 'text-gray-600 bg-gray-50', label: 'Never synced', icon: Clock },
  }

  const config = statusConfig[status]
  const Icon = config.icon

  return (
    <Badge variant="secondary" className={cn('flex items-center gap-1', config.color)}>
      <Icon className={cn('w-3 h-3', status === 'pending' && 'animate-spin')} />
      {config.label}
    </Badge>
  )
}

/**
 * Statistics display for integrations
 */
interface IntegrationStatsProps {
  stats: Array<{
    label: string
    value: string | number
    subtext?: string
  }>
}

export function IntegrationStats({ stats }: IntegrationStatsProps) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
      {stats.map((stat, index) => (
        <div key={index} className="text-center">
          <div className="text-2xl font-bold text-foreground">{stat.value}</div>
          <div className="text-sm font-medium text-muted-foreground">{stat.label}</div>
          {stat.subtext && (
            <div className="text-xs text-muted-foreground">{stat.subtext}</div>
          )}
        </div>
      ))}
    </div>
  )
}