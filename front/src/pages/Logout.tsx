import { useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '@/hooks/useAuth'

export default function Logout() {
  const { logout } = useAuth()
  const navigate = useNavigate()
  const hasLoggedOut = useRef(false)

  useEffect(() => {
    // Prevent multiple logout calls in StrictMode
    if (hasLoggedOut.current) return

    hasLoggedOut.current = true
    // Clear auth state and redirect to login
    logout()
    navigate('/login', { replace: true })
  }, [logout, navigate])

  return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="text-center">
        <h2 className="text-lg font-semibold">Logging out...</h2>
        <p className="text-muted-foreground">Please wait while we sign you out.</p>
      </div>
    </div>
  )
}

