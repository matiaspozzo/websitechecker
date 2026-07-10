import { useEffect, useMemo, useState } from "react"
import { api } from "../api/client"
import type { CheckType, Incident, Site } from "../api/types"
import { IncidentTable } from "../components/IncidentTable"

const CHECK_TYPES: CheckType[] = [
  "uptime",
  "health",
  "content",
  "redirect",
  "ssl",
  "domain",
  "wp_cve",
  "new_admin",
  "dependency_cve",
  "blacklist",
]

export function Incidents() {
  const [sites, setSites] = useState<Site[]>([])
  const [incidents, setIncidents] = useState<Incident[]>([])
  const [siteId, setSiteId] = useState<string>("")
  const [checkType, setCheckType] = useState<string>("")
  const [openOnly, setOpenOnly] = useState(false)

  useEffect(() => {
    api.get<Site[]>("/sites").then(setSites)
  }, [])

  useEffect(() => {
    const params = new URLSearchParams()
    if (siteId) params.set("site_id", siteId)
    if (checkType) params.set("check_type", checkType)
    if (openOnly) params.set("open", "true")
    api.get<Incident[]>(`/incidents?${params.toString()}`).then(setIncidents)
  }, [siteId, checkType, openOnly])

  const siteNameById = useMemo(() => {
    const map = new Map<number, string>()
    sites.forEach((s) => map.set(s.id, s.name))
    return map
  }, [sites])

  return (
    <div className="mx-auto max-w-6xl px-4 py-6">
      <h1 className="mb-4 font-mono text-base font-semibold text-ink">Incidents</h1>

      <div className="mb-4 flex flex-wrap items-center gap-3 font-mono text-sm">
        <select
          className="rounded border border-border bg-surface px-2 py-1.5 text-ink"
          value={siteId}
          onChange={(e) => setSiteId(e.target.value)}
        >
          <option value="">All sites</option>
          {sites.map((s) => (
            <option key={s.id} value={s.id}>
              {s.name}
            </option>
          ))}
        </select>

        <select
          className="rounded border border-border bg-surface px-2 py-1.5 text-ink"
          value={checkType}
          onChange={(e) => setCheckType(e.target.value)}
        >
          <option value="">All checks</option>
          {CHECK_TYPES.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>

        <label className="flex items-center gap-1.5 text-ink-muted">
          <input type="checkbox" checked={openOnly} onChange={(e) => setOpenOnly(e.target.checked)} />
          open only
        </label>
      </div>

      <div className="rounded-lg border border-border bg-surface p-4">
        <IncidentTable incidents={incidents} showSite={(id) => siteNameById.get(id) ?? `#${id}`} />
      </div>
    </div>
  )
}
