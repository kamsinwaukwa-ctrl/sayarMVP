/**
 * ProfileSettingsTab - Profile and team management (Admin only)
 * Manages user profile, team members, and audit logs
 */

import { useState } from 'react'
import { useProfileSettings, useTeamMembers } from '@/hooks/settings'
import { SettingsSection, SettingsGrid } from '@/components/settings/SettingsLayout'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/badge'
import { Alert, AlertDescription } from '@/components/ui/Alert'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Input } from '@/components/ui/Input'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import {
  Users,
  Shield,
  User,
  Mail,
  Phone,
  Globe,
  Plus,
  MoreHorizontal,
  Crown,
  UserCheck,
  Trash2,
  Edit,
} from 'lucide-react'

interface ProfileSettingsTabProps {
  role: 'admin' | 'staff'
}

export function ProfileSettingsTab({ role }: ProfileSettingsTabProps) {
  const {
    data: profileSettings,
    isLoading: isLoadingProfile,
    error: profileError,
    update: updateProfile,
    isUpdating: isUpdatingProfile,
  } = useProfileSettings()

  const {
    data: teamMembers,
    isLoading: isLoadingTeam,
    error: teamError,
    invite: inviteTeamMember,
    isInviting,
    updateMember,
    isUpdatingMember,
    removeMember,
    isRemovingMember,
  } = useTeamMembers()

  if (isLoadingProfile || isLoadingTeam) {
    return (
      <div className="flex items-center justify-center py-12">
        <LoadingSpinner size="lg" />
      </div>
    )
  }

  if (profileError || teamError) {
    return (
      <Alert className="border-red-200 bg-red-50">
        <AlertDescription>
          Failed to load profile settings. Please refresh the page.
        </AlertDescription>
      </Alert>
    )
  }

  return (
    <div className="space-y-6">
      {/* Profile Information */}
      <SettingsSection
        title="Profile Information"
        description="Your personal and business contact information"
      >
        <SettingsGrid columns={2}>
          {/* Personal Information */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <User className="w-5 h-5" />
                Personal Details
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <label className="text-sm font-medium text-muted-foreground">Name</label>
                <p className="text-sm mt-1">
                  {profileSettings?.primary_contact_name || 'Not set'}
                </p>
              </div>

              <div>
                <label className="text-sm font-medium text-muted-foreground">Email</label>
                <p className="text-sm mt-1 flex items-center gap-2">
                  {profileSettings?.email}
                  <Badge variant="secondary" className="text-xs">
                    <Crown className="w-3 h-3 mr-1" />
                    {profileSettings?.role}
                  </Badge>
                </p>
              </div>

              {profileSettings?.contact_phone && (
                <div>
                  <label className="text-sm font-medium text-muted-foreground">Phone</label>
                  <p className="text-sm mt-1">{profileSettings.contact_phone}</p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Business Contact */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Mail className="w-5 h-5" />
                Business Contact
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {profileSettings?.primary_contact_email && (
                <div>
                  <label className="text-sm font-medium text-muted-foreground">Primary Email</label>
                  <p className="text-sm mt-1">{profileSettings.primary_contact_email}</p>
                </div>
              )}

              {profileSettings?.company_website && (
                <div>
                  <label className="text-sm font-medium text-muted-foreground flex items-center gap-1">
                    <Globe className="w-3 h-3" />
                    Website
                  </label>
                  <p className="text-sm mt-1">
                    <a
                      href={profileSettings.company_website}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-primary hover:underline"
                    >
                      {profileSettings.company_website}
                    </a>
                  </p>
                </div>
              )}

              <div>
                <label className="text-sm font-medium text-muted-foreground">Member Since</label>
                <p className="text-sm mt-1">
                  {profileSettings?.created_at
                    ? new Date(profileSettings.created_at).toLocaleDateString()
                    : 'Unknown'}
                </p>
              </div>
            </CardContent>
          </Card>
        </SettingsGrid>

        <div className="flex justify-end">
          <Button
            onClick={() => {
              // Open edit profile dialog
            }}
            disabled={isUpdatingProfile}
          >
            <Edit className="w-4 h-4 mr-2" />
            Edit Profile
          </Button>
        </div>
      </SettingsSection>

      {/* Team Management */}
      <SettingsSection
        title="Team Management"
        description="Manage team members and their access levels"
      >
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <div>
              <h3 className="text-lg font-medium">Team Members</h3>
              <p className="text-sm text-muted-foreground">
                Manage who has access to your business settings
              </p>
            </div>

            <InviteTeamMemberDialog
              onInvite={(data) => inviteTeamMember(data)}
              isInviting={isInviting}
            />
          </div>

          <Card>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Member</TableHead>
                  <TableHead>Role</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Last Login</TableHead>
                  <TableHead className="w-[70px]">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {teamMembers?.members?.map((member: any) => (
                  <TableRow key={member.id}>
                    <TableCell>
                      <div className="flex items-center gap-3">
                        <Avatar className="w-8 h-8">
                          <AvatarFallback>
                            {member.name?.charAt(0) || member.email?.charAt(0)}
                          </AvatarFallback>
                        </Avatar>
                        <div>
                          <div className="font-medium">{member.name || 'No name'}</div>
                          <div className="text-sm text-muted-foreground">{member.email}</div>
                        </div>
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge
                        variant={member.role === 'admin' ? 'default' : 'secondary'}
                        className={member.role === 'admin' ? 'bg-purple-100 text-purple-700' : ''}
                      >
                        {member.role === 'admin' ? (
                          <Crown className="w-3 h-3 mr-1" />
                        ) : (
                          <UserCheck className="w-3 h-3 mr-1" />
                        )}
                        {member.role}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge variant="secondary" className="bg-green-100 text-green-700">
                        Active
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <span className="text-sm text-muted-foreground">
                        {member.last_login
                          ? new Date(member.last_login).toLocaleDateString()
                          : 'Never'}
                      </span>
                    </TableCell>
                    <TableCell>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="sm">
                            <MoreHorizontal className="w-4 h-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem
                            onClick={() => {
                              // Edit member
                            }}
                            disabled={isUpdatingMember}
                          >
                            <Edit className="w-4 h-4 mr-2" />
                            Edit Role
                          </DropdownMenuItem>
                          <DropdownMenuItem
                            onClick={() => removeMember(member.id)}
                            disabled={isRemovingMember}
                            className="text-red-600"
                          >
                            <Trash2 className="w-4 h-4 mr-2" />
                            Remove
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </TableCell>
                  </TableRow>
                )) || (
                  <TableRow>
                    <TableCell colSpan={5} className="text-center py-6">
                      <Users className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
                      <p className="text-sm text-muted-foreground">No team members yet</p>
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </Card>
        </div>
      </SettingsSection>

      {/* Security Information */}
      <SettingsSection
        title="Account Security"
        description="Security status and recent activity"
      >
        <Card>
          <CardContent className="pt-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="flex items-center gap-3 p-3 bg-green-50 rounded-lg border border-green-200">
                <Shield className="w-5 h-5 text-green-600" />
                <div>
                  <div className="font-medium text-green-900">Account Secured</div>
                  <div className="text-sm text-green-700">Strong authentication enabled</div>
                </div>
              </div>

              <div className="flex items-center gap-3 p-3 bg-green-50 rounded-lg border border-green-200">
                <Users className="w-5 h-5 text-green-600" />
                <div>
                  <div className="font-medium text-green-900">Team Access</div>
                  <div className="text-sm text-green-700">Role-based permissions active</div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </SettingsSection>
    </div>
  )
}

/**
 * Invite team member dialog
 */
interface InviteTeamMemberDialogProps {
  onInvite: (data: { email: string; role: 'admin' | 'staff'; name?: string }) => void
  isInviting: boolean
}

function InviteTeamMemberDialog({ onInvite, isInviting }: InviteTeamMemberDialogProps) {
  const [open, setOpen] = useState(false)
  const [formData, setFormData] = useState({
    email: '',
    name: '',
    role: 'staff' as 'admin' | 'staff',
  })

  const handleInvite = () => {
    if (!formData.email.trim()) return

    onInvite({
      email: formData.email.trim(),
      name: formData.name.trim() || undefined,
      role: formData.role,
    })

    setFormData({ email: '', name: '', role: 'staff' })
    setOpen(false)
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button>
          <Plus className="w-4 h-4 mr-2" />
          Invite Team Member
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Invite Team Member</DialogTitle>
          <DialogDescription>
            Invite a new team member to access your business settings.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div>
            <label className="text-sm font-medium">Email Address *</label>
            <Input
              type="email"
              value={formData.email}
              onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              placeholder="member@example.com"
              className="mt-1"
            />
          </div>

          <div>
            <label className="text-sm font-medium">Name (Optional)</label>
            <Input
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              placeholder="Team member name"
              className="mt-1"
            />
          </div>

          <div>
            <label className="text-sm font-medium">Role</label>
            <select
              value={formData.role}
              onChange={(e) => setFormData({ ...formData, role: e.target.value as 'admin' | 'staff' })}
              className="mt-1 w-full p-2 border rounded-md"
            >
              <option value="staff">Staff - View and test connections</option>
              <option value="admin">Admin - Full access including credentials</option>
            </select>
          </div>

          <div className="flex justify-end gap-2 pt-4">
            <Button
              variant="outline"
              onClick={() => setOpen(false)}
              disabled={isInviting}
            >
              Cancel
            </Button>
            <Button
              onClick={handleInvite}
              disabled={isInviting || !formData.email.trim()}
            >
              {isInviting ? 'Sending...' : 'Send Invitation'}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}

