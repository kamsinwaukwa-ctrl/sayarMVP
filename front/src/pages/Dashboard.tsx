import {
  AppBar,
  Toolbar,
  Typography,
  Button,
  Container,
  Grid,
  Paper,
  Box,
} from '@mui/material'
import { useAuth } from '../context/AuthProvider'

const Dashboard = () => {
  const { user, signOut } = useAuth()

  const handleSignOut = async () => {
    try {
      await signOut()
    } catch (error) {
      console.error('Error signing out:', error)
    }
  }

  return (
    <Box sx={{ flexGrow: 1 }}>
      <AppBar position="static">
        <Toolbar>
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            Sayar Dashboard
          </Typography>
          <Typography variant="body2" sx={{ mr: 2 }}>
            {user?.email}
          </Typography>
          <Button color="inherit" onClick={handleSignOut}>
            Sign Out
          </Button>
        </Toolbar>
      </AppBar>

      <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
        <Grid container spacing={3}>
          <Grid item xs={12}>
            <Paper sx={{ p: 2, display: 'flex', flexDirection: 'column' }}>
              <Typography variant="h4" gutterBottom>
                Welcome to Sayar WhatsApp Commerce
              </Typography>
              <Typography variant="body1" paragraph>
                Your merchant dashboard is ready! Here you can manage your products,
                orders, customers, and WhatsApp commerce settings.
              </Typography>
              <Typography variant="body2" color="textSecondary">
                Coming soon: Products, Orders, Customers, Analytics, and more...
              </Typography>
            </Paper>
          </Grid>

          {/* Placeholder cards for future features */}
          <Grid item xs={12} md={4}>
            <Paper sx={{ p: 2, textAlign: 'center' }}>
              <Typography variant="h6" gutterBottom>
                Products
              </Typography>
              <Typography variant="body2" color="textSecondary">
                Manage your catalog
              </Typography>
            </Paper>
          </Grid>

          <Grid item xs={12} md={4}>
            <Paper sx={{ p: 2, textAlign: 'center' }}>
              <Typography variant="h6" gutterBottom>
                Orders
              </Typography>
              <Typography variant="body2" color="textSecondary">
                Track WhatsApp orders
              </Typography>
            </Paper>
          </Grid>

          <Grid item xs={12} md={4}>
            <Paper sx={{ p: 2, textAlign: 'center' }}>
              <Typography variant="h6" gutterBottom>
                Analytics
              </Typography>
              <Typography variant="body2" color="textSecondary">
                View your performance
              </Typography>
            </Paper>
          </Grid>
        </Grid>
      </Container>
    </Box>
  )
}

export default Dashboard