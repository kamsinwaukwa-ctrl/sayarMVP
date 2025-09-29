import { Routes, Route } from 'react-router-dom'
import { AuthProvider } from '@/context/AuthProvider'
import Dashboard from '@/pages/Dashboard'
import Login from '@/pages/Login'
import Signup from '@/pages/Signup'
import Logout from '@/pages/Logout'
import Settings from '@/pages/Settings'
import ProtectedRoute from '@/components/ProtectedRoute'
//import UIShowcase from '@/pages/_dev/ui'

function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/signup" element={<Signup />} />
        <Route path="/logout" element={<Logout />} />

        {/* Protected Routes */}
        <Route element={<ProtectedRoute />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/dashboard" element={<Dashboard />} />

          {/* Settings Routes */}
          <Route path="/settings" element={<Settings />} />
          <Route path="/settings/:tab" element={<Settings />} />

        </Route>

        {/* Development Routes */}
        {/*<Route path="_dev/ui" element={<UIShowcase />} />*/}
      </Routes>
    </AuthProvider>
  )
}

export default App