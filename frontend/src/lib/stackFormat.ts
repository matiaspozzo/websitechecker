import type { CSSProperties } from "react"
import type { SiteType } from "../api/types"

export const STACK_ORDER: SiteType[] = ["wordpress", "laravel", "nextjs", "other"]

export const STACK_LABELS: Record<SiteType, string> = {
  wordpress: "WordPress",
  laravel: "Laravel",
  nextjs: "Next.js",
  other: "Other",
}

const STACK_COLOR_VAR: Record<SiteType, string> = {
  wordpress: "var(--color-stack-wordpress)",
  laravel: "var(--color-stack-laravel)",
  nextjs: "var(--color-stack-nextjs)",
  other: "var(--color-stack-other)",
}

export function stackColor(type: SiteType): string {
  return STACK_COLOR_VAR[type]
}

/** Subtle left-border + background wash so cards/rows read as grouped by
 * stack without fighting the status colors (up/warning/critical) already
 * used elsewhere on the same card. */
export function stackCardStyle(type: SiteType): CSSProperties {
  const color = stackColor(type)
  return {
    borderLeft: `3px solid ${color}`,
    backgroundColor: `color-mix(in srgb, ${color} 6%, var(--color-surface))`,
  }
}

export function stackRowStyle(type: SiteType): CSSProperties {
  const color = stackColor(type)
  return {
    borderLeft: `3px solid ${color}`,
    backgroundColor: `color-mix(in srgb, ${color} 5%, var(--color-surface))`,
  }
}
