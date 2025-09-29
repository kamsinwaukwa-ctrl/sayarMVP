/**
 * Settings data management hooks using React Query
 * Provides secure caching and state management for settings
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useToast } from '@/hooks/use-toast'
import { settingsApi } from '@/lib/settings-api'
import { trackSettingsEvent, SETTINGS_EVENTS } from '@/lib/security'
import {
  IntegrationSettingsResponse,
  PaymentSettings,
  WhatsAppSettings,
  MetaCatalogSettings,
  BrandSettings,
  ProfileSettings,
  PaymentProvider,
  CredentialUpdateFormData,
  WhatsAppUpdateFormData,
  WhatsAppDetailsUpdateData,
  WhatsAppTokenReplaceData,
  MetaCatalogUpdateFormData,
} from '@/types/settings'

// Query keys for React Query cache management
export const SETTINGS_QUERY_KEYS = {
  integrations: ['settings', 'integrations'] as const,
  brand: ['settings', 'brand'] as const,
  payments: ['settings', 'payments'] as const,
  whatsapp: ['settings', 'whatsapp'] as const,
  metaCatalog: ['settings', 'meta-catalog'] as const,
  profile: ['settings', 'profile'] as const,
  teamMembers: ['settings', 'team-members'] as const,
  auditLogs: ['settings', 'audit-logs'] as const,
} as const

/**
 * Hook for integration settings overview (status only, no credentials)
 */
export function useIntegrationSettings() {
  return useQuery({
    queryKey: SETTINGS_QUERY_KEYS.integrations,
    queryFn: () => settingsApi.getIntegrationSettings(),
    staleTime: 5 * 60 * 1000, // 5 minutes
    gcTime: 10 * 60 * 1000, // 10 minutes
  })
}

/**
 * Hook for brand settings management
 */
export function useBrandSettings() {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  const query = useQuery({
    queryKey: SETTINGS_QUERY_KEYS.brand,
    queryFn: () => settingsApi.getBrandSettings(),
    staleTime: 10 * 60 * 1000, // 10 minutes
  })

  const updateMutation = useMutation({
    mutationFn: (data: Partial<BrandSettings>) =>
      settingsApi.updateBrandSettings(data),
    onSuccess: (data) => {
      queryClient.setQueryData(SETTINGS_QUERY_KEYS.brand, data)
      queryClient.invalidateQueries({ queryKey: SETTINGS_QUERY_KEYS.integrations })

      toast({
        title: 'Brand settings updated',
        description: 'Your brand information has been successfully updated.',
      })

      trackSettingsEvent('settings.brand_updated', {
        fields: Object.keys(data),
      })
    },
    onError: (error) => {
      toast({
        title: 'Failed to update brand settings',
        description: error.message,
        variant: 'destructive',
      })
    },
  })

  return {
    data: query.data,
    isLoading: query.isLoading,
    error: query.error,
    update: updateMutation.mutate,
    isUpdating: updateMutation.isPending,
  }
}

/**
 * Hook for payment settings (masked credentials only)
 */
