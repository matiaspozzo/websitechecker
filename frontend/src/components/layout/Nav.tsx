import { NavLink } from "react-router-dom"
import { useAuth } from "../../auth"

const LINK_CLASS =
  "px-3 py-1.5 rounded font-mono text-sm text-ink-muted hover:text-ink transition"
const ACTIVE_CLASS = "text-accent"

export function Nav() {
  const { logout, user } = useAuth()

  return (
    <header className="border-b border-border bg-surface">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
        <div className="flex items-center gap-1">
          <span className="mr-3 font-mono text-sm font-semibold text-accent">SiteWatch</span>
          <NavLink to="/" end className={({ isActive }) => `${LINK_CLASS} ${isActive ? ACTIVE_CLASS : ""}`}>
            Dashboard
          </NavLink>
          <NavLink to="/incidents" className={({ isActive }) => `${LINK_CLASS} ${isActive ? ACTIVE_CLASS : ""}`}>
            Incidents
          </NavLink>
          <NavLink to="/settings" className={({ isActive }) => `${LINK_CLASS} ${isActive ? ACTIVE_CLASS : ""}`}>
            Settings
          </NavLink>
        </div>
        <div className="flex items-center gap-3 font-mono text-xs text-ink-muted">
          {user && <span>{user.username}</span>}
          <button
            onClick={() => logout()}
            className="rounded border border-border px-2 py-1 text-ink-muted hover:border-accent hover:text-accent transition"
          >
            log out
          </button>
        </div>
      </div>
    </header>
  )
}
