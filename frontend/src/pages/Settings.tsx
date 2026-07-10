import { useEffect, useState } from "react"
import { api } from "../api/client"
import type { GlobalConfig, SuspiciousPattern, TrustedDomain } from "../api/types"

function inputClass() {
  return "w-full rounded border border-border bg-bg px-3 py-2 font-mono text-sm text-ink outline-none focus:border-accent"
}

function labelClass() {
  return "mb-1 block font-mono text-xs uppercase tracking-wide text-ink-muted"
}

export function Settings() {
  const [config, setConfig] = useState<GlobalConfig | null>(null)
  const [patterns, setPatterns] = useState<SuspiciousPattern[]>([])
  const [trustedDomains, setTrustedDomains] = useState<TrustedDomain[]>([])
  const [saved, setSaved] = useState(false)
  const [newPattern, setNewPattern] = useState("")
  const [newDomain, setNewDomain] = useState("")

  function load() {
    api.get<GlobalConfig>("/config").then(setConfig)
    api.get<SuspiciousPattern[]>("/config/patterns").then(setPatterns)
    api.get<TrustedDomain[]>("/config/trusted-domains").then(setTrustedDomains)
  }

  useEffect(load, [])

  function set<K extends keyof GlobalConfig>(key: K, value: GlobalConfig[K]) {
    setConfig((c) => (c ? { ...c, [key]: value } : c))
  }

  async function save() {
    if (!config) return
    await api.put("/config", config)
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  async function togglePattern(pattern: SuspiciousPattern) {
    await api.put(`/config/patterns/${pattern.id}`, { enabled: !pattern.enabled })
    load()
  }

  async function deletePattern(id: number) {
    await api.delete(`/config/patterns/${id}`)
    load()
  }

  async function addPattern() {
    if (!newPattern.trim()) return
    await api.post("/config/patterns", { pattern: newPattern, is_regex: false, enabled: true, severity: "critical" })
    setNewPattern("")
    load()
  }

  async function toggleTrustedDomain(domain: TrustedDomain) {
    await api.put(`/config/trusted-domains/${domain.id}`, { enabled: !domain.enabled })
    load()
  }

  async function deleteTrustedDomain(id: number) {
    await api.delete(`/config/trusted-domains/${id}`)
    load()
  }

  async function addTrustedDomain() {
    if (!newDomain.trim()) return
    await api.post("/config/trusted-domains", { domain: newDomain.trim(), enabled: true })
    setNewDomain("")
    load()
  }

  if (!config) {
    return <div className="mx-auto max-w-3xl px-4 py-6 font-mono text-sm text-ink-muted">Loading…</div>
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-6 space-y-6">
      <h1 className="font-mono text-base font-semibold text-ink">Settings</h1>

      <section className="rounded-lg border border-border bg-surface p-4 space-y-4">
        <h2 className="font-mono text-sm font-medium text-ink">Telegram &amp; digest</h2>

        <div>
          <label className={labelClass()}>Telegram chat ID</label>
          <input
            className={inputClass()}
            value={config.telegram_chat_id ?? ""}
            onChange={(e) => set("telegram_chat_id", e.target.value)}
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className={labelClass()}>Digest hour (0-23)</label>
            <input
              type="number"
              min={0}
              max={23}
              className={inputClass()}
              value={config.digest_hour}
              onChange={(e) => set("digest_hour", Number(e.target.value))}
            />
          </div>
          <div>
            <label className={labelClass()}>Timezone</label>
            <input
              className={inputClass()}
              value={config.digest_timezone}
              onChange={(e) => set("digest_timezone", e.target.value)}
            />
          </div>
        </div>

        <div>
          <label className={labelClass()}>Panel base URL</label>
          <input
            className={inputClass()}
            value={config.panel_base_url}
            onChange={(e) => set("panel_base_url", e.target.value)}
            placeholder="http://192.168.1.x:8000"
          />
        </div>
      </section>

      <section className="rounded-lg border border-border bg-surface p-4 space-y-4">
        <h2 className="font-mono text-sm font-medium text-ink">Alert thresholds (days before expiry)</h2>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className={labelClass()}>SSL</label>
            <input
              className={inputClass()}
              value={config.ssl_alert_days_json.join(",")}
              onChange={(e) => set("ssl_alert_days_json", e.target.value.split(",").map((v) => Number(v.trim())).filter((n) => !Number.isNaN(n)))}
            />
          </div>
          <div>
            <label className={labelClass()}>Domain</label>
            <input
              className={inputClass()}
              value={config.domain_alert_days_json.join(",")}
              onChange={(e) => set("domain_alert_days_json", e.target.value.split(",").map((v) => Number(v.trim())).filter((n) => !Number.isNaN(n)))}
            />
          </div>
        </div>
      </section>

      <section className="rounded-lg border border-border bg-surface p-4 space-y-4">
        <h2 className="font-mono text-sm font-medium text-ink">API keys</h2>
        <div>
          <label className={labelClass()}>WPScan API key</label>
          <input className={inputClass()} value={config.wpscan_api_key ?? ""} onChange={(e) => set("wpscan_api_key", e.target.value)} />
        </div>
        <div>
          <label className={labelClass()}>Google Safe Browsing API key</label>
          <input className={inputClass()} value={config.gsb_api_key ?? ""} onChange={(e) => set("gsb_api_key", e.target.value)} />
        </div>
        <div>
          <label className={labelClass()}>VirusTotal API key (optional)</label>
          <input className={inputClass()} value={config.vt_api_key ?? ""} onChange={(e) => set("vt_api_key", e.target.value)} />
        </div>
        <div>
          <label className={labelClass()}>Healthchecks.io URL</label>
          <input className={inputClass()} value={config.healthchecks_url ?? ""} onChange={(e) => set("healthchecks_url", e.target.value)} />
        </div>
      </section>

      <div className="flex items-center gap-3">
        <button onClick={save} className="rounded bg-accent px-4 py-2 font-mono text-sm font-medium text-bg">
          save
        </button>
        {saved && <span className="font-mono text-xs text-status-up">saved</span>}
      </div>

      <section className="rounded-lg border border-border bg-surface p-4 space-y-3">
        <h2 className="font-mono text-sm font-medium text-ink">Suspicious content patterns</h2>
        <ul className="space-y-2">
          {patterns.map((p) => (
            <li key={p.id} className="flex items-center justify-between gap-3 font-mono text-xs">
              <span className={`truncate ${p.enabled ? "text-ink" : "text-ink-muted line-through"}`}>
                {p.pattern}
                {p.description && <span className="text-ink-muted"> — {p.description}</span>}
              </span>
              <div className="flex shrink-0 gap-2">
                <button onClick={() => togglePattern(p)} className="rounded border border-border px-2 py-1 text-ink-muted">
                  {p.enabled ? "disable" : "enable"}
                </button>
                <button onClick={() => deletePattern(p.id)} className="rounded border border-status-critical/40 px-2 py-1 text-status-critical">
                  delete
                </button>
              </div>
            </li>
          ))}
        </ul>
        <div className="flex gap-2">
          <input
            className={inputClass()}
            placeholder="new pattern (literal substring)"
            value={newPattern}
            onChange={(e) => setNewPattern(e.target.value)}
          />
          <button onClick={addPattern} className="shrink-0 rounded bg-accent px-3 py-2 font-mono text-sm font-medium text-bg">
            add
          </button>
        </div>
      </section>

      <section className="rounded-lg border border-border bg-surface p-4 space-y-3">
        <h2 className="font-mono text-sm font-medium text-ink">Trusted embed domains</h2>
        <p className="font-mono text-xs text-ink-muted">
          Iframes and meta-refreshes pointing to these domains are never flagged as a possible
          compromise. If a legitimate embed on one of your sites gets flagged, add its domain here
          — the open incident will close itself on the next check.
        </p>
        <ul className="space-y-2">
          {trustedDomains.map((d) => (
            <li key={d.id} className="flex items-center justify-between gap-3 font-mono text-xs">
              <span className={`truncate ${d.enabled ? "text-ink" : "text-ink-muted line-through"}`}>
                {d.domain}
                {d.description && <span className="text-ink-muted"> — {d.description}</span>}
              </span>
              <div className="flex shrink-0 gap-2">
                <button onClick={() => toggleTrustedDomain(d)} className="rounded border border-border px-2 py-1 text-ink-muted">
                  {d.enabled ? "disable" : "enable"}
                </button>
                <button onClick={() => deleteTrustedDomain(d.id)} className="rounded border border-status-critical/40 px-2 py-1 text-status-critical">
                  delete
                </button>
              </div>
            </li>
          ))}
        </ul>
        <div className="flex gap-2">
          <input
            className={inputClass()}
            placeholder="domain (e.g. kuula.co)"
            value={newDomain}
            onChange={(e) => setNewDomain(e.target.value)}
          />
          <button onClick={addTrustedDomain} className="shrink-0 rounded bg-accent px-3 py-2 font-mono text-sm font-medium text-bg">
            add
          </button>
        </div>
      </section>
    </div>
  )
}
