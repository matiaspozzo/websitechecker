import type { SiteStatus } from "../api/types"

const STATUS_META: Record<SiteStatus, { label: string; color: string }> = {
  up: { label: "up", color: "var(--color-status-up)" },
  down: { label: "down", color: "var(--color-status-down)" },
  paused: { label: "paused", color: "var(--color-status-paused)" },
  unknown: { label: "unknown", color: "var(--color-status-paused)" },
}

export function StatusBadge({ status }: { status: SiteStatus }) {
  const meta = STATUS_META[status]
  return (
    <span className="inline-flex items-center gap-1.5 font-mono text-xs uppercase tracking-wide text-ink-muted">
      <span
        className="inline-block h-2 w-2 rounded-full"
        style={{ backgroundColor: meta.color }}
        aria-hidden
      />
      {meta.label}
    </span>
  )
}
