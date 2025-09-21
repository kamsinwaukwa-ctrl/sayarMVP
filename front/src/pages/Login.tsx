/**
 * Login Page for Sayar WhatsApp Commerce Platform
 * Professional two-column layout with AuthLayout component
 */

import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '@/hooks/useAuth'
import LoginForm from '@/components/auth/LoginForm'
import AuthLayout from '@/components/auth/AuthLayout'

const Login = () => {
  const navigate = useNavigate()
  const { isAuthenticated, loading } = useAuth()

  useEffect(() => {
    if (isAuthenticated && !loading) {
      // Always redirect to dashboard - setup cards will handle incomplete setup
      navigate('/dashboard', { replace: true })
    }
  }, [isAuthenticated, loading, navigate])

  const handleLoginSuccess = () => {
    // Always redirect to dashboard - setup cards will handle incomplete setup
    navigate('/dashboard', { replace: true })
  }

  const handleLoginError = (error: string) => {
    console.error('Login error:', error)
  }

  if (isAuthenticated) {
    return null
  }

  return (
    <AuthLayout
      title="Welcome back"
      description="Sign in to your Sayar account to continue"
      footerText="Don't have an account?"
      footerLink={{ text: "Sign up", href: "/signup" }}
    >
      <LoginForm 
        onSuccess={handleLoginSuccess}
        onError={handleLoginError}
      />
    </AuthLayout>
  )
}

export default Login