import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"
import type { LatencyPoint } from "../api/types"

export function LatencyChart({ points }: { points: LatencyPoint[] }) {
  if (points.length === 0) {
    return <div className="font-mono text-sm text-ink-muted">No latency data yet.</div>
  }

  const data = points.map((p) => ({
    timestamp: p.timestamp,
    label: new Date(p.timestamp).toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit" }),
    latency_ms: p.latency_ms,
    success: p.success,
  }))

  return (
    <div className="h-64 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
          <XAxis
            dataKey="label"
            stroke="var(--color-ink-muted)"
            fontSize={11}
            fontFamily="var(--font-mono)"
            tickLine={false}
            axisLine={{ stroke: "var(--color-border)" }}
            minTickGap={40}
          />
          <YAxis
            stroke="var(--color-ink-muted)"
            fontSize={11}
            fontFamily="var(--font-mono)"
            tickLine={false}
            axisLine={{ stroke: "var(--color-border)" }}
            width={48}
            unit="ms"
          />
          <Tooltip
            contentStyle={{
              backgroundColor: "var(--color-surface)",
              border: "1px solid var(--color-border)",
              borderRadius: 6,
              fontFamily: "var(--font-mono)",
              fontSize: 12,
            }}
            labelStyle={{ color: "var(--color-ink)" }}
          />
          <Line
            type="monotone"
            dataKey="latency_ms"
            stroke="var(--color-accent)"
            strokeWidth={2}
            dot={false}
            connectNulls
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
