import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider } from './features/auth/AuthProvider'
import { ProtectedRoute } from './features/auth/ProtectedRoute'
import { WorkspaceProvider } from './features/workspace/WorkspaceProvider'
import './App.css'
import { AuthCallbackPage } from './pages/AuthCallbackPage'
import { ConsolePage } from './pages/ConsolePage'
import { LoginPage } from './pages/LoginPage'

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/" element={<Navigate to="/app" replace />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/auth/callback" element={<AuthCallbackPage />} />

          <Route element={<ProtectedRoute />}>
            <Route
              path="/app/*"
              element={
                <WorkspaceProvider>
                  <ConsolePage />
                </WorkspaceProvider>
              }
            />
          </Route>

          <Route path="*" element={<Navigate to="/app" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}

export default App
