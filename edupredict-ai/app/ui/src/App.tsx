import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import LandingPage from './pages/LandingPage'
import LenderDashboard from './pages/LenderDashboard'
import StudentPortal from './pages/StudentPortal'
import AdminOps from './pages/AdminOps'
import ProtectedRoute from './components/ProtectedRoute'

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        
        {/* Protected Lender Route */}
        <Route 
          path="/lender" 
          element={
            <ProtectedRoute requireRole="lender">
              <LenderDashboard />
            </ProtectedRoute>
          } 
        />
        
        {/* Protected Admin Route */}
        <Route 
          path="/admin" 
          element={
            <ProtectedRoute requireRole="admin">
              <AdminOps />
            </ProtectedRoute>
          } 
        />
        
        {/* Student Portal (may have demo mode without auth) */}
        <Route path="/student" element={<StudentPortal />} />
      </Routes>
    </Router>
  )
}

export default App
