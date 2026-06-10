import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider } from './features/auth/AuthProvider'
import { ProtectedRoute } from './features/auth/ProtectedRoute'
import { WorkspaceProvider } from './features/workspace/WorkspaceProvider'
import './App.css'
import { DesignGallery } from './designs/DesignGallery'
import { AppShell } from './pages/AppShell'
import { AuthCallbackPage } from './pages/AuthCallbackPage'
import { LoginPage } from './pages/LoginPage'
import {
  DashboardPage,
  IntellexPage,
  MathesysPage,
  ProjectsPage,
  QnGenPage,
  SourcesPage,
} from './pages/WorkspacePages'

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/" element={<Navigate to="/app" replace />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/auth/callback" element={<AuthCallbackPage />} />
          <Route path="/designs" element={<DesignGallery />} />

          <Route element={<ProtectedRoute />}>
            <Route
              path="/app"
              element={
                <WorkspaceProvider>
                  <AppShell />
                </WorkspaceProvider>
              }
            >
              <Route index element={<DashboardPage />} />
              <Route path="projects" element={<ProjectsPage />} />
              <Route path="sources" element={<SourcesPage />} />
              <Route path="intellex" element={<IntellexPage />} />
              <Route path="mathesys" element={<MathesysPage />} />
              <Route path="qngen" element={<QnGenPage />} />
            </Route>
          </Route>

          <Route path="*" element={<Navigate to="/app" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}

export default App
