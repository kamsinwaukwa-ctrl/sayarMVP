/**
 * Signup Page for Sayar WhatsApp Commerce Platform
 * Professional two-column layout with AuthLayout component
 */

import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import SignupForm from '../components/auth/SignupForm'
import AuthLayout from '../components/auth/AuthLayout'

const Signup = () => {
  const navigate = useNavigate()
  const { isAuthenticated, loading } = useAuth()

  useEffect(() => {
    if (isAuthenticated && !loading) {
      navigate('/dashboard', { replace: true })
    }
  }, [isAuthenticated, loading, navigate])

  const handleSignupError = (error: string) => {
    console.error('Signup error:', error)
  }

  if (isAuthenticated) {
    return null
  }


  return (
    <AuthLayout
      title="Create your account"
      description="Get started with Sayar WhatsApp Commerce Platform"
      footerText="Already have an account?"
      footerLink={{ text: "Sign in", href: "/login" }}
    >
      <SignupForm 
        onError={handleSignupError}
      />
    </AuthLayout>
  )
}

export default Signup