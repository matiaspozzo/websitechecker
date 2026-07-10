export type SiteType = "wordpress" | "laravel" | "nextjs"
export type MonitoringMode = "full" | "basic"

export interface Site {
  id: number
  name: string
  client_name: string | null
  url: string
  type: SiteType
  monitoring_mode: MonitoringMode
  check_interval_seconds: number
  expected_keyword: string | null
  active: boolean
  mu_plugin_token: string | null
  health_endpoint_url: string | null
  ssh_host: string | null
  ssh_user: string | null
  ssh_key_path: string | null
  ssh_project_path: string | null
  audit_fetch_url: string | null
  audit_fetch_token: string | null
  notes: string | null
  expected_domain: string
  created_at: string
  updated_at: string
}

export type SiteInput = Omit<Site, "id" | "expected_domain" | "created_at" | "updated_at">

export type CheckType =
  | "uptime"
  | "health"
  | "content"
  | "redirect"
  | "ssl"
  | "domain"
  | "wp_cve"
  | "new_admin"
  | "dependency_cve"
  | "blacklist"

export type Severity = "warning" | "critical"

export interface Incident {
  id: number
  site_id: number
  check_type: CheckType
  severity: Severity
  opened_at: string
  closed_at: string | null
  cause: string
  detail_json: Record<string, unknown>
}

export interface SparklinePoint {
  timestamp: string
  latency_ms: number | null
  success: boolean
}

export type SiteStatus = "up" | "down" | "paused" | "unknown"

export interface SiteDashboardEntry {
  id: number
  name: string
  client_name: string | null
  url: string
  type: SiteType
  monitoring_mode: MonitoringMode
  active: boolean
  status: SiteStatus
  uptime_24h_pct: number | null
  uptime_7d_pct: number | null
  avg_latency_ms: number | null
  sparkline: SparklinePoint[]
  next_ssl_expiry: string | null
  ssl_valid: boolean | null
  ssl_error: string | null
  next_domain_expiry: string | null
  vulnerable_plugin_count: number
  outdated_plugin_count: number
  core_update_available: string | null
  mu_plugin_version: string | null
  mu_plugin_outdated: boolean
  open_incident_count: number
}

export interface DashboardResponse {
  sites: SiteDashboardEntry[]
}

export interface GlobalConfig {
  id: number
  telegram_chat_id: string | null
  digest_hour: number
  digest_timezone: string
  ssl_alert_days_json: number[]
  domain_alert_days_json: number[]
  panel_base_url: string
  wpscan_api_key: string | null
  gsb_api_key: string | null
  vt_api_key: string | null
  healthchecks_url: string | null
  wpscan_daily_limit: number
  wpscan_requests_today: number
  wpscan_requests_date: string | null
}

export interface SuspiciousPattern {
  id: number
  pattern: string
  is_regex: boolean
  description: string | null
  enabled: boolean
  severity: Severity
}

export interface TrustedDomain {
  id: number
  domain: string
  description: string | null
  enabled: boolean
}

export interface WpInventory {
  snapshot: {
    timestamp: string
    mu_plugin_version: string | null
    mu_plugin_outdated: boolean
    core_version: string | null
    core_update_available: string | null
    php_version: string | null
    plugins: Array<{ slug: string; installed: string; available: string | null; active: boolean }>
    themes: Array<{ slug: string; installed: string; available: string | null }>
    admin_usernames: string[]
  } | null
}

export interface DependencyAuditSummary {
  id: number
  timestamp: string
  tool: string
  high_critical_count: number
  summary: string | null
}

export interface LatencyPoint {
  timestamp: string
  latency_ms: number | null
  success: boolean
}
