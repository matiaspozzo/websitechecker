import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { api } from "../api/client"
import type { DashboardResponse } from "../api/types"
import { SiteCard } from "../components/SiteCard"

export function Dashboard() {
  const [data, setData] = useState<DashboardResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    function load() {
      api
        .get<DashboardResponse>("/dashboard")
        .then((res) => !cancelled && setData(res))
        .catch(() => !cancelled && setError("Failed to load dashboard"))
    }
    load()
    const interval = setInterval(load, 30_000)
    return () => {
      cancelled = true
      clearInterval(interval)
    }
  }, [])

  return (
    <div className="mx-auto max-w-6xl px-4 py-6">
      <div className="mb-4 flex items-center justify-between">
        <h1 className="font-mono text-base font-semibold text-ink">Sites</h1>
        <Link
          to="/sites/new"
          className="rounded bg-accent px-3 py-1.5 font-mono text-sm font-medium text-bg"
        >
          + add site
        </Link>
      </div>

      {error && <p className="font-mono text-sm text-status-critical">{error}</p>}

      {data && data.sites.length === 0 && (
        <p className="font-mono text-sm text-ink-muted">No sites yet. Add your first one.</p>
      )}

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {data?.sites.map((site) => <SiteCard key={site.id} site={site} />)}
      </div>
    </div>
  )
}
