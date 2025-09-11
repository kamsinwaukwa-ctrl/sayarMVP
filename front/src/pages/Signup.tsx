/**
 * Signup Page for Sayar WhatsApp Commerce Platform
 * Pure Tailwind implementation
 */

import { useEffect, useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import SignupForm from '../components/auth/SignupForm'

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
      <div className="min-h-screen bg-white flex flex-col justify-center py-12 sm:px-6 lg:px-8">
        <div className="sm:mx-auto sm:w-full sm:max-w-md">
          <div className="bg-white py-8 px-4 shadow sm:rounded-lg sm:px-10 border border-gray-200 text-center">
            <div className="flex justify-center mb-4">
              <svg className="h-16 w-16 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            
            <h2 className="text-2xl font-bold text-gray-900 mb-2">
              Welcome to Sayar!
            </h2>
            
            <p className="text-gray-600 mb-6">
              Your account has been created successfully.
            </p>
            
            <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-md">
              <p className="text-sm">Redirecting you to your dashboard...</p>
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-white flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        {/* Logo */}
        <div className="flex justify-center">
          <img src="/logo.png" alt="Sayar" className="h-12 w-auto" />
        </div>
        
        <h2 className="mt-6 text-center text-3xl font-bold tracking-tight text-gray-900">
          Create your account
        </h2>
        <p className="mt-2 text-center text-sm text-gray-600">
          Or{' '}
          <Link
            to="/login"
            className="font-medium text-blue-600 hover:text-blue-500"
          >
            sign in to your existing account
          </Link>
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-white py-8 px-4 shadow sm:rounded-lg sm:px-10 border border-gray-200">
          <SignupForm 
            onSuccess={handleSignupSuccess}
            onError={handleSignupError}
          />
        </div>
      </div>
    </div>
  )
}

export default Signup