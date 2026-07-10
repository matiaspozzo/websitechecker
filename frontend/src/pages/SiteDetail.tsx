import { useEffect, useRef, useState } from "react"
import { Link, useParams } from "react-router-dom"
import { api } from "../api/client"
import type {
  DependencyAuditSummary,
  Incident,
  LatencyPoint,
  Site,
  WpInventory,
} from "../api/types"
import { IncidentTable } from "../components/IncidentTable"
import { LatencyChart } from "../components/LatencyChart"

// Checks retry with 5s/15s/30s backoff before giving up (uptime, then content
// does its own separate fetch+retry too), so a single check-now can legitimately
// take up to ~100s on a genuinely down site. Poll for a while instead of a single
// short-delay refresh, or "check now" looks like it did nothing.
const POLL_INTERVAL_MS = 5000
const POLL_DURATION_MS = 120_000

export function SiteDetail() {
  const { id } = useParams()
  const [site, setSite] = useState<Site | null>(null)
  const [incidents, setIncidents] = useState<Incident[]>([])
  const [latency, setLatency] = useState<LatencyPoint[]>([])
  const [wpInventory, setWpInventory] = useState<WpInventory | null>(null)
  const [audits, setAudits] = useState<DependencyAuditSummary[]>([])
  const [range, setRange] = useState<"7d" | "30d">("7d")
  const [message, setMessage] = useState<string | null>(null)
  const pollRef = useRef<{ interval: ReturnType<typeof setInterval>; timeout: ReturnType<typeof setTimeout> } | null>(null)

  function load() {
    if (!id) return
    api.get<Site>(`/sites/${id}`).then(setSite)
    api.get<Incident[]>(`/incidents?site_id=${id}`).then(setIncidents)
    api.get<LatencyPoint[]>(`/sites/${id}/latency?range=${range}`).then(setLatency)
    api.get<DependencyAuditSummary[]>(`/sites/${id}/dependency-audits`).then(setAudits)
    api.get<WpInventory>(`/sites/${id}/wp-inventory`).then(setWpInventory)
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id, range])

  useEffect(() => {
    return () => {
      if (pollRef.current) {
        clearInterval(pollRef.current.interval)
        clearTimeout(pollRef.current.timeout)
      }
    }
  }, [])

  async function checkNow() {
    if (!id) return
    if (pollRef.current) {
      clearInterval(pollRef.current.interval)
      clearTimeout(pollRef.current.timeout)
    }

    setMessage("Check started — this can take up to ~100s on a down site (retry/backoff before giving up)…")
    await api.post(`/sites/${id}/check-now`)

    const interval = setInterval(load, POLL_INTERVAL_MS)
    const timeout = setTimeout(() => {
      clearInterval(interval)
      pollRef.current = null
      setMessage(null)
      load()
    }, POLL_DURATION_MS)
    pollRef.current = { interval, timeout }
  }

  async function silence() {
    if (!id) return
    const hours = Number(prompt("Silence for how many hours?", "4"))
    if (!hours) return
    await api.post(`/sites/${id}/silence`, { hours })
    setMessage(`Silenced for ${hours}h`)
  }

  if (!site) {
    return <div className="mx-auto max-w-4xl px-4 py-6 font-mono text-sm text-ink-muted">Loading…</div>
  }

  return (
    <div className="mx-auto max-w-4xl px-4 py-6">
      <div className="mb-4 flex items-start justify-between">
        <div>
          <h1 className="font-mono text-base font-semibold text-ink">{site.name}</h1>
          <a href={site.url} target="_blank" rel="noreferrer" className="font-mono text-xs text-ink-muted underline">
            {site.url}
          </a>
        </div>
        <div className="flex gap-2">
          <button onClick={checkNow} className="rounded bg-accent px-3 py-1.5 font-mono text-xs font-medium text-bg">
            check now
          </button>
          <button onClick={silence} className="rounded border border-border px-3 py-1.5 font-mono text-xs text-ink-muted">
            silence
          </button>
          <Link
            to={`/sites/${site.id}/edit`}
            className="rounded border border-border px-3 py-1.5 font-mono text-xs text-ink-muted"
          >
            edit
          </Link>
        </div>
      </div>

      {message && <p className="mb-3 font-mono text-xs text-ink-muted">{message}</p>}

      <section className="mb-6 rounded-lg border border-border bg-surface p-4">
        <div className="mb-2 flex items-center justify-between">
          <h2 className="font-mono text-sm font-medium text-ink">Latency</h2>
          <div className="flex gap-1 font-mono text-xs">
            {(["7d", "30d"] as const).map((r) => (
              <button
                key={r}
                onClick={() => setRange(r)}
                className={`rounded px-2 py-1 ${range === r ? "bg-accent text-bg" : "text-ink-muted"}`}
              >
                {r}
              </button>
            ))}
          </div>
        </div>
        <LatencyChart points={latency} />
      </section>

      {site.type === "wordpress" && site.monitoring_mode === "full" && (
        <section className="mb-6 rounded-lg border border-border bg-surface p-4">
          <h2 className="mb-2 font-mono text-sm font-medium text-ink">WordPress inventory</h2>
          {wpInventory?.snapshot ? (
            <>
              <p className="mb-2 font-mono text-xs text-ink-muted">
                core {wpInventory.snapshot.core_version}
                {wpInventory.snapshot.core_update_available && ` → ${wpInventory.snapshot.core_update_available} available`}
                {" · PHP "}
                {wpInventory.snapshot.php_version}
              </p>
              <table className="w-full font-mono text-xs">
                <thead>
                  <tr className="text-left text-ink-muted">
                    <th className="py-1 font-normal">Plugin</th>
                    <th className="py-1 font-normal">Installed</th>
                    <th className="py-1 font-normal">Available</th>
                  </tr>
                </thead>
                <tbody>
                  {wpInventory.snapshot.plugins.map((p) => (
                    <tr key={p.slug} className="border-t border-border/60">
                      <td className="py-1 text-ink">{p.slug}</td>
                      <td className="py-1 text-ink-muted">{p.installed}</td>
                      <td className={`py-1 ${p.available && p.available !== p.installed ? "text-status-warning" : "text-ink-muted"}`}>
                        {p.available ?? "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          ) : site.mu_plugin_token ? (
            <p className="font-mono text-xs text-status-warning">
              No inventory data yet. If this doesn't resolve after "check now", the mu-plugin's
              report endpoint likely isn't reachable — check the incident history below, and see{" "}
              <code className="text-ink">agents/wp-mu-plugin/README.md</code> to verify install.
            </p>
          ) : (
            <p className="font-mono text-xs text-ink-muted">
              No mu-plugin token configured for this site —{" "}
              <Link to={`/sites/${site.id}/edit`} className="text-accent underline">
                add one
              </Link>{" "}
              to enable WordPress inventory checks.
            </p>
          )}
        </section>
      )}

      {site.type !== "wordpress" && audits.length > 0 && (
        <section className="mb-6 rounded-lg border border-border bg-surface p-4">
          <h2 className="mb-2 font-mono text-sm font-medium text-ink">Dependency audits</h2>
          <ul className="space-y-1 font-mono text-xs">
            {audits.map((a) => (
              <li key={a.id} className="flex justify-between text-ink-muted">
                <span>{new Date(a.timestamp).toLocaleString()} ({a.tool})</span>
                <span className={a.high_critical_count > 0 ? "text-status-critical" : "text-status-up"}>
                  {a.summary}
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}

      <section className="rounded-lg border border-border bg-surface p-4">
        <h2 className="mb-2 font-mono text-sm font-medium text-ink">Incident history</h2>
        <IncidentTable incidents={incidents} />
      </section>
    </div>
  )
}