export function usePaymentSettings() {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  const query = useQuery({
    queryKey: SETTINGS_QUERY_KEYS.payments,
    queryFn: () => settingsApi.getPaymentSettings(),
    staleTime: 5 * 60 * 1000,
  })

  const updateCredentialsMutation = useMutation({
    mutationFn: ({ provider, data }: { provider: PaymentProvider; data: CredentialUpdateFormData }) =>
      settingsApi.updatePaymentCredentials(provider, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: SETTINGS_QUERY_KEYS.payments })
      queryClient.invalidateQueries({ queryKey: SETTINGS_QUERY_KEYS.integrations })

      toast({
        title: 'Payment credentials updated',
        description: `${variables.provider} credentials have been successfully updated and verified.`,
      })
    },
    onError: (error) => {
      toast({
        title: 'Failed to update credentials',
        description: error.message,
        variant: 'destructive',
      })
    },
  })

  const testConnectionMutation = useMutation({
    mutationFn: (provider: PaymentProvider) =>
      settingsApi.testPaymentConnection(provider),
    onSuccess: (result, provider) => {
      toast({
        title: result.success ? 'Connection successful' : 'Connection failed',
        description: result.message,
        variant: result.success ? 'default' : 'destructive',
      })

      trackSettingsEvent(
        result.success
          ? SETTINGS_EVENTS.CONNECTION_TEST_SUCCESS
          : SETTINGS_EVENTS.CONNECTION_TEST_FAILED,
        { provider }
      )
    },
  })

  const disconnectMutation = useMutation({
    mutationFn: (provider: PaymentProvider) =>
      settingsApi.disconnectPaymentProvider(provider),
    onSuccess: (_, provider) => {
      queryClient.invalidateQueries({ queryKey: SETTINGS_QUERY_KEYS.payments })
      queryClient.invalidateQueries({ queryKey: SETTINGS_QUERY_KEYS.integrations })

      toast({
        title: 'Payment provider disconnected',
        description: `${provider} has been disconnected successfully.`,
      })
    },
  })

  const syncPaystackMutation = useMutation({
    mutationFn: () => settingsApi.syncPaystackSubaccount(),
    onSuccess: (result) => {
      // Invalidate queries to refresh data after sync
      queryClient.invalidateQueries({ queryKey: SETTINGS_QUERY_KEYS.payments })
      queryClient.invalidateQueries({ queryKey: SETTINGS_QUERY_KEYS.integrations })

      toast({
        title: result.success ? 'Sync successful' : 'Sync failed',
        description: result.message,
        variant: result.success ? 'default' : 'destructive',
      })

      trackSettingsEvent(
        result.success
          ? SETTINGS_EVENTS.CONNECTION_TEST_SUCCESS
          : SETTINGS_EVENTS.CONNECTION_TEST_FAILED,
        { provider: 'paystack', action: 'sync' }
      )
    },
    onError: (error) => {
      toast({
        title: 'Sync failed',
        description: error.message,
        variant: 'destructive',
      })
    },
  })

  return {
    data: query.data,
    isLoading: query.isLoading,
    error: query.error,
    updateCredentials: updateCredentialsMutation.mutate,
    isUpdatingCredentials: updateCredentialsMutation.isPending,
    testConnection: testConnectionMutation.mutate,
    isTestingConnection: testConnectionMutation.isPending,
    disconnect: disconnectMutation.mutate,
    isDisconnecting: disconnectMutation.isPending,
    syncPaystack: syncPaystackMutation.mutate,
    isSyncingPaystack: syncPaystackMutation.isPending,
  }
}

/**
 * Hook for WhatsApp settings (no tokens exposed)
 */
