/**
 * WhatsAppSettingsTab - WhatsApp Business API configuration
 * System user tokens are NEVER displayed, not even masked
 * Separate edit flows for details vs token replacement
 */

import { useState } from 'react'
import { useWhatsAppSettings } from '@/hooks/settings'
import { SettingsSection } from '@/components/settings/SettingsLayout'
import { Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { Alert, AlertDescription } from '@/components/ui/Alert'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Input } from '@/components/ui/Input'
import { Label } from '@/components/ui/Label'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/Dialog'
import { useToast } from '@/hooks/use-toast'
import {
  MessageCircle,
  Shield,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Lock,
  RefreshCw,
  Activity,
  Edit3,
  Key,
  Eye,
  EyeOff,
  Webhook,
  Copy,
  Info,
} from 'lucide-react'

interface WhatsAppSettingsTabProps {
  role: 'admin' | 'staff'
}

export function WhatsAppSettingsTab({ role }: WhatsAppSettingsTabProps) {
  const { toast } = useToast()
  const [showTokenInput, setShowTokenInput] = useState(false)
  const [newToken, setNewToken] = useState('')
  const [editDetailsOpen, setEditDetailsOpen] = useState(false)
  const [replaceTokenOpen, setReplaceTokenOpen] = useState(false)

  // Form state for editing details
  const [detailsForm, setDetailsForm] = useState({
    app_id: '',
    waba_id: '',
    phone_number_id: '',
    whatsapp_phone_e164: ''
  })

  // Admin-only access control
  if (role !== 'admin') {
    return (
      <Alert className="border-red-200 bg-red-50">
        <AlertTriangle className="h-4 w-4" />
        <AlertDescription>
          You need admin privileges to access WhatsApp integration settings.
        </AlertDescription>
      </Alert>
    )
  }

  const {
    data: whatsappSettings,
    isLoading,
    error,
    updateDetails,
    isUpdatingDetails,
    replaceToken,
    isReplacingToken,
    testConnection,
    isTestingConnection,
    verifyWebhook,
    isVerifyingWebhook,
  } = useWhatsAppSettings()

  // Initialize form when data loads
  const handleEditDetails = () => {
    if (whatsappSettings) {
      setDetailsForm({
        app_id: whatsappSettings.app_id_masked?.replace(/•/g, '') || '',
        waba_id: whatsappSettings.waba_id_masked?.replace(/•/g, '') || '',
        phone_number_id: whatsappSettings.phone_number_id_masked?.replace(/•/g, '') || '',
        whatsapp_phone_e164: whatsappSettings.phoneNumber || ''
      })
    }
    setEditDetailsOpen(true)
  }

  // Validation helper functions
  const isValidLength = (value: string, min: number, max: number) => {
    return value.length >= min && value.length <= max
  }

  const isValidToken = (token: string) => {
    return token.length >= 100
  }

  const isValidPhone = (phone: string) => {
    return phone.startsWith('+') && phone.length >= 10
  }

  // Check if details form is valid
  const isDetailsFormValid = () => {
    return (
      isValidLength(detailsForm.app_id, 15, 17) &&
      isValidLength(detailsForm.waba_id, 15, 17) &&
      isValidLength(detailsForm.phone_number_id, 15, 17) &&
      isValidPhone(detailsForm.whatsapp_phone_e164)
    )
  }

  const handleSaveDetails = async () => {
    try {
      await updateDetails(detailsForm)
      setEditDetailsOpen(false)
      toast({
        title: 'Details updated',
        description: 'WhatsApp configuration details have been updated successfully.'
      })
    } catch (error: any) {
      toast({
        title: 'Failed to update details',
        description: error.message || 'An error occurred while updating details.',
        variant: 'destructive'
      })
    }
  }

  const handleReplaceToken = async () => {
    if (!newToken.trim()) {
      toast({
        title: 'Token required',
        description: 'Please enter a valid system user token.',
        variant: 'destructive'
      })
      return
    }

    try {
      await replaceToken(newToken)
      setReplaceTokenOpen(false)
      setNewToken('')
      toast({
        title: 'Token replaced',
        description: 'System user token has been replaced successfully.'
      })
    } catch (error: any) {
      toast({
        title: 'Failed to replace token',
        description: error.message || 'An error occurred while replacing the token.',
        variant: 'destructive'
      })
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    )
  }

  if (error) {
    return (
      <Alert className="border-red-200 bg-red-50">
        <AlertDescription>
          Failed to load WhatsApp settings. Please refresh the page.
        </AlertDescription>
      </Alert>
    )
  }

  const connectionStatus = whatsappSettings?.connected ? 'Connected' : 'Not Connected'
  const statusColor = whatsappSettings?.status === 'active' ? 'text-green-600' : 'text-red-600'

  return (
    <div className="space-y-6">
      {/* Security Notice */}
      <Alert>
        <Shield className="h-4 w-4" />
        <AlertDescription>
          System user access tokens are never displayed for security.
          Only connection status and masked IDs are shown.
        </AlertDescription>
      </Alert>

      {/* Connection Overview */}
      <SettingsSection
        title="WhatsApp Business API"
        description="Connect WhatsApp to communicate with customers"
      >
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <MessageCircle className="w-5 h-5 text-green-600" />
              WhatsApp Business API Integration
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Connection Status */}
            <div className="flex items-center justify-between p-4 bg-muted/50 rounded-lg">
              <div className="flex items-center gap-3">
                {whatsappSettings?.connected ? (
                  <CheckCircle className="w-5 h-5 text-green-600" />
                ) : (
                  <XCircle className="w-5 h-5 text-red-600" />
                )}
                <div>
                  <div className="font-medium">{connectionStatus}</div>
                  <div className={`text-sm ${statusColor}`}>
                    Status: {whatsappSettings?.status || 'inactive'}
                  </div>
                </div>
              </div>

              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => testConnection()}
                  disabled={isTestingConnection}
                >
                  {isTestingConnection ? 'Testing...' : 'Test Connection'}
                </Button>

                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => verifyWebhook()}
                  disabled={isVerifyingWebhook}
                >
                  {isVerifyingWebhook ? 'Verifying...' : 'Verify Webhook'}
                </Button>
              </div>
            </div>

            {/* Configuration Details */}
            {whatsappSettings?.connected && (
              <div className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <Label className="text-sm font-medium text-muted-foreground">App ID</Label>
                    <p className="font-mono text-sm mt-1">
                      {whatsappSettings.app_id_masked || 'Not configured'}
                    </p>
                  </div>

                  <div>
                    <Label className="text-sm font-medium text-muted-foreground">WABA ID</Label>
                    <p className="font-mono text-sm mt-1">
                      {whatsappSettings.waba_id_masked || 'Not configured'}
                    </p>
                  </div>

                  <div>
                    <Label className="text-sm font-medium text-muted-foreground">Phone Number ID</Label>
                    <p className="font-mono text-sm mt-1">
                      {whatsappSettings.phone_number_id_masked || 'Not configured'}
                    </p>
                  </div>

                  <div>
                    <Label className="text-sm font-medium text-muted-foreground">WhatsApp Phone Number</Label>
                    <p className="font-mono text-sm mt-1">
                      {whatsappSettings.phoneNumber || 'Not configured'}
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                  <div>
                    <Label className="text-muted-foreground">Token Last Updated</Label>
                    <p className="mt-1">
                      {whatsappSettings.token_last_updated
                        ? new Date(whatsappSettings.token_last_updated).toLocaleString()
                        : 'Never'}
                    </p>
                  </div>
                  <div>
                    <Label className="text-muted-foreground">Last Verified</Label>
                    <p className="mt-1">
                      {whatsappSettings.lastVerifiedAt
                        ? new Date(whatsappSettings.lastVerifiedAt).toLocaleString()
                        : 'Never verified'}
                    </p>
                  </div>
                </div>

                {/* Validation Status */}
                {whatsappSettings.validation_result && (
                  <div className="mt-4 p-3 rounded-lg border">
                    <div className="flex items-center gap-2 mb-2">
                      {whatsappSettings.validation_result.is_valid ? (
                        <CheckCircle className="w-4 h-4 text-green-600" />
                      ) : (
                        <XCircle className="w-4 h-4 text-red-600" />
                      )}
                      <Label className="font-medium">
                        Latest Validation: {whatsappSettings.validation_result.is_valid ? 'Passed' : 'Failed'}
                      </Label>
                    </div>

                    <div className="text-sm text-muted-foreground">
                      Tested: {new Date(whatsappSettings.validation_result.tested_at).toLocaleString()}
                    </div>

                    {whatsappSettings.validation_result.business_name && (
                      <div className="text-sm mt-1">
                        <span className="text-muted-foreground">Business: </span>
                        <span className="font-medium">{whatsappSettings.validation_result.business_name}</span>
                      </div>
                    )}

                    {whatsappSettings.validation_result.error_message && (
                      <div className="text-sm text-red-600 mt-1">
                        {whatsappSettings.validation_result.error_message}
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      </SettingsSection>

      {/* Configuration Management */}
      <SettingsSection
        title="Configuration Management"
        description="Manage WhatsApp Business API settings with separate security flows"
      >
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Edit Details Card */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Edit3 className="w-5 h-5" />
                Edit Details
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground mb-4">
                Update your WhatsApp Business API configuration details.
              </p>

              <Dialog open={editDetailsOpen} onOpenChange={setEditDetailsOpen}>
                <DialogTrigger asChild>
                  <Button
                    variant="outline"
                    className="w-full"
                    onClick={handleEditDetails}
                  >
                    <Edit3 className="w-4 h-4 mr-2" />
                    Edit Configuration Details
                  </Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>Edit WhatsApp Configuration Details</DialogTitle>
                    <DialogDescription>
                      Update your WhatsApp Business API configuration. IDs are shown partially masked for security.
                    </DialogDescription>
                  </DialogHeader>

                  <div className="space-y-4">
                    <div>
                      <Label htmlFor="app_id">App ID</Label>
                      <Input
                        id="app_id"
                        className={`h-12 ${
                          detailsForm.app_id && !isValidLength(detailsForm.app_id, 15, 17)
                            ? 'border-red-500 focus:border-red-500'
                            : ''
                        }`}
                        value={detailsForm.app_id}
                        onChange={(e) => setDetailsForm(prev => ({ ...prev, app_id: e.target.value }))}
                        placeholder="Enter your App ID (15-17 digits)"
                      />
                      <p className={`text-xs mt-1 ${
                        detailsForm.app_id && !isValidLength(detailsForm.app_id, 15, 17)
                          ? 'text-red-600'
                          : 'text-muted-foreground'
                      }`}>
                        Must be 15-17 characters long {detailsForm.app_id && `(current: ${detailsForm.app_id.length})`}
                      </p>
                    </div>

                    <div>
                      <Label htmlFor="waba_id">WABA ID</Label>
                      <Input
                        id="waba_id"
                        className={`h-12 ${
                          detailsForm.waba_id && !isValidLength(detailsForm.waba_id, 15, 17)
                            ? 'border-red-500 focus:border-red-500'
                            : ''
                        }`}
                        value={detailsForm.waba_id}
                        onChange={(e) => setDetailsForm(prev => ({ ...prev, waba_id: e.target.value }))}
                        placeholder="Enter your WABA ID (15-17 digits)"
                      />
                      <p className={`text-xs mt-1 ${
                        detailsForm.waba_id && !isValidLength(detailsForm.waba_id, 15, 17)
                          ? 'text-red-600'
                          : 'text-muted-foreground'
                      }`}>
                        Must be 15-17 characters long {detailsForm.waba_id && `(current: ${detailsForm.waba_id.length})`}
                      </p>
                    </div>

                    <div>
                      <Label htmlFor="phone_number_id">Phone Number ID</Label>
                      <Input
                        id="phone_number_id"
                        className={`h-12 ${
                          detailsForm.phone_number_id && !isValidLength(detailsForm.phone_number_id, 15, 17)
                            ? 'border-red-500 focus:border-red-500'
                            : ''
                        }`}
                        value={detailsForm.phone_number_id}
                        onChange={(e) => setDetailsForm(prev => ({ ...prev, phone_number_id: e.target.value }))}
                        placeholder="Enter your Phone Number ID (15-17 digits)"
                      />
                      <p className={`text-xs mt-1 ${
                        detailsForm.phone_number_id && !isValidLength(detailsForm.phone_number_id, 15, 17)
                          ? 'text-red-600'
                          : 'text-muted-foreground'
                      }`}>
                        Must be 15-17 characters long {detailsForm.phone_number_id && `(current: ${detailsForm.phone_number_id.length})`}
                      </p>
                    </div>

                    <div>
                      <Label htmlFor="whatsapp_phone">WhatsApp Phone Number (E164)</Label>
                      <Input
                        id="whatsapp_phone"
                        className={`h-12 ${
                          detailsForm.whatsapp_phone_e164 && !isValidPhone(detailsForm.whatsapp_phone_e164)
                            ? 'border-red-500 focus:border-red-500'
                            : ''
                        }`}
                        value={detailsForm.whatsapp_phone_e164}
                        onChange={(e) => setDetailsForm(prev => ({ ...prev, whatsapp_phone_e164: e.target.value }))}
                        placeholder="+1234567890"
                      />
                      <p className={`text-xs mt-1 ${
                        detailsForm.whatsapp_phone_e164 && !isValidPhone(detailsForm.whatsapp_phone_e164)
                          ? 'text-red-600'
                          : 'text-muted-foreground'
                      }`}>
                        Must start with + and include country code {detailsForm.whatsapp_phone_e164 && `(current: ${detailsForm.whatsapp_phone_e164.length})`}
                      </p>
                    </div>
                  </div>

                  <DialogFooter>
                    <Button variant="outline" onClick={() => setEditDetailsOpen(false)}>
                      Cancel
                    </Button>
                    <Button
                      onClick={handleSaveDetails}
                      disabled={isUpdatingDetails || !isDetailsFormValid()}
                    >
                      {isUpdatingDetails ? 'Saving...' : 'Save Changes'}
                    </Button>
                  </DialogFooter>
                </DialogContent>
              </Dialog>
            </CardContent>
          </Card>

          {/* Replace Token Card */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Key className="w-5 h-5" />
                Replace Token
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground mb-4">
                Replace your system user token. The current token is never displayed for security.
              </p>

              <Dialog open={replaceTokenOpen} onOpenChange={setReplaceTokenOpen}>
                <DialogTrigger asChild>
                  <Button variant="outline" className="w-full">
                    <Key className="w-4 h-4 mr-2" />
                    Replace System User Token
                  </Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>Replace System User Token</DialogTitle>
                    <DialogDescription>
                      Enter your new system user token. The current token will be completely replaced.
                    </DialogDescription>
                  </DialogHeader>

                  <div className="space-y-4">
                    <div>
                      <Label htmlFor="new_token">New System User Token</Label>
                      <div className="relative">
                        <Input
                          id="new_token"
                          className={`h-12 ${
                            newToken && !isValidToken(newToken)
                              ? 'border-red-500 focus:border-red-500'
                              : ''
                          }`}
                          type={showTokenInput ? 'text' : 'password'}
                          value={newToken}
                          onChange={(e) => setNewToken(e.target.value)}
                          placeholder="Enter your new system user token"
                        />
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          className="absolute right-0 top-0 h-full px-3 py-2 hover:bg-transparent"
                          onClick={() => setShowTokenInput(!showTokenInput)}
                        >
                          {showTokenInput ? (
                            <EyeOff className="h-4 w-4" />
                          ) : (
                            <Eye className="h-4 w-4" />
                          )}
                        </Button>
                      </div>
                      <p className={`text-xs mt-1 ${
                        newToken && !isValidToken(newToken)
                          ? 'text-red-600'
                          : 'text-muted-foreground'
                      }`}>
                        Must be at least 100 characters long {newToken && `(current: ${newToken.length})`}
                      </p>
                    </div>

                    <Alert>
                      <AlertTriangle className="h-4 w-4" />
                      <AlertDescription>
                        This will completely replace your current token. Make sure the new token is valid before proceeding.
                      </AlertDescription>
                    </Alert>
                  </div>

                  <DialogFooter>
                    <Button variant="outline" onClick={() => {
                      setReplaceTokenOpen(false)
                      setNewToken('')
                    }}>
                      Cancel
                    </Button>
                    <Button
                      onClick={handleReplaceToken}
                      disabled={isReplacingToken || !isValidToken(newToken)}
                    >
                      {isReplacingToken ? 'Replacing...' : 'Replace Token'}
                    </Button>
                  </DialogFooter>
                </DialogContent>
              </Dialog>
            </CardContent>
          </Card>
        </div>
      </SettingsSection>

      {/* Webhook Configuration */}
      <SettingsSection
        title="Webhook Configuration"
        description="Webhook URL and setup instructions for receiving WhatsApp events"
      >
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Webhook className="w-5 h-5" />
              Webhook Endpoint
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {whatsappSettings?.webhookUrl ? (
              <>
                <div className="space-y-2">
                  <Label className="text-sm font-medium">Callback URL</Label>
                  <div className="flex items-center gap-2">
                    <div className="flex-1 p-3 bg-muted rounded-lg font-mono text-sm break-all">
                      {whatsappSettings.webhookUrl}
                    </div>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        navigator.clipboard.writeText(whatsappSettings.webhookUrl)
                        toast({
                          title: 'Copied!',
                          description: 'Webhook URL copied to clipboard'
                        })
                      }}
                    >
                      <Copy className="w-4 h-4" />
                    </Button>
                  </div>
                </div>

                {whatsappSettings.lastWebhookAt && (
                  <div>
                    <Label className="text-sm font-medium text-muted-foreground">Last Webhook Received</Label>
                    <p className="text-sm mt-1">
                      {new Date(whatsappSettings.lastWebhookAt).toLocaleString()}
                    </p>
                  </div>
                )}

                <Alert>
                  <Info className="h-4 w-4" />
                  <AlertDescription>
                    <strong>Setup Instructions:</strong>
                    <ol className="mt-2 ml-4 list-decimal space-y-1 text-sm">
                      <li>Go to Meta Developer Console → Your App → WhatsApp → Configuration</li>
                      <li>Click 'Edit' on Webhook</li>
                      <li>Paste the Callback URL above</li>
                      <li>Enter the verify token provided by your administrator</li>
                      <li>Subscribe to: messages, message_status, message_template_status_update</li>
                      <li>Click 'Verify and Save'</li>
                    </ol>
                  </AlertDescription>
                </Alert>
              </>
            ) : (
              <Alert>
                <AlertTriangle className="h-4 w-4" />
                <AlertDescription>
                  No webhook URL configured. Please contact your administrator to set up the webhook endpoint.
                </AlertDescription>
              </Alert>
            )}
          </CardContent>
        </Card>
      </SettingsSection>

      {/* Security Information */}
      <SettingsSection
        title="Security & Privacy"
        description="WhatsApp integration security status"
      >
        <Card>
          <CardContent className="pt-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="flex items-center gap-3 p-3 bg-green-50 rounded-lg border border-green-200">
                <CheckCircle className="w-5 h-5 text-green-600" />
                <div>
                  <div className="font-medium text-green-900">Token Security</div>
                  <div className="text-sm text-green-700">Access tokens never displayed</div>
                </div>
              </div>

              <div className="flex items-center gap-3 p-3 bg-green-50 rounded-lg border border-green-200">
                <CheckCircle className="w-5 h-5 text-green-600" />
                <div>
                  <div className="font-medium text-green-900">ID Masking</div>
                  <div className="text-sm text-green-700">Sensitive IDs are server-side masked</div>
                </div>
              </div>

              <div className="flex items-center gap-3 p-3 bg-green-50 rounded-lg border border-green-200">
                <CheckCircle className="w-5 h-5 text-green-600" />
                <div>
                  <div className="font-medium text-green-900">Message Encryption</div>
                  <div className="text-sm text-green-700">End-to-end encryption by WhatsApp</div>
                </div>
              </div>

              <div className="flex items-center gap-3 p-3 bg-green-50 rounded-lg border border-green-200">
                <CheckCircle className="w-5 h-5 text-green-600" />
                <div>
                  <div className="font-medium text-green-900">Token Rotation</div>
                  <div className="text-sm text-green-700">Admin-controlled token management</div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </SettingsSection>
    </div>
  )
}