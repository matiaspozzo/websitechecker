import { useEffect, useMemo, useState } from "react"
import { Link } from "react-router-dom"
import { api } from "../api/client"
import type { DashboardResponse, SiteDashboardEntry, SiteType } from "../api/types"
import { SiteCard } from "../components/SiteCard"
import { SiteTable } from "../components/SiteTable"
import { STACK_LABELS, STACK_ORDER, stackColor } from "../lib/stackFormat"

type ViewMode = "card" | "list"

const VIEW_MODE_STORAGE_KEY = "sitewatch.dashboardView"
const UNASSIGNED = "(no client)"

function loadViewMode(): ViewMode {
  const stored = localStorage.getItem(VIEW_MODE_STORAGE_KEY)
  return stored === "list" ? "list" : "card"
}

export function Dashboard() {
  const [data, setData] = useState<DashboardResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [viewMode, setViewMode] = useState<ViewMode>(loadViewMode)
  const [clientFilter, setClientFilter] = useState<string>("")

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

  function selectViewMode(mode: ViewMode) {
    setViewMode(mode)
    localStorage.setItem(VIEW_MODE_STORAGE_KEY, mode)
  }

  const clients = useMemo(() => {
    if (!data) return []
    const names = new Set(data.sites.map((s) => s.client_name || UNASSIGNED))
    return Array.from(names).sort()
  }, [data])

  const filteredSites = useMemo(() => {
    if (!data) return []
    if (!clientFilter) return data.sites
    return data.sites.filter((s) => (s.client_name || UNASSIGNED) === clientFilter)
  }, [data, clientFilter])

  const groups = useMemo(() => {
    const byType = new Map<SiteType, SiteDashboardEntry[]>()
    for (const site of filteredSites) {
      const list = byType.get(site.type) ?? []
      list.push(site)
      byType.set(site.type, list)
    }
    return STACK_ORDER.map((type) => ({ type, sites: byType.get(type) ?? [] })).filter((g) => g.sites.length > 0)
  }, [filteredSites])

  return (
    <div className="mx-auto max-w-6xl px-4 py-6">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <h1 className="font-mono text-base font-semibold text-ink">Sites</h1>
        <div className="flex items-center gap-3">
          {clients.length > 1 && (
            <select
              className="rounded border border-border bg-surface px-2 py-1.5 font-mono text-xs text-ink"
              value={clientFilter}
              onChange={(e) => setClientFilter(e.target.value)}
            >
              <option value="">All clients</option>
              {clients.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          )}
          <div className="flex rounded border border-border font-mono text-xs">
            <button
              onClick={() => selectViewMode("card")}
              aria-pressed={viewMode === "card"}
              className={`px-2.5 py-1.5 ${viewMode === "card" ? "bg-accent text-bg" : "text-ink-muted"}`}
            >
              cards
            </button>
            <button
              onClick={() => selectViewMode("list")}
              aria-pressed={viewMode === "list"}
              className={`border-l border-border px-2.5 py-1.5 ${viewMode === "list" ? "bg-accent text-bg" : "text-ink-muted"}`}
            >
              list
            </button>
          </div>
          <Link
            to="/sites/new"
            className="rounded bg-accent px-3 py-1.5 font-mono text-sm font-medium text-bg"
          >
            + add site
          </Link>
        </div>
      </div>

      {error && <p className="font-mono text-sm text-status-critical">{error}</p>}

      {data && data.sites.length === 0 && (
        <p className="font-mono text-sm text-ink-muted">No sites yet. Add your first one.</p>
      )}

      {data && data.sites.length > 0 && filteredSites.length === 0 && (
        <p className="font-mono text-sm text-ink-muted">No sites for this client.</p>
      )}

      {groups.map(({ type, sites }) => (
        <section key={type} className="mb-6">
          <h2
            className="mb-2 flex items-center gap-2 font-mono text-xs font-semibold uppercase tracking-wide"
            style={{ color: stackColor(type) }}
          >
            <span className="inline-block h-2 w-2 rounded-full" style={{ backgroundColor: stackColor(type) }} />
            {STACK_LABELS[type]}
            <span className="font-normal text-ink-muted">({sites.length})</span>
          </h2>

          {viewMode === "card" ? (
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {sites.map((site) => (
                <SiteCard key={site.id} site={site} />
              ))}
            </div>
          ) : (
            <SiteTable sites={sites} />
          )}
        </section>
      ))}
    </div>
  )
}