export function useWhatsAppSettings() {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  const query = useQuery({
    queryKey: SETTINGS_QUERY_KEYS.whatsapp,
    queryFn: () => settingsApi.getWhatsAppSettings(),
    staleTime: 2 * 60 * 1000, // 2 minutes (more frequent updates)
  })

  const updateMutation = useMutation({
    mutationFn: (data: WhatsAppUpdateFormData) =>
      settingsApi.updateWhatsAppSettings(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: SETTINGS_QUERY_KEYS.whatsapp })
      queryClient.invalidateQueries({ queryKey: SETTINGS_QUERY_KEYS.integrations })

      toast({
        title: 'WhatsApp settings updated',
        description: 'Your WhatsApp configuration has been updated successfully.',
      })
    },
  })

  const testConnectionMutation = useMutation({
    mutationFn: () => settingsApi.testWhatsAppConnection(),
    onSuccess: (result) => {
      toast({
        title: result.success ? 'WhatsApp connection successful' : 'WhatsApp connection failed',
        description: result.message,
        variant: result.success ? 'default' : 'destructive',
      })
    },
  })

  const updateDetailsMutation = useMutation({
    mutationFn: (data: WhatsAppDetailsUpdateData) =>
      settingsApi.updateWhatsAppDetails(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: SETTINGS_QUERY_KEYS.whatsapp })
      queryClient.invalidateQueries({ queryKey: SETTINGS_QUERY_KEYS.integrations })

      toast({
        title: 'WhatsApp details updated',
        description: 'Your WhatsApp configuration details have been updated successfully.',
      })
    },
    onError: (error) => {
      toast({
        title: 'Failed to update WhatsApp details',
        description: error.message,
        variant: 'destructive',
      })
    },
  })

  const replaceTokenMutation = useMutation({
    mutationFn: (token: string) => settingsApi.replaceWhatsAppToken(token),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: SETTINGS_QUERY_KEYS.whatsapp })
      queryClient.invalidateQueries({ queryKey: SETTINGS_QUERY_KEYS.integrations })

      toast({
        title: 'WhatsApp token replaced',
        description: 'Your WhatsApp system user token has been replaced successfully.',
      })
    },
    onError: (error) => {
      toast({
        title: 'Failed to replace WhatsApp token',
        description: error.message,
        variant: 'destructive',
      })
    },
  })

  const rotateTokenMutation = useMutation({
    mutationFn: (newToken: string) => settingsApi.replaceWhatsAppToken(newToken),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: SETTINGS_QUERY_KEYS.whatsapp })

      toast({
        title: 'WhatsApp token rotated',
        description: 'Your WhatsApp access token has been rotated successfully.',
      })
    },
  })

  const verifyWebhookMutation = useMutation({
    mutationFn: () => settingsApi.verifyWhatsAppWebhook(),
    onSuccess: (result) => {
      if (result.success) {
        queryClient.invalidateQueries({ queryKey: SETTINGS_QUERY_KEYS.whatsapp })
      }

      toast({
        title: result.success ? 'Webhook verified' : 'Webhook verification failed',
        description: result.message,
        variant: result.success ? 'default' : 'destructive',
      })
    },
  })

  return {
    data: query.data,
    isLoading: query.isLoading,
    error: query.error,
    update: updateMutation.mutate,
    isUpdating: updateMutation.isPending,
    updateDetails: updateDetailsMutation.mutate,
    isUpdatingDetails: updateDetailsMutation.isPending,
    replaceToken: replaceTokenMutation.mutate,
    isReplacingToken: replaceTokenMutation.isPending,
    testConnection: testConnectionMutation.mutate,
    isTestingConnection: testConnectionMutation.isPending,
    rotateToken: rotateTokenMutation.mutate,
    isRotatingToken: rotateTokenMutation.isPending,
    verifyWebhook: verifyWebhookMutation.mutate,
    isVerifyingWebhook: verifyWebhookMutation.isPending,
  }
}

/**
 * Hook for Meta Catalog settings (no access tokens exposed)
 */
export function useMetaCatalogSettings() {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  const query = useQuery({
    queryKey: SETTINGS_QUERY_KEYS.metaCatalog,
    queryFn: () => settingsApi.getMetaCatalogSettings(),
    staleTime: 5 * 60 * 1000,
  })

  const updateMutation = useMutation({
    mutationFn: (data: MetaCatalogUpdateFormData) =>
      settingsApi.updateMetaCatalogSettings(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: SETTINGS_QUERY_KEYS.metaCatalog })
      queryClient.invalidateQueries({ queryKey: SETTINGS_QUERY_KEYS.integrations })

      toast({
        title: 'Meta Catalog settings updated',
        description: 'Your Meta Catalog configuration has been updated successfully.',
      })
    },
  })

  const syncMutation = useMutation({
    mutationFn: () => settingsApi.syncMetaCatalog(),
    onSuccess: (result) => {
      // Don't immediately invalidate - sync happens in background
      setTimeout(() => {
        queryClient.invalidateQueries({ queryKey: SETTINGS_QUERY_KEYS.metaCatalog })
      }, 2000)

      toast({
        title: 'Catalog sync started',
        description: result.message,
      })
    },
  })

  const updateCatalogIdMutation = useMutation({
    mutationFn: (catalogId: string) => settingsApi.updateCatalogId(catalogId),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: SETTINGS_QUERY_KEYS.metaCatalog })
      queryClient.invalidateQueries({ queryKey: SETTINGS_QUERY_KEYS.integrations })

      toast({
        title: result.success ? 'Catalog ID updated' : 'Update failed',
        description: result.message,
        variant: result.success ? 'default' : 'destructive',
      })
    },
    onError: (error) => {
      toast({
        title: 'Failed to update catalog ID',
        description: error.message,
        variant: 'destructive',
      })
    },
  })

  const verifyCatalogIdMutation = useMutation({
    mutationFn: () => settingsApi.verifyCatalogId(),
    onSuccess: (result) => {
      // Refresh data after verification
      queryClient.invalidateQueries({ queryKey: SETTINGS_QUERY_KEYS.metaCatalog })

      toast({
        title: result.success ? 'Catalog verified' : 'Verification failed',
        description: result.message,
        variant: result.success ? 'default' : 'destructive',
      })
    },
    onError: (error) => {
      toast({
        title: 'Verification failed',
        description: error.message,
        variant: 'destructive',
      })
    },
  })

  return {
    data: query.data,
    isLoading: query.isLoading,
    error: query.error,
    update: updateMutation.mutate,
    isUpdating: updateMutation.isPending,
    sync: syncMutation.mutate,
    isSyncing: syncMutation.isPending,
    updateCatalogId: updateCatalogIdMutation.mutate,
    isUpdatingCatalogId: updateCatalogIdMutation.isPending,
    verifyCatalogId: verifyCatalogIdMutation.mutate,
    isVerifyingCatalogId: verifyCatalogIdMutation.isPending,
  }
}

