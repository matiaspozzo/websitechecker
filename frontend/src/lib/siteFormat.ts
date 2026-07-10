export function formatPct(pct: number | null): string {
  return pct === null ? "—" : `${pct.toFixed(1)}%`
}

export function formatLatency(ms: number | null): string {
  return ms === null ? "—" : `${Math.round(ms)}ms`
}

export function daysUntil(iso: string | null): number | null {
  if (!iso) return null
  return Math.ceil((new Date(iso).getTime() - Date.now()) / (1000 * 60 * 60 * 24))
}

export function formatCertDays(days: number | null): string {
  if (days === null) return "—"
  return days < 0 ? `expired ${-days}d ago` : `${days}d`
}

export function sslLabel(sslValid: boolean | null, days: number | null): string {
  if (sslValid === null) return "SSL —"
  if (sslValid === false) return `SSL invalid (${formatCertDays(days)})`
  return `SSL ${formatCertDays(days)}`
}

export function sslColorClass(sslValid: boolean | null, days: number | null): string {
  if (sslValid === false) return "text-status-critical"
  if (days !== null && days <= 14) return "text-status-warning"
  return "text-ink-muted"
}

export function domainColorClass(days: number | null): string {
  if (days !== null && days <= 30) return "text-status-warning"
  return "text-ink-muted"
}
