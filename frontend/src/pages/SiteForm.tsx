import { type FormEvent, useEffect, useState } from "react"
import { useNavigate, useParams } from "react-router-dom"
import { api, ApiError } from "../api/client"
import type { MonitoringMode, Site, SiteInput, SiteType } from "../api/types"

const EMPTY: SiteInput = {
  name: "",
  client_name: "",
  url: "",
  type: "wordpress",
  monitoring_mode: "full",
  check_interval_seconds: 300,
  expected_keyword: "",
  active: true,
  mu_plugin_token: "",
  health_endpoint_url: "",
  ssh_host: "",
  ssh_user: "",
  ssh_key_path: "",
  ssh_project_path: "",
  audit_fetch_url: "",
  audit_fetch_token: "",
  notes: "",
}

function inputClass() {
  return "w-full rounded border border-border bg-bg px-3 py-2 font-mono text-sm text-ink outline-none focus:border-accent"
}

function labelClass() {
  return "mb-1 block font-mono text-xs uppercase tracking-wide text-ink-muted"
}

export function SiteForm() {
  const { id } = useParams()
  const isEdit = Boolean(id)
  const navigate = useNavigate()
  const [form, setForm] = useState<SiteInput>(EMPTY)
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [existingClients, setExistingClients] = useState<string[]>([])

  useEffect(() => {
    if (!id) return
    api.get<Site>(`/sites/${id}`).then((site) => setForm(site))
  }, [id])

  useEffect(() => {
    api.get<Site[]>("/sites").then((sites) => {
      const names = Array.from(new Set(sites.map((s) => s.client_name).filter((n): n is string => Boolean(n))))
      setExistingClients(names.sort())
    })
  }, [])

  function set<K extends keyof SiteInput>(key: K, value: SiteInput[K]) {
    setForm((f) => ({ ...f, [key]: value }))
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      if (isEdit) {
        await api.put(`/sites/${id}`, form)
      } else {
        await api.post("/sites", form)
      }
      navigate("/")
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to save site")
    } finally {
      setSubmitting(false)
    }
  }

  async function handleDelete() {
    if (!id || !confirm("Delete this site? This removes its history too.")) return
    await api.delete(`/sites/${id}`)
    navigate("/")
  }

  return (
    <div className="mx-auto max-w-2xl px-4 py-6">
      <h1 className="mb-4 font-mono text-base font-semibold text-ink">
        {isEdit ? "Edit site" : "Add site"}
      </h1>

      <form onSubmit={handleSubmit} className="space-y-4 rounded-lg border border-border bg-surface p-5">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className={labelClass()}>Name</label>
            <input className={inputClass()} value={form.name} onChange={(e) => set("name", e.target.value)} required />
          </div>
          <div>
            <label className={labelClass()}>Client</label>
            <input
              className={inputClass()}
              value={form.client_name ?? ""}
              onChange={(e) => set("client_name", e.target.value)}
              placeholder="e.g. Acme Corp"
              list="existing-clients"
            />
            <datalist id="existing-clients">
              {existingClients.map((c) => (
                <option key={c} value={c} />
              ))}
            </datalist>
          </div>
        </div>

        <div>
          <label className={labelClass()}>URL</label>
          <input
            className={inputClass()}
            value={form.url}
            onChange={(e) => set("url", e.target.value)}
            placeholder="https://example.com"
            required
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className={labelClass()}>Type</label>
            <select
              className={inputClass()}
              value={form.type}
              onChange={(e) => set("type", e.target.value as SiteType)}
            >
              <option value="wordpress">WordPress</option>
              <option value="laravel">Laravel</option>
              <option value="nextjs">Next.js</option>
            </select>
          </div>
          <div>
            <label className={labelClass()}>Check interval (s)</label>
            <input
              type="number"
              min={30}
              className={inputClass()}
              value={form.check_interval_seconds}
              onChange={(e) => set("check_interval_seconds", Number(e.target.value))}
            />
          </div>
        </div>

        <div>
          <label className={labelClass()}>Monitoring</label>
          <select
            className={inputClass()}
            value={form.monitoring_mode}
            onChange={(e) => set("monitoring_mode", e.target.value as MonitoringMode)}
          >
            <option value="full">Full (uptime, content, SSL/domain, {form.type === "wordpress" ? "WP inventory" : "deps audit"}, blacklist)</option>
            <option value="basic">Basic (uptime + SSL/domain expiry only)</option>
          </select>
        </div>

        {form.monitoring_mode === "full" && (
          <div>
            <label className={labelClass()}>Expected keyword</label>
            <input
              className={inputClass()}
              value={form.expected_keyword ?? ""}
              onChange={(e) => set("expected_keyword", e.target.value)}
              placeholder="text expected in the page HTML"
            />
          </div>
        )}

        <label className="flex items-center gap-2 font-mono text-sm text-ink">
          <input
            type="checkbox"
            checked={form.active}
            onChange={(e) => set("active", e.target.checked)}
          />
          active
        </label>

        {form.monitoring_mode === "full" && form.type === "wordpress" && (
          <div>
            <label className={labelClass()}>mu-plugin token</label>
            <input
              className={inputClass()}
              value={form.mu_plugin_token ?? ""}
              onChange={(e) => set("mu_plugin_token", e.target.value)}
              placeholder="matches SITEWATCH_TOKEN in wp-config.php"
            />
          </div>
        )}

        {form.monitoring_mode === "full" && form.type !== "wordpress" && (
          <>
            <div>
              <label className={labelClass()}>Health endpoint URL (optional)</label>
              <input
                className={inputClass()}
                value={form.health_endpoint_url ?? ""}
                onChange={(e) => set("health_endpoint_url", e.target.value)}
                placeholder="https://example.com/api/health"
              />
            </div>

            <fieldset className="rounded border border-border p-3">
              <legend className="px-1 font-mono text-xs uppercase tracking-wide text-ink-muted">
                Dependency audit via SSH (optional)
              </legend>
              <div className="grid grid-cols-2 gap-3">
                <input
                  className={inputClass()}
                  placeholder="ssh host"
                  value={form.ssh_host ?? ""}
                  onChange={(e) => set("ssh_host", e.target.value)}
                />
                <input
                  className={inputClass()}
                  placeholder="ssh user"
                  value={form.ssh_user ?? ""}
                  onChange={(e) => set("ssh_user", e.target.value)}
                />
                <input
                  className={inputClass()}
                  placeholder="ssh key path (on SiteWatch server)"
                  value={form.ssh_key_path ?? ""}
                  onChange={(e) => set("ssh_key_path", e.target.value)}
                />
                <input
                  className={inputClass()}
                  placeholder="project path on remote"
                  value={form.ssh_project_path ?? ""}
                  onChange={(e) => set("ssh_project_path", e.target.value)}
                />
              </div>
            </fieldset>

            <fieldset className="rounded border border-border p-3">
              <legend className="px-1 font-mono text-xs uppercase tracking-wide text-ink-muted">
                or: fetch pre-generated audit JSON (no SSH)
              </legend>
              <div className="grid grid-cols-2 gap-3">
                <input
                  className={inputClass()}
                  placeholder="audit JSON URL"
                  value={form.audit_fetch_url ?? ""}
                  onChange={(e) => set("audit_fetch_url", e.target.value)}
                />
                <input
                  className={inputClass()}
                  placeholder="token (X-SiteWatch-Token)"
                  value={form.audit_fetch_token ?? ""}
                  onChange={(e) => set("audit_fetch_token", e.target.value)}
                />
              </div>
            </fieldset>
          </>
        )}

        <div>
          <label className={labelClass()}>Notes</label>
          <textarea
            className={inputClass()}
            rows={3}
            value={form.notes ?? ""}
            onChange={(e) => set("notes", e.target.value)}
          />
        </div>

        {error && <p className="font-mono text-xs text-status-critical">{error}</p>}

        <div className="flex items-center justify-between pt-2">
          <div className="flex gap-2">
            <button
              type="submit"
              disabled={submitting}
              className="rounded bg-accent px-4 py-2 font-mono text-sm font-medium text-bg disabled:opacity-50"
            >
              {submitting ? "saving..." : "save"}
            </button>
            <button
              type="button"
              onClick={() => navigate("/")}
              className="rounded border border-border px-4 py-2 font-mono text-sm text-ink-muted"
            >
              cancel
            </button>
          </div>
          {isEdit && (
            <button
              type="button"
              onClick={handleDelete}
              className="rounded border border-status-critical/40 px-4 py-2 font-mono text-sm text-status-critical"
            >
              delete
            </button>
          )}
        </div>
      </form>
    </div>
  )
}