/**
 * Hook for profile settings (admin only)
 */
export function useProfileSettings() {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  const query = useQuery({
    queryKey: SETTINGS_QUERY_KEYS.profile,
    queryFn: () => settingsApi.getProfileSettings(),
    staleTime: 10 * 60 * 1000,
  })

  const updateMutation = useMutation({
    mutationFn: (data: Partial<ProfileSettings>) =>
      settingsApi.updateProfileSettings(data),
    onSuccess: (data) => {
      queryClient.setQueryData(SETTINGS_QUERY_KEYS.profile, data)

      toast({
        title: 'Profile settings updated',
        description: 'Your profile information has been updated successfully.',
      })
    },
  })

  return {
    data: query.data,
    isLoading: query.isLoading,
    error: query.error,
    update: updateMutation.mutate,
    isUpdating: updateMutation.isPending,
  }
}

/**
 * Hook for team management (admin only)
 */
export function useTeamMembers() {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  const query = useQuery({
    queryKey: SETTINGS_QUERY_KEYS.teamMembers,
    queryFn: () => settingsApi.getTeamMembers(),
    staleTime: 5 * 60 * 1000,
  })

  const inviteMutation = useMutation({
    mutationFn: (data: { email: string; role: 'admin' | 'staff'; name?: string }) =>
      settingsApi.inviteTeamMember(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: SETTINGS_QUERY_KEYS.teamMembers })

      toast({
        title: 'Team member invited',
        description: 'Invitation sent successfully. They will receive an email to join.',
      })
    },
  })

  const updateMemberMutation = useMutation({
    mutationFn: ({ memberId, data }: {
      memberId: string;
      data: { role?: 'admin' | 'staff'; name?: string }
    }) => settingsApi.updateTeamMember(memberId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: SETTINGS_QUERY_KEYS.teamMembers })

      toast({
        title: 'Team member updated',
        description: 'Team member information updated successfully.',
      })
    },
  })

  const removeMemberMutation = useMutation({
    mutationFn: (memberId: string) => settingsApi.removeTeamMember(memberId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: SETTINGS_QUERY_KEYS.teamMembers })

      toast({
        title: 'Team member removed',
        description: 'Team member has been removed successfully.',
      })
    },
  })

  return {
    data: query.data,
    isLoading: query.isLoading,
    error: query.error,
    invite: inviteMutation.mutate,
    isInviting: inviteMutation.isPending,
    updateMember: updateMemberMutation.mutate,
    isUpdatingMember: updateMemberMutation.isPending,
    removeMember: removeMemberMutation.mutate,
    isRemovingMember: removeMemberMutation.isPending,
  }
}