import { Link } from "react-router-dom"
import type { SiteDashboardEntry } from "../api/types"
import { Sparkline } from "./Sparkline"
import { StatusBadge } from "./StatusBadge"

function formatPct(pct: number | null): string {
  return pct === null ? "—" : `${pct.toFixed(1)}%`
}

function formatLatency(ms: number | null): string {
  return ms === null ? "—" : `${Math.round(ms)}ms`
}

function daysUntil(iso: string | null): number | null {
  if (!iso) return null
  return Math.ceil((new Date(iso).getTime() - Date.now()) / (1000 * 60 * 60 * 24))
}

export function SiteCard({ site }: { site: SiteDashboardEntry }) {
  const sslDays = daysUntil(site.next_ssl_expiry)
  const domainDays = daysUntil(site.next_domain_expiry)

  return (
    <Link
      to={`/sites/${site.id}`}
      className="block rounded-lg border border-border bg-surface p-4 transition hover:bg-surface-hover"
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="truncate font-medium text-ink">{site.name}</div>
          <div className="truncate font-mono text-xs text-ink-muted">{site.url}</div>
        </div>
        <StatusBadge status={site.status} />
      </div>

      <div className="mt-3 flex items-end justify-between">
        <div className="font-mono text-xs text-ink-muted">
          <div>
            24h: <span className="text-ink">{formatPct(site.uptime_24h_pct)}</span> · 7d:{" "}
            <span className="text-ink">{formatPct(site.uptime_7d_pct)}</span>
          </div>
          <div>latency: <span className="text-ink">{formatLatency(site.avg_latency_ms)}</span></div>
        </div>
        <Sparkline points={site.sparkline} />
      </div>

      <div className="mt-3 flex flex-wrap gap-2 font-mono text-[11px]">
        {sslDays !== null && sslDays <= 14 && (
          <span className="rounded border border-status-warning/40 px-1.5 py-0.5 text-status-warning">
            SSL {sslDays}d
          </span>
        )}
        {domainDays !== null && domainDays <= 30 && (
          <span className="rounded border border-status-warning/40 px-1.5 py-0.5 text-status-warning">
            domain {domainDays}d
          </span>
        )}
        {site.vulnerable_plugin_count > 0 && (
          <span className="rounded border border-status-critical/40 px-1.5 py-0.5 text-status-critical">
            {site.vulnerable_plugin_count} vuln plugin{site.vulnerable_plugin_count > 1 ? "s" : ""}
          </span>
        )}
        {site.open_incident_count > 0 && (
          <span className="rounded border border-status-down/40 px-1.5 py-0.5 text-status-down">
            {site.open_incident_count} open incident{site.open_incident_count > 1 ? "s" : ""}
          </span>
        )}
      </div>
    </Link>
  )
}
