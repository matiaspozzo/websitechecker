import type { ReactNode } from "react"
import { Navigate, Route, Routes, useLocation } from "react-router-dom"
import { AuthProvider, useAuth } from "./auth"
import { Nav } from "./components/layout/Nav"
import { Dashboard } from "./pages/Dashboard"
import { Incidents } from "./pages/Incidents"
import { Login } from "./pages/Login"
import { Settings } from "./pages/Settings"
import { SiteDetail } from "./pages/SiteDetail"
import { SiteForm } from "./pages/SiteForm"

function RequireAuth({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth()
  const location = useLocation()

  if (loading) {
    return <div className="flex min-h-screen items-center justify-center font-mono text-sm text-ink-muted">Loading…</div>
  }
  if (!user) {
    return <Navigate to="/login" state={{ from: location.pathname }} replace />
  }
  return <>{children}</>
}

function AppShell() {
  return (
    <RequireAuth>
      <Nav />
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/sites/new" element={<SiteForm />} />
        <Route path="/sites/:id/edit" element={<SiteForm />} />
        <Route path="/sites/:id" element={<SiteDetail />} />
        <Route path="/incidents" element={<Incidents />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </RequireAuth>
  )
}

function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/*" element={<AppShell />} />
      </Routes>
    </AuthProvider>
  )
}

export default App
