/**
 * Signup Page for Sayar WhatsApp Commerce Platform
 * Professional two-column layout with AuthLayout component
 */

import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import SignupForm from '../components/auth/SignupForm'
import AuthLayout from '../components/auth/AuthLayout'

const Signup = () => {
  const navigate = useNavigate()
  const { isAuthenticated, loading } = useAuth()
  const [success, setSuccess] = useState(false)

  useEffect(() => {
    if (isAuthenticated && !loading) {
      navigate('/dashboard', { replace: true })
    }
  }, [isAuthenticated, loading, navigate])

  const handleSignupSuccess = () => {
    setSuccess(true)
    setTimeout(() => {
      navigate('/dashboard', { replace: true })
    }, 2000)
  }

  const handleSignupError = (error: string) => {
    console.error('Signup error:', error)
  }

  if (isAuthenticated) {
    return null
  }

  if (success) {
    return (
      <AuthLayout
        title="Welcome to Sayar!"
        description="Your account has been created successfully"
        footerText=""
      >
        <div className="text-center space-y-6">
          <div className="flex justify-center mb-6">
            <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center">
              <svg className="h-8 w-8 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
          </div>
          
          <div className="space-y-2">
            <h3 className="text-lg font-semibold text-gray-900">Account Created Successfully</h3>
            <p className="text-gray-600">
              You can now start building your WhatsApp commerce experience.
            </p>
          </div>
          
          <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-lg">
            <p className="text-sm">Redirecting you to your dashboard...</p>
          </div>
        </div>
      </AuthLayout>
    )
  }

  return (
    <AuthLayout
      title="Create your account"
      description="Get started with Sayar WhatsApp Commerce Platform"
      footerText="Already have an account?"
      footerLink={{ text: "Sign in", href: "/login" }}
    >
      <SignupForm 
        onSuccess={handleSignupSuccess}
        onError={handleSignupError}
      />
    </AuthLayout>
  )
}

export default Signup