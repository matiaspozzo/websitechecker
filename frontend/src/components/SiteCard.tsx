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
import { stackCardStyle, stackColor, STACK_LABELS } from "../lib/stackFormat"
import { Sparkline } from "./Sparkline"
import { StatusBadge } from "./StatusBadge"

export function SiteCard({ site }: { site: SiteDashboardEntry }) {
  const sslDays = daysUntil(site.next_ssl_expiry)
  const domainDays = daysUntil(site.next_domain_expiry)

  return (
    <Link
      to={`/sites/${site.id}`}
      className="block rounded-lg border border-border bg-surface p-4 transition hover:bg-surface-hover"
      style={stackCardStyle(site.type)}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="flex items-center gap-1.5">
            {site.client_name && (
              <span className="truncate font-mono text-[10px] uppercase tracking-wide text-accent-dim">
                {site.client_name}
              </span>
            )}
            <span className="shrink-0 font-mono text-[10px] uppercase tracking-wide" style={{ color: stackColor(site.type) }}>
              {site.client_name && "·"} {STACK_LABELS[site.type]}
            </span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="truncate font-medium text-ink">{site.name}</span>
            {site.monitoring_mode === "basic" && (
              <span className="shrink-0 rounded border border-border px-1 py-0.5 font-mono text-[10px] uppercase text-ink-muted">
                basic
              </span>
            )}
          </div>
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

      <div className="mt-3 flex items-center gap-3 font-mono text-[11px]">
        <span className={sslColorClass(site.ssl_valid, sslDays)} title={site.ssl_error ?? undefined}>
          {sslLabel(site.ssl_valid, sslDays)}
        </span>
        <span className={domainColorClass(domainDays)}>domain {formatCertDays(domainDays)}</span>
      </div>

      {(site.core_update_available ||
        site.vulnerable_plugin_count > 0 ||
        site.outdated_plugin_count > 0 ||
        site.open_incident_count > 0 ||
        site.mu_plugin_outdated ||
        site.mu_plugin_version ||
        site.has_wp_snapshot) && (
        <div className="mt-2 flex flex-wrap gap-2 font-mono text-[11px]">
          {site.mu_plugin_outdated ? (
            <span
              className="rounded border border-border px-1.5 py-0.5 text-ink-muted"
              title={`Installed: ${site.mu_plugin_version ?? "unknown (pre-1.1.0)"} — re-upload sitewatch-report.php`}
            >
              mu-plugin outdated
            </span>
          ) : (
            site.mu_plugin_version && (
              <span
                className="rounded border border-status-up/40 px-1.5 py-0.5 text-status-up"
                title={`mu-plugin v${site.mu_plugin_version}`}
              >
                mu-plugin up to date
              </span>
            )
          )}
          {site.core_update_available ? (
            <span className="rounded border border-status-warning/40 px-1.5 py-0.5 text-status-warning">
              core update: {site.core_update_available}
            </span>
          ) : (
            site.has_wp_snapshot && (
              <span className="rounded border border-status-up/40 px-1.5 py-0.5 text-status-up">core up to date</span>
            )
          )}
          {site.vulnerable_plugin_count > 0 ? (
            <span className="rounded border border-status-critical/40 px-1.5 py-0.5 text-status-critical">
              {site.vulnerable_plugin_count} vuln plugin{site.vulnerable_plugin_count > 1 ? "s" : ""}
            </span>
          ) : (
            site.has_wp_snapshot && (
              <span className="rounded border border-status-up/40 px-1.5 py-0.5 text-status-up">no known vulnerabilities</span>
            )
          )}
          {site.outdated_plugin_count > 0 ? (
            <span className="rounded border border-status-warning/40 px-1.5 py-0.5 text-status-warning">
              {site.outdated_plugin_count} plugin{site.outdated_plugin_count > 1 ? "s" : ""} to update
            </span>
          ) : (
            site.has_wp_snapshot && (
              <span className="rounded border border-status-up/40 px-1.5 py-0.5 text-status-up">plugins up to date</span>
            )
          )}
          {site.open_incident_count > 0 && (
            <span className="rounded border border-status-down/40 px-1.5 py-0.5 text-status-down">
              {site.open_incident_count} open incident{site.open_incident_count > 1 ? "s" : ""}
            </span>
          )}
        </div>
      )}
    </Link>
  )
}
