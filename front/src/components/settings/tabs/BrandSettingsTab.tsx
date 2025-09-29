/**
 * BrandSettingsTab - Brand and business identity settings
 * Reuses existing BrandBasicsSetup component in settings mode
 */

import { useState } from 'react'
import { useBrandSettings } from '@/hooks/settings'
import { SettingsSection } from '@/components/settings/SettingsLayout'
import { BrandBasicsSetup } from '@/components/setup/BrandBasicsSetup'
import { Button } from '@/components/ui/Button'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { Alert, AlertDescription } from '@/components/ui/Alert'
import { Badge } from '@/components/ui/Badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Separator } from '@/components/ui/separator'
import { Building, Globe, Mail, Phone, MapPin, Edit, Lock } from 'lucide-react'

interface BrandSettingsTabProps {
  role: 'admin' | 'staff'
}

export function BrandSettingsTab({ role }: BrandSettingsTabProps) {
  const { data: brandSettings, isLoading, error, isUpdating } = useBrandSettings()
  const [isEditing, setIsEditing] = useState(false)

  const canEdit = role === 'admin'

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
          Failed to load brand settings. Please refresh the page.
        </AlertDescription>
      </Alert>
    )
  }

  const handleUpdateComplete = () => {
    setIsEditing(false)
    // The hook will automatically update the cache
  }

  return (
    <div className="space-y-6">
      {/* Current Brand Information */}
      <SettingsSection
        title="Brand Identity"
        description="Your business identity as it appears to customers"
      >
        <div className="grid gap-6 md:grid-cols-2">
          {/* Business Info Card */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-base font-medium flex items-center gap-2">
                <Building className="w-4 h-4" />
                Business Information
              </CardTitle>
              {!canEdit && (
                <Badge variant="secondary" className="text-xs">
                  <Lock className="w-3 h-3 mr-1" />
                  View Only
                </Badge>
              )}
            </CardHeader>
            <CardContent className="space-y-4">
              {brandSettings?.business_name && (
                <div>
                  <dt className="text-sm font-medium text-muted-foreground">Business Name</dt>
                  <dd className="text-sm">{brandSettings.business_name}</dd>
                </div>
              )}

              {brandSettings?.slug && (
                <div>
                  <dt className="text-sm font-medium text-muted-foreground">Business Slug</dt>
                  <dd className="text-sm font-mono bg-muted px-2 py-1 rounded">
                    {brandSettings.slug}
                  </dd>
                </div>
              )}

              {brandSettings?.description && (
                <div>
                  <dt className="text-sm font-medium text-muted-foreground">Description</dt>
                  <dd className="text-sm">{brandSettings.description}</dd>
                </div>
              )}

              {brandSettings?.currency && (
                <div>
                  <dt className="text-sm font-medium text-muted-foreground">Currency</dt>
                  <dd className="text-sm">{brandSettings.currency}</dd>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Logo Card */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base font-medium">Brand Logo</CardTitle>
            </CardHeader>
            <CardContent>
              {brandSettings?.logo_url ? (
                <div className="flex items-center gap-4">
                  <img
                    src={brandSettings.logo_url}
                    alt="Business Logo"
                    className="w-16 h-16 rounded-lg object-cover border"
                  />
                  <div className="text-sm text-muted-foreground">
                    Current brand logo
                  </div>
                </div>
              ) : (
                <div className="flex items-center gap-4">
                  <div className="w-16 h-16 rounded-lg bg-muted flex items-center justify-center">
                    <Building className="w-8 h-8 text-muted-foreground" />
                  </div>
                  <div className="text-sm text-muted-foreground">
                    No logo uploaded
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Extended Information (Settings Mode Only) */}
        {(brandSettings?.website_url ||
          brandSettings?.support_email ||
          brandSettings?.support_phone_e164 ||
          brandSettings?.address_line1) && (
          <>
            <Separator className="my-6" />

            <div className="space-y-4">
              <h3 className="text-lg font-medium">Contact Information</h3>

              <div className="grid gap-6 md:grid-cols-2">
                {/* Contact Details */}
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base font-medium flex items-center gap-2">
                      <Mail className="w-4 h-4" />
                      Contact Details
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    {brandSettings?.website_url && (
                      <div>
                        <dt className="text-sm font-medium text-muted-foreground flex items-center gap-1">
                          <Globe className="w-3 h-3" />
                          Website
                        </dt>
                        <dd className="text-sm">
                          <a
                            href={brandSettings.website_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-primary hover:underline"
                          >
                            {brandSettings.website_url}
                          </a>
                        </dd>
                      </div>
                    )}

                    {brandSettings?.support_email && (
                      <div>
                        <dt className="text-sm font-medium text-muted-foreground flex items-center gap-1">
                          <Mail className="w-3 h-3" />
                          Support Email
                        </dt>
                        <dd className="text-sm">
                          <a href={`mailto:${brandSettings.support_email}`} className="text-primary hover:underline">
                            {brandSettings.support_email}
                          </a>
                        </dd>
                      </div>
                    )}

                    {brandSettings?.support_phone_e164 && (
                      <div>
                        <dt className="text-sm font-medium text-muted-foreground flex items-center gap-1">
                          <Phone className="w-3 h-3" />
                          Support Phone
                        </dt>
                        <dd className="text-sm">
                          <a href={`tel:${brandSettings.support_phone_e164}`} className="text-primary hover:underline">
                            {brandSettings.support_phone_e164}
                          </a>
                        </dd>
                      </div>
                    )}
                  </CardContent>
                </Card>

                {/* Address */}
                {brandSettings?.address_line1 && (
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-base font-medium flex items-center gap-2">
                        <MapPin className="w-4 h-4" />
                        Business Address
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <address className="text-sm not-italic space-y-1">
                        <div>{brandSettings.address_line1}</div>
                        {brandSettings.address_line2 && <div>{brandSettings.address_line2}</div>}
                        <div>
                          {[
                            brandSettings.city,
                            brandSettings.state_region,
                            brandSettings.postal_code
                          ].filter(Boolean).join(', ')}
                        </div>
                        {brandSettings.country_code && (
                          <div className="font-medium">{brandSettings.country_code}</div>
                        )}
                      </address>
                    </CardContent>
                  </Card>
                )}
              </div>
            </div>
          </>
        )}

        {/* Action Buttons */}
        <div className="flex justify-end pt-4 border-t">
          {canEdit ? (
            <Button
              onClick={() => setIsEditing(true)}
              disabled={isUpdating}
              className="flex items-center gap-2"
            >
              <Edit className="w-4 h-4" />
              Edit Brand Information
            </Button>
          ) : (
            <Alert className="border-orange-200 bg-orange-50">
              <Lock className="h-4 w-4" />
              <AlertDescription>
                You need admin privileges to edit brand settings.
              </AlertDescription>
            </Alert>
          )}
        </div>
      </SettingsSection>

      {/* Edit Dialog */}
      {isEditing && canEdit && (
        <SettingsSection
          title="Edit Brand Information"
          description="Update your business identity and contact details"
        >
          <BrandBasicsSetup
            mode="settings"
            onComplete={handleUpdateComplete}
            onCancel={() => setIsEditing(false)}
            showExtended={true}
          />
        </SettingsSection>
      )}
    </div>
  )
}