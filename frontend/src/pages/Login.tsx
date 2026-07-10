import { type FormEvent, useState } from "react"
import { useLocation, useNavigate } from "react-router-dom"
import { ApiError } from "../api/client"
import { useAuth } from "../auth"

export function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [username, setUsername] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  const from = (location.state as { from?: string } | null)?.from ?? "/"

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      await login(username, password)
      navigate(from, { replace: true })
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Login failed")
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-bg px-4">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-sm rounded-lg border border-border bg-surface p-6"
      >
        <div className="mb-6 flex items-center gap-2">
          <img src="/wirall-logo.png" alt="Wirall Interactive" className="h-6 w-auto" />
          <span className="h-5 w-px bg-border" aria-hidden />
          <h1 className="font-mono text-lg font-semibold text-accent">SiteWatch</h1>
        </div>

        <label className="mb-3 block">
          <span className="mb-1 block font-mono text-xs uppercase tracking-wide text-ink-muted">
            Username
          </span>
          <input
            className="w-full rounded border border-border bg-bg px-3 py-2 font-mono text-sm text-ink outline-none focus:border-accent"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoFocus
            required
          />
        </label>

        <label className="mb-4 block">
          <span className="mb-1 block font-mono text-xs uppercase tracking-wide text-ink-muted">
            Password
          </span>
          <input
            type="password"
            className="w-full rounded border border-border bg-bg px-3 py-2 font-mono text-sm text-ink outline-none focus:border-accent"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </label>

        {error && <p className="mb-4 font-mono text-xs text-status-critical">{error}</p>}

        <button
          type="submit"
          disabled={submitting}
          className="w-full rounded bg-accent py-2 font-mono text-sm font-medium text-bg transition disabled:opacity-50"
        >
          {submitting ? "signing in..." : "sign in"}
        </button>
      </form>
    </div>
  )
}
