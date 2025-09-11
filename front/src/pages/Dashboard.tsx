/**
 * Dashboard Page for Sayar WhatsApp Commerce Platform
 * Main merchant dashboard with navigation and overview
 */

import { useEffect, useState } from 'react'
import {
  AppBar,
  Toolbar,
  Typography,
  Button,
  Container,
  Grid,
  Paper,
  Box,
  Avatar,
  Chip,
  Alert,
  CircularProgress,
  Card,
  CardContent,
} from '@mui/material'
import { 
  ExitToApp, 
  Store, 
  ShoppingCart, 
  Analytics,
  WhatsApp,
  Person,
  Business 
} from '@mui/icons-material'
import { useAuth } from '../hooks/useAuth'
import { apiClient } from '../lib/api-client'

interface MerchantInfo {
  id: string
  name: string
  slug?: string
  whatsapp_phone_e164?: string
  currency: string
  created_at: string
}

const Dashboard = () => {
  const { user, logout, loading: authLoading } = useAuth()
  const [merchantInfo, setMerchantInfo] = useState<MerchantInfo | null>(null)
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

  const handleSignOut = () => {
    logout()
  }

  const getRoleDisplayName = (role: string) => {
    return role === 'admin' ? 'Owner' : 'Staff'
  }

  const getRoleColor = (role: string) => {
    return role === 'admin' ? 'primary' : 'secondary'
  }

  if (authLoading || loading) {
    return (
      <Box 
        display="flex" 
        justifyContent="center" 
        alignItems="center" 
        minHeight="100vh"
      >
        <CircularProgress />
      </Box>
    )
  }

  return (
    <Box sx={{ flexGrow: 1, minHeight: '100vh', bgcolor: 'grey.50' }}>
      {/* Header */}
      <AppBar position="static" elevation={1}>
        <Toolbar>
          <WhatsApp sx={{ mr: 2 }} />
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            Sayar Dashboard
          </Typography>
          
          {user && (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              <Box sx={{ textAlign: 'right' }}>
                <Typography variant="body2">
                  {user.name}
                </Typography>
                <Chip
                  label={getRoleDisplayName(user.role)}
                  size="small"
                  color={getRoleColor(user.role)}
                  variant="outlined"
                  sx={{ fontSize: '0.75rem', height: 20 }}
                />
              </Box>
              
              <Avatar sx={{ width: 32, height: 32 }}>
                {user.name.charAt(0).toUpperCase()}
              </Avatar>
              
              <Button 
                color="inherit" 
                onClick={handleSignOut}
                startIcon={<ExitToApp />}
                variant="outlined"
                size="small"
              >
                Sign Out
              </Button>
            </Box>
          )}
        </Toolbar>
      </AppBar>

      <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
        {error && (
          <Alert severity="error" sx={{ mb: 3 }}>
            {error}
          </Alert>
        )}

        {/* Welcome Section */}
        <Grid container spacing={3}>
          <Grid item xs={12}>
            <Card elevation={2}>
              <CardContent sx={{ p: 4 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <Business sx={{ mr: 2, fontSize: 40, color: 'primary.main' }} />
                  <Box>
                    <Typography variant="h4" gutterBottom>
                      Welcome to Sayar WhatsApp Commerce
                    </Typography>
                    <Typography variant="h6" color="text.secondary">
                      {merchantInfo?.name || 'Your Business'}
                    </Typography>
                  </Box>
                </Box>
                
                <Typography variant="body1" paragraph>
                  Your merchant dashboard is ready! Here you can manage your products,
                  orders, customers, and WhatsApp commerce settings.
                </Typography>
                
                {merchantInfo?.whatsapp_phone_e164 && (
                  <Chip 
                    icon={<WhatsApp />}
                    label={`WhatsApp: ${merchantInfo.whatsapp_phone_e164}`}
                    variant="outlined"
                    color="success"
                    sx={{ mr: 1 }}
                  />
                )}
                
                <Chip 
                  label={`Currency: ${merchantInfo?.currency || 'NGN'}`}
                  variant="outlined"
                  sx={{ mr: 1 }}
                />
              </CardContent>
            </Card>
          </Grid>

          {/* Feature Cards */}
          <Grid item xs={12} md={4}>
            <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
              <CardContent sx={{ textAlign: 'center', flexGrow: 1 }}>
                <Store sx={{ fontSize: 48, color: 'primary.main', mb: 2 }} />
                <Typography variant="h6" gutterBottom>
                  Products
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Manage your product catalog and sync with WhatsApp Business
                </Typography>
                <Box sx={{ mt: 2 }}>
                  <Button variant="outlined" disabled>
                    Coming Soon
                  </Button>
                </Box>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} md={4}>
            <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
              <CardContent sx={{ textAlign: 'center', flexGrow: 1 }}>
                <ShoppingCart sx={{ fontSize: 48, color: 'primary.main', mb: 2 }} />
                <Typography variant="h6" gutterBottom>
                  Orders
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Track and manage WhatsApp orders and customer interactions
                </Typography>
                <Box sx={{ mt: 2 }}>
                  <Button variant="outlined" disabled>
                    Coming Soon
                  </Button>
                </Box>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} md={4}>
            <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
              <CardContent sx={{ textAlign: 'center', flexGrow: 1 }}>
                <Analytics sx={{ fontSize: 48, color: 'primary.main', mb: 2 }} />
                <Typography variant="h6" gutterBottom>
                  Analytics
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  View performance metrics and customer insights
                </Typography>
                <Box sx={{ mt: 2 }}>
                  <Button variant="outlined" disabled>
                    Coming Soon
                  </Button>
                </Box>
              </CardContent>
            </Card>
          </Grid>

          {/* User Info Card */}
          <Grid item xs={12}>
            <Card elevation={1}>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <Person sx={{ mr: 2 }} />
                  <Typography variant="h6">
                    Account Information
                  </Typography>
                </Box>
                
                <Grid container spacing={2}>
                  <Grid item xs={12} sm={6} md={3}>
                    <Typography variant="body2" color="text.secondary">
                      Email
                    </Typography>
                    <Typography variant="body1">
                      {user?.email}
                    </Typography>
                  </Grid>
                  
                  <Grid item xs={12} sm={6} md={3}>
                    <Typography variant="body2" color="text.secondary">
                      Role
                    </Typography>
                    <Typography variant="body1">
                      {getRoleDisplayName(user?.role || 'staff')}
                    </Typography>
                  </Grid>
                  
                  <Grid item xs={12} sm={6} md={3}>
                    <Typography variant="body2" color="text.secondary">
                      Merchant ID
                    </Typography>
                    <Typography variant="body1" sx={{ fontFamily: 'monospace', fontSize: '0.875rem' }}>
                      {user?.merchant_id}
                    </Typography>
                  </Grid>
                  
                  {merchantInfo && (
                    <Grid item xs={12} sm={6} md={3}>
                      <Typography variant="body2" color="text.secondary">
                        Member Since
                      </Typography>
                      <Typography variant="body1">
                        {new Date(merchantInfo.created_at).toLocaleDateString()}
                      </Typography>
                    </Grid>
                  )}
                </Grid>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </Container>
    </Box>
  )
}

export default Dashboard