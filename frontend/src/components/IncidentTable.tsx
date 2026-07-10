import type { Incident } from "../api/types"

function formatDuration(openedAt: string, closedAt: string | null): string {
  const end = closedAt ? new Date(closedAt) : new Date()
  const ms = end.getTime() - new Date(openedAt).getTime()
  const minutes = Math.floor(ms / 60000)
  if (minutes < 60) return `${minutes}m`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}h ${minutes % 60}m`
  const days = Math.floor(hours / 24)
  return `${days}d ${hours % 24}h`
}

export function IncidentTable({ incidents, showSite }: { incidents: Incident[]; showSite?: (siteId: number) => string }) {
  if (incidents.length === 0) {
    return <div className="font-mono text-sm text-ink-muted">No incidents.</div>
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[560px] border-collapse font-mono text-sm">
        <thead>
          <tr className="border-b border-border text-left text-xs uppercase tracking-wide text-ink-muted">
            {showSite && <th className="py-2 pr-4 font-normal">Site</th>}
            <th className="py-2 pr-4 font-normal">Check</th>
            <th className="py-2 pr-4 font-normal">Severity</th>
            <th className="py-2 pr-4 font-normal">Cause</th>
            <th className="py-2 pr-4 font-normal">Opened</th>
            <th className="py-2 pr-4 font-normal">Duration</th>
            <th className="py-2 font-normal">Status</th>
          </tr>
        </thead>
        <tbody>
          {incidents.map((incident) => (
            <tr key={incident.id} className="border-b border-border/60 align-top">
              {showSite && <td className="py-2 pr-4 text-ink">{showSite(incident.site_id)}</td>}
              <td className="py-2 pr-4 text-ink-muted">{incident.check_type}</td>
              <td className="py-2 pr-4">
                <span
                  className={
                    incident.severity === "critical" ? "text-status-critical" : "text-status-warning"
                  }
                >
                  {incident.severity}
                </span>
              </td>
              <td className="max-w-[320px] py-2 pr-4 text-ink">{incident.cause}</td>
              <td className="py-2 pr-4 text-ink-muted">{new Date(incident.opened_at).toLocaleString()}</td>
              <td className="py-2 pr-4 text-ink-muted">{formatDuration(incident.opened_at, incident.closed_at)}</td>
              <td className="py-2">
                {incident.closed_at ? (
                  <span className="text-status-up">closed</span>
                ) : (
                  <span className="text-status-down">open</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
