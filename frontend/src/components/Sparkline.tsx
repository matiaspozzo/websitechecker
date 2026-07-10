import type { SparklinePoint } from "../api/types"

const WIDTH = 120
const HEIGHT = 28

export function Sparkline({ points }: { points: SparklinePoint[] }) {
  const withLatency = points.filter((p) => p.latency_ms !== null) as Array<
    SparklinePoint & { latency_ms: number }
  >

  if (withLatency.length < 2) {
    return <div className="h-[28px] w-[120px] font-mono text-xs text-ink-muted">no data</div>
  }

  const max = Math.max(...withLatency.map((p) => p.latency_ms))
  const min = Math.min(...withLatency.map((p) => p.latency_ms))
  const range = max - min || 1

  const coords = withLatency.map((p, i) => {
    const x = (i / (withLatency.length - 1)) * WIDTH
    const y = HEIGHT - ((p.latency_ms - min) / range) * HEIGHT
    return { x, y, success: p.success }
  })

  const path = coords.map((c, i) => `${i === 0 ? "M" : "L"}${c.x.toFixed(1)},${c.y.toFixed(1)}`).join(" ")
  const lastFailed = !coords[coords.length - 1].success

  return (
    <svg width={WIDTH} height={HEIGHT} viewBox={`0 0 ${WIDTH} ${HEIGHT}`} role="img" aria-label="Latency trend">
      <path d={path} fill="none" stroke="var(--color-accent-dim)" strokeWidth={1.5} />
      <circle
        cx={coords[coords.length - 1].x}
        cy={coords[coords.length - 1].y}
        r={2.5}
        fill={lastFailed ? "var(--color-status-down)" : "var(--color-accent)"}
      />
    </svg>
  )
}
