/**
 * MetaCatalogSettingsTab - Meta Business Catalog configuration
 * System user tokens are never displayed, sync status and metadata only
 */

import React, { useState } from 'react'
import { useMetaCatalogSettings } from '@/hooks/settings'
import { SettingsSection } from '@/components/settings/SettingsLayout'
import { SyncStatusBadge } from '@/components/settings/ConnectionStatus'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { Button } from '@/components/ui/Button'
import { Alert, AlertDescription } from '@/components/ui/Alert'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Progress } from '@/components/ui/progress'
import { Input } from '@/components/ui/Input'
import { Label } from '@/components/ui/label'
import {
  Store,
  Shield,
  AlertTriangle,
  CheckCircle,
  XCircle,
  RefreshCw,
  Loader2,
  BarChart3,
  CheckCircle2,
  Edit,
  Save,
  X,
} from 'lucide-react'

interface MetaCatalogSettingsTabProps {
  role: 'admin' | 'staff'
}

export function MetaCatalogSettingsTab({ role }: MetaCatalogSettingsTabProps) {
  // State for catalog ID editing
  const [isEditingCatalogId, setIsEditingCatalogId] = useState(false)
  const [catalogIdValue, setCatalogIdValue] = useState('')

  const {
    data: catalogSettings,
    isLoading,
    error,
    sync,
    isSyncing,
    updateCatalogId,
    isUpdatingCatalogId,
    verifyCatalogId,
    isVerifyingCatalogId,
  } = useMetaCatalogSettings()

  // Initialize catalogIdValue when data loads
  React.useEffect(() => {
    if (catalogSettings?.catalogId && !catalogIdValue) {
      setCatalogIdValue(catalogSettings.catalogId)
    }
  }, [catalogSettings?.catalogId, catalogIdValue])

  // Admin-only access control
  if (role !== 'admin') {
    return (
      <Alert className="border-red-200 bg-red-50">
        <AlertTriangle className="h-4 w-4" />
        <AlertDescription>
          You need admin privileges to access Meta Catalog integration settings.
        </AlertDescription>
      </Alert>
    )
  }

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
          Failed to load Meta Catalog settings. Please refresh the page.
        </AlertDescription>
      </Alert>
    )
  }

  // Handlers for catalog ID editing
  const handleEditCatalogId = () => {
    setIsEditingCatalogId(true)
    setCatalogIdValue(catalogSettings?.catalogId || '')
  }

  const handleSaveCatalogId = () => {
    updateCatalogId(catalogIdValue)
    setIsEditingCatalogId(false)
  }

  const handleCancelEdit = () => {
    setIsEditingCatalogId(false)
    setCatalogIdValue(catalogSettings?.catalogId || '')
  }

  const handleVerifyCatalogId = () => {
    verifyCatalogId()
  }

  const syncProgress = catalogSettings?.productsCount
    ? ((catalogSettings.productsCount - (catalogSettings.failedProducts || 0)) / catalogSettings.productsCount) * 100
    : 0

  return (
    <div className="space-y-6">
      {/* Meta Catalog Connection */}
      <SettingsSection
        title="Meta Business Catalog"
        description="Sync your products to Facebook and Instagram Shopping"
      >
        <Alert>
          <Shield className="h-4 w-4" />
          <AlertDescription>
            Catalog access tokens are never displayed for security.
            Only sync status and catalog metadata are shown.
          </AlertDescription>
        </Alert>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Store className="w-5 h-5 text-blue-600" />
              Meta Business Catalog
            </CardTitle>
            <p className="text-sm text-muted-foreground">
              Sync products to Facebook and Instagram for shopping
            </p>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Connection Status */}
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-muted-foreground">Status:</span>
              <SyncStatusBadge status={catalogSettings?.syncStatus || 'never'} />
            </div>

            {/* Catalog ID Management */}
            <div className="space-y-2">
              <Label htmlFor="catalog-id">Catalog ID</Label>
              {isEditingCatalogId ? (
                <div className="flex items-center gap-2">
                  <Input
                    id="catalog-id"
                    value={catalogIdValue}
                    onChange={(e) => setCatalogIdValue(e.target.value)}
                    placeholder="Enter Meta Commerce Catalog ID"
                    className="flex-1 h-12"
                  />
                  <Button
                    size="sm"
                    onClick={handleSaveCatalogId}
                    disabled={isUpdatingCatalogId || !catalogIdValue.trim()}
                  >
                    {isUpdatingCatalogId ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Save className="w-4 h-4" />
                    )}
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={handleCancelEdit}
                    disabled={isUpdatingCatalogId}
                  >
                    <X className="w-4 h-4" />
                  </Button>
                </div>
              ) : (
                <div className="flex items-center gap-2">
                  <Input
                    value={catalogSettings?.catalogId || 'Not configured'}
                    readOnly
                    className="flex-1 bg-muted h-12"
                  />
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={handleEditCatalogId}
                  >
                    <Edit className="w-4 h-4" />
                  </Button>
                </div>
              )}
            </div>

            {/* Error Message for Invalid Status */}
            {catalogSettings?.syncStatus === 'failed' && catalogSettings?.message && (
              <Alert className="border-red-200 bg-red-50">
                <AlertTriangle className="h-4 w-4" />
                <AlertDescription>
                  {catalogSettings.message}
                </AlertDescription>
              </Alert>
            )}

            {/* Action Buttons */}
            <div className="flex flex-wrap gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => sync()}
                disabled={isSyncing}
              >
                {isSyncing ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Syncing...
                  </>
                ) : (
                  <>
                    <RefreshCw className="w-4 h-4 mr-2" />
                    Sync Now
                  </>
                )}
              </Button>

              <Button
                variant="outline"
                size="sm"
                onClick={handleVerifyCatalogId}
                disabled={isVerifyingCatalogId || !catalogSettings?.catalogId}
              >
                {isVerifyingCatalogId ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Verifying...
                  </>
                ) : (
                  <>
                    <CheckCircle2 className="w-4 h-4 mr-2" />
                    Verify Catalog
                  </>
                )}
              </Button>
            </div>
          </CardContent>
        </Card>
      </SettingsSection>

      {/* Sync Status Details */}
      <SettingsSection
        title="Synchronization Status"
        description="Product sync progress and error details"
      >
        <div className="grid gap-6 md:grid-cols-2">
          {/* Sync Progress Card */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <BarChart3 className="w-5 h-5" />
                Sync Progress
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {catalogSettings?.productsCount ? (
                <>
                  <div className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span>Products Synced</span>
                      <span>{Math.round(syncProgress)}%</span>
                    </div>
                    <Progress value={syncProgress} className="h-2" />
                  </div>

                  <div className="grid grid-cols-2 gap-4 text-center">
                    <div>
                      <div className="text-2xl font-bold text-green-600">
                        {catalogSettings.productsCount - (catalogSettings.failedProducts || 0)}
                      </div>
                      <div className="text-xs text-muted-foreground">Successful</div>
                    </div>
                    <div>
                      <div className="text-2xl font-bold text-red-600">
                        {catalogSettings.failedProducts || 0}
                      </div>
                      <div className="text-xs text-muted-foreground">Failed</div>
                    </div>
                  </div>
                </>
              ) : (
                <div className="text-center py-6">
                  <Store className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
                  <h4 className="font-medium mb-2">No Products Synced</h4>
                  <p className="text-sm text-muted-foreground">
                    Start by syncing your products to Meta Catalog.
                  </p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Sync Health Card */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Shield className="w-5 h-5" />
                Catalog Health
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {catalogSettings?.syncStatus === 'synced' ? (
                <>
                  <div className="flex items-center gap-3 p-3 bg-green-50 rounded-lg border border-green-200">
                    <CheckCircle className="w-5 h-5 text-green-600" />
                    <div>
                      <div className="font-medium text-green-900">Catalog Healthy</div>
                      <div className="text-sm text-green-700">All products synced successfully</div>
                    </div>
                  </div>
                </>
              ) : catalogSettings?.syncStatus === 'failed' ? (
                <>
                  <div className="flex items-center gap-3 p-3 bg-red-50 rounded-lg border border-red-200">
                    <XCircle className="w-5 h-5 text-red-600" />
                    <div>
                      <div className="font-medium text-red-900">Sync Issues</div>
                      <div className="text-sm text-red-700">
                        {catalogSettings.failedProducts} products failed to sync
                      </div>
                    </div>
                  </div>

                  <Alert className="border-orange-200 bg-orange-50">
                    <AlertTriangle className="h-4 w-4" />
                    <AlertDescription>
                      Some products couldn't be synced to Meta Catalog.
                      Check product details and try syncing again.
                    </AlertDescription>
                  </Alert>
                </>
              ) : catalogSettings?.syncStatus === 'pending' ? (
                <>
                  <div className="flex items-center gap-3 p-3 bg-yellow-50 rounded-lg border border-yellow-200">
                    <Loader2 className="w-5 h-5 text-yellow-600 animate-spin" />
                    <div>
                      <div className="font-medium text-yellow-900">Sync In Progress</div>
                      <div className="text-sm text-yellow-700">Products are being synced to catalog</div>
                    </div>
                  </div>
                </>
              ) : (
                <>
                  <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg border border-gray-200">
                    <Store className="w-5 h-5 text-gray-600" />
                    <div>
                      <div className="font-medium text-gray-900">Never Synced</div>
                      <div className="text-sm text-gray-700">No products have been synced yet</div>
                    </div>
                  </div>
                </>
              )}

              {catalogSettings?.lastSyncAt && (
                <div className="text-sm text-muted-foreground">
                  <strong>Last sync:</strong> {new Date(catalogSettings.lastSyncAt).toLocaleString()}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </SettingsSection>

      {/* Catalog Features */}
      <SettingsSection
        title="Catalog Features"
        description="Available features for your Meta Business Catalog"
      >
        <Card>
          <CardContent className="pt-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="flex items-center gap-3 p-3 bg-blue-50 rounded-lg border border-blue-200">
                <CheckCircle className="w-5 h-5 text-blue-600" />
                <div>
                  <div className="font-medium text-blue-900">Facebook Shop</div>
                  <div className="text-sm text-blue-700">Products appear on Facebook</div>
                </div>
              </div>

              <div className="flex items-center gap-3 p-3 bg-blue-50 rounded-lg border border-blue-200">
                <CheckCircle className="w-5 h-5 text-blue-600" />
                <div>
                  <div className="font-medium text-blue-900">Instagram Shopping</div>
                  <div className="text-sm text-blue-700">Tag products in Instagram posts</div>
                </div>
              </div>

              <div className="flex items-center gap-3 p-3 bg-blue-50 rounded-lg border border-blue-200">
                <CheckCircle className="w-5 h-5 text-blue-600" />
                <div>
                  <div className="font-medium text-blue-900">WhatsApp Catalog</div>
                  <div className="text-sm text-blue-700">Share products in WhatsApp chats</div>
                </div>
              </div>

              <div className="flex items-center gap-3 p-3 bg-blue-50 rounded-lg border border-blue-200">
                <CheckCircle className="w-5 h-5 text-blue-600" />
                <div>
                  <div className="font-medium text-blue-900">Dynamic Ads</div>
                  <div className="text-sm text-blue-700">Automated product advertisements</div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </SettingsSection>
    </div>
  )
}