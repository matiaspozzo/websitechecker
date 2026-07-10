import { Link } from "react-router-dom"
import type { SiteDashboardEntry } from "../api/types"
import {
  daysUntil,
  domainColorClass,
  formatCertDays,
  formatLatency,
  formatPct,
  sslColorClass,
  sslLabel,
} from "../lib/siteFormat"
import { StatusBadge } from "./StatusBadge"

export function SiteTable({ sites }: { sites: SiteDashboardEntry[] }) {
  if (sites.length === 0) {
    return <div className="font-mono text-sm text-ink-muted">No sites yet.</div>
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-border bg-surface">
      <table className="w-full min-w-[820px] border-collapse font-mono text-sm">
        <thead>
          <tr className="border-b border-border text-left text-xs uppercase tracking-wide text-ink-muted">
            <th className="px-4 py-2 font-normal">Status</th>
            <th className="px-2 py-2 font-normal">Name</th>
            <th className="px-2 py-2 font-normal">24h</th>
            <th className="px-2 py-2 font-normal">7d</th>
            <th className="px-2 py-2 font-normal">Latency</th>
            <th className="px-2 py-2 font-normal">SSL</th>
            <th className="px-2 py-2 font-normal">Domain</th>
            <th className="px-2 py-2 font-normal">Vuln</th>
            <th className="px-2 py-2 font-normal">Updates</th>
            <th className="px-2 py-2 pr-4 font-normal">Incidents</th>
          </tr>
        </thead>
        <tbody>
          {sites.map((site) => {
            const sslDays = daysUntil(site.next_ssl_expiry)
            const domainDays = daysUntil(site.next_domain_expiry)
            return (
              <tr key={site.id} className="border-b border-border/60 last:border-b-0 hover:bg-surface-hover">
                <td className="px-4 py-2">
                  <StatusBadge status={site.status} />
                </td>
                <td className="px-2 py-2">
                  <Link to={`/sites/${site.id}`} className="text-ink hover:text-accent">
                    {site.name}
                  </Link>
                  {site.monitoring_mode === "basic" && (
                    <span className="ml-1.5 rounded border border-border px-1 py-0.5 text-[10px] uppercase text-ink-muted">
                      basic
                    </span>
                  )}
                  <div className="truncate text-xs text-ink-muted">{site.url}</div>
                </td>
                <td className="px-2 py-2 text-ink-muted">{formatPct(site.uptime_24h_pct)}</td>
                <td className="px-2 py-2 text-ink-muted">{formatPct(site.uptime_7d_pct)}</td>
                <td className="px-2 py-2 text-ink-muted">{formatLatency(site.avg_latency_ms)}</td>
                <td className={`px-2 py-2 ${sslColorClass(site.ssl_valid, sslDays)}`} title={site.ssl_error ?? undefined}>
                  {sslLabel(site.ssl_valid, sslDays)}
                </td>
                <td className={`px-2 py-2 ${domainColorClass(domainDays)}`}>{formatCertDays(domainDays)}</td>
                <td className="px-2 py-2">
                  {site.vulnerable_plugin_count > 0 ? (
                    <span className="text-status-critical">{site.vulnerable_plugin_count}</span>
                  ) : (
                    <span className="text-ink-muted">—</span>
                  )}
                </td>
                <td className="px-2 py-2">
                  {site.outdated_plugin_count > 0 ? (
                    <span className="text-status-warning">{site.outdated_plugin_count}</span>
                  ) : (
                    <span className="text-ink-muted">—</span>
                  )}
                </td>
                <td className="px-2 py-2 pr-4">
                  {site.open_incident_count > 0 ? (
                    <span className="text-status-down">{site.open_incident_count} open</span>
                  ) : (
                    <span className="text-ink-muted">—</span>
                  )}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
